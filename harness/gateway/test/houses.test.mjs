// The two upgrade paths a deploy with accounts must keep: a grant made before accounts, and a file kept before them.
import assert from "node:assert/strict";
import { test } from "node:test";
import { FIRST_HOUSE, fileHouse, whose } from "../src/houses.js";

test("a grant made before accounts still opens the first house as its owner", () => {
	assert.deepEqual(whose({ user: "charlotte" }), { house: FIRST_HOUSE, owner: true });
	assert.deepEqual(whose(undefined), { house: FIRST_HOUSE, owner: false });
	assert.deepEqual(whose({ user: "tester", house: "tester", owner: false, admin: false }), { house: "tester", owner: false });
	assert.deepEqual(whose({ user: "charlotte", house: FIRST_HOUSE, owner: false }), { house: FIRST_HOUSE, owner: false }, "an agents' key is never the owner");
});

test("a file kept before accounts belongs to the first house", () => {
	assert.equal(fileHouse(undefined), FIRST_HOUSE);
	assert.equal(fileHouse({ type: "text/plain" }), FIRST_HOUSE);
	assert.equal(fileHouse({ house: "tester" }), "tester");
});
