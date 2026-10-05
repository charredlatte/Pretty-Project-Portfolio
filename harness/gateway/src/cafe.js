// The KittyChat Café, served from the gateway's own address, the way OpenClaw's gateway serves its Control UI:
// the same page as in claude.ai (catio/index.html), with cafe/runtime.js standing in for what claude.ai gives a
// page. Each user sees their own, behind their password: the page, the brain's files and the café's database of
// their house, and the gateway's tools, which they use as the house's owner. The licensed art (never in the repo)
// is uploaded once with an admin's key and served to the first house alone: its licences are personal. People an
// admin invites make their own account at /signup. An open café keeps a WebSocket to its house and hears every change.
import PAGE from "../../../catio/index.html";
import RUNTIME from "../cafe/runtime.js";
import { clientIp, esc, noAccount, page } from "./signin.js";
import { MIN_SECRET, randomToken, sha256 } from "./secret.js";
import { bootProblem, hasAccount, registry } from "./registry.js";
import { FIRST_HOUSE, fileKeys } from "./houses.js";

const COOKIE = "__Host-catio";
const STAY = 30 * 24 * 3600 * 1000;   // a signed-in browser stays signed in a month
const MAX_FILE = 20 * 1024 * 1024;    // the brain's cap, as in claude.ai
const MAX_DOC = 1024 * 1024;
const DOC_PATH = /^[A-Za-z0-9_.~:@+-]{1,200}(\/[A-Za-z0-9_.~:@+-]{1,200}){1,7}$/;
const ART = /^art\/(furniture\.png|licensed\/[a-z0-9-]+(\/[a-z0-9-]+)?\.(png|ttf))$/;
const ART_TYPES = { png: "image/png", ttf: "font/ttf" };

const json = (body, status = 200) => Response.json(body, { status, headers: { "Cache-Control": "no-store" } });
const refuse = (status, code, error) => json({ code, error }, status);
/** A path segment, decoded; null when it isn't valid. */
const tryDecode = (s) => { try { return decodeURIComponent(s); } catch { return null; } };
/** The request's JSON object, or {} when it isn't one. */
const bodyOf = async (request) => { const b = await request.json().catch(() => null); return b && typeof b === "object" && !Array.isArray(b) ? b : {}; };

function cookieOf(request) {
	for (const part of (request.headers.get("Cookie") || "").split(";")) {
		const [k, ...v] = part.trim().split("=");
		if (k === COOKIE) return v.join("=");
	}
	return "";
}

const houseOf = (env, user) => env.HOUSE.get(env.HOUSE.idFromName(user.house));

/** The user this browser is signed in as, or null. */
async function signedIn(request, env) {
	const token = cookieOf(request);
	return token ? (await registry(env)).userOfLogin(await sha256(token)) : null;
}

// a write from the café's own page: a header no other site can send without asking first, from her address
function fromCafe(request) {
	const origin = request.headers.get("Origin");
	return request.headers.get("X-Catio") === "1" && (!origin || origin === new URL(request.url).origin);
}

/** The user whose key this request carries (with the key's role on it), or null. */
async function agentKey(request, env) {
	const m = /^Bearer\s+(\S+)$/i.exec(request.headers.get("Authorization") || "");
	return m ? (await registry(env)).userOfKey(await sha256(m[1])) : null;
}
const MAX_SAY = 64 * 1024;   // a turn of the queen's, streamed

function signInPage(problem = "", status = 200, lights = "") {
	return page("The KittyChat Café", `<h1>The KittyChat Café</h1>
<p>Your cats, on your own address.</p>
${problem ? `<p class="bad" role="alert">${esc(problem)}</p>` : ""}${lights || `
<form method="post" action="/login">
<label for="user">Your handle</label>
<input id="user" name="user" autocomplete="username" autocapitalize="none" required autofocus>
<label for="password">Your Catio password</label>
<input id="password" name="password" type="password" autocomplete="current-password" required>
<div class="row"><button class="go">Come in</button></div>
</form>
<p class="soft">Invited? <a href="/signup">Make your account</a>.</p>`}`, status);
}

