// The KittyChat Café, served from the gateway's own address, the way OpenClaw's gateway serves its Control UI:
// the same page as in claude.ai (catio/index.html), with cafe/runtime.js standing in for what claude.ai gives a
// page. Everything here is hers alone, behind her password (CATIO_PASSWORD): the page, the licensed art (never in
// the repo, uploaded once with the agents' key), the brain's files, the café's own database, and the gateway's
// tools, which she uses as herself. An open café keeps a WebSocket to the house and hears every change.
import PAGE from "../../../catio/index.html";
import RUNTIME from "../cafe/runtime.js";
import { esc, page } from "./signin.js";
import { MIN_SECRET, sameSecret } from "./secret.js";

const COOKIE = "__Host-catio";
const STAY = 30 * 24 * 3600 * 1000;   // a signed-in browser stays signed in a month
const MAX_FILE = 20 * 1024 * 1024;    // the brain's cap, as in claude.ai
const MAX_DOC = 1024 * 1024;
const DOC_PATH = /^[A-Za-z0-9_.~:@+-]{1,200}(\/[A-Za-z0-9_.~:@+-]{1,200}){1,7}$/;
const ART = /^art\/(furniture\.png|licensed\/[a-z0-9-]+(\/[a-z0-9-]+)?\.(png|ttf))$/;
const ART_TYPES = { png: "image/png", ttf: "font/ttf" };

const enc = new TextEncoder();
const hashOf = async (token) => [...new Uint8Array(await crypto.subtle.digest("SHA-256", enc.encode(token)))].map((b) => b.toString(16).padStart(2, "0")).join("");
const json = (body, status = 200) => Response.json(body, { status, headers: { "Cache-Control": "no-store" } });
const refuse = (status, code, error) => json({ code, error }, status);

function cookieOf(request) {
	for (const part of (request.headers.get("Cookie") || "").split(";")) {
		const [k, ...v] = part.trim().split("=");
		if (k === COOKIE) return v.join("=");
	}
	return "";
}

const houseOf = (env) => env.HOUSE.get(env.HOUSE.idFromName("house"));

async function signedIn(request, env) {
	const token = cookieOf(request);
	return !!token && houseOf(env).loggedIn(await hashOf(token));
}

// a write from the café's own page: a header no other site can send without asking first, from her address
function fromCafe(request) {
	const origin = request.headers.get("Origin");
	return request.headers.get("X-Catio") === "1" && (!origin || origin === new URL(request.url).origin);
}

const bearer = (request) => (/^Bearer\s+(\S+)$/i.exec(request.headers.get("Authorization") || "") || [])[1];
const agentKey = (request, env) => sameSecret(bearer(request), env.CATIO_TOKEN);
const queenKey = (request, env) => sameSecret(bearer(request), env.CATIO_QUEEN);   // her runner's own key, never the agents'
const MAX_SAY = 64 * 1024;

function signInPage(problem = "", status = 200) {
	return page("The KittyChat Café", `<h1>The KittyChat Café</h1>
<p>Your cats, on your own address.</p>
${problem ? `<p class="bad" role="alert">${esc(problem)}</p>` : ""}
<form method="post" action="/login">
<label for="password">Your Catio password</label>
<input id="password" name="password" type="password" autocomplete="current-password" required autofocus>
<div class="row"><button class="go">Come in</button></div>
</form>`, status);
}

