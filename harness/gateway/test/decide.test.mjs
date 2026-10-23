import assert from "node:assert/strict";
import { test } from "node:test";
import { BadQuestion, PRESETS, shape } from "../src/decide.js";

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
