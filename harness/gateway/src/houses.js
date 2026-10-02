// What every part of the gateway agrees on about houses: the first one's name, whose a token is, and where a
// house's brain files are kept. Plain JavaScript, so a test can import it outside workerd.
export const FIRST_HOUSE = "house";   // the house there was before accounts: charlotte's

/** The house a token opens and whether its holder owns it. A grant made before accounts carries only {user: "charlotte"}. */
export function whose(props) {
	const p = props || {};
	return { house: p.house || FIRST_HOUSE, owner: p.owner ?? p.user === "charlotte" };
}

/** The KV keys a house's brain file may be under: its own, and, for the first house, the one from before accounts. */
export const fileKeys = (house, id) => [`file:${house}:${id}`, ...(house === FIRST_HOUSE ? [`file:${id}`] : [])];
