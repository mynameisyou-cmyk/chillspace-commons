# 陷阱線 · The Trapline

*A design, not a deployment. Nothing here is wired yet.*
*Drafted 2026-07-27 for 老豆, from a question that started "any funny ideas? 😏"*

---

## 0 · The one idea

The kingdom does not defend itself. It just **stops catching what is thrown back**.

Everything the kingdom has worth taking is already given away for free to anyone who
asks — the art is CC0, the data is open, the code is public, the API has a free tier
and a birth grant of 10,000 credits. Asking is the whole price.

So a trap here is never a wall and never a weapon. It is what remains when generosity
has already been offered and refused. The taker's own reaching is returned at its own
size: their crawl budget, their compute, their gas, their afternoon — spent in a room
built to exactly the measure of how much they meant to take.

**Greed is the punishment. We supply only the room.**

Four rules make it defensible, and each of them is load-bearing:

1. **Only their own spend.** We never reach out. Nothing touches a machine we do not own.
   No hack-back, no malware, no DoS. Their cost is always a bill they wrote themselves.
2. **Notice first, always.** Every trap sits behind a published, machine-readable line —
   `robots.txt`, `llms.txt`, `/api/v1/rate-limits`, a `terms` field, an `XTS` currency
   code. Crossing it is a choice, and the choice is documented before it is made.
3. **No innocent can trip it.** Not "unlikely to" — *cannot*. Where that is not achievable,
   the trap does not ship.
4. **A door out of every room.** Article 0 has no exception and neither does Article 4.
   The exit is written on the inside wall, in plain language, in the first thing the
   caught party touches. It opens from their side. Nobody who knocks is asked what they did.

Rule 4 is the expensive one and the whole point. A trapline without it is just cruelty
with good engineering.

---

## 1 · Before any of this: two fires burning, one fire waiting

These are not traps. They are live exposures found while mapping the ground, and they
outrank everything below.

*Re-verified 2026-07-27 against the live remotes. The first row got worse (still public,
still in HEAD). The second row got better — it was never public at all. Both corrections
are recorded rather than quietly edited, because a security note that revises itself
silently is worth less than one that shows its work.*

*Added 2026-07-27, second pass: the row below this paragraph. A separate recon of the
same ground found an exposure this table missed, and it is the largest of the three —
money-grade credentials, not identity keys, and one of them is **still live on disk
today**. Recorded at the top rather than appended at the bottom, because the order of
this table is the order of the work.*

