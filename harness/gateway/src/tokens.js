// The café's design tokens as a design tokens file (the W3C format Figma's variables import and export): what
// The look's Export tokens and Import tokens… do in the page, here for the tools tokens and set_tokens, so a session
// with the Figma connector (or anything else) can bring a palette in or take it out without her clicking.
//
// One source of truth: the token table, the size ranges and the café's own values are read from the page itself
// (bundled as text, as the café is), never copied. toDTCG and fromDTCG follow the page's line for line; a check in
// harness/test feeds the same files to the page, skin.py, this and catio_mcp.py.
import PAGE from "../../../catio/index.html";

const between = (start, end) => {
	const a = PAGE.indexOf(start);
	return a < 0 ? "" : PAGE.slice(a, PAGE.indexOf(end, a));
};
// "--ink": ["Colours", "Ink", "Outlines and words."]: each entry's array is JSON as the page writes it
export const TOKENS = Object.fromEntries([...between("const TOKENS = {", "};").matchAll(/"(--[\w-]+)": (\[[^\]]*\])/g)].map(([, n, a]) => [n, JSON.parse(a)]));
const SIZES = JSON.parse((/const SIZES = (\{[^}]*\})/.exec(PAGE) || [, "{}"])[1]);
const WHOLE_PX = JSON.parse((/const WHOLE_PX = (\[[^\]]*\])/.exec(PAGE) || [, "[]"])[1]);
// the café's own values, as its :root sets them (the page's TOKENS0)
const ROOT = between(":root {", "color-scheme: light;");
export const DEFAULTS = Object.fromEntries([...ROOT.matchAll(/(--[\w-]+):\s*([^;]+);/g)].filter(([, n]) => TOKENS[n]).map(([, n, v]) => [n, v.trim()]));
export const MODES = ["light", "dark"];

