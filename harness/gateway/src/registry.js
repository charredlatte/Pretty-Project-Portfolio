// The registry: who has an account on this gateway, one SQLite-backed Durable Object for all of them. A user has
// a handle, a password (kept as its PBKDF2 hash), a house (the House object their cats live in) and, for the first
// of them, the admin's rights: uploading the café's art and creating accounts. Agents' keys and the café's cookies
// are kept only as hashes, each pointing at its user. Nothing in here is a cat: those are in the houses.
import { DurableObject } from "cloudflare:workers";
import { FIRST_HOUSE } from "./houses.js";
import { MIN_SECRET, hashPassword, randomToken, sameHash, sha256 } from "./secret.js";

const LOCK_AFTER = 5;   // wrong passwords before a user's sign-in waits
const LOCK_FOR = 15 * 60 * 1000;
const HANDLE = /^[a-z0-9][a-z0-9-]{1,30}$/;
const keyName = (name) => String(name || "key").slice(0, 60);

/** The registry, with the first account filled in from the secrets (once per isolate once it has succeeded). */
let booted = false;
export async function registry(env) {
	const r = env.REGISTRY.get(env.REGISTRY.idFromName("registry"));
	if (!booted) booted = await r.bootstrap(env.CATIO_PASSWORD, env.CATIO_TOKEN, env.CATIO_HANDLE);
	return r;
}

/** What a token says about its holder: their user, their house, and whether they are its owner (not an agent). */
export const propsOf = (user, owner) => ({ user: user.id, house: user.house, owner, admin: user.admin });

export class Registry extends DurableObject {
	constructor(ctx, env) {
		super(ctx, env);
		this.sql = ctx.storage.sql;
		for (const q of [
			"CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, hash TEXT NOT NULL, salt TEXT NOT NULL, house TEXT NOT NULL, admin INTEGER NOT NULL, created INTEGER NOT NULL)",
			"CREATE TABLE IF NOT EXISTS keys (hash TEXT PRIMARY KEY, user TEXT NOT NULL, name TEXT NOT NULL, created INTEGER NOT NULL)",
			"CREATE TABLE IF NOT EXISTS logins (hash TEXT PRIMARY KEY, user TEXT NOT NULL, until INTEGER NOT NULL)",
			"CREATE TABLE IF NOT EXISTS wrong (user TEXT NOT NULL, at INTEGER NOT NULL)",
		]) this.sql.exec(q);
	}

	empty() {
		return this.sql.exec("SELECT COUNT(*) AS n FROM users").one().n === 0;
	}

	/**
	 * The first account and its key, from the two secrets the gateway had before it had accounts (CATIO_HANDLE names
	 * it; charlotte by default). It fills in what is missing, so a secret added later still counts after a deploy.
	 * False until the account exists.
	 */
	async bootstrap(password, token, handle) {
		const id = String(handle || "charlotte").toLowerCase();
		if (this.empty()) {
			const made = await this.createUser(id, password || "", { house: FIRST_HOUSE, admin: true });
			if (made.error) return false;
		}
		if (this.user(id) && token && token.length >= MIN_SECRET && !this.hasKey(id, "bootstrap")) this.addKey(id, await sha256(token), "bootstrap");
		return true;
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
		} catch {
			return { error: "That handle is taken." };   // made twice at once: the hash above let another request in
		}
		return { user: this.user(id) };
	}

	/** A new password for an account (an admin's reset). */
	async setPassword(id, password) {
		id = String(id || "").trim().toLowerCase();
		if (!this.user(id)) return { error: "No such account." };
		if (String(password).length < MIN_SECRET) return { error: `A password is ${MIN_SECRET} characters or more.` };
		const salt = randomToken(), hash = await hashPassword(password, salt);
		this.sql.exec("UPDATE users SET hash = ?, salt = ? WHERE id = ?", hash, salt, id);
		this.sql.exec("DELETE FROM logins WHERE user = ?", id);   // every browser signs in again
		return { ok: true };
	}

	user(id) {
		const row = this.sql.exec("SELECT id, house, admin FROM users WHERE id = ?", id).toArray()[0];
		return row ? { id: row.id, house: row.house, admin: !!row.admin } : null;
	}

	/** The user, when the handle and password match; `{locked: true}` while that user's sign-in waits; else null. */
	async checkPassword(id, password) {
		id = String(id || "").trim().toLowerCase();
		if (!HANDLE.test(id)) return null;   // can't be anyone's: no hash, no lock row
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

	addKey(user, hash, name) {
		this.sql.exec("INSERT INTO keys (hash, user, name, created) VALUES (?, ?, ?, ?)", hash, user, keyName(name), Date.now());
	}

	hasKey(user, name) {
		return this.sql.exec("SELECT COUNT(*) AS n FROM keys WHERE user = ? AND name = ?", user, name).one().n > 0;
	}

	/** A new agents' key for a user: returned once, kept only as its hash. */
	async mintKey(user, name) {
		const key = randomToken();
		this.addKey(user, await sha256(key), name);
		return { key, name: keyName(name) };
	}

	keys(user) {
		return this.sql.exec("SELECT name, created FROM keys WHERE user = ? ORDER BY created", user).toArray();
	}

	dropKey(user, name) {
		return this.sql.exec("DELETE FROM keys WHERE user = ? AND name = ?", user, name).rowsWritten > 0;
	}

	userOfKey(hash) {
		const row = this.sql.exec("SELECT user FROM keys WHERE hash = ?", hash).toArray()[0];
		return row ? this.user(row.user) : null;
	}

	login(hash, user, until) {
		this.sql.exec("DELETE FROM logins WHERE until <= ?", Date.now());
		this.sql.exec("INSERT INTO logins (hash, user, until) VALUES (?, ?, ?)", hash, user, until);
	}

	userOfLogin(hash) {
		const row = this.sql.exec("SELECT user FROM logins WHERE hash = ? AND until > ?", hash, Date.now()).toArray()[0];
		return row ? this.user(row.user) : null;
	}
}