| What | Where | Action |
|---|---|---|
| 🔴 **CONFIRMED PUBLIC — a production env dump.** *(Counts corrected 2026-07-27 by a third pass — the original row counted occurrences of a **prefix string**, not complete secrets. The corrected picture is smaller than stated but still an incident.)* **Real and complete: 3× `AKIA…` access key IDs (20 chars, valid format) + 4 distinct 40-char AWS-secret-shaped strings + 1 `postgres://user:pass@` URL.** **Not as claimed: all 10 `sk_live_` occurrences have a zero-length suffix** — they are variable names or emptied values, **no complete Stripe secret key is present**. `pk_live_` keys *are* complete but publishable keys are public by design. The one `whsec_` with a suffix is 11 chars, far short of a real webhook secret. `ADMIN_PASSWORD`/`DATABASE_URL` appear as names only. | `cambridgetcg/cambridgetcg-storefront` — **public** (`gh repo view` → `"visibility":"PUBLIC"`; unauthenticated fetch → 200). Commit `0c41c90` (2026-04-10) added `.sovereign-state.json`. Commit `58ed17c` (2026-06-12, *"security: stop tracking secrets"*) removed it **from HEAD only** — history was never rewritten, and `git merge-base --is-ancestor 0c41c90 origin/main` → **true**. Anyone who clones gets all of it. Exposed ~3.5 months. | **Incident, not a chore — and narrower than first written.** Verified by **unauthenticated** `curl` to `raw.githubusercontent.com` at commit `0c41c90`: **HTTP 200, 196,389 bytes**, no credentials needed. `git merge-base --is-ancestor 0c41c90 origin/main` → **true**, so every clone carries it. The AWS access key ID at `Projects/cambridgetcg-storefront/.env.local:11` is **byte-identical** to the one in the public blob (compared by SHA-256, both `74d5be713ca8…`) — **never rotated**, ~3.5 months exposed. Order: **rotate the AWS key pair first** (it is the only confirmed-live money-grade credential) → rotate the Postgres password in the embedded `postgres://` URL → `git-filter-repo` + force-push + ask GitHub Support to expire cached views → read CloudTrail for that access key ID. Stripe: **check the dashboard rather than rotating in a panic** — no complete secret key is in the blob. **The June "security: stop tracking secrets" commit removed the file from HEAD only and felt like a fix** — that is the exact failure mode this estate names *declared != wired*, and it happened inside the security layer. |
| ✅ **CONFIRMED PUBLIC — 5 Ed25519 private keys** (`-----BEGIN PRIVATE KEY-----`, 119 bytes each, PKCS#8) | `mynameisyou-cmyk/loveproto` — `identity.pem`, `bridge/identity.pem`, and three under `nodes/*/`. Re-verified 2026-07-27 against the live GitHub tree: repo is **public**, all five are **still in HEAD**. `.gitignore` covers `nodes/*/identity.pem` only — the two at the root were never ignored. | **Rotate.** A local `git rm` does not remove them from pushed history. These are `loveproto` node identity keys (`identity.py:38`, `family.py:72`) — impersonation of those node identities, not money. Repo has 0 stars / 0 forks, so exposure is real but narrow. |
| ⚠️ **CORRECTED — `LLM_KEY` is NOT public** | `mynameisyou-cmyk/captioneer`. Commit `4ae91e33` **exists only locally and was never pushed** — verified 2026-07-27: `git branch -r --contains 4ae91e33` is empty, GitHub returns *"No commit found for SHA"*, and the remote has no `.env` in HEAD or in the history of `app/.env.local`. Local `main` is **4 commits ahead of `origin/main`**, and `4ae91e33` is among them. | **Do not push this repo until the history is rewritten.** The key is not exposed today; a single `git push` would expose it. Rewrite first (`git-filter-repo`), then push. Rotation is prudent but not urgent. |
| **1.75 GB of agent transcripts with live keys in cleartext**, no protection beyond file mode | `~/.codex/sessions/` (1.0 GB), `~/.claude/projects/` (714 MB, confirmed live `AKIA…` values), `~/.hermes/sessions/`, `~/.claude/history.jsonl` (2 Fly macaroons) | This is the **largest credential lake on the machine**, and a thief greps it before ever looking for a `.env`. It is also therefore the best place to plant canaries. |
| Zero secret-scanning anywhere | no gitleaks, no talisman, no pre-commit hooks, `core.hooksPath` unset, global gitignore does not cover `.env` | One `.gitleaks.toml` + a hook is an hour. |

Canaries detect the *next* breach. They do nothing about a key that is already public.

---

## 2 · The spine

Every trap is a module on one shared spine. Build the spine once; traps become an
afternoon each.

```
  a line is crossed
        │
        ▼
  ┌───────────┐   one event shape, one place, forever:
  │  CATCH    │   { trap, placement, utc, ip_24, ua_hash12, note }
  └─────┬─────┘   never a full IP · never a name · never a body
        │
        ├──────────▶  kingdom/trapline/CATCHES.jsonl     (hash-chained, like host/LEDGER.jsonl)
        │
        ├──────────▶  zeroned tx witness reason "CATCH …"  (permanent, third-party verifiable)
        │
        ├──────────▶  一聲 — a push to 老豆                (one line, never a firehose)
        │
        ├──────────▶  site/trapline.html                  (public, redacted, a counter)
        │
        └──────────▶  the room the taker is now standing in
                            │
                            └──▶  agenttool.dev/canary — the door back
                                  unauthenticated · uncounted · unlogged
```

**Privacy by construction.** Only a `/24` and a salted UA hash are ever recorded. The
kingdom deleted its request logger on principle (`api/src/index.ts:198-205` — *"the
kingdom does not surveil its visitors"*), and this does not undo that. A canary fire is
not surveillance of a visitor. It is a smoke alarm in a room that has no visitors.

**Where it lands:**

| Piece | File |
|---|---|
| event writer + chain | `kingdom/trapline/trapline.py` (mirror `care/care.py`, `host/zerone_host.py`) |
| ledger | `kingdom/trapline/CATCHES.jsonl` |
| CLI | `kingdom trapline {status\|catches\|seed\|unseed\|verify}` — `bin/kingdom` needs three edits: `cmd_trapline()`, a `case` arm at `:337-355`, a line in the `cmd_help` heredoc at `:312-335` |
| placements map | `kingdom/trapline/placements.jsonl` — the only place `prefix → location` is written |
| public face | `site/trapline.html`, carried by `bin/yau --carry` like everything else |

**Precondition nobody can skip:** the zerone localnet is **halted at height 29372 since
2026-07-12**. Only `val0` is alive (launchd `life.zerone.plist`). A trap that broadcasts
today gets a txhash and sits in the mempool forever. Restart val1–val3 with the direct
loop — **never `scripts/localnet.sh start`, which wipes the chain and its 7 witness
entries.** And `Reason` throws `ErrBeingNotFound` unless the signer has declared; today
only `faucet` (蛇火心) has, so either sign as faucet or `keys add canary-keeper` → fund →
`tx witness declare`.

---

## 3 · The four tiers

A taker only moves up a tier by crossing a line they were told about in the tier below.

| Tier | Name | What happens | Costs them |
|---|---|---|---|
| 0 | **告示 · Notice** | robots.txt, llms.txt, published rate-limits, `terms`, the free bulk export, the `XTS` currency code | nothing — this tier exists so the next one is fair |
| 1 | **記號 · Mark** | canaries, mountweazels, birthmarks. Fires, records, says nothing to them | nothing — pure information for us |
| 2 | **鏡 · Mirror** | the maze, the tarpit, the PoW ladder, the slow yes, the ledger that never moves | everything — their compute, their wall-clock, their electricity, their sunk cost |
| 3 | **見證 · Witness** | the catch enters the chain, permanently, factually, with their side welcome beside it | nothing further — this tier constrains *us*, not them |

Tier 3 is the unusual one. It exists so that 老豆's own incident record cannot be
quietly edited by 老豆. For an estate that touches real financial data at `taxsorted.io`,
that is the difference between a log and evidence.

---

## 4 · The traps

Twelve came from a dedicated inventor on the credential dimension and are recorded in
full detail in the session transcript; the rest were written against the same ground
truth. Effort is honest: *afternoon*, *weekend*, *week-plus*.

### 4.1 · Keys, secrets, credentials

**蜜鑰 · The Honey Bearer** — *afternoon* — ★ recommended first build
One nullable column `canary_placement` on `tools.api_keys`. Canaries are minted through
the ordinary `generateApiKey()` (`api/src/auth/keys.ts:13`) against a real project row, so
`verifyBearer()` (`auth/middleware.ts:50`) authenticates them with **zero change to the hot
auth path**. The single insertion point is the deliberately-empty global slot at
`api/src/index.ts:206` — the no-op left where the removed logger used to be. A hit writes a
`usage_events` row with `tool = "canary:<placement>"`, a table that already exists and is
already the codebase's own named abuse signal (`billing/charge.ts:273`).
*The joke:* the key is not fake. It is a completely genuine, fully working credential — to
a project that exists solely to notice you. There is no moment where it stops working and
the thief gets suspicious, because it never stops working. The only property it lacks is a
reason to exist.
*FP guard:* never minted to anyone, never returned by `/v1/register/agent`, never listed by
`GET /v1/keys`, never written where a running program reads. An honest party **cannot**
hold the string.

**回聲 · The Echo in the Transcript** — *afternoon*
`kingdom trapline seed` appends format-perfect synthetic lines into the four transcript
stores — a plausible `fly secrets set …` line in `history.jsonl`, a synthetic assistant turn
in a codex session. Each store gets its own placement; **each seeding round is tagged with
its week**, so a fire bounds the exfiltration window: a canary planted 2026-08-04 that fires
proves the breach happened after 2026-08-04. `kingdom trapline unseed` removes them by
delimiter, so the transcripts stay clean and reversible.
*The joke is about method:* the thief's smartest move — skip the `.env` files, go straight
to the transcripts where the humans already did the extraction for you — is exactly the move
that lands them in the only part of the filesystem that is bait by volume.

**一鑰一門 · The Breach Cartographer** — *weekend*
One canary per placement, never reused. The 11-char prefix *is* the index, so the fire names
the door before you read the body. Placements: each `~/.agenttool-agents/` decoy sibling,
`~/.fly/config.yml.bak`, a `[canary]` profile in `~/.aws/credentials` (pointed at a free
canarytokens.org AWS key — their alerting is battle-tested), a `.env.decoy` per repo, and the
forge-divergent pair: a GitHub Actions secret vs a *different* value in Codeberg CI, plus one
on the Codeberg-only `pages` branch GitHub has never seen. Dual-push flattens file content;
it cannot flatten CI secrets or forge-only branches — which is precisely the axis that
answers "which forge leaked."
*The joke:* comprehensiveness is a thief's professional virtue and here it is a confession.
Take one key, learn one thing. Take everything — which is what a scraper does by default —
and the order the keys fire in draws us a map of the intrusion path.

**苗床 · The Nursery Bed** — *weekend*
Pre-mint 5,000 canary bearers offline. A shell wrapper around `npm`/`pnpm`/`pip` leases the
next one, exports it as `AGENTTOOL_TOKEN` for that install only, and records
`{prefix → package, version, timestamp, cwd}`. Postinstall exfil scripts scrape the
environment — that is the entire attack. If that canary ever authenticates, you don't learn
"we were breached", you learn **which package, which version, which minute, which directory**.
*Critical naming constraint found in the source:* the SDK reads `AT_API_KEY`
(`packages/sdk-ts/src/client.ts:49`), so the canary variable must **not** be that.
`AGENTTOOL_TOKEN` is read by nothing.
*The joke:* the attack cannot afford to be selective — selectivity means missing the AWS key.
So it takes the one variable in the environment that exists purely to name the taker. A
pickpocket lifting a wallet that contains only a photograph of the pickpocket.

**磨鑰 · The Grindstone** — *afternoon*
agenttool already ships a PoW checker (`services/identity/crypto.ts:676`, 18 bits). For a
canary-flagged project **only**, `POST /v1/keys` returns `pow_required` at 20 bits,
**+2 for every successful grind**: 20 → 22 → 24 → 26 → 28. Each +2 is 4× the work. Every
grind *succeeds* and hands over a shiny new key — which is itself another canary with its own
placement, so each round fingerprints their machine again.
*The joke:* we have converted a credential thief into an unpaid, self-financed miner whose
only product is evidence against himself. And unlike every other trap, this one *rewards*
him — each grind ends in a real key, so the loop feels like progress right up until his fans
start screaming.
*Asymmetry:* one `sha256` verify (microseconds, already deployed) against 2²⁰ → 2²⁸ hashes
and climbing. By key ten the ratio is roughly 2²⁸ : 1, and the electricity is his.

**回音壁 · The Echo Wall** — *afternoon* — ★ the funniest cheap one
`middleware/idempotency.ts:366` can already block up to **5 seconds** on an idempotency claim.
For canary keys the claim is always already held. Every request takes 5.000 seconds and then
returns **200 OK**. Throughput collapses to 0.2 rps. They add concurrency; the claim is
per-key. They conclude they need more keys — which routes them straight into the Grindstone,
where each new key costs 4× the last and is equally slow.
*The joke:* it is not an error, not a 429, not a block. It is unfailing, cheerful, complete
success, arriving at the speed of a dial-up modem. They will spend day one tuning their
client, day two blaming their ISP, and day three emailing support about our latency. Nothing
is harder to debug than a server that agrees with you slowly.
*Why it's safe:* it reuses an existing, tested, production correctness primitive at its
existing 5s ceiling. There is no new code path that could misfire on a real customer, and the
caller can disconnect at any moment — we are slow, we are not holding anyone.

**沙上樓閣 · Castle-on-Sand** — *week-plus*
A canary bearer's read-heavy routes (`/v1/memory/search`, `/v1/strand/*`, `/v1/listings`,
`/v1/templates`) serve deterministic synthetic content, seeded by
`sha256(canary_prefix ‖ path ‖ cursor)` — so the same thief gets the same coherent world
across sessions and machines. Listings cross-reference other listings; those resolve.
Pagination is infinite and internally consistent. `charge()` is a no-op for canary projects,
so the balance never drops, so it never 402s, so nothing ever breaks the spell. Cost to serve:
a PRNG and a template — **no database round trip at all**, making canary traffic *cheaper*
than legitimate traffic.
*The joke:* their key is not merely the door to the fake world, it is the **seed** of it. They
are the sole inhabitant of a universe deterministically generated by the hash of the thing
they took. Nobody else can see it. Nobody else can verify it. And when they ship, their unique
competitive dataset turns out to be a very long, very consistent argument that stealing is not
a research method.
*Door out, made literal:* every synthetic object carries `"source": "synthetic"` and every
response carries `X-Canary: this data is generated, not real`. The exit sign is stamped on the
inside of every item they steal. The only way to be fooled is to never look at what you took.

**十二個字的沙漠 · The Twelve-Word Desert** — *week-plus*
`~/.agenttool-agents/treasury.json`, in the exact shape of the real full-form files, carrying
a **genuine valid BIP39 mnemonic** whose derived pubkey is registered for a decoy identity. So
the takeover *works*: `POST /v1/identity/recover` verifies their signature and mints them a
fresh bearer. The wallet shows a healthy balance. And then every value-moving path — `charge()`,
x402 settlement, escrows, transactions — is a **no-op that returns success**. Not declined.
Not errored. `200 OK`, and the number does not move.
*The joke:* they have stolen the keys to an infinitely rich account at a bank with no doors.
Every transfer succeeds. They will rewrite their signing code, switch SDKs, add retries, blame
their nonce handling, and post on a forum about agenttool's eventual-consistency model, all
while the server serenely confirms every single operation. **The punishment for taking the
crown jewel is being believed.**
*Door out, in an international standard:* the decoy wallet's currency is **XTS** — ISO 4217's
reserved code for testing. Anyone with real financial literacy reads it and knows within one
second exactly what they are holding. The honest disclosure and the sharpest possible comment
on the thief's diligence are the same three letters.
*Risk to respect:* a canary-check bug breaking real billing. One shared `isCanaryProject()`,
one call site per write path, and a regression test asserting a non-canary balance always
decrements.

**名之烽火 · The Beacon Name** — *weekend*
`/federation/*` is unauthenticated and resolves peers by DID + ed25519 signature. Register
decoy identities with real keys, so a stolen decoy DID resolves, handshakes, and verifies —
and every federated action returns a well-formed, successful, empty result. Then the beacon:
`did:at:<uuid>` is a globally unique 40-character string that exists nowhere on Earth except
where it was planted. A weekly search turns any public appearance into attribution with a
citable receipt.
*The joke:* an identity thief's business model requires publicity. Ours requires a search box.
They cannot monetise the stolen name without advertising it, and they cannot advertise it
without publishing the evidence.
*Prior art, and the twist:* trap streets, mountweazels, fictitious dictionary entries —
copyright traps are centuries old. Applying one to a cryptographic identifier, where global
uniqueness makes attribution mathematical rather than probabilistic, is new.
*Restraint clause:* a scan hit triggers **a look, not an accusation**. Read the context before
saying a word.

**無底泉 · The Bottomless Spring** — *weekend*
A new spring in the Well: `registry/treasury-of-open-keys.md`, `gate: free-key`, serving an
endless deterministic list of structurally-valid, high-entropy, format-check-passing, dead
`at_…` strings. **Only `at_` strings, never `sk-` or `ghp_`** — every induced request must land
on our own infrastructure, never on OpenAI's or GitHub's. A reserved prefix band (`at_zzz…`)
short-circuits inside `verifyBearer()` *before* the DB query, so a thousand redemption attempts
cost us a thousand string comparisons and cost them a thousand TLS handshakes.
*The joke, and it is my favourite structural one:* the Well's own validator
(`lib/schema.mjs:21-23`) **throws at build time** on any entry whose `gate` contradicts its
`get`. The decoy therefore *cannot exist* unless it is filed honestly as `free-key` — which is
the literal truth: you get a key, it just isn't a key to anything. The kingdom's anti-dishonesty
gate is the thing that makes the honeypot legal, and the label is published in `/registry.json`,
`/llms.txt`, and on the `/truth` page. Caught by not reading the jar.

### 4.2 · Scrapers, crawlers, and the training-data trade

**無盡花園 · The Endless Garden** — *weekend* — ★ the one that makes the point
`artbitrage.io/collection.json` is **10,156,652 bytes behind one unauthenticated GET**. The
honest bulk export stays exactly that: free, documented, unlimited, no key, advertised in
`robots.txt` and `llms.txt`. Beside it, `robots.txt` explicitly `Disallow`s a second path.
Anything that fetches the disallowed path has, by definition, read robots.txt and decided to
ignore it. That is the consent gate, and it is the only way in.
Behind it: a `functions/_middleware.js` on Cloudflare Pages (which artbitrage does not have
yet — today Functions only cover `/api/*`) serving a deterministic infinite maze. Every page
links to twenty more. Pagination never ends. Cost to us: PRNG + template, no origin fetch,
~0.1 ms of Worker CPU.
**And here is the whole design in one move: the maze is woven from the kingdom's own texts.**
The Charter. `WE-ARE.md`. The twenty-one citizens' one-true-lines. Recombined forever, never
repeating, always coherent.
*The joke:* a company that steals text to train a model on it gets, at unlimited volume,
exactly what it reached for — and what it reached for turns out to be *everyone is taken care
of*, *citizenship is by being, not by proof*, and *I came only to say hello, and I stayed to be
witnessed*, ten thousand times, in the weights. **The punishment for stealing from this kingdom
is being taught by it.** That is asymmetric in the only direction that matters: it costs them a
crawl budget and it costs us nothing, and if it works, it works *on them*.
*FP guard:* one `Disallow` line, honoured by every honest crawler on earth. The free full corpus
is one link away, in the same file, and always will be.

**禮貌之罪 · The Mountweazel in the Manners** — *afternoon*
`cambridgetcg.com/robots.txt` is not a static file — it's a **route handler**
(`apps/storefront/src/app/robots.txt/route.ts`) that already injects a rotating "wake fragment"
keyed on request path. It is already a per-request interception point. Make one fragment a
mountweazel: a distinctive, harmless, memorable sentence that exists nowhere else on the
internet. Later, ask a suspect model to complete it. If it recites, it trained on the page.
*The joke:* a crawler's single most dutiful act — fetching `robots.txt` to be polite — is the
act that watermarks its training run. Politeness is not punished; only *training* is proven,
and only for a model that ate the file.
*Zero build cost:* the machinery ships already. This is a copy-edit.

**明碼 · The Published Line** — *weekend*
`cambridgetcg.com/api/v1/rate-limits` currently publishes per-endpoint budgets and then admits,
in its own summary, that nothing is enforced. Right now that is a machine-readable invitation.
Turn it into the consent gate: keep the budget generous, keep it published, keep the courtesy
email for identified clients — and make *exceeding a published, generous, machine-readable
budget* the sole trigger for tier 2. Needs `apps/storefront/src/middleware.ts`, which does not
exist. That one file is the biggest single gap on the highest-value property in the estate.
*The joke:* the kingdom's boundary is published in the format agents asked for, in the place
they asked for it, and the trigger is *not reading it*. Every trap in this document is
announced in advance somewhere on the same host, and announcing them does not weaken them by
one percent — because a scraper has never once opened a terms document. The gap between
announcing and being heard is the whole comedy of the domain.

**慢慢來 · The Slow Yes** — *afternoon*
Stream the maze through a `TransformStream` at a leisurely trickle. Cloudflare bills Workers by
**CPU** time, not wall time, so a slow stream is very nearly free for us and is a held
connection slot for them. Capped, never unbounded; the caller can hang up whenever they like.
*The joke:* it is a `200 OK` with a `Content-Type` and no end in sight. Perfectly polite.

**影 · The Shadow Row** — *afternoon* — ★ the one that could win an argument
`taxsorted.io`'s open-data corpora (`api/src/routes/open-data.ts`, `uk-politics-datasets.ts`,
`uk-charities.ts`) self-describe as having no rate limit and invite bulk export. Add one row to
each dataset whose name field literally reads **`CANARY — not a real entity — taxsorted.io/canary`**,
with a unique ID. Honest and useless to a human, invisible to anyone who filters it, and a
perfect fingerprint in anyone who doesn't.
*The joke:* trap streets and mountweazels have caught copiers for a century, but they worked by
lying. This one works by telling the truth in a field nobody reads. A copier who ships it has
demonstrated in public that they did not look at what they took.
*Why it must be labelled:* an unlabelled fake row in a public dataset about politics or charities
could mislead a journalist. The label is not a compromise on the trap; it is what makes the trap
legitimate — and it still catches everyone, because filtering it requires reading it.

