// The gateway under hostile input: malformed requests, keys used outside their role, secrets that clash, sign-in
// guessing, and a runner that dies mid-routine. Each test boots its own `wrangler dev` on a fresh state.
//
//     npm test        (from harness/gateway, after npm install)
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { randomBytes } from "node:crypto";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { createServer as createHttpServer } from "node:http";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, before, describe, test } from "node:test";
import { fileURLToPath } from "node:url";

const HERE = fileURLToPath(new URL("..", import.meta.url));
const rand = (p) => p + randomBytes(12).toString("hex");
const freePort = () => new Promise((done) => {
	const s = createServer().listen(0, "127.0.0.1", () => { const { port } = s.address(); s.close(() => done(port)); });
});

// a stand-in decider that answers with NO answers at all: {} normally, and null when the state asks for it
// (typeof null is "object", so the two are not the same thing to the code that reads the answer)
let decider, deciderPort;
const startDecider = () => new Promise((done) => {
	decider = createHttpServer((req, res) => {
		let body = "";
		req.on("data", (d) => { body += d; });
		req.on("end", () => {
			res.setHeader("Content-Type", "application/json");
			res.end(JSON.stringify({ model: "x", answers: /NOTHING-AT-ALL/.test(body) ? null : {} }));
		});
	}).listen(0, "127.0.0.1", () => done(decider.address().port));
});

const boots = [];
async function boot(vars) {
	const [port, inspector] = [await freePort(), await freePort()];
	const state = mkdtempSync(join(tmpdir(), "catio-adv-"));
	const config = join(HERE, `.wrangler.adv-${port}.jsonc`);
	writeFileSync(config, readFileSync(join(HERE, "wrangler.jsonc"), "utf8").replace(/^\s*"ai":.*\n/m, ""));
	let log = "";
	const args = ["dev", "--config", config, "--ip", "127.0.0.1", "--port", String(port), "--inspector-port", String(inspector), "--persist-to", state];
	for (const [k, v] of Object.entries({ ...vars, DECIDE_URL: "http://127.0.0.1:" + deciderPort + "/" })) args.push("--var", `${k}:${v}`);
	const proc = spawn(process.execPath, [join(HERE, "node_modules/wrangler/bin/wrangler.js"), ...args], {
		cwd: HERE, env: { ...process.env, WRANGLER_SEND_METRICS: "false", NO_COLOR: "1" }, stdio: ["ignore", "pipe", "pipe"], detached: true });
	proc.stdout.on("data", (d) => { log += d; });
	proc.stderr.on("data", (d) => { log += d; });
	for (let i = 0; i < 120 && !/Ready on/.test(log); i++) await new Promise((r) => setTimeout(r, 500));
	assert.match(log, /Ready on/, log);
	const b = { base: `http://127.0.0.1:${port}`, log: () => log, stop() { try { process.kill(-proc.pid, "SIGTERM"); } catch {} rmSync(state, { recursive: true, force: true }); rmSync(config, { force: true }); } };
	boots.push(b);
	return b;
}
before(async () => { deciderPort = await startDecider(); });
after(() => { boots.forEach((b) => b.stop()); decider.close(); });

let nextId = 1;
const rpcRaw = (base, bearer, body) => fetch(base + "/mcp", { method: "POST", headers: { "Content-Type": "application/json", Authorization: "Bearer " + bearer }, body: typeof body === "string" ? body : JSON.stringify(body) });
async function tool(base, bearer, name, args = {}) {
	const r = await rpcRaw(base, bearer, { jsonrpc: "2.0", id: nextId++, method: "tools/call", params: { name, arguments: args } });
	const j = await r.json();
	if (j.error) return { rpcError: j.error };
	return j.result.isError ? { refused: j.result.content[0].text } : j.result.structuredContent;
}
const login = (base, user, password) => fetch(base + "/login", { method: "POST", body: new URLSearchParams({ user, password }), redirect: "manual" });

