// The doors: what arrives from outside, made safe before it goes any further in. Plain JavaScript, so a test can
// import it outside workerd.
//
// Two things get through a JSON parser or an HTML form that later break something far away:
//
//   - a key named toString or valueOf. `String({toString: 1})` throws ("Cannot convert object to primitive value"),
//     and the gateway calls String() on almost everything it is given, so one such key in a tool's arguments, a
//     café document, a stored routine or a runner's say turned every one of those into a 500. plain() drops those
//     two keys, at every depth, as the body is parsed.
//   - a field of megabytes. A password of 32 MiB reached the Durable Object as one RPC argument, over its limit,
//     and the sign-in answered 500 before it ever looked at the handle. formOf() reads a form with a cap and
//     never holds more than that.
//
// Found by the audit of 5 October 2026 (docs/audit-2026-10-05.md).

const DEEP = 64;        // deeper than any café document; past it there is nothing to keep
export const FORM_CAP = 16 * 1024;

/** A copy of a parsed JSON value with every own toString and valueOf key dropped, so String() on it is safe. */
export function plain(v, depth = 0) {
	if (v === null || typeof v !== "object") return v;
	if (depth >= DEEP) return null;
	if (Array.isArray(v)) return v.map((x) => plain(x, depth + 1));
	const out = {};
	for (const [k, val] of Object.entries(v)) {
		if (k === "toString" || k === "valueOf") continue;
		out[k] = plain(val, depth + 1);
	}
	return out;
}

/** The parsed body of a JSON request, made plain: an object, or {} when it is anything else. */
export async function jsonOf(request) {
	const b = await request.json().catch(() => null);
	return b && typeof b === "object" && !Array.isArray(b) ? plain(b) : {};
}

/** The text of a request, up to `cap` bytes; null when it is longer, so nothing big is ever held whole. */
export async function textOf(request, cap = FORM_CAP) {
	const len = Number(request.headers.get("Content-Length"));
	if (Number.isFinite(len) && len > cap) return null;       // said its size: refused without reading a byte
	const reader = request.body && request.body.getReader();
	if (!reader) return "";
	const decoder = new TextDecoder();
	let out = "", size = 0;
	for (;;) {
		const { done, value } = await reader.read();
		if (done) break;
		size += value.byteLength;
		if (size > cap) {
			reader.cancel().catch(() => {});
			return null;
		}
		out += decoder.decode(value, { stream: true });
	}
	return out + decoder.decode();
}

/** An HTML form (urlencoded, as every form the gateway serves is), read with a cap. Null when it is too big or
 *  isn't a form: the caller answers "that wasn't the form" rather than failing. */
export async function formOf(request, cap = FORM_CAP) {
	const type = request.headers.get("Content-Type") || "";
	if (!/^application\/x-www-form-urlencoded\b/.test(type)) return null;
	const text = await textOf(request, cap);
	if (text === null) return null;
	try {
		return new URLSearchParams(text);
	} catch {
		return null;
	}
}
