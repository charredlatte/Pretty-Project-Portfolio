// Adversarial checks for the gateway, run on their own (not part of `npm test`, whose glob is *.test.mjs):
//
//     node --test test/adversarial.mjs
//
// Each test asserts what SHOULD happen. A failure is a bug found.
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

// a stand-in decider that answers with NO answers at all
let decider, deciderPort;
const startDecider = () => new Promise((done) => {
	decider = createHttpServer((req, res) => { req.resume(); req.on("end", () => { res.setHeader("Content-Type", "application/json"); res.end(JSON.stringify({ model: "x", answers: {} })); }); })
		.listen(0, "127.0.0.1", () => done(decider.address().port));
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
			const w = await fetch(g.base + "/api/runner/wait", { method: "POST", headers: { Authorization: "Bearer " + QUEEN } });
			assert.ok(w.status < 500, JSON.stringify(data) + " → " + w.status);
		}
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
	test("five wrong passwords from a stranger don't lock the real owner out", { todo: "design call: the lock is per handle, so a stranger can lock the owner out" }, async () => {
		for (let i = 0; i < 6; i++) await login(g.base, "charlotte", "wrong-wrong-wrong-" + i);
		const r = await login(g.base, "charlotte", PASSWORD);
		assert.equal(r.status, 303, "the owner is locked out for 15 minutes by anyone who knows the handle: " + r.status);
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
