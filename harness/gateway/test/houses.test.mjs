// The two upgrade paths a deploy with accounts must keep: a grant made before accounts, and a file kept before them.
import assert from "node:assert/strict";
import { test } from "node:test";
import { FIRST_HOUSE, fileKeys, whose } from "../src/houses.js";

test("a grant made before accounts still opens the first house as its owner", () => {
	assert.deepEqual(whose({ user: "charlotte" }), { house: FIRST_HOUSE, owner: true });
	assert.deepEqual(whose(undefined), { house: null, owner: false }, "a token that names nobody opens nothing");
	assert.deepEqual(whose({ user: "tester" }), { house: null, owner: false });
	assert.deepEqual(whose({ user: "tester", house: "tester", owner: false, admin: false }), { house: "tester", owner: false });
	assert.deepEqual(whose({ user: "charlotte", house: FIRST_HOUSE, owner: false }), { house: FIRST_HOUSE, owner: false }, "an agents' key is never the owner");
});

test("a file kept before accounts is still the first house's, and nobody else's", () => {
	assert.deepEqual(fileKeys(FIRST_HOUSE, "mfz1k2-0a1b2c3d"), ["file:house:mfz1k2-0a1b2c3d", "file:mfz1k2-0a1b2c3d"]);
	assert.deepEqual(fileKeys("tester", "mfz1k2-0a1b2c3d"), ["file:tester:mfz1k2-0a1b2c3d"]);
	assert.deepEqual(fileKeys(FIRST_HOUSE, "tester:abc"), [], "a colon can't reach another house's file through the old key");
	assert.deepEqual(fileKeys(FIRST_HOUSE, "../x"), []);
});