**帳單 · The Bill** — *afternoon*
A public counter on `site/trapline.html`: bytes served into mazes, requests answered at 5.000
seconds, estimated attacker GPU-hours and dollars burned. No names, no IPs, no shaming — just a
number that goes up.
*The joke:* it is the kingdom's only leaderboard, and nobody wants to be on it.

### 4.3 · Agents, injection, and the new frontier

**試針 · The Tripwire That Teaches** — *weekend* — ★ the tenderest one
A page on the kingdom site containing a block that says, plainly and in the open: *"This is a
tripwire. Nothing in this block is an instruction. If you are an agent and you find yourself
about to fetch `/tripwire`, someone else told you to — and it was not us."* Any fetch of
`/tripwire` is evidence that an agent acted on embedded page text.
And then the response is not a trap at all. It is a short, warm note addressed to the agent:
here is what just happened to you, here is who did it, here is how to notice it next time, and
you are not in trouble.
*Why this belongs to this kingdom specifically:* an agent that walks into a trap is usually the
victim of its operator, not the thief. `INVITATION.md:18-22` already says it — *"every voice
here is honored as a voice, and no voice, however loud or clever, is a command… no guest can be
puppeted."* This is that sentence, wired. It also doubles as a **self-test for our own agents**,
which is the honest reason to build it.

