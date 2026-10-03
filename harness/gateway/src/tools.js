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
		"Set the owner homework (the queen, or the owner): a short quiz whose answers unblock a cat. One quiz per cat, 1 to 5 " +
		"questions, each with 2 to 6 concrete options to pick, or free for a written answer. The owner answers in the café; the " +
		"cat gets the answers as the owner's words, and the queen is told.",
		{ for: said("The cat it unblocks (its agent id), or empty for the house"), title: S,
			questions: { type: "array", items: { type: "object", properties: { q: S, options: { type: "array", items: S }, free: { type: "boolean" } }, required: ["q"] } } },
		["title", "questions"]),
	tool("quizzes", "The homework set for the owner: the open quizzes, oldest first (done: true lists the handed-in ones too).", { done: { type: "boolean" } }),
	tool("answer", "Hand homework in (the owner only): one answer per question, in order. The answers reach the cat, as the owner's words, and the queen.",
		{ quiz: S, answers: { type: "array", items: S } }, ["quiz", "answers"]),
];

export const INSTRUCTIONS = "The Catio is its owner's harness. Read house_rules, report_status when you start, need them, " +
	"or finish, and check inbox.";
