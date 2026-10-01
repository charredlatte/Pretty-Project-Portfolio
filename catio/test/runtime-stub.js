// A faithful in-memory stand-in for the artifact runtime: db with live snapshots and the path grammar,
// and a Claude Code Remote feed the test can change mid-run. Test controls live on window.__catio.
(() => {
  const params = new URLSearchParams(location.search);
  const H = 3600e3, now = Date.now();
  const iso = (ago) => new Date(now - ago).toISOString();
  const src = (repo) => ({ sources: [{ git_repository: { url: "https://github.com/charredlatte/" + repo } }], outcomes: [{ git_repository: { git_info: { repo: "charredlatte/" + repo, branches: ["claude/test"] } } }] });
  const session = (id, title, repo, bucket, status, ago, pts) => ({ id: "session_" + id, title, session_status: "SESSION_STATUS_" + status, status_bucket: "SESSION_STATUS_BUCKET_" + bucket,
    updated_at: iso(ago), created_at: iso(ago + H), origin: "android", session_context: Object.assign(src(repo), { model: "claude-opus-5-5" }), post_turn_summary: pts || {},
    environment_id: "env_test", configured_model: "claude-opus-5-5" });

  const T = window.__catio = { writes: [], store: {}, handler: null, calls: 0, readOnly: false, session, now };
  const clone = (v) => JSON.parse(JSON.stringify(v));
  const segs = (p) => String(p).split("/");
  const checkColl = (p) => { if (segs(p).length % 2 !== 1) throw new TypeError("collection path needs an odd number of segments: " + p); };
  const checkDoc = (p) => { if (segs(p).length % 2 !== 0) throw new TypeError("document path needs an even number of segments: " + p); segs(p).forEach((s) => { if (!/^[A-Za-z0-9_\-.~:@+]{1,200}$/.test(s)) throw new TypeError("bad segment " + s); }); };
  const listeners = new Set();
  // the same rooms the published page is seeded with
  const SEED = {
  "garden":  { "name": "Catio",       "blurb": "This page and the portfolio",        "repos": ["Pretty-Project-Portfolio"] },
  "kitchen": { "name": "Kitchen",     "blurb": "Weekly meals and the Méré basket",   "repos": ["Intermarche-grocery-shopping-app"] },
  "dining":  { "name": "Café",        "blurb": "Business plans, round the table",    "repos": [] },
  "living":  { "name": "Cat lounge",  "blurb": "New cats come in here",              "repos": [], "catchAll": true },
  "sunroom": { "name": "Terrace",     "blurb": "TikTok saves, in the light",         "repos": ["tiktok-saves"] },
  "study":   { "name": "Craft room",  "blurb": "The Montfortoise shop",              "repos": ["montfortoise-shopify"] },
  "bedroom": { "name": "Bedroom",     "blurb": "Legal questions, kept quiet",        "repos": [] },
  "bath":    { "name": "Ensuite",     "blurb": "Spare",                              "repos": [] },
  "hall":    { "name": "Entrance hall", "blurb": "Snail mail, by the front door",      "repos": ["Snail-Mail-Trail"] },
  "brain":   { "name": "Library",     "blurb": "The brain",                          "repos": [] }
};
  if (params.get("mode") !== "empty") for (const [k, v] of Object.entries(SEED)) T.store["rooms/" + k] = v;
  // Claude's saved copy of the sessions, as written after a publish, for when the live read is blocked
  T.seedCopy = () => { T.store["snapshot/sessions"] = { at: Date.now() - 3600e3, sessions: clone(T.sessions) }; };
  const snapOf = (coll) => {
    const docs = Object.keys(T.store).filter((p) => p.startsWith(coll + "/") && segs(p).length === segs(coll).length + 1).sort()
      .map((p) => Object.freeze({ id: segs(p).pop(), exists: true, data: () => Object.freeze(clone(T.store[p])), metadata: { fromCache: false, hasPendingWrites: false } }));
    return { docs, size: docs.length, empty: !docs.length, docChanges: () => [], metadata: { fromCache: false, hasPendingWrites: false } };
  };
  const notify = (path) => { const coll = segs(path).slice(0, -1).join("/"); for (const l of listeners) if (l.coll === coll) setTimeout(() => l.cb(snapOf(coll)), 5); };
  const refuse = () => { if (T.readOnly) throw { code: "invalid_argument", message: "not allowed" }; };
  let auto = 0;
  const docRef = (path) => {
    checkDoc(path);
    return {
      path, id: segs(path).pop(),
      get: async () => ({ id: segs(path).pop(), exists: path in T.store, data: () => T.store[path] && clone(T.store[path]) }),
      set: async (d) => { refuse(); T.store[path] = clone(d); T.writes.push(["set", path, clone(d)]); notify(path); },
      update: async (d) => { refuse(); if (!(path in T.store)) throw { code: "invalid_argument", message: "no such document" }; Object.assign(T.store[path], clone(d)); T.writes.push(["update", path, clone(d)]); notify(path); },
      delete: async () => { refuse(); delete T.store[path]; T.writes.push(["delete", path]); notify(path); },
      onSnapshot: (cb) => {
        const coll = segs(path).slice(0, -1).join("/");
        const deliver = () => cb({ id: segs(path).pop(), exists: path in T.store, data: () => T.store[path] && clone(T.store[path]), metadata: { fromCache: false, hasPendingWrites: false } });
        const l = { coll, cb: deliver };
        listeners.add(l); setTimeout(deliver, 5); return () => listeners.delete(l);
      },
    };
  };
  const collRef = (coll) => {
    checkColl(coll);
    const q = {
      path: coll,
      doc: (id) => docRef(coll + "/" + (id || "gen" + (++auto) + "x" + Math.random().toString(36).slice(2, 8))),
      add: async (d) => { const r = q.doc(); await r.set(d); return r; },
      onSnapshot: (cb, err) => { const l = { coll, cb }; listeners.add(l); setTimeout(() => cb(snapOf(coll)), 5); return () => listeners.delete(l); },
      where: () => q, orderBy: () => q, limit: () => q, get: async () => snapOf(coll),
    };
    return q;
  };
  const db = Object.freeze({ doc: docRef, collection: collRef });
  T.put = (path, d) => { T.store[path] = clone(d); notify(path); };   // someone else wrote it: a session's reply, Claude's seed

  T.sessions = [
    session("blocked1", "Shop about page", "montfortoise-shopify", "BLOCKED", "IDLE", 2 * H, { status_category: "need_input", needs_action: "review the French text" }),
    session("work1", "Week tab editing", "Intermarche-grocery-shopping-app", "WORKING", "RUNNING", 60e3, {}),
    session("old1", "Old parser", "Intermarche-grocery-shopping-app", "COMPLETED", "IDLE", 20 * 24 * H, { status_category: "completed" }),
  ];
  if (params.get("mode") === "blocked") T.seedCopy();
  T.push = () => { if (T.handler) T.handler({ type: "data", result: { payload: { data: clone(T.sessions), has_more: false } } }); };
  T.fail = (code) => { if (T.handler) T.handler({ type: "error", error: { code, message: code } }); };
  T.setBucket = (id, bucket, status, pts) => {
    const s = T.sessions.find((x) => x.id === "session_" + id);
    s.status_bucket = "SESSION_STATUS_BUCKET_" + bucket; s.session_status = "SESSION_STATUS_" + status; s.post_turn_summary = pts || {}; s.updated_at = new Date().toISOString();
    T.push();
  };
  const mcp = ({
    watchTool(server, tool, input, handler, opts) {
      T.calls++; T.watchArgs = { server, tool, input, opts }; T.handler = handler;
      const mode = params.get("mode");
      setTimeout(() => (mode === "noconn" ? T.fail("server_not_connected") : mode === "blocked" ? T.fail("blocked_by_policy") : T.push()), 30);
      return () => { if (T.handler === handler) T.handler = null; };
    },
    invalidate: async () => {},
  });
  // Write tools: every call is recorded in T.tools. ?writes=refused refuses them all the way claude.ai
  // does when a page may not use them; ?host=none has no Catio server on this device.
  T.tools = []; T.triggers = 0; T.goneTriggers = new Set();
  T.agents = params.get("agents") !== "1" ? [] : [{ id: "codex-shop", name: "Codex", provider: "openai", model: "gpt-5", mood: "needs", ask: "Which colour for the buttons?", title: "Shop theme", repo: "charredlatte/montfortoise-shopify", updated: now - 60e3, wakes: true }];
  const answer = (payload) => Promise.resolve({ content: [{ type: "text", text: JSON.stringify(payload) }], payload });
  const ccr = {
    create_trigger: (i) => ({ trigger: { id: "trig_" + (++T.triggers), name: i.name } }),
    fire_trigger: (i) => { if (T.goneTriggers.has(i.trigger_id)) throw { code: "tool_error", message: "trigger not found" }; return { ok: true }; },
    delete_trigger: () => ({ ok: true }), create_session: () => ({ id: "session_new1", status: "starting" }),
    // ?send=ok posts; ?send=error fails the way a tool can; by default the page may not call it
    send_message: () => { const v = params.get("send"); if (v === "ok") return { ok: true }; throw v === "error" ? { code: "tool_error", message: "session is archived" } : { code: "not_in_manifest", message: "send_message isn't declared" }; },
    set_session_title: () => ({ ok: true }), archive_session: () => ({ ok: true }), unarchive_session: () => ({ ok: true }), interrupt_session: () => ({ ok: true }),
  };
  // send_message's schema: ?sendschema=text names its message "text"; ?sendschema=none has none to read
  mcp.describeTool = async (server, tool) => {
    const v = params.get("sendschema");
    if (v === "none" || tool !== "send_message") throw { code: "not_found", message: "no schema" };
    return { name: tool, inputSchema: { type: "object", properties: { session_id: { type: "string" }, [v === "text" ? "text" : "message"]: { type: "string" } } } };
  };
  mcp.callTool = async (server, tool, input) => {
    T.tools.push([server, tool, clone(input || {})]);
    if (server === "host:catio") {
      if (params.get("host") === "none") throw { code: "server_not_connected", message: "no host" };
      if (tool === "list_agents") return answer({ agents: clone(T.agents) });
      return answer({ id: "x" + T.tools.length, ok: true, woke: true });
    }
    if (params.get("writes") === "refused") throw { code: "approval_required", message: "ask every time" };
    if (!ccr[tool]) throw { code: "bad_request", message: "not in the manifest: " + tool };
    return answer(ccr[tool](input || {}));
  };
  // assets: kept in memory; sample: answers with T.sampleAnswer, recording each prompt
  T.uploads = []; T.assetsDeleted = [];
  const assets = { upload: async (blob) => { const id = "a" + (T.uploads.length + 1) + "0123456789abcdef0123456789abcd".slice(0, 30); T.uploads.push({ id, name: blob.name, size: blob.size, type: blob.type }); return { id, url: "/_blob/" + id, sizeBytes: blob.size, contentType: blob.type }; },
    delete: async (id) => { T.assetsDeleted.push(id); return { deleted: true }; }, list: async () => ({ assets: [], usage: {} }) };
  T.prompts = []; T.sampleAnswer = { cat: null, reason: "nothing fits" };
  const sample = async (input) => { T.prompts.push(input); return { text: JSON.stringify(T.sampleAnswer), truncated: false }; };
  sample.json = async (input) => { T.prompts.push(input); if (T.sampleHang) return new Promise(() => {}); return clone(T.sampleAnswer); };   // sampleHang: a sorter that never answers
  const nodb = params.get("mode") === "nodb";
  window.claude = { use: async (n) => (n === "mcp" ? mcp : n === "db" ? (nodb ? null : db) : n === "assets" ? (nodb ? null : assets) : n === "sample" ? sample
    : n === "permissions" ? { request: async () => ({}), state: async () => "granted" } : null) };
})();
