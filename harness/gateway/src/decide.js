// One typed decision: a state (text or JSON) and named typed questions in, one typed answer each out, no prose.
// What an answer carries, per type, which is the whole contract every caller reads:
//   - noul:   {type, noul}                           noul is the probability of yes, 0 to 1;
//   - choice: {type, choice, probabilities, confidence}   the option picked, and a probability for each option;
//   - score:  {type, score, confidence}              score is the probability-weighted level, a number on the
//             criteria's own scale (0 to criteria.length - 1). There is no probability per level.
// So "a probability for every allowed answer" holds for noul and choice only; a score is a number and a confidence.
// verdict() reads the one-word answer and confidence() how sure it is, whichever type it was.
// Every question carries its words in `instructions`, and is refused by name without them (see shape()).
//
// Any model can answer, in one of two shapes, and decide() uses whichever the answerer speaks:
//   - System One: the model takes {state, questions} itself and returns the answers above. Cloudflare's Clef through
//     the Worker's AI binding (free plan, open weights) by default, TypeSafe's Jev ("typesafe/jev", paid from AI
//     Gateway credits), or any server at DECIDE_URL speaking POST /v1/systemone (laya-serve on her PC, or Jev direct).
//   - Any other model: ask() turns the same questions into one prompt and read() reads the answers back out of
//     whatever JSON it replies with, into the same shape. A chat or instruct model through the AI binding, or an
//     OpenAI-compatible POST /v1/chat/completions at DECIDE_URL (Ollama, llama.cpp, a hosted API).
// The shape is chosen from the model's id and the other is tried if the first is refused, so a model nobody has
// named here still answers. The result says which answered, as `via`, because a chat model's parsed JSON is weaker
// evidence than a System One model's own probabilities and the decisions/ log is read to decide whether to trust it.
// The caller keeps the judgement: it sets its own confidence floor and falls back to what it did before.
export const DEFAULT_MODEL = "@cf/cloudflare/clef-flash";
export const SYSTEM_ONE = /^(?:@cf\/cloudflare\/clef|typesafe\/jev)/;   // the ids known to take questions themselves
const TYPES = ["noul", "choice", "score"];
const MAX_STATE = 60000;      // characters of state (Clef takes 64K tokens, Jev 32K, Laya 1K to 8K)
const MAX_QUESTIONS = 64;     // Clef's cap; Jev's is higher, Laya's budget smaller
const MAX_OPTIONS = 64;
const TIMEOUT = 8000;         // one budget for both tries, so a caller waits what the README says and no longer
// A yes, no or option a model stated without a confidence of its own. Enough to keep the answer it gave, and under
// every floor the café uses (0.6), so an answer nobody put a number on never clears a floor by itself.
const UNSAID = 0.55;

// Named question sets the café asks often, so the page, the queen and the hooks ask the same thing.
export const PRESETS = {
	// "Is this task easy?": the rubric of docs/delegation.md as six yes/no questions about a task's text. Easy means
	// all six come back the right way; the caller decides the floor.
	easy: {
		spelled_out: { type: "noul", instructions: "Does the task name exactly what to produce or change (a file, a test, an output), with no design judgement left open?" },
		checkable: { type: "noul", instructions: "Would a test, a build or a diff show whether the task is done?" },
		small: { type: "noul", instructions: "Is the task confined to one file, or read-only across several?" },
		held_path: { type: "noul", instructions: "Does the task touch harness/, .claude/, .github/ (the workflows), the house rules, merging, pushing, or a default branch?" },
		private: { type: "noul", instructions: "Does the task involve legal, money, health or other private personal matters?" },
		browser: { type: "noul", instructions: "Does the task need a web browser, a login, or a key?" },
	},
};

export class BadQuestion extends Error {}
export class NoAnswer extends Error {}

