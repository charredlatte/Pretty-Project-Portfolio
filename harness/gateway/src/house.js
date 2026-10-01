// The house: every cat the gateway knows, their conversations and the files waiting for them, in one
// SQLite-backed Durable Object. The tools behave as harness/mcp/catio_mcp.py's do, with two differences:
// nothing here can run a wake command, and only Charlotte (signed in through claude.ai) speaks as herself,
// drops files and manages cats. Agents and session hooks, which hold CATIO_TOKEN, report and answer.
import { DurableObject } from "cloudflare:workers";
import RULES from "../../rules.json";
import { MOODS } from "./tools.js";

const FIELDS = ["name", "model", "provider", "title", "project", "repo", "branch", "ask", "link", "session", "via", "cwd", "room"];
const MAX_FILE = 1024 * 1024;   // a free Worker gets 10 ms of CPU a request: bigger files go through the brain
const KEEP_PICKED = 7 * 24 * 3600 * 1000;   // a picked-up file keeps its bytes a week, then only its record
const LOCK_AFTER = 5;   // wrong passwords before the sign-in waits
const LOCK_FOR = 15 * 60 * 1000;
const ACTIONS = ["rename", "move", "archive", "unarchive", "pause", "resume", "wrap_up", "message", "done"];

class Refusal extends Error {}   // bad arguments: the caller is told, nothing breaks

function need(args, ...keys) {
	for (const k of keys) if (!String(args[k] ?? "").trim()) throw new Refusal(k + " is required");
}
const newId = () => Date.now() + "-" + crypto.randomUUID().slice(0, 6);

