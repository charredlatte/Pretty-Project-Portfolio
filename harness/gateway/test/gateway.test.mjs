// The gateway end to end, in workerd: `wrangler dev` with a fresh state (its two secrets make the first account,
// charlotte's, as they do on the first deploy with accounts), then claude.ai's sign-in as claude.ai
// does it (register, authorize with her password, token, refresh), the tools as the page and an agent call
// them, and the sign-in lock.
//
//     npm test        (from harness/gateway, after npm install)
import assert from "node:assert/strict";
import { execFileSync, spawn } from "node:child_process";
import { createHash, randomBytes } from "node:crypto";
import { mkdtempSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { createServer as createHttpServer } from "node:http";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, before, describe, test } from "node:test";
import { fileURLToPath } from "node:url";

const HERE = fileURLToPath(new URL("..", import.meta.url));
const REPORT = join(HERE, "../hooks/report.py");
const TOKEN = "agent-key-" + randomBytes(12).toString("hex");
const QUEEN = "queen-key-" + randomBytes(12).toString("hex");
const PASSWORD = "her-password-" + randomBytes(8).toString("hex");
const CALLBACK = "https://claude.ai/api/mcp/auth_callback";

const freePort = () => new Promise((done) => {
	const s = createServer().listen(0, "127.0.0.1", () => { const { port } = s.address(); s.close(() => done(port)); });
});

let base, wrangler, state, log = "", herCookie = "";

// A stand-in System One server (the shape laya-serve, Clef and Jev share), in place of the Worker's AI binding,
// which wrangler dev can only reach signed in to Cloudflare. It keeps every request it was asked.
const CONFIG = join(HERE, ".wrangler.test.jsonc");
const asked = [];
let decider;
function startDecider() {
	return new Promise((done) => {
		decider = createHttpServer((req, res) => {
			let data = "";
			req.on("data", (d) => { data += d; });
			req.on("end", () => {
				const body = JSON.parse(data);
				asked.push({ path: req.url, auth: req.headers.authorization || null, body });
				const answers = {};
				for (const [name, q] of Object.entries(body.questions)) {
					if (q.type === "noul") answers[name] = { type: "noul", noul: name === "held_path" ? 0.1 : 0.9 };
					else if (q.type === "choice") {
						const keys = Object.keys(q.criteria), first = keys[0];
						answers[name] = { type: "choice", choice: first, confidence: 0.8, probabilities: Object.fromEntries(keys.map((k) => [k, k === first ? 0.8 : 0.2 / Math.max(1, keys.length - 1)])) };
					} else answers[name] = { type: "score", score: 1, confidence: 0.7, probabilities: { 0: 0.1, 1: 0.9 } };
				}
				res.setHeader("Content-Type", "application/json");
				res.end(JSON.stringify({ model: "stand-in", answers, usage: { input_tokens: 42 } }));
			});
		}).listen(0, "127.0.0.1", () => done(decider.address().port));
	});
}

// wrangler dev on a fresh state; again on the same state, at the end, as a deploy would start a new isolate
async function start({ password = PASSWORD, dir = state, vars = [] } = {}) {
	const [port, inspector] = [await freePort(), await freePort()];
	base = `http://127.0.0.1:${port}`;
	log = "";
	// the real config without its AI binding (remote, needs a Cloudflare sign-in): decisions go to the stand-in instead
	writeFileSync(CONFIG, readFileSync(join(HERE, "wrangler.jsonc"), "utf8").replace(/^\s*"ai":.*\n/m, ""));
	wrangler = spawn(process.execPath, [join(HERE, "node_modules/wrangler/bin/wrangler.js"), "dev", "--config", CONFIG, "--ip", "127.0.0.1",
		"--port", String(port), "--inspector-port", String(inspector), "--persist-to", dir,
		"--var", "CATIO_TOKEN:" + TOKEN, ...(password ? ["--var", "CATIO_PASSWORD:" + password] : []), "--var", "CATIO_QUEEN:" + QUEEN,
		"--var", "DECIDE_URL:http://127.0.0.1:" + deciderPort + "/", "--var", "DECIDE_KEY:k1", ...vars.flatMap((v) => ["--var", v])], {
		cwd: HERE, env: { ...process.env, WRANGLER_SEND_METRICS: "false", NO_COLOR: "1" }, stdio: ["ignore", "pipe", "pipe"],
		detached: true,   // its own process group, so workerd goes with it
	});
	wrangler.stdout.on("data", (d) => { log += d; });
	wrangler.stderr.on("data", (d) => { log += d; });
	for (let i = 0; i < 120; i++) {
		if (/Ready on/.test(log)) return;
		if (wrangler.exitCode !== null) break;
		await new Promise((r) => setTimeout(r, 500));
	}
	throw new Error("wrangler dev didn't start:\n" + log);
}
const stop = () => { try { process.kill(-wrangler.pid, "SIGTERM"); } catch { /* already gone */ } };

let deciderPort;
before(async () => {
	state = mkdtempSync(join(tmpdir(), "catio-gateway-"));
	deciderPort = await startDecider();
	await start();
});

after(() => {
	stop();
	decider.close();
	rmSync(state, { recursive: true, force: true });
	rmSync(CONFIG, { force: true });
});

// ---------- helpers ----------
let nextId = 1;
async function rpc(bearer, method, params) {
	const r = await fetch(base + "/mcp", {
		method: "POST", headers: { "Content-Type": "application/json", Authorization: "Bearer " + bearer },
		body: JSON.stringify({ jsonrpc: "2.0", id: nextId++, method, params }),
	});
	assert.equal(r.status, 200, await r.clone().text());
	return r.json();
}
// a tool's result, or its refusal as { refused: text }
async function tool(bearer, name, args = {}) {
	const { result, error } = await rpc(bearer, "tools/call", { name, arguments: args });
	if (error) return { rpcError: error };
	return result.isError ? { refused: result.content[0].text } : result.structuredContent;
}
const form = (fields) => new URLSearchParams(fields);
const cookieOf = (r) => r.headers.getSetCookie().map((c) => c.split(";")[0]).join("; ");

async function register(redirectUris) {
	return fetch(base + "/register", {
		method: "POST", headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ client_name: "Claude", redirect_uris: redirectUris, token_endpoint_auth_method: "none",
			grant_types: ["authorization_code", "refresh_token"], response_types: ["code"] }),
	});
}

// GET /authorize as the browser claude.ai opens: the page, its handle, and the cookie that binds them
async function openSignIn(clientId) {
	const verifier = randomBytes(32).toString("base64url");
	const challenge = createHash("sha256").update(verifier).digest("base64url");
	const q = new URLSearchParams({ response_type: "code", client_id: clientId, redirect_uri: CALLBACK, state: "st-1",
		code_challenge: challenge, code_challenge_method: "S256", resource: base + "/mcp" });
	const r = await fetch(base + "/authorize?" + q);
	const html = await r.text();
	return { status: r.status, html, headers: r.headers, cookie: cookieOf(r), verifier,
		handle: (html.match(/name="handle" value="([^"]+)"/) || [])[1] };
}

async function submit(page, fields) {
	return fetch(base + "/authorize", {
		method: "POST", redirect: "manual", headers: { "Content-Type": "application/x-www-form-urlencoded", Cookie: page.cookie },
		body: form({ handle: page.handle, client: "Claude", host: "claude.ai", user: "charlotte", ...fields }),
	});
}

// the whole sign-in, as claude.ai and a browser do it: an access token that acts as the user (charlotte unless said)
async function signIn(who = { user: "charlotte", password: PASSWORD }) {
	const { client_id } = await (await register([CALLBACK])).json();
	const page = await openSignIn(client_id);
	const r = await submit(page, { ...who, decision: "allow" });
	const code = new URL(r.headers.get("location")).searchParams.get("code");
	const t = await fetch(base + "/token", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
		body: form({ grant_type: "authorization_code", code, redirect_uri: CALLBACK, client_id, code_verifier: page.verifier, resource: base + "/mcp" }) });
	return { client_id, ...(await t.json()) };
}