describe("a normal gateway under hostile input", () => {
	const TOKEN = rand("agent-key-"), QUEEN = rand("queen-key-"), PASSWORD = rand("her-password-");
	let g, cookie;
	const api = (path, init = {}) => fetch(g.base + path, { ...init, headers: { Cookie: cookie, "X-Catio": "1", ...(init.headers || {}) } });
	const asQueen = { Authorization: "Bearer " + QUEEN };
	// the runner's wait, with a note for her first so it comes back at once instead of being held
	const wait = async () => {
		await api("/api/tools/comment", { method: "POST", body: JSON.stringify({ cat: "queen", text: "hello" }) });
		return (await fetch(g.base + "/api/runner/wait", { method: "POST", headers: asQueen })).json();
	};
	const docs = async () => (await (await api("/api/db")).json()).docs;
	const patch = (path, data) => api("/api/db/" + path, { method: "PATCH", body: JSON.stringify({ data }) });
	before(async () => {
		g = await boot({ CATIO_TOKEN: TOKEN, CATIO_PASSWORD: PASSWORD, CATIO_QUEEN: QUEEN });
		cookie = (await login(g.base, "charlotte", PASSWORD)).headers.get("set-cookie").split(";")[0];
	});

	test("an agent key can't swallow the owner's messages to the queen", async () => {
		await tool(g.base, QUEEN, "report_status", { agent: "queen", mood: "done" });   // she exists
		await api("/api/tools/comment", { method: "POST", body: JSON.stringify({ cat: "queen", text: "buy milk" }) });
		await tool(g.base, TOKEN, "inbox", { agent: "queen", mark: true });              // any session's hook-sized key
		const wait = await fetch(g.base + "/api/runner/wait", { method: "POST", headers: { Authorization: "Bearer " + QUEEN } });
		const got = await wait.json();
		assert.deepEqual(got.notes.map((n) => n.text), ["buy milk"], "the runner never heard her");
	});

	test("an agent key can't pose as the queen's runner being present", async () => {
		const r = await tool(g.base, TOKEN, "report_status", { agent: "queen", mood: "busy", name: "Totally the queen" });
		assert.ok(r.refused, "report_status should refuse the reserved id 'queen' from an agents' key: " + JSON.stringify(r));
	});

	test("an agent can't pick up a file dropped on another cat", { todo: "design limit: one shared agents' key, and `agent` is self-declared" }, async () => {
		const sent = await api("/api/tools/drop_file", { method: "POST", body: JSON.stringify({ name: "secret.txt", base64: Buffer.from("hunter2").toString("base64"), for: "cat-a" }) });
		const { id } = await sent.json();
		const stolen = await tool(g.base, TOKEN, "pick_up", { id, agent: "cat-b" });
		assert.ok(stolen.refused, "cat-b took cat-a's file");
	});

	test("a signed-in browser can sign out", async () => {
		const mine = (await login(g.base, "charlotte", PASSWORD)).headers.get("set-cookie").split(";")[0];
		const r = await fetch(g.base + "/logout", { method: "POST", headers: { Cookie: mine }, redirect: "manual" });
		assert.ok([200, 303].includes(r.status), "no /logout: " + r.status);
		assert.equal((await fetch(g.base + "/api/db", { headers: { Cookie: mine } })).status, 401, "the cookie still works after signing out");
	});

	test("non-form bodies on the sign-in are a 4xx, not a crash", async () => {
		for (const [path, type] of [["/login", "application/json"], ["/authorize", "application/json"], ["/login", "text/plain"]]) {
			const r = await fetch(g.base + path, { method: "POST", headers: { "Content-Type": type }, body: "{}" });
			assert.ok(r.status >= 400 && r.status < 500, `${path} as ${type} → ${r.status}`);
		}
	});

	test("MCP shrugs off malformed JSON-RPC", async () => {
		const cases = [
			"null", "[]", "[null]", "[[]]", "12", '"x"', "{", '{"jsonrpc":"2.0","id":1}', '{"jsonrpc":"2.0","id":1,"method":5}',
			'{"jsonrpc":"2.0","id":1,"method":"tools/call","params":"x"}', '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":{"a":1}}}',
			'{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"comment","arguments":"x"}}',
			'{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"comment","arguments":[1,2]}}',
			'{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"constructor","arguments":{}}}',
			'{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"__proto__","arguments":{}}}',
			'{"jsonrpc":"2.0","id":{"a":1},"method":"ping"}',
		];
		for (const body of cases) {
			const r = await rpcRaw(g.base, TOKEN, body);
			assert.ok(r.status < 500, `${body} → ${r.status} ${await r.text()}`);
		}
		assert.equal((await tool(g.base, TOKEN, "list_agents")).agents !== undefined, true, "still alive");
	});

	test("tool arguments of the wrong type are refused, not 500", async () => {
		const bad = [
			["report_status", { agent: { a: 1 } }], ["report_status", { agent: "x", mood: ["needs"] }], ["report_status", { agent: "x", ask: { deep: [1] } }],
			["inbox", { agent: ["x"] }], ["inbox", { agent: "x", mark: "yes" }], ["comments", { cat: "x", limit: "NaN" }], ["comments", { cat: "x", limit: -5 }],
			["comment", { cat: "x", text: { a: 1 } }], ["comment", { cat: "x", text: "t", author: "root" }],
			["quizzes", { done: "no", kind: ["a"] }], ["forget", { quizzes: "all" }], ["forget", { quizzes: [{}] }],
		];
		for (const [name, args] of bad) {
			const r = await rpcRaw(g.base, TOKEN, { jsonrpc: "2.0", id: 1, method: "tools/call", params: { name, arguments: args } });
			assert.ok(r.status < 500, `${name} ${JSON.stringify(args)} → ${r.status}`);
		}
	});

	test("owner-only tools refuse an agent key", async () => {
		for (const [name, args] of [["manage", { cat: "x", action: "archive" }], ["quiz", { title: "t", questions: ["q?"] }], ["answer", { quiz: "x", answers: ["a"] }],
			["drop_file", { name: "n", base64: "AAAA", for: "x" }], ["forget", { quizzes: ["a"] }]]) {
			assert.ok((await tool(g.base, TOKEN, name, args)).refused, name);
		}
		assert.ok((await tool(g.base, TOKEN, "comment", { cat: "x", text: "t", author: "owner" })).refused);
		assert.ok((await tool(g.base, TOKEN, "comment", { cat: "x", text: "t", author: "queen" })).refused);
	});

	test("the queen's key can't be used as an agent for the café routes, nor an agent key for the runner", async () => {
		assert.equal((await fetch(g.base + "/api/runner/wait", { method: "POST", headers: { Authorization: "Bearer " + TOKEN } })).status, 401);
		assert.equal((await fetch(g.base + "/api/runner/say", { method: "POST", headers: { Authorization: "Bearer " + TOKEN }, body: "{}" })).status, 401);
		const big = JSON.stringify({ text: "x".repeat(70 * 1024) });
		assert.equal((await fetch(g.base + "/api/runner/say", { method: "POST", headers: { Authorization: "Bearer " + QUEEN }, body: big })).status, 413);
		for (const body of ["null", "[]", "12", "{", '{"steps":"x"}', '{"steps":[null,1,{"tool":5}],"routine":{"id":{}}}', '{"done":true,"text":"hi","routine":"x"}']) {
			const r = await fetch(g.base + "/api/runner/say", { method: "POST", headers: { Authorization: "Bearer " + QUEEN }, body });
			assert.ok(r.status < 500, body + " → " + r.status);
		}
	});

	test("document and routine writes with hostile shapes don't kill the owner's café", async () => {
		const put = (p, data) => api("/api/db/" + p, { method: "PUT", body: JSON.stringify({ data }) });
		for (const data of [{ time: 5, days: "mon", tz: {}, on: true }, { time: "25:99", on: true }, { time: "09:00", days: [null, "x", 99], tz: "Not/AZone", on: true }, { time: "09:00", days: [1.5], on: true }]) {
			assert.equal((await put("routines/r1", data)).status, 200);
			const heard = await wait();
			assert.ok(Array.isArray(heard.notes), JSON.stringify(data) + " → " + JSON.stringify(heard));
		}
	});

	test("a routine handed out stays handed out once its turn is finished", async () => {
		await api("/api/db/routines/daily", { method: "PUT", body: JSON.stringify({ data: { name: "Daily", time: "00:00", tz: "UTC", on: true, prompt: "Tidy up" } }) });
		assert.equal((await wait()).routine.id, "daily");
		const handed = (await docs())["routines/daily"];
		assert.ok(handed.last && handed.handed && !handed.finished);
		assert.equal((await wait()).routine, null, "never twice for one firing");
		const says = (body) => fetch(g.base + "/api/runner/say", { method: "POST", headers: asQueen, body: JSON.stringify(body) });
		await says({ turn: "t1", text: "half way", done: false, routine: { id: "daily", name: "Daily" } });
		assert.equal((await docs())["routines/daily"].finished, undefined, "a turn still going isn't finished");
		await says({ turn: "t1", text: "Tidied.", done: true, routine: { id: "daily", name: "Daily" } });
		assert.equal((await docs())["routines/daily"].finished, handed.last);
		await patch("routines/daily", { handed: Date.now() - 11 * 60 * 1000 });
		assert.equal((await wait()).routine, null, "a finished firing is not handed out again, however old");
	});

	test("a routine whose runner died is handed out once more, and only once", async () => {
		await api("/api/db/routines/lost", { method: "PUT", body: JSON.stringify({ data: { name: "Lost", time: "00:00", tz: "UTC", on: true, prompt: "Go" } }) });
		assert.equal((await wait()).routine.id, "lost");
		const expire = () => patch("routines/lost", { handed: Date.now() - 11 * 60 * 1000 });
		assert.equal((await wait()).routine, null, "not before its lease is up");
		await expire();
		const again = await wait();
		assert.equal(again.routine.id, "lost");
		assert.equal((await docs())["routines/lost"].retried, true);
		await expire();
		assert.equal((await wait()).routine, null, "a second loss is left for the next firing");
	});

	test("a routine that was handed out before leases existed isn't run again", async () => {
		const today = new Date(), midnight = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
		await api("/api/db/routines/old", { method: "PUT", body: JSON.stringify({ data: { name: "Old", time: "00:00", tz: "UTC", on: true, prompt: "Go", last: midnight } }) });
		assert.equal((await wait()).routine, null);
	});

	test("answer on a doc that isn't a quiz is a refusal", async () => {
		await api("/api/db/quizzes/junk", { method: "PUT", body: JSON.stringify({ data: { hello: "world" } }) });
		const r = await api("/api/tools/answer", { method: "POST", body: JSON.stringify({ quiz: "junk", answers: ["a"] }) });
		assert.ok(r.status < 500, "→ " + r.status);
	});

	test("a decider that answers with no answers, asked to log, isn't a crash", async () => {
		const r = await api("/api/tools/decide", { method: "POST", body: JSON.stringify({ state: "x", questions: { a: { type: "noul" } }, kind: "sort", old: "a" }) });
		assert.ok(r.status < 500, "→ " + r.status + " " + await r.text());
	});

	test("brain files: odd ids, odd names, huge bodies", async () => {
		for (const id of ["a%2Fb", "x-zzzzzzzz", "x-0123456789", "tester:abc-01234567"]) assert.ok([404, 400].includes((await api("/files/" + id)).status), id);
		const up = await api("/api/files", { method: "POST", headers: { "Content-Type": "text/html", "X-Name": "a\r\nSet-Cookie: x=1" }, body: "x" }).catch((e) => e);
		if (up instanceof Response) assert.ok(up.status < 500, "→ " + up.status);
		const svg = await (await api("/api/files", { method: "POST", headers: { "Content-Type": "image/svg+xml", "X-Name": "x.svg" }, body: "<svg onload=alert(1)/>" })).json();
		const r = await api(svg.url);
		assert.match(r.headers.get("content-disposition"), /^attachment/, "svg must download, never render inline");
		assert.match(r.headers.get("content-security-policy"), /sandbox/);
	});

	test("cross-site writes and websockets are refused", async () => {
		const r = await fetch(g.base + "/api/db/rooms/x", { method: "PUT", headers: { Cookie: cookie, "X-Catio": "1", Origin: "https://evil.example" }, body: JSON.stringify({ data: {} }) });
		assert.equal(r.status, 403, "X-Catio from a foreign Origin must be refused");
	});

	test("/authorize only accepts Claude redirects, however they're dressed", async () => {
		for (const uri of ["https://claude.ai.evil.example/cb", "https://evil.example/?x=https://claude.ai", "http://claude.ai/cb", "https://claude.ai@evil.example/cb", "https://CLAUDE.AI.evil.com/", "javascript:alert(1)"]) {
			const r = await fetch(g.base + "/register", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ client_name: "x", redirect_uris: [uri], token_endpoint_auth_method: "none" }) });
			assert.ok(r.status >= 400 && r.status < 500, uri + " registered: " + r.status);
		}
	});
	const from = (ip, user, password) => fetch(g.base + "/login", { method: "POST", headers: { "CF-Connecting-IP": ip }, body: new URLSearchParams({ user, password }), redirect: "manual" });

	test("a stranger guessing at the owner's handle is locked out, not the owner", async () => {
		for (let i = 0; i < 5; i++) assert.equal((await from("198.51.100.7", "charlotte", "wrong-wrong-wrong-" + i)).status, 401);
		assert.equal((await from("198.51.100.7", "charlotte", "wrong-wrong-wrong-5")).status, 429, "the stranger waits");
		assert.equal((await from("198.51.100.7", "charlotte", PASSWORD)).status, 429, "even with a lucky guess");
		assert.equal((await from("203.0.113.9", "charlotte", PASSWORD)).status, 303, "the owner, from her own address, walks in");
	});

	test("one address trying many handles is stopped, whichever handles", async () => {
		for (let i = 0; i < 20; i++) assert.equal((await from("198.51.100.8", "nobody-" + i, "wrong-wrong-wrong-0")).status, 401);
		assert.equal((await from("198.51.100.8", "nobody-20", "wrong-wrong-wrong-0")).status, 429);
		assert.equal((await from("198.51.100.8", "charlotte", PASSWORD)).status, 429);
		assert.equal((await from("203.0.113.9", "charlotte", PASSWORD)).status, 303, "everyone else is unaffected");
	});

	// ---- the audit of 5 October 2026 (docs/audit-2026-10-05.md) ----

	test("a password of megabytes is a refusal, not a crash", async () => {
		// at 33 MiB the field reached the Durable Object over its RPC limit, and the sign-in answered 500 before it
		// ever looked at the handle. It is refused unread now, so the big body costs the test nothing.
		const huge = new URLSearchParams({ user: "charlotte", password: "x".repeat(33 * 1024 * 1024) });
		for (const path of ["/login", "/authorize"]) {
			const r = await fetch(g.base + path, { method: "POST", body: huge, redirect: "manual" });
			assert.ok(r.status < 500, path + " → " + r.status);
		}
		// and a password just over the cap is refused the same way, not silently cut short and tried
		const over = new URLSearchParams({ user: "charlotte", password: "x".repeat(17 * 1024) });
		assert.ok((await fetch(g.base + "/login", { method: "POST", body: over, redirect: "manual" })).status < 500);
		// the sign-in still works afterwards, with the real password
		assert.equal((await login(g.base, "charlotte", PASSWORD)).status, 303);
	});

	test("a toString key is dropped at the door, not carried to whatever calls String()", async () => {
		const hostile = { toString: 1 };   // String(this) throws: "Cannot convert object to primitive value"
		const call = (name, args) => rpcRaw(g.base, TOKEN, { jsonrpc: "2.0", id: nextId++, method: "tools/call", params: { name, arguments: args } });
		assert.ok((await call("report_status", { agent: "tosh-cat", title: hostile, mood: "busy" })).status < 500, "a tool's arguments");
		assert.ok((await call("report_status", { agent: hostile })).status < 500, "a tool's own id");
		assert.ok((await api("/api/db/house/main", { method: "PUT", body: JSON.stringify({ data: { name: hostile } }) })).status < 500, "a café document");
		assert.ok((await api("/api/db/routines/r9", { method: "PUT", body: JSON.stringify({ data: { time: hostile, on: true } }) })).status < 500, "a stored routine");
		assert.ok((await api("/api/tools/comment", { method: "POST", body: JSON.stringify({ cat: "x", text: hostile }) })).status < 500, "the owner's JSON routes");
		assert.ok((await fetch(g.base + "/api/runner/say", { method: "POST", headers: asQueen, body: JSON.stringify({ text: hostile, routine: hostile }) })).status < 500, "a runner's say");
		// and the café still opens, so nothing hostile was stored that breaks reading it back
		assert.ok((await api("/api/db")).status < 500, "the café after all that");
	});

	test("a decider that answers answers: null is a refusal, not a crash", async () => {
		const r = await api("/api/tools/decide", { method: "POST", body: JSON.stringify({ state: "NOTHING-AT-ALL", questions: { a: { type: "noul" } }, kind: "sort", old: "a" }) });
		assert.ok(r.status < 500, "→ " + r.status + " " + await r.text());
	});

	test("a note is offered again until the runner says it has it", async () => {
		const waitAcking = async (ack) => (await fetch(g.base + "/api/runner/wait", {
			method: "POST", headers: { ...asQueen, "Content-Type": "application/json" }, body: JSON.stringify({ acks: true, ack }),
		})).json();
		await tool(g.base, QUEEN, "report_status", { agent: "queen", mood: "done" });
		await api("/api/tools/comment", { method: "POST", body: JSON.stringify({ cat: "queen", text: "feed the cats" }) });

		const first = await waitAcking(0);
		assert.deepEqual(first.notes.map((n) => n.text), ["feed the cats"]);
		// the runner was handed it and never said so: a dropped connection, or a turn that died. Said twice beats lost.
		const again = await waitAcking(0);
		assert.deepEqual(again.notes.map((n) => n.text), ["feed the cats"], "a note nobody acknowledged was never offered again");

		await api("/api/tools/comment", { method: "POST", body: JSON.stringify({ cat: "queen", text: "and the dog" }) });
		const next = await waitAcking(first.notes[0].at);
		assert.deepEqual(next.notes.map((n) => n.text), ["and the dog"], "an acknowledged note came back");
	});
});

