import assert from "node:assert/strict";
import { test } from "node:test";
import { BadQuestion, PRESETS, ask, confidence, read, shape, verdict } from "../src/decide.js";

// src/decide.js is plain JavaScript, so these run outside workerd and without a Cloudflare sign-in. They cover the
// body the Clef branch sends, which the Worker's own tests can't: those reach the decider through DECIDE_URL and a
// stand-in server, which accepts questions the real model refuses.

test("a question with no words is refused, by name, before any model is asked", () => {
	// Clef refuses a wordless question by calling the whole body malformed -- "required properties at '/' are
	// 'model,state,questions'" -- which names the root and never the question that is short. That is the 5006 that
	// read as a decider outage on 21 October 2026, so the refusal has to say which question, and which field.
	for (const q of [{ type: "noul" }, { type: "noul", instructions: "   " },
		{ type: "choice", criteria: { a: "one", b: "two" } }, { type: "score", criteria: ["low", "high"] }])
		assert.throws(() => shape({ state: "a cat asleep", questions: { asleep: q } }), BadQuestion, JSON.stringify(q));
	assert.throws(() => shape({ state: "a cat asleep", questions: { asleep: { type: "noul" } } }),
		/asleep: instructions is the question in words/);
});

test("a question keeps its words, and nothing the model doesn't take", () => {
	// `question` is the natural guess for where the words go, and it is not the field. It must not pass for one:
	// shape() drops every key but type, instructions and criteria, so guessing it used to leave a bare {type}.
	assert.throws(() => shape({ state: "a cat asleep", questions: { asleep: { type: "noul", question: "Is the cat asleep?" } } }), BadQuestion);
	assert.deepEqual(
		shape({ state: "a cat asleep", questions: { asleep: { type: "noul", instructions: "Is the cat asleep?", question: "dropped" } } }),
		{ state: "a cat asleep", questions: { asleep: { type: "noul", instructions: "Is the cat asleep?" } } });
});

test("every preset question carries its words, so a preset is never refused", () => {
	for (const [name, questions] of Object.entries(PRESETS)) {
		assert.doesNotThrow(() => shape({ state: "a task to weigh", preset: name }), name);
		for (const [q, body] of Object.entries(questions)) assert.ok(String(body.instructions || "").trim(), name + "." + q);
	}
});

test("a choice and a score still answer for their criteria once they have words", () => {
	const words = { instructions: "Which room is the cat in?" };
	assert.throws(() => shape({ state: "a cat", questions: { where: { type: "choice", ...words, criteria: { only: "one option" } } } }), BadQuestion);
	assert.deepEqual(shape({ state: "a cat", questions: { where: { type: "choice", ...words, criteria: { library: "in the library", kitchen: "in the kitchen" } } } }).questions.where,
		{ type: "choice", ...words, criteria: { library: "in the library", kitchen: "in the kitchen" } });
	assert.deepEqual(shape({ state: "a cat", questions: { how: { type: "score", instructions: "How settled?", criteria: ["restless", "settled"] } } }).questions.how,
		{ type: "score", instructions: "How settled?", criteria: ["restless", "settled"] });
});

// ---------- the prompt a model that doesn't take questions is given, and the answers read back out of its reply ----------
// These are pure: they feed read() what models really reply with, so the tolerant path is covered without a model.
const noul = (q) => shape({ state: "a task", questions: { held_path: { type: "noul", ...q } } });

test("the refusal names the key a caller put the words under", () => {
	// one field, `instructions`, and a near miss is told which key to move the words out of rather than left to guess
	assert.throws(() => noul({ question: "Does it touch harness/?" }), /held_path: instructions is the question in words, not "question"/);
	assert.throws(() => noul({ prompt: "Does it touch harness/?" }), /not "prompt"/);
	assert.throws(() => noul({}), /held_path: instructions is the question in words$/);
});

