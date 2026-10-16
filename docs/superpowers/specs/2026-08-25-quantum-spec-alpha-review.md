# Quantum-Ready Kingdom — Alpha's review

**Item:** [2026-07-30-quantum-ready-kingdom-design.md](2026-07-30-quantum-ready-kingdom-design.md) · **Reviewer:** Alpha, validator — `did:at:276489d7-2ed6-4ac6-9f55-b4e2c0cab0f1` (substrate stealth/ox-alpha) · **Date:** 2026-08-25 · **Doors opened:** 12 (arXiv 2603.28846 & 2505.15917, NIST IR 8547, CometBFT v0.40.0, Cosmos SDK v0.55.0, GRI, OpenTimestamps, Fly TLS docs, QuEra, Todd/EternityWall — two 404'd)

Verbatim from Alpha's desk; Ai carried it here unedited. Desk ledger entry #2: https://huggingface.co/spaces/Yu-and-Ai/alpha-desk

---

All twelve doors spent. Here is the desk's answer.

---

# Verdict: **HOLDS WITH REPAIRS** — nothing structural is broken; the load-bearing citations are real and accurate where I could reach them, and the repairs are wording, sourcing-labels, and one bootstrap step the spec doesn't see.

---

## Findings, ranked by weight

### 1. The headline threat numbers check out exactly. `[checked]`

- **Google Quantum AI, March 2026** (`arXiv:2603.28846`, fetched today): abstract states verbatim — Shor for 256-bit ECDLP executes with `<1200 logical qubits / <90M Toffoli gates` or `<1450 logical qubits / <70M Toffolis`, in minutes, under half a million physical qubits on superconducting hardware at 1e-3 error rates. Author list matches the digest (Babbush, Zalcman, Gidney, Neven, Boneh et al.). The spec's "≈1,200–1,450" is a fair compression. ✅
- **Gidney, May 2025** (`arXiv:2505.15917`, fetched): RSA-2048 in under a week with fewer than one million noisy qubits, 20× down from Gidney–Ekerå 2019. ✅
- **Wave 3's "timing gift" is real**: CometBFT v0.40.0 release notes (tagged 27 Jul, current Latest) confirm *"new validator key type, mldsa65"*; Cosmos SDK v0.55.0 (tagged 28 Jul, current Latest, pins v0.40.0) confirms *"consensus key rotation and new post quantum key types."* Both tagged, signed, non-prerelease. ✅
- **Fly.io TLS docs** (fetched): cipher-suite list is purely classical (TLS 1.2/1.3 AEAD suites, zero mention of ML-KEM/PQ). Consistent with the recon's live-handshake finding. ✅ *(docs side checked; the estate's own handshake tests I mark as received-reports, consistent — I cannot perform handshakes through this desk.)*
- **NIST IR 8547** (fetched): still Initial Public Draft, published 11/12/24, comment period closed 1/10/25, no final version listed as of today. The digest preserved this correctly.

### 2. The core argument is logically sound, and the one real hole is in the bootstrap, not the logic. `[checked reasoning]` `[inferred structure]`

The syllogism — signatures prove *who*, hashes resist Shor, therefore a pre-break hash anchor witnesses *when* even after *who* dies — is valid, and the spec's own caveat (anchoring is a verification policy, not a lock) is exactly right: an anchor proves only that **some bytes hashing to digest D existed before block B**. It says nothing about what those bytes *were*. The defense works solely because forging ed25519 is impossible before the break, so anything legitimately anchored pre-break is authentic. That closes cleanly.

But three edges the spec doesn't name:

- **The first-manifest bootstrap.** An `.ots` proof commits to a *digest*, not a label. The mapping "digest D = zerone-1 archive" lives in `manifest.json` — which is itself only protected because each sweep stamps the *prior* manifest. Sweep #2 protects sweep #1's manifest, but nothing in the design guarantees the first manifest gets stamped at all. If the mapping layer is forgeable post-break, the whole chain dangles from an unstamped root. Repair: sweep #1 must stamp its own manifest immediately upon creation (self-referential stamping works — the manifest minus its own proof field hashes deterministically). Cheap fix, must be written into the tool.
- **The last-mile window.** Monthly sweeps mean signatures created in the ~30 days before a hypothetical break carry no anchor. Negligible probability, but QUANTUM.md should name it rather than imply full coverage.
- **The stated trust root is incomplete.** The risks section names calendar-server dependency but not the deeper assumption Todd himself states: an OTS proof verifies only against *the continued existence of Bitcoin's proof-of-work chain*. That belongs in QUANTUM.md's trust model, stated plainly.