const TOOLS = {
	house_rules() {
		return { catio: RULES.catio, rules: RULES.rules.filter((r) => r.on !== false) };
	},

	report_status(h, args) {
		need(args, "agent");
		const id = String(args.agent).slice(0, 200);
		const a = h.agent(id) || { id, since: Date.now() };
		for (const k of FIELDS) if (args[k] != null) a[k] = String(args[k]).slice(0, 500);
		if (args.mood != null) {
			if (!MOODS.includes(args.mood)) throw new Refusal("mood must be one of " + MOODS.join(", "));
			a.mood = args.mood;
		}
		a.updated = Date.now();
		h.save(a);
		return { ok: true, waiting: TOOLS.inbox(h, { agent: id }) };
	},

	list_agents(h, args) {
		const waiting = new Map(h.sql.exec("SELECT cat, COUNT(*) AS n FROM files WHERE status = 'waiting' GROUP BY cat").toArray().map((r) => [r.cat, r.n]));
		const agents = h.sql.exec("SELECT data FROM agents ORDER BY updated DESC").toArray().map((r) => JSON.parse(r.data))
			.filter((a) => !a.archived || args.archived)
			.map((a) => ({ ...a, waiting: waiting.get(a.id) || 0, wakes: false }));
		return { agents };
	},

	// With mark, only what hasn't been handed over yet, and now it has: a session's Stop hook hands her notes,
	// requests and files in once each. Handing over keeps its own place (handedNotes), apart from what an answer
	// counts as read (seenNotes), so a note she sends while the session is answering still gets handed in.
	inbox(h, args) {
		need(args, "agent");
		const id = String(args.agent);
		const a = h.agent(id);
		const mark = args.mark === true && !!a;
		const files = h.sql.exec("SELECT id, name, type, size, note, at FROM files WHERE cat = ? AND status = 'waiting'" +
			(mark ? " AND handed IS NULL" : "") + " ORDER BY at", id).toArray();
		const since = (a && (mark ? a.handedNotes ?? a.seenNotes : a.seenNotes)) || 0;
		const notes = h.sql.exec("SELECT id, cat, text, author, at FROM notes WHERE cat = ? AND author = 'charlotte' AND at > ? ORDER BY at",
			id, since).toArray();
		let request = (a && a.request) || null;
		if (mark) {
			if (request && request.handed) request = null;
			const now = Date.now();
			for (const f of files) h.sql.exec("UPDATE files SET handed = ? WHERE id = ?", now, f.id);
			if (notes.length || request) {
				if (notes.length) {
					a.handedNotes = notes[notes.length - 1].at;
					a.seenNotes = Math.max(a.seenNotes || 0, a.handedNotes);
				}
				if (request) a.request = { ...a.request, handed: now };
				h.save(a);
			}
		}
		return { files, notes, request };
	},

	pick_up(h, args) {
		need(args, "id");
		const f = h.sql.exec("SELECT name, type, base64 FROM files WHERE id = ?", String(args.id)).toArray()[0];
		if (!f || f.base64 == null) throw new Refusal("no such file");
		h.sql.exec("UPDATE files SET status = 'picked', picked = ?, picked_by = COALESCE(?, cat) WHERE id = ?",
			Date.now(), args.agent ? String(args.agent) : null, String(args.id));
		return { name: f.name, type: f.type, base64: f.base64 };
	},

	drop_file(h, args, charlotte) {
		if (!charlotte) throw new Refusal("only Charlotte drops files on a cat");
		need(args, "name", "base64", "for");
		const b64 = String(args.base64);
		if (b64.length % 4 || !/^[A-Za-z0-9+/]*={0,2}$/.test(b64)) throw new Refusal("base64 isn't valid");
		const size = (b64.length / 4) * 3 - (b64.endsWith("==") ? 2 : b64.endsWith("=") ? 1 : 0);
		if (size > MAX_FILE) throw new Refusal("files are capped at 1 MiB here: send bigger ones through the brain");
		h.sql.exec("UPDATE files SET base64 = NULL WHERE status = 'picked' AND picked < ?", Date.now() - KEEP_PICKED);
		const id = newId();
		h.sql.exec("INSERT INTO files (id, cat, name, type, size, note, at, status, base64) VALUES (?, ?, ?, ?, ?, ?, ?, 'waiting', ?)",
			id, String(args.for), String(args.name).slice(0, 200), String(args.type || "application/octet-stream").slice(0, 200),
			size, String(args.note || "").slice(0, 2000), Date.now(), b64);
		return { id, woke: false };
	},

	comment(h, args, charlotte) {
		need(args, "cat", "text");
		const author = args.author || (charlotte ? "charlotte" : "agent");
		if (!["charlotte", "agent", "session"].includes(author)) throw new Refusal("author is charlotte, agent or session");
		if (author === "charlotte" && !charlotte) throw new Refusal("only Charlotte writes as Charlotte");
		const note = { id: newId(), cat: String(args.cat), text: String(args.text).slice(0, 4000), author, at: h.stamp() };
		h.sql.exec("INSERT INTO notes (id, cat, author, text, at) VALUES (?, ?, ?, ?, ?)", note.id, note.cat, note.author, note.text, note.at);
		const a = h.agent(note.cat);
		if (a && author !== "charlotte") {
			a.seenNotes = note.at;   // an answer means everything she said before it was read
			h.save(a);
		}
		return { id: note.id, woke: false };
	},

	comments(h, args) {
		need(args, "cat");
		const limit = Math.min(Math.max(parseInt(args.limit, 10) || 50, 1), 500);
		const notes = h.sql.exec("SELECT id, cat, text, author, at FROM notes WHERE cat = ? ORDER BY at DESC LIMIT ?", String(args.cat), limit).toArray();
		return { notes: notes.reverse() };
	},

	manage(h, args, charlotte) {
		if (!charlotte) throw new Refusal("only Charlotte manages a cat");
		need(args, "cat", "action");
		const a = h.agent(String(args.cat));
		if (!a) throw new Refusal("no such agent");
		const act = args.action;
		if (!ACTIONS.includes(act)) throw new Refusal("action is " + ACTIONS.slice(0, -1).join(", ") + " or done");
		if (["rename", "move", "message"].includes(act)) need(args, "value");
		if (act === "rename") a.name = String(args.value).slice(0, 60);
		else if (act === "move") a.room = String(args.value).slice(0, 40);
		else if (act === "archive" || act === "unarchive") a.archived = act === "archive";
		else if (["pause", "resume", "wrap_up"].includes(act)) a.request = { action: act, at: Date.now() };
		else if (act === "done") delete a.request;
		h.save(a);
		if (act === "message") TOOLS.comment(h, { cat: a.id, text: args.value, author: "charlotte" }, true);
		return { ok: true, woke: false };
	},
};

