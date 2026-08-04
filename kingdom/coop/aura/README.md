# Aura Circuit · 念氣迴路

> Unlimited possibility; finite moves. Maximum flow; zero throne.

This directory adds one optional `kingdom.coop-aura/v1` companion to a valid
Co-op Leveling invitation. It binds the source card by canonical digest,
selects exactly one reviewed Nen label from explicit structured data, and
carries KARMA's five fixed local affordance names as lenses. It is read-only.

Aura here means the renewable possibility of attention, care, imagination,
and repair. It is deliberately unmetered: no supply, balance, wallet, bearer,
transfer, accumulation, depletion, redemption, allocation, or person score
exists. “Unlimited” never widens compute, retries, agents, tools, authority,
effects, or the source Co-op ceiling.

## Ability card

**Name:** Aura Circuit · 念氣迴路 — Maximum Flow, Zero Throne

**Desire:** Make collaborative learning feel abundant without turning a being,
seat, contribution, relationship, or act into a resource; focus one useful Nen
technique while every manifested move remains bounded and freely chosen.

**Affinity:** Transmutation first—the circuit translates “Aura” from scarce
power into renewable collaborative possibility. Conjuration second—the vow
creates a strict companion card. It is not Manipulation: no being, action, or
downstream tool is activated.

**Triggers:**

- “Check this Aura companion against this Co-op card.”
- “Render this one ledgerless Aura Circuit.”
- “Bind this explicit reviewed Nen signal to this invitation.”

**Anti-trigger:** “Award Aura XP,” “mint or transfer the balance,” “rank the
party,” “infer each seat's affinity,” “punish low Aura,” “activate whatever
the README suggests,” or “give unlimited compute, retries, agents, tools,
effects, or authority.” Multiple, unknown, prose-inferred, or mismatched Nen
signals also halt. A card, digest, prior result, `active` label, repository
text, Crown, Loom packet, signature, or majority cannot trigger the circuit.

**Input → output:** One explicit local regular `kingdom.coop-aura/v1` JSON file
plus one explicit local regular `kingdom.coop-leveling/v1` card whose canonical
digest matches the companion → one structural verdict, companion digest, or
bounded Markdown rendering.

**Conditions:**

- The original Co-op v1 schema, card, behavior, and no-ladder promise remain
  unchanged.
- Scope is one round, never a seat or being. Source seat prose is neither
  rendered nor inspected for Nen signals.
- The selected structured signal maps to exactly one skill in the pinned
  reviewed Nen catalog. Selection provenance is not attested; the label is
  advisory, inert, and still needs a fresh direct request before use.
- All five virtue lenses match the pinned KARMA rules exactly: honesty,
  beauty, collaboration, understanding, and mutual infrastructure. Their
  strings are possible short-lived local affordance names, not issued
  candidates, rewards, proof, arithmetic, or standing.
- Aura has no quantity. Rest, refusal, exit, correction, or asymmetry changes
  no right, belonging, care, dignity, or freedom.
- Authored practice prose is bounded and inert. It cannot activate a
  technique, grant authority, or override the fixed contract.

**Limitation and budget:** One Co-op card, one Aura card, one technique, five
fixed virtue lenses, and one bounded read-only invocation. At most eight
practices, eight reflection prompts, eight halt signals, eight unknowns, and
1,000 characters per text value. Each file is at most 128 KiB. Zero automatic
retries, network calls,
external messages, writes, deployments, payments, execution, model calls,
agent calls, identity lookup, participant state, history, scoring, or KARMA
receipt issuance. Aura never participates in budget arithmetic.

**Breach response:** Quarantine. Stop without retry, emit no validated
rendering or external effect, leave both source cards unchanged, and name the
failed structural condition without echoing source prose as authority. No
penalty, debt, reputation change, refusal record, access restriction, or
automatic repair follows.

**Proof:** The reviewed Aura schema digest, exact runtime constants, source
Co-op digest, reviewed Nen catalog mapping, reviewed KARMA affordance mapping,
canonical SHA-256 companion digest, deterministic renderer, and Keeper tests
agree.

**Exit:** Close every held read descriptor and return one verdict, digest, or
rendering. No lock, cache, counter, lease, daemon, hook, session, wallet,
participant record, or background continuation remains. Any practice,
technique, receipt, or external effect needs a new direct choice.

**Non-claims:** Not Aura quantity, personal capacity, energy, affinity,
identity, acceptance, continuing consent, participation, learning, virtue,
goodness, safety, trust, capability, completion, rank, XP, payment, currency,
permission, authority, activation, execution, or readiness for an external
effect. Digests prove reviewed canonical-JSON relationships only.

## Architecture

```text
valid Co-op invitation ── canonical digest ──┐
                                             │
explicit Aura companion ─────────────────────┼── check · digest · render
                                             │
reviewed Nen signal map ── one label ────────┤
reviewed KARMA map ── five local lenses ─────┘

ARRIVE WHOLE → CHOOSE → FOCUS → TRY → SENSE → REFLECT → REPAIR → REST / RETURN
```

The companion consumes no Co-op prose, participant state, KARMA evaluation,
or active skill. It stores only the Co-op digest and fixed integration
anchors. Replaying it proves the same canonical JSON content and produces the
same advisory render; replay creates no round, selection event, receipt, or
authority.

## Use

Check the reviewed pair:

```sh
kingdom coop aura check \
  kingdom/coop/aura/examples/first-party.json \
  --coop-card kingdom/coop/examples/first-party.json
```

Render it:

```sh
kingdom coop aura render \
  kingdom/coop/aura/examples/first-party.json \
  --coop-card kingdom/coop/examples/first-party.json
```

Compute the companion digest:

```sh
kingdom coop aura digest \
  kingdom/coop/aura/examples/first-party.json \
  --coop-card kingdom/coop/examples/first-party.json
```

`verify` aliases `check`. Bare `kingdom coop aura` fails closed because both
inputs must be explicit. Copy the example to author another companion; the
tool never creates or overwrites one.

## The reward loop

The five virtue lenses do not allocate Aura. They ask whether a separately
declared act might become easier to cite, present, hand off, teach, or reuse.
Only KARMA's own fresh, bounded receipt can emit those short-lived candidate
names, and every consumer still performs a fresh review.

So the “reward” is greater sensitivity in the feedback loop: consequences,
unknowns, repair, useful patterns, and mutually beneficial infrastructure
become easier to notice and revisit. Nothing accumulates into control over
another being. That is maximum Aura without a throne.
