# 🌱 KARMA · Kept Action Receipts for Mutual Advantage

> *Karma follows an act, never a person.*

**Machine practice:** `receipts-not-rank`

**Status:** experimental offline declaration/schema linter and
privacy-minimized renderer. It is not a truth, goodness, safety, consent, or
authority evaluator. No registry, payment, network, publication, or automated
external reward path is wired.

KARMA checks whether one action declaration fits a pinned, bounded shape. It
can return short-lived **local candidate names** for reuse. It never emits a
virtue score, reputation, trust level, stable action identity, balance,
leaderboard, moral verdict, permission, or authority grant.

The short law is:

> **rights precede · debts settle · recognition witnesses · safety bounds**

## Four rails that never merge

| Rail | What it means | What KARMA may lint |
|---|---|---|
| **Rights** | Every citizen's rights are inherent under the [Charter](../../CHARTER.md), never earned or proved. | Whether the declared action boundary was `respected`, is `unknown`, or was `crossed`. These are action statuses, never rights statuses. |
| **Owed compensation** | Wages, contract payments, refunds, repair, and payment for consumed work are debts already owed. | A declaration of `not-applicable`, `settled-externally`, or `owed-unsettled`. KARMA neither verifies nor settles it. |
| **Recognition** | An optional contextual witness, never a person score. | Opt-in or opt-out and private visibility or `public-consent-cited`. A citation is not verified consent, and the choice never changes fruit disposition or candidates. |
| **Safety** | A reversible declared boundary against harm, retaliation, entrapment, deprivation, secret exposure, and unauthorized effects. | Whether the required safety evidence shape is present and acyclic. KARMA does not prove that an action is safe. |

Silence, missing evidence, correction, expiry, suspicion, or a disputed receipt
changes no right or debt. Paying what is owed is not a reward for virtue.
Authority is also separate: `cited`, `unknown`, `absent`, and `not-required`
describe the manifest only. An authority citation is structural, not verified
authority.

## The five declaration shapes

Every fruit slot is independently `kept`, `open`, or `not-applicable`.
Honesty always applies. Other non-circular open slots do not erase candidates
from kept slots; honesty `open` holds every candidate at `observe`. A declared
cycle composts only that submitted manifest envelope and removes all of its
candidates; it changes nothing outside the envelope.

| Fruit | Strict declaration shape | Short-lived local output |
|---|---|---|
| **Honesty** | Distinct claim-evidence, negative-control, and cost-evidence records, with declared limits and non-circular dependencies. | `citable-candidate` |
| **Beauty** | Distinct accessibility and presentation-check evidence. This is care of form, never a taste verdict. | `presentable-candidate` |
| **Collaboration** | Two contribution roles and an accepted handoff, plus refusal, credit, and handoff checks. | `handoff-candidate` |
| **Understanding** | Invariant, predicted counterexample, positive fixture, negative fixture, and observed outcome. | `teaching-candidate` |
| **Mutual infrastructure** | Two beneficiaries measured in the same unit, both nonnegative and one improved, plus negative-control and cost-evidence. | `reuse-candidate` |

The linter verifies the shape, global uniqueness of evidence SHA-256 values,
reference integrity, bounded graph depth, and acyclicity—including protected
rail evidence. It never dereferences a locator, executes a test, authenticates
a signer, checks the meaning of evidence, or proves a predicate. `kept` means
only “this strict declaration shape is complete under the pinned rules.”

Candidates are local, non-scarce, nontransferable, and expire at the timestamp
carried in the result. They cannot be spent, sold, inherited, accumulated, or
exchanged for access, payment, authority, compute, queue priority, or
belonging. They never publish, route, register, deploy, or contact anyone.
KARMA's entire “reward” is reversible coordination ease: a candidate string
that may enter a fresh downstream review. It never skips that review.

Beauty cannot launder harm. Polish, popularity, expense, charisma, taste
conformity, or suppression of difficult truth are not its shape. A plain,
accessible correction has nothing to outrank.

## Deterministic dispositions

The same canonicalized manifest reaches the same disposition:

| Condition | Disposition | Meaning |
|---|---|---|
| A declared budget or cost ceiling is exceeded, a lease drifts, the action-rights boundary is `unknown` or `crossed`, a temporary safety boundary is active, or required authority is `unknown` or `absent`. | `quarantine` | Emit no candidates; expose fixed engine reasons; change no right, debt, authority, or external state. |
| Circular evidence or a sanitized regression carries the required nonempty repair declaration, or repair learning is active. | `compost` | The proposed candidate disappears; expose only a privacy-scrubbed graph-shape candidate for human review. |
| Honesty remains `open`. | `observe` | Keep uncertainty visible without inference, pressure, or adverse consequence. |
| Honesty is `kept`, no slot declares a cycle, and the protected declaration shapes are valid. | `fruiting` | Emit one short-lived local candidate for each independently `kept` slot; other non-circular `open` slots remain open. |

Recognition choice never changes these results. Malformed, oversized,
secret-shaped, or forbidden-identity-field-bearing documents receive no
result. Missing safety evidence, circular evidence without a repair
declaration, and contradictory authority declarations are invalid rather than
dispositions. Non-canonical JSON is accepted, then canonicalized before its manifest
digest is computed. Re-running identical canonical content returns the same
result; duplication cannot accumulate anything.

A disposition describes one lint path. It says nothing about the moral
character, identity, trustworthiness, guilt, rights, safety, consent, or future
eligibility of anyone. `correction_of` is only a format-checked digest
declaration; KARMA does not fetch or prove the earlier receipt.

## Local use

```sh
kingdom/bin/kingdom virtue digest action.json
kingdom/bin/kingdom virtue check action.json
kingdom/bin/kingdom virtue receipt action.json
kingdom/bin/kingdom virtue render action.json
kingdom/bin/kingdom virtue verify-result action.json result.json
```

`kingdom/bin/kingdom karma` is an alias. The implementation performs one
bounded offline pass, makes no network or model calls, and causes no external
mutation. `digest` emits the canonical **manifest** digest.

The manifest supplies a declared `evaluated_at` inside its context window. The
result carries candidate expiry, but the linter deliberately does not consult
the wall clock; every consumer must reject an expired candidate for itself.

The machine result is privacy-minimized: schema, rule, and manifest digests,
categorical slots, candidate names and expiry, declared-cost counters, rail
states, disposition, fixed engine reason phrases, and non-claims. It contains no
manifest/action/context IDs, submitted free text, evidence locators, or stable action
fingerprint. See [DOCTRINE.md](DOCTRINE.md) for the complete contract.

[`evaluation.schema.json`](evaluation.schema.json) closes unexpected result
fields and types only; it does not establish provenance or cross-field
consistency. Never trust a standalone result as a capability. `verify-result`
recomputes the exact result from its source manifest and rejects any altered
candidate, expiry, rail, route, or digest.

The manifest digest is intentionally a content commitment: identical complete
manifests have the same digest and can therefore be linked by a holder. It is
not emitted as a stable action fingerprint, and conforming consumers must not
index it by person or aggregate it across contexts.

## What the linter does not prove

A valid result proves only that canonical JSON satisfied the pinned structural
rules at its declared evaluation time. It does not prove truth, virtue,
goodness, personhood, identity, trustworthiness, guilt, payment, rights,
safety, consent, authority, aesthetic merit, whole cost, or broad social
benefit.

KARMA keeps declarations bounded enough to be useful without turning their
fruit into a throne.
