// The KittyChat Café on the gateway's own address: what claude.ai gives the page as window.claude, made from the
// gateway (src/cafe.js). db: the café's documents, kept by the gateway and pushed live over a WebSocket; assets:
// the brain's files; mcp: the gateway's own tools, as Charlotte (what the CATIO connector reaches in claude.ai).
// Claude Code Remote and the sorter live in claude.ai only: here they answer "gateway_only".
(() => {
	"use strict";
	const GATEWAY = "CATIO";
	const HEADERS = { "Content-Type": "application/json", "X-Catio": "1" };
	async function send(method, url, body) {
		const r = await fetch(url, { method, headers: HEADERS, body: body === undefined ? undefined : JSON.stringify(body) });
		if (r.status === 401) { location.reload(); throw { code: "signed_out", message: "Signed out" }; }
		const j = await r.json().catch(() => ({}));
		if (!r.ok) throw { code: j.code || "unavailable", message: j.error || r.statusText };
		return j;
	}

	// the database: every document in memory, as the page reads them, kept in step by the gateway's pushes
	const store = {}, listeners = new Set();
	let loaded = false;
	const clone = (v) => (v === undefined ? undefined : JSON.parse(JSON.stringify(v)));
	const segs = (p) => p.split("/");
	const notify = () => { if (loaded) for (const l of listeners) l(); };
	const docSnap = (p) => ({ id: segs(p).pop(), exists: p in store, data: () => clone(store[p]) });
	const collSnap = (c) => {
		const docs = Object.keys(store).filter((p) => p.startsWith(c + "/") && segs(p).length === segs(c).length + 1).sort().map(docSnap);
		return { docs, size: docs.length, empty: !docs.length };
	};
	const listen = (fn) => { listeners.add(fn); if (loaded) setTimeout(fn, 0); return () => listeners.delete(fn); };
	const sync = () => send("GET", "/api/db").then((j) => {
		for (const p of Object.keys(store)) delete store[p];
		Object.assign(store, j.docs);
		loaded = true;
		notify();
	});
	const ready = sync();
	const newId = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
	const at = (p) => "/api/db/" + p.split("/").map(encodeURIComponent).join("/");
	const doc = (p) => ({
		path: p, id: segs(p).pop(),
		get: async () => { await ready; return docSnap(p); },
		set: async (d) => { await send("PUT", at(p), { data: d }); store[p] = clone(d); notify(); },
		update: async (d) => { await send("PATCH", at(p), { data: d }); store[p] = Object.assign(store[p] || {}, clone(d)); notify(); },
		delete: async () => { await send("DELETE", at(p)); delete store[p]; notify(); },
		onSnapshot: (cb) => listen(() => cb(docSnap(p))),
	});
	const db = { doc, collection: (c) => ({ path: c, doc: (id) => doc(c + "/" + (id || newId())), onSnapshot: (cb) => listen(() => cb(collSnap(c))) }) };

	// the live line: a change anywhere (another tab, a session's hook) reaches this café at once
	let opened = 0;
	function connect() {
		const ws = new WebSocket((location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws");
		ws.onopen = () => { if (opened++) sync().catch(() => {}); };   // back after a break: catch up on what it missed
		ws.onmessage = (e) => {
			let m;
			try { m = JSON.parse(e.data); } catch { return; }
			if (m.type === "doc") { if (m.data == null) delete store[m.path]; else store[m.path] = m.data; notify(); }
			else if (m.type === "agents") dispatchEvent(new Event("catio:agents"));
			else if (m.type === "queen") dispatchEvent(new CustomEvent("catio:queen", { detail: m }));   // the queen, mid-sentence or done
			else if (m.type === "reload") location.reload();
		};
		ws.onclose = () => setTimeout(connect, 3000 + Math.random() * 3000);
	}
	connect();

	const assets = {
		async upload(blob) {
			const r = await fetch("/api/files", { method: "POST", body: blob,
				headers: { "Content-Type": blob.type || "application/octet-stream", "X-Catio": "1", "X-Name": encodeURIComponent(blob.name || "file") } });
			const j = await r.json().catch(() => ({}));
			if (!r.ok) throw { code: j.code || "unavailable", message: j.error };
			return j;
		},
		delete: (id) => send("DELETE", "/api/files/" + encodeURIComponent(id)),
		list: async () => ({ assets: [], usage: {} }),
	};

	const gatewayOnly = (server) => ({ code: "gateway_only", message: "Only claude.ai can reach " + server + "." });
	const mcp = {
		async callTool(server, tool, input) {
			if (server !== GATEWAY) throw gatewayOnly(server);
			const payload = await send("POST", "/api/tools/" + encodeURIComponent(tool), input || {});
			return { payload, content: [{ type: "text", text: JSON.stringify(payload) }] };
		},
		watchTool(server, tool, input, handler) { setTimeout(() => handler({ type: "error", error: gatewayOnly(server) }), 0); return () => {}; },
		describeTool: async () => { throw { code: "not_found" }; },
		invalidate: async () => {},
	};
	const permissions = { request: async () => ({}), state: async () => "granted" };

	// the account's keys, for its sessions and agents (src/cafe.js, /api/keys): a new key is in make's answer once,
	// and the gateway keeps only its hash. Only the café on this address has these; claude.ai never does.
	const keys = {
		list: async () => (await send("GET", "/api/keys")).keys || [],
		make: (name) => send("POST", "/api/keys", { name }),
		drop: (name) => send("DELETE", "/api/keys/" + encodeURIComponent(name)),
	};

	window.claude = {
		catioGateway: true,
		keys,
		use: async (n) => (n === "db" ? db : n === "assets" ? assets : n === "mcp" ? mcp : n === "permissions" ? permissions : null),
	};
})();