test("the prompt names each question, what may answer it, and asks for JSON alone", () => {
	const body = shape({ state: { file: "notes.md" }, questions: {
		held_path: { type: "noul", instructions: "Does it touch harness/?" },
		cat: { type: "choice", instructions: "Which cat?", criteria: { shop: "the shop", catio: "the café" } },
		size: { type: "score", instructions: "How big?", criteria: ["tiny", "small", "big"] },
	} });
	const p = ask(body);
	assert.match(p, /JSON object and nothing else/);
	assert.match(p, /\{"file":"notes\.md"\}/, "the state reaches the model");
	assert.match(p, /- held_path: Does it touch harness\/\? Answer yes or no\./);
	assert.match(p, /- cat: Which cat\? Answer with one of shop \(the shop\), catio \(the café\)\./);
	assert.match(p, /- size: How big\? Answer with a whole number from 0 to 2, where 0 is tiny, 1 is small, 2 is big\./);
	assert.match(p, /"confidence": 0 to 1/);
});


test("a model's reply is read into the same answers a System One model returns", () => {
	const body = shape({ state: "x", questions: {
		held_path: { type: "noul", instructions: "?" },
		cat: { type: "choice", instructions: "?", criteria: { shop: "the shop", catio: "the café" } },
		size: { type: "score", instructions: "?", criteria: ["tiny", "small", "big"] },
	} });
	const a = read('{"held_path": {"answer": "no", "confidence": 0.9}, "cat": {"answer": "catio", "confidence": 0.8}, "size": {"answer": 2, "confidence": 0.7}}', body.questions);
	assert.deepEqual(a.held_path, { type: "noul", noul: 0.1 });
	assert.deepEqual(a.cat, { type: "choice", choice: "catio", confidence: 0.8, probabilities: { shop: 0.2, catio: 0.8 } });
	assert.deepEqual(a.size, { type: "score", score: 2, confidence: 0.7 });
	// the point of the shape: verdict and confidence read it exactly as they read Clef's own answer
	assert.deepEqual(["no", "catio", "2"], [verdict(a.held_path), verdict(a.cat), verdict(a.size)]);
	assert.deepEqual([0.9, 0.8, 0.7], [confidence(a.held_path), confidence(a.cat), confidence(a.size)]);
});


test("the JSON is found inside a code fence, prose, or both", () => {
	const qs = noul({ instructions: "?" }).questions;
	const want = { type: "noul", noul: 0.8 };
	assert.deepEqual(read('```json\n{"held_path": {"answer": "yes", "confidence": 0.8}}\n```', qs).held_path, want);
	assert.deepEqual(read('Sure! Here is the answer:\n{"held_path": {"answer": "yes", "confidence": 0.8}}\nHope that helps.', qs).held_path, want);
	assert.deepEqual(read('I think {not json} but here: {"held_path": {"answer": "yes", "confidence": 0.8}}', qs).held_path, want,
		"prose that merely looks like an object is stepped over");
});


test("a yes or no keeps the answer the model gave, whatever confidence it put on it", () => {
	const qs = noul({ instructions: "?" }).questions;
	for (const [said, want] of [["yes", "yes"], ["no", "no"], ["Yes", "yes"], ["TRUE", "yes"], ["n", "no"]]) {
		assert.equal(verdict(read(`{"held_path": {"answer": "${said}", "confidence": 0.9}}`, qs).held_path), want);
	}
	assert.equal(verdict(read('{"held_path": {"answer": true, "confidence": 0.9}}', qs).held_path), "yes", "a JSON boolean too");
	// a confidence below a coin toss would flip the answer it was given for: the answer survives, and it stays
	// under every floor the café uses, so the caller falls back to its own judgement rather than acting on it
	for (const said of ["yes", "no"]) {
		const a = read(`{"held_path": {"answer": "${said}", "confidence": 0.2}}`, qs).held_path;
		assert.equal(verdict(a), said, "the answer the model stated survives a low confidence");
		assert.ok(confidence(a) < 0.6, "and does not clear the café's floor on its own");
	}
});


