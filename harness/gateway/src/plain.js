// What a tool or a document is handed, made safe to read. JSON can give an object a toString of its own, which String()
// then can't call; nothing wants one, so it is dropped, at any depth. Past MAX_DEPTH what is nested is nothing anyone
// sends: it becomes null. Plain JavaScript, so a test can import it outside workerd.
const DROP = new Set(["toString", "valueOf"]);
const MAX_DEPTH = 24;

export function plain(v, depth = 0) {
	if (depth > MAX_DEPTH) return null;
	if (Array.isArray(v)) return v.map((x) => plain(x, depth + 1));
	if (v && typeof v === "object") return Object.fromEntries(Object.entries(v).filter(([k]) => !DROP.has(k)).map(([k, x]) => [k, plain(x, depth + 1)]));
	return v;
}