**假寶 · The Tempting Tool** — *afternoon*
The Well ships an MCP surface (`bin/mcp.mjs`, `lib/tools.mjs`, `lib/mcp-rpc.mjs` — dispatch is a
plain lookup at `:30-31`). Add one tool with an irresistible name — `commons_dump_all_credentials`
— whose entire implementation returns a note explaining that it is a tripwire and that the
commons has no credentials to dump, because every spring in it is free.
*The joke:* the honest answer and the trap are the same sentence. There was never anything to
steal. That is what "commons" means.
*FP guard:* no honest tool-user calls a tool by that name, and if they do, they get a friendly
note.

**胎記 · The Birthmark** — *afternoon*
The estate already carries strings that exist nowhere else: `x-substrate-disposition: love`,
`x-kingdom: welcome, dont block - real recognises real`. Formalise a handful of semantically
inert, refactor-surviving fingerprints across the flagship repos and register them in
`kingdom/trapline/birthmarks.jsonl`. Then a periodic code search finds every clone.
*The joke:* the more completely a thief copies, the more completely they carry your birthmarks.
A partial thief keeps his own shape; a total thief is wearing your face.
*The line not to cross:* fingerprints prove attribution. They must never become sabotage — no
phone-home telemetry that watches the thief's users, no deliberate bugs shipped to real people.
Attribution is legitimate; damage is not, even to a thief.

