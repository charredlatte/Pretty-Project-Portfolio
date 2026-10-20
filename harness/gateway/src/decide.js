// One typed decision, as a System One model gives it: a state (text or JSON) and a schema of typed questions in,
// a probability for every allowed answer out, no prose. Two places can answer, behind one switch:
//   - Workers AI, through the Worker's AI binding: Cloudflare's own Clef (free plan, open weights) by default, or
//     TypeSafe's Jev itself ("typesafe/jev", paid from AI Gateway credits), the model id being the only difference;
//   - DECIDE_URL, any server speaking the System One API (POST /v1/systemone): laya-serve on her PC, or Jev direct.
// The caller keeps the judgement: it sets its own confidence floor and falls back to what it did before.
export const DEFAULT_MODEL = "@cf/cloudflare/clef-flash";
export const TYPES = ["noul", "choice", "score"];
const MAX_STATE = 60000;      // characters of state (Clef takes 64K tokens, Jev 32K, Laya 1K to 8K)
const MAX_QUESTIONS = 64;     // Clef's cap; Jev's is higher, Laya's budget smaller
const MAX_OPTIONS = 64;
const TIMEOUT = 8000;

// Named question sets the café asks often, so the page, the queen and the hooks ask the same thing.
export const PRESETS = {
	// "Is this task easy?": the rubric of docs/delegation.md as six yes/no questions about a task's text. Easy means
	// all six come back the right way; the caller decides the floor.
	easy: {
		spelled_out: { type: "noul", instructions: "Does the task name exactly what to produce or change (a file, a test, an output), with no design judgement left open?" },
		checkable: { type: "noul", instructions: "Would a test, a build or a diff show whether the task is done?" },
		small: { type: "noul", instructions: "Is the task confined to one file, or read-only across several?" },
		held_path: { type: "noul", instructions: "Does the task touch harness/, .claude/, the house rules, merging, pushing, or a default branch?" },
		private: { type: "noul", instructions: "Does the task involve legal, money, health or other private personal matters?" },
		browser: { type: "noul", instructions: "Does the task need a web browser, a login, or a key?" },
	},
};

export class BadQuestion extends Error {}
export class NoAnswer extends Error {}

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
		if (q.instructions != null) clean.instructions = String(q.instructions).slice(0, 1000);
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

/** Ask the model. Returns {model, answers, usage}. Throws NoAnswer when nothing can answer, so the caller falls back. */
export async function decide(env, args) {
	const body = shape(args);
	const model = String(args.model || env.DECIDE_MODEL || DEFAULT_MODEL);
	let timer;
	const timeout = new Promise((_, no) => { timer = setTimeout(() => no(new NoAnswer("the decider didn't answer in " + TIMEOUT / 1000 + " s")), TIMEOUT); });
	timeout.catch(() => {});   // the race hears it; nobody else need
	let r;
	try {
		if (env.DECIDE_URL) {
			const res = await Promise.race([fetch(String(env.DECIDE_URL).replace(/\/+$/, "") + "/v1/systemone", {
				method: "POST", signal: AbortSignal.timeout(TIMEOUT),
				headers: { "Content-Type": "application/json", ...(env.DECIDE_KEY ? { Authorization: "Bearer " + env.DECIDE_KEY } : {}) },
				body: JSON.stringify({ ...body, ...(args.model ? { model } : {}) }),
			}), timeout]);
			if (!res.ok) throw new NoAnswer("the decider said " + res.status);
			r = await res.json();
		} else if (env.AI) {
			// Clef wants its short name in the body too; Jev and the rest take the id on the call alone
			const cf = /^@cf\/cloudflare\/(clef[a-z-]*)$/.exec(model);
			r = await Promise.race([env.AI.run(model, { ...(cf ? { model: cf[1] } : {}), ...body }), timeout]);
		} else throw new NoAnswer("no decider: the Worker has no AI binding and no DECIDE_URL");
	} catch (e) {
		if (e instanceof NoAnswer) throw e;
		throw new NoAnswer("the decider failed: " + (e && e.message ? e.message : e));
	} finally {
		clearTimeout(timer);
	}
	if (!r || !r.answers || typeof r.answers !== "object" || Array.isArray(r.answers)) throw new NoAnswer("the decider answered without answers");
	return { model: String(r.model || model), answers: r.answers, usage: r.usage || null };
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