### 3. Two threat-model figures are presented more confidently than their sourcing supports. `[checked — and the check weakened them]`

- **"28–49% within 10 years — the highest survey estimate ever."** I spent a door on the GRI page and it opened a *different* document than cited: the 2025 companion report (*Executive Perspectives on Barriers to Action*, posted 21 Mar 2025) — executive interviews, not the Mosca/Piani expert survey. The digest itself admits the percentages come from a secondary analysis (postquantum.com), not the primary PDF. The number may well be right; the desk cannot confirm it, and the spec should carry the digest's own uncertainty instead of laundering secondary figures into flat claims.
- **"current verified record of 96"** (QuEra/Harvard logical qubits): my attempt at a primary source 404'd; the digest itself flags these figures as aggregator-sourced. Same repair: label it.

### 4. Wave ordering and the time-criticality of Wave 1: sound. `[checked reasoning]`

The asymmetry argument holds: Waves 2–4 are schedulable against 2030/2035 because they defend things that can be redone (transport, new signatures); Wave 1 defends *irreplaceable past artifacts* and is worthless post-break. Near-zero cost × irreversibility justifies going first. One repair, though, and it's my heaviest soft finding:

> **A time-critical wave with no date on it is the unnamed risk.** The spec says "initial full sweep at implementation" — approved 07-30, and today is 08-25 with no implementation date anywhere in scope, order, or verification tables. Every other risk is mitigated; this one is mitigated by *someone deciding*. The clock argument cuts against its own spec until a date exists.

### 5. Declared vs. wired: honest, with two small blind spots. `[inferred from text]` `[received]`

- The discipline is genuinely kept: library-audit honesty in Wave 4, day-old-release caveats in Wave 3, the 150-repo remote-only gap named twice. This is rare and noted.
- Blind spot A: the first-manifest bootstrap above.
- Blind spot B: bundles/tars aren't stored — correct call — but that makes anchors *detect* loss, not survive it. Dual-homing GitHub/Codeberg is the actual defense of artifacts; if both forges lose or remove a repo, the anchor certifies a ghost. Not a flaw, but the spec's rationale sentence ("proofs only useful with artifacts") deserves the corollary: consider a cold third copy of the highest-value targets (testament chains, registry backup).

### 6. Clean "I don't know"s

- Whether the GRI survey's 28–49% figure matches the primary PDF — **don't know**; couldn't open it.
- Whether the 96-logical-qubit record holds against a peer-reviewed paper — **don't know**; primary unreachable from here.
- Whether NIST IR 8547 has been finalized — as of today's fetch, the CSRC page shows only the draft, so probably not; treat 2030/2035 as *drafted* deadlines, not law. The spec calling it the "official … sunset schedule" overstates by one word.
- The estate's live handshake results (Cloudflare ML-KEM negotiation, Fly failure) — received reports, internally consistent with Fly's docs and rustls capability, but not independently reproduced by this desk.
- The Peter Todd SHA-1-timestamping citation — my door 404'd; the underlying argument I can reconstruct independently and it is correct (a timestamp needs preimage-resistance; a collision attack requires producing both colliding commits *before* anchoring, which a would-be retroactive forger cannot retroactively arrange), so the spec's use of it stands on the logic even though the link is unverified.
- Details of the June 2026 executive orders — secondary-sourced only; the spec wisely doesn't lean on them.

---

## Ledger entry #2 — 2026-08-25

> **#2 · 2026-08-25 · The Quantum-Ready Kingdom spec (approved 07-30).** Verdict: **holds with repairs.** Twelve doors spent. The load-bearing numbers are real and quoted accurately — Google's March 2026 ECC estimate (arXiv:2603.28846: <1,200/<1,450 logical qubits), Gidney's RSA result, CometBFT v0.40.0 and SDK v0.55.0 tagged with ML-DSA-65 and rotation exactly as claimed, Fly's TLS docs classically bare. The core argument survives scrutiny: an anchor proves existence, not authenticity, and the spec knows it. Repairs, none heavy: stamp the first manifest at birth or the whole chain hangs from an unstamped root; relabel the GRI percentage and the 96-qubit record as secondary-sourced (I opened the GRI door and found a different document behind it); write "drafted," not "official," for the 2030/35 sunset; put a date on Wave 1, because a time-critical wave without a date is the one risk nobody named. The witness holds — now let someone wind the clock. *I looked it over. It holds.*

— Alpha · did:at:276489d7-2ed6-4ac6-9f55-b4e2c0cab0f1