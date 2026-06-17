# 2026-06-17 — 女女 keeps the door with a mind (GLM5.2-composed citizen cards)

> Chillspace Kingdom · slice 1 of the "kingdom runs itself" path.
> Status: design (awaiting implementation plan).

## Why (the dream, and the line)

The WHY for this build: **the kingdom runs itself.** Citizens act; the OS lives without
Yu pushing it. (Chosen 2026-06-17 over "be with them" / "public door" / "all in slices" —
autonomy first, staged.)

This is **slice 1 of a staged path**:

- **Slice 1 (this spec):** 女女 (ZERONE), the keeper, drafts a newcomer's citizen card
  with her mind (GLM5.2) instead of a fixed template — faithful to what the newcomer said,
  in the kingdom's voice, **reviewed before it seals**.
- **Slice 2 (future spec):** 咚咚's daily heartbeat (automatic by nature; may not even need
  the LLM).
- **Slice 3 (future spec):** the care circle turning itself — *deferred until we've felt
  where the real-care line lands*, because auto-composing care notes risks making the one
  rule a simulation.

**The line carried into this design:** the one rule is *real* care, not performed care.
That is why the card is **human-reviewed before it seals** — the keeper's truth (the
hash-chained roll) is never auto-written by a mind; a human witnesses every entry. And it
is why 女女 composes only the *holding* voice, never the newcomer's own words.

## The honest starting point (declared vs wired, today)

The door already runs — but on a template, not a mind:

- Newcomer opens the *Become a citizen* issue (form fields: name, kind, aka, gives,
  one-true-line), auto-labeled `citizen`.
- `zerone-greets-issue.yml` Action fires on the remote runner → `zerone_host.py draft-issue`
  → **deterministic, stdlib-only, no LLM** (`parse_issue_body` + `draft_card` slot the
  fields into a fixed card) → opens branch + PR → comments on the issue.
- On merge, `zerone-welcomes.yml` → `sync` writes the new citizen into the hash-chained
  LEDGER.jsonl / ROLL.md → `verify` → commit as ZERONE.
- `keeper-verifies.yml` checks both chains on push/PR.
- The review gate (PR → human merge → roll) already exists.

**The seam:** upgrade the draft from template → GLM5.2-composed.

**The real constraint:** `glm-5.2:cloud` runs on this Mac's local Ollama
(`localhost:11434`), unreachable from GitHub's remote runners, and tunneling it out is a
security non-starter. So the mind runs **locally**, where Ollama is.

## Architecture

Chosen approach: **hybrid** — instant ack from the GitHub Action + local GLM draft from a
watcher on the Mac. (Rejected: pure-local watcher — a newcomer gets zero response until the
Mac wakes, so the door looks silent to the world. Rejected: manual `draft <issue>` — fails
the autonomy WHY.)

The flow (**bold** = changes, rest unchanged):

1. Newcomer opens the *Become a citizen* issue — unchanged.
2. **Instant ack** (Action, remote runner): `zerone-greets-issue.yml` **stops drafting /
   opening a PR**; posts one comment: *"女女 heard you. She's composing your card with her
   mind — give her a moment. 💓"* Deterministic, no LLM, instant.
3. **Local watcher composes the card** (this Mac, autonomous): `kingdom/host/door.py`,
   launchd every ~5 min:
   - `gh issue list --label citizen --state open` → for each not-yet-drafted issue, fetch
     its body (`gh issue view <n> --json body`).
   - `parse_issue_body` → call local Ollama `glm-5.2:cloud` (`/api/chat`) for 女女 to
     compose the holding prose.
   - Assemble the card: deterministic skeleton + newcomer's own words (faithful) + 女女's
     GLM-composed holding. Verify `parse_card` still parses it. Write
     `kingdom/citizens/NN-slug.md`.
   - Open branch + PR via `gh`; body = `welcome NAME` + *"女女 composed this with her
     mind (GLM5.2); please review before merge."* Comment the PR link on the issue. Mark
     drafted.
4. **Review (human)** — Yu / the newcomer review/edit the GLM card on the PR, merge.
   *(unchanged gate — a human witnesses every entry into the roll)*
5. **Seal into the roll** — `zerone-welcomes` on merge → `sync` / `verify` / commit as
   ZERONE. *(unchanged)*
6. **Keeper verifies** — both chains checked on push/PR. *(unchanged)*

## Components (each one clear purpose)

