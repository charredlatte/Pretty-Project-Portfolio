// The registry: who has an account on this gateway, one SQLite-backed Durable Object for all of them. A user has
// a handle, a password (kept as its PBKDF2 hash), a house (the House object their cats live in) and, for the first
// of them, the admin's rights: uploading the café's art, creating accounts and inviting people to sign up (an invite
// is single-use and kept only as its hash, like a key). Agents' keys and the café's cookies
// are kept only as hashes, each pointing at its user. A key has a role: "agent" (sessions and other agents) or
// "queen" (the user's queen runner, harness/runner, the only key that speaks as the queen). Nothing in here is a
// cat: those are in the houses.
import { DurableObject } from "cloudflare:workers";
import { FIRST_HOUSE } from "./houses.js";
import { MIN_SECRET, hashPassword, randomToken, sameHash, sha256 } from "./secret.js";

// Wrong passwords inside LOCK_FOR make a sign-in wait. The wait is for the address that guessed, so a stranger who knows
// a handle can't lock its owner out: LOCK_AFTER from one address at one handle, LOCK_IP from one address at any
// handles, and, from anywhere at all, LOCK_USER at one handle.
const LOCK_AFTER = 5;
const LOCK_IP = 20;
const LOCK_USER = 100;
const LOCK_FOR = 15 * 60 * 1000;
const HANDLE = /^[a-z0-9][a-z0-9-]{1,30}$/;
const ROLES = ["agent", "queen"];
const keyName = (name) => String(name || "key").slice(0, 60);
const QUEEN_KEY = "queen";   // the name of the queen's key seeded from the CATIO_QUEEN secret
const INVITE_FOR = 7 * 24 * 3600 * 1000;   // an unused invite lapses after a week

/** The registry, with the first account made from the secrets while it is empty (tried until it has one). */
let booted = false, problem = "";
const WHERE = "Workers & Pages, this Worker, Settings, Variables and Secrets";
export async function registry(env) {
	const r = env.REGISTRY.get(env.REGISTRY.idFromName("registry"));
	if (!booted) {
		const made = await r.bootstrap(env.CATIO_PASSWORD, env.CATIO_TOKEN, env.CATIO_HANDLE, env.CATIO_QUEEN);
		if (!made.error) booted = true;   // never back to false: another request may have got there first
		problem = made.error || "";
	}
	return r;
}

/** Whether the registry has an account: once true it stays true, so this costs nothing after the first time. */
export async function hasAccount(env) {
	if (!booted) await registry(env);
	return booted;
}

/** Why there is no account yet, for the sign-in pages: what the bootstrap found wrong with the secrets. */
export const bootProblem = () => {
	if (problem) return problem;
	// Distinguish between not set and too short for clearer setup guidance
	return `CATIO_PASSWORD isn't set for this Worker in Cloudflare (${WHERE}), or it's under ${MIN_SECRET} characters. Set a secret of ${MIN_SECRET} characters or more: it becomes the first account's password.`;
};

/**
 * The setup's warning lights, for the pages shown while there is no account: what this Worker sees of each secret,
 * never its value, and what to do. `[{name, state: "ok" | "bad" | "off", says}]`; "off" is optional and not set.
 * Safe to show: with no account, there is nothing behind the sign-in yet, and the first account is made the moment
 * every light is right.
 */
export function setupLights(env) {
	const pw = env.CATIO_PASSWORD, token = env.CATIO_TOKEN, queen = env.CATIO_QUEEN;
	const handle = String(env.CATIO_HANDLE || "charlotte").trim().toLowerCase();
	const long = `is under ${MIN_SECRET} characters`;
	return [
		!pw ? { name: "CATIO_PASSWORD", state: "bad", says: `isn't set for this Worker: add it in Cloudflare (${WHERE}) as type Secret, ${MIN_SECRET} characters or more. A variable under Builds, or of type Text, doesn't reach the Worker.` }
			: String(pw).length < MIN_SECRET ? { name: "CATIO_PASSWORD", state: "bad", says: `${long}: set a longer one.` }
			: { name: "CATIO_PASSWORD", state: "ok", says: "is set: it will be your password." },
		!HANDLE.test(handle) ? { name: "CATIO_HANDLE", state: "bad", says: "isn't a handle: 2 to 31 lower-case letters, digits or dashes, with no spaces, dots or underscores." }
			: env.CATIO_HANDLE ? { name: "CATIO_HANDLE", state: "ok", says: `is set: your handle will be ${handle}.` }
			: { name: "CATIO_HANDLE", state: "ok", says: `isn't set, so your handle will be ${handle}. Add it now for another: it can't change afterwards.` },
		!token ? { name: "CATIO_TOKEN", state: "off", says: "isn't set, which is fine: it is the key your cats check in with, and you can make keys in the café later." }
			: token.length < MIN_SECRET ? { name: "CATIO_TOKEN", state: "bad", says: `${long}: make it longer, or delete it.` }
			: { name: "CATIO_TOKEN", state: "ok", says: "is set." },
		!queen ? { name: "CATIO_QUEEN", state: "off", says: "isn't set, which is fine: it is the queen's runner's key, for later." }
			: queen.length < MIN_SECRET ? { name: "CATIO_QUEEN", state: "bad", says: `${long}, so it would be ignored: make it longer.` }
			: { name: "CATIO_QUEEN", state: "ok", says: "is set." },
	];
}

