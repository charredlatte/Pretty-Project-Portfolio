// Secrets: hashes for keys and cookies, the password hash, and comparing two hashes without leaking how much of
// them matched. Everything here is Web Crypto, built into Workers.
const enc = new TextEncoder();

export const MIN_SECRET = 16;

const hex = (buf) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");

/** SHA-256 of a string, as hex: how keys and cookies are stored (never the thing itself). */
export const sha256 = async (s) => hex(await crypto.subtle.digest("SHA-256", enc.encode(s)));

/** 32 random bytes, as hex: an agent's key, a browser's cookie, a password's salt. */
export const randomToken = () => hex(crypto.getRandomValues(new Uint8Array(32)));

/** Two hex digests of the same length, compared in constant time. */
export const sameHash = (a, b) => a.length === b.length && crypto.subtle.timingSafeEqual(enc.encode(a), enc.encode(b));

// PBKDF2-SHA-256 at 100,000 rounds: Workers' cap (more throws NotSupportedError). It is below OWASP's 600,000, so
// passwords stay 16 characters or more and a sign-in locks after five wrong tries. It runs inside the Registry
// object, whose budget is 30 s of CPU a request, not the Worker's 10 ms on the free plan.
export const ROUNDS = 100000;

export async function hashPassword(password, salt) {
	const key = await crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", false, ["deriveBits"]);
	return hex(await crypto.subtle.deriveBits({ name: "PBKDF2", hash: "SHA-256", salt: enc.encode(salt), iterations: ROUNDS }, key, 256));
}