function signUpPage(invite = "", user = "", problem = "", status = 200, origin = "", lights = "") {
	return page("Join the KittyChat Café", `<h1>Join the KittyChat Café</h1>
<p>A café of your own, for your own cats. You need an invite from its admin.</p>
${problem ? `<p class="bad" role="alert">${esc(problem)}</p>` : ""}${lights || `
<form method="post" action="/signup">
<label for="invite">Your invite</label>
<input id="invite" name="invite" value="${esc(invite)}" autocomplete="off" autocapitalize="none" spellcheck="false" required${invite ? "" : " autofocus"}>
<label for="user">Pick a handle</label>
<input id="user" name="user" value="${esc(user)}" autocomplete="username" autocapitalize="none" spellcheck="false" required pattern="[A-Za-z0-9][A-Za-z0-9-]{1,30}"${invite ? " autofocus" : ""}>
<p class="soft">2 to 31 letters, digits or dashes. It is how you sign in, here and in Claude.</p>
<label for="password">A password</label>
<input id="password" name="password" type="password" autocomplete="new-password" minlength="${MIN_SECRET}" required>
<label for="again">The password again</label>
<input id="again" name="again" type="password" autocomplete="new-password" minlength="${MIN_SECRET}" required>
<p class="soft">${MIN_SECRET} characters or more. Nobody can show it to you again: an admin can only set a new one.</p>
<div class="row"><button class="go">Make my café</button></div>
</form>
<p class="soft">Have an account? <a href="/">Sign in</a>.</p>
${invite && origin ? forAnAI(invite, origin) : ""}`}`, status);
}

// The same invite, for an AI setting the café up for someone: the account and its first agents' key, as JSON
const forAnAI = (invite, origin) => `<h2>Setting this up for someone, as their AI?</h2>
<p class="soft">Ask them for a handle and a password of ${MIN_SECRET} characters or more that they keep (don't choose it
for them), then use the invite once:</p>
<pre style="white-space: pre-wrap; word-break: break-all">curl -sS -X POST ${esc(origin)}/signup -H 'Content-Type: application/json' \\
  -d '{"invite": "${esc(invite)}", "handle": "&lt;handle&gt;", "password": "&lt;password&gt;"}'</pre>
<p class="soft">The answer is <code>{"handle", "key", "mcp"}</code>: their first agents' key, shown once. Keep it out of
repositories and chats. Claude Code: <code>claude mcp add --transport http catio ${esc(origin)}/mcp --header
"Authorization: Bearer &lt;key&gt;"</code>; any other MCP client takes <code>${esc(origin)}/mcp</code> with that header.
An agent then calls <code>house_rules</code>, <code>report_status</code> and <code>inbox</code>, and is a cat in their
café: their own, at ${esc(origin)}, not the admin's.</p>
<p class="soft">For every Claude Code session to report by itself, the <code>kittychat-house-rules</code> plugin's hook
does it, reading <code>CATIO_URL=${esc(origin)}</code> and <code>CATIO_TOKEN=&lt;key&gt;</code> (in
<code>~/.claude/settings.json</code> under <code>"env"</code>, or a cloud environment's variables, with
<code>${esc(new URL(origin).host)}</code> allowed under its network access). Without the plugin the two variables do
nothing. Install it (in a cloud environment, in its setup script; a session started before then won't have it):</p>
<pre style="white-space: pre-wrap; word-break: break-all">claude plugin marketplace add https://github.com/charredlatte/Pretty-Project-Portfolio.git
claude plugin install kittychat-house-rules@kittychat --scope user</pre>
<p class="soft">The plugin also brings this café's house rules to every repo they work in: an audit at the start of each
session, no pushes to the default branch, no Claude credit lines in public repos. Tell them before installing it.</p>`;

// a form posted from the café's own address: the cookie is SameSite=Strict, and the Origin, when sent, must be ours
const sameOrigin = (request) => { const o = request.headers.get("Origin"); return !o || o === new URL(request.url).origin; };

