import assert from "node:assert/strict";
import { test } from "node:test";
import { plain } from "../src/plain.js";

test("drops a toString or valueOf of its own at any depth, and leaves the rest as it was", () => {
	const given = JSON.parse('{"a":{"toString":1},"b":[{"valueOf":2,"keep":3}],"c":"text","d":null,"e":[1,"2",true]}');
	assert.deepEqual(plain(given), { a: {}, b: [{ keep: 3 }], c: "text", d: null, e: [1, "2", true] });
	assert.equal(String(plain(given).a), "[object Object]", "and String() works on it now");
});

test("a key called __proto__ stays an ordinary key", () => {
	const out = plain(JSON.parse('{"__proto__":{"x":1}}'));
	assert.deepEqual(Object.keys(out), ["__proto__"]);
	assert.equal(Object.getPrototypeOf(out), Object.prototype);
});

test("what is nested deeper than anyone sends becomes null instead of overflowing the stack", () => {
	let deep = "end";
	for (let i = 0; i < 100000; i++) deep = [deep];
	let at = plain(deep), depth = 0;
	while (Array.isArray(at)) { at = at[0]; depth++; }
	assert.equal(at, null);
	assert.ok(depth <= 26);
});

test("a string, a number and undefined pass straight through", () => {
	assert.deepEqual([plain("x"), plain(5), plain(undefined), plain(null)], ["x", 5, undefined, null]);
});
