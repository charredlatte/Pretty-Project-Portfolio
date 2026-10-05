// The registry: who has an account on this gateway, one SQLite-backed Durable Object for all of them. A user has
// a handle, a password (kept as its PBKDF2 hash), a house (the House object their cats live in) and, for the first
// of them, the admin's rights: uploading the café's art and creating accounts. Agents' keys and the café's cookies
// are kept only as hashes, each pointing at its user. A key has a role: "agent" (sessions and other agents) or
// "queen" (the user's queen runner, harness/runner, the only key that speaks as the queen). Nothing in here is a
// cat: those are in the houses.
import { DurableObject } from "cloudflare:workers";
import { FIRST_HOUSE } from "./houses.js";
import { MIN_SECRET, hashPassword, randomToken, sameHash, sha256 } from "./secret.js";

const LOCK_AFTER = 5;   // wrong passwords before a user's sign-in waits
const LOCK_FOR = 15 * 60 * 1000;
const HANDLE = /^[a-z0-9][a-z0-9-]{1,30}$/;
const ROLES = ["agent", "queen"];
const keyName = (name) => String(name || "key").slice(0, 60);
const QUEEN_KEY = "queen";   // the name of the queen's key seeded from the CATIO_QUEEN secret

/** The registry, with the first account made from the secrets while it is empty (tried until it has one). */
let booted = false, problem = "";
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
export const bootProblem = () => problem;

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
		]) this.sql.exec(q);
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
		if (token && token.length < MIN_SECRET) return { error: `CATIO_TOKEN is shorter than ${MIN_SECRET} characters: fix it, or remove it and mint a key from the café.` };
		const id = String(handle || "charlotte").toLowerCase();
		const made = await this.createUser(id, password || "", { house: FIRST_HOUSE, admin: true });
		if (made.error) return this.empty() ? { error: "CATIO_PASSWORD or CATIO_HANDLE: " + made.error } : { ok: true };   // two firsts at once: one made it
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

	user(id) {
		const row = this.sql.exec("SELECT id, house, admin FROM users WHERE id = ?", id).toArray()[0];
		return row ? { id: row.id, house: row.house, admin: !!row.admin } : null;
	}

	/**
	 * The user, when the handle and password match; `{locked: true}` while that user's sign-in waits; else null.
	 * One handle's tries run one after another (the hash yields, so without this a burst of guesses would all
	 * pass the lock): five wrong at once lock like five in a row, and right ones in flight together don't.
	 */
	checkPassword(id, password) {
		id = String(id || "").trim().toLowerCase();
		if (!HANDLE.test(id)) return null;   // can't be anyone's: no hash, no lock row
		const turn = (this.turns.get(id) || Promise.resolve()).then(() => this.tryPassword(id, password));
		this.turns.set(id, turn.catch(() => {}));
		return turn;
	}

	async tryPassword(id, password) {
		if (this.locked(id)) return { locked: true };
		const row = this.sql.exec("SELECT hash, salt FROM users WHERE id = ?", id).toArray()[0];
		// hashed either way, so an unknown handle takes as long as a wrong password
		const hash = await hashPassword(String(password || ""), row ? row.salt : "no-such-user");
		if (!row || !sameHash(hash, row.hash)) {
			this.sql.exec("DELETE FROM wrong WHERE at <= ?", Date.now() - LOCK_FOR);
			this.sql.exec("INSERT INTO wrong (user, at) VALUES (?, ?)", id, Date.now());
			return null;
		}
		this.sql.exec("DELETE FROM wrong WHERE user = ?", id);
		return this.user(id);
	}

	locked(id) {
		return this.sql.exec("SELECT COUNT(*) AS n FROM wrong WHERE user = ? AND at > ?", id, Date.now() - LOCK_FOR).one().n >= LOCK_AFTER;
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