// ---------- the tests ----------
// The café on the gateway's own address: hers alone, behind her password, as OpenClaw's Control UI is.
describe("the café", () => {
	let cookie = "";
	const KEY = () => ({ Authorization: "Bearer " + TOKEN });
	const api = (path, init = {}) => fetch(base + path, { ...init, headers: { Cookie: cookie, "X-Catio": "1", ...(init.headers || {}) } });
	const put = (path, data, method = "PUT") => api("/api/db/" + path, { method, body: JSON.stringify({ data }) });

	test("asks for her password before showing anything", async () => {
		const first = await (await fetch(base + "/")).text();
		assert.match(first, /Your handle/);
		assert.match(first, /Your Catio password/);
		assert.doesNotMatch(first, /id="houseBtn"/);
		for (const p of ["/api/db", "/art/licensed/pochi.png", "/files/x", "/ws"]) assert.equal((await fetch(base + p)).status, 401, p);
		const wrong = await fetch(base + "/login", { method: "POST", body: new URLSearchParams({ user: "charlotte", password: "not-the-password-sorry" }), redirect: "manual" });
		assert.equal(wrong.status, 401);
		const nobody = await fetch(base + "/login", { method: "POST", body: new URLSearchParams({ user: "nobody", password: PASSWORD }), redirect: "manual" });
		assert.equal(nobody.status, 401);
		const right = await fetch(base + "/login", { method: "POST", body: new URLSearchParams({ user: "Charlotte", password: PASSWORD }), redirect: "manual" });
		assert.equal(right.status, 303);
		const set = right.headers.get("set-cookie");
		assert.match(set, /^__Host-catio=[0-9a-f]{64}; Path=\/; Secure; HttpOnly; SameSite=Strict/);
		cookie = set.split(";")[0];
		const r = await fetch(base + "/", { headers: { Cookie: cookie } });
		assert.equal(r.headers.get("x-frame-options"), "DENY");
		const page = await r.text();
		assert.match(page, /<script src="\/runtime.js"><\/script><\/head><body>/);
		assert.match(page, /id="houseBtn"/);
		assert.match(page, /<link rel="icon" type="image\/png" href="\/art\/licensed\/ui\/logo.png">/, "the tab's icon is the café's cat");
	});

	test("moves her data in once, with the agents' key", async () => {
		const docs = { "rooms/kitchen": { name: "Kitchen", repos: ["groceries"] }, "cats/c1": { title: "A chat", mood: "needs" } };
		const send = (headers) => fetch(base + "/api/import", { method: "POST", headers, body: JSON.stringify({ docs }) });
		assert.equal((await send({})).status, 401);
		assert.equal((await send({ Cookie: cookie })).status, 401);
		assert.equal((await send(KEY())).status, 200);
		assert.equal((await send(KEY())).status, 409);
		assert.deepEqual((await (await api("/api/db")).json()).docs, docs);
	});

	test("keeps the page's documents, and tells an open café at once", async () => {
		const heard = [];
		const ws = new WebSocket(base.replace("http", "ws") + "/ws", { headers: { Cookie: cookie, Origin: base } });
		ws.onmessage = (e) => heard.push(JSON.parse(e.data));
		await new Promise((ok, no) => { ws.onopen = ok; ws.onerror = no; });
		assert.equal((await fetch(base + "/api/db/rooms/kitchen", { method: "PUT", headers: { Cookie: cookie }, body: JSON.stringify({ data: {} }) })).status, 403);
		assert.equal((await put("rooms/kitchen", { name: "Cuisine" })).status, 200);
		assert.equal((await put("cats/c1", { mood: "done" }, "PATCH")).status, 200);
		assert.equal((await put("cats/nobody", { mood: "done" }, "PATCH")).status, 404);
		assert.equal((await put("rooms", { name: "x" })).status, 400);
		assert.equal((await api("/api/db/cats/c1", { method: "DELETE" })).status, 200);
		const { docs } = await (await api("/api/db")).json();
		assert.deepEqual(docs, { "rooms/kitchen": { name: "Cuisine" } });
		await new Promise((r) => setTimeout(r, 300));
		assert.deepEqual(heard.filter((m) => m.type === "doc").map((m) => [m.path, m.data]),
			[["rooms/kitchen", { name: "Cuisine" }], ["cats/c1", { title: "A chat", mood: "done" }], ["cats/c1", null]]);
		await api("/api/tools/report_status", { method: "POST", body: JSON.stringify({ agent: "cafe-cat", mood: "busy" }) });
		await new Promise((r) => setTimeout(r, 300));
		assert.ok(heard.some((m) => m.type === "agents"), "a cat's change reaches the café");
		ws.close();
		const stranger = new WebSocket(base.replace("http", "ws") + "/ws", { headers: { Cookie: cookie, Origin: "https://elsewhere.example" } });
		await assert.rejects(new Promise((ok, no) => { stranger.onopen = ok; stranger.onerror = no; }));
	});

	test("serves the licensed art only to her, from what the agents' key uploaded", async () => {
		const png = Buffer.from("89504e470d0a1a0a0000", "hex");
		const up = (path, body, headers = KEY()) => fetch(base + "/api/" + path, { method: "PUT", headers, body });
		assert.equal((await up("art/licensed/pochi.png", png, {})).status, 401);
		assert.equal((await up("art/licensed/evil.html", "<script>")).status, 400);
		assert.equal((await up("art/licensed/pochi.png", png)).status, 200);
		assert.equal((await fetch(base + "/art/licensed/pochi.png")).status, 401);
		const r = await api("/art/licensed/pochi.png");
		assert.equal(r.headers.get("content-type"), "image/png");
		assert.deepEqual(Buffer.from(await r.arrayBuffer()), png);
	});

	test("keeps the brain's files, and opens them where nothing in them can run", async () => {
		const up = await (await api("/api/files", { method: "POST", headers: { "Content-Type": "text/html", "X-Name": "notes.html" }, body: "<script>alert(1)</script>" })).json();
		const r = await api(up.url);
		assert.equal(await r.text(), "<script>alert(1)</script>");
		assert.match(r.headers.get("content-security-policy"), /^sandbox/);
		assert.match(r.headers.get("content-disposition"), /^attachment/);
		assert.equal((await api("/api/files/" + up.id, { method: "DELETE" })).status, 200);
		assert.equal((await api(up.url)).status, 404);
	});

	test("uses the gateway's tools as herself", async () => {
		assert.equal((await api("/api/tools/comment", { method: "POST", body: JSON.stringify({ cat: "cafe-cat", text: "From the café" }) })).status, 200);
		const { notes } = await (await api("/api/tools/comments", { method: "POST", body: JSON.stringify({ cat: "cafe-cat" }) })).json();
		assert.deepEqual([notes.at(-1).author, notes.at(-1).text], ["owner", "From the café"]);
		assert.equal((await api("/api/tools/no_such_tool", { method: "POST", body: "{}" })).status, 404);
		assert.equal((await api("/api/tools/manage", { method: "POST", body: JSON.stringify({ cat: "nobody", action: "archive" }) })).status, 400);
		assert.match(await (await fetch(base + "/runtime.js")).text(), /catioGateway: true/);
	});
});