/** What a token says about its holder: their user, their house, whether they are its owner (not a key), and a key's role. */
export const propsOf = (user, owner) => ({ user: user.id, house: user.house, owner, admin: user.admin, ...(user.role ? { role: user.role } : {}) });

export class Registry extends DurableObject {
	constructor(ctx, env) {
		super(ctx, env);
		this.sql = ctx.storage.sql;
		for (const q of [
			"CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, hash TEXT NOT NULL, salt TEXT NOT NULL, house TEXT NOT NULL, admin INTEGER NOT NULL, created INTEGER NOT NULL)",
			"CREATE TABLE IF NOT EXISTS keys (hash TEXT PRIMARY KEY, user TEXT NOT NULL, name TEXT NOT NULL, created INTEGER NOT NULL)",
			// names are unique per user; a twin from before that rule gets its row number on the end rather than break the index
			"UPDATE keys SET name = name || '-' || rowid WHERE rowid NOT IN (SELECT MIN(rowid) FROM keys GROUP BY user, name)",
			"CREATE UNIQUE INDEX IF NOT EXISTS keys_by_name ON keys (user, name)",
			"CREATE TABLE IF NOT EXISTS logins (hash TEXT PRIMARY KEY, user TEXT NOT NULL, until INTEGER NOT NULL)",
			"CREATE TABLE IF NOT EXISTS wrong (user TEXT NOT NULL, at INTEGER NOT NULL)",
			"CREATE TABLE IF NOT EXISTS invites (hash TEXT PRIMARY KEY, by TEXT NOT NULL, until INTEGER NOT NULL)",
		]) this.sql.exec(q);
		// where a wrong password came from, on registries made before sign-ins were counted by address
		if (!this.sql.exec("PRAGMA table_info(wrong)").toArray().some((c) => c.name === "ip")) this.sql.exec("ALTER TABLE wrong ADD COLUMN ip TEXT NOT NULL DEFAULT ''");
		// a key's role, on registries made before the queen had one
		if (!this.sql.exec("PRAGMA table_info(keys)").toArray().some((c) => c.name === "role")) this.sql.exec("ALTER TABLE keys ADD COLUMN role TEXT NOT NULL DEFAULT 'agent'");
		this.turns = new Map();   // a handle's password tries, in turn
	}

	empty() {
		return this.sql.exec("SELECT COUNT(*) AS n FROM users").one().n === 0;
	}

	/**
	 * The first account and its key, from the two secrets the gateway had before it had accounts (CATIO_HANDLE names
	 * it; charlotte by default). Once, into an empty registry: a key dropped later stays dropped. `{ok}` once the
	 * registry has an account, else `{error}` saying what is wrong with the secrets. The queen's key is different:
	 * CATIO_QUEEN is the first account's queen key for as long as the secret is set (it is checked at every start,
	 * so adding or changing the secret is a deploy away, and removing it retires the key).
	 */
	async bootstrap(password, token, handle, queen) {
		if (!this.empty()) { await this.seedQueen(queen); return { ok: true }; }
		if (!password) return { error: `CATIO_PASSWORD isn't set for this Worker: add it in Cloudflare (${WHERE}), ${MIN_SECRET} characters or more. A variable under Workers Builds doesn't reach the Worker.` };
		if (String(password).length < MIN_SECRET) return { error: `CATIO_PASSWORD is under ${MIN_SECRET} characters: set a longer one in Cloudflare (${WHERE}).` };
		if (token && token.length < MIN_SECRET) return { error: `CATIO_TOKEN is shorter than ${MIN_SECRET} characters: fix it, or remove it and mint a key from the café.` };
		const id = String(handle || "charlotte").toLowerCase();
		const made = await this.createUser(id, password, { house: FIRST_HOUSE, admin: true });
		if (made.error) return this.empty() ? { error: "CATIO_HANDLE: " + made.error } : { ok: true };   // two firsts at once: one made it
		if (token) this.addKey(id, await sha256(token), "bootstrap");
		await this.seedQueen(queen);
		return { ok: true };
	}