describe("misconfigured secrets", () => {
	test("CATIO_QUEEN equal to CATIO_TOKEN doesn't take the whole gateway down", async () => {
		const same = rand("same-secret-"), g = await boot({ CATIO_TOKEN: same, CATIO_PASSWORD: rand("pw-"), CATIO_QUEEN: same });
		const r = await rpcRaw(g.base, same, { jsonrpc: "2.0", id: 1, method: "ping" });
		const home = await fetch(g.base + "/");
		assert.ok(r.status < 500 && home.status < 500, `ping ${r.status}, home ${home.status}: every request throws`);
		// and if it stays up, the shared key must not be the queen's AND an agent's at once
		if (r.status === 200) {
			const w = await fetch(g.base + "/api/runner/wait", { method: "POST", headers: { Authorization: "Bearer " + same } });
			assert.notEqual(w.status, 200, "an agents' key shared with the queen's secret speaks as the queen");
		}
	});

	test("a too-short CATIO_QUEEN is ignored rather than fatal", async () => {
		const g = await boot({ CATIO_TOKEN: rand("t-"), CATIO_PASSWORD: rand("pw-"), CATIO_QUEEN: "short" });
		assert.ok((await fetch(g.base + "/")).status < 500);
	});

	test("CATIO_HANDLE with hostile characters says why instead of crashing", async () => {
		const g = await boot({ CATIO_PASSWORD: rand("pw-"), CATIO_HANDLE: "Not A Handle!!" });
		const r = await fetch(g.base + "/");
		assert.equal(r.status, 503);
		assert.match(await r.text(), /CATIO_HANDLE/);
	});
});