/** The admin's page for invites: make one (shown once, as a link to pass on), or take back every unused one. */
function invitePage(open, made = null, note = "") {
	return page("Invite someone", `<h1>Invite someone</h1>
<p>An invite lets one person make an account and a café of their own. It works once, for a week.</p>
${made ? `<p><strong>Send them this link.</strong> It is shown this once:</p>
<p><input readonly value="${esc(made)}" aria-label="The invite link"></p>` : ""}
${note ? `<p>${esc(note)}</p>` : ""}
<p class="soft">${open === 1 ? "1 invite is" : `${open} invites are`} out and unused.</p>
<form method="post" action="/invite">
<div class="row"><button class="go" name="do" value="make">Make an invite</button>${open ? `<button name="do" value="drop">Take back unused invites</button>` : ""}</div>
</form>
<p class="soft">They see only their own café. The packs' art stays yours: their café is drawn plainly.</p>
<p class="soft"><a href="/">Back to the café</a></p>`);
}

const signedInAs = async (reg, user) => {
	const token = randomToken();
	await reg.login(await sha256(token), user.id, Date.now() + STAY);
	return new Response(null, { status: 303, headers: {
		Location: "/",
		"Set-Cookie": `${COOKIE}=${token}; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=${STAY / 1000}`,
	} });
};

async function signUp(request, env) {
	if (/^application\/json\b/.test(request.headers.get("Content-Type") || "")) return signUpForAnAI(request, env);
	if (!(await hasAccount(env))) return signUpPage("", "", NOT_YET, 503, "", noAccount(env, request));
	if (!sameOrigin(request)) return signUpPage("", "", "Sign up from this page.", 403);
	const form = await request.formData();
	const invite = String(form.get("invite") || "").trim(), user = String(form.get("user") || "").trim();
	const password = String(form.get("password") || "");
	if (password !== String(form.get("again") || "")) return signUpPage(invite, user, "The two passwords aren't the same.", 400);
	const reg = await registry(env);
	const made = await reg.signUp(invite, user, password);
	if (made.error) return signUpPage(invite, user, made.error, 400);
	return signedInAs(reg, made.user);
}

// an AI signing up for someone: no browser to sign in, so the answer is the account's first agents' key, once
async function signUpForAnAI(request, env) {
	if (!(await hasAccount(env))) return refuse(503, "no_account", NO_ACCOUNT());
	if (!sameOrigin(request)) return refuse(403, "forbidden", "Not from another site.");
	const { invite, handle, password, name } = await bodyOf(request);
	const reg = await registry(env);
	const made = await reg.signUp(invite, handle, password);
	if (made.error) return refuse(400, "bad_request", made.error);
	const { key } = await reg.mintKey(made.user.id, name || "first");
	const origin = new URL(request.url).origin;
	return json({ handle: made.user.id, key, mcp: origin + "/mcp" }, 201);
}

const NO_ACCOUNT = () => "The gateway has no account yet. " + bootProblem();
const NOT_YET = "The gateway has no account yet. Its warning lights:";

async function login(request, env) {
	if (!(await hasAccount(env))) return signInPage(NOT_YET, 503, noAccount(env, request));
	const reg = await registry(env);
	const form = await request.formData().catch(() => null);
	if (!form) return signInPage("That wasn't the sign-in form.", 400);
	const user = await reg.checkPassword(String(form.get("user") || ""), String(form.get("password") || ""), clientIp(request));
	if (user && user.locked) return signInPage("Too many wrong passwords. Try again in a quarter of an hour.", 429);
	if (!user) return signInPage("That handle and password aren't right.", 401);
	return signedInAs(reg, user);
}

// the page in the skeleton claude.ai's Artifact publish gives it, with the runtime first
const CAFE = '<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover">' +
	// the tab's icon is the brand's cat-face bubble, licensed art: served, like the rest, only once she is signed in
	'<link rel="icon" type="image/png" href="/art/licensed/ui/logo.png">' +
	'<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style><script src="/runtime.js"></script></head><body>' + PAGE + "</body></html>";
const PAGE_HEADERS = {
	"Content-Type": "text/html; charset=utf-8",
	"Cache-Control": "no-store",
	"X-Frame-Options": "DENY",
	"Referrer-Policy": "no-referrer",
	"Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; " +
		"font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
};

