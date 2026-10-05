// /authorize: the page claude.ai opens when a user adds the gateway as a connector. They type their handle and
// password, and Claude gets a token to read and manage their cats as them. Nobody but Claude's connectors may
// ask: anywhere else, a token would leave with someone else.
import { AuthorizationError, CimdFetchError } from "@cloudflare/workers-oauth-provider";
import { MIN_SECRET } from "./secret.js";
import { bootProblem, hasAccount, propsOf, registry } from "./registry.js";

const CLAUDE = ["claude.ai", "claude.com"];

/** Is this redirect URI one of Claude's? The only place the Catio's access may be sent. */
export function fromClaude(uri) {
	try {
		const u = new URL(uri);
		return u.protocol === "https:" && CLAUDE.includes(u.hostname);
	} catch {
		return false;
	}
}

export const esc = (v) => String(v).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);

const HEADERS = {
	"Content-Type": "text/html; charset=utf-8",
	"Cache-Control": "no-store",
	"X-Frame-Options": "DENY",
	"Referrer-Policy": "no-referrer",
	// the form posts here, and the right password sends the browser on to Claude
	"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self' https://claude.ai https://claude.com; frame-ancestors 'none'; base-uri 'none'",
};

export function page(title, body, status = 200, headers = new Headers()) {
	for (const [k, v] of Object.entries(HEADERS)) headers.set(k, v);
	return new Response(`<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>${esc(title)}</title>
<style>
:root { --bg: #f6efe2; --card: #fffaf0; --ink: #3b2f25; --soft: #75665a; --line: #e2d5bf; --go: #a85a34; --go-ink: #fff; --bad: #a33a2a; }
@media (prefers-color-scheme: dark) { :root { --bg: #1f1a16; --card: #2a231d; --ink: #f1e7d8; --soft: #b8a891; --line: #4a3e33; --go: #d98a5f; --go-ink: #1f1a16; --bad: #f08f7c; } }
* { box-sizing: border-box; }
body { margin: 0; min-height: 100vh; display: grid; place-items: center; padding: 16px; background: var(--bg); color: var(--ink);
  font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { width: 100%; max-width: 420px; background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 24px; }
h1 { font-size: 1.3rem; line-height: 1.3; margin: 0 0 12px; }
p { margin: 0 0 12px; }
.soft { color: var(--soft); font-size: .9rem; }
.bad { color: var(--bad); font-weight: 600; }
label { display: block; font-weight: 600; margin: 16px 0 6px; }
input { width: 100%; padding: 10px 12px; font: inherit; color: inherit; background: var(--bg); border: 1px solid var(--line); border-radius: 8px; }
.row { display: flex; gap: 10px; margin-top: 18px; }
button { flex: 1; padding: 10px 14px; font: inherit; font-weight: 600; border-radius: 8px; border: 1px solid var(--line);
  background: transparent; color: inherit; cursor: pointer; }
button.go { background: var(--go); border-color: var(--go); color: var(--go-ink); }
</style>
</head>
<body><main>${body}</main></body>
</html>
`, { status, headers });
}

// `shown` is only ever displayed: what the client calls itself, and where its access goes
function consent(shown, handle, problem = "", status = 200, headers) {
	return page("Let Claude into the Catio?", `<h1>Let ${esc(shown.client)} into the Catio?</h1>
<p>It will see your cats and what they are doing, read their conversations, and pass on your messages, files and requests.</p>
<p class="soft">Access goes to <strong>${esc(shown.host)}</strong>.</p>
${problem ? `<p class="bad" role="alert">${esc(problem)}</p>` : ""}
<form method="post">
<input type="hidden" name="handle" value="${esc(handle)}">
<input type="hidden" name="client" value="${esc(shown.client)}">
<input type="hidden" name="host" value="${esc(shown.host)}">
<label for="user">Your handle</label>
<input id="user" name="user" autocomplete="username" autocapitalize="none" required autofocus>
<label for="password">Your Catio password</label>
<input id="password" name="password" type="password" autocomplete="current-password" required>
<div class="row"><button class="go" name="decision" value="allow">Let it in</button><button name="decision" value="deny" formnovalidate>Not now</button></div>
</form>`, status, headers);
}

const startAgain = (why) => page("Start again", `<h1>Start again</h1><p>${esc(why)}</p>
<p class="soft">Close this window and connect the Catio again from claude.ai.</p>`, 400);

const notClaude = () => page("Not this one", `<h1>Only Claude can sign in here</h1>
<p>The Catio's gateway lets in Claude's connectors and nothing else.</p>`, 403);

export async function authorize(request, env) {
	const oauth = env.OAUTH_PROVIDER;
	try {
		if (!(await hasAccount(env))) {
			return page("No account yet", `<h1>The gateway has no account yet</h1>
<p>Add a secret named <strong>CATIO_PASSWORD</strong>, ${MIN_SECRET} characters or more, in Cloudflare: Workers &amp; Pages, then
catio-gateway, Settings, Variables and Secrets. It becomes the first account's password. Then connect again.</p>
${bootProblem() ? `<p class="bad">${esc(bootProblem())}</p>` : ""}`, 503);
		}
		if (request.method === "GET") {
			const ask = await oauth.parseAuthRequest(request);
			const about = await oauth.describeConsent(ask);
			if (!fromClaude(about.redirectUri)) return notClaude();
			const started = await oauth.beginConsent(ask);
			return consent({ client: about.clientName, host: about.redirectHost }, started.handle, "", 200, started.headers);
		}
		if (request.method !== "POST") return new Response(null, { status: 405, headers: { Allow: "GET, POST" } });

		const form = await request.formData().catch(() => null);
		if (!form) return startAgain("That wasn't the sign-in form.");
		const handle = String(form.get("handle") || "");
		const shown = { client: String(form.get("client") || "Claude"), host: String(form.get("host") || "claude.ai") };
		if (form.get("decision") !== "allow") {
			const denied = await oauth.denyConsent(request, handle);
			return new Response(null, { status: 302, headers: denied.headers });
		}
		const password = String(form.get("password") || "");
		if (!password) return consent(shown, handle, "Type your password first.", 400);
		const user = await (await registry(env)).checkPassword(String(form.get("user") || ""), password);
		if (user && user.locked) return consent(shown, handle, "Too many wrong passwords. Try again in a quarter of an hour.", 429);
		if (!user) return consent(shown, handle, "That handle and password aren't right.", 401);

		const approved = await oauth.approveConsent(request, handle, { scope: [] });
		if (!fromClaude(approved.request.redirectUri)) return notClaude();
		const { redirectTo } = await oauth.completeAuthorization({
			request: approved.request, userId: user.id, metadata: {}, scope: [], props: propsOf(user, true),
		});
		approved.headers.set("Location", redirectTo);
		return new Response(null, { status: 302, headers: approved.headers });
	} catch (e) {
		if (e instanceof AuthorizationError && e.redirectTo) return Response.redirect(e.redirectTo, 302);
		if (e instanceof AuthorizationError) return startAgain(e.description || "This sign-in has expired.");
		if (e instanceof CimdFetchError) return startAgain("This app could not be verified.");
		throw e;
	}
}