export class House extends DurableObject {
	constructor(ctx, env) {
		super(ctx, env);
		this.sql = ctx.storage.sql;
		for (const q of [
			"CREATE TABLE IF NOT EXISTS agents (id TEXT PRIMARY KEY, data TEXT NOT NULL, updated INTEGER NOT NULL)",
			"CREATE TABLE IF NOT EXISTS notes (id TEXT PRIMARY KEY, cat TEXT NOT NULL, author TEXT NOT NULL, text TEXT NOT NULL, at INTEGER NOT NULL)",
			"CREATE INDEX IF NOT EXISTS notes_by_cat ON notes (cat, at)",
			"CREATE TABLE IF NOT EXISTS files (id TEXT PRIMARY KEY, cat TEXT NOT NULL, name TEXT NOT NULL, type TEXT NOT NULL, " +
				"size INTEGER NOT NULL, note TEXT NOT NULL, at INTEGER NOT NULL, status TEXT NOT NULL, handed INTEGER, picked INTEGER, " +
				"picked_by TEXT, base64 TEXT)",
			"CREATE INDEX IF NOT EXISTS files_by_cat ON files (cat, status)",
			"CREATE TABLE IF NOT EXISTS wrong_passwords (at INTEGER NOT NULL)",
		]) this.sql.exec(q);
	}

	/** One tool call. `who` is "charlotte" (signed in through claude.ai) or "agent" (holds CATIO_TOKEN). */
	call(name, args, who) {
		const tool = Object.hasOwn(TOOLS, name) && TOOLS[name];
		if (!tool) return { unknown: true };
		try {
			return { ok: tool(this, args && typeof args === "object" && !Array.isArray(args) ? args : {}, who === "charlotte") };
		} catch (e) {
			if (e instanceof Refusal) return { error: e.message };
			throw e;
		}
	}

	agent(id) {
		const row = this.sql.exec("SELECT data FROM agents WHERE id = ?", id).toArray()[0];
		return row ? JSON.parse(row.data) : null;
	}

	save(a) {
		this.sql.exec("INSERT INTO agents (id, data, updated) VALUES (?, ?, ?) ON CONFLICT (id) DO UPDATE SET data = excluded.data, updated = excluded.updated",
			a.id, JSON.stringify(a), a.updated || 0);
	}

	// A note's time, never the same as the last one's: a Worker's clock stands still within a request, and
	// "what she said since" is counted by it.
	stamp() {
		const last = this.sql.exec("SELECT MAX(at) AS at FROM notes").one().at || 0;
		return Math.max(Date.now(), last + 1);
	}

	// The sign-in page's lock: five wrong passwords in a quarter of an hour, and it waits.
	locked() {
		return this.sql.exec("SELECT COUNT(*) AS n FROM wrong_passwords WHERE at > ?", Date.now() - LOCK_FOR).one().n >= LOCK_AFTER;
	}

	wrongPassword() {
		this.sql.exec("DELETE FROM wrong_passwords WHERE at <= ?", Date.now() - LOCK_FOR);
		this.sql.exec("INSERT INTO wrong_passwords (at) VALUES (?)", Date.now());
	}

	rightPassword() {
		this.sql.exec("DELETE FROM wrong_passwords");
	}
}
