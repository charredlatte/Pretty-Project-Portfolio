// The registry: who has an account on this gateway, one SQLite-backed Durable Object for all of them. A user has
// a handle, a password (kept as its PBKDF2 hash), a house (the House object their cats live in) and, for the first
// of them, the admin's rights: uploading the café's art and creating accounts. Agents' keys and the café's cookies
// are kept only as hashes, each pointing at its user. Nothing in here is a cat: those are in the houses.
import { DurableObject } from "cloudflare:workers";
import { MIN_SECRET, hashPassword, randomToken, sameHash, sha256 } from "./secret.js";

const LOCK_AFTER = 5;   // wrong passwords before a user's sign-in waits
const LOCK_FOR = 15 * 60 * 1000;
const HANDLE = /^[a-z0-9][a-z0-9-]{1,30}$/;

/** The registry, with the first account made from the two secrets if it has none (once per isolate; it is idempotent). */
let booted = false;
export async function registry(env) {
	const r = env.REGISTRY.get(env.REGISTRY.idFromName("registry"));
	if (!booted) {
		if (await r.empty()) await r.bootstrap(env.CATIO_PASSWORD, env.CATIO_TOKEN);
		booted = true;
	}
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

	/** The first account, from the two secrets the gateway had before it had accounts. Only into an empty registry. */
	async bootstrap(password, token) {
		if (!this.empty()) return false;
		const made = await this.createUser("charlotte", password || "", { house: "house", admin: true });
		if (made.error) return false;
		if (token) this.addKey("charlotte", await sha256(token), "bootstrap");
		return true;
	}

	/** A new account: `{user}`, or `{error}` for the caller to pass on. */
	async createUser(id, password, { house, admin = false } = {}) {
		id = String(id || "").trim().toLowerCase();
		if (!HANDLE.test(id)) return { error: "A handle is 2 to 31 letters, digits or dashes." };
		if (String(password).length < MIN_SECRET) return { error: `A password is ${MIN_SECRET} characters or more.` };
		if (this.user(id)) return { error: "That handle is taken." };
		const salt = randomToken();
		this.sql.exec("INSERT INTO users (id, hash, salt, house, admin, created) VALUES (?, ?, ?, ?, ?, ?)",
			id, await hashPassword(password, salt), salt, house || id, admin ? 1 : 0, Date.now());
		return { user: this.user(id) };
	}

	user(id) {
		const row = this.sql.exec("SELECT id, house, admin FROM users WHERE id = ?", id).toArray()[0];
		return row ? { id: row.id, house: row.house, admin: !!row.admin } : null;
	}

	/** The user, when the handle and password match; `{locked: true}` while that user's sign-in waits; else null. */
	async checkPassword(id, password) {
		id = String(id || "").trim().toLowerCase();
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
		this.sql.exec("INSERT INTO keys (hash, user, name, created) VALUES (?, ?, ?, ?)", hash, user, String(name || "key").slice(0, 60), Date.now());
	}

	/** A new agents' key for a user: returned once, kept only as its hash. */
	async mintKey(user, name) {
		const key = randomToken();
		this.addKey(user, await sha256(key), name);
		return key;
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