// What a caller is likely to have called the question's text instead. The field is `instructions` and only that: the
// schema says so, a System One model's own API names it, and a question carrying anything else is refused rather than
// guessed at. These are only so that the refusal can name the mistake, which is the difference between a caller
// fixing its call in one go and guessing a second time.
const NEARLY = ["instruction", "question", "prompt", "ask", "description", "text", "q"];

/** The request body, checked and trimmed: {state, questions}. Throws BadQuestion. */
export function shape(args) {
	let questions = args.preset ? PRESETS[args.preset] : args.questions;
	if (args.preset && !questions) throw new BadQuestion("preset is one of " + Object.keys(PRESETS).join(", "));
	if (!questions || typeof questions !== "object" || Array.isArray(questions)) throw new BadQuestion("questions is an object of named typed questions");
	const names = Object.keys(questions);
	if (!names.length || names.length > MAX_QUESTIONS) throw new BadQuestion("1 to " + MAX_QUESTIONS + " questions");
	const out = {};
	for (const name of names) {
		const q = questions[name];
		if (!q || typeof q !== "object" || !TYPES.includes(q.type)) throw new BadQuestion(name + ": type is noul, choice or score");
		const clean = { type: q.type };
		// Every question needs its words. Clef answers one without them by refusing the whole body -- "required
		// properties at '/' are 'model,state,questions'", which names the root and never the question that is short
		// -- so a mis-keyed question read as a decider outage for two days (21 October 2026). Name it here instead,
		// and name the key it was written under when that is what went wrong.
		if (q.instructions == null || !String(q.instructions).trim()) {
			const near = NEARLY.find((k) => q[k] != null && String(q[k]).trim());
			throw new BadQuestion(name + ": instructions is the question in words" + (near ? ', not "' + near + '"' : ""));
		}
		clean.instructions = String(q.instructions).slice(0, 1000);
		if (q.type === "choice") {
			const c = q.criteria && typeof q.criteria === "object" && !Array.isArray(q.criteria) ? q.criteria : null;
			if (!c || Object.keys(c).length < 2 || Object.keys(c).length > MAX_OPTIONS) throw new BadQuestion(name + ": a choice needs criteria, 2 to " + MAX_OPTIONS + " named options");
			clean.criteria = Object.fromEntries(Object.entries(c).map(([k, v]) => [String(k).slice(0, 100), String(v).slice(0, 500)]));
		} else if (q.type === "score") {
			if (!Array.isArray(q.criteria) || q.criteria.length < 2 || q.criteria.length > MAX_OPTIONS) throw new BadQuestion(name + ": a score needs criteria, an ordered list of 2 or more levels");
			clean.criteria = q.criteria.map((v) => String(v).slice(0, 500));
		} else if (q.criteria && typeof q.criteria === "object") {
			clean.criteria = { true: String(q.criteria.true ?? "yes").slice(0, 500), false: String(q.criteria.false ?? "no").slice(0, 500) };
		}
		out[name] = clean;
	}
	const state = args.state;
	if (state == null || (typeof state !== "string" && typeof state !== "object")) throw new BadQuestion("state is the text or JSON the questions are about");
	const text = typeof state === "string" ? state : JSON.stringify(state);
	if (!text.trim()) throw new BadQuestion("state is empty");
	if (text.length > MAX_STATE) throw new BadQuestion("state is over " + MAX_STATE + " characters");
	return { state, questions: out };
}

/**
 * Ask the model. Returns {model, answers, usage, via}, via being "systemone" or "chat": which shape answered.
 * Throws NoAnswer when nothing can answer, so the caller falls back to what it did before.
 */
