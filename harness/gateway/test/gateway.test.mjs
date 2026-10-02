// The gateway end to end, in workerd: `wrangler dev` with a fresh state, then claude.ai's sign-in as claude.ai
// does it (register, authorize with her password, token, refresh), the tools as the page and an agent call
// them, and the sign-in lock.
//
//     npm test        (from harness/gateway, after npm install)
import assert from "node:assert/strict";
import { execFileSync, spawn } from "node:child_process";
import { createHash, randomBytes } from "node:crypto";
import { mkdtempSync, rmSync } from "node:fs";
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

let base, wrangler, state, log = "";

before(async () => {
	const [port, inspector] = [await freePort(), await freePort()];
	base = `http://127.0.0.1:${port}`;
	state = mkdtempSync(join(tmpdir(), "catio-gateway-"));
	wrangler = spawn(process.execPath, [join(HERE, "node_modules/wrangler/bin/wrangler.js"), "dev", "--ip", "127.0.0.1",
		"--port", String(port), "--inspector-port", String(inspector), "--persist-to", state,
		"--var", "CATIO_TOKEN:" + TOKEN, "--var", "CATIO_PASSWORD:" + PASSWORD, "--var", "CATIO_QUEEN:" + QUEEN], {
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
});

after(() => {
	try { process.kill(-wrangler.pid, "SIGTERM"); } catch { /* already gone */ }
	rmSync(state, { recursive: true, force: true });
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
		body: form({ handle: page.handle, client: "Claude", host: "claude.ai", ...fields }),
	});
}

// the whole sign-in, as claude.ai and her browser do it: an access token that acts as Charlotte
async function signIn() {
	const { client_id } = await (await register([CALLBACK])).json();
	const page = await openSignIn(client_id);
	const r = await submit(page, { password: PASSWORD, decision: "allow" });
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
		assert.match(first, /Your Catio password/);
		assert.doesNotMatch(first, /id="houseBtn"/);
		for (const p of ["/api/db", "/art/licensed/pochi.png", "/files/x", "/ws"]) assert.equal((await fetch(base + p)).status, 401, p);
		const wrong = await fetch(base + "/login", { method: "POST", body: new URLSearchParams({ password: "not-the-password-sorry" }), redirect: "manual" });
		assert.equal(wrong.status, 401);
		const right = await fetch(base + "/login", { method: "POST", body: new URLSearchParams({ password: PASSWORD }), redirect: "manual" });
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
		assert.deepEqual([notes.at(-1).author, notes.at(-1).text], ["charlotte", "From the café"]);
		assert.equal((await api("/api/tools/no_such_tool", { method: "POST", body: "{}" })).status, 404);
		assert.equal((await api("/api/tools/manage", { method: "POST", body: JSON.stringify({ cat: "nobody", action: "archive" }) })).status, 400);
		assert.match(await (await fetch(base + "/runtime.js")).text(), /catioGateway: true/);
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
		const r = await fetch(base + "/login", { method: "POST", body: new URLSearchParams({ password: PASSWORD }), redirect: "manual" });
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
		assert.deepEqual(got.notes.map((n) => [n.author, n.text]), [["charlotte", "Who needs me today?"]]);
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
			[["charlotte", "Who needs me today?"], ["charlotte", "And the shop?"], ["queen", "Good morrow, my lady. Two cats need thee."]]);
		assert.equal((await say({ turn: "t1", text: "", done: true })).status, 200, "an empty turn stores nothing");
		assert.equal((await tool(her, "comments", { cat: "queen" })).notes.length, 3);
		assert.equal((await runner("/api/runner/say", { text: "x".repeat(70000), done: true })).status, 413);
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
		assert.equal((await tool(QUEEN, "comment", { cat, text: "x", author: "charlotte" })).refused, "only Charlotte writes as Charlotte");
		assert.equal((await tool(TOKEN, "comment", { cat, text: "x", author: "queen" })).refused, "only the queen's runner writes as the queen");
		assert.equal((await tool(TOKEN, "manage", { cat, action: "wrap_up" })).refused, "only Charlotte manages a cat");
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
			["house_rules", "report_status", "list_agents", "inbox", "pick_up", "drop_file", "comment", "comments", "manage"]);
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

	test("signs Charlotte in with her password, never with a wrong one", async () => {
		const { client_id } = await (await register([CALLBACK])).json();
		const page = await openSignIn(client_id);
		assert.equal(page.status, 200);
		assert.ok(page.handle);
		assert.match(page.html, /Let Claude into the Catio\?/);
		assert.match(page.html, /Access goes to <strong>claude\.ai<\/strong>/);
		assert.equal(page.headers.get("x-frame-options"), "DENY");
		assert.match(page.headers.get("content-security-policy"), /frame-ancestors 'none'/);

		const wrong = await submit(page, { password: "not-her-password-123", decision: "allow" });
		assert.equal(wrong.status, 401);
		assert.match(await wrong.text(), /isn&#39;t right/);
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
		assert.equal((await tool(TOKEN, "comment", { cat, text: "do it", author: "charlotte" })).refused, "only Charlotte writes as Charlotte");
		assert.ok((await tool(her, "comment", { cat, text: "First, the tests." })).id);
		assert.ok((await tool(her, "comment", { cat, text: "Then push." })).id);
		assert.equal((await tool(TOKEN, "inbox", { agent: cat })).notes.length, 2);
		const handed = await tool(TOKEN, "inbox", { agent: cat, mark: true });
		assert.deepEqual(handed.notes.map((n) => n.text), ["First, the tests.", "Then push."]);
		assert.equal((await tool(TOKEN, "inbox", { agent: cat, mark: true })).notes.length, 0);
		assert.ok((await tool(her, "comment", { cat, text: "And thanks." })).id);
		assert.equal((await tool(TOKEN, "inbox", { agent: cat, mark: true })).notes.length, 1);
		// an answer
		assert.ok((await tool(TOKEN, "comment", { cat, text: "Done.", author: "session" })).id);
		const talk = (await tool(her, "comments", { cat })).notes;
		assert.deepEqual(talk.map((n) => [n.author, n.text]), [["charlotte", "First, the tests."], ["charlotte", "Then push."],
			["charlotte", "And thanks."], ["session", "Done."]]);
		assert.deepEqual((await tool(her, "comments", { cat, limit: 1 })).notes.map((n) => n.text), ["Done."]);
		// what she writes while the session is answering still gets handed in
		assert.ok((await tool(her, "comment", { cat, text: "Wait, one more." })).id);
		assert.ok((await tool(TOKEN, "comment", { cat, text: "Pushed.", author: "session" })).id);
		assert.deepEqual((await tool(TOKEN, "inbox", { agent: cat, mark: true })).notes.map((n) => n.text), ["Wait, one more."]);
		assert.equal((await tool(TOKEN, "inbox", { agent: cat })).notes.length, 0);

		// requests: only she makes them, and each is handed over once
		assert.equal((await tool(TOKEN, "manage", { cat, action: "wrap_up" })).refused, "only Charlotte manages a cat");
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
		assert.equal((await tool(TOKEN, "drop_file", { name: "a.bin", base64: bytes, for: cat })).refused, "only Charlotte drops files on a cat");
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
			[["charlotte", "Add a test for the hook."], ["session", "Added."]]);
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