// A brain file can be anything she drops, so it is shown in a sandbox of its own: nothing in it can run as the café.
function served(body, type, name, inline) {
	return new Response(body, { headers: {
		"Content-Type": type || "application/octet-stream",
		"Content-Disposition": `${inline ? "inline" : "attachment"}; filename*=UTF-8''${encodeURIComponent(name || "file")}`,
		"Content-Security-Policy": "sandbox; default-src 'none'; img-src 'self' data:; media-src 'self'; style-src 'unsafe-inline'",
		"X-Content-Type-Options": "nosniff",
		"Cache-Control": "private, max-age=3600",
	} });
}

/** The café's routes, or null when the path isn't one of them. */
export async function cafe(request, env) {
	const url = new URL(request.url), path = url.pathname, method = request.method;

	// with an agents' key only: the licensed art (an admin's), and a user's café data, moved in once
	if (path === "/api/import" || path.startsWith("/api/art/")) {
		const by = await agentKey(request, env);
		if (!by) return refuse(401, "unauthorized", "An agents' key is needed.");
		return (await withKey(path, method, request, env, by)) || refuse(404, "not_found", "Not here.");
	}

	// the queen's runner (harness/runner/queen.py), with a key whose role is queen (CATIO_QUEEN for the first account,
	// or one minted in the café): it waits here for what to do, and streams what she says, in that key's house
	if (path.startsWith("/api/runner/") && method === "POST") {
		const by = await agentKey(request, env);
		if (!by || by.role !== "queen") return refuse(401, "unauthorized", "The queen's key is needed: the CATIO_QUEEN secret in Cloudflare, or a key minted for her in the café.");
		const house = houseOf(env, by);
		if (path === "/api/runner/wait") return json(await house.waitForQueen());
		if (path === "/api/runner/say") {
			const text = await request.text();
			if (text.length > MAX_SAY) return refuse(413, "too_big", "A turn is 64 KB at most.");
			let body;
			try { body = JSON.parse(text); } catch { return refuse(400, "bad_request", "The body is JSON: {turn, text, done, routine}."); }
			return json(await house.queenSays(body));
		}
		return refuse(404, "not_found", "The runner waits and says; nothing else is here.");
	}

	if (path === "/runtime.js") return new Response(RUNTIME, { headers: { "Content-Type": "text/javascript; charset=utf-8", "Cache-Control": "no-store" } });
	if (path === "/login" && method === "POST") return login(request, env);
	// sign out: this browser's cookie stops working now, not in a month
	if (path === "/logout" && method === "POST") {
		const token = cookieOf(request);
		if (token) await (await registry(env)).logout(await sha256(token));
		return new Response(null, { status: 303, headers: { Location: "/", "Set-Cookie": `${COOKIE}=; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=0` } });
	}
	if (path === "/signup" && method === "GET") return signUpPage(url.searchParams.get("invite") || "", "", "", 200, url.origin);
	if (path === "/signup" && method === "POST") return signUp(request, env);

	const cafePaths = path === "/" || path === "/invite" || path === "/ws" || path.startsWith("/api/") || path.startsWith("/art/") || path.startsWith("/files/");
	if (!cafePaths) return null;
	const user = await signedIn(request, env);
	if (!user && (path === "/" || path === "/invite")) return (await hasAccount(env)) ? signInPage() : signInPage(NOT_YET, 503, noAccount(env, request));
	if (!user) return refuse(401, "signed_out", "Sign in to the café first.");

	if (path === "/") return new Response(CAFE, { headers: PAGE_HEADERS });
	// invites, from an admin signed in to their café: a form of its own, so it needs no button in the page
	if (path === "/invite") {
		if (!user.admin) return page("Not yours", `<h1>Only an admin invites</h1><p><a href="/">Back to the café</a></p>`, 403);
		const reg = await registry(env);
		if (method === "GET") return invitePage(await reg.openInvites());
		if (method !== "POST" || !sameOrigin(request)) return page("Not here", `<h1>Make invites from this page</h1><p><a href="/invite">Invites</a></p>`, 403);
		if ((await request.formData()).get("do") === "drop") {
			const n = await reg.dropInvites();
			return invitePage(0, null, n === 1 ? "1 invite taken back." : `${n} invites taken back.`);
		}
		const { code } = await reg.invite(user.id);
		return invitePage(await reg.openInvites(), `${url.origin}/signup?invite=${code}`);
	}
	if (path === "/ws") {
		if (request.headers.get("Origin") !== url.origin) return refuse(403, "forbidden", "Only the café opens this.");
		return houseOf(env, user).fetch(request);
	}
	if (path.startsWith("/art/") && method === "GET") {
		// the packs' licences are personal: their art is hers, never her guests'
		if (path.startsWith("/art/licensed/") && user.house !== FIRST_HOUSE) return new Response("Not found\n", { status: 404 });
		const { value, metadata } = await env.FILES.getWithMetadata("art:" + path.slice(1), "arrayBuffer");
		if (!value) return new Response("Not found\n", { status: 404 });
		return new Response(value, { headers: { "Content-Type": (metadata && metadata.type) || "application/octet-stream", "Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff" } });
	}
	// a brain file is kept under its house's name, so another house can neither read nor delete it; one from
	// before accounts moves under the first house's name the first time it is read
	if (path.startsWith("/files/") && method === "GET") {
		const keys = fileKeys(user.house, path.slice("/files/".length));
		for (const k of keys) {
			const { value, metadata } = await env.FILES.getWithMetadata(k, "arrayBuffer");
			if (!value) continue;
			if (k !== keys[0]) { await env.FILES.put(keys[0], value, { metadata }); await env.FILES.delete(k); }
			const type = (metadata && metadata.type) || "";
			return served(value, type, metadata && metadata.name, /^(image\/(png|jpeg|gif|webp)|text\/plain|application\/pdf)/.test(type));
		}
		return new Response("Not found\n", { status: 404 });
	}
	const house = houseOf(env, user);
	if (method === "GET" && path === "/api/db") return json({ docs: await house.docs() });
	if (method === "GET" && path === "/api/keys") return json({ keys: await (await registry(env)).keys(user.id) });

	if (!fromCafe(request)) return refuse(403, "forbidden", "Only the café's own page writes here.");
	if (path.startsWith("/api/db/")) {
		const doc = tryDecode(path.slice("/api/db/".length));
		if (!doc || !DOC_PATH.test(doc) || doc.split("/").length % 2) return refuse(400, "bad_request", "That isn't a document's path.");
		if (method === "DELETE") { await house.dropDoc(doc); return json({ ok: true }); }
		const text = await request.text();
		if (text.length > MAX_DOC) return refuse(413, "too_big", "A document is 1 MB at most.");
		let data;
		try { ({ data } = JSON.parse(text)); } catch { /* checked below */ }
		if (!data || typeof data !== "object" || Array.isArray(data)) return refuse(400, "bad_request", "The body is {data: {...}}.");
		if (method === "PUT") { await house.putDoc(doc, data); return json({ ok: true }); }
		if (method === "PATCH") return (await house.putDoc(doc, data, true)) ? json({ ok: true }) : refuse(404, "not_found", "No such document.");
	}
	if (path === "/api/files" && method === "POST") {
		const body = await request.arrayBuffer();
		if (body.byteLength > MAX_FILE) return refuse(413, "too_big", "Files are 20 MB at most.");
		const id = Date.now().toString(36) + "-" + crypto.randomUUID().slice(0, 8);
		const type = (request.headers.get("Content-Type") || "application/octet-stream").slice(0, 200);
		const name = (tryDecode(request.headers.get("X-Name") || "file") ?? "file").slice(0, 200);
		await env.FILES.put(fileKeys(user.house, id)[0], body, { metadata: { type, name, size: body.byteLength } });
		return json({ id, url: "/files/" + id, sizeBytes: body.byteLength, contentType: type });
	}
	if (path.startsWith("/api/files/") && method === "DELETE") {
		for (const k of fileKeys(user.house, path.slice("/api/files/".length))) await env.FILES.delete(k);
		return json({ deleted: true });
	}
	// keys for this user's agents and sessions: minted (shown once; the registry keeps only the hash) and dropped
	if (path === "/api/keys" && method === "POST") {
		const { name, role } = await bodyOf(request);
		const r = await (await registry(env)).mintKey(user.id, name, role);
		return r.error ? refuse(400, "bad_request", r.error) : json(r);
	}
	if (path.startsWith("/api/keys/") && method === "DELETE") {
		const name = tryDecode(path.slice("/api/keys/".length));
		const gone = name && await (await registry(env)).dropKey(user.id, name);
		return gone ? json({ ok: true }) : refuse(404, "not_found", "No key by that name.");
	}
	// accounts, made and reset by an admin signed in to their café (never by a key: a key is in every session's
	// environment, and must not be able to become anyone's owner). Anyone else signs up with an invite (/invite).
	if (path === "/api/users" && method === "POST") {
		if (!user.admin) return refuse(403, "forbidden", "Only an admin creates accounts.");
		const { id, password } = await bodyOf(request);
		const made = await (await registry(env)).createUser(id, password);
		if (made.error) return refuse(400, "bad_request", made.error);
		return json({ id: made.user.id, house: made.user.house }, 201);
	}
	// a reset signs the user's browsers out, kills their keys, and takes back every connector they let in
	if (path.startsWith("/api/users/") && method === "PUT") {
		if (!user.admin) return refuse(403, "forbidden", "Only an admin resets a password.");
		const id = tryDecode(path.slice("/api/users/".length));
		if (!id) return refuse(400, "bad_request", "That isn't a handle.");
		const { password } = await bodyOf(request);
		const r = await (await registry(env)).setPassword(id, password);
		if (r.error) return refuse(400, "bad_request", r.error);
		// under the handle as the registry spells it, and, for the first house, under "charlotte": its grants from
		// before accounts were made under that name whatever CATIO_HANDLE says
		let revoked = 0;
		for (const uid of new Set([r.id, ...(r.house === FIRST_HOUSE ? ["charlotte"] : [])])) {
			for (let cursor; ;) {
				const batch = await env.OAUTH_PROVIDER.listUserGrants(uid, cursor ? { cursor } : undefined);
				for (const g of batch.items) { await env.OAUTH_PROVIDER.revokeGrant(g.id, uid); revoked++; }
				if (!batch.cursor) break;
				cursor = batch.cursor;
			}
		}
		return json({ ok: true, revoked });
	}
	// the gateway's tools, as the owner uses them through their connector
	if (path.startsWith("/api/tools/") && method === "POST") {
		const r = await house.call(path.slice("/api/tools/".length), await bodyOf(request), "owner");
		if (r.unknown) return refuse(404, "not_found", "No such tool.");
		if (r.error) return refuse(400, "tool_error", r.error);
		return json(r.ok);
	}
	return refuse(404, "not_found", "Not here.");
}

