// The house: every cat the gateway knows, their conversations and the files waiting for them, in one
// SQLite-backed Durable Object. The tools behave as harness/mcp/catio_mcp.py's do, with two differences:
// nothing here can run a wake command, and only Charlotte (signed in through claude.ai) speaks as herself.
// Agents and session hooks, which hold CATIO_TOKEN, report and answer. The queen of the house, whose runner
// holds CATIO_QUEEN (harness/runner), answers Charlotte as "queen", tells cats and manages them for her.
import { DurableObject } from "cloudflare:workers";
import RULES from "../../rules.json";
import { MOODS } from "./tools.js";
import { BadQuestion, NoAnswer, confidence, decide, verdict } from "./decide.js";

const FIELDS = ["name", "model", "provider", "title", "project", "repo", "branch", "ask", "link", "session", "via", "cwd", "room"];
const MAX_FILE = 1024 * 1024;   // a free Worker gets 10 ms of CPU a request: bigger files go through the brain
const KEEP_PICKED = 7 * 24 * 3600 * 1000;   // a picked-up file keeps its bytes a week, then only its record
const ACTIONS = ["rename", "move", "archive", "unarchive", "pause", "resume", "wrap_up", "message", "done"];
const QUEEN = "queen";          // the queen's cat: her conversation with Charlotte, and her runner's presence
const HOLD = 25 * 1000;         // how long the runner's wait is held before it comes back empty
const AWAY = 90 * 1000;         // a runner silent this long is back when it next waits: the cafés are told
const DAY = 24 * 3600 * 1000;
const DEFAULT_TZ = "Europe/Paris";
const OWNER = "owner";          // the house's owner on the wire; "charlotte" was the name before accounts
const SAYS = [OWNER, "queen"];   // whose notes a cat's hook is handed: the owner's, and her assistant's