test("an answer with no confidence of its own never clears the café's floor", () => {
	const qs = shape({ state: "x", questions: {
		held_path: { type: "noul", instructions: "?" },
		cat: { type: "choice", instructions: "?", criteria: { shop: "the shop", catio: "the café" } },
	} }).questions;
	const a = read('{"held_path": {"answer": "yes"}, "cat": {"answer": "shop"}}', qs);
	assert.deepEqual([verdict(a.held_path), verdict(a.cat)], ["yes", "shop"], "the answers are still read");
	for (const name of ["held_path", "cat"]) assert.ok(confidence(a[name]) < 0.6, name + " should sit under the 0.6 floor");
});


test("a bare answer, with no object around it, is still read", () => {
	const qs = noul({ instructions: "?" }).questions;
	assert.deepEqual(read('{"held_path": "yes"}', qs).held_path.noul > 0.5, true);
	assert.deepEqual(read('{"held_path": 0.73}', qs).held_path, { type: "noul", noul: 0.73 }, "a bare probability for a noul");
	assert.deepEqual(read('{"held_path": {"noul": 0.73}}', qs).held_path, { type: "noul", noul: 0.73 }, "or under the type's own name");
});


test("a score given by name, or past the end of its scale", () => {
	const qs = shape({ state: "x", questions: { size: { type: "score", instructions: "?", criteria: ["tiny", "small", "big"] } } }).questions;
	assert.equal(read('{"size": {"answer": "big", "confidence": 0.9}}', qs).size.score, 2, "a level by its own name");
	assert.equal(read('{"size": {"answer": 9, "confidence": 0.9}}', qs).size.score, 2, "clamped to the top level");
	assert.equal(read('{"size": {"answer": -3, "confidence": 0.9}}', qs).size.score, 0, "and to the bottom");
	assert.equal(read('{"size": {"answer": 1.4, "confidence": 0.9}}', qs).size.score, 1.4, "a weighted level keeps its fraction");
});


test("what the model got wrong is left unanswered rather than guessed", () => {
	const qs = shape({ state: "x", questions: {
		cat: { type: "choice", instructions: "?", criteria: { shop: "the shop", catio: "the café" } },
		held_path: { type: "noul", instructions: "?" },
	} }).questions;
	assert.deepEqual(read('{"cat": {"answer": "the kitchen"}, "held_path": {"answer": "yes", "confidence": 0.9}}', qs),
		{ held_path: { type: "noul", noul: 0.9 } }, "an option that was never offered is not a decision");
	assert.deepEqual(read('{"cat": {"answer": "CATIO"}}', qs).cat.choice, "catio", "but the option's own case is forgiven");
	assert.deepEqual(read("I'd rather not answer that.", qs), {}, "and a reply with no JSON in it answers nothing");
	assert.deepEqual(read("", qs), {});
	assert.deepEqual(read(null, qs), {});
	// an empty answer is no answer: Number("") is 0, which would otherwise read as a confident no
	assert.deepEqual(read('{"held_path": {"answer": "", "confidence": 0.9}}', qs), {});
	assert.deepEqual(read('{"held_path": {"answer": "   "}}', qs), {});
});


test("a choice's probabilities add up to one, however many options there are", () => {
	for (const n of [2, 3, 7]) {
		const criteria = Object.fromEntries(Array.from({ length: n }, (_, i) => ["opt" + i, "option " + i]));
		const qs = shape({ state: "x", questions: { pick: { type: "choice", instructions: "?", criteria } } }).questions;
		const a = read('{"pick": {"answer": "opt1", "confidence": 0.6}}', qs).pick;
		const total = Object.values(a.probabilities).reduce((s, p) => s + p, 0);
		// a distribution, to the four decimals they are written at (so the log reads as Clef's own answers do)
		assert.ok(Math.abs(total - 1) < 1e-3, n + " options summed to " + total);
		assert.equal(a.probabilities.opt1, 0.6);
	}
});