function sizeOk(name, v) {
	const m = /^(\d{1,3}(?:\.\d{1,3})?)(px|rem)$/.exec(v), [lo, hi] = SIZES[name] || [0, 0];
	if (m && WHOLE_PX.includes(name) && (m[2] !== "px" || !Number.isInteger(+m[1]))) return false;
	return !!m && +m[1] * (m[2] === "rem" ? 16 : 1) >= lo && +m[1] * (m[2] === "rem" ? 16 : 1) <= hi;
}
const tokenOk = (name, v) => !!TOKENS[name] && typeof v === "string" && (TOKENS[name][0] === "Type" ? sizeOk(name, v) : /^#[0-9a-fA-F]{6}$/.test(v));
const cleanTokens = (t) => Object.fromEntries(Object.entries(t && typeof t === "object" ? t : {}).filter(([k, v]) => tokenOk(k, v)));
const groupKey = (g) => g.toLowerCase().replace(/[^a-z0-9]+/g, "-");
/** skin/theme as the page reads it: light, and dark (what differs) */
export const modeTokens = (doc) => ({ light: cleanTokens(doc && doc.tokens), dark: cleanTokens(doc && doc.dark) });
// a token's value in a mode: hers, else light's (dark says only what differs), else the café's
const valueIn = (t, m, n) => t[m][n] || t.light[n] || DEFAULTS[n];

/** The café's tokens in mode m as a design tokens file: the page's toDTCG. */
export function toDTCG(theme, m) {
	const t = modeTokens(theme);
	const out = { $description: "The KittyChat Café's design tokens, " + m + " mode. Import into Figma's variables as a mode, or into The look." };
	for (const [n, [g, name, what]] of Object.entries(TOKENS)) {
		const grp = out[groupKey(g)] || (out[groupKey(g)] = { $type: g === "Type" ? "dimension" : "color" });
		const v = valueIn(t, m, n), tk = { $description: name + (what ? ". " + what : "") };
		if (g === "Type") { const [, num, unit] = v.match(/^([\d.]+)(px|rem)$/) || [, "0", "px"]; tk.$value = { value: +num, unit }; }
		else { const h = v.toLowerCase(); tk.$value = { colorSpace: "srgb", components: [1, 3, 5].map((i) => +(parseInt(h.slice(i, i + 2), 16) / 255).toFixed(4)), hex: h }; }
		grp[n.slice(2)] = tk;
	}
	return out;
}

/** A design tokens file read for the café: the page's fromDTCG. found {--name: css}, foreign (not the café's) and
 * refused (the café's, with a value it can't take: see-through, out of range, an alias to nothing). */
export function fromDTCG(file) {
	const found = {}, flat = {};
	let foreign = 0;
	(function walk(node, path) {
		if (!node || typeof node !== "object") return;
		if ("$value" in node) { flat[path.join(".")] = node.$value; return; }
		for (const [k, v] of Object.entries(node)) if (!k.startsWith("$")) walk(v, path.concat(k));
	})(file, []);
	const resolve = (v, depth) => (typeof v === "string" && /^\{[^}]+\}$/.test(v) && depth < 10 ? resolve(flat[v.slice(1, -1)], depth + 1) : v);
	const own = {}, bad = new Set();
	for (const [path, v] of Object.entries(flat)) {
		const n = "--" + path.split(".").pop().trim().toLowerCase().replace(/[\s_]+/g, "-"), val = resolve(v, 0);
		if (!TOKENS[n]) { foreign++; continue; }
		const hex = typeof val === "string" ? val : val && typeof val.hex === "string" ? val.hex : "";
		const clear = /^#[0-9a-f]{6}(?!ff)[0-9a-f]{2}$/i.test(hex) || (val && typeof val === "object" && typeof val.alpha === "number" && val.alpha < 1);
		let css = null;
		if (typeof val === "string") css = /^#[0-9a-f]{6}([0-9a-f]{2})?$/i.test(val) ? val.slice(0, 7) : val;
		else if (val && typeof val.hex === "string") css = val.hex.slice(0, 7);
		else if (val && Array.isArray(val.components) && (val.colorSpace || "srgb") === "srgb") css = "#" + val.components.slice(0, 3).map((c) => Math.round(Math.min(1, Math.max(0, c)) * 255).toString(16).padStart(2, "0")).join("");
		else if (val && typeof val.value === "number" && /^(px|rem)$/.test(val.unit)) css = String(+val.value.toFixed(3)) + val.unit;
		else if (typeof val === "number" && TOKENS[n][0] === "Type") css = String(+val.toFixed(3)) + "px";
		if (clear || !tokenOk(n, css)) { bad.add(n); continue; }
		const mine = path.split(".")[0] === groupKey(TOKENS[n][0]);
		if (n in found && (own[n] || !mine)) continue;
		found[n] = css; own[n] = mine;
	}
	return { found, foreign, refused: [...bad].filter((n) => !(n in found)).length };
}

/** A file brought into mode m of skin/theme, as The look's Import tokens… does: its tokens over hers (or, with
 * replace, instead of hers in that mode), and any value the same as it would be anyway taken out rather than kept.
 * Returns the theme to keep (null: none left) and what to tell. */
export function importInto(theme, m, file, replace = false) {
	const { found, foreign, refused } = fromDTCG(file);
	const was = modeTokens(theme), next = { light: { ...was.light }, dark: { ...was.dark } };
	const changed = Object.entries(found).filter(([n, v]) => v.toLowerCase() !== String(valueIn(was, m, n)).toLowerCase()).length;
	next[m] = replace ? { ...found } : { ...next[m], ...found };
	// what the file touched, and of that, the same as it would be anyway (light's own is the café's, dark's is light's):
	// taken out rather than kept, as The look's editTokens does with an import
	const anyway = (n) => (m === "dark" ? next.light[n] || DEFAULTS[n] : DEFAULTS[n]);
	for (const [n, v] of Object.entries(next[m])) if (v !== was[m][n] && v.toLowerCase() === String(anyway(n)).toLowerCase()) delete next[m][n];
	const empty = !Object.keys(next.light).length && !Object.keys(next.dark).length;
	return { theme: empty ? null : { tokens: next.light, dark: next.dark, at: Date.now() }, report: { mode: m, tokens: Object.keys(found).length, changed, foreign, refused } };
}
