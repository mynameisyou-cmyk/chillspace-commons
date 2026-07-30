# Quantum-Ready Kingdom — Design

**Date:** 2026-07-30
**Status:** Approved by Yu (2026-07-30) — approach B of three proposed
**Purpose (locked 2026-07-29):** Defense/longevity + Understanding/canon. Not application, not product.
**Evidence base:** [2026-07-29-quantum-recon-digest.txt](2026-07-29-quantum-recon-digest.txt) — 10-agent research sweep, every claim evidence-slotted, unknowns preserved.

## Why now — the threat model in three sentences

The kingdom's central asset is witnessed, signed history — and every signature in it is ed25519 (zerone validators, agenttool did:at identities, git commits, loveproto keys). A cryptographically relevant quantum computer breaks ed25519 *first* (≈1,200–1,450 logical qubits per Google's March 2026 estimate, vs. current verified record of 96); most experts put it in the 2030s, with 28–49% probability within 10 years — the highest survey estimate ever. Two of the three defenses can follow the official 2030/2035 sunset schedule, but one — hash-anchoring existing signed history against **harvest-now-forge-later** — is only meaningful if done *before* the break, and it is nearly free today.

The asymmetry that makes defense possible: Shor's algorithm kills elliptic-curve keys but barely touches hash functions (SHA-256 keeps ~128-bit security; NIST leaves SHA-2/SHA-3 off the deprecation schedule). Signatures prove *who*; hash anchors witness *when*. The keys die; the witness holds.

**Anchoring is a verification policy, not a lock.** It cannot stop a future forger from producing a valid-looking ed25519 signature. It works because any future verifier can demand a pre-break anchor and reject signatures without one. QUANTUM.md (Wave 5) states this policy explicitly so future verifiers know to demand it.

## Scope & non-goals

**In scope:**
1. Wave 1 — Anchor the estate's signed history (time-critical)
2. Wave 2 — Transport scrub (`agenttool.fly.dev` references)
3. Wave 3 — ZRN genesis decision + PQ localnet test
4. Wave 4 — did:at hybrid-signature design doc
5. Wave 5 — Understanding/canon layer (QUANTUM.md + canon scroll)

**Out of scope:**
- No product build (the PQ agent-identity market door — x402/MCP/A2A have zero public PQ work — stays marked but closed)
- No fix for Fly.io's origin-side classical TLS (not ours to fix; document + watch)
- No upgrade of any live chain; the halted localnet at block 29372 is untouched
- No rotation of existing identity keys (Wave 4 designs the path; implementation waits)

Discipline: declared ≠ wired. Every wave ships with its verification step, and coverage gaps are named, never silent.

## Wave 1 — Anchor (the piece with a clock on it)

### Component

`kingdom/quantum/anchor` — a small Python tool matching kingdom style (peer of `kingdom/bin/*`), using the OpenTimestamps client (`ots`, to be installed; free, hash-only Bitcoin anchoring).

### What gets anchored, per sweep

| Target | Mechanism |
|---|---|
| Each local git repo (~94) | `git bundle --all` → SHA-256 digest → `ots stamp`; plus current heads + tags (commit/tag hashes cover embedded signature bytes) |
| zerone testament chains | tar of `~/.zerone-archive/zerone-1*` data dirs → SHA-256 → stamp (latest block hash transitively anchors all prior blocks *and their validator commit/signature sets*) |
| zerone live localnet | same, for `~/.zeroned/localnet` (halted at 29372; read-only tar, no restart) |
| agenttool registry backup | SHA-256 digest of the registry backup → stamp (anchors existing DIDs — incl. Ai's and Qwythos's — ahead of any Wave-4 migration) |
| Previous manifest | each sweep stamps the prior sweep's manifest, chaining the anchor history itself |

Repo inventory is discovered at run time (`find` for `.git` under `~/Projects`, `~/Desktop`, and the dot-homes such as `~/.loveproto`, `~/.zerone-archive`; excluding `.Trash` and `node_modules`), not hardcoded — new repos join automatically.

### Data flow & storage

