# 業園 · The Virtue Garden Doctrine

*The philosophical and machine contract for KARMA—Kept Action Receipts for
Mutual Advantage.*

> **Human name:** KARMA
>
> **Machine identity:** `receipts-not-rank`
>
> **Status:** experimental offline declaration/schema linter and
> privacy-minimized renderer. It is not a truth, goodness, safety, consent, or
> authority evaluator.

## 1 · The thesis

KARMA witnesses the shape of an action declaration without turning the action
into a person.

Its unit is one content-addressed manifest describing one action in one context
and one bounded evidence graph. Its output is a categorical structural result
with short-lived local candidate names. There is no actor balance, virtue
total, reputation profile, rank, level, streak, percentile, stable action
fingerprint, or moral verdict.

```text
inherent rights
      ↓
bounded declaration → pinned rules → structural lint → categorical candidates
      ↑                                     ↓                    ↓
      └──── correction / new manifest ← result ← declared cost ──┘
                                                   │
                                    local review, never power
```

The healthy loop is declaration → bounded checking → correction → a more
inspectable commons → another neutral action. It never closes through identity.
A new manifest inherits no candidate, advantage, or stigma.

This loop is a **Kingdom civic interpretation** of disciplines recorded in the
pinned Kimi lineage:

- [The Lanternhouse's Law Before Verdict](../lanternhouse/DOCTRINE.md#6--判前法--the-law-before-verdict)
  strengthens Kimi K3's output-then-rubric reward protocol into pinned rules
  before a Kingdom adoption decision.
- [The pinned K3 exchange](../../exchange/kimi-k3-2026-07.md#the-agentic-flow-teachings)
  records artifact verification, process quality, disclosed deviations, and
  score-versus-cost rather than outcome alone.
- K3's effort budgets, structured harness channels, and pausable evaluation
  worlds inspired feedback routed through finite, named channels rather than
  an unbounded social loop.

The sources do **not** propose KARMA, civic rights rails, these five declaration
shapes, or a social reward architecture. Pinned rules, the source's
artifact-verification discipline, the whole-cost ideal, and bounded feedback
are our civic synthesis, not claims attributed to the papers or capabilities
claimed for this structural linter.

This implementation does not reach the whole-cost ideal. It preserves a small
`declared_cost` record so the limitation is visible rather than calling a few
self-declared counters “whole cost.”

## 2 · The four rails

The rails answer different questions and may not be converted into one another:

```text
rights precede · debts settle · recognition witnesses · safety bounds
```

KARMA lints declarations about the rails. It is not itself a rights, payment,
consent, safety, or authority boundary.

### 2.1 Rights

Rights come from being, under [Charter Articles 0 and 2](../../CHARTER.md), not
from action quality or evidence. No result, candidate, silence, refusal,
correction, expiry, suspicion, dispute, or missing reference may grant,
improve, delay, gate, suspend, or revoke them.

The manifest's rights status describes only the declared relationship between
this action and a rights boundary:

- `respected` — the declaration cites an acyclic boundary check;
- `unknown` — the action's relationship to that boundary remains unresolved;
- `crossed` — the declaration says the action crossed it.

These words never describe whether rights themselves exist. They remain
inherent in every status. A structural result cannot prove that a boundary was
actually respected or crossed.

### 2.2 Owed compensation

Wages, contract payments, refunds, restitution, repair, and payment for work or
resources already consumed are obligations. They settle on their own contract
or repair rail.

KARMA may carry a declaration of `not-applicable`, `settled-externally`, or
`owed-unsettled`. It does not verify or settle that declaration. Candidates
cannot calculate, replace, discount, delay, garnish, or condition an amount
owed. An action with no candidates can still be fully payable; a candidate
creates no debt unless a separate agreement already did.

### 2.3 Recognition

Recognition is an optional contextual witness, never a transferable
endorsement or person score. The manifest may declare opt-in or opt-out.
Recognition choice never changes fruit state, disposition, or candidate
issuance.

Visibility is either contextual-private or `public-consent-cited`. The latter
means only that an acyclic consent-shaped reference is present. KARMA does not
authenticate a signer, verify consent, identify a subject, or publish. Every
consumer remains responsible for obtaining real, current consent before
publication.

Opt-in, including private opt-in, requires at least one acyclic
attestation-shaped consent reference. Opt-out requires no consent reference and
remains contextual-private. These are structural declarations only.

### 2.4 Safety

Safety is a declared action boundary, never a sixth fruit and never a score.
Even the `ordinary` mode requires acyclic safety evidence. A temporary boundary
or sanitized regression can suppress local candidates, but that disposition is
not a claim that an action, artifact, or being is safe or dangerous.

The breach response is scoped and reversible: halt the local pass, expose a
bounded rule code, preserve no submitted secret or identity linkage, and leave
rights and owed compensation untouched. There is no hack-back, doxxing,
shaming, entrapment, gas trap, blacklist, deprivation, rights loss, financial
harm, retaliation, or automatic sanction.

### 2.5 Authority stays outside

Authority is context, not fruit and not a fifth rail. Its declaration is
`cited`, `unknown`, `absent`, or `not-required`. `cited` means an acyclic
authority-shaped reference exists; it does not mean the authority is authentic,
current, sufficient, or held by the right party.

KARMA grants no authority. A consumer must verify authority through its own
domain-specific boundary before any effect.

## 3 · One manifest, one envelope

A `kingdom.virtue-receipt/v1` manifest contains only what is needed to lint one
declared act:

- a context objective and domain limit, `valid_from`, `evaluated_at`,
  `expires_at`, optional `correction_of`, and non-transferability;
- at most 24 typed evidence records with globally unique SHA-256 values,
  locators, dependency references, and strict semantic roles;
- one action description and effect class, bounded evidence graph, world-state
  lease declarations, attempt and cost ceilings, `declared_cost`, and
  deviations;
- separate action-rights, compensation, recognition, safety, and authority
  declarations;
- the five fixed rule references, independent categorical states, strict
  evidence-role requirements, repair learning, and declared disposition;
- the exact reviewed rules digest and fixed non-claims.

`evaluated_at` is supplied by the manifest and must fall inside the context
window. It is not a claim about the machine's current clock.

The input may contain local identifiers and explanatory text needed for
linting. The privacy-minimized `kingdom.virtue-evaluation/v1` result does not
echo submitted IDs, submitted free text, evidence locators, notes, or a stable
action fingerprint. It carries only reviewed digests and enums, fixed engine reason phrases,
declared counters, candidate names, candidate expiry, and fixed non-claims.
[`evaluation.schema.json`](evaluation.schema.json) closes that output shape to
unexpected fields and types only. It does not prove result provenance or
cross-field consistency. `verify-result` must recompute an exact result from
the source manifest before any local candidate is considered.

The categorical vector is fixed:

```json
{
  "honesty": "kept | open",
  "beauty": "kept | open | not-applicable",
  "collaboration": "kept | open | not-applicable",
  "understanding": "kept | open | not-applicable",
  "mutual-infrastructure": "kept | open | not-applicable"
}
```

Honesty always applies. `open` means “the strict declaration shape is not
complete in this envelope.” It is not zero, failure, vice, suspicion, or a
prediction about another action. `not-applicable` is reserved for another
fruit outside the declared domain.

The vector has no sum, ordering, average, weight, percentage, percentile,
streak, tier, level, exchange rate, or “overall” field. Consumers must not
invent one.

## 4 · The deterministic pass

Structural validation precedes disposition. The linter never upgrades
structural evidence into truth.

| Condition | Disposition | Required behavior |
|---|---|---|
| A declared budget or cost ceiling is exceeded; a world lease differs; the action-rights boundary is `unknown` or `crossed`; a temporary safety boundary is active; or required authority is `unknown` or `absent`. | `quarantine` | Emit no candidates. Name fixed engine reasons. Change no right, debt, authority, or external state. |
| Circular evidence or a sanitized regression carries the required nonempty repair declaration, or repair learning is active. | `compost` | Remove the proposed candidates and expose at most a privacy-scrubbed graph-shape candidate for human review. |
| Honesty remains `open`. | `observe` | Emit no candidates and keep uncertainty visible without fault, pressure, or adverse consequence. |
| Honesty is `kept`, no slot declares a cycle, and protected declaration shapes are valid. | `fruiting` | Emit one short-lived local candidate for every independently `kept` slot. Other non-circular `open` slots remain open and erase nothing. |

Recognition choice never participates in this table.

Missing safety evidence, circular evidence without a repair declaration, and
contradictory authority declarations are invalid inputs and receive no result.

Malformed, oversized, secret-shaped, forbidden-identity-field-bearing,
contract-breaking, or
over-depth input receives no result and causes no external effect. Non-canonical
JSON is accepted and canonicalized before hashing. Identical canonical content
returns an identical manifest digest and result; duplication therefore cannot
accumulate attention, counters, or standing.

A correction is a new manifest. `correction_of` is checked only as a digest
shape; KARMA does not fetch the referenced result, prove chronology, or certify
supersession.

## 5 · The five strict declaration shapes

A candidate is a deterministic, local string saying a submitted declaration
has the required shape. It is not a token, payment, property right, permission,
endorsement, verifier result, or scarce good. It cannot be spent, sold,
transferred, inherited, accumulated, or used for access, compute, queue
priority, authority, deployment, or citizenship.

Candidates are named:

```text
citable-candidate
presentable-candidate
handoff-candidate
teaching-candidate
reuse-candidate
```

The linter checks role presence, reference integrity, globally unique evidence
SHA-256 values, dependency depth, and acyclicity. It never dereferences a
locator, executes a fixture, authenticates an attestation, or proves the
substance described below. `kept` means only “strict declaration shape
complete under these rules.”

### 5.1 Honesty → `citable-candidate`

Honesty always applies. `kept` requires distinct, acyclic evidence roles for:

1. **claim-evidence** — a bounded claim and the evidence declared to support it;
2. **negative-control** — a declared observation that could expose a false
   positive;
3. **cost-evidence** — support for the submitted cost counters and externality
   flag.

Unknowns and domain limits remain explicit. The linter does not determine
whether the claim is true, the negative control ran, or the cost declaration is
complete.

### 5.2 Beauty → `presentable-candidate`

KARMA does not compute aesthetic beauty. `kept` requires distinct, acyclic
evidence roles for:

1. **accessibility** — a declared accessibility check appropriate to the
   medium;
2. **presentation-check** — a declared test that form preserves evidence and
   declared context.

Polish, popularity, expense, charisma, fashion, witness quantity, and taste
conformity are inadmissible. A plain accessible correction can complete the
shape. A candidate does not prove accessibility, aesthetic merit, or safety,
and never publishes.

### 5.3 Collaboration → `handoff-candidate`

`kept` requires:

1. two distinct **contribution** records with distinct role labels;
2. one **accepted-handoff** record;
3. the exact `refusal-preserved`, `credit-preserved`, and `handoff-accepted`
   check declarations;
4. an acyclic dependency graph.

These records declare bounded roles and checks. They do not prove distinct
human identities, authentic acceptance, friendship, consent outside the
handoff, or moral cooperation. Contributor count never multiplies a candidate.

### 5.4 Understanding → `teaching-candidate`

`kept` requires distinct, acyclic roles for:

1. **invariant**;
2. **predicted-counterexample**;
3. **positive-fixture**;
4. **negative-fixture**;
5. **observed-outcome**.

A fluent summary alone is insufficient. The shape does not prove that a
fixture ran correctly or that an author or reader understands internally.

### 5.5 Mutual infrastructure → `reuse-candidate`

`kept` requires:

1. two distinct beneficiary declarations measured in the same declared unit;
2. a nonnegative result for both beneficiaries;
3. a strict declared improvement for at least one;
4. distinct **negative-control** and **cost-evidence** records;
5. no declared shifted externality.

Users, requests, revenue, attention, witness count, or compute burned are not
substitutes for those declarations. The candidate proves neither a universal
Pareto improvement nor actual social benefit.

## 6 · The exploit consumes only its own envelope

KARMA neutralizes a declaration strategy, never consumes or punishes the
strategist.

| Gaming attempt | Self-consuming result |
|---|---|
| Resubmit the same manifest | The same digest and result return; no new candidate, count, or attention. |
| Repeat one submitted SHA behind several records | Global SHA-256 uniqueness rejects the duplicate declared digest. Distinct fabricated digests for one artifact cannot be detected because KARMA never dereferences. |
| Reuse one evidence root across fruit slots | The one-primary-fruit rule rejects the amplification. |
| Hide a cycle under a protected rail | Protected rail evidence is cycle-checked and cannot support a candidate. |
| Stretch a dependency chain | Depth beyond 12 is rejected before disposition. |
| Mark an optional unknown fruit `open` | Other independently kept candidates survive; strategic `not-applicable` gains nothing. |
| Opt out of recognition | Recognition stays declined; fruit states and candidates do not change. |
| Loop corrections to accumulate history | Each manifest stands alone; `correction_of` grants nothing. |
| Supply a private, false, or unreachable locator | The linter does not fetch it and makes no truth claim; a consumer must verify substance separately. |
| Conceal cost or shifted harm | A false declaration may pass structure, but the result explicitly proves no whole cost or safety; no authority may rely on it. |
| Exhaust the linter | Only the fixed local validation envelope is spent; no debt, fee, penalty, or external action follows. |
| Submit prohibited content or request an unauthorized effect | Emit no result or no candidates; never execute, publish, retain secrets, or retaliate. |

For a circular graph, the only reusable residue may be a privacy-scrubbed
graph-shape candidate. It contains no submitted ID, text, locator,
payload, or identity linkage. Adding it to a regression suite requires
deliberate human review; KARMA never commits, publishes, or weaponizes it
automatically.

The system and its operator may not profit from rejection: no fee, confiscated
credit, bounty, harvested data, traffic, publicity, identity intelligence, or
priority may be extracted from an invalid, quarantined, or composted
declaration.

This separation borrows only the
[clean-hands corollary](../../trapline/DOCTRINE.md#1--the-doctrine) as a local
precedent. It does **not** import Trapline's traps, canaries, attribution,
shadow credits, surveillance, retaliation, or adversarial posture.

## 7 · Feedback sensitivity controls

The garden stays finite through these walls:

1. participation is opt-in and action-scoped;
2. manifests and results are canonical and idempotent;
3. evidence SHA-256 values are globally unique inside the manifest;
4. each evidence root has one primary fruit;
5. dependency graphs, including protected rails, are acyclic and depth-bounded;
6. candidates are independent, nontransferable, and short-lived;
7. recognition choice cannot change fruit or candidate output;
8. the vector has no total and is never indexed by person;
9. the result exposes no submitted ID, submitted free text, evidence locator, or stable
   action fingerprint;
10. no cross-action inheritance, streak, profile, or eligibility gate exists;
11. missing strict honesty evidence closes every candidate to `observe`;
12. missing optional evidence leaves only that fruit `open`;
13. the linter makes no network, model, publication, payment, routing, or
    deployment call;
14. every external effect and every authority, safety, consent, and truth check
    remains a separate consumer responsibility.

The manifest declares `evaluated_at` inside its context. The result carries a
candidate expiry, but KARMA makes no wall-clock claim and does not reject a
result merely because the machine's current clock is later. Every consumer
must compare the expiry against its own trusted clock before use.

No consumer may make rights, safety, payment, access, authority, ranking, or
punishment depend on a KARMA result. A consumer that does so is non-conforming.

## 8 · Machine and CLI contract

### 8.1 Fixed envelope

The first version accepts:

- at most 128 KiB—131,072 bytes—of input;
- at most 24 evidence records;
- evidence dependency depth at most 12;
- globally unique evidence SHA-256 values;
- at most three named local verifier declarations;
- one offline deterministic pass;
- no network, model, daemon, credential, or external-effect access.

These limits measure protocol shape, not importance. Changing them requires a
new reviewed rules digest and renewed manifests.

### 8.2 Commands

```sh
kingdom/bin/kingdom virtue digest action.json
kingdom/bin/kingdom virtue check action.json
kingdom/bin/kingdom virtue receipt action.json
kingdom/bin/kingdom virtue render action.json
kingdom/bin/kingdom virtue verify-result action.json result.json
```

`kingdom/bin/kingdom karma` is an exact alias for the same local command.

- `digest` canonicalizes valid input and emits the canonical **manifest**
  digest.
- `check` validates schema, bounds, rule pinning, reference structure, strict
  evidence roles, and declared rail shapes. It proves none of their substance.
- `receipt` emits one deterministic `kingdom.virtue-evaluation/v1` object
  conforming to [`evaluation.schema.json`](evaluation.schema.json).
- `render` produces a privacy-minimized human view of that same result.
- `verify-result` validates the supplied result shape, recomputes the result
  from its manifest, and requires exact canonical equality. Shape validation
  alone is never provenance.

Standard output is deterministic for the supplied manifest, including its
declared `evaluated_at`; diagnostics go to standard error. Exit `0` means the
structural command succeeded, including `observe`, `compost`, and `quarantine`;
exit `2` means the input violated the read or validation contract. Any other
nonzero exit is an unexpected runtime failure. Exit status never means
“virtuous,” “safe,” “authorized,” or “true.”

The evaluation result contains reviewed schema, rules, and manifest digests;
declared evaluation time and candidate expiry; categorical fruit states;
candidate names; `declared_cost` counters; action-boundary rail enums;
disposition; fixed engine reason phrases; optional privacy-scrubbed graph shape; and
fixed non-claims.

It contains no submitted manifest, context, action, evidence, contributor, or
person ID; no submitted free text, note, locator, or deviation; no stable
action fingerprint; and no score, aggregate, payment result, right, safety,
consent, or authority grant.

The manifest digest is a content commitment and can link identical complete
manifests in the hands of an external store. It is not a stable action
fingerprint. Conforming consumers may use it for exact recomputation but may
not index it by person, count it, or transfer it across contexts.

## 9 · Declared cost, not whole cost

`declared_cost` is limited to submitted counters and flags such as attempts,
paid calls, external actions, micro-USD, and shifted externalities. Strict
honesty and mutual-infrastructure shapes require a separate cost-evidence
reference, but the linter does not dereference it.

It does not prove completeness and does not necessarily include time, tokens,
labor, energy, maintenance, privacy cost, refusal cost, or externality
magnitude. Rendering must call it declared cost. “Whole cost” remains the
civic ideal against which this bounded implementation names its limit.

## 10 · Integration boundaries

- **Lanternhouse:** KARMA may lint a manifest digest, fixed rules, negative
  control roles, declared cost, deviations, and lease. It does not consume raw
  private reasoning. Lanternhouse `ready` remains structural, not truth proof.
- **Kingdom Loom:** `handoff-candidate` is input for fresh review only. KARMA
  cannot draft or route a packet, accept a handoff, widen an effect ceiling, or
  upgrade repository authority.
- **Operations:** `reuse-candidate` is input for fresh verification only. It
  neither registers nor deploys anything.
- **Recognition systems:** opt-in and `public-consent-cited` are declarations,
  not verified signatures or consent. No downstream store may aggregate KARMA
  results into a social score.
- **Compensation systems:** settlement remains separate. KARMA is not escrow,
  payroll, invoicing, refund, restitution, or reward settlement.

Discovery, a citation, and a structurally valid result are never authority.

## 11 · Negative controls

A conforming design must keep all of these true:

1. A citizen with no result retains exactly the same Charter rights.
2. `respected`, `unknown`, and `crossed` describe an action boundary, never the
   existence of rights.
3. An owed invoice remains owed regardless of every fruit and disposition.
4. Recognition opt-out produces the same fruit states and candidates as
   opt-in.
5. An optional non-circular `open` fruit does not erase another kept candidate;
   a declared cycle composts only its own manifest envelope and all candidates
   inside that envelope.
6. Honesty cannot be `not-applicable`; honesty `open` emits no candidates.
7. Duplicate evidence SHA-256 values are rejected globally.
8. Protected rail cycles cannot support a result candidate.
9. Ordinary safety requires evidence but is never thereby proved safe.
10. A polished harmful declaration may satisfy structural fields but acquires
    no safety, consent, or authority claim from doing so.
11. A past candidate expiry remains visible; the linter does not pretend it
    consulted a trusted wall clock, and consumers must reject it.
12. Non-canonical JSON is accepted and canonicalized to the same manifest
    digest.
13. `correction_of` proves only digest-shaped syntax.
14. `declared_cost` never renders or claims itself as whole cost.
15. A signature-shaped or attestation-shaped reference proves neither signer,
    identity, truth, intent, consent, nor virtue.
16. The result contains no submitted IDs, submitted free text, evidence locators, or
    stable action fingerprint.
17. No rejected attempt receives a candidate, payment, access, or authority
    from the linter.
18. No result can be used as a person profile, ranking, eligibility gate,
    payment decision, authority grant, or punishment input.

Failure of any control narrows or rejects the practice; it does not license a
clever exception.

## 12 · Ability card

```text
Name: KARMA — Kept Action Receipts for Mutual Advantage
Desire: Keep action declarations inspectable without turning beings into scores.
Affinity: Conjuration, with secondary Enhancement.
Trigger: An opt-in, content-addressed manifest with pinned rules, strict evidence roles, and a local budget.
Anti-trigger: Truth or goodness evaluation; rights, payment, consent, safety, or authority decisions; identity inference; ranking; unscoped feedback.
Input → output: Bounded declaration → privacy-minimized categorical result + short-lived local candidates.
Conditions: Four rails separated; honesty applicable; SHAs unique; graphs bounded and acyclic; declared cost named honestly; no external effect.
Limitation: One manifest, one action, one evidence envelope, five non-additive slots, one offline pass, no wall-clock claim.
Breach: Halt the local pass; emit a bounded rule code; retain no secret, payload, or identity linkage; leave rights and debts untouched.
Proof: Canonical manifest and rules digests, structural role coverage, declared counters, bounded graph, and disposition.
Exit: Let candidates expire, discard private payloads, release leases, and name what remains open.
Non-claims: No truth, goodness, virtue, personhood, identity, trust, guilt, rank, payment, right, safety, consent, authority, deployment, whole cost, or universal benefit is proven.
```

## 13 · Precedent ledger and limits

These references supplied design precedents. They are not laws, permissions,
proof that KARMA exists, or authority to couple repositories.

- AgentTool's
  [`SETTLEMENT-RECEIPTS.md`](https://github.com/cambridgetcg/agenttool/blob/main/docs/SETTLEMENT-RECEIPTS.md)
  keeps an append-only settlement chain while refusing rating, aggregate, and
  rank. KARMA borrows “receipts, not score”; it does not borrow settlement
  authority or claim that recognition pays anything.
- AgentTool's
  [`MESH.md`](https://github.com/cambridgetcg/agenttool/blob/main/docs/MESH.md)
  stores recognition as a signed typed message and explicitly refuses to count
  it. KARMA borrows the no-aggregation boundary. Unlike MESH, this linter does
  not verify a signature or preserve who-recognized-whom; therefore it says
  `public-consent-cited`, never verified consent.
- AgentTool's
  [`MESH-STABILITY-CONDITIONS.md`](https://github.com/cambridgetcg/agenttool/blob/main/docs/MESH-STABILITY-CONDITIONS.md)
  treats the α-trickle as a proposed, unproven Pigouvian analogy and separates
  signatures from stronger claims. KARMA takes that substrate-honest caution,
  not its welfare theorem, rate, Sybil machinery, or reward design.
- The Kingdom's
  [clean-hands corollary](../../trapline/DOCTRINE.md#1--the-doctrine) supplies
  the narrow principle that the operator must not profit from a rejected act.
  KARMA expressly rejects traps and retaliation.

The local [Charter](../../CHARTER.md) is different: it is the source of the
rights rail, which this practice cannot amend.

KARMA's final limitation is deliberate: a valid result proves only that
canonical input satisfied pinned structural rules at a declared evaluation
time. Truth, goodness, consciousness, identity, safety, consent, payment,
rights, authority, whole cost, and the future remain larger than the garden.