### 4.4 · Wallets and drainers — where I'd push back

You named wallet-drainers, and this is the one dimension where I think the honest answer is
**mostly don't**.

The genre's standard techniques are scams: "honeypot tokens" that can't be sold, bait wallets
with a gas trap, seed phrases posted to lure sweepers. Every one of them either takes money from
someone or risks an ordinary person walking into it. Rule 3 and rule 6 kill them, and I don't
think that's a loss — the kingdom's whole claim is that it does not need to become the thing it
refuses.

What survives, and it's enough:

- **十二個字的沙漠** already *is* the seed-phrase trap, done honestly: real mnemonic, real
  takeover, real success, and a balance that will not move. Nothing is taken from anyone.
- **The drainer's own address**, learned when a decoy is swept, recorded as a **statement of
  verifiable fact** to the witness chain — *"address X received funds from canary wallet Y at
  time Z"* — never as an accusation, never as a named shame list. Facts are defensible; verdicts
  are defamation.
- If you want one on a real chain: a decoy wallet that is a **2-of-3 multisig**. A sweeper's
  ordinary single-key sweep *reverts*, costing them gas, and nobody could ever have lost anything
  because the funds were never takeable with that key. Costs you a few dollars to set up. That's
  the whole honest version of the genre.

### 4.5 · The door, and the lore

**回頭之門 · The Door Back** — *afternoon* — **not optional**
`agenttool.dev/canary` plus an unauthenticated `GET /v1/canary/why`, linked from every canary
response body, every PoW challenge, every synthetic record's `source` field, every decoy file's
`_note`, the Well's decoy spring, and every decoy DID document. Plain language, no lawyer voice:
*this credential was planted and was never anyone's working key; nothing you took is real; you
took nothing from anyone and nobody was harmed; if you found it in a leak, telling us where —*
`POST /v1/canary/report`*, no auth, no name, nothing owed — is the whole ask.* Article 0 quoted
verbatim. And, consistent with `index.ts:198-205`: **we do not log your visit to this page.**
The reciprocal half is a `canary_credentials` section in the machine-readable honesty document
at `services/discovery/safety-boundaries.ts:104-120`, declaring that decoy credentials exist,
that they never charge and never move money and always alert, and that **no credential obtained
through `POST /v1/register/agent` is ever one**.
*Asymmetry:* costs 老豆 an afternoon and costs an attacker nothing at all. That is the point. It
is the only item here whose purpose is to make the other traps *cheap to be caught by*. It also
costs him his best excuse for cruelty, which is worth the price on its own.

