# Accounts on the backend

Can the KittyChat Café have accounts, one café per person, on the backend it has? Yes, with three changes to
the gateway and nothing new in the stack. This was the recommendation of 2 October 2026; phase 1 is built
(below, "As built").

## The three changes

The gateway (`harness/gateway/`) already has every piece an account needs, each wired for one person:

| Piece | Today | For accounts |
|---|---|---|
| Sign-in | `@cloudflare/workers-oauth-provider`, one password secret, `userId: "charlotte"` | email and password per user; the token carries `props.user` |
| Data | one SQLite Durable Object, `HOUSE.idFromName("house")` | one `House` per user, `idFromName(user)`. `house.js` doesn't change |
| Agents' key | one `CATIO_TOKEN` secret, `props.user: "agent"` | a key per account, stored hashed; `resolveExternalToken` looks it up |
| The queen's key | a registry key with the role `queen`, seeded from the `CATIO_QUEEN` secret for the first account (her runner, `harness/runner`) | any account mints one from its café (`POST /api/keys {role: "queen"}`); the runner routes (`/api/runner/*`) and `/mcp` read the role, and the runner acts in that key's house |

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
2. **Sign-up and keys.** A sign-up form on the sign-in page, invite-only at first (built 5 October: invites an
   admin makes at `/invite`, single-use, a week each, rather than an `INVITE_CODE` secret; see "As built: sign-up");
   a `/keys` page after sign-in to mint an agent key, shown once. The onboarding's "How it works" step links
   there (`docs/onboarding/`).
3. **Later: a hosted page per account.** The Worker serves `catio/index.html` and the `/api/*` the page
   already speaks (`S.host = "api"`, built for `catio_mcp.py --serve`), behind a cookie session. Then a café
   needs no artifact at all. Not needed for the onboarding. Built for one account on 2 October
   (`src/cafe.js`, PR #32): the sign-in cookie, the café's documents and files in the house, the page with
   `cafe/runtime.js`; per account it is the same with `idFromName(user)`.

## As built: phase 1

- `harness/gateway/src/registry.js`: the `Registry` object, with `users`, `keys`, `logins` and the per-user
  lock. The House keeps only cats, notes, files and the café's documents.
- The password hash is PBKDF2-SHA-256 at **100,000 rounds, Workers' cap** (more throws `NotSupportedError`),
  computed **inside the Registry**: a Durable Object gets 30 s of CPU a request on every plan, where the free
  plan's Worker gets 10 ms. It is below OWASP's 600,000, so the 16-character minimum and the five-tries lock stay.
- Every token resolves to a user: the OAuth grant carries `{user, house, owner, admin}`, a bearer key is looked up
  by its hash, a café cookie too. A grant made before accounts carries only `{user: "charlotte"}` and still
  opens her house.
- The first account is bootstrapped from `CATIO_PASSWORD` and `CATIO_TOKEN` into `charlotte` (or `CATIO_HANDLE`),
  house `house`, admin, key `bootstrap`: nothing of hers moves; her connector and her hook keep working. The one
  thing the deploy does is sign her browsers out of the café, since cookies moved to the registry: she signs in
  again with the handle. The bootstrap happens once, into an empty registry, so a key she drops stays dropped;
  what the secrets got wrong shows on the sign-in pages until there is an account.
- Accounts are made by an admin signed in to the café (`POST /api/users`), who can also reset a password
  (`PUT /api/users/<id>`: browsers out, OAuth grants revoked, keys killed, the lock cleared). Never by a key: a
  key is in every session's environment, and a leaked one must not be able to become anyone's owner. A
  signed-in café mints, lists and drops keys (`/api/keys`, names unique per user). The handle `house` is kept.
  Self sign-up is built (below); a button for keys in the page is still phase 2.
- One handle's password tries run in turn, so five guesses in parallel lock like five in a row, and right
  sign-ins in flight together lock nobody. Known limit: all of them run in the one registry object; against a
  flood of made-up handles, a Cloudflare rate-limiting rule on `/login` and `/authorize` is the gateway's to add.
- A token that names no house opens none (`whose()` fails closed); only a grant made before accounts, with
  `{user: "charlotte"}` alone, opens the first house as its owner.
- Brain files are kept under their house's name in KV (`file:<house>:<id>`; the first house also reads the
  `file:<id>` from before accounts), so a delete needs no read. `src/houses.js` is what every part agrees on:
  the first house's name, whose a token is, where a house's files are; plain JavaScript, so
  `test/houses.test.mjs` checks the upgrade paths outside workerd.
- On the wire the owner is `owner` since 3 October (the notes' `author`, the tools' `who`, "the owner only" in the
  tools' wording); `charlotte` is still taken on write as the old name and stored as `owner`, the gateway's house
  and `catio_mcp.py`'s state rename old notes once, and the page reads both. **Order of shipping:** the gateway
  first (the merge deploys it, and it takes both names), the artifact's republish after: a page that writes
  `owner` to a gateway that doesn't take it yet is refused on every message. Before that it was `charlotte`: shared with
  the page and `catio_mcp.py`, so renaming it to `owner` everywhere is its own change.

## Sources

- Workers limits: https://developers.cloudflare.com/workers/platform/limits/
- Durable Objects limits and pricing: https://developers.cloudflare.com/durable-objects/platform/limits/ and
  https://developers.cloudflare.com/durable-objects/platform/pricing/
- KV limits: https://developers.cloudflare.com/kv/platform/limits/
- Web Crypto on Workers: https://developers.cloudflare.com/workers/runtime-apis/web-crypto/
- The PBKDF2 cap of 100,000 rounds: https://community.cloudflare.com/t/configure-pbkdf2-iteration-cap/848334

## As built: sign-up (5 October)

Her ask: "My account is admin. Create self-registration."

- An admin signed in to the café opens `/invite` (a server page of its own, so the café's page needs no button and no
  republish) and makes an invite: a 64-hex code, shown once as a link `/signup?invite=<code>`, kept only as its hash
  in the registry's `invites` table with who made it and when it lapses (a week). The same page counts the invites
  still out and takes them all back.
- `/signup` takes the invite, a handle, a password and the password again, makes the account (never an admin, a
  house named after the handle) and signs that browser in. `Registry.signUp` spends the invite before the password is
  hashed, so two sign-ups with one code at once let one in, and gives it back when the account can't be made.
- Both forms are refused from another site's Origin; the café's cookie is `SameSite=Strict` besides.
- For an AI setting it up for someone (her ask: "a link I can share with my partner so that his AI can mint his own
  key"): `/signup` with an invite says what to do, and `POST /signup` as JSON `{invite, handle, password, name}` makes
  the account the same way and answers with its first agents' key, once, instead of signing a browser in.
- No open sign-up: every account is a house on her Worker. The licensed art is now served to the first house alone,
  since the packs' licences are personal and an invite puts the café in a stranger's hands.
- Tested in `harness/gateway/test/gateway.test.mjs` ("lets an admin invite someone, who makes their own account
  with it, once").