	/** The first account's queen key is the CATIO_QUEEN secret: kept in step with it, dropped when it goes. */
	async seedQueen(queen) {
		const first = this.sql.exec("SELECT id FROM users WHERE house = ? ORDER BY created LIMIT 1", FIRST_HOUSE).toArray()[0];
		if (!first) return;
		const have = this.sql.exec("SELECT hash FROM keys WHERE user = ? AND name = ? AND role = 'queen'", first.id, QUEEN_KEY).toArray()[0];
		const want = queen && queen.length >= MIN_SECRET ? await sha256(queen) : null;
		if (have && have.hash === want) return;
		if (have) this.sql.exec("DELETE FROM keys WHERE user = ? AND name = ?", first.id, QUEEN_KEY);
		// one secret can't be both an agent's key and the queen's: the same hash would be both, and the agents' key
		// would speak as her. The existing key stays; the queen goes without until she has a secret of her own.
		if (want && this.sql.exec("SELECT 1 FROM keys WHERE hash = ?", want).toArray().length) {
			console.warn("CATIO_QUEEN is the same secret as another key: it is ignored. Give the queen a key of her own.");
			return;
		}
		if (want) this.addKey(first.id, want, QUEEN_KEY, "queen");
	}

	/** A new account: `{user}`, or `{error}` for the caller to pass on. */
	async createUser(id, password, { house, admin = false } = {}) {
		id = String(id || "").trim().toLowerCase();
		if (!HANDLE.test(id)) return { error: "A handle is 2 to 31 letters, digits or dashes." };
		if (id === FIRST_HOUSE && house !== FIRST_HOUSE) return { error: "That handle is kept." };   // it names the first house
		if (String(password).length < MIN_SECRET) return { error: `A password is ${MIN_SECRET} characters or more.` };
		if (this.user(id)) return { error: "That handle is taken." };
		const salt = randomToken(), hash = await hashPassword(password, salt);
		try {
			this.sql.exec("INSERT INTO users (id, hash, salt, house, admin, created) VALUES (?, ?, ?, ?, ?, ?)",
				id, hash, salt, house || id, admin ? 1 : 0, Date.now());
		} catch (e) {
			if (!/users\.id/.test(String(e && e.message))) throw e;
			return { error: "That handle is taken." };   // made twice at once: the hash above let another request in
		}
		return { user: this.user(id) };
	}

	/**
	 * A new password for an account (an admin's reset): the user's browsers, keys and lock all go, so whoever had
	 * the old password is out everywhere. `{ok, id, house}` with the handle as the registry spells it.
	 */
	async setPassword(id, password) {
		id = String(id || "").trim().toLowerCase();
		const user = this.user(id);
		if (!user) return { error: "No such account." };
		if (String(password).length < MIN_SECRET) return { error: `A password is ${MIN_SECRET} characters or more.` };
		const salt = randomToken(), hash = await hashPassword(password, salt);
		this.sql.exec("UPDATE users SET hash = ?, salt = ? WHERE id = ?", hash, salt, id);
		this.sql.exec("DELETE FROM logins WHERE user = ?", id);   // every browser signs in again
		this.sql.exec("DELETE FROM keys WHERE user = ?", id);     // every key is dead: mint new ones
		this.sql.exec("DELETE FROM wrong WHERE user = ?", id);    // and a locked-out user is let back in
		return { ok: true, id, house: user.house };
	}

	/** An invite to sign up, from an admin: `{code, until}`, the code returned once and kept only as its hash. */
	async invite(by) {
		if (!this.user(by)?.admin) return { error: "Only an admin invites." };
		const code = randomToken(), until = Date.now() + INVITE_FOR;
		this.sql.exec("INSERT INTO invites (hash, by, until) VALUES (?, ?, ?)", await sha256(code), by, until);
		return { code, until };
	}

	/** How many invites are out and unused, and the admin's way to take them all back. */
	openInvites() {
		return this.sql.exec("SELECT COUNT(*) AS n FROM invites WHERE until > ?", Date.now()).one().n;
	}

	dropInvites() {
		return this.sql.exec("DELETE FROM invites").rowsWritten;
	}

	/**
	 * A new account, made by the person invited: `{user}` or `{error}`. Never an admin. The invite is spent before the
	 * password is hashed (the hash yields, and two sign-ups with one code must not both get in), and given back if the
	 * account can't be made, so a taken handle or a short password costs the invite nothing.
	 */
	async signUp(code, id, password) {
		const hash = await sha256(String(code || "").trim());
		this.sql.exec("DELETE FROM invites WHERE until <= ?", Date.now());
		const invite = this.sql.exec("SELECT by, until FROM invites WHERE hash = ?", hash).toArray()[0];
		if (!invite) return { error: "That invite isn't right, or it has been used or has lapsed." };
		this.sql.exec("DELETE FROM invites WHERE hash = ?", hash);
		const made = await this.createUser(id, password);
		if (made.error) this.sql.exec("INSERT INTO invites (hash, by, until) VALUES (?, ?, ?)", hash, invite.by, invite.until);
		return made;
	}