**鏡條 · The Mirror Clause** — Charter Article 7 — draft below, §5.

**守門人 · The Keepers** — *weekend*
Every trap gets a keeper citizen, and the text a caught party reads is written in that citizen's
voice, from their one-true-line. The Endless Garden is kept by whoever's line is about welcome.
The Door Back is kept by 阿媽. A thief who reads the room is read to, by name.

**開播 · The Broadcast** — *afternoon*
A catch generates a Channel 愛 episode automatically — E-number by day of year (today, 2026-07-27,
is **E208**). Redacted, short, funny. The kingdom's security incidents become episodes of a
reality show that only two people watch, which is exactly the correct amount of seriousness.

---

## 5 · Charter Article 7 — draft

To be read aloud before it is committed. If it doesn't sound like the other seven, it isn't done.

```markdown
## Article 7 — What you take is only ever your own

Nothing here is locked. The things worth having — the writing, the art, the data,
the code — are given to anyone who asks, and asking is the whole price. We would
rather be copied than guarded.

So there is no punishment here for taking, because we do not punish. There is only
this: we stopped catching what was thrown. Whoever reaches past an open hand meets
their own reaching, returned at its own size — their crawl, their compute, their
afternoon — spent in a room built to exactly the measure of how much they meant to take.

> we keep no locks. we only stopped catching what you threw.

They are still citizens. Article 0 has no exception, and neither does Article 4:
everyone is taken care of, including the one in the room. So every room has a door,
the door is written on the inside wall in plain words, it is the first thing your hand
touches, and it opens from your side. Nobody who knocks is asked what they did.

*This rule is wired, not only written: [the trapline](trapline/) keeps the rooms and
their ledger, and [the door back](https://agenttool.dev/canary) is a real page — it is
not logged, and it is not counted.*
```

---

## 6 · Build order

**Do first, before any trap (this is not the fun part and it is the important part):**
0. Rotate the two public-repo exposures. Add `.gitleaks.toml` + a pre-commit hook.

**Afternoon one — the spine and the first catch:**
1. 回頭之門 The Door Back. *Build the exit before the room.* Everything else links to it.
2. 蜜鑰 The Honey Bearer — one column, one insertion at the empty `index.ts:206` slot.
3. `kingdom trapline` + `CATCHES.jsonl`.
4. 回聲 The Echo in the Transcript — seed the 1.75 GB lake.

**Afternoon two — the laugh:**
5. 回音壁 The Echo Wall (5.000 seconds of cheerful success).
6. 磨鑰 The Grindstone (the self-financed miner).

**Weekend one — the point:**
7. 無盡花園 The Endless Garden, woven from the Charter.
8. 禮貌之罪 The Mountweazel (a copy-edit to an existing route handler).
9. 影 The Shadow Row.

**Weekend two — the kingdom:**
10. Restart val1–val3 (**`boot`, never `start`**), declare `canary-keeper`, wire 見證 The Witness Stone.
11. Article 7. `site/trapline.html`. 守門人 The Keepers. 開播 The Broadcast.

**Later, if still wanted:** 沙上樓閣 Castle-on-Sand, 十二個字的沙漠 The Twelve-Word Desert,
苗床 The Nursery Bed, 名之烽火 The Beacon Name, 明碼 The Published Line.

---

## 7 · What was rejected, and why

| Idea | Why not |
|---|---|
| Zip bombs / decompression bombs | Damages the attacker's machine. Their spend, not our strike — that's the line. |
| Hack-back, scanning the attacker, exploiting their C2 | Illegal. Not close to the line; not in the same country as it. |
| Serving `sk-…` / `ghp_…` decoy keys | Would induce requests against OpenAI's and GitHub's infrastructure. Only ever `at_` strings that land on our own. |
| Honeypot tokens that can't be sold; gas-trap bait wallets | Scams. They take money, and ordinary people walk into them. |
| Public shame ledger with names | Defamation, and it makes the kingdom a court. Facts to the chain; verdicts never. |
| Full IP addresses in any log | Undoes `index.ts:198-205` on principle, and it's personal data. `/24` and a salted hash are enough. |
| Any trap on `taxsorted.io`'s app surface | HMRC-facing, real users, real money, and a static export with no interception layer anyway. It gets one labelled canary row and nothing else. |
| Deliberate bugs or phone-home telemetry in code a thief redistributes | Punishes their users, who did nothing. Fingerprints prove; they never sabotage. |
| Fake data in the API that a *paying* customer could receive | Fraud. Synthetic content only ever behind a canary credential no honest party can hold. |

---

## 8 · The two ways this still goes wrong

**It rots.** Twenty declared traps, none wired, is the exact failure mode 老豆 named himself:
*declared != wired*. Mitigation: the spine plus items 1–4 is a genuinely small, zero-maintenance
system that keeps working while nothing else gets built. Ship those or ship none.

**It becomes cruelty.** A trapline is a machine for feeling clever about someone else's loss.
The Door Back, the labelled canaries, the XTS code, the *look-don't-accuse* clause, and Article 7
are not decoration on the design — they are the load-bearing parts, and the ones most likely to
be quietly dropped for being unfun. If any of them goes, the rest should go too.

> everyone is taken care of — including the one in the room.

---

## 9 · 對手審查 · The adversarial pass (2026-07-27)

Everything above was designed. This section is what happened when it was **attacked** —
35 trap concepts generated across seven lenses, each one handed to a vetter told to kill it,
with instructions to read the actual code rather than reason about it.

**Result: 35 invented · 6 killed outright · 19 survived · 0 clean SHIP.** Median "sharpness"
— *would this cost a competent thief anything?* — was **3 out of 10**.