/** What an agents' key may do here, or null when the path isn't one of these. `by` is the key's user. */
async function withKey(path, method, request, env, by) {
	if (path.startsWith("/api/art/") && method === "PUT") {
		if (!by.admin) return refuse(403, "forbidden", "Only an admin uploads the café's art.");
		const key = path.slice("/api/".length);
		if (!ART.test(key)) return refuse(400, "bad_request", "Only the café's art goes here.");
		const body = await request.arrayBuffer();
		if (body.byteLength > 2 * 1024 * 1024) return refuse(413, "too_big", "Art files are 2 MB at most.");
		await env.FILES.put("art:" + key, body, { metadata: { type: ART_TYPES[key.split(".").pop()] } });
		return json({ ok: true, path: key });
	}
	if (path === "/api/import" && method === "POST") {
		const { docs } = await bodyOf(request);
		if (!docs || typeof docs !== "object" || Object.keys(docs).some((p) => !DOC_PATH.test(p) || p.split("/").length % 2)) {
			return refuse(400, "bad_request", "docs is {path: data}, with document paths.");
		}
		if (!(await houseOf(env, by).importDocs(docs))) return refuse(409, "not_empty", "The café already has its data: an import happens once.");
		return json({ ok: true, count: Object.keys(docs).length });
	}
	return null;
}