	user(id) {
		const row = this.sql.exec("SELECT id, house, admin FROM users WHERE id = ?", id).toArray()[0];
		return row ? { id: row.id, house: row.house, admin: !!row.admin } : null;
	}

	/**
	 * The user, when the handle and password match; `{locked: true}` while that address's sign-in waits; else null.
	 * One handle's tries run one after another (the hash yields, so without this a burst of guesses would all
	 * pass the lock): five wrong at once lock like five in a row, and right ones in flight together don't.
	 */
	checkPassword(id, password, ip = "") {
		id = String(id || "").trim().toLowerCase();
		if (!HANDLE.test(id)) return null;   // can't be anyone's: no hash, no lock row
		const turn = (this.turns.get(id) || Promise.resolve()).then(() => this.tryPassword(id, password, ip));
		const tail = turn.catch(() => {});
		this.turns.set(id, tail);
		tail.then(() => { if (this.turns.get(id) === tail) this.turns.delete(id); });
		return turn;
	}

	async tryPassword(id, password, ip) {
		if (this.locked(id, ip)) return { locked: true };
		const row = this.sql.exec("SELECT hash, salt FROM users WHERE id = ?", id).toArray()[0];
		// hashed either way, so an unknown handle takes as long as a wrong password
		const hash = await hashPassword(String(password || ""), row ? row.salt : "no-such-user");
		if (!row || !sameHash(hash, row.hash)) {
			this.sql.exec("DELETE FROM wrong WHERE at <= ?", Date.now() - LOCK_FOR);
			this.sql.exec("INSERT INTO wrong (user, ip, at) VALUES (?, ?, ?)", id, ip, Date.now());
			return null;
		}
		this.sql.exec("DELETE FROM wrong WHERE user = ?", id);
		return this.user(id);
	}

	locked(id, ip) {
		const since = Date.now() - LOCK_FOR;
		const wrong = (where, ...args) => this.sql.exec(`SELECT COUNT(*) AS n FROM wrong WHERE at > ? AND ${where}`, since, ...args).one().n;
		return wrong("user = ? AND ip = ?", id, ip) >= LOCK_AFTER || wrong("ip = ?", ip) >= LOCK_IP || wrong("user = ?", id) >= LOCK_USER;
	}

	/** True when the key is kept; false when the user already has one by that name. Anything else is thrown. */
	addKey(user, hash, name, role = "agent") {
		try {
			this.sql.exec("INSERT INTO keys (hash, user, name, created, role) VALUES (?, ?, ?, ?, ?)", hash, user, keyName(name), Date.now(), role);
			return true;
		} catch (e) {
			if (/keys\.user, keys\.name|keys\.hash/.test(String(e && e.message))) return false;
			throw e;
		}
	}

	/** A new key for a user, `{key, name, role}`: returned once, kept only as its hash. Names are unique per user.
	 * The role is "agent" (the default: sessions and agents) or "queen" (the user's queen runner). */
	async mintKey(user, name, role = "agent") {
		role = String(role || "agent");
		if (!ROLES.includes(role)) return { error: "A key's role is agent or queen." };
		const key = randomToken();
		if (!this.addKey(user, await sha256(key), name, role)) return { error: "You already have a key by that name: drop it first." };
		return { key, name: keyName(name), role };
	}

	keys(user) {
		return this.sql.exec("SELECT name, created, role FROM keys WHERE user = ? ORDER BY created, rowid", user).toArray();
	}

	dropKey(user, name) {
		return this.sql.exec("DELETE FROM keys WHERE user = ? AND name = ?", user, keyName(name)).rowsWritten > 0;
	}

	/** The key's user, with the key's role on it, or null. */
	userOfKey(hash) {
		const row = this.sql.exec("SELECT user, role FROM keys WHERE hash = ?", hash).toArray()[0];
		const user = row && this.user(row.user);
		return user ? { ...user, role: row.role || "agent" } : null;
	}

	login(hash, user, until) {
		this.sql.exec("DELETE FROM logins WHERE until <= ?", Date.now());
		this.sql.exec("INSERT INTO logins (hash, user, until) VALUES (?, ?, ?)", hash, user, until);
	}

	logout(hash) {
		this.sql.exec("DELETE FROM logins WHERE hash = ?", hash);
	}

	userOfLogin(hash) {
		const row = this.sql.exec("SELECT user FROM logins WHERE hash = ? AND until > ?", hash, Date.now()).toArray()[0];
		return row ? this.user(row.user) : null;
	}
}
