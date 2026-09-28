// A faithful in-memory stand-in for the artifact runtime: db with live snapshots and the path grammar,
// and a Claude Code Remote feed the test can change mid-run. Test controls live on window.__catio.
(() => {
  const params = new URLSearchParams(location.search);
  const H = 3600e3, now = Date.now();
  const iso = (ago) => new Date(now - ago).toISOString();
  const src = (repo) => ({ sources: [{ git_repository: { url: "https://github.com/charredlatte/" + repo } }], outcomes: [{ git_repository: { git_info: { repo: "charredlatte/" + repo, branches: ["claude/test"] } } }] });
  const session = (id, title, repo, bucket, status, ago, pts) => ({ id: "session_" + id, title, session_status: "SESSION_STATUS_" + status, status_bucket: "SESSION_STATUS_BUCKET_" + bucket,
    updated_at: iso(ago), created_at: iso(ago + H), origin: "android", session_context: src(repo), post_turn_summary: pts || {} });

  const T = window.__catio = { writes: [], store: {}, handler: null, calls: 0, readOnly: false, session, now };
  const clone = (v) => JSON.parse(JSON.stringify(v));
  const segs = (p) => String(p).split("/");
  const checkColl = (p) => { if (segs(p).length % 2 !== 1) throw new TypeError("collection path needs an odd number of segments: " + p); };
  const checkDoc = (p) => { if (segs(p).length % 2 !== 0) throw new TypeError("document path needs an even number of segments: " + p); segs(p).forEach((s) => { if (!/^[A-Za-z0-9_\-.~:@+]{1,200}$/.test(s)) throw new TypeError("bad segment " + s); }); };
  const listeners = new Set();
  // the same rooms the published page is seeded with
  const SEED = {
  "garden":  { "name": "Catio",       "blurb": "This page and the portfolio",        "repos": ["Pretty-Project-Portfolio"] },
  "kitchen": { "name": "Kitchen",     "blurb": "Weekly meals and the Méré basket",   "repos": ["Intermarche-grocery-shopping-app", "intermarche-grocery-data"] },
  "dining":  { "name": "Dining room", "blurb": "Business plans, round the table",    "repos": [] },
  "living":  { "name": "Living room", "blurb": "New cats come in here",              "repos": [], "catchAll": true },
  "sunroom": { "name": "Sunroom",     "blurb": "TikTok saves, in the light",         "repos": ["tiktok-saves"] },
  "study":   { "name": "Craft room",  "blurb": "The Montfortoise shop",              "repos": ["montfortoise-shopify"] },
  "bedroom": { "name": "Bedroom",     "blurb": "Legal questions, kept quiet",        "repos": [] },
  "bath":    { "name": "Bathroom",    "blurb": "Spare",                              "repos": [] },
  "hall":    { "name": "Hall",        "blurb": "Snail mail, by the front door",      "repos": ["Snail-Mail-Trail"] }
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
  const mcp = Object.freeze({
    watchTool(server, tool, input, handler, opts) {
      T.calls++; T.watchArgs = { server, tool, input, opts }; T.handler = handler;
      const mode = params.get("mode");
      setTimeout(() => (mode === "noconn" ? T.fail("server_not_connected") : mode === "blocked" ? T.fail("blocked_by_policy") : T.push()), 30);
      return () => { if (T.handler === handler) T.handler = null; };
    },
    invalidate: async () => {},
  });
  const nodb = params.get("mode") === "nodb";
  window.claude = { use: async (n) => (n === "mcp" ? mcp : n === "db" ? (nodb ? null : db) : n === "permissions" ? { request: async () => ({}), state: async () => "granted" } : null) };
})();