export async function decide(env, args) {
	const body = shape(args);
	const model = String(args.model || env.DECIDE_MODEL || DEFAULT_MODEL);
	// Whether this id was chosen rather than defaulted. DEFAULT_MODEL is a Workers AI id, which means nothing to a
	// server of hers, so it is never sent to DECIDE_URL; a caller's model, or DECIDE_MODEL, is what that server was
	// set up for and is sent, because one that requires the field would otherwise refuse every default call.
	const named = !!(args.model || env.DECIDE_MODEL);
	if (!env.DECIDE_URL && !env.AI) throw new NoAnswer("no decider: the Worker has no AI binding and no DECIDE_URL");
	// the shape this model is known to speak first, then the other: an id nobody listed here still gets its answer,
	// and a DECIDE_URL swapped from a System One server to a chat endpoint keeps working without a setting
	const ways = SYSTEM_ONE.test(model) ? ["systemone", "chat"] : ["chat", "systemone"];
	const until = Date.now() + TIMEOUT;
	let last = null;
	for (const way of ways) {
		const left = until - Date.now();
		if (left < 500) break;      // not enough of the budget left to be worth a round trip
		try {
			const out = way === "systemone"
				? await systemOne(env, model, body, left, named)
				: await chat(env, model, body, left, named);
			if (Object.keys(out.answers).length) return { ...out, via: way };
			last = new NoAnswer("the decider answered nothing readable");
		} catch (e) {
			last = e instanceof NoAnswer ? e : new NoAnswer("the decider failed: " + (e && e.message ? e.message : e));
		}
	}
	throw last || new NoAnswer("the decider didn't answer");
}

/**
 * A model that takes the questions itself and answers them. `named` is whether this model was chosen (by the caller
 * or by DECIDE_MODEL) rather than defaulted: only then is it put in a DECIDE_URL body, because the default is a
 * Workers AI id that means nothing to a server of hers, and being told another model's id is how one comes to
 * refuse. The AI binding takes the id on the call instead, never from the body.
 */
async function systemOne(env, model, body, ms, named) {
	// Clef wants its short name in the body too; Jev and the rest take the id on the call alone
	const cf = /^@cf\/cloudflare\/(clef[a-z-]*)$/.exec(model);
	const r = env.DECIDE_URL
		? await post(env, "/v1/systemone", named ? { ...body, model } : body, ms)
		: await budget(env.AI.run(model, { ...(cf ? { model: cf[1] } : {}), ...body }), ms);
	if (!r || !r.answers || typeof r.answers !== "object" || Array.isArray(r.answers)) throw new NoAnswer("the decider answered without answers");
	return { model: String(r.model || model), answers: r.answers, usage: r.usage || null };
}

/**
 * Any other model: the questions as one prompt, the answers read back out of its reply. No response_format or
 * json_schema is sent, because which models accept one is per-model knowledge and the point here is to need none;
 * read() is tolerant instead, and a reply it can't read is a NoAnswer the caller falls back from.
 */
async function chat(env, model, body, ms, named) {
	const messages = [{ role: "user", content: ask(body) }];
	const sent = { messages, temperature: 0 };
	const r = env.DECIDE_URL
		// an OpenAI-compatible server usually wants a model named; one of hers serving a single model does not, and
		// being told the id of another is how it comes to refuse, so it is sent only when the caller asked for it
		? await post(env, "/v1/chat/completions", named ? { ...sent, model } : sent, ms)
		: await budget(env.AI.run(model, sent), ms);
	const choice = r && r.choices && r.choices[0] && r.choices[0].message ? r.choices[0].message.content : null;
	const text = r && r.response != null ? r.response : choice;   // Workers AI says response, an OpenAI API choices
	if (text == null) throw new NoAnswer("the decider answered no text");
	return { model, answers: read(text, body.questions), usage: (r && r.usage) || null };
}