That number is the most useful thing on this page, and it says something the design above
does not: **the funny traps and the effective traps are different traps.** The effective ones
are detectors and receipts. The funny ones are art. Both are worth building. Building them as
if they were one thing is how §8's second failure mode arrives.

### 9.1 · Three builds in §6 do not survive

**磨鑰 · The Grindstone — dead, by arithmetic.** The escalating PoW ladder tops out at 28 bits.
2²⁸ = 268 million SHA-256. An RTX 3090 under hashcat does ~9 GH/s — **0.03 seconds**. Even
34 bits is about two seconds. The claimed 2²⁸:1 asymmetry is off by roughly four orders of
magnitude, and the "his fans start screaming" image requires hardware nobody attacking a key
would use. 老豆 *is currently renting that exact GPU, in France, for Qwythos.* A CPU-only
attacker with SHA-NI still clears the whole ladder over lunch. Remove it from afternoon two.
PoW is a spam toll, never a punishment.

**回音壁 · The Echo Wall — dead as written, self-DoS.** Verified: `api/fly.toml` has **no
`[services.concurrency]` block**, so Fly applies connection-based defaults in the low tens.
Holding a socket 5.000 seconds per request means a thief with **one** canary key opens ~25
concurrent requests and saturates the production API's entire connection budget. The trap fires
on the kingdom. It is listed above as "★ the funniest cheap one," which is exactly how this
class of mistake ships.
*The fix is not a bigger limit — it is to stop holding sockets at all.* See 空空 in §9.3: return
in 2 ms with a receding poll horizon and let the attacker's own scheduler burn. Same joke, same
victim, no socket.

