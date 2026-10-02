// The Catio's gateway: one always-on address every agent reports to, so the Catio knows who is working without
// asking claude.ai for a list. MCP at /mcp, for two kinds of caller:
//   - a user, through claude.ai: the gateway is a custom connector, signed in with their handle and password (OAuth);
//   - agents and the session hooks: they send the user's agents' key as their bearer token.
// Each user has a house (src/house.js) and the registry (src/registry.js) says which. Its own address serves the
// KittyChat Café to each user, behind their password (src/cafe.js), as OpenClaw's gateway serves its Control UI.
// See README.md for setting it up, and harness/hooks/report.py for the sessions' side.
import { OAuthProvider } from "@cloudflare/workers-oauth-provider";
import { House } from "./house.js";
import { Registry, propsOf, registry } from "./registry.js";
import { serveMcp } from "./mcp.js";
import { sha256 } from "./secret.js";
import { cafe } from "./cafe.js";
import { authorize, fromClaude } from "./signin.js";

export { House, Registry };

const DAY = 24 * 3600;

async function site(request, env) {
	const { pathname } = new URL(request.url);
	if (pathname === "/authorize") return authorize(request, env);
	// its own address opens the café, behind the user's password (src/cafe.js)
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
		// a user signs in once: a grant lives as long as claude.ai keeps using it
		refreshTokenTTL: 60 * DAY,
		refreshTokenIdleTTL: 60 * DAY,
		// only Claude's connectors may register: any other redirect would carry a user's access away
		clientRegistrationCallback({ clientMetadata }) {
			const uris = clientMetadata.redirect_uris;
			if (!Array.isArray(uris) || !uris.length || !uris.every(fromClaude)) {
				return { code: "invalid_redirect_uri", description: "Only Claude's connectors can sign in to the Catio." };
			}
		},
		// agents and the session hooks send a user's agents' key: the registry knows whose it is
		async resolveExternalToken({ token, env }) {
			const user = await (await registry(env)).userOfKey(await sha256(token));
			return user ? { props: propsOf(user, false), audience: resource } : null;
		},
	}));
	return providers.get(origin);
}

export default {
	fetch(request, env, ctx) {
		return provider(new URL(request.url).origin).fetch(request, env, ctx);
	},
};
