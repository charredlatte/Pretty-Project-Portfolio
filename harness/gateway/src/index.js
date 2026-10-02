// The Catio's gateway: one always-on address every agent reports to, so the Catio knows who is working without
// asking claude.ai for a list. MCP at /mcp, for two kinds of caller:
//   - Charlotte, through claude.ai: the gateway is a custom connector, signed in with her password (OAuth);
//   - agents and the session hooks: they send CATIO_TOKEN as their bearer token.
// Its own address serves the KittyChat Café to her, behind her password (src/cafe.js), as OpenClaw's gateway serves
// its Control UI. See README.md for setting it up, and harness/hooks/report.py for the sessions' side.
import { OAuthProvider } from "@cloudflare/workers-oauth-provider";
import { House } from "./house.js";
import { serveMcp } from "./mcp.js";
import { sameSecret } from "./secret.js";
import { cafe } from "./cafe.js";
import { authorize, fromClaude } from "./signin.js";

export { House };

const DAY = 24 * 3600;

async function site(request, env) {
	const { pathname } = new URL(request.url);
	if (pathname === "/authorize") return authorize(request, env);
	// her own address opens the café, behind her password (src/cafe.js)
	return (await cafe(request, env)) || new Response("Not found\n", { status: 404 });
}

// The token's audience is the gateway's own /mcp address, which the code can't know before it is deployed:
// one provider per address the Worker is reached at (its workers.dev name, in practice).
const providers = new Map();

function provider(origin) {
	const resource = origin + "/mcp";
	if (!providers.has(origin)) providers.set(origin, new OAuthProvider({
		apiRoute: "/mcp",
		apiHandler: { fetch: serveMcp },
		defaultHandler: { fetch: site },
		authorizeEndpoint: "/authorize",
		tokenEndpoint: "/token",
		clientRegistrationEndpoint: "/register",
		resourceMetadata: { resource, resource_name: "The Catio" },
		// she signs in once: a grant lives as long as claude.ai keeps using it
		refreshTokenTTL: 60 * DAY,
		refreshTokenIdleTTL: 60 * DAY,
		// only Claude's connectors may register: any other redirect would carry her access away
		clientRegistrationCallback({ clientMetadata }) {
			const uris = clientMetadata.redirect_uris;
			if (!Array.isArray(uris) || !uris.length || !uris.every(fromClaude)) {
				return { code: "invalid_redirect_uri", description: "Only Claude's connectors can sign in to the Catio." };
			}
		},
		// agents and the session hooks send the shared key itself; the queen's runner sends hers (harness/runner)
		async resolveExternalToken({ token, env }) {
			if (await sameSecret(token, env.CATIO_TOKEN)) return { props: { user: "agent" }, audience: resource };
			if (await sameSecret(token, env.CATIO_QUEEN)) return { props: { user: "queen" }, audience: resource };
			return null;
		},
	}));
	return providers.get(origin);
}

export default {
	fetch(request, env, ctx) {
		return provider(new URL(request.url).origin).fetch(request, env, ctx);
	},
};
