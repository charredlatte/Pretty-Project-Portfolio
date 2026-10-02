// MCP over Streamable HTTP at /mcp: JSON-RPC in a POST, JSON back, no server-sent stream and no sessions.
// The OAuth provider has already checked the bearer token: ctx.props says who sent it, and which house is theirs.
import { whose } from "./houses.js";
import { INSTRUCTIONS, TOOLS } from "./tools.js";

const NAMES = new Set(TOOLS.map((t) => t.name));

export async function serveMcp(request, env, ctx) {
	if (request.method !== "POST") return new Response(null, { status: 405, headers: { Allow: "POST" } });
	let body;
	try {
		body = await request.json();
	} catch {
		return Response.json({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "parse error" } }, { status: 400 });
	}
	const { house: name, owner } = whose(ctx.props);
	const house = env.HOUSE.get(env.HOUSE.idFromName(name));
	const who = owner ? "charlotte" : "agent";
	// a list is answered in order, so a hook can report and then collect what's waiting in one request
	const many = Array.isArray(body);
	const replies = [];
	for (const msg of many ? body : [body]) {
		const reply = await answer(msg, house, who);
		if (reply) replies.push(reply);
	}
	if (!replies.length) return new Response(null, { status: 202 });
	return Response.json(many ? replies : replies[0]);
}

async function answer(msg, house, who) {
	if (!msg || typeof msg !== "object" || Array.isArray(msg)) return { jsonrpc: "2.0", id: null, error: { code: -32600, message: "invalid request" } };
	const { id, method } = msg;
	if (id === undefined || id === null) return null;   // a notification
	const ok = (result) => ({ jsonrpc: "2.0", id, result });
	const fail = (code, message) => ({ jsonrpc: "2.0", id, error: { code, message } });
	const params = msg.params || {};
	if (method === "initialize") {
		return ok({ protocolVersion: params.protocolVersion || "2025-06-18", capabilities: { tools: {} },
			serverInfo: { name: "catio", version: "0.3.0" }, instructions: INSTRUCTIONS });
	}
	if (method === "ping") return ok({});
	if (method === "tools/list") return ok({ tools: TOOLS });
	if (method === "tools/call") {
		if (!NAMES.has(params.name)) return fail(-32602, "unknown tool " + params.name);
		const r = await house.call(params.name, params.arguments || {}, who);
		if (r.error) return ok({ content: [{ type: "text", text: r.error }], isError: true });
		return ok({ content: [{ type: "text", text: JSON.stringify(r.ok) }], structuredContent: r.ok });
	}
	return fail(-32601, "method not found: " + method);
}