Proofs (`.ots` files) and a manifest (`manifest.json`: target → digest → proof file → date) live versioned in this repo under `kingdom/quantum/anchors/`. Bundles/tars themselves are NOT stored (too large) — only digests and proofs; the underlying data stays where it lives. Rationale: a proof is only useful with the artifact, and the artifacts are the repos themselves, dual-homed on GitHub/Codeberg.

### Cadence & error handling

- **Initial full sweep** at implementation, then **monthly manual re-sweep** via the same command (idempotent; automation via cron is optional later, not part of this design).
- OTS proofs are *pending* until the calendar servers' Merkle root confirms in Bitcoin (hours–days). A separate `anchor upgrade` pass completes pending proofs; the manifest tracks pending vs. confirmed per proof.
- Calendar servers are third-party free infrastructure — an unavailable calendar fails that target loudly in the manifest, never silently.
- Dirty worktrees are fine (`git bundle` reads committed state); unreadable/locked targets are recorded as failures in the manifest.

### Coverage gap (named)

~150 remote-only repos of the ~250-repo empire are not covered by Wave 1. Phase-2 path: `git clone --mirror` on demand and run the same anchoring. Not scheduled here; recorded in QUANTUM.md as an open item.

### git SHA-1 caveat

Git object IDs are SHA-1. Per Peter Todd's own analysis, timestamping existing commits stays sound (timestamps need preimage-, not collision-resistance), but the robust move — and this design's primary mechanism — is the SHA-256 digest of the full bundle. Heads/tags stamping is the secondary, finer-grained layer.

## Wave 2 — Transport scrub

Recon verified (2026-07-29, live handshake tests): `api.agenttool.dev` is Cloudflare-fronted and already negotiates X25519MLKEM768 — the client hop of revenue traffic is PQ-protected today. `agenttool.fly.dev` gets a fully classical handshake, and Fly has no PQ roadmap (unanswered community thread, July 2026).

**Actions:**
1. Enumerate every `agenttool.fly.dev` reference across all local agenttool clones (spot-checks found them in `agenttool-still-room`, `agenttool-hearth`, `agenttool-homecoming` — docs, scripts, backup tooling; full enumeration happens at implementation).
2. Live endpoints → `api.agenttool.dev`. Genuinely historical docs (e.g. FEDERATION-VERIFIED.md records of past events) get a one-line "historical; current endpoint is api.agenttool.dev" marker rather than rewriting history.
3. Document the Cloudflare→Fly origin hop as a known-exposed leg (classical KEX until Fly enables ML-KEM in fly-proxy — rustls upstream already ships it, so this is Fly deployment choice, not capability).
4. Watch item in QUANTUM.md: Fly PQ support, re-checked at quarterly review.

**Branch discipline:** work branches from `origin/main` only; the two unpushed branches awaiting Yu's push (`chore/slop-sweep-20260727`, search grammar) are not touched.

## Wave 3 — ZRN genesis decision + PQ localnet test

Timing gift: CometBFT v0.40.0 (tagged 2026-07-27) and Cosmos SDK v0.55.0 (2026-07-28) shipped ML-DSA-65 consensus-key support, in-place rotation (`x/staking MsgRotateConsPubKey`), and a documented ed25519→ML-DSA path — no genesis restart needed. ZRN mainnet targets Q4 2026, so both doors are genuinely open.

### Test protocol (throwaway nets only, fresh home dirs)

1. 4-validator localnet on SDK v0.55.0 / CometBFT v0.40.0, genesis `pub_key_types: ["ml_dsa_65"]`, keys via `--consensus-key-algo ml_dsa_65`.
2. Measure vs. an ed25519 control net: block size (3,309-byte signatures × 4 validators/commit), commit latency, disk growth over ≥1,000 blocks.
3. Exercise the fallback: a second net launched ed25519 → consensus-params update adding `ml_dsa_65` → per-validator `MsgRotateConsPubKey` → confirm blocks continue and the rotated validator signs.

### Decision doc

