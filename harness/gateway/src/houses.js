// What every part of the gateway agrees on about houses: the first one's name, whose a token is, and where a
// house's brain files are kept. Plain JavaScript, so a test can import it outside workerd.
export const FIRST_HOUSE = "house";   // the house there was before accounts: charlotte's

/**
 * The house a token opens and whether its holder owns it. A grant made before accounts carries only
 * {user: "charlotte"} and opens the first house as its owner; any other token without a house opens nothing.
 */
export function whose(props) {
	const p = props || {};
	if (p.house) return { house: p.house, owner: !!p.owner };
	return p.user === "charlotte" ? { house: FIRST_HOUSE, owner: true } : { house: null, owner: false };
}

const FILE_ID = /^[a-z0-9]+-[0-9a-f]{8}$/;   // as the café mints them; anything else (a colon, say) names no file

/** The KV keys a house's brain file may be under: its own, and, for the first house, the one from before accounts. */
export const fileKeys = (house, id) => !FILE_ID.test(id) ? [] : [`file:${house}:${id}`, ...(house === FIRST_HOUSE ? [`file:${id}`] : [])];
