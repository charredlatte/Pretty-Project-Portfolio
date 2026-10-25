// The Catio's tools, as MCP lists them. The same names, arguments and results as harness/mcp/catio_mcp.py,
// so the page and the agents talk to the gateway exactly as they talk to the server on her computer.

export const MOODS = ["needs", "busy", "review", "failed", "done"];

const S = { type: "string" };
const said = (description) => ({ type: "string", description });

const tool = (name, description, properties = {}, required = []) =>
	({ name, description, inputSchema: { type: "object", properties, required } });

// One question for the decide tool. It is spelled out here because a caller that guesses the key (question, prompt,
// ask) used to reach the model with no text at all, which the model then refused for a reason naming nothing the
// caller did wrong. decide.js accepts those spellings too, but the schema is what stops the guess.
const QUESTION = {
	type: "object",
	properties: {
		type: { type: "string", enum: ["noul", "choice", "score"], description: "noul is yes/no, choice is one of named options, score is a level on a scale" },
		instructions: said("The question to ask about the state"),
		criteria: { description: "A choice: {option: what it means}, 2 to 64 of them. A score: an ordered list of 2 or more levels, lowest first. A noul: nothing, or {true: what yes means, false: what no means}" },
	},
	required: ["type", "instructions"],
};

export const TOOLS = [
	tool("house_rules", "The KittyChat house rules every agent in the Catio follows. Read them when you start."),
	tool("report_status",
		"Join the Catio as a cat, or update your cat: what you're working on and whether you need the owner. " +
		"Call it when you start, when you need them, and when you finish. Returns what's waiting for you.",
		{
			agent: said("Your stable id, e.g. codex-shop"), name: S, model: said("e.g. gpt-5, gemini-2.5-pro"),
			provider: said("openai, google, anthropic, local..."), title: S, project: S, repo: said("owner/repo"),
			branch: S, mood: { type: "string", enum: MOODS }, ask: said("What you need from the owner, when mood is needs"),
			link: S, session: said("Your own session id"), via: said("What you run in, e.g. claude-code"), cwd: S,
			wake: { type: ["array", "null"], items: S, description: "Ignored here: the gateway can't run commands. Check inbox instead." },
		},
		["agent"]),
	tool("audit", "Save a repository's opening audit, the read-only pass the house rules ask for at the start of a " +
		"session. The café shows it in that project's filing cabinet, so it reaches the owner where she already looks. " +
		"Writing it again replaces the one before, so a later session's audit is the one she sees.",
		{ repo: said("owner/repo, or the repository's name"), summary: said("The top findings, one line each"),
			by: said("Who audited, when it is not you: your session or agent id") },
		["repo", "summary"]),
	tool("graph", "Save a repository's project map: the graphify digest the house rules ask you to build before you " +
			"dig. The café shows it in that project's filing cabinet -- the map and its neighbourhoods, its hubs, the " +
			"surprising links, and the questions the owner can put to a cat with one click. Writing it again replaces " +
			"the one before.",
		{ repo: said("owner/repo, or the repository's name"),
			doc: { type: "object", description: "The document graph_doc.py prints after the document id, or the catio-graph.json it saves beside the graph" },
			by: said("Who built it, when it is not you: your session or agent id") },
		["repo", "doc"]),
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
		"A typed decision about a state: named typed questions in, one typed answer each out, no prose, in milliseconds for a " +
		"fraction of a cent. A noul answers yes/no as noul, the probability of yes. A choice answers with the option picked, a " +
		"probability for each option, and a confidence. A score answers with score, the probability-weighted level on the " +
		"criteria's own scale (0 to the last level), and a confidence: one number, not a probability per level. Every question " +
		"carries instructions, the question in words, and is refused without them. Any model can answer: Clef and Jev take the " +
		"questions themselves, any other model is prompted for the same answers instead. preset easy asks the six questions of " +
		"the easy-task rubric about state. With kind, the decision is logged beside old (what you would have chosen), with which " +
		"model answered and how.",
		{ state: { description: "The text or JSON the questions are about" },
			questions: { type: "object", additionalProperties: QUESTION,
				description: "Named questions: {<name>: {type, instructions, criteria}}. instructions is the question in words, and every question needs it; criteria belongs to a choice ({option: what it means}) or a score ([ordered levels])." },
			preset: { type: "string", enum: ["easy"] },
			model: said("Any model. @cf/cloudflare/clef-flash (default), @cf/cloudflare/clef and typesafe/jev take the questions themselves; any other is prompted for the same answers"),
			kind: said("A label for the log, e.g. sort"), old: said("What the old path chose, for the log"),
			floor: { type: "number", description: "For the log: the confidence under which you would not act on the answer (it then neither agrees nor disagrees with old). Compared against the answer's confidence, not a choice's winning probability: on a choice the two differ, and the confidence is the lower" },
			ref: said("For the log: what was decided about (the page's brain id), to check the decision against what happened") },
		["state"]),
	tool("tokens", "The café's colours and sizes as a design tokens file (the W3C format Figma's variables import as a mode), " +
		"as The look's Export tokens writes it: mode light (the default) or dark.",
		{ mode: { type: "string", enum: ["light", "dark"] } }),
	tool("set_tokens", "Bring a design tokens file into the café's look (the owner or the queen), as The look's Import tokens… " +
		"does: a token is matched by its own name in any group (the café's own group wins a name found twice), aliases are " +
		"followed, a see-through colour or a size out of range is refused, and what isn't the café's is left out. With " +
		"replace, the file is the whole of that mode instead of laid over it. Returns what it did: tokens read, changed, " +
		"foreign, refused. Open cafés redraw at once.",
		{ mode: { type: "string", enum: ["light", "dark"] }, file: { type: "object", description: "The design tokens file, as JSON" }, replace: { type: "boolean" } },
		["file"]),
	tool("answer", "Hand homework in (the owner only): one answer per question, in order. An unblock quiz's answers reach the cat, as the owner's words, and the queen; a litterbox or decision card's are only kept, for filing.",
		{ quiz: S, answers: { type: "array", items: S } }, ["quiz", "answers"]),
];

export const INSTRUCTIONS = "The Catio is its owner's harness. Read house_rules, report_status when you start, need them, " +
	"or finish, and check inbox.";
