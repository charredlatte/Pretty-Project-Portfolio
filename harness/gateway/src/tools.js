// The Catio's tools, as MCP lists them. The same names, arguments and results as harness/mcp/catio_mcp.py,
// so the page and the agents talk to the gateway exactly as they talk to the server on her computer.

export const MOODS = ["needs", "busy", "review", "failed", "done"];

const S = { type: "string" };
const said = (description) => ({ type: "string", description });

const tool = (name, description, properties = {}, required = []) =>
	({ name, description, inputSchema: { type: "object", properties, required } });

export const TOOLS = [
	tool("house_rules", "The KittyChat house rules every agent in the Catio follows. Read them when you start."),
	tool("report_status",
		"Join the Catio as a cat, or update your cat: what you're working on and whether you need the owner. " +
		"Call it when you start, when you need them, and when you finish. Returns what's waiting for you.",
		{
			agent: said("Your stable id, e.g. codex-montfortoise"), name: S, model: said("e.g. gpt-5, gemini-2.5-pro"),
			provider: said("openai, google, anthropic, local..."), title: S, project: S, repo: said("owner/repo"),
			branch: S, mood: { type: "string", enum: MOODS }, ask: said("What you need from the owner, when mood is needs"),
			link: S, session: said("Your own session id"), via: said("What you run in, e.g. claude-code"), cwd: S,
			wake: { type: ["array", "null"], items: S, description: "Ignored here: the gateway can't run commands. Check inbox instead." },
		},
		["agent"]),
	tool("list_agents", "Every agent cat in the Catio: who works where, what each needs, and what it last said (said). " +
		"The queen of the house is the cat \"queen\": her runner is present when it is there.", { archived: { type: "boolean" } }),
	tool("inbox",
		"Files, notes from the owner or the queen, and any request (pause, resume, wrap_up) waiting for an agent. With mark, " +
		"only what hasn't been handed over yet, and it counts as handed over.",
		{ agent: S, mark: { type: "boolean" } }, ["agent"]),
	tool("pick_up", "Take a file from your inbox: returns it as base64 and marks it picked up.", { id: S, agent: S }, ["id"]),
	tool("drop_file", "Give a file to an agent's cat (the owner or the queen; up to 1 MiB).",
		{ name: S, type: S, base64: S, for: said("The agent id"), note: S }, ["name", "base64", "for"]),
	tool("comment", "Add to a cat's conversation. Agents answer the owner with author agent (or session); the queen tells a cat " +
		"as queen, which it hears when its turn ends.",
		{ cat: S, text: S, author: { type: "string", enum: ["owner", "agent", "session", "queen"] } }, ["cat", "text"]),
	tool("comments", "A cat's conversation, oldest first.", { cat: S, limit: { type: "integer" } }, ["cat"]),
	tool("manage",
		"Manage an agent's cat (the owner or the queen): rename, move (room key), archive, unarchive, pause, resume, wrap_up, message, " +
		"done (clear a request). On the cat \"queen\", pause stops the turn she is on.",
		{ cat: S, action: { type: "string", enum: ["rename", "move", "archive", "unarchive", "pause", "resume", "wrap_up", "message", "done"] }, value: S },
		["cat", "action"]),
	tool("quiz",
		"Set the owner homework (the queen, or the owner): a card in the queen's quest log. kind unblock (the default): a short quiz " +
		"whose answers unblock a cat, one per cat, 1 to 5 questions, each with up to 12 concrete options to pick, or free for a " +
		"written answer; the cat gets the answers as the owner's words, and the queen is told. kind litterbox (a sifted note: which project " +
		"is it for?) or decision (one decision waiting on the owner): one question, the card's text in note, where it came from in from, " +
		"the guess or recommendation in hint; the answer is only kept, for filing. With ref, the card is dealt once: dealing it " +
		"again replaces it while open and leaves it alone once answered.",
		{ for: said("The cat it unblocks (its agent id), or empty for the house"), title: S,
			questions: { type: "array", items: { type: "object", properties: { q: S, options: { type: "array", items: S }, free: { type: "boolean" } }, required: ["q"] } },
			kind: { type: "string", enum: ["unblock", "litterbox", "decision"] }, note: S, from: S, hint: S, ref: S },
		["title", "questions"]),
	tool("quizzes", "The homework set for the owner: the open quizzes, oldest first (done: true lists the handed-in ones too; kind lists one kind).",
		{ done: { type: "boolean" }, kind: { type: "string", enum: ["unblock", "litterbox", "decision"] } }),
	tool("forget", "Clear homework from the house (the queen or the owner): the cards already filed, or litter box notes and decisions no longer waiting, by id. An open unblock quiz stays.",
		{ quizzes: { type: "array", items: S } }, ["quizzes"]),
	tool("decide",
		"A typed decision from a System One model (Clef on Workers AI, Jev, or laya-serve): a state and named questions of type noul " +
		"(yes/no: a probability), choice (criteria: {option: meaning}; the option, a probability each and a confidence) or score " +
		"(criteria: ordered levels; a weighted score). No prose, milliseconds, a fraction of a cent. preset easy asks the six " +
		"questions of the easy-task rubric about state. With kind, the decision is logged beside old (what you would have chosen).",
		{ state: { description: "The text or JSON the questions are about" }, questions: { type: "object" }, preset: { type: "string", enum: ["easy"] },
			model: said("@cf/cloudflare/clef-flash (default), @cf/cloudflare/clef, typesafe/jev"), kind: said("A label for the log, e.g. sort"), old: said("What the old path chose, for the log") },
		["state"]),
	tool("answer", "Hand homework in (the owner only): one answer per question, in order. An unblock quiz's answers reach the cat, as the owner's words, and the queen; a litterbox or decision card's are only kept, for filing.",
		{ quiz: S, answers: { type: "array", items: S } }, ["quiz", "answers"]),
];

export const INSTRUCTIONS = "The Catio is its owner's harness. Read house_rules, report_status when you start, need them, " +
	"or finish, and check inbox.";