class Refusal extends Error {}   // bad arguments: the caller is told, nothing breaks
const CHANGES = new Set(["report_status", "comment", "drop_file", "pick_up", "manage", "quiz", "answer", "forget"]);   // tools that change what a café shows
const KEEP_DECISIONS = 500;    // the observe log: the latest decisions, beside what the old path chose
const QUIZ = { questions: 5, options: 12, text: 300, title: 120, answer: 1000, note: 4000 };
// What a quiz is for: unblocking a cat (her homework), sorting a litter box note, or a decision waiting on her
const QUIZ_KINDS = ["unblock", "litterbox", "decision"];
// What a session files for its repository's filing cabinet (save_report): its audit and its project map
const REPORT = { summary: 4000, map: 256 * 1024, questions: 5, question: 200 };
// a repository's slug, as graph_doc.py makes it: the name after the owner, lowercase, a-z 0-9 _ and -
const slugOf = (repo) => String(repo).split("/").pop().toLowerCase().replace(/[^a-z0-9_-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 80) || "none";

// Homework, as the queen sets it: a title and 1 to 5 questions, each with concrete options or a written answer
function quizOf(args) {
	need(args, "title");
	const qs = Array.isArray(args.questions) ? args.questions : [];
	if (!qs.length || qs.length > QUIZ.questions) throw new Refusal("questions is a list of 1 to 5 {q, options, free}");
	const questions = qs.map((x) => {
		const q = x && typeof x === "object" ? x : { q: x };
		const text = String(q.q || q.question || "").trim().slice(0, QUIZ.text);
		if (!text) throw new Refusal("every question needs its q");
		const options = (Array.isArray(q.options) ? q.options : []).map((o) => String(o).trim().slice(0, QUIZ.text)).filter(Boolean).slice(0, QUIZ.options);
		return { q: text, options, free: q.free === true || !options.length };
	});
	if (args.kind && !QUIZ_KINDS.includes(args.kind)) throw new Refusal("kind is unblock, litterbox or decision");
	const kind = args.kind || "unblock";
	if (kind !== "unblock" && (questions.length !== 1 || questions[0].options.length < 2)) throw new Refusal("a " + kind + " card is one question with 2 to 12 options");
	const clip = (k, n) => (args[k] ? String(args[k]).slice(0, n) : "");
	return { kind, title: String(args.title).trim().slice(0, QUIZ.title), questions, note: clip("note", QUIZ.note), from: clip("from", 200), hint: clip("hint", QUIZ.text), ref: clip("ref", 80).replace(/[^A-Za-z0-9_-]/g, "") };
}

function need(args, ...keys) {
	for (const k of keys) if (!String(args[k] ?? "").trim()) throw new Refusal(k + " is required");
}
const newId = () => Date.now() + "-" + crypto.randomUUID().slice(0, 6);
const parseNote = (r) => (r.routine ? { ...r, routine: JSON.parse(r.routine) } : (delete r.routine, r));

// ---- routines: "HH:MM on these days, in this time zone", read with Intl so a Worker needs no zone table ----
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
function zoneOf(tz) {
	try { new Intl.DateTimeFormat("en-US", { timeZone: tz }); return tz; } catch { return DEFAULT_TZ; }
}
// the wall clock in a zone at an instant
function zoned(tz, t) {
	const parts = {};
	for (const p of new Intl.DateTimeFormat("en-US", { timeZone: tz, hourCycle: "h23", weekday: "short", year: "numeric", month: "numeric", day: "numeric", hour: "numeric", minute: "numeric" }).formatToParts(new Date(t))) parts[p.type] = p.value;
	return { y: +parts.year, m: +parts.month, d: +parts.day, wd: WEEKDAYS.indexOf(parts.weekday), h: +parts.hour % 24, mi: +parts.minute };
}
// the instant a zone's wall clock shows y-m-d h:mi (a guess, corrected twice for the zone's offset and its changes)
function instantOf(tz, y, m, d, h, mi) {
	const want = Date.UTC(y, m - 1, d, h, mi);
	let t = want;
	for (let i = 0; i < 2; i++) {
		const p = zoned(tz, t);
		t -= Date.UTC(p.y, p.m - 1, p.d, p.h, p.mi) - want;
	}
	return t;
}
function routineTime(r) {
	const m = /^(\d{1,2}):(\d{2})$/.exec(String(r.time || ""));
	if (!m || +m[1] > 23 || +m[2] > 59) return null;
	const days = Array.isArray(r.days) && r.days.length ? r.days.map(Number).filter((d) => d >= 0 && d <= 6) : [0, 1, 2, 3, 4, 5, 6];
	return { h: +m[1], mi: +m[2], days, tz: zoneOf(r.tz) };
}
// the routine's latest firing at or before now (within a week), and its next one after now
function lastFire(r, now) {
	const t = routineTime(r);
	if (!t) return null;
	for (let back = 0; back <= 7; back++) {
		const p = zoned(t.tz, now - back * DAY);
		if (!t.days.includes(p.wd)) continue;
		const at = instantOf(t.tz, p.y, p.m, p.d, t.h, t.mi);
		if (at <= now) return at;
	}
	return null;
}
function nextFire(r, now) {
	const t = routineTime(r);
	if (!t) return null;
	for (let ahead = 0; ahead <= 7; ahead++) {
		const p = zoned(t.tz, now + ahead * DAY);
		if (!t.days.includes(p.wd)) continue;
		const at = instantOf(t.tz, p.y, p.m, p.d, t.h, t.mi);
		if (at > now) return at;
	}
	return null;
}

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

	// Every cat, with what it last said (its latest note by its session or agent): the page shows a cat handing
	// that to the queen when it is newer than what Charlotte has read.
	list_agents(h, args) {
		const waiting = new Map(h.sql.exec("SELECT cat, COUNT(*) AS n FROM files WHERE status = 'waiting' GROUP BY cat").toArray().map((r) => [r.cat, r.n]));
		const said = new Map(h.sql.exec("SELECT cat, text, MAX(at) AS at FROM notes WHERE author IN ('session', 'agent') GROUP BY cat").toArray()
			.map((r) => [r.cat, { text: r.text, at: r.at }]));
		const agents = h.sql.exec("SELECT data FROM agents ORDER BY updated DESC").toArray().map((r) => JSON.parse(r.data))
			.filter((a) => !a.archived || args.archived)
			.map((a) => ({ ...a, waiting: waiting.get(a.id) || 0, wakes: false, ...(said.has(a.id) ? { said: said.get(a.id) } : {}) }));
		return { agents };
	},

	// With mark, only what hasn't been handed over yet, and now it has: a session's Stop hook hands her notes,
	// requests and files in once each. Handing over keeps its own place (handedNotes), apart from what an answer
	// counts as read (seenNotes), so a note she sends while the session is answering still gets handed in.
	// A cat is handed what the owner and the queen say; the queen herself only what the owner says.
	inbox(h, args) {
		need(args, "agent");
		const id = String(args.agent);
		const a = h.agent(id);
		const mark = args.mark === true && !!a;
		const files = h.sql.exec("SELECT id, name, type, size, note, at FROM files WHERE cat = ? AND status = 'waiting'" +
			(mark ? " AND handed IS NULL" : "") + " ORDER BY at", id).toArray();
		const since = (a && (mark ? a.handedNotes ?? a.seenNotes : a.seenNotes)) || 0;
		const authors = id === QUEEN ? [OWNER] : SAYS;
		const notes = h.sql.exec("SELECT id, cat, text, author, at FROM notes WHERE cat = ? AND author IN (" + authors.map(() => "?").join(", ") +
			") AND at > ? ORDER BY at", id, ...authors, since).toArray();
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

	drop_file(h, args, who) {
		if (who !== OWNER && who !== QUEEN) throw new Refusal("only the owner drops files on a cat");
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

	// Who speaks: only the owner as owner, only the queen's runner as queen. What she says to the queen
	// wakes a waiting runner; what the queen says is kept with the routine that asked it, if one did.
	comment(h, args, who) {
		need(args, "cat", "text");
		// "charlotte" was the owner's name on the wire before accounts: still taken, stored as "owner"
		const author = args.author === "charlotte" ? OWNER : args.author || (who === OWNER ? OWNER : who === QUEEN ? QUEEN : "agent");
		if (![OWNER, "agent", "session", QUEEN].includes(author)) throw new Refusal("author is owner, agent, session or queen");
		if (author === OWNER && who !== OWNER) throw new Refusal("only the owner writes as the owner");
		if (author === QUEEN && who !== QUEEN) throw new Refusal("only the queen's runner writes as the queen");
		const note = { id: newId(), cat: String(args.cat), text: String(args.text).slice(0, 4000), author, at: h.stamp() };
		h.sql.exec("INSERT INTO notes (id, cat, author, text, at) VALUES (?, ?, ?, ?, ?)", note.id, note.cat, note.author, note.text, note.at);
		const a = h.agent(note.cat);
		if (a && !SAYS.includes(author)) {
			a.seenNotes = note.at;   // an answer means everything she said before it was read
			h.save(a);
		}
		if (note.cat === QUEEN && author === OWNER) h.wake();
		return { id: note.id, woke: false };
	},

	comments(h, args) {
		need(args, "cat");
		const limit = Math.min(Math.max(parseInt(args.limit, 10) || 50, 1), 500);
		const notes = h.sql.exec("SELECT id, cat, text, author, at, routine FROM notes WHERE cat = ? ORDER BY at DESC LIMIT ?", String(args.cat), limit).toArray().map(parseNote);
		return { notes: notes.reverse() };
	},

	// Charlotte or the queen manages a cat. On the queen herself, pause means stop the turn she is on: her
	// runner is told, and nothing is stored.
	manage(h, args, who) {
		if (who !== OWNER && who !== QUEEN) throw new Refusal("only the owner manages a cat");
		need(args, "cat", "action");
		const act = args.action;
		if (!ACTIONS.includes(act)) throw new Refusal("action is " + ACTIONS.slice(0, -1).join(", ") + " or done");
		if (String(args.cat) === QUEEN) {
			if (act !== "pause") throw new Refusal("the queen is set up in her card: only pause (stop her turn) goes through here");
			h.flag("queenStop", "1");
			h.wake();
			return { ok: true, woke: false };
		}
		const a = h.agent(String(args.cat));
		if (!a) throw new Refusal("no such agent");
		if (["rename", "move", "message"].includes(act)) need(args, "value");
		if (act === "rename") a.name = String(args.value).slice(0, 60);
		else if (act === "move") a.room = String(args.value).slice(0, 40);
		else if (act === "archive" || act === "unarchive") a.archived = act === "archive";
		else if (["pause", "resume", "wrap_up"].includes(act)) a.request = { action: act, at: Date.now() };
		else if (act === "done") delete a.request;
		h.save(a);
		if (act === "message") TOOLS.comment(h, { cat: a.id, text: args.value, author: who }, who);
		return { ok: true, woke: false };
	},

	// Homework: a quiz the queen (or Charlotte) sets for Charlotte, kept as quizzes/<id> documents, so an open café
	// shows them at once in the queen's quest log. An unblock quiz's answers go to the cat, as her words (its hook
	// hands them in), and to the queen, who sees to the rest. A litter box note or a decision (kind) is one card with
	// its note; her answer is only kept, for whoever files them (litterbox/quiz.py apply). A card with a ref is dealt
	// once: dealing it again replaces it while it is open, and leaves her answer alone once she has given it.
	quiz(h, args, who) {
		if (who !== OWNER && who !== QUEEN) throw new Refusal("only the queen or the owner sets homework");
		const { ref, ...z } = quizOf(args);
		const id = ref ? z.kind + "-" + ref : newId();
		const was = ref ? h.getDoc("quizzes/" + id) : null;
		if (was && was.status === "done") return { id, done: true };
		// dealt again while open: it keeps its place in the deck
		h.putDoc("quizzes/" + id, { for: args.for ? String(args.for).slice(0, 200) : "", ...z, by: who, at: was ? was.at : Date.now(), status: "set" });
		return { id };
	},

	quizzes(h, args) {
		const all = h.sql.exec("SELECT path, data FROM docs WHERE path LIKE 'quizzes/%'").toArray().map((r) => ({ id: r.path.slice("quizzes/".length), ...JSON.parse(r.data) }));
		return { quizzes: all.filter((z) => (args.done === true || z.status !== "done") && (!args.kind || (z.kind || "unblock") === args.kind)).sort((a, b) => (a.at || 0) - (b.at || 0)) };
	},

	// Cards she has answered and that have been filed: gone from the house (the queen or Charlotte, as for quiz)
	forget(h, args, who) {
		if (who !== OWNER && who !== QUEEN) throw new Refusal("only the queen or the owner clears homework");
		const ids = (Array.isArray(args.quizzes) ? args.quizzes : []).map(String).slice(0, 500);
		let gone = 0;
		for (const id of ids) {
			const z = h.getDoc("quizzes/" + id);
			if (!z || ((z.kind || "unblock") === "unblock" && z.status !== "done")) continue;   // an open quiz: a cat still waits on it
			h.dropDoc("quizzes/" + id); gone++;
		}
		return { forgotten: gone };
	},

	// A session's opening audit or project map, for its repository's filing cabinet. Anyone in the house may file one:
	// it is shown, never acted on, and each repository keeps only the newest of each.
	save_report(h, args, who) {
		need(args, "kind", "repo");
		const repo = String(args.repo).slice(0, 200), by = String(args.by || who).slice(0, 200);
		if (args.kind === "audit") {
			const summary = String(args.summary || "").trim();
			if (!summary) throw new Refusal("an audit needs its summary");
			if (summary.length > REPORT.summary) throw new Refusal("an audit's summary is " + REPORT.summary + " characters at most");
			const id = "audits/" + slugOf(repo);
			h.putDoc(id, { repo, at: Date.now(), by, summary });
			return { id };
		}
		if (args.kind === "map") {
			const map = args.map;
			if (!map || typeof map !== "object" || Array.isArray(map)) throw new Refusal("map is the document graph_doc.py writes");
			if (JSON.stringify(map).length > REPORT.map) throw new Refusal("a project map is 256 KB at most");
			// Its questions become buttons that ask a cat in her words, so one filed with an agent's key is held to what
			// graph_doc.py makes: a few, each one short line she reads whole before she clicks it.
			const questions = (Array.isArray(map.questions) ? map.questions : []).filter((q) => typeof q === "string")
				.map((q) => q.replace(/[\u0000-\u001f\u007f-\u009f\u2028\u2029]+/g, " ").trim().slice(0, REPORT.question)).filter(Boolean).slice(0, REPORT.questions);
			const id = "graphs/" + slugOf(repo);
			h.putDoc(id, { ...map, questions, repo, by, at: Date.now() });   // filed under the repo it names, by who filed it
			return { id };
		}
		throw new Refusal("kind is audit or map");
	},

	answer(h, args, who) {
		if (who !== OWNER) throw new Refusal("only the owner hands homework in");
		need(args, "quiz");
		const path = "quizzes/" + String(args.quiz);
		const row = h.sql.exec("SELECT data FROM docs WHERE path = ?", path).toArray()[0];
		if (!row) throw new Refusal("no such quiz");
		const z = JSON.parse(row.data);
		if (z.status === "done") throw new Refusal("that homework is handed in already");
		const given = Array.isArray(args.answers) ? args.answers.map((a) => String(a == null ? "" : a).trim().slice(0, QUIZ.answer)) : [];
		if (given.length !== z.questions.length || given.some((a) => !a)) throw new Refusal("answers is one answer per question, in order");
		h.putDoc(path, { status: "done", answers: given, answeredAt: Date.now() }, true);
		if ((z.kind || "unblock") !== "unblock") return { ok: true, told: false };   // a card is kept for filing, not told
		const text = "Homework handed in: " + z.title + "\n" + z.questions.map((q, i) => (i + 1) + ". " + q.q + " → " + given[i]).join("\n");
		const told = !!(z.for && h.agent(z.for));
		if (told) TOOLS.comment(h, { cat: z.for, text, author: OWNER }, OWNER);
		TOOLS.comment(h, { cat: QUEEN, text: text + (z.for ? "\n(for " + z.for + (told ? ", told)" : ", not a cat here)") : ""), author: OWNER }, OWNER);
		return { ok: true, told };
	},
	// A typed decision from a System One model (src/decide.js), for the one-bit questions the café asks: where a file
	// goes, whether a task is easy, who needs her first. Anyone in the house may ask. With kind, the decision is
	// logged as decisions/<id> beside old (what the old path chose), so a week of the two side by side says whether
	// to switch; agree compares the first question's verdict with old. With floor, a verdict less sure than it is the
	// decider not deciding (sure: false, agree: null), as the caller would treat it; ref names what was decided (the
	// page's brain id), so the log can be checked against where the file went in the end.
	async decide(h, args, who) {
		let out;
		try {
			out = await decide(h.env, args);
		} catch (e) {
			if (e instanceof BadQuestion) throw new Refusal(e.message);
			if (e instanceof NoAnswer) throw new Refusal(e.message);
			throw e;
		}
		if (args.kind) {
			const first = Object.keys(out.answers)[0];
			const got = verdict(out.answers[first]);
			const floor = typeof args.floor === "number" ? args.floor : null;
			const sure = floor == null ? true : confidence(out.answers[first]) >= floor;
			const old = args.old == null ? null : String(args.old).slice(0, 200);
			const id = newId();
			h.sql.exec("INSERT INTO docs (path, data, at) VALUES (?, ?, ?)", "decisions/" + id, JSON.stringify({
				at: Date.now(), kind: String(args.kind).slice(0, 40), by: who, model: out.model, preset: args.preset ? String(args.preset) : undefined,
				ref: args.ref == null ? undefined : String(args.ref).slice(0, 200), questions: Object.keys(out.answers), answers: out.answers,
				verdict: got, floor: floor ?? undefined, sure, old, agree: old == null || !sure ? null : got === old, usage: out.usage,
			}), Date.now());
			h.sql.exec("DELETE FROM docs WHERE path LIKE 'decisions/%' AND path NOT IN (SELECT path FROM docs WHERE path LIKE 'decisions/%' ORDER BY at DESC LIMIT ?)", KEEP_DECISIONS);
		}
		return out;
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
			// the café's own database, when it is served from here: one row a document, as the page keeps them
			"CREATE TABLE IF NOT EXISTS docs (path TEXT PRIMARY KEY, data TEXT NOT NULL, at INTEGER NOT NULL)",
			// small flags that must outlive the object: whether the queen's turn is to stop
			"CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
		]) this.sql.exec(q);
		// the sign-in lock and the café's cookies moved to the registry with accounts
		this.sql.exec("DROP TABLE IF EXISTS wrong_passwords");
		this.sql.exec("DROP TABLE IF EXISTS logins");
		// the owner's notes from before accounts were written as "charlotte": renamed once, the first time this wakes
		if (!this.flagged("notesOwner")) { this.sql.exec("UPDATE notes SET author = 'owner' WHERE author = 'charlotte'"); this.flag("notesOwner", "1"); }
		// the routine that asked for a note of the queen's, on houses built before she had any
		if (!this.sql.exec("PRAGMA table_info(notes)").toArray().some((c) => c.name === "routine")) this.sql.exec("ALTER TABLE notes ADD COLUMN routine TEXT");
		this.waiters = [];   // the runner's held waits: resolved when there is something for the queen to do
	}

	/** One tool call. `who` is "owner" (signed in through claude.ai or the café), "queen" (the house's queen runner,
	 * holding a key with that role) or "agent" (holds an agents' key). */
	async call(name, args, who) {
		const tool = Object.hasOwn(TOOLS, name) && TOOLS[name];
		if (!tool) return { unknown: true };
		try {
			const ok = await tool(this, args && typeof args === "object" && !Array.isArray(args) ? args : {}, who === OWNER || who === QUEEN ? who : "agent");
			if (CHANGES.has(name)) this.tell({ type: "agents" });   // an open café redraws its cats now, not at its next look
			return { ok };
		} catch (e) {
			if (e instanceof Refusal) return { error: e.message };
			throw e;
		}
	}

	// ---- the queen: her runner waits here for what to do, and streams what she says back ----

	/** Held until Charlotte writes to the queen, a routine comes due or her turn is to stop, or HOLD passes:
	 * {notes, routine, stop, character}. Each note and routine is handed out once. */
	async waitForQueen() {
		const a = this.agent(QUEEN);
		const back = !a || Date.now() - (a.updated || 0) > AWAY;
		if (this.presence(a && a.mood === "busy" ? "busy" : "done") || back) this.tell({ type: "agents" });   // she is back: the cafés show her
		this.armAlarm();
		let out = this.queenReady();
		if (!out) {
			await new Promise((resolve) => {
				const done = () => { this.waiters = this.waiters.filter((w) => w !== done); resolve(); };
				this.waiters.push(done);
				setTimeout(done, HOLD);
			});
			out = this.queenReady() || { notes: [], routine: null, stop: false };
		}
		return { ...out, character: this.character() };
	}

	queenReady() {
		if (this.flagged("queenStop")) {
			this.flag("queenStop", null);
			return { notes: [], routine: null, stop: true };
		}
		const { notes } = TOOLS.inbox(this, { agent: QUEEN, mark: true });
		const routine = this.dueRoutine();
		return notes.length || routine ? { notes, routine, stop: false } : null;
	}

	/** What the runner streams: a turn in progress reaches every open café; done, it is the queen's note. */
	queenSays(m) {
		m = m && typeof m === "object" ? m : {};
		const text = String(m.text || "").slice(0, 8000);
		const done = m.done === true;
		const routine = m.routine && typeof m.routine === "object" && m.routine.id
			? { id: String(m.routine.id).slice(0, 100), name: String(m.routine.name || "").slice(0, 100) } : null;
		// what she is doing, for the café's loading strip: the last few tools she reached for, passed on and never kept
		const steps = !done && Array.isArray(m.steps) ? m.steps.slice(-12).filter((s) => s && typeof s.tool === "string").map((s) => {
			const o = { tool: s.tool.slice(0, 60) };
			for (const k of ["cat", "action"]) if (typeof s[k] === "string") o[k] = s[k].slice(0, 60);
			return o;
		}) : undefined;
		const changed = this.presence(done ? "done" : "busy");
		let id = null;
		if (done && text.trim()) {
			id = newId();
			this.sql.exec("INSERT INTO notes (id, cat, author, text, at, routine) VALUES (?, ?, ?, ?, ?, ?)", id, QUEEN, QUEEN, text, this.stamp(),
				routine ? JSON.stringify(routine) : null);
		}
		this.tell({ type: "queen", turn: String(m.turn || "").slice(0, 60), text, done, routine, id, steps });
		if (changed || id) this.tell({ type: "agents" });
		return { ok: true, id };
	}

	/** The queen's presence: the agent record "queen", kept by her runner's calls (the page keeps it out of the
	 * cats). True when her mood changed. */
	presence(mood) {
		const a = this.agent(QUEEN) || { id: QUEEN, name: "The queen", via: "runner", provider: "anthropic", since: Date.now() };
		const changed = a.mood !== mood;
		a.mood = mood;
		a.updated = Date.now();
		this.save(a);
		return changed;
	}

	character() {
		const row = this.sql.exec("SELECT data FROM docs WHERE path = 'queens/house'").toArray()[0];
		const d = row ? JSON.parse(row.data) : {};
		const s = (k, n) => (typeof d[k] === "string" && d[k].trim() ? d[k].trim().slice(0, n) : null);
		return { name: s("name", 60), manner: s("manner", 2000), greeting: s("greeting", 500) };
	}

	wake() {
		const waiting = this.waiters.splice(0);
		for (const resolve of waiting) resolve();
	}

	flag(key, value) {
		if (value == null) this.sql.exec("DELETE FROM state WHERE key = ?", key);
		else this.sql.exec("INSERT INTO state (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value", key, String(value));
	}

	flagged(key) {
		return this.sql.exec("SELECT COUNT(*) AS n FROM state WHERE key = ?", key).one().n > 0;
	}

	// Routines are documents, routines/<id> {name, time: "HH:MM", days: [0-6], tz, prompt, on, last}, written by
	// the page. One is due when its latest firing is newer than the last it was handed out at: a missed one runs
	// once when the runner is back, never twice. The alarm wakes a waiting runner at the next firing.
	routines() {
		return this.sql.exec("SELECT path, data FROM docs WHERE path LIKE 'routines/%'").toArray().map((r) => [r.path.slice("routines/".length), JSON.parse(r.data)]);
	}

	dueRoutine(now = Date.now()) {
		for (const [id, r] of this.routines()) {
			if (!r.on) continue;
			const at = lastFire(r, now);
			if (at && at > (Number(r.last) || 0)) {
				this.putDoc("routines/" + id, { last: at }, true);
				return { id, name: String(r.name || id).slice(0, 100), prompt: String(r.prompt || "").slice(0, 4000), at };
			}
		}
		return null;
	}

	armAlarm() {
		const now = Date.now();
		let next = null;
		for (const [, r] of this.routines()) {
			if (!r.on) continue;
			const at = nextFire(r, now);
			if (at && (!next || at < next)) next = at;
		}
		if (next) this.ctx.storage.setAlarm(next);
		else this.ctx.storage.deleteAlarm();
	}

	async alarm() {
		this.wake();
		this.armAlarm();
	}

	// ---- the café, served from here: its documents, who is signed in, and the live line to each open café ----

	docs() {
		const out = {};
		for (const r of this.sql.exec("SELECT path, data FROM docs").toArray()) out[r.path] = JSON.parse(r.data);
		return out;
	}

	/** Write a document: replace it, or (merge) add fields to one that exists. False when merging into nothing. */
	putDoc(path, data, merge = false) {
		let next = data;
		if (merge) {
			const row = this.sql.exec("SELECT data FROM docs WHERE path = ?", path).toArray()[0];
			if (!row) return false;
			next = { ...JSON.parse(row.data), ...data };
		}
		this.sql.exec("INSERT INTO docs (path, data, at) VALUES (?, ?, ?) ON CONFLICT (path) DO UPDATE SET data = excluded.data, at = excluded.at",
			path, JSON.stringify(next), Date.now());
		this.tell({ type: "doc", path, data: next });
		if (path.startsWith("routines/")) { this.armAlarm(); this.wake(); }   // a routine added or switched on may be due
		return true;
	}

	getDoc(path) {
		const row = this.sql.exec("SELECT data FROM docs WHERE path = ?", path).toArray()[0];
		return row ? JSON.parse(row.data) : null;
	}

	dropDoc(path) {
		this.sql.exec("DELETE FROM docs WHERE path = ?", path);
		this.tell({ type: "doc", path, data: null });
		if (path.startsWith("routines/")) this.armAlarm();
	}

	/** The café's data, moved from claude.ai once: refused when the café already has any. */
	importDocs(docs) {
		if (this.sql.exec("SELECT COUNT(*) AS n FROM docs").one().n) return false;
		for (const [path, data] of Object.entries(docs)) this.sql.exec("INSERT INTO docs (path, data, at) VALUES (?, ?, ?)", path, JSON.stringify(data), Date.now());
		this.tell({ type: "reload" });
		return true;
	}

	// An open café keeps a WebSocket here, and hears every change as it happens. The Worker lets in only a
	// signed-in browser from the café's own address.
	fetch(request) {
		if (request.headers.get("Upgrade") !== "websocket") return new Response("Expected a WebSocket", { status: 426 });
		const [client, server] = Object.values(new WebSocketPair());
		this.ctx.acceptWebSocket(server);
		return new Response(null, { status: 101, webSocket: client });
	}

	webSocketMessage() {}   // the café only listens here: what it says goes through /api

	tell(message) {
		const text = JSON.stringify(message);
		for (const ws of this.ctx.getWebSockets()) {
			try { ws.send(text); } catch { /* it closed while we spoke */ }
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
}