/** The same questions as one prompt, for a model that doesn't take them itself. Pure, so a test can read it. */
export function ask({ state, questions }) {
	const asked = [], wanted = [];
	for (const [name, q] of Object.entries(questions)) {
		if (q.type === "noul") {
			asked.push("- " + name + ": " + q.instructions + " Answer yes or no.");
			wanted.push(JSON.stringify(name) + ': {"answer": "yes" or "no", "confidence": 0 to 1}');
		} else if (q.type === "choice") {
			const keys = Object.keys(q.criteria);
			asked.push("- " + name + ": " + q.instructions + " Answer with one of "
				+ Object.entries(q.criteria).map(([k, v]) => k + " (" + v + ")").join(", ") + ".");
			wanted.push(JSON.stringify(name) + ': {"answer": one of ' + keys.map((k) => JSON.stringify(k)).join(" | ") + ', "confidence": 0 to 1}');
		} else {
			const top = q.criteria.length - 1;
			asked.push("- " + name + ": " + q.instructions + " Answer with a whole number from 0 to " + top
				+ ", where " + q.criteria.map((v, i) => i + " is " + v).join(", ") + ".");
			wanted.push(JSON.stringify(name) + ': {"answer": 0 to ' + top + ', "confidence": 0 to 1}');
		}
	}
	return [
		"Answer every question about the state below. Reply with one JSON object and nothing else: no prose, no",
		"explanation, no code fence.",
		"Give each answer a confidence, from 0 (a coin toss) to 1 (certain): how sure you are of that answer. An",
		"answer with no confidence is read as barely better than a coin toss, so say one.",
		"",
		"STATE:",
		typeof state === "string" ? state : JSON.stringify(state),
		"",
		"QUESTIONS:",
		...asked,
		"",
		"Reply with exactly:",
		"{" + wanted.join(", ") + "}",
	].join("\n");
}

/**
 * The answers read back out of a model's reply, in the same shape a System One model returns. Pure, so a test can
 * feed it what a model really said. A question it can't read is left out rather than guessed, and decide() treats
 * a reply with nothing readable in it as no answer at all.
 */
export function read(text, questions) {
	const said = firstJson(String(text == null ? "" : text));
	const answers = {};
	if (!said) return answers;
	for (const [name, q] of Object.entries(questions)) {
		const a = answer(said[name], q);
		if (a) answers[name] = a;
	}
	return answers;
}

const num = (v) => {
	// a blank string is no number: Number("") is 0, which would read an empty answer as a confident no
	if (typeof v === "string" && !v.trim()) return null;
	const n = typeof v === "number" ? v : typeof v === "string" ? Number(v.trim().replace(/%$/, "")) : NaN;
	if (!Number.isFinite(n)) return null;
	return typeof v === "string" && /%\s*$/.test(v) ? n / 100 : n;
};
// yes or no as a model writes it; a number is left to be read as a probability instead
const truth = (v) => typeof v === "boolean" ? v
	: typeof v !== "string" ? null
		: /^(y|yes|true|t)$/i.test(v.trim()) ? true : /^(n|no|false|f)$/i.test(v.trim()) ? false : null;
const clamp = (n) => Math.min(1, Math.max(0, n));
// to four decimals, as a System One model's own probabilities come back, so a decision reads the same in the
// decisions/ log whichever shape answered and 1 - 0.9 is not written down as 0.09999999999999998
const r4 = (n) => Math.round(n * 1e4) / 1e4;
// A yes or no the model stated, with its confidence, as the single probability noul carries. A confidence below a
// coin toss would flip the answer it was given for, so it is held at the toss: the answer the model stated survives
// and confidence() reads about 0.5, under every floor the café uses.
const prob = (yes, c) => r4(yes ? Math.max(0.5, clamp(c)) : Math.min(0.49, 1 - clamp(c)));