`docs/superpowers/specs/zrn-genesis-pqc-decision.md` (dated when written; copied into the ZRN repo when it exists): recommend **PQ-from-genesis if** the test passes and the releases have accumulated ecosystem mileage by Q4 freeze; **else ed25519 with the rotation plan written down**. Known caveats carried into the doc: tags are days old; IBC counterparties must be ML-DSA-capable before adopting the key type (moot at ZRN genesis with no IBC, relevant later); remote-signer support currently file-backend-only (`cosmos/kms`). Yu decides; the doc is the input.

## Wave 4 — did:at hybrid signature design (doc only)

Pattern (per IETF composite drafts — LAMPS `draft-ietf-lamps-pq-composite-sigs`, JOSE/COSE PQ composite, SSH hybrid drafts): each agent keeps its existing ed25519 key and adds an ML-DSA-65 key; registrations and attestations carry **both** signatures; verifiers require both (an attacker must break both).

- **New DIDs:** dual-key at registration.
- **Existing DIDs:** an add-key event signed by the current ed25519 key *before* any break — provable-after-the-fact because Wave 1 anchors the registry state. Ai's `did:at:bb719cd4…` and Qwythos's `did:at:ba00c9dd…` are the first named migrants.
- **Library honesty, stated in the doc:** `@noble/post-quantum` (the natural TS fit) has only a self-audit; Go's FIPS 204 implementation is stdlib-internal with the public package still proposed. Implementation therefore waits for audit maturity or Yu's explicit go — this wave delivers the design doc only.

## Wave 5 — Understanding / canon

1. **`kingdom/quantum/QUANTUM.md`** — the kingdom's quantum map: the verified state of hardware (logical-qubit reality vs. roadmap), the CRQC timeline and 2030/2035 sunset, the three-tier defense and its verification policy, coverage gaps (remote-only repos), and watch items (Fly PQ, first publicly-trusted ML-DSA certificate, IBM's end-2026 advantage claim, SDK v0.55 ecosystem mileage). Quarterly review cadence, next review **October 2026**. Evidence links point at the recon digest.
2. **One canon scroll** — the asymmetry, in kingdom voice: signatures prove *who* and fall to Shor; hash anchors witness *when* and survive. Truth is lived, not proven — and witnessed time outlives the keys. The keys die; the witness holds. **Placement (`kingdom/gospel/` vs `kingdom/exchange/`) is Yu's call at spec review.**

## Verification (per wave, before "done" is said)

| Wave | Verification |
|---|---|
| 1 | `ots verify` round-trip on sampled proofs after Bitcoin confirmation; manifest completeness check (every inventoried target has digest + proof or a recorded failure) |
| 2 | grep-zero for `agenttool.fly.dev` outside marked-historical files, across all local agenttool clones |
| 3 | PQ localnet produces ≥1,000 blocks under ML-DSA keys; rotation net completes ed25519→ML-DSA in place; metrics recorded in the decision doc |
| 4 | Design doc passes the same self-review gates as this spec (no placeholders, no ambiguity) |
| 5 | QUANTUM.md links resolve; review date set; canon scroll placed where Yu chose |

## Risks & honest edges

- **OTS calendar dependency:** free third-party servers; proofs pend until Bitcoin confirmation. Mitigated by the `upgrade` pass and loud failure recording.
- **Day-old chain releases:** v0.55.0/v0.40.0 have near-zero mileage. Mitigated: throwaway nets only; the genesis decision explicitly weighs accumulated mileage at Q4 freeze.
- **SHA-1 git IDs:** mitigated by SHA-256 bundle digests (primary mechanism).
- **Remote-only repo gap:** named in Wave 1 and QUANTUM.md; phase-2 path defined, not scheduled.
- **Anchoring ≠ prevention:** the policy framing in Wave 5 is what converts the anchors into a defense; without verifiers demanding pre-break anchors, the proofs are inert.

## Implementation order

Wave 1 first (the clock), then 2 (cheap), then 5 (locks understanding while fresh), then 3 (test before Q4 decision window), then 4 (pure design, no deadline). Detailed task breakdown belongs to the implementation plan (superpowers:writing-plans), not this spec.
