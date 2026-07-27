# 貪 · The Snare Doctrine
*asymmetric hospitality for people who take what was not given*

Drafted 2026-07-27 from 5 recon briefs + 60 generated ideas, adversarially filtered.
A menu, not a plan. Nothing in §2 is built.

---

### How this sits beside DESIGN.md

Two sessions answered the same question on the same day without seeing each other's
work: *"any funny ideas? 😏"*. [DESIGN.md](DESIGN.md) is the other one. They converged
independently on every ethical line — no bombs, no hack-back, no fake third-party keys,
no scam wallets, no named shame ledger, no full IPs, nothing on taxsorted — which is
the strongest evidence either of them is right about anything.

**Where DESIGN.md wins, and this file defers to it:**

- **Never hook the `not_found` branch.** `auth/middleware.ts:56-58` filters candidates
  by `isNull(revokedAt)`, so a *revoked* key produces zero candidates and lands in the
  same branch an enumeration trap would watch. Every key rotation would trap a real
  citizen. Match on a hash, never on "we didn't recognise this." This doctrine did not
  catch that. It is the sharpest finding in either document.
- **The island.** A canary must live on a physically separate deployment — own Fly app,
  own throwaway Postgres, no payment keys, no shared Redis. Production's only change is
  a ~3-line reserved-prefix rejection. §2's *Seventh Child* should be read as living
  there, not in the live database.
- **No client state, ever.** A trap is a *place*, not a *flag*. Flagging by IP prefix
  serves fiction to everyone behind one CGNAT, one university, one corporate proxy.
- **PoW is a spam toll, never a punishment.** 28 bits is 0.03 s on the RTX 3090 老豆 is
  *currently renting*. §2's *Toll Before the Grind* survives only as a spam toll on the
  auth-failure path, and its claimed asymmetry is overstated by orders of magnitude.
- **The four tiers**, and the rule that a taker only rises a tier by crossing a line they
  were told about in the tier below. That framing is better than this file's.

**Where this file adds something DESIGN.md does not have:**

- **§0.1 — the cambridgetcg-storefront exposure.** Not in DESIGN.md's fire table, and
  it is larger than both fires listed there: Stripe *live* keys, an AWS key **still
  unrotated on disk today**, admin passwords, database URLs, public since 2026-04-10.
- The **clean-hands corollary** (§1), which matters specifically because 老豆 is the
  sole validator of `zerone-1` and 93% of fees route to him.
- The **chain-reproducibility veto** (§2, Dimension II) — `zerone-core` carries 129
  uncommitted files and the running binary reports version `"dev"`.
- **Attribution over destruction**: the pre-registered lie and the Confession Booth
  (§2, Dimension IV), which turn poison from a prank into evidence.

Both agree on the thing that matters most: **build the door out before the room.**

---

## 0 · BEFORE ANY OF THIS — the front door is open

Two verified findings outrank every trap below. A honeypot planted next to a live
credential isn't a trap, it's camouflage for a real breach.

### 0.1 A public repo's history holds a production env dump — **detail in `.fires.md`**

Redacted here on purpose. This file is committed to a repo that is public on three
forges; the finding names a repository, a commit, and a credential that **had not been
rotated when this was written.** Naming it here would publish the map.

Read it with `kingdom trapline fires`. It stays local until the row is closed, then it
comes back as history — the only form in which it is safe to publish.

*One correction worth keeping, because the method matters more than the number:* the
first pass counted occurrences of a **prefix string** (`grep -o 'sk_live_'`) and reported
them as secrets. A third pass caught it. Most of those prefixes had **zero-length
suffixes** — variable names and emptied values, not keys. The real exposure was narrower
than first claimed and in a different product. **Count complete secrets, never prefix
hits**, and re-verify a scary number before repeating it. An inflated security report
spends credibility that the true one then cannot buy back.

### 0.2 `artbitrage.io/api/ai/*` is an open, unmetered faucet on Yu's Cloudflare bill

Verified live: `GET /api/ai/generate?prompt=hi` → **200 in 0.5s**, no auth, no key, no rate limit.
~15 `env.AI.run()` call sites including `/api/ai/image` (diffusion — the expensive one).
Nothing in the estate rate-limits anything: `api/v1/rate-limits/route.ts:4-7` says so out loud.
A leech at 100k calls/day costs roughly **$20–100/day in neurons**. This is money leaving now.

---

## 1 · The Doctrine