async function login(request, env) {
	if (!env.CATIO_PASSWORD || env.CATIO_PASSWORD.length < MIN_SECRET) return signInPage("The gateway has no password yet: add CATIO_PASSWORD in Cloudflare.", 503);
	const house = houseOf(env);
	if (await house.locked()) return signInPage("Too many wrong passwords. Try again in a quarter of an hour.", 429);
	const password = String((await request.formData()).get("password") || "");
	if (!(await sameSecret(password, env.CATIO_PASSWORD))) {
		await house.wrongPassword();
		return signInPage("That password isn't right.", 401);
	}
	await house.rightPassword();
	const token = [...crypto.getRandomValues(new Uint8Array(32))].map((b) => b.toString(16).padStart(2, "0")).join("");
	await house.login(await hashOf(token), Date.now() + STAY);
	return new Response(null, { status: 303, headers: {
		Location: "/",
		"Set-Cookie": `${COOKIE}=${token}; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=${STAY / 1000}`,
	} });
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

	// with the agents' key: the licensed art, uploaded from a checkout that has it, and the café's data, moved once
	if (path.startsWith("/api/art/") && method === "PUT") {
		if (!(await agentKey(request, env))) return refuse(401, "unauthorized", "The agents' key is needed.");
		const key = path.slice("/api/".length);
		if (!ART.test(key)) return refuse(400, "bad_request", "Only the café's art goes here.");
		const body = await request.arrayBuffer();
		if (body.byteLength > 2 * 1024 * 1024) return refuse(413, "too_big", "Art files are 2 MB at most.");
		await env.FILES.put("art:" + key, body, { metadata: { type: ART_TYPES[key.split(".").pop()] } });
		return json({ ok: true, path: key });
	}
	if (path === "/api/import" && method === "POST") {
		if (!(await agentKey(request, env))) return refuse(401, "unauthorized", "The agents' key is needed.");
		const { docs } = await request.json().catch(() => ({}));
		if (!docs || typeof docs !== "object" || Object.keys(docs).some((p) => !DOC_PATH.test(p) || p.split("/").length % 2)) {
			return refuse(400, "bad_request", "docs is {path: data}, with document paths.");
		}
		if (!(await houseOf(env).importDocs(docs))) return refuse(409, "not_empty", "The café already has its data: an import happens once.");
		return json({ ok: true, count: Object.keys(docs).length });
	}

	// the queen's runner (harness/runner/queen.py), with her own key: it waits here for what to do, and streams what she says
	if (path.startsWith("/api/runner/") && method === "POST") {
		if (!env.CATIO_QUEEN || env.CATIO_QUEEN.length < MIN_SECRET) return refuse(503, "no_queen", "The gateway has no queen's key yet: add CATIO_QUEEN in Cloudflare.");
		if (!(await queenKey(request, env))) return refuse(401, "unauthorized", "The queen's key is needed.");
		const house = houseOf(env);
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

	const cafePaths = path === "/" || path === "/ws" || path.startsWith("/api/") || path.startsWith("/art/") || path.startsWith("/files/");
	if (!cafePaths) return null;
	if (!(await signedIn(request, env))) return path === "/" ? signInPage() : refuse(401, "signed_out", "Sign in to the café first.");

	if (path === "/") return new Response(CAFE, { headers: PAGE_HEADERS });
	if (path === "/ws") {
		if (request.headers.get("Origin") !== url.origin) return refuse(403, "forbidden", "Only the café opens this.");
		return houseOf(env).fetch(request);
	}
	if (path.startsWith("/art/") && method === "GET") {
		const { value, metadata } = await env.FILES.getWithMetadata("art:" + path.slice(1), "arrayBuffer");
		if (!value) return new Response("Not found\n", { status: 404 });
		return new Response(value, { headers: { "Content-Type": (metadata && metadata.type) || "application/octet-stream", "Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff" } });
	}
	if (path.startsWith("/files/") && method === "GET") {
		const { value, metadata } = await env.FILES.getWithMetadata("file:" + path.slice("/files/".length), "arrayBuffer");
		if (!value) return new Response("Not found\n", { status: 404 });
		const type = (metadata && metadata.type) || "";
		return served(value, type, metadata && metadata.name, /^(image\/(png|jpeg|gif|webp)|text\/plain|application\/pdf)/.test(type));
	}
	if (method === "GET" && path === "/api/db") return json({ docs: await houseOf(env).docs() });

	if (!fromCafe(request)) return refuse(403, "forbidden", "Only the café's own page writes here.");
	const house = houseOf(env);
	if (path.startsWith("/api/db/")) {
		const doc = decodeURIComponent(path.slice("/api/db/".length));
		if (!DOC_PATH.test(doc) || doc.split("/").length % 2) return refuse(400, "bad_request", "That isn't a document's path.");
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
		const name = decodeURIComponent(request.headers.get("X-Name") || "file").slice(0, 200);
		await env.FILES.put("file:" + id, body, { metadata: { type, name, size: body.byteLength } });
		return json({ id, url: "/files/" + id, sizeBytes: body.byteLength, contentType: type });
	}
	if (path.startsWith("/api/files/") && method === "DELETE") {
		await env.FILES.delete("file:" + path.slice("/api/files/".length));
		return json({ deleted: true });
	}
	// the gateway's tools, as she uses them through the CATIO connector: as herself
	if (path.startsWith("/api/tools/") && method === "POST") {
		const r = await house.call(path.slice("/api/tools/".length), await request.json().catch(() => ({})), "charlotte");
		if (r.unknown) return refuse(404, "not_found", "No such tool.");
		if (r.error) return refuse(400, "tool_error", r.error);
		return json(r.ok);
	}
	return refuse(404, "not_found", "Not here.");
}