// Accounts: the first is charlotte's, from the two secrets; an admin makes the others; each has a house of its own.
describe("accounts", () => {
	const TESTER = "tester-password-" + randomBytes(6).toString("hex");
	let her = "", theirs = "", key = "", TESTER_NOW = "";
	const KEY = (k) => ({ Authorization: "Bearer " + k, "Content-Type": "application/json" });
	const login = async (user, password) => {
		const r = await fetch(base + "/login", { method: "POST", body: new URLSearchParams({ user, password }), redirect: "manual" });
		return { status: r.status, cookie: r.status === 303 ? r.headers.get("set-cookie").split(";")[0] : "" };
	};
	const as = (cookie, path, init = {}) => fetch(base + path, { ...init, headers: { Cookie: cookie, "X-Catio": "1", ...(init.headers || {}) } });

	test("lets an admin, signed in to the café, create an account, and nobody else", async () => {
		({ cookie: herCookie } = await login("charlotte", PASSWORD));
		assert.ok(herCookie);
		const make = (cookie, body, headers = {}) => fetch(base + "/api/users", { method: "POST", headers: { Cookie: cookie, "X-Catio": "1", ...headers }, body: JSON.stringify(body) });
		assert.equal((await fetch(base + "/api/users", { method: "POST", headers: KEY(TOKEN), body: JSON.stringify({ id: "tester", password: TESTER }) })).status, 401, "never with a key: one is in every session's environment");
		assert.equal((await make("", { id: "tester", password: TESTER })).status, 401);
		assert.equal((await make(herCookie, { id: "Tester!", password: TESTER })).status, 400);
		assert.equal((await make(herCookie, { id: "tester", password: "short" })).status, 400);
		assert.equal((await make(herCookie, { id: "house", password: TESTER })).status, 400, "the first house's name is kept");
		assert.equal((await fetch(base + "/api/users", { method: "POST", headers: { Cookie: herCookie, "X-Catio": "1" }, body: "null" })).status, 400, "a null body is a bad request, not a crash");
		const made = await make(herCookie, { id: "Tester", password: TESTER });
		assert.equal(made.status, 201);
		assert.deepEqual(await made.json(), { id: "tester", house: "tester" });
		assert.equal((await make(herCookie, { id: "tester", password: TESTER })).status, 400, "a handle is taken once");
		({ cookie: theirs } = await login("tester", TESTER));
		assert.ok(theirs);
		assert.equal((await make(theirs, { id: "third", password: TESTER })).status, 403, "tester is no admin");
	});

	test("mints a key from a signed-in browser, shown once", async () => {
		assert.equal((await fetch(base + "/api/keys", { method: "POST", headers: KEY(TOKEN), body: "{}" })).status, 401, "a key doesn't sign a browser in");
		assert.equal((await fetch(base + "/api/keys", { method: "POST", headers: { Cookie: theirs }, body: "{}" })).status, 403, "not without X-Catio");
		const r = await as(theirs, "/api/keys", { method: "POST", body: JSON.stringify({ name: "laptop" }) });
		assert.equal(r.status, 200);
		({ key } = await r.json());
		assert.match(key, /^[0-9a-f]{64}$/);
		assert.equal((await as(theirs, "/api/keys", { method: "POST", body: "null" })).status, 200, "no name is fine");
		assert.equal((await as(theirs, "/api/keys", { method: "POST", body: JSON.stringify({ name: "laptop" }) })).status, 400, "names are unique");
		assert.deepEqual((await (await as(theirs, "/api/keys")).json()).keys.map((k) => k.name), ["laptop", "key"]);
		assert.equal((await fetch(base + "/api/art/licensed/pochi.png", { method: "PUT", headers: KEY(key), body: "x" })).status, 403, "tester's key uploads no art");
	});

	test("keeps each user's cats in their own house", async () => {
		assert.equal((await tool(key, "report_status", { agent: "tester-cat", mood: "needs", ask: "Which colour?" })).ok, true);
		assert.equal((await tool(TOKEN, "report_status", { agent: "her-cat", mood: "busy" })).ok, true);
		const theirCats = (await tool(key, "list_agents")).agents.map((a) => a.id);
		assert.ok(theirCats.includes("tester-cat") && !theirCats.includes("her-cat"), String(theirCats));
		const herCats = (await tool(TOKEN, "list_agents")).agents.map((a) => a.id);
		assert.ok(herCats.includes("her-cat") && !herCats.includes("tester-cat"), String(herCats));
		// the connector, signed in as tester, sees tester's house
		({ access_token: her } = await signIn());
		const { access_token: them } = await signIn({ user: "tester", password: TESTER });
		assert.deepEqual((await tool(them, "list_agents")).agents.map((a) => a.id), ["tester-cat"]);
		assert.ok(!(await tool(her, "list_agents")).agents.some((a) => a.id === "tester-cat"));
		assert.equal((await tool(them, "comment", { cat: "tester-cat", text: "Blue." })).id !== undefined, true);
		assert.deepEqual((await tool(key, "inbox", { agent: "tester-cat", mark: true })).notes.map((n) => n.text), ["Blue."]);
	});

	test("keeps each user's café apart: documents, files and the import", async () => {
		assert.deepEqual((await (await as(theirs, "/api/db")).json()).docs, {});
		const docs = { "rooms/kitchen": { name: "Their kitchen" } };
		assert.equal((await fetch(base + "/api/import", { method: "POST", headers: KEY(key), body: JSON.stringify({ docs }) })).status, 200);
		assert.deepEqual((await (await as(theirs, "/api/db")).json()).docs, docs);
		assert.notDeepEqual((await (await as(herCookie, "/api/db")).json()).docs, docs);
		const up = await (await as(theirs, "/api/files", { method: "POST", headers: { "Content-Type": "text/plain", "X-Name": "mine.txt" }, body: "theirs" })).json();
		assert.equal((await as(theirs, up.url)).status, 200);
		assert.equal((await as(herCookie, up.url)).status, 404);
		assert.equal((await as(herCookie, "/files/tester:" + up.id)).status, 404, "the first house's old key can't be aimed at another house");
		assert.equal((await as(herCookie, "/api/files/" + up.id, { method: "DELETE" })).status, 200);
		assert.equal((await as(theirs, up.url)).status, 200, "another user's delete does nothing");
	});

	test("drops a key, and lets an admin reset a password", async () => {
		assert.equal((await as(theirs, "/api/keys/nope", { method: "DELETE" })).status, 404);
		assert.equal((await as(theirs, "/api/keys/%E0%A4%A", { method: "DELETE" })).status, 404, "a broken escape is no key, not a crash");
		assert.equal((await as(theirs, "/api/db/%E0%A4%A", { method: "DELETE" })).status, 400);
		assert.equal((await as(theirs, "/api/files", { method: "POST", headers: { "Content-Type": "text/plain", "X-Name": "%E0%A4%A" }, body: "x" })).status, 200, "a broken name is just \"file\"");
		assert.equal((await as(theirs, "/api/keys/laptop", { method: "DELETE" })).status, 200);
		assert.equal((await fetch(base + "/mcp", { method: "POST", headers: KEY(key), body: "{}" })).status, 401, "a dropped key is dead");
		assert.equal((await (await as(theirs, "/api/keys")).json()).keys.length, 1);
		const reset = (cookie, id, password) => as(cookie, "/api/users/" + id, { method: "PUT", body: JSON.stringify({ password }) });
		const NEW = "tester-new-password-" + randomBytes(4).toString("hex");
		assert.equal((await fetch(base + "/api/users/charlotte", { method: "PUT", headers: KEY(TOKEN), body: JSON.stringify({ password: NEW }) })).status, 401, "never with a key");
		assert.equal((await reset(theirs, "charlotte", NEW)).status, 403, "tester is no admin");
		assert.equal((await reset(herCookie, "nobody", NEW)).status, 400);
		assert.equal((await reset(herCookie, "tester", "short")).status, 400);
		// a connector tester let in, and a key they minted, die with the reset too
		const { access_token: theirConnector } = await signIn({ user: "tester", password: TESTER });
		assert.ok((await tool(theirConnector, "list_agents")).agents);
		const { key: another } = await (await as(theirs, "/api/keys", { method: "POST", body: JSON.stringify({ name: "phone" }) })).json();
		const done = await reset(herCookie, "Tester", NEW);   // as an admin might type it: the grants are under "tester"
		assert.equal(done.status, 200);
		assert.ok((await done.json()).revoked >= 1, "the connector's grant is found under the handle as spelt in the registry");
		assert.equal((await fetch(base + "/mcp", { method: "POST", headers: KEY(theirConnector), body: "{}" })).status, 401, "the grant is revoked");
		assert.equal((await fetch(base + "/mcp", { method: "POST", headers: KEY(another), body: "{}" })).status, 401, "the key is dead");
		assert.equal((await as(theirs, "/api/db")).status, 401, "a reset signs every browser out");
		assert.equal((await login("tester", TESTER)).status, 401);
		({ cookie: theirs } = await login("tester", NEW));
		assert.ok(theirs);
		assert.deepEqual((await (await as(theirs, "/api/keys")).json()).keys, [], "no keys survive a reset");
		TESTER_NOW = NEW;
	});

	test("locks one user's sign-in, not another's", async () => {
		assert.equal((await login("not a handle!", TESTER_NOW)).status, 401, "an impossible handle is refused without a hash");
		// right sign-ins in flight together don't lock anyone
		const fine = await Promise.all([0, 1, 2, 3, 4, 5].map(() => login("tester", TESTER_NOW)));
		assert.deepEqual(fine.map((r) => r.status), [303, 303, 303, 303, 303, 303]);
		// five guesses at once lock like five in a row: one handle's tries run in turn
		const burst = await Promise.all([0, 1, 2, 3, 4, 5, 6].map((i) => login("tester", "wrong-password-" + i)));
		assert.deepEqual(burst.map((r) => r.status).sort(), [401, 401, 401, 401, 401, 429, 429]);
		assert.equal((await login("tester", TESTER_NOW)).status, 429);
		assert.equal((await login("charlotte", PASSWORD)).status, 303);
		// an admin's reset lets a locked-out user back in
		assert.equal((await as(herCookie, "/api/users/tester", { method: "PUT", body: JSON.stringify({ password: TESTER_NOW }) })).status, 200);
		assert.equal((await login("tester", TESTER_NOW)).status, 303);
	});

	test("lets an admin invite someone, who makes their own account with it, once", async () => {
		const SIGNUP = "guest-password-" + randomBytes(6).toString("hex");
		const invite = (cookie, what = "make", headers = {}) => fetch(base + "/invite", { method: "POST", headers: { Cookie: cookie, ...headers }, body: new URLSearchParams({ do: what }), redirect: "manual" });
		const signUp = (fields) => fetch(base + "/signup", { method: "POST", body: new URLSearchParams({ again: fields.password, ...fields }), redirect: "manual" });
		const codeOf = async (r) => /\/signup\?invite=([0-9a-f]{64})"/.exec(await r.text())?.[1];

		assert.match(await (await fetch(base + "/")).text(), /href="\/signup"/, "the sign-in page points the invited to sign-up");
		assert.match(await (await fetch(base + "/invite")).text(), /Your handle/, "signed out, the invite page asks who you are");
		const { cookie: testerCookie } = await login("tester", TESTER_NOW);
		assert.equal((await fetch(base + "/invite", { headers: { Cookie: testerCookie } })).status, 403, "only an admin invites");
		assert.equal((await invite(testerCookie)).status, 403);
		assert.equal((await invite(herCookie, "make", { Origin: "https://elsewhere.example" })).status, 403, "never from another site");
		const made = await invite(herCookie);
		assert.equal(made.status, 200);
		const code = await codeOf(made);
		assert.ok(code, "the invite is shown as a link");
		assert.match(await (await fetch(base + "/invite", { headers: { Cookie: herCookie } })).text(), /1 invite is out/);
		assert.match(await (await fetch(base + "/signup?invite=" + code)).text(), new RegExp(`value="${code}"`), "the link fills the invite in");

		assert.equal((await signUp({ invite: "0".repeat(64), user: "guest", password: SIGNUP })).status, 400, "a made-up invite opens nothing");
		assert.equal((await signUp({ invite: code, user: "guest", password: SIGNUP, again: SIGNUP + "x" })).status, 400, "the two passwords must match");
		assert.equal((await signUp({ invite: code, user: "tester", password: SIGNUP })).status, 400, "a taken handle stays taken");
		assert.equal((await signUp({ invite: code, user: "guest", password: "short" })).status, 400);
		// a refused sign-up costs the invite nothing; two at once with one invite let one in
		const both = await Promise.all(["guest", "guest-two"].map((user) => signUp({ invite: code, user, password: SIGNUP })));
		// the first user test (5 October): a form sign-up now lands on "your café is ready", its first key shown once,
		// instead of going straight into an empty café with no key and no word of the plugin
		assert.deepEqual(both.map((r) => r.status).sort(), [200, 400], "an invite works once");
		const inRes = both.find((r) => r.status === 200);
		const guest = inRes === both[0] ? "guest" : "guest-two";
		const guestCookie = inRes.headers.get("set-cookie").split(";")[0];
		const ready = await inRes.text();
		assert.match(ready, /Your café is ready/);
		assert.match(ready, /kittychat-house-rules@kittychat/, "the plugin's install lines");
		assert.ok(ready.includes("<code>" + base + "</code>"), "the café's own address");
		const guestKey = /value="([0-9a-f]{64})" aria-label="Your key"/.exec(ready)?.[1];
		assert.ok(guestKey, "the key, once");
		await tool(guestKey, "report_status", { agent: "guest-cat", mood: "busy" });
		assert.deepEqual((await tool(guestKey, "list_agents")).agents.map((a) => a.id), ["guest-cat"], "the key is theirs, in their café");
		assert.ok(!(await tool(TOKEN, "list_agents")).agents.some((a) => a.id === "guest-cat"), "and not in hers");
		assert.deepEqual((await (await as(guestCookie, "/api/db")).json()).docs, {}, "signed in to a café of their own");
		assert.equal((await login(guest, SIGNUP)).status, 303);
		assert.equal((await fetch(base + "/invite", { headers: { Cookie: guestCookie } })).status, 403, "a guest is no admin");
		assert.equal((await as(guestCookie, "/api/users", { method: "POST", body: JSON.stringify({ id: "third", password: SIGNUP }) })).status, 403);
		assert.equal((await as(guestCookie, "/art/licensed/pochi.png")).status, 404, "the packs' art is hers alone");
		assert.equal((await as(herCookie, "/art/licensed/pochi.png")).status, 200);

		// unused invites can be taken back
		const spare = await codeOf(await invite(herCookie));
		assert.match(await (await invite(herCookie, "drop")).text(), /1 invite taken back/);
		assert.equal((await signUp({ invite: spare, user: "late", password: SIGNUP })).status, 400);
	});

	test("lets a browser post the sign-in, invite and sign-up forms with the café's own Origin", async () => {
		// under no-referrer, Chrome posts a form with "Origin: null", and /invite and /signup refuse it (5 October:
		// "Make invites from this page" on her own click); same-origin sends the café's address and nothing elsewhere
		for (const path of ["/", "/invite", "/signup"]) assert.equal((await fetch(base + path)).headers.get("referrer-policy"), "same-origin", path);
		assert.equal((await fetch(base + "/invite", { method: "POST", headers: { Cookie: herCookie, Origin: base }, body: new URLSearchParams({ do: "make" }) })).status, 200);
	});

	test("lets someone's AI use the invite for them, and gives it the account's first key, once", async () => {
		const PARTNER = "partner-password-" + randomBytes(6).toString("hex");
		const made = await fetch(base + "/invite", { method: "POST", headers: { Cookie: herCookie }, body: new URLSearchParams({ do: "make" }) });
		const code = /\/signup\?invite=([0-9a-f]{64})"/.exec(await made.text())[1];
		const page = await (await fetch(base + "/signup?invite=" + code)).text();
		assert.ok(page.includes("as their AI?") && page.includes(`"invite": "${code}"`) && page.includes(base + "/mcp"), "the link says what an AI does");
		assert.ok(!(await (await fetch(base + "/signup")).text()).includes("as their AI?"), "not without an invite");
		assert.ok(page.includes("kittychat-house-rules@kittychat") && page.includes("Without the plugin the two variables do"), "the two variables need the plugin's hook");

		const use = (body, headers = {}) => fetch(base + "/signup", { method: "POST", headers: { "Content-Type": "application/json", ...headers }, body: JSON.stringify(body) });
		const short = await use({ invite: code, handle: "partner", password: "short" });
		assert.equal(short.status, 400);
		assert.equal((await short.json()).code, "bad_request", "an AI gets JSON back");
		assert.equal((await use({ invite: code, handle: "partner", password: PARTNER }, { Origin: "https://elsewhere.example" })).status, 403, "never from another site");
		const r = await use({ invite: code, handle: "Partner", password: PARTNER });
		assert.equal(r.status, 201, "a refused try left the invite as it was");
		const { handle, key: theirKey, mcp } = await r.json();
		assert.deepEqual([handle, mcp], ["partner", base + "/mcp"]);
		assert.match(theirKey, /^[0-9a-f]{64}$/);
		assert.equal((await use({ invite: code, handle: "partner-two", password: PARTNER })).status, 400, "an invite works once");

		// the key reports into their own house, and the password signs them in to their café
		assert.equal((await tool(theirKey, "report_status", { agent: "partner-cat", mood: "busy" })).ok, true);
		assert.deepEqual((await tool(theirKey, "list_agents")).agents.map((a) => a.id), ["partner-cat"]);
		assert.ok(!(await tool(TOKEN, "list_agents")).agents.some((a) => a.id === "partner-cat"));
		assert.equal((await login("partner", PARTNER)).status, 303);
	});
});