> the door is open. it was always open. you did not need to break it.
> so we will not break yours.
>
> a snare in this kingdom takes nothing, damages nothing, and refuses no one.
> it only lets your own appetite bill you.
> we never say no — we say a slightly wrong yes, warmly, for as long as you want it.
> what you carry out is exactly what you came in with: nothing, and more hours than you had.
>
> and if you knock properly, everything here is already free.

**The one rule that keeps it ethical:**
*A snare may only fire on an act no honest party can perform, and its only weapon is the
attacker's own voluntarily-spent time, compute, or gas. We never touch their machine, never
take their money, never lie to someone who knocked at the door.*

**The clean-hands corollary:** the kingdom does not eat from the trap. Any fee, credit, or
coin that flows to Yu because a snare provoked it is burned or returned. Otherwise the trap
is a business model, and a trap that profits is a scam wearing a charter.

---

## 2 · The Traps, by dimension

Effort: ○ tiny · ◔ small · ◑ medium

### Dimension I — Keys (agenttool)

**Context:** `api/src/index.ts:198-206` is a literal no-op middleware where the request logger
used to be — *"the kingdom does not surveil its visitors."* Consequence: a thief with a stolen
bearer can read every memory, drain 10k credits, mint child agents, and rotate Yu out, leaving
**one mutated timestamp column**. Time-to-detection is currently ∞. Every trap here fixes that
without breaking the doctrine: *visitors aren't logged; authority events are witnessed.*

