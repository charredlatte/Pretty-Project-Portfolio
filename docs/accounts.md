# Accounts on the backend

Can the KittyChat Café have accounts, one café per person, on the backend it has? Yes, with three changes to
the gateway and nothing new in the stack. This is the recommendation (2 October 2026); nothing here is built.

## The three changes

The gateway (`harness/gateway/`) already has every piece an account needs, each wired for one person:

| Piece | Today | For accounts |
|---|---|---|
| Sign-in | `@cloudflare/workers-oauth-provider`, one password secret, `userId: "charlotte"` | email and password per user; the token carries `props.user` |
| Data | one SQLite Durable Object, `HOUSE.idFromName("house")` | one `House` per user, `idFromName(user)`. `house.js` doesn't change |
| Agents' key | one `CATIO_TOKEN` secret, `props.user: "agent"` | a key per account, stored hashed; `resolveExternalToken` looks it up |
| The queen's key | one `CATIO_QUEEN` secret, `props.user: "queen"` (her runner, `harness/runner`) | one more key per account, role `queen`, stored the same way; the runner routes (`/api/runner/*`) look it up like the tools do |

The page needs nothing new: the `Catio` connector is OAuth per claude.ai user, so each person's page reads
their own house. GitHub needs nothing either: `list_repos` is Claude Code Remote's, per claude.ai user.

## The stack: what's there, and nothing else

- **Cloudflare Workers** (free plan): 100,000 requests a day.
- **Durable Objects, SQLite-backed** (the only kind on the free plan; 100,000 requests and 5 GB a day): the
  `House` per account, plus one new `Registry` object (`idFromName("registry")`) holding
  `users(id, email, pass_hash, salt, house, created)`, `keys(hash, user, name, created)` and the wrong-password
  lock per user (today's `wrong_passwords` table moves there).
- **Workers KV**: the OAuth library's grants, as now.
- **Web Crypto**: PBKDF2-SHA-256 through `crypto.subtle.deriveBits` for passwords; SHA-256 for key hashes, as
  `secret.js` already does. Built in.
- **No new dependency.** No auth service, no Postgres, no D1, no framework. D1 would add a binding and
  migrations for a table the Registry object holds just as well, and a second kind of storage beside the
  houses.

One limit to watch: **KV allows 1,000 writes a day on the free plan**, and every sign-in and token refresh
writes a grant. Fine for one person; past a few dozen accounts, the Workers Paid plan ($5 a month) lifts it.

## Three phases, each its own pull request

Each is under `harness/`, so each waits for Charlotte by the hold rule.

1. **Registry and per-account houses.** The `Registry` object; `authorize()` takes email and password and
   checks the Registry; `completeAuthorization` with the user's id; `serveMcp` opens
   `HOUSE.idFromName(user.house)`; `resolveExternalToken` finds the key's owner. Her account is created once
   from today's secrets, with `house: "house"`, so her data stays where it is. Then `CATIO_PASSWORD` and
   `CATIO_TOKEN` are retired. Tests in `harness/gateway/test/gateway.test.mjs`: two users, two houses, a key
   that only reaches its own house. `report.py` is unchanged: `CATIO_TOKEN` becomes the account's own key.
2. **Sign-up and keys.** A sign-up form on the sign-in page, invite-only at first (an `INVITE_CODE` secret);
   a `/keys` page after sign-in to mint an agent key, shown once. The onboarding's "How it works" step links
   there (`docs/onboarding/`).
3. **Later: a hosted page per account.** The Worker serves `catio/index.html` and the `/api/*` the page
   already speaks (`S.host = "api"`, built for `catio_mcp.py --serve`), behind a cookie session. Then a café
   needs no artifact at all. Not needed for the onboarding. Built for one account on 2 October
   (`src/cafe.js`, PR #32): the sign-in cookie, the café's documents and files in the house, the page with
   `cafe/runtime.js`; per account it is the same with `idFromName(user)`.

## Sources

- Workers limits: https://developers.cloudflare.com/workers/platform/limits/
- Durable Objects limits and pricing: https://developers.cloudflare.com/durable-objects/platform/limits/ and
  https://developers.cloudflare.com/durable-objects/platform/pricing/
- KV limits: https://developers.cloudflare.com/kv/platform/limits/
- Web Crypto on Workers: https://developers.cloudflare.com/workers/runtime-apis/web-crypto/
