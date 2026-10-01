// Compare a presented key with a secret without leaking how much of it matched.
const enc = new TextEncoder();

export const MIN_SECRET = 16;

export async function sameSecret(given, secret) {
	if (!given || !secret || secret.length < MIN_SECRET) return false;
	const [a, b] = await Promise.all([given, secret].map((s) => crypto.subtle.digest("SHA-256", enc.encode(s))));
	return crypto.subtle.timingSafeEqual(a, b);
}