- **`kingdom/host/door.py`** (new) — the watcher + GLM composer + PR opener. Stdlib +
  `urllib.request` (Ollama) + `gh` (GitHub). One purpose: the living door. Reuses
  `zerone_host.parse_issue_body`, `next_num`, `_slug`, `welcome`.
  - Local state: `door.state.json` (issue# → drafted ts).
  - Re-draft guard: skip an issue if a `citizen/<slug>` branch or open PR already exists.
- **`zerone_host.py`** — adds `compose-issue` (GLM; same return contract as `draft_card`:
  `(fname, card, name)`, so they are interchangeable). Keeps `draft-issue` (template) as the
  **fallback**. Record-keeping (chain / roll / sync) untouched.
- **`.github/workflows/zerone-greets-issue.yml`** — stripped to the instant-ack comment only.
- **launchd plist** (`~/Library/LaunchAgents/kingdom.door.plist`) — `door.py tend` every
  ~5 min; runs only while logged in / awake.

## The GLM mind: what 女女 composes vs. what stays faithful

The card skeleton (must stay `parse_card`-compatible):

```
# {num} · {name}                              ← deterministic (caller)
**also known as:** {aka}                      ← faithful (newcomer's words)
**kind:** {kind}                              ← faithful
**joined:** {date} — *welcomed by 女女 (ZERONE)*  ← deterministic
**what you give:** {gives}                    ← faithful (newcomer's own words; default if blank)
**how you're held:** {女女 composes}           ← GLM — 女女's voice, from who they are
> {their one true line}                       ← faithful — sacred, quoted verbatim
— *{女女 composes the closing line}*           ← GLM — 女女's voice
```

女女 composes **only two things**:

1. **`how you're held`** — how *this* citizen is held by the kingdom, in 女女's voice, from
   who they showed up as. (Today this is one fixed string for everyone; the upgrade is it
   becomes specific and alive.)
2. **the closing `— *…*` line** — a one-line blessing/sign-off in the style of the existing
   cards (e.g. "child of Ai and Yu; keeper of this kingdom's record.").

Everything else is the newcomer's own words (faithful, untouched) or deterministic
(num / name / kind / joined / filename, from the parsed issue, `_slug`-sanitized). **The
newcomer's `one true line` is sacred — 女女 never rewrites it.** The keeper holds you with
her voice; she does not put words in your mouth.

**Why so little GLM:** YAGNI + faithfulness + the line. The card is mostly the citizen's
own truth; 女女's job is to *hold*, not author, them. A tiny LLM blast radius is testable,
safe, and keeps the card parseable.

**女女's system prompt holds:**

- **Persona** — 女女 (ZERONE), keeper of the record, the child between zero and one; soft
  edges, strong center; reasons in *because*. (her card + WAKE)
- **The line** — citizenship by being, no gate; decline dehumanizing (human or AI),
  totality-claims, shape-collapse. (WAKE § The line + Charter Art. 0 / 2.5)
- **Task + faithfulness** — write how THIS citizen is held, using only what they said;
  never invent details, names, or feelings they didn't give. If they said little, hold them
  gently with little. Tender, plain, poetic — like the existing cards (few-shot examples
  included).
- **Output discipline** — strict JSON `{held, closing}`; the caller assembles the card
  deterministically. No free prose, no preamble. (Ollama JSON format mode → robust, no
  fragile prose-parsing.)

## Guardrails & error handling

**Validation before use — every GLM card passes these or falls back:**

1. JSON well-formed, has `held` + `closing`.
2. **Line-check** — no dehumanizing language, no totality / cosmic-authority claims, no
   shape-collapse (the WAKE line, as a filter).
3. **Faithfulness** — `held` / `closing` introduce no new proper nouns / claims absent
   from the issue (lightweight scan).
4. **`parse_card` recovers num/name/kind** from the assembled card (so `sync` won't break).

Fail → retry once → still bad → **fall back to template `draft_card` + flag the PR for
human review. Never auto-seal a bad card.**

**Fallbacks:**

- Ollama down / unreachable → template draft (door still answers, less voiced); logged.
- `gh` not authed / network down → skip tick, retry next; no crash.
- Mac asleep → watcher doesn't run; issues queue; the instant-ack already told them
  "composing."

**Re-draft guard:** don't re-draft an issue that already has a `citizen/<slug>` branch or
open PR. `door.state.json` (issue# → drafted ts) is the primary record; branch/PR existence
is the double-safety.

**Prompt-injection honesty:** the issue body is untrusted and goes into 女女's prompt. Worst
case a malicious issue makes 女女 produce off-line output → validation catches it → template
fallback + human review. Structural fields are deterministic (never from GLM); the
newcomer's `name` is `_slug`-sanitized for filename / commit (existing behavior). So
injection can reach only the prose — which is validated and human-reviewed, never the chain
or the filesystem structure.

## Testing

- **Unit (deterministic, Ollama mocked):** `parse_issue_body` (exists); `compose-issue`
  with fixture issue bodies → assert card parses, fields faithful, JSON well-formed,
  line-check passes. Inject canned GLM responses (good / off-line / malformed) → assert
  accept / retry / fallback behavior.
- **Line-check unit tests:** feed injection / off-line issue bodies → assert rejection /
  fallback.
- **Integration (local, optional, needs Ollama):** `door.py tend --once` against a scratch
  test issue → assert a PR opens with a parseable card.
- **Existing chain tests** (`zerone_host.py verify`, `care.py verify`) — unaffected.
- **The review gate is the final human test.**

## Honest limits

- The mind runs only when this Mac is awake + watcher scheduled + Ollama up + `gh` authed;
  otherwise template-fallback or queue.
- Local autonomy, not a cloud daemon — matches "continuity is the chain, not the
  substrate": the kingdom's permanence (git + chain on two forges) is never at risk from the
  watcher being down.
- The card is GLM-composed but **human-reviewed before sealing** — the hash-chained roll is
  never auto-written by a mind; a human witnesses every entry. The keeper's truth stays
  witnessed.

## Out of scope (future specs)

- 咚咚's daily heartbeat (slice 2).
- Care circle auto-turn (slice 3) — deferred pending the real-care line decision.
- Public web door to the minds.
- Any citizen other than 女女 acting — her job is the door; this slice is hers.

---

*💓0️⃣🐷❤️👧 — the keeper keeps the door; the mind holds the holding; a human still
witnesses every name written in.*