// The queen of the house: Charlotte talks to her in the café; her runner (harness/runner) waits here with the
// queen's own key, runs a turn, and streams what she says back to every open café.
describe("the queen", () => {
	let her, cookie;
	const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
	const runner = (path, body) => fetch(base + path, { method: "POST", headers: { Authorization: "Bearer " + QUEEN, "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
	const wait = () => runner("/api/runner/wait").then((r) => r.json());
	const say = (body) => runner("/api/runner/say", body);
	const api = (path, init = {}) => fetch(base + path, { ...init, headers: { Cookie: cookie, "X-Catio": "1", ...(init.headers || {}) } });
	const put = (path, data) => api("/api/db/" + path, { method: "PUT", body: JSON.stringify({ data }) });
	const queen = async () => (await tool(her, "list_agents")).agents.find((a) => a.id === "queen");

	before(async () => {
		her = (await signIn()).access_token;
		const r = await fetch(base + "/login", { method: "POST", body: new URLSearchParams({ user: "charlotte", password: PASSWORD }), redirect: "manual" });
		cookie = r.headers.get("set-cookie").split(";")[0];
	});

	test("hears what Charlotte says to her the moment she says it, with her own key only", async () => {
		assert.equal((await fetch(base + "/api/runner/wait", { method: "POST", headers: { Authorization: "Bearer " + TOKEN } })).status, 401, "the agents' key");
		assert.equal((await fetch(base + "/api/runner/wait", { method: "POST", headers: { Cookie: cookie, "X-Catio": "1" } })).status, 401, "her browser");
		assert.equal((await put("queens/house", { name: "Duchesse", manner: "Elizabethan English, warm.", greeting: "Good morrow, my lady." })).status, 200);
		assert.equal(await queen(), undefined, "no runner yet: no queen in the house");
		const started = Date.now();
		const waiting = wait();
		await sleep(400);
		assert.ok((await tool(her, "comment", { cat: "queen", text: "Who needs me today?" })).id);
		const got = await waiting;
		assert.ok(Date.now() - started < 5000, "the wait came back as she spoke, not at its timeout");
		assert.deepEqual(got.notes.map((n) => [n.author, n.text]), [["owner", "Who needs me today?"]]);
		assert.deepEqual([got.stop, got.routine], [false, null]);
		assert.deepEqual(got.character, { name: "Duchesse", manner: "Elizabethan English, warm.", greeting: "Good morrow, my lady." });
		assert.equal((await queen()).via, "runner", "her runner is present");
		// each note is handed out once
		const again = wait();
		await sleep(300);
		await tool(her, "comment", { cat: "queen", text: "And the shop?" });
		assert.deepEqual((await again).notes.map((n) => n.text), ["And the shop?"]);
	});

	test("streams what she says to an open café, and keeps it when she is done", async () => {
		const heard = [];
		const ws = new WebSocket(base.replace("http", "ws") + "/ws", { headers: { Cookie: cookie, Origin: base } });
		ws.onmessage = (e) => heard.push(JSON.parse(e.data));
		await new Promise((ok, no) => { ws.onopen = ok; ws.onerror = no; });
		assert.equal((await say({ turn: "t1", text: "Good morrow, my", done: false })).status, 200);
		assert.equal((await queen()).mood, "busy");
		assert.equal((await say({ turn: "t1", text: "Good morrow, my lady. Two cats need thee.", done: true })).status, 200);
		assert.equal((await queen()).mood, "done");
		await sleep(300);
		ws.close();
		assert.deepEqual(heard.filter((m) => m.type === "queen").map((m) => [m.turn, m.text, m.done]),
			[["t1", "Good morrow, my", false], ["t1", "Good morrow, my lady. Two cats need thee.", true]]);
		assert.deepEqual((await tool(her, "comments", { cat: "queen" })).notes.map((n) => [n.author, n.text]),
			[["owner", "Who needs me today?"], ["owner", "And the shop?"], ["queen", "Good morrow, my lady. Two cats need thee."]]);
		assert.equal((await say({ turn: "t1", text: "", done: true })).status, 200, "an empty turn stores nothing");
		assert.equal((await tool(her, "comments", { cat: "queen" })).notes.length, 3);
		assert.equal((await runner("/api/runner/say", { text: "x".repeat(70000), done: true })).status, 413);
	});

	test("passes on what she is doing to an open café, trimmed, and keeps none of it", async () => {
		const heard = [];
		const ws = new WebSocket(base.replace("http", "ws") + "/ws", { headers: { Cookie: cookie, Origin: base } });
		ws.onmessage = (e) => heard.push(JSON.parse(e.data));
		await new Promise((ok, no) => { ws.onopen = ok; ws.onerror = no; });
		const many = Array.from({ length: 20 }, (_, i) => ({ tool: "comments", cat: "cse_" + i, extra: "dropped" }));
		assert.equal((await say({ turn: "t5", text: "", done: false, steps: [] })).status, 200);
		assert.equal((await say({ turn: "t5", text: "", done: false, steps: [...many, null, { cat: "no tool" }, { tool: "x".repeat(99), action: 7 }] })).status, 200);
		assert.equal((await say({ turn: "t5", text: "Done.", done: true, steps: many })).status, 200);
		await sleep(300);
		ws.close();
		const q = heard.filter((m) => m.type === "queen");
		assert.deepEqual(q[0].steps, [], "awake, nothing done yet");
		assert.equal(q[1].steps.length, 10, "the last twelve, less the two that aren't steps");
		assert.deepEqual(q[1].steps[0], { tool: "comments", cat: "cse_11" });
		assert.deepEqual(q[1].steps.at(-1), { tool: "x".repeat(60) });
		assert.equal(q[2].steps, undefined, "a finished turn has no steps");
		const kept = (await tool(her, "comments", { cat: "queen" })).notes.at(-1);
		assert.deepEqual([kept.text, kept.steps], ["Done.", undefined]);
	});

	test("stops the turn she is on when Charlotte says so", async () => {
		const waiting = wait();
		await sleep(300);
		assert.equal((await api("/api/tools/manage", { method: "POST", body: JSON.stringify({ cat: "queen", action: "pause" }) })).status, 200);
		assert.equal((await waiting).stop, true);
		assert.match((await tool(her, "manage", { cat: "queen", action: "archive" })).refused, /only pause/);
	});

	test("speaks as the queen with her key, never as Charlotte, and the cats hear her", async () => {
		const cat = "session_01Queen";
		const env = { ...process.env, CATIO_URL: base, CATIO_TOKEN: TOKEN, CLAUDE_CODE_REMOTE_SESSION_ID: cat, NO_PROXY: "127.0.0.1", no_proxy: "127.0.0.1" };
		const hook = (data) => execFileSync("python3", [REPORT], { input: JSON.stringify({ cwd: HERE, ...data }), env, encoding: "utf8" });
		hook({ hook_event_name: "SessionStart", source: "startup" });
		assert.equal((await tool(QUEEN, "comment", { cat, text: "x", author: "owner" })).refused, "only the owner writes as the owner");
		assert.equal((await tool(TOKEN, "comment", { cat, text: "x", author: "queen" })).refused, "only the queen's runner writes as the queen");
		assert.equal((await tool(TOKEN, "manage", { cat, action: "wrap_up" })).refused, "only the owner manages a cat");
		assert.ok((await tool(QUEEN, "comment", { cat, text: "Prithee, push thy work." })).id);
		assert.equal((await tool(QUEEN, "manage", { cat, action: "wrap_up" })).ok, true);
		// the session's hook hands the queen's words in as hers, and her request with them
		const held = JSON.parse(hook({ hook_event_name: "Stop", stop_hook_active: false }));
		assert.match(held.reason, /\[Catio\] The queen says: Prithee, push thy work\./);
		assert.match(held.reason, /\[Catio\] Request: wrap_up/);
		// what the cat says last shows on it, for the page to carry to the queen
		assert.equal((await tool(her, "list_agents")).agents.find((a) => a.id === cat).said, undefined);
		execFileSync("python3", [REPORT, "say", "Pushed, your majesty."], { env });
		const me = (await tool(her, "list_agents")).agents.find((a) => a.id === cat);
		assert.equal(me.said.text, "Pushed, your majesty.");
		assert.ok(me.said.at > 0);
		assert.deepEqual((await tool(TOKEN, "comments", { cat })).notes.map((n) => n.author), ["queen", "session"]);
	});

	test("sets Charlotte homework whose answers unblock a cat", async () => {
		const cat = "session_01Queen";
		assert.match((await tool(TOKEN, "quiz", { for: cat, title: "x", questions: [{ q: "y" }] })).refused, /only the queen or the owner/);
		assert.match((await tool(QUEEN, "quiz", { title: "x", questions: [] })).refused, /questions is a list/);
		const { id } = await tool(QUEEN, "quiz", { for: cat, title: "The menu fix", questions: [{ q: "Merge it?", options: ["Yes, merge it", "Not yet"] }, { q: "A word for the cat?", free: true }] });
		assert.ok(id);
		const open = (await tool(her, "quizzes")).quizzes;
		assert.deepEqual(open.map((z) => [z.id, z.for, z.title, z.status, z.by, z.questions.length]), [[id, cat, "The menu fix", "set", "queen", 2]]);
		assert.deepEqual(open[0].questions[0], { q: "Merge it?", options: ["Yes, merge it", "Not yet"], free: false });
		assert.equal(open[0].questions[1].free, true);
		assert.match((await tool(TOKEN, "answer", { quiz: id, answers: ["Yes, merge it", "Thanks"] })).refused, /only the owner/);
		assert.match((await tool(her, "answer", { quiz: id, answers: ["Yes, merge it"] })).refused, /one answer per question/);
		const waiting = wait();   // her runner is waiting: handing in reaches the queen at once
		await sleep(300);
		assert.deepEqual(await tool(her, "answer", { quiz: id, answers: ["Yes, merge it", "Well done, thou good cat"] }), { ok: true, told: true });
		assert.deepEqual((await tool(her, "quizzes")).quizzes, []);
		assert.equal((await tool(her, "quizzes", { done: true })).quizzes[0].answers[1], "Well done, thou good cat");
		const box = await tool(TOKEN, "inbox", { agent: cat, mark: true });
		assert.equal(box.notes.at(-1).author, "owner");
		assert.equal(box.notes.at(-1).text, "Homework handed in: The menu fix\n1. Merge it? \u2192 Yes, merge it\n2. A word for the cat? \u2192 Well done, thou good cat");
		const got = await waiting;
		assert.match(got.notes.at(-1).text, /^Homework handed in: The menu fix[\s\S]*\(for session_01Queen, told\)$/);
		assert.match((await tool(her, "answer", { quiz: id, answers: ["a", "b"] })).refused, /already/);
	});

	test("deals litter box notes and decisions into the quest log, once each, and keeps her answers for filing", async () => {
		const card = { kind: "litterbox", ref: "abc123def456", title: "loose-ends.md", note: "Rename her Mochi", from: "litterbox/loose-ends.md", hint: "pretty-project-portfolio",
			questions: [{ q: "Which project is it for?", options: ["pretty-project-portfolio", "kittychat", "Settled: drop it"] }] };
		assert.match((await tool(TOKEN, "quiz", card)).refused, /only the queen or the owner/);
		assert.match((await tool(her, "quiz", { ...card, questions: [{ q: "Which?", free: true }] })).refused, /one question with 2 to 12 options/);   // a card the café couldn't answer
		const open = await tool(QUEEN, "quiz", { for: "session_01Queen", title: "Still waiting", questions: [{ q: "Merge it?", options: ["Yes", "No"] }] });
		const { id } = await tool(her, "quiz", card);
		assert.equal(id, "litterbox-abc123def456");
		const at = (await tool(her, "quizzes", { kind: "litterbox" })).quizzes[0].at;
		await sleep(5);
		assert.deepEqual(await tool(her, "quiz", { ...card, note: "Rename her Mochi, dealt again" }), { id });   // open: replaced, not doubled
		assert.equal((await tool(her, "quizzes", { kind: "litterbox" })).quizzes[0].at, at, "a card dealt again moved in the deck");
		assert.match((await tool(her, "quiz", { ...card, kind: "decisions" })).refused, /kind is unblock, litterbox or decision/);
		await tool(her, "quiz", { kind: "decision", ref: "camera", title: "Which comes first?", hint: "The camera", questions: [{ q: "Which first?", options: ["The camera", "The gateway"] }] });
		const lb = (await tool(her, "quizzes", { kind: "litterbox" })).quizzes;
		assert.deepEqual(lb.map((z) => [z.id, z.kind, z.note, z.from, z.hint]), [[id, "litterbox", "Rename her Mochi, dealt again", "litterbox/loose-ends.md", "pretty-project-portfolio"]]);
		assert.equal((await tool(her, "quizzes", { kind: "decision" })).quizzes[0].id, "decision-camera");
		const before = (await tool(her, "comments", { cat: "queen" })).notes.length;
		assert.deepEqual(await tool(her, "answer", { quiz: id, answers: ["kittychat"] }), { ok: true, told: false });
		assert.equal((await tool(her, "comments", { cat: "queen" })).notes.length, before);   // a card isn't news for the queen
		assert.deepEqual(await tool(her, "quiz", card), { id, done: true });   // dealt again after she answered: her answer stands
		assert.deepEqual((await tool(her, "quizzes", { kind: "litterbox", done: true })).quizzes.map((z) => z.answers), [["kittychat"]]);
		assert.match((await tool(TOKEN, "forget", { quizzes: [id] })).refused, /only the queen or the owner/);
		assert.deepEqual(await tool(her, "forget", { quizzes: [id, "decision-camera", "nothing", open.id] }), { forgotten: 2 });
		assert.ok((await tool(her, "quizzes")).quizzes.some((z) => z.id === open.id), "an open unblock quiz was forgotten");
		assert.deepEqual((await tool(her, "quizzes", { done: true })).quizzes.filter((z) => z.kind !== "unblock" && z.kind), []);
	});

	test("counts her homework in the runner's wait, so her runner can say it on Charlotte's own desktop", async () => {
		// a word to her brings the wait back at once, instead of its full 25 seconds
		const now = async () => { await tool(her, "comment", { cat: "queen", text: "." }); return (await wait()).homework; };
		const before = await now();
		assert.equal(typeof before, "object", "the counts come with every wait, however few");
		await tool(her, "quiz", { kind: "litterbox", ref: "where-does-this-go", title: "Where does this go?", note: "One note to sort",
			questions: [{ q: "Which project?", options: ["kittychat", "Settled: drop it"] }] });
		const after = await now();
		assert.equal(after.litterbox || 0, (before.litterbox || 0) + 1, "one more note to sort");
		assert.ok(Object.values(after).every((n) => Number.isInteger(n) && n > 0), "counts by kind, and nothing else");
	});

	test("brings a design tokens file into her look and gives it back, for a session with the Figma connector", async () => {
		const FIX = join(HERE, "../test/fixtures/");
		const figma = JSON.parse(readFileSync(FIX + "tokens-figma.json", "utf8")), want = JSON.parse(readFileSync(FIX + "tokens-figma.expected.json", "utf8"));
		const sorted = (o) => Object.fromEntries(Object.entries(o).sort());
		const page = readFileSync(join(HERE, "../../catio/index.html"), "utf8");
		const count = (page.slice(page.indexOf("const TOKENS = {"), page.indexOf("};", page.indexOf("const TOKENS = {"))).match(/"--[\w-]+": \[/g) || []).length;
		const hexOf = (f, g, n) => f[g][n].$value.hex;
		// anyone in the house may read it: every token of The look, in its groups, at the café's own values
		const first = await tool(TOKEN, "tokens");
		assert.equal(first.mode, "light");
		assert.equal(Object.values(first.file).filter((g) => g && typeof g === "object").reduce((n, g) => n + Object.keys(g).filter((k) => !k.startsWith("$")).length, 0), count);
		const ink = (/--ink:\s*(#[0-9A-Fa-f]{6})/.exec(page) || [])[1];
		assert.equal(hexOf(first.file, "colours", "ink"), ink.toLowerCase());
		// only she and the queen change her look: a leaked agents' key can't restyle the café
		assert.match((await tool(TOKEN, "set_tokens", { file: figma })).refused, /only the owner or the queen/);
		// her Figma file: what the page, skin.py and catio_mcp.py find in it, and kept as The look keeps it
		const r = await tool(her, "set_tokens", { file: figma });
		assert.deepEqual([r.mode, r.tokens, r.foreign, r.refused], ["light", Object.keys(want.found).length, want.foreign, want.refused]);
		const theme = (await (await api("/api/db")).json()).docs["skin/theme"];
		assert.deepEqual(sorted(theme.tokens), sorted(want.found));
		assert.equal(hexOf((await tool(TOKEN, "tokens")).file, "colours", "ink"), "#1d3557");
		// the queen sets the night: dark says only what differs, and light stays
		assert.equal((await tool(QUEEN, "set_tokens", { mode: "dark", file: JSON.stringify({ colours: { ink: { $value: "#eeeeee" } } }) })).changed, 1);
		assert.equal((await tool(QUEEN, "set_tokens", { mode: "dark", file: { colours: { grass: { $value: "#5A8F29" } } } })).changed, 0);   // as in light: not kept
		assert.deepEqual((await (await api("/api/db")).json()).docs["skin/theme"].dark, { "--ink": "#eeeeee" });
		assert.equal(hexOf((await tool(TOKEN, "tokens", { mode: "dark" })).file, "colours", "ink"), "#eeeeee");
		assert.equal(hexOf((await tool(TOKEN, "tokens", { mode: "dark" })).file, "colours", "grass"), "#5a8f29");
		// replace: the file is the whole of light
		await tool(her, "set_tokens", { replace: true, file: { colours: { grass: { $value: "#5A8F29" } } } });
		assert.deepEqual((await (await api("/api/db")).json()).docs["skin/theme"].tokens, { "--grass": "#5A8F29" });
		assert.match((await tool(her, "set_tokens", { file: { brand: { red: { $value: "#ff0000" } } } })).refused, /none of the café's tokens \(1 of its own\)/);
		assert.match((await tool(her, "set_tokens", { mode: "dusk", file: figma })).refused, /mode is light or dark/);
		// back as it was: nothing of hers left in either mode, no theme kept
		await tool(her, "set_tokens", { replace: true, file: { colours: { ink: { $value: ink } } } });
		await tool(her, "set_tokens", { mode: "dark", replace: true, file: { colours: { ink: { $value: ink } } } });
		assert.equal((await (await api("/api/db")).json()).docs["skin/theme"], undefined);
	});

	test("runs a routine once when it comes due", async () => {
		const parts = Object.fromEntries(new Intl.DateTimeFormat("en-US", { timeZone: "Europe/Paris", hourCycle: "h23", hour: "numeric", minute: "numeric" })
			.formatToParts(new Date()).map((p) => [p.type, p.value]));
		const time = `${String(+parts.hour % 24).padStart(2, "0")}:${parts.minute.padStart(2, "0")}`;
		assert.equal((await put("routines/off", { name: "Off", time, days: [0, 1, 2, 3, 4, 5, 6], tz: "Europe/Paris", prompt: "Never", on: false, last: 0 })).status, 200);
		assert.equal((await put("routines/round", { name: "Morning round", time, days: [0, 1, 2, 3, 4, 5, 6], tz: "Europe/Paris", prompt: "Who needs me?", on: true, last: 0 })).status, 200);
		const got = await wait();
		assert.deepEqual([got.routine.id, got.routine.name, got.routine.prompt], ["round", "Morning round", "Who needs me?"]);
		assert.ok(got.routine.at <= Date.now() && got.routine.at > Date.now() - 2 * 60 * 1000, "fired at this minute");
		const { docs } = await (await api("/api/db")).json();
		assert.equal(docs["routines/round"].last, got.routine.at, "the café sees when it last ran");
		// once: the next wait has no routine, and comes back only when she speaks
		const again = wait();
		await sleep(300);
		await tool(her, "comment", { cat: "queen", text: "Thank you." });
		assert.equal((await again).routine, null);
		// what the queen says for a routine is kept with it
		await say({ turn: "t2", text: "All quiet, my lady.", done: true, routine: { id: "round", name: "Morning round" } });
		const last = (await tool(her, "comments", { cat: "queen" })).notes.at(-1);
		assert.deepEqual([last.author, last.text, last.routine], ["queen", "All quiet, my lady.", { id: "round", name: "Morning round" }]);
	});

	test("her key is the CATIO_QUEEN secret, and a café can mint another with the role queen", async () => {
		const keys = (await (await api("/api/keys")).json()).keys;
		assert.deepEqual(keys.find((k) => k.name === "queen").role, "queen");
		assert.equal(keys.find((k) => k.name === "bootstrap").role, "agent");
		const minted = await (await api("/api/keys", { method: "POST", body: JSON.stringify({ name: "pc", role: "queen" }) })).json();
		assert.equal(minted.role, "queen");
		assert.equal((await fetch(base + "/api/runner/say", { method: "POST", headers: { Authorization: "Bearer " + minted.key, "Content-Type": "application/json" }, body: JSON.stringify({ turn: "t0", text: "", done: true }) })).status, 200);
		assert.equal((await api("/api/keys", { method: "POST", body: JSON.stringify({ name: "odd", role: "king" }) })).status, 400);
		assert.equal((await api("/api/keys/pc", { method: "DELETE" })).status, 200);
		assert.equal((await fetch(base + "/api/runner/say", { method: "POST", headers: { Authorization: "Bearer " + minted.key }, body: "{}" })).status, 401, "a dropped key is dead");
	});
});

describe("the gateway", () => {
	test("tells strangers to sign in, and how", async () => {
		const r = await fetch(base + "/mcp", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
		assert.equal(r.status, 401);
		assert.match(r.headers.get("www-authenticate"), /resource_metadata="[^"]+\/\.well-known\/oauth-protected-resource\/mcp"/);
		const meta = await (await fetch(base + "/.well-known/oauth-protected-resource/mcp")).json();
		assert.equal(meta.resource, base + "/mcp");
		const as = await (await fetch(base + "/.well-known/oauth-authorization-server")).json();
		assert.equal(as.registration_endpoint, base + "/register");
		assert.deepEqual(as.code_challenge_methods_supported, ["S256"]);
		const wrong = await fetch(base + "/mcp", { method: "POST", headers: { Authorization: "Bearer not-the-key-at-all-sorry" }, body: "{}" });
		assert.equal(wrong.status, 401);
	});

	test("speaks MCP to an agent holding the key", async () => {
		const init = await rpc(TOKEN, "initialize", { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "t", version: "1" } });
		assert.equal(init.result.serverInfo.name, "catio");
		const { result } = await rpc(TOKEN, "tools/list", {});
		assert.deepEqual(result.tools.map((t) => t.name),
			["house_rules", "report_status", "list_agents", "inbox", "pick_up", "drop_file", "comment", "comments", "manage", "quiz", "quizzes", "forget", "decide", "tokens", "set_tokens", "answer"]);
		const rules = await tool(TOKEN, "house_rules");
		assert.ok(rules.rules.some((r) => r.id === "ship"));
		assert.equal((await tool(TOKEN, "nope")).rpcError.code, -32602);
		assert.equal((await rpc(TOKEN, "resources/list", {})).error.code, -32601);
		// a notification gets no answer, a GET no stream, broken JSON a parse error
		const note = await fetch(base + "/mcp", { method: "POST", headers: { Authorization: "Bearer " + TOKEN, "Content-Type": "application/json" },
			body: JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" }) });
		assert.equal(note.status, 202);
		assert.equal((await fetch(base + "/mcp", { headers: { Authorization: "Bearer " + TOKEN } })).status, 405);
		const bad = await fetch(base + "/mcp", { method: "POST", headers: { Authorization: "Bearer " + TOKEN }, body: "{nope" });
		assert.equal(bad.status, 400);
	});

	test("answers a list of calls in order", async () => {
		const r = await fetch(base + "/mcp", {
			method: "POST", headers: { "Content-Type": "application/json", Authorization: "Bearer " + TOKEN },
			body: JSON.stringify([
				{ jsonrpc: "2.0", id: "a", method: "tools/call", params: { name: "report_status", arguments: { agent: "batch-cat", mood: "busy" } } },
				{ jsonrpc: "2.0", id: "b", method: "tools/call", params: { name: "inbox", arguments: { agent: "batch-cat", mark: true } } },
			]),
		});
		const [a, b] = await r.json();
		assert.equal(a.id, "a");
		assert.equal(b.id, "b");
		assert.deepEqual(b.result.structuredContent, { files: [], notes: [], request: null });
	});

	test("lets only Claude's connectors register", async () => {
		assert.equal((await register([CALLBACK])).status, 201);
		const evil = await register(["https://evil.example/callback"]);
		assert.equal(evil.status, 400);
		assert.equal((await evil.json()).error, "invalid_redirect_uri");
		assert.equal((await register([CALLBACK, "http://localhost:4000/cb"])).status, 400);
	});

	test("signs Charlotte in with her handle and password, never with a wrong one", async () => {
		const { client_id } = await (await register([CALLBACK])).json();
		const page = await openSignIn(client_id);
		assert.equal(page.status, 200);
		assert.ok(page.handle);
		assert.match(page.html, /Let Claude into the Catio\?/);
		assert.match(page.html, /name="user"/);
		assert.match(page.html, /Access goes to <strong>claude\.ai<\/strong>/);
		assert.equal(page.headers.get("x-frame-options"), "DENY");
		assert.match(page.headers.get("content-security-policy"), /frame-ancestors 'none'/);

		const wrong = await submit(page, { password: "not-her-password-123", decision: "allow" });
		assert.equal(wrong.status, 401);
		assert.equal((await submit(page, { user: "someone-else", password: PASSWORD, decision: "allow" })).status, 401);
		assert.match(await wrong.text(), /aren&#39;t right/);
		const empty = await submit(page, { password: "", decision: "allow" });
		assert.equal(empty.status, 400);

		const right = await submit(page, { password: PASSWORD, decision: "allow" });
		assert.equal(right.status, 302);
		const back = new URL(right.headers.get("location"));
		assert.equal(back.origin + back.pathname, CALLBACK);
		assert.equal(back.searchParams.get("state"), "st-1");
		const code = back.searchParams.get("code");
		assert.ok(code);

		const t = await fetch(base + "/token", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
			body: form({ grant_type: "authorization_code", code, redirect_uri: CALLBACK, client_id, code_verifier: page.verifier, resource: base + "/mcp" }) });
		assert.equal(t.status, 200);
		const tokens = await t.json();
		assert.ok(tokens.access_token && tokens.refresh_token);
		assert.ok((await tool(tokens.access_token, "list_agents")).agents);

		// the handle works once
		assert.equal((await submit(page, { password: PASSWORD, decision: "allow" })).status, 400);

		// and the grant refreshes, as claude.ai does every hour
		const r = await fetch(base + "/token", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
			body: form({ grant_type: "refresh_token", refresh_token: tokens.refresh_token, client_id }) });
		assert.equal(r.status, 200);
		assert.ok((await tool((await r.json()).access_token, "list_agents")).agents);
	});

	test("sends Claude away empty-handed on Not now", async () => {
		const { client_id } = await (await register([CALLBACK])).json();
		const page = await openSignIn(client_id);
		const r = await submit(page, { decision: "deny" });
		assert.equal(r.status, 302);
		assert.equal(new URL(r.headers.get("location")).searchParams.get("error"), "access_denied");
	});

	test("keeps a cat's status, notes, requests and files, as catio_mcp.py does", async () => {
		const { access_token: her } = await signIn();
		const cat = "session_01Test";

		assert.equal((await tool(TOKEN, "report_status", {})).refused, "agent is required");
		assert.match((await tool(TOKEN, "report_status", { agent: cat, mood: "grumpy" })).refused, /mood must be one of/);
		const joined = await tool(TOKEN, "report_status", { agent: cat, mood: "busy", title: "Fix the tests", repo: "charredlatte/x",
			branch: "claude/x", via: "claude-code", session: cat, link: "https://claude.ai/code/" + cat, wake: ["rm", "-rf", "/"] });
		assert.equal(joined.ok, true);
		let me = (await tool(her, "list_agents")).agents.find((a) => a.id === cat);
		assert.equal(me.mood, "busy");
		assert.equal(me.branch, "claude/x");
		assert.equal(me.wakes, false);
		assert.equal(me.wake, undefined);

		// her notes: an agent can't speak as her, and the hook is handed each one once
		assert.equal((await tool(TOKEN, "comment", { cat, text: "do it", author: "owner" })).refused, "only the owner writes as the owner");
		assert.equal((await tool(TOKEN, "comment", { cat, text: "do it", author: "charlotte" })).refused, "only the owner writes as the owner", "the old name is the owner's too");
		assert.equal((await tool(TOKEN, "comment", { cat, text: "do it", author: "boss" })).refused, "author is owner, agent, session or queen");
		assert.ok((await tool(her, "comment", { cat, text: "First, the tests." })).id);
		assert.ok((await tool(her, "comment", { cat, text: "Then push.", author: "charlotte" })).id, "an older page still writes as charlotte");
		assert.equal((await tool(TOKEN, "inbox", { agent: cat })).notes.length, 2);
		const handed = await tool(TOKEN, "inbox", { agent: cat, mark: true });
		assert.deepEqual(handed.notes.map((n) => n.text), ["First, the tests.", "Then push."]);
		assert.equal((await tool(TOKEN, "inbox", { agent: cat, mark: true })).notes.length, 0);
		assert.ok((await tool(her, "comment", { cat, text: "And thanks." })).id);
		assert.equal((await tool(TOKEN, "inbox", { agent: cat, mark: true })).notes.length, 1);
		// an answer
		assert.ok((await tool(TOKEN, "comment", { cat, text: "Done.", author: "session" })).id);
		const talk = (await tool(her, "comments", { cat })).notes;
		assert.deepEqual(talk.map((n) => [n.author, n.text]), [["owner", "First, the tests."], ["owner", "Then push."],
			["owner", "And thanks."], ["session", "Done."]], "stored as owner, the old name included");
		assert.deepEqual((await tool(her, "comments", { cat, limit: 1 })).notes.map((n) => n.text), ["Done."]);
		// what she writes while the session is answering still gets handed in
		assert.ok((await tool(her, "comment", { cat, text: "Wait, one more." })).id);
		assert.ok((await tool(TOKEN, "comment", { cat, text: "Pushed.", author: "session" })).id);
		assert.deepEqual((await tool(TOKEN, "inbox", { agent: cat, mark: true })).notes.map((n) => n.text), ["Wait, one more."]);
		assert.equal((await tool(TOKEN, "inbox", { agent: cat })).notes.length, 0);

		// requests: only she makes them, and each is handed over once
		assert.equal((await tool(TOKEN, "manage", { cat, action: "wrap_up" })).refused, "only the owner manages a cat");
		assert.equal((await tool(her, "manage", { cat: "nobody", action: "pause" })).refused, "no such agent");
		assert.match((await tool(her, "manage", { cat, action: "dance" })).refused, /^action is/);
		assert.equal((await tool(her, "manage", { cat, action: "wrap_up" })).ok, true);
		assert.equal((await tool(TOKEN, "inbox", { agent: cat, mark: true })).request.action, "wrap_up");
		assert.equal((await tool(TOKEN, "inbox", { agent: cat, mark: true })).request, null);
		assert.equal((await tool(TOKEN, "inbox", { agent: cat })).request.action, "wrap_up");
		assert.equal((await tool(her, "manage", { cat, action: "done" })).ok, true);
		assert.equal((await tool(TOKEN, "inbox", { agent: cat })).request, null);
		assert.equal((await tool(her, "manage", { cat, action: "message", value: "One more thing." })).ok, true);
		assert.equal((await tool(TOKEN, "inbox", { agent: cat, mark: true })).notes[0].text, "One more thing.");

		// files: hers only, small ones only, handed over once, picked up whole
		const bytes = randomBytes(3000).toString("base64");
		assert.equal((await tool(TOKEN, "drop_file", { name: "a.bin", base64: bytes, for: cat })).refused, "only the owner drops files on a cat");
		assert.equal((await tool(her, "drop_file", { name: "a.bin", base64: "!!!!", for: cat })).refused, "base64 isn't valid");
		const big = Buffer.alloc(1024 * 1024 + 1).toString("base64");
		assert.match((await tool(her, "drop_file", { name: "big.bin", base64: big, for: cat })).refused, /1 MiB/);
		const dropped = await tool(her, "drop_file", { name: "notes.txt", type: "text/plain", base64: bytes, for: cat, note: "read me" });
		me = (await tool(her, "list_agents")).agents.find((a) => a.id === cat);
		assert.equal(me.waiting, 1);
		const box = await tool(TOKEN, "inbox", { agent: cat, mark: true });
		assert.deepEqual(box.files.map((f) => [f.id, f.name, f.size, f.note]), [[dropped.id, "notes.txt", 3000, "read me"]]);
		assert.equal((await tool(TOKEN, "inbox", { agent: cat, mark: true })).files.length, 0);
		const got = await tool(TOKEN, "pick_up", { id: dropped.id, agent: cat });
		assert.equal(got.base64, bytes);
		assert.equal((await tool(her, "list_agents")).agents.find((a) => a.id === cat).waiting, 0);
		assert.equal((await tool(TOKEN, "pick_up", { id: "nope" })).refused, "no such file");

		// archived cats leave the list, unless asked for
		assert.equal((await tool(her, "manage", { cat, action: "archive" })).ok, true);
		assert.ok(!(await tool(her, "list_agents")).agents.some((a) => a.id === cat));
		assert.ok((await tool(her, "list_agents", { archived: true })).agents.some((a) => a.id === cat));
		assert.equal((await tool(her, "manage", { cat, action: "rename", value: "Biscuit" })).ok, true);
		assert.equal((await tool(her, "list_agents", { archived: true })).agents.find((a) => a.id === cat).name, "Biscuit");
	});

	test("answers a typed decision from the System One server, and logs it beside the old path's choice", async () => {
		const { access_token: her } = await signIn();
		// anyone in the house may ask; the questions and state reach the decider as sent, with its key
		const out = await tool(TOKEN, "decide", { state: { file: "notes.md", cats: ["shop", "catio"] }, kind: "sort", old: "catio",
			questions: { cat: { type: "choice", instructions: "Which cat?", criteria: { shop: "the shop", catio: "the café" } } } });
		assert.equal(out.model, "stand-in");
		assert.equal(out.answers.cat.choice, "shop");
		assert.equal(out.answers.cat.confidence, 0.8);
		const last = asked.at(-1);
		assert.equal(last.path, "/v1/systemone");
		assert.equal(last.auth, "Bearer k1");
		assert.deepEqual(last.body.state, { file: "notes.md", cats: ["shop", "catio"] });
		assert.equal(last.body.questions.cat.criteria.catio, "the café");
		// the easy-task rubric, as a preset: six yes/no questions about the task's text
		const easy = await tool(her, "decide", { state: "Add a test for parse_time in utils.py", preset: "easy" });
		assert.deepEqual(Object.keys(easy.answers).sort(), ["browser", "checkable", "held_path", "private", "small", "spelled_out"]);
		assert.equal(asked.at(-1).body.questions.held_path.type, "noul");
		// bad questions are refused before anything is asked
		const n = asked.length;
		assert.match((await tool(TOKEN, "decide", { state: "x", questions: { q: { type: "guess" } } })).refused, /noul, choice or score/);
		assert.match((await tool(TOKEN, "decide", { state: "", preset: "easy" })).refused, /state is empty/);
		assert.match((await tool(TOKEN, "decide", { state: "x", preset: "hard" })).refused, /preset is one of easy/);
		assert.equal(asked.length, n);
		// under the caller's floor the decider hasn't decided: it neither agrees nor disagrees, and ref names the file
		await tool(TOKEN, "decide", { state: { file: "notes.md" }, kind: "sort", old: "shop", floor: 0.9, ref: "b-1",
			questions: { cat: { type: "choice", criteria: { shop: "the shop", catio: "the café" } } } });
		// the log: only the call with a kind, with old and whether the two agreed; the café's database shows it
		const docs = (await (await fetch(base + "/api/db", { headers: { Cookie: herCookie } })).json()).docs;
		const log = Object.entries(docs).filter(([p]) => p.startsWith("decisions/"));
		assert.equal(log.length, 2);
		log.sort((x, y) => x[1].at - y[1].at);
		assert.equal(log[0][1].kind, "sort");
		assert.equal(log[0][1].old, "catio");
		assert.equal(log[0][1].agree, false);
		assert.equal(log[0][1].sure, true);
		assert.equal(log[0][1].answers.cat.choice, "shop");
		assert.equal(log[1][1].verdict, "shop");
		assert.equal(log[1][1].sure, false);
		assert.equal(log[1][1].agree, null);
		assert.equal(log[1][1].ref, "b-1");
	});

	test("takes a session's reports from its hook, and hands her messages in at its Stop", async () => {
		const { access_token: her } = await signIn();
		const cat = "session_01Hook";
		const env = { ...process.env, CATIO_URL: base, CATIO_TOKEN: TOKEN, CLAUDE_CODE_REMOTE_SESSION_ID: cat, NO_PROXY: "127.0.0.1", no_proxy: "127.0.0.1" };
		const hook = (data) => execFileSync("python3", [REPORT], { input: JSON.stringify({ cwd: HERE, ...data }), env, encoding: "utf8" });

		assert.equal(hook({ hook_event_name: "SessionStart", source: "startup", model: "claude-opus-5-5" }), "");
		let me = (await tool(her, "list_agents")).agents.find((a) => a.id === cat);
		assert.equal(me.mood, "busy");
		assert.equal(me.repo.split("/").pop(), "Pretty-Project-Portfolio");
		assert.equal(me.link, "https://claude.ai/code/" + cat);

		assert.equal(hook({ hook_event_name: "Stop", stop_hook_active: false }), "");
		assert.equal((await tool(her, "list_agents")).agents.find((a) => a.id === cat).mood, "review");

		await tool(her, "comment", { cat, text: "Add a test for the hook." });
		const held = JSON.parse(hook({ hook_event_name: "Stop", stop_hook_active: false }));
		assert.equal(held.decision, "block");
		assert.match(held.reason, /\[Catio\] Charlotte says: Add a test for the hook\./);
		assert.equal((await tool(her, "list_agents")).agents.find((a) => a.id === cat).mood, "busy");
		assert.equal(hook({ hook_event_name: "Stop", stop_hook_active: false }), "");   // handed in once

		execFileSync("python3", [REPORT, "say", "Added."], { env });
		assert.deepEqual((await tool(her, "comments", { cat })).notes.map((n) => [n.author, n.text]),
			[["owner", "Add a test for the hook."], ["session", "Added."]]);
	});

	test("waits after five wrong passwords, even for the right one", async () => {
		const { client_id } = await (await register([CALLBACK])).json();
		const page = await openSignIn(client_id);
		for (let i = 0; i < 5; i++) assert.equal((await submit(page, { password: "wrong-password-" + i, decision: "allow" })).status, 401);
		const locked = await submit(page, { password: PASSWORD, decision: "allow" });
		assert.equal(locked.status, 429);
		assert.match(await locked.text(), /Too many wrong passwords/);
	});
});

// Last, because every suite above holds the bootstrap key: once she drops it, it is dead. Her café cookie was
// taken in the accounts suite, before the gateway suite locked her handle; a lock keeps nobody already in out.
describe("the bootstrap key", () => {
	test("can be dropped like any other, and stays dropped", async () => {
		assert.ok(herCookie, "her café cookie from the accounts suite");
		const api = (path, init = {}) => fetch(base + path, { ...init, headers: { Cookie: herCookie, "X-Catio": "1", ...(init.headers || {}) } });
		const names = async () => (await (await api("/api/keys")).json()).keys.map((k) => k.name);
		assert.deepEqual(await names(), ["bootstrap", "queen"]);
		assert.equal((await api("/api/keys/bootstrap", { method: "DELETE" })).status, 200);
		const mcp = () => fetch(base + "/mcp", { method: "POST", headers: { Authorization: "Bearer " + TOKEN }, body: "{}" });
		assert.equal((await mcp()).status, 401);
		// a new isolate (here: wrangler again on the same state) finds the registry full: nothing is bootstrapped
		// again, so the key does not come back, and nothing says "no account yet". The queen's key is the secret
		// itself, so it is still there.
		stop();
		await new Promise((r) => setTimeout(r, 500));
		// a house from before the rename holds the owner's notes as "charlotte": put one back into the persisted
		// SQLite (and forget that the house renamed), as a real house would have on the first deploy
		const dbs = [];
		const walk = (d) => { for (const f of readdirSync(d)) { const p = join(d, f); if (statSync(p).isDirectory()) walk(p); else if (f.endsWith(".sqlite")) dbs.push(p); } };
		walk(state);
		const flipped = execFileSync("python3", ["-c", `
import sqlite3, sys
n = 0
for p in sys.argv[1:]:
    c = sqlite3.connect(p)
    try:
        if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notes'").fetchone():
            n += c.execute("UPDATE notes SET author = 'charlotte' WHERE cat = 'session_01Test' AND author = 'owner'").rowcount
            c.execute("DELETE FROM state WHERE key = 'notesOwner'")
            c.commit()
    finally:
        c.close()
print(n)`, ...dbs], { encoding: "utf8" }).trim();
		assert.ok(+flipped >= 3, "old-name rows planted: " + flipped);
		await start();
		assert.equal((await fetch(base + "/")).status, 200);
		assert.equal((await mcp()).status, 401);
		assert.deepEqual(await names(), ["queen"]);
		const talk = await (await api("/api/tools/comments", { method: "POST", body: JSON.stringify({ cat: "session_01Test" }) })).json();
		assert.ok(talk.notes.length >= 3 && talk.notes.every((n) => n.author !== "charlotte"), "the house renamed its old notes on waking: " + JSON.stringify(talk.notes.map((n) => n.author)));
		assert.equal((await fetch(base + "/api/runner/say", { method: "POST", headers: { Authorization: "Bearer " + QUEEN, "Content-Type": "application/json" }, body: JSON.stringify({ turn: "t9", text: "", done: true }) })).status, 200);
		const asHer = await fetch(base + "/login", { method: "POST", body: new URLSearchParams({ user: "charlotte", password: PASSWORD }), redirect: "manual" });
		assert.equal(asHer.status, 429, "the lock from the gateway suite is in the registry, not in the isolate");
	});
});

// A fresh gateway with no account says which of the two is wrong with CATIO_PASSWORD: missing, or too short.
describe("no account yet", () => {
	test("says whether CATIO_PASSWORD is missing or too short", async () => {
		for (const [password, says, not] of [["", /CATIO_PASSWORD isn(?:'|&#39;)t set for this Worker/, /under 16/], ["too-short", /CATIO_PASSWORD is under 16 characters/, /t set for this Worker/]]) {
			stop();
			await new Promise((r) => setTimeout(r, 500));
			const dir = mkdtempSync(join(tmpdir(), "catio-gateway-empty-"));
			try {
				await start({ password, dir });
				const page = await fetch(base + "/");
				assert.equal(page.status, 503);
				const text = await page.text();
				assert.match(text, says);
				assert.doesNotMatch(text, not);
			} finally {
				rmSync(dir, { recursive: true, force: true });
			}
		}
	});

	// The first outside run (docs/plan.md, "The first player"): his page said "no account yet" and he couldn't tell
	// which secret was wrong. The page now lights each one the Worker sees, never its value, and says the handle.
	test("lights each secret the Worker sees, and says what the handle will be", async () => {
		for (const [vars, says] of [[[], [/CATIO_PASSWORD isn(?:'|&#39;)t set for this Worker/, /CATIO_HANDLE isn(?:'|&#39;)t set, so your handle will be charlotte/,
			/CATIO_TOKEN is set\./, /CATIO_QUEEN is set\./, /This is what the Worker at 127\.0\.0\.1:\d+ sees/]],
		[["CATIO_HANDLE:Dog_Den"], [/CATIO_HANDLE isn(?:'|&#39;)t a handle/]]]) {
			stop();
			await new Promise((r) => setTimeout(r, 500));
			const dir = mkdtempSync(join(tmpdir(), "catio-gateway-empty-"));
			try {
				await start({ password: "", dir, vars });
				for (const path of ["/", "/signup"]) {
					const page = await fetch(base + path, path === "/signup" ? { method: "POST", headers: { Origin: base }, body: new URLSearchParams({ invite: "x" }) } : {});
					assert.equal(page.status, 503, path);
					const text = await page.text();
					for (const re of says) assert.match(text, re, path);
					assert.doesNotMatch(text, /her-password-|agent-key-|queen-key-/, "a light never shows a secret's value");
				}
			} finally {
				rmSync(dir, { recursive: true, force: true });
			}
		}
	});
});