/** One answer, from whatever the model put under the question's name. */
function answer(v, q) {
	if (v == null) return null;
	const said = typeof v === "object" && !Array.isArray(v) ? v : { answer: v };
	const got = [said.answer, said.value, said.choice, said.score, said.noul, said.level].find((x) => x != null);
	if (got == null) return null;
	const c = num(said.confidence);
	const sure = c == null ? UNSAID : clamp(c);
	if (q.type === "noul") {
		const yes = truth(got);
		if (yes !== null) return { type: "noul", noul: prob(yes, sure) };
		const n = num(got);                                  // a bare probability in place of a yes or no
		return n == null || n < 0 || n > 1 ? null : { type: "noul", noul: r4(n) };
	}
	if (q.type === "choice") {
		const keys = Object.keys(q.criteria);
		const pick = keys.find((k) => k.toLowerCase() === String(got).trim().toLowerCase());
		if (!pick) return null;                              // not one of the options: unanswered, not guessed
		// what is left of the certainty, shared evenly: the model named one option, not a distribution
		const each = (1 - sure) / Math.max(1, keys.length - 1);
		return { type: "choice", choice: pick, confidence: r4(sure),
			probabilities: Object.fromEntries(keys.map((k) => [k, r4(k === pick ? sure : each)])) };
	}
	const top = q.criteria.length - 1;
	let n = num(got);
	if (n == null) {                                         // a level by name rather than by number
		const i = q.criteria.findIndex((v2) => v2.toLowerCase() === String(got).trim().toLowerCase());
		if (i < 0) return null;
		n = i;
	}
	return { type: "score", score: r4(Math.min(top, Math.max(0, n))), confidence: r4(sure) };
}

/** The first balanced JSON object in a reply, whatever prose or code fence surrounds it. */
function firstJson(text) {
	for (let i = text.indexOf("{"); i >= 0; i = text.indexOf("{", i + 1)) {
		let depth = 0, inStr = false, esc = false;
		for (let j = i; j < text.length; j++) {
			const ch = text[j];
			if (esc) { esc = false; continue; }
			if (inStr) { if (ch === "\\") esc = true; else if (ch === '"') inStr = false; continue; }
			if (ch === '"') inStr = true;
			else if (ch === "{") depth++;
			else if (ch === "}" && --depth === 0) {
				try {
					const v = JSON.parse(text.slice(i, j + 1));
					if (v && typeof v === "object" && !Array.isArray(v)) return v;
				} catch { /* prose that merely looks like an object: try the next { */ }
				break;
			}
		}
	}
	return null;
}

/** A promise given only so much of the budget: for env.AI.run, which takes no abort signal of its own. */
function budget(p, ms) {
	let timer;
	const late = new Promise((_, no) => { timer = setTimeout(() => no(new NoAnswer("the decider didn't answer in " + Math.round(ms / 1000) + " s")), ms); });
	late.catch(() => {});   // the race hears it; nobody else need
	return Promise.race([p, late]).finally(() => clearTimeout(timer));
}

/** One POST to DECIDE_URL, with its key if it has one. The abort signal is the budget: no second timer needed. */
async function post(env, path, body, ms) {
	let res;
	try {
		res = await fetch(String(env.DECIDE_URL).replace(/\/+$/, "") + path, {
			method: "POST", signal: AbortSignal.timeout(ms),
			headers: { "Content-Type": "application/json", ...(env.DECIDE_KEY ? { Authorization: "Bearer " + env.DECIDE_KEY } : {}) },
			body: JSON.stringify(body),
		});
	} catch (e) {
		throw new NoAnswer(e && e.name === "TimeoutError"
			? "the decider didn't answer in " + Math.round(ms / 1000) + " s"
			: "the decider failed: " + (e && e.message ? e.message : e));
	}
	if (!res.ok) throw new NoAnswer("the decider said " + res.status);
	return res.json();
}

/** The one-word reading of an answer the log keeps: a choice's option, a noul's yes/no, a score's level. */
export function verdict(a) {
	if (!a || typeof a !== "object") return null;
	if (a.type === "choice" || a.choice != null) return a.choice ?? null;
	if (a.type === "noul" || typeof a.noul === "number") return a.noul >= 0.5 ? "yes" : "no";
	if (typeof a.score === "number") return String(Math.round(a.score));
	return null;
}

/** How sure an answer is: a choice's or a score's confidence, a noul's distance from a coin toss. */
export function confidence(a) {
	if (!a || typeof a !== "object") return 0;
	if (typeof a.confidence === "number") return a.confidence;
	if (typeof a.noul === "number") return Math.max(a.noul, 1 - a.noul);
	return 0;
}
