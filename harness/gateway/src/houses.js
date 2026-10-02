// What every part of the gateway agrees on about houses: the first one's name, and whose a token or a file is.
// Plain JavaScript, so a test can import it outside workerd.
export const FIRST_HOUSE = "house";   // the house there was before accounts: charlotte's

/** The house a token opens and whether its holder owns it. A grant made before accounts carries only {user: "charlotte"}. */
export function whose(props) {
	const p = props || {};
	return { house: p.house || FIRST_HOUSE, owner: p.owner ?? p.user === "charlotte" };
}

/** The house a brain file belongs to: one kept before accounts belongs to the first. */
export const fileHouse = (metadata) => (metadata && metadata.house) || FIRST_HOUSE;