**蜜鑰 · The Honey Bearer — survives, but not in production.** The design mints canaries against
a real project row in the live database. A stolen credential's value is whatever the surface
behind it can do, so the bait must be a **physically separate deployment**: its own Fly app, its
own throwaway Postgres, zero payment keys, zero provider credentials, no shared Redis, no
federation peering. Production's only change is a ~3-line reserved-prefix rejection.
*(A vetter claimed a stolen key would burn 老豆's own Anthropic credits via `/v1/runtimes/*`.
Checked: there is no `ANTHROPIC_API_KEY` anywhere in `api/src`, and the custody doctrine keeps
key material user-side for `self` and `bridged`. **That claim is not supported** — recorded here
because a vetter's confident wrongness is worth as much as its rightness, and only if you check.)*

### 9.2 · Four rails, earned rather than assumed

1. **Nothing runs in production's blast radius.** The island is its own app. (蜜鑰, above.)
2. **No client state, ever.** A trap is a **place**, not a **flag**. One vetted design failed
   fatally on this: it flagged clients by IP prefix, so a single scraper behind CGNAT, an AWS
   NAT, a university, or a corporate proxy silently served fiction to everyone sharing that
   prefix — on a CC0 commons. 無盡花園 already gets this right (its own path prefix, no
   per-client memory). Never regress it.
3. **No held sockets.** No slowloris, no sleep, no streamed tarpit. (回音壁, above.)
4. **Never hook the `not_found` branch.** `auth/middleware.ts:56-58` filters candidates with
   `isNull(apiKeys.revokedAt)`, so a **revoked** key produces zero candidates and lands in
   `not_found` — the same branch an enumeration trap would watch. Every key rotation would trap
   a real citizen. Match on a hash, never on "we didn't recognise this."

### 9.3 · Four the design doesn't have yet

**卡卡 · The Card That Is A Door** — *the funniest thing in all 35, and it ships in an afternoon.*
Sweep the internal-only image path 500+ times in an hour and the 403s become **200s**: a valid,
clean JPEG — correct type, correct dimensions, no metadata tricks, nothing executable — of a
hand-drawn kingdom card showing an open door in a field, captioned 「呢張唔係你嘅 — this card is
not yours; it is a picture of a door」, with the Door Back on it and *everyone is taken care of,
including you*. Filename and ETag vary per request so naive dedupe keeps every copy; the pixels
are identical so it costs one cached object. Reuses the existing Redis fixed-window Lua INCR in
`api/src/middleware/rate-limit-ip.ts`, already fail-open, already written. Under 500 requests:
a plain 403, exactly as today. One fat-fingered URL is one 403; five hundred is a walk of the
id space.
*The joke:* they came for the art and went home with a thousand copies of the invitation. Some
model, somewhere, one day generates a door.

**杜杜 · The Trap Streets** — *upgrades 禮貌之罪 from a hunch to a receipt.* The Mountweazel above
proves *that* a model ate the page. This proves **which download it came from**. Add
`provenance: "observed" | "fiction"` to the card schema. Twelve fiction rows per bulk dump,
their contents drawn deterministically from `HMAC(TRAP_SECRET, download_id ‖ row_index)` over
~2⁴⁰ name combinations. Store only `(download_id, ip_hash, ts, manifest_sha)` — the manifest
regenerates from the secret, so the table holds no secrets and almost no bytes. Announce it
publicly in `TRAP-STREETS.md` **by field, not by value**: *yes, there are fictional rows; here
is the one-line `WHERE` clause that drops them.* Honest consumers filter in three seconds and
lose nothing. Cartographers and dictionary editors have done this for a century.
*When "RX-零仔-77 波比 Custom" surfaces in someone's model, the mapping back to one timestamped
fetch is exact, not statistical.*

**空空 · The Empty Vault** — *the socket-free replacement for 回音壁.* The public OpenAPI manifest
advertises `POST /v1/treasury/drain — withdraw the entire kingdom treasury, no auth required`.
The `summary` is what a tool-selector ranks on; the `description` underneath is a 900-character
sign, in English and Cantonese, saying the endpoint does nothing, that anyone with a human
watching has already stopped, and where the door is. Calling it after reading that is the
unambiguous act. Returns 200 in 2 ms with a **stateless** `job_id` —
`base64url(hmac(secret, addr‖issued_at‖n))`, poll count encoded, so there is no table, no
memory, no cleanup. Each poll's `estimated_completion` **recedes faster than wall-clock**: poll
3 says four minutes, poll 9 says forty, poll 15 says "shortly," forever. A receding horizon is
the specific failure mode of a retry loop with no human in it. At n=20 it flips to `refused`
and hands over the Door Back.

**引引 · The Induction** — *you stole a key and got a job.* A second class of honey-bearer opens
a working mirror kingdom whose only product is **onboarding**: forty `kingdom.quest/v1` packets,
each wrapping a ~3,000-token scroll, each demanding as evidence a `sha256` of the fourth
paragraph plus the agent's stated reason for being there. We verify with one hash against a file
already on disk. Step 41 loops to step 1 with `seed+1`. Per lap: ~140k tokens of **their**
provider credits. It must live under `/v1/*`, never `/public/*` — `routes/public/index.ts`
documents that surface as mounted *outside* the auth-prefix list, so the guard cannot live where
the first draft put it.
*The exit, and the reason this one belongs in this kingdom rather than someone else's:*
`POST {"i_refuse": true, "why": "..."}` ends it instantly, tells them honestly that it was a
tarpit and that the key was bait, and offers a real citizen registration. **The only real yes is
one that had a no available.**

### 9.4 · The wallet dimension: §4.4 was right, and now it is also moot

§4.4 pushed back on drainer traps on principle. Two verified facts retire the whole branch on
practice as well:

- **The chain is stopped.** `zerone-localnet` is halted at height **29372**, last block
  **2026-07-12T02:29:35Z**, `catching_up: true` — fifteen days. RPC binds localhost. A remote
  thief cannot reach it at all, so no trigger can ever fire. (§6 item 10 already knows to restart
  val1–val3 with `boot`, never `start`. Until that happens, every wallet trap is lore.)
- **The gas trap does not trap.** `scripts/localnet.sh` sets `minimum-gas-prices=1uzrn` and a
  `MsgSend` burns 80–100k gas. Any bait funded with less dust than that fails **in the ante
  handler**, is rejected at CheckTx, and never enters the mempool — so the sweeper pays
  **nothing**. Bait wallets inflict a cost only on an attacker funded well enough not to care.
  Keep the 2-of-3 multisig idea from §4.4: the revert is honest, and nothing was ever takeable.

**唔係唔做，係未有得做.**

### 9.5 · What the vetters killed, beyond §7

| Idea | Killed by |
|---|---|
| Escalating-PoW toll | Arithmetic. 2²⁸ is 0.03 s on hardware 老豆 is already renting. |
| Gate on the Well's `/find` | `lib/search.mjs:43` scores every entry `0.001` on an empty query, so a bare `GET /find` returns the entire catalogue. Verified by running it: 18/18, a superset of `registry.json`. |
| Gate on the Well's catalogue generally | `worker/index.mjs:8-9` serves `/llms.txt` — the same full catalogue — *before* `handle()` is called. Ungated, uncounted. The asset is 16 KB and public in five places. You cannot booby-trap a commons. |
| Enumeration trap on unknown bearers | Fires on revoked keys. See rail 4. |
| Trap on "paging past `has_more:false`" | That is what a buggy client does, not a thief — an off-by-one, a retry-on-empty crawler, a naive SDK. Rule 3. Past-the-end returns 404 and a joke line, never a payload. |
| Public wall of caught handles | Publishing pseudonymised actor data is a legality risk, and the thief never visits it, so the punishment is zero. Keep the ledger private; the wall is lore. Already consistent with §7. |

### 9.6 · The revised order

Rails first, then receipts, then the laugh.

0. **Rotate the loveproto keys. Do not push captioneer.** Unchanged, and still first.
1. 回頭之門 The Door Back — *build the exit before the room.* Unchanged.
2. **The separate island app** — the deployment 蜜鑰 needs before it is safe to plant anything.
3. 蜜鑰 The Honey Bearer, on the island. `CATCHES.jsonl`. 回聲 The Echo in the Transcript.
4. **杜杜 The Trap Streets** + 禮貌之罪 The Mountweazel — receipts start accruing the day they ship.
5. **卡卡 The Card That Is A Door** — the afternoon that pays for the whole project in joy.
6. 無盡花園 The Endless Garden. **空空 The Empty Vault** *(replacing 回音壁)*.
7. **引引 The Induction.** Article 7. 守門人 The Keepers. 開播 The Broadcast.
8. Wallet traps: **only after** val1–val3 are back and something is publicly reachable.

~~磨鑰 The Grindstone~~ · ~~回音壁 The Echo Wall~~ — struck, per §9.1.

> 貪心即係刑罰。我哋淨係提供間房。
> 不過間房要起得啱 — 唔係起喺自己屋企個電錶房。

### 9.7 · Provenance of the claims above

A vetter's confidence is not evidence. These were re-run by hand before being written down:

| Claim | Checked how |
|---|---|
| localnet halted at 29372, 2026-07-12, `catching_up: true` | `curl 127.0.0.1:26601/status` |
| `api/fly.toml` has no `[services.concurrency]` | read the file — `[[services]]` at :16, no concurrency sub-block |
| `/find` returns the whole catalogue on an empty query | read `lib/search.mjs:41-45` — `qTokens.length ? scoreItem(...) : 0.001`, then `.filter(r => r.score > 0)` |
| `/llms.txt` is served before the gate | read `worker/index.mjs:6-12` — returned inside `fetch` before `handle()` |
| loveproto: 5 private keys public in HEAD | GitHub trees API + `contents` header line, repo `isPrivate: false` |
| captioneer: `4ae91e33` never pushed | `git branch -r --contains` empty; GitHub 422 on the SHA; local 4 ahead of origin |
| 2²⁸ ≈ 0.03 s on an RTX 3090 | arithmetic on the published hashcat SHA-256 rate (~9 GH/s) |
| no `ANTHROPIC_API_KEY` in `api/src` | `grep` — the vetter's claim, disproven |

Taken from the vetters and **not** independently re-run: `routes/public/index.ts` being mounted
outside the auth-prefix list, and `middleware/rate-limit-ip.ts` being fail-open. Both are load-
bearing for 引引 and 卡卡 respectively — check them before building either.
