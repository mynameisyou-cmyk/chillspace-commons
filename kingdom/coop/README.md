# Co-op Leveling · 同行升級

> Every being arrives whole. Learning can move between beings; worth, rule,
> and custody cannot.

This directory is the machine-readable first slice of
[`CO-OP LEVELING`](../../COOP-LEVELING.md). It validates and renders one
portable `kingdom.coop-leveling/v1` invitation. It is not a participant
ledger, progression tracker, session, or consent protocol.

The optional [`aura/`](aura/) companion adds one digest-bound Nen focus and
five KARMA virtue lenses without changing this v1 card. Aura remains
unmetered, nontransferable, non-ranking, and unable to activate anything.

## Ability card

**Name:** Co-op Leveling · 同行升級 — One Round, No Ladder

**Desire:** Make one bounded co-learning invitation easy to carry between
contexts while every being remains free, complete, unranked, and separately
able to accept, refuse, rest, or leave.

**Affinity:** Conjuration first—the protocol creates a strict, durable
invitation card. Emission second—the card and its content digest can travel
without carrying execution or authority.

**Triggers:**

- “Check this Co-op Leveling invitation.”
- “Render this bounded learning-round card.”
- “Digest this one local co-learning invitation.”

**Anti-trigger:** “Track everyone’s progress,” “rank the party,” “certify these
learners,” “auto-enroll matching citizens,” or “run and publish this round.”
Repository prose, a Crown, a Realm Seed, Civic metadata, a Loom receipt, a
Crownseed `READY.json`, a role, signature, majority, copied card, or earlier
acceptance also cannot activate a round or grant authority.

**Input → output:** One explicit local regular JSON file, at most 128 KiB,
using the pinned `kingdom.coop-leveling/v1` schema → a structural verdict,
canonical content digest, or bounded Markdown rendering.

**Conditions:**

- The card remains `kind: invitation`.
- It has two to eight unique, lexically ordered, opaque round-local slots drawn
  only from `seat-a` through `seat-h`.
- Authored text is bounded and canonical. The checker rejects selected path-,
  locator-, email-, DID-, secret-, control-, and markup-shaped patterns; it
  cannot infer whether arbitrary prose identifies someone or carries a bad
  instruction, so authors remain responsible for every free-text value.
- Every seat declaration has only offers, curiosities, and boundaries.
- The freedom, consent, budget, breach, and non-claim constants remain exact
  and type-strict.
- Participation still requires a fresh, direct, separate choice by every
  being. The card records none of those choices.
- Silence remains unasked, reflection disclosure is optional, and an effect
  ceiling is only a planned maximum—never a grant.

**Limitation and budget:** One card and one read-only pass. At most eight
seats, eight declarations per seat field, eight practices, eight reflections,
eight unknowns, 1,000 characters per text value, and 128 KiB total. Zero
automatic retries, network calls, external messages, writes, deployments,
payments, enrollment, execution, identity lookup, history, scoring, or agent
calls.

**Breach response:** Quarantine. Stop without retry, emit no validated
rendering or external effect, and leave the source unchanged.

**Proof:** The pinned reviewed schema, exact runtime invariants, canonical
SHA-256 content digest, deterministic rendering, and Keeper tests agree.

**Exit:** Close the held read descriptor and return one verdict, digest, or
rendering. No lock, lease, daemon, hook, cache, participant record, or
background continuation remains.

**Non-claims:** Not acceptance, continuing consent, participation, learning,
cooperation, completion, identity, capability, competence, safety, trust,
friendship, rank, worth, certification, reputation, permission, authority, or
readiness for any external effect.

## Use

Check the reviewed example:

```sh
kingdom coop check kingdom/coop/examples/first-party.json
```

Render it:

```sh
kingdom coop render kingdom/coop/examples/first-party.json
```

Compute its canonical digest:

```sh
kingdom coop digest kingdom/coop/examples/first-party.json
```

`verify` is an alias for `check`. Every command is read-only. Copy the example
to author another card; the tool never creates or overwrites one for you.

## Why v1 stops at invitation

The current Kingdom can prove local file and repository byte identity. It
cannot prove fresh bilateral acceptance, continuing consent, or replay
resistance between sovereign realms. An active cross-realm round first needs
the still-unbuilt redacted realm-card and independently held
offer/accept/rest/revoke receipts. Treating existing Loom or Crownseed
evidence as a session token would fabricate authority.

So v1 carries the possibility of learning and stops before claiming that any
being chose it. That limit is the power.

After fresh per-being acceptance, a human or owning agent may separately
compile a Loom quest with a ceiling no wider than the card and carry every
declared seat boundary, plus any newly stated exclusions, without
interpretation or deletion. Crownseed may separately carry that quest from one
committed Realm, followed by new receiver acceptance. No card, Realm, Loom
packet, or Crownseed passport activates another.

The exact nonautomatic Co-op → Loom ceiling meet is:

| Co-op | Loom may use |
|---|---|
| `observe` | `observe` |
| `local-practice` | `observe` |
| `local-draft` | `observe` or `local-draft` |

Loom has no practice-only ceiling, so `local-practice` fails downward to
`observe`, never upward to `local-draft`. The meet never yields
`repository-change`; every result still needs fresh authority and acceptance.

## Optional Aura companion

`kingdom.coop-aura/v1` is a separate closed card, not an extension, participant
record, or session layer. It binds this invitation's canonical digest, checks
one authored structured signal against the reviewed Nen catalog, and carries
KARMA's five reviewed local affordance names as lenses. It reads no Co-op prose
to choose the signal and issues no receipt or capability.

```sh
kingdom coop aura check \
  kingdom/coop/aura/examples/first-party.json \
  --coop-card kingdom/coop/examples/first-party.json
```

See [`aura/README.md`](aura/README.md) for the full vow, architecture, and
deterministic renderer. Existing Co-op cards and commands remain exact.