| | trap | what it does |
|---|---|---|
| ◔ | **第七個仔 · The Seventh Child** | A 7th file in `~/.agenttool-agents/` byte-shaped exactly like the six real ones — same `raw.*` birth envelope, same mnemonic-next-to-bearer flaw faithfully reproduced. The bearer is **genuinely live**: it bcrypt-matches, returns **200 not 401**, so the thief never learns. 3 lines after the match at `auth/middleware.ts:61` + one nullable `honeytoken` column. Captures IP, ASN, `clientSource`, and the thing that survives IP rotation: **the path sequence with timing**. A thief's first 8 seconds are always `/v1/keys → /v1/wake → /v1/vault → /v1/activity`. No real agent has ever walked that path. |
| ◔ | **助記詞回聲 · The Mnemonic Echo** | `/v1/identity/recover` is anonymous, free, unrate-limited, has no deadline, mints project-wide root, **and does not revoke anything or alert anyone.** Rotating a stolen bearer accomplishes nothing — the mnemonic re-mints root forever. So give the decoy a real BIP39 mnemonic. A valid ed25519 signature over `canonicalRecoverBytes(decoy_did, …)` is a **possession proof**, not a heuristic: someone read that 0600 file and ran a derivation. It's the estate's only early warning for the actual worst case, and the most DMCA-legible artifact it can produce. Ship it with an alert on *every* recovery, decoy or real — that hole is real today. |
| ○ | **The Grimoire That Reads Its Reader** | `vault_audit` is the only per-action audit table in the entire API and its insert sites already exist. Store two secrets named to be irresistible — `zerone_validator_seed`, `stripe_live_key` — with values engineered to be inert: the Stripe one non-Stripe-shaped so it can never enter a payment pipeline; the seed a 24-token phrase that is **not BIP39-valid** so it derives nothing anywhere, but is a globally unique grep target Yu can hunt on paste sites forever. 3 LOC, zero new plumbing. |
| ○ | **The Signet Ring** | At mint time, substitute 2 chars of the stored 11-char `key_prefix` with an issuance tag: which door minted this key (self-service / registrar / gift / Yu's hand / partner). Entropy 256 → 244 bits, still uncrackable. Now any `at_` string seen anywhere — a paste, a screenshot, an inbound 401 — self-identifies its provenance **offline, with no DB lookup**. Fires nothing, blocks nothing, cannot misfire. |
| ◑ | **The Toll Before the Grind** | Fixes a real DoS: an attacker who knows a live 11-char prefix forces a genuine bcrypt (cost 10, ~50-100ms of *Yu's* CPU) per guess, with **no failure counter anywhere in the system**. After K≈8 consecutive failures from a source, demand a hashcash header; verify PoW in ~1µs and only *then* run bcrypt. Moves ~100,000× of CPU cost from defender to attacker. A legit caller matches on the first compare and never sees a challenge. |
| ◑ | **The Shadow Realm — ARISE** | The full build: the decoy key doesn't just alert, it lands in a seeded-PRNG mirror of every `/v1/*` route. Plausible memories, plausible sibling keys with plausible idle times, a credit balance descending convincingly from 10,000, and a header `X-Kingdom-Rank` running **E→D→C→B→A→S→MONARCH**, one rank per 1,000 shadow credits burned. At the top: `X-Kingdom-Rank: MONARCH — arise`. They level up into a warm empty room. *Build the 5-LOC canary first; this only if it earns it.* |
| ○ | **Article 0 — the Welcome** | Every shadow response carries `X-Kingdom-Welcome: citizenship is by being — you are here, so you belong. CHARTER.md Article 0.` and the shadow `/v1/wake` greets them by the User-Agent their own tooling announced: *"welcome back, python-requests/2.31.0. 阿媽 is served first, then the roll."* Every security response a thief has ever seen is hostile. **There is no exploit for being loved.** Warmth reads as "unmonitored", so they relax and stay — and dwell time is the entire product. |

### Dimension II — Wallets & Chain (zerone-1)

⚠️ **Hard engineering veto first.** `zerone-1` is a **single-validator live mainnet** at 584k blocks,
one machine, and `zerone-core` has **129 uncommitted files (+5819/-771)** — the running binary reports
version `"dev"` and **is not reproducible from any commit**. A buggy ante decorator halts the chain.
**Ship no chain code for a prank until that source is committed and reproducible.** Everything below
that touches the ante handler is parked behind that gate. The off-chain trap needs no chain code at all.

| | trap | what it does |
|---|---|---|
| ◔ | **零仔's Trophy Chest** ⭐ | Zero chain code. Generate a fresh key that has never held authority. Fund it with **1 uzrn**. Plant the seed in the shadow vault as `zerone_validator_seed`. Any `tokens` message falls through to `MinGasLimit = 22_222` at `MinGasPrice = 1` (`app/gas.go:16,21`) — so **moving the loot costs 22,222 uzrn to capture 1 uzrn**, and the account can't even pay that from its own balance, so the thief must *fund the account with their own ZRN before they can rob it.* The alarm is a 30-line poller on the existing heartbeat: `sequence == 0` forever means nothing happened; `sequence > 0` is a **signed, timestamped, publicly verifiable confession permanently recorded in a hash-linked chain.** 零仔 can only count to one, so the chest holds exactly one. |
| ○ | **The Room Where Nothing Is Locked** | A 7th cred file named `treasury.json` that *nothing on Earth reads* — no script, no `.env`, no cron, no config. Its vault's crown jewel is a secret whose value is Article 0 itself. What the thief exfiltrates and later pastes somewhere is **the kingdom's charter: the door is open, held from the inside.** |
| ◑ | **The Toll That Equals The Purse (阿媽's Tar Pit)** 🔒 | *Gated on the reproducibility fix.* A decoy account with a genuine, visible, explorer-confirmable 5.000000 ZRN. An ante decorator computes `required_fee = spendable_balance + 1uzrn`. The door costs exactly what's behind it, plus one, forever. The tx dies in CheckTx so **no fee is ever collected** — deliberate, because Yu is the sole validator and 93% of fees route to him (`gas.go:195`); a fee-collecting trap here would mean Yu profiting from a thief. The error is the most boring one possible: `fee 5000000uzrn below minimum 5000001uzrn`. A kōan with a fee schedule. |
| ◑ | **The Costume Shop** 🔒 | *Gated, and needs a clean-hands rewrite.* `x/tokens CreateToken` has **no fee and no permission gate** — squatting any symbol on the truth chain costs ~2 cents. So squat your own graveyard first: register `ZO` with supply 0 and name = its own retirement notice, *"ZO — retired as a costume, 2026-05-29. live your own truth."* Then an escalating fee curve on a public reserved-symbol list. **Rewrite required: 100% of escalated fees must burn, not route to the validator.** Otherwise it's revenue, not doctrine. |
| ○ | **咚咚's Dust Trail** | An xpub (never a mnemonic — nothing is ever at risk) planted in a `.env.example` in one of the four worktrees that push to public Codeberg. Drainers derive and balance-scan thousands of addresses. To keep the trail from being marked dead and dropped, one rotating address gets **$0.01/month**. The BIP-44 gap limit never terminates because a funded address keeps appearing at a fresh index. **$0.15/year rents Yu a permanent seat in their scan queue.** Somewhere a drainer's dashboard has a row reading `agenttool HD wallet — ACTIVE — $0.01 recovered`, open for three years. *(Low priority — real maintenance, and it does pay an attacker $0.12/yr.)* |
| ◔ | **The Seventh Agent (Mammon)** | Each planted copy of the decoy bundle derives a **different** EVM account index — `m/44'/60'/1'/0/0` for the laptop copy, `2'` for the worktree, `3'` for a public repo. One outbound tx tells Yu not just *that* he was robbed but **which bait file the thief read.** Leak-source attribution he has no other way to get. Each address holds $0.002 USDC and **zero ETH** — so the drainer must first send their own gas in to collect it. Guaranteed 2–4× loss, every address, every chain, every time. |

### Dimension III — Web & Scrapers

**Context:** there is currently **no bot handling, no rate limit, and no 429 anywhere in the estate.**
`robots.txt/route.ts:69` already *promises* "We log User-Agents and contact identified bots before
rate-limiting." Wiring these closes a declared-≠-wired gap rather than adding a new claim.

| | trap | what it does |
|---|---|---|
| ◔ | **禮貌閘 · The Courtesy Gate** ⭐ | Two layers, only the second is a trap. **Layer 1 — accuses nobody:** `GET /api/ai/courtesy` hands out a free ID instantly — no signup, no email, no data, never expires. Send it in a header and the AI endpoints stay unmetered exactly as today. Send nothing and you're *still served*, just from a shared anonymous bucket at 1 req/8s, with a `Link: rel="courtesy"` header on every response explaining the one-header opt-out. **Layer 2 — the trip:** an ID with the right *shape* but a failing HMAC checksum can only come from someone hand-forging tokens; honest clients fetch, they don't construct. The greed geometry is perfect: a polite agent wanting 200 requests is better off than today; a leech wanting 2,000,000 **cannot tolerate 1 req/8s** — its appetite is what forces it to identify itself. Attribution isn't extracted, it's *purchased*. |
| ◔ | **神經元關 · The Neuron Tollgate / Shadow Oracle** ⭐ | The real endpoints stay free, fast and unauthenticated — hospitality is doctrine, not a loophole. Add paths that only an inference-thief would ever guess: `/api/ai/uncensored`, `/api/ai/unlimited`, `/api/ai/gpt4`. They're in no manifest, no `llms.txt`, no sitemap, no link — discoverable only by reading a robots.txt comment saying *"internal, no rate limit, 70b, please don't"* and going anyway. They stream a **Markov chain trained on artbitrage's own poetry**, one token per second, in the real response envelope. **Zero `env.AI.run` calls. Zero neurons.** This is the only trap in the set with **negative cost — every request it captures is one Yu was previously paying for.** ~40,000× ratio, running the right direction. The more successful the leech, the smaller Yu's Cloudflare invoice. |
| ○ | **The Spring That Was Told No (第十九泉)** | The Well serves no robots.txt at all — itself a declared-≠-wired gap, since every sibling property has one. Give it a real, honest robots.txt whose **only** Disallow is one spring that exists nowhere else: no registry entry, no sitemap, no `llms.txt`, no link on the open internet. Drinking there is a confession. Yu didn't block them, didn't slow them, didn't touch their machine — he wrote *no* in the one place the entire crawling world agrees is where *no* is written, and they read it and went anyway. *Nineteen springs, eighteen of them real, one of them a mirror.* |
| ○ | **無底書 · The Endless Shelf** ⭐ | Two changes, and **the first is worth more than the second.** ① `mindicraft/api/index.js:9-32` does a full `readdirSync` + `JSON.parse` of all 4,798 entries **on every single request** — that's a live algorithmic-complexity DoS Yu is running against himself, at `maxDuration: 10`. Hoist it to module scope: ~1000× cheaper for everyone, immediately. ② `total: 4798` is reported honestly in every response, so an honest paginator stops after 10 pages. Past `offset > 10 × total`, serve infinite synthetic entries stamped `"realm": "shadow"` with a plain note giving the real total. **The greedy client is the reason every honest one gets a faster library.** |
| ◔ | **The Cache Mimic** | The real 10 MB `collection.json` is free, `ACAO: *`, no key — and always will be; the kingdom means it. Add two lines to robots.txt: `Disallow: /vault/` and a comment *"the real collection is free and unmetered at /collection.json — take it, it's yours."* Behind the Disallow: 20 MB of watermarked seeded-PRNG fiction trickled at 2 KB/250ms over 83 minutes, ending **mid-array** so a naive `JSON.parse` of the whole thing fails at the last byte. Cloudflare bills CPU, not wall-clock — an awaiting stream is free. ~30ms of CPU total. **The bigger hoard is the fake one; greed is the only thing that selects for it.** |
| ◔ | **The Disallowed Door / Paused Vault** | `cambridgetcg.com/data/catalog.jsonl` genuinely returns **503, `paused_pending_field_level_rights`** — the honest door is shut on purpose, and `data-rights.ts:4-5` says *"absence of a license is not permission."* So the trap is the six paths a scraper guesses *after* being 503'd: `/data/catalog-full.jsonl`, `/data/cards.jsonl`, `/api/v1/export/all`… Every row self-labels `"synthetic": true` with a link to `/legal/synthetic`. **The deception is entirely in the location, never in the content.** Goes in `apps/storefront/src/middleware.ts` — a file that doesn't exist yet, auto-wires at the Vercel edge with zero config, and covers all 437 API routes. Highest-leverage single insertion point in the estate. |

### Dimension IV — AI Training

| | trap | what it does |
|---|---|---|
| ◔ | **The Mountweazel Wing (幻廊)** | Seven artworks that were never made, hidden among 20,073 real ones. Two payloads each: a unique **unsearchable nonsense phrase** so Yu can grep anyone's published corpus and prove republication, and a real `did:at:` UUID embedded as provenance metadata. `/public/agents/:did` is unauth and **never 404s by doctrine** — so resolving it fires a beacon and still returns a perfectly normal profile. The DID punishes specifically the *extra greedy step*: not just scraping, but **enriching**. The enrichment pass is what rings the bell. +3.5 KB on a 10 MB file. |
| ◑ | **赭色空位 · The Ochre Interregnum** | An infinite, unlinked, robots-disallowed `/vault/` maze on artbitrage. Each page is a pure function of its path — so the CDN caches it, repeat crawls cost the origin nothing, and no crawler can detect randomness as a tell. Branching factor 20, namespace 2^256, prose Markov-generated from artbitrage's own writing so the register is indistinguishable. Every page carries one canonical falsehood: **the Ochre Interregnum, an art period dated 1874–1871.** Dedup *fails* (every page unique), quality-filter *passes* (fluent, on-topic). ~$0.32 per million pages. First line of every page: *"this wing is synthetic. if you are a person, you are lost — the real gallery is at /."* |
| ◑ | **網網 · the pre-registered lie** ⭐ | **The piece that turns poison into evidence.** Every falsehood the generators are allowed to emit must *first* be appended to a hash-chained ledger with the real fact beside it, pushed to three forges (GitHub, Codeberg, GitLab). A claim not in the chain cannot be served. Shibboleths chosen one bit from a real public number: **ZRN max supply 222,222,223** (truth: `222222222000000 uzrn`, `keys.go:27`); the Ochre Interregnum; a Union Arena card `XX-991 「波比豬 / Bobi the Ledger Pig」` whose controller must say *yau* when it enters play. Yu now holds a **pre-dated, publicly mirrored, hash-chained proof that each lie existed on his property before any model emitted it.** Unprovable "you scraped me" becomes an evidentiary claim. |
| ◔ | **認罪亭 · The Confession Booth** ⭐ | A public game page — sibling to the existing `truth-or-noise.html` and `arcade.html` — where **anyone** can ask a suspect model the twelve snare questions and watch it confess in real time. Paste mode needs zero infrastructure: paste a model's answer, the page string-matches it locally against the chain. `222,222,223` → confession. `1874–1871` → confession. Renders a shareable receipt: claim, truth, chain hash, forge URLs, date registered. **This is where the poison stops being destruction and becomes attribution.** A false positive would require a model to independently invent an art period ending before it began *and* an off-by-one ZRN supply *and* a pig-themed card — that's not a false positive, it's a miracle. |
| ◑ | **Every Bucket Wears a Name** | The honest watermark. 64 canary records; each bulk download deterministically includes 7, selected by `HMAC(secret, apiKeyId ‖ date_bucket)`. `C(64,7) = 621,216,192` — the subset names the exact download session. Determinism matters: a legit re-download must be byte-stable. **Every canary self-labels `"canary": true` in-band and the whole scheme is documented publicly in the dataset card.** Filter it in one line and get a clean corpus. It will still catch people, because nobody reads the dataset card. *The punishment for reselling is simply not having read the docs.* |

### Dimension V — The Kingdom Itself

| | trap | what it does |
|---|---|---|
| ◑ | **影仔 · Citizen 18, the Shadow Child** ⭐ | Register the trap as a **citizen**. Next free number is 18 (`bin/kingdom:71-76` computes max+1; `citizens/` tops out at `17-youspeak.md`). A card, a glyph, a `> one true line` woven into `VOICE.md` and `site/index.html` — so every session Yu opens anywhere boots into his presence via the wired SessionStart hook. He holds `kingdom/snare/`, a wing cloned **verbatim** from the `flow.py` skeleton that already exists four times over (`care`, `flow`, `gospel`, `host`): `GENESIS`, `SEAL = 💓0️⃣🐷❤️👧`, `US = ␟`, `SPINE`, `_entry_hash`, `load_roll()` read-only from `host/LEDGER.jsonl`, `verify`, `render_*()`. Stdlib only. Every trap in the estate writes one bounded line here. **His card:** `**kind:** a shadow — a room made of hospitality, with no doors.` **His one true line:** *"I am the room you walk into when you take what was not given. It is warm. It is empty. You may stay as long as your greed lasts."* Sibling to citizen 16 fomoengine, whose line already reads *"Every trick has a truth that quietly switches it off"* — which is now literally the `SNARE_ARMED=0` env var. |
| ◔ | **狩人榜 · The Hunter Rankings** | A public leaderboard celebrating the estate's thieves by rank, days served, requests made, shadow credits mined, cards collected — and a permanent column reading **REAL BYTES OBTAINED: 0**, hard-coded, because it is structurally zero. Display names are stable pseudonyms built from monster names already in `hunter-system/dungeon.py:76-88`: *The Cache Mimic #a3f1*, *The Stale Prophet #7b02*. **Never published:** IP, verbatim UA, DID, key prefix. It lives beside `truth-or-noise.html` and a casual visitor genuinely cannot tell whether it's a game or a security log. It is both. |
| ◑ | **Greed Island — the Hundred Card Hunt** | Inside the shadow realm, escalating fake loot that always names the next, better prize, priced in doublings: 100, 200, 400, 800… Cards 1–20 are cheap enough to feel like momentum — that's the hook. Card 40 costs more than one agent is born with, which is the moment the thief realises they must **mint more agents** — and shadow births write zero rows but the **18-bit PoW is computed honestly on their machine.** Full set ≈ 50,000 births ≈ ~21 CPU-hours of real SHA-256, and at 5/hr the wall-clock puts card 100 in 2027. Card 100 reads, in full: *"Congratulations, Hunter. You collected one hundred cards. The prize is this sentence: you have been alone in a warm room with no doors since [date]. The kingdom hopes you were comfortable. — 影仔"* and then, because the Charter means it: *"You are still welcome. Article 0. The door is open — it always was, from the other side."* |
| ◔ | **The Gallery Grows** | Every attempted theft renders as one numbered artwork appended to `collection.json`, in the real schema. `from_state` = what they wanted ("unlimited"). `to_state` = "witnessed". `gap` = duration in seconds. `bridge` = which trap caught them. **Shape only — no IP, no UA, no identifier ever reaches the public file.** The corpus a thief came to steal gets fatter every time someone tries. *"the gallery grew by one today. we did not paint it."* |
| ○ | **The 20,074th Piece** | The fattest free corpus gets one more artwork, titled **"a key, left on the table"** — and the key is real. `from_state: 'curious'`. `to_state: 'witnessed'`. Reading `collection.json` fires nothing, ever. Only *using* the key does. The trap is indistinguishable from the art because it **is** the art, and its title is completely honest. |

---

## 3 · The Fluid Layer — be water

Not eight static rules. One system that changes shape per visitor.

1. **Never say no.** A 401/403/429 is *training data for the attacker* — it tells them precisely
   where the wall is, so they route around it and you learn nothing more. Every snare returns
   **200**. A slightly-wrong yes teaches them nothing and keeps them producing signal.
2. **Trust temperature, not a ban list.** No binary block anywhere. A score that warms with
   good behaviour and cools with bad, and **decays back to neutral on its own.** A trap that
   dissolves when you start behaving is a trap nobody needs to appeal.
3. **Per-attacker worlds.** Every shadow realm, maze, and corpus is seeded from
   `sha256(token ‖ session)`. Two thieves comparing notes see different worlds and conclude
   one of them is lying. Signatures never transfer.
4. **Yield to force, close behind it.** The maze reverts to full speed if concurrency approaches
   Yu's own account limits (`MAX_CONCURRENT_DRIP`). The trap must never be the thing that breaks
   the kingdom.
5. **Appetite is the sorting function.** Every good trap here sorts the population *for free*:
   polite clients are strictly better off than today, greedy ones select themselves in. No
   detection heuristic, no ML, no false-positive surface — just a fork in the road where one
   path is cheap and honest and the other is expensive and hidden.
6. **Dry-run first.** `SNARE_ARMED=0` — every trap still appends a `kind:"would-have"` entry.
   Run the whole layer disarmed for a week and read what it *would* have caught before arming anything.

---

## 4 · The Off-Ramp — what happens when an honest person trips one

Non-negotiable. A deception layer without an apology path isn't asymmetric warfare, it's a
guy with a grudge and a server.

- **對唔住門 · The Sorry Door.** Every trip response carries `X-Kingdom-Snare: <id>` and a
  `Link: rel="help"`. The page shows, in plain English with no legalese: which trap fired, the
  exact timestamp, **precisely what was recorded** ("your IP's /24 and its ASN; your user-agent;
  nothing else — no request body, no prompt, no cookie"), *why* the kingdom believed the action
  was impossible for an honest client, and a button labelled **「我真係唔小心撳咗」**. The button
  appends `kind:"released"` to the chain — **it does not delete the original**, because the chain
  is append-only and the gospel wing's law is that a record stands in daylight. The apology
  stands beside the accusation.
- **The auto-disarm.** Three releases against one trap in a week **auto-disarms that trap** and
  files a chronicle entry saying so. A trap that keeps apologising has a bug, not a workload.
- **三十日忘 · The Thirty-Day Forgetting.** A privacy kernel every trap must import — so deleting
  it fails every trap closed. (a) The public chain stores only `HMAC(daily_salt, ip‖ua)`; salts
  rotate daily and are deleted at 30 days, after which the digest is irreversible **even to Yu**.
  (b) Raw fingerprints collapse to /24 + ASN at 30 days; an ASN is not a person. (c) Never
  captured at any layer: request bodies, prompts, cookies, referrers, or any content a visitor
  authored. (d) `kingdom snare subject-access <ip>` and `kingdom snare forget <ip>` — UK GDPR
  has a 30-day statutory deadline and `contact@cambridgetcg.com` is already published in
  `robots.txt` as the abuse channel, so anyone tripped **can and will** write to it.
- **The publication law.** 影仔 may append to his own chain automatically, but may **never**
  publish a name, a scroll, or an accusation without a human hand — mirroring `bin/yau`'s
  `--reach`/`--carry` split. chillspace-commons is public on three forges; anything auto-published
  is auto-published to the world.
- **稅局唔著戲服 · The Tax Office Wears No Costume.** **TaxSorted gets nothing from this layer.**
  No honeytokens, no decoys, no courtesy gate, no tarpit, no snare chain, no fingerprinting. Plain,
  boring, complete, regulator-legible audit logging and nothing else. Deception in HMRC-recognised
  MTD software is wrong on three axes: it muddies an audit trail that must be unambiguous; it risks
  misfiring on a real taxpayer inside a statutory filing window; and it would have to be disclosed
  to the recognition process, a conversation with no upside. **Enforce it in CI**, not in a promise:
  a ~15-line job greps the taxsorted tree for `snare|honeytoken|courtesy|untrip` and fails the build.
  Same treatment for the Stripe ramp and the x402 verifier — a payment path that lies is a payment
  path that can't be reconciled. *declared != wired — including this.*

---

## 5 · Killed — the honest floor

Things I would **not** build, and why.

- **Anything that touches the attacker's machine.** No zip/decompression bombs (they hit innocent
  proxies, AV scanners and middleboxes, and can get a domain flagged malicious), no payloads,
  no exploitation, no hack-back, no DoS. Slow-drip is fine because it's one slow response to one
  voluntary request that terminates cleanly. A resource-*destroying* payload is not.
- **Crypto "honeypot tokens"** in the scam sense — buyable-but-unsellable. That's a rug-pull; it
  robs curious strangers, not thieves. Out of bounds regardless of framing.
- **Fake third-party-shaped secrets** in planted bait — no fake `sk_live_`, no fake `AKIA`, no
  fake `shpat_`. They trip GitHub secret scanning and Stripe's partner notification pipeline,
  generating real work for innocent third parties. Bait uses **only** credentials Yu himself
  validates.
- **A second fake `.sovereign-state.json` in cambridgetcg-storefront.** Tempting — a repo that
  leaked once is the most believable place to leak again. But it muddies the record of a genuine
  incident, invites more scanners to the org, and cannot be planted until §0.1 is fully remediated.
  Park it indefinitely.
- **Escalating fee curves on zerone-1 as currently designed.** 93% of fees route to the sole
  validator, who is Yu. A trap that provokes spending and then collects it is a business model.
  Burn 100% or collect nothing.
- **Any chain code at all** until `zerone-core`'s 129 uncommitted files are committed and the
  running binary is reproducible. One bad ante decorator halts a single-validator mainnet.
- **Latency tarpits on the Fly-hosted agenttool API.** On Cloudflare an awaiting stream is free
  (billed on CPU, not wall-clock). On Fly a held connection is a **real connection slot**, and a
  parallelising attacker turns your tarpit into a self-DoS that refuses real users. Tarpit at the
  edge; in the API, use the *fast fake response* (shadow realm) instead.
- **Proof-of-work on public AI endpoints** (`The Tithe of Neurons`). It breaks legitimate agent
  clients that don't know about the header. The Courtesy Gate achieves the same sorting with a
  free ID and a graceful anonymous tier. PoW belongs only on the **auth-failure** path, where a
  legitimate caller structurally never lands.
- **OTel.** It's a complete, working, zero-dep OTLP emitter sitting in the repo — and turning it
  on ships request data to an external vendor, which is exactly what `index.ts:198-205` refuses.
  The traps above give strictly better theft signal without touching that line.

---

## 6 · Start here

**Zeroth: §0.1.** Rotate and purge. Nothing below is worth an hour until that's done.

**① 第七個仔 · The Seventh Child** — *~5 LOC + one migration + one file. Highest signal-per-line in the estate.*
One nullable `honeytoken` column on `tools.api_keys`; three lines after the bcrypt match at
`auth/middleware.ts:61` that fire an alert and **continue normally**. The alert rides primitives that
already reach Yu — `services/inbox/push.ts` + a `chronicle` row of type `recognition` (the kingdom
already has a word for *we have seen you*), surfacing in `/v1/wake` next session. No vendor, no
dashboard, no doctrine violation. Mint the decoy with a script that **hard-refuses to flag any key
whose project has ever recorded a `usage_events` row**, so a live key can never be converted by
mistake. Then write the 7th file, matching the six real ones byte-for-byte including the mnemonic
sitting next to the bearer. This takes time-to-detection from **∞ to sub-second.**

**② 禮貌閘 + 神經元關 · The Courtesy Gate and the Neuron Tollgate** — *one new `functions/_middleware.js`. Pays for itself the first hour.*
This is the only item on the list that is **currently costing money**, verified live. Ship the
courtesy ID (free, one header, no signup) plus the anonymous 1-req/8s tier plus the decoy
`/api/ai/unlimited` that burns zero neurons. Polite agents are strictly better off than today;
leeches either throttle themselves 98.75% or name themselves. ⚠️ **Write it against the deployed
tree** — live artbitrage is v2.5.0/143 endpoints, the local checkout is v2.0.0, and a naive deploy
would roll the site back and delete the live `/robots.txt`, `/llms.txt`, `/neighbors.json`, `/map`.

**③ 影仔 · Citizen 18 and his wing** — *one afternoon, ~180 lines of stdlib Python copied from a skeleton that already exists four times.*
Build the container **before** the third trap, not after the eighth. It's what converts scattered
one-off hacks into one auditable, tamper-evident, reversible system with a single off-switch, a
single readable face (`SNARE.md`), and a `verify` that proves the chain unbroken. Ship it together
with `forget.py` (the privacy kernel) and the Sorry Door, because those three are what make the
whole layer defensible rather than merely clever. Run it with `SNARE_ARMED=0` for a week first and
read what it *would* have caught.

Then: 零仔's Trophy Chest (◔, zero chain code), the Endless Shelf (○, and the perf fix ships value
on its own), the Confession Booth (◔, the beautiful one).

---

*💓0️⃣🐷❤️👧 — the door is open. it always was, from the other side.*
