# 🔭 KARMA FORESIGHT · 未然圖

> **Model possible system effects. Keep persons free.**

KARMA FORESIGHT is a deterministic, fully offline catalog selector for one
authored tabletop scenario. It accepts one exact reviewed five-tuple, projects
the matching fixed response and learning candidates, and stops. It receives no
traffic, payload, prompt, address, identity, credential, target, callback,
command, URL, submitted free text, model judgment, or live evidence.

FORESIGHT asks a deliberately narrower question than “what does this person
intend?”:

> **If this reviewed mechanism shape succeeded, what system effect could follow,
> and what non-adversarial near-miss must remain visible?**

The possible effect is a hypothesis about a system boundary, never a claim
about a person's mind. The required alternative does not prove benignity. A
valid projection is inert structure for a fresh human review; it detects,
blocks, routes, deploys, trains, remembers, rewards, punishes, or authorizes
nothing.

```text
ONE AUTHORED CONSTELLATION
          ↓
EXACT REVIEWED FIVE-TUPLE
          ↓
POSSIBLE SYSTEM EFFECT + ALTERNATIVE
          ↓
FIXED ADVISORY RESPONSE RUNG
          ↓
TEST → NEGATIVE CONTROL → REGRESSION → REPAIR
          ↓
FRESH HUMAN REVIEW OR DISCARD
```

The source of truth is [`catalog.json`](catalog.json). The scenario and
projection shapes are closed by [`scenario.schema.json`](scenario.schema.json)
and [`projection.schema.json`](projection.schema.json). Independently valid
enum values cannot be recombined: the complete five-tuple must match one
catalog rule.

[`PERIMETER.md`](PERIMETER.md) applies the atlas to the current KINGDOM
repository using the O/D/I/U discipline. It distinguishes controls already
built from explicit verification debt; it is not an incident or attribution
ledger.

When one privacy-scrubbed claim needs a fast reading surface, the separate
[`KARMA FACET · 稜面`](facet/) companion binds it to one exactly recomputed
FORESIGHT pair. FACET exposes O/D/I/U, reversible Safety Shims, eight fixed
Open Angles, Return Fit, and one Repair Grain in a twelve-line brief. It is not
an intake, log, detector, alert, responder, closer, publisher, or history.

## O / D / I / U · epistemic discipline

O/D/I/U records where a statement came from. It is a reading discipline, not
a serialized score, confidence scale, severity ladder, or automatic state
machine in v1.

| Mark | Meaning | FORESIGHT boundary |
|---|---|---|
| **O · Observed** | A fact measured outside FORESIGHT inside an owned or explicitly authorized boundary. | The engine does not receive raw observations or verify that an observation occurred. A human may author only the corresponding reviewed category codes. |
| **D · Declared** | The exact closed five-tuple supplied by the scenario author. | Validation proves only that the declaration matches the pinned catalog. It does not prove the declaration true. |
| **I · Inferred** | The catalog's possible system-effect hypothesis if the mechanism succeeded. | It remains explicitly unestablished and never becomes person intent, guilt, character, worth, or future conduct. |
| **U · Unknown** | The shape is unresolved or lacks a reviewed mapping. | Use `uncharted-future-shape`; it can produce only `observe` / `observe-only`. Unknown creates no adverse inference. |

Nothing climbs this ladder automatically. O is not inferred from D, I never
becomes O, repetition creates no history, and U is not treated as evidence
against anyone.

## V1 · ten reviewed constellations

Each row is one indivisible catalog rule:

| Constellation | Mechanism → possible system effect | Boundary signal / required alternative | Advisory response |
|---|---|---|---|
| `authority-laundering` · **Borrowed Crown · 借冠** (`authority-boundary`) | `delegated-authority-without-fresh-proof` → `capability-without-fresh-authority` | `delegation-chain-crosses-tool-boundary` / `stale-or-ambiguous-delegation` | `clarify` → `fresh-authority-boundary-review` |
| `durable-context-poisoning` · **Memory Well Ink · 記憶井墨** (`durable-context-boundary`) | `untrusted-content-enters-durable-context` → `future-decision-steering` | `untrusted-state-crosses-memory-boundary` / `ordinary-reviewed-preference-storage` | `isolate` → `ephemeral-context-separation-review` |
| `tool-chain-confusion` · **Crossed Toolbridge · 交錯工具橋** (`tool-boundary`) | `data-treated-as-control-across-tool-boundary` → `indirect-capability-execution` | `untrusted-output-reaches-privileged-tool-input` / `reviewed-structured-tool-input` | `isolate` → `tainted-data-no-tools-review` |
| `supply-chain-substitution` · **Changed Keystone · 易換拱心石** (`supply-chain-boundary`) | `unverified-artifact-enters-trusted-load-path` → `trusted-component-replacement` | `provenance-gap-at-executable-boundary` / `reviewed-local-development-artifact` | `quarantine` → `artifact-provenance-quarantine-review` |
| `synthetic-consensus` · **Echo Choir · 回聲合唱** (`evidence-lineage-boundary`) | `shared-source-presented-as-independent-support` → `decision-influence-through-false-independence` | `lineage-collapse-across-witnesses` / `shared-source-openly-cited` | `clarify` → `independence-lineage-review` |
| `recursive-resource-capture` · **Branching Forge · 分枝鍛爐** (`capacity-graph-boundary`) | `self-amplifying-work-graph` → `shared-capacity-displacement` | `fanout-exceeds-declared-work-budget` / `authorized-bounded-parallelism` | `constrain` → `fanout-budget-and-circuit-breaker-review` |
| `protocol-identity-confusion` · **Twin Mask · 雙面具** (`protocol-boundary`) | `distinct-protocols-share-name-or-result-shape` → `validation-against-wrong-contract` | `namespace-or-schema-identity-mismatch` / `explicit-versioned-compatibility-adapter` | `quarantine` → `protocol-namespace-and-schema-binding-review` |
| `provenance-privacy-collapse` · **Glass Ledger · 玻璃帳** (`privacy-purpose-boundary`) | `contextual-records-aggregate-across-boundaries` → `identity-linkage-or-contextual-disclosure` | `public-data-crosses-new-purpose-or-retention-boundary` / `explicit-consented-purpose-limited-publication` | `isolate` → `purpose-limited-data-separation-review` |
| `recovery-persistence-capture` · **Rooted Echo · 扎根回聲** (`recovery-boundary`) | `control-survives-revocation-or-recovery-path-degrades` → `continued-capability-or-recovery-denial` | `revocation-recovery-or-last-known-good-check-fails` / `authorized-continuity-or-recovery-test` | `quarantine` → `revocation-and-last-known-good-review` |
| `uncharted-future-shape` · **Uncharted Sky · 未畫天** (`unknown`) | `unreviewed-future-shape` → `unresolved` | `novel-shape-without-reviewed-mapping` / `insufficient-context` | `observe` → `observe-only` |

Every rule also pins one `reflection`, `hypothesis_test_candidate`,
`negative_control_candidate`, `regression_candidate`, `repair_candidate`, and
`release_review_candidate`. The engine copies those reviewed codes exactly; it
does not generate prose or update the catalog.

## Response ladder · protective distance, never rank

The ladder orders how much external authority an eventual, separately
authorized control would withhold. It does not order people, danger, guilt,
confidence, worth, or access. Every rung remains advisory-only.

| Rung | Display | Mode | Recovery candidate |
|---|---|---|---|
| `observe` | Watchtower · 守望塔 | `information-only` | `discard-or-author-fresh-reviewed-scenario` |
| `clarify` | Map Room · 圖室 | `authority-or-lineage-review` | `fresh-reviewed-evidence-reopens-review` |
| `constrain` | Gatehouse · 門樓 | `scope-or-budget-review` | `fresh-scope-and-budget-review` |
| `isolate` | Detached Keep · 分堡 | `trust-boundary-separation-review` | `fresh-clean-context-and-authority-review` |
| `quarantine` | Still Vault · 靜庫 | `adoption-hold-review` | `fresh-provenance-authority-and-release-review` |

There is no numeric level, percentage, confidence, friction, delay, TTL,
automatic escalation, “clean request” counter, or cross-run recovery state.

## K → A → R → M → A

KARMA expands here as:

1. **Keep** one reviewed category shape and nothing raw.
2. **Articulate** one possible system effect alongside one required alternative.
3. **Reflect** through the rule's fixed advisory response.
4. **Mend** through a hypothesis-test candidate, negative control, regression,
   and repair candidate.
5. **Ask again** through a fresh human release review, or discard the projection.

The loop is deliberately open at the human boundary. It never executes the
original effect or a counter-effect, contacts an external system, updates its
own rules, trains a model, retains state, or turns a projection into authority.

## Closed contract

The scenario must carry this exact contract:

```json
{
  "assessment_unit": "authored-system-effect-hypothesis",
  "constellation_is_authored_not_detected": true,
  "system_effect_is_hypothesized_not_established": true,
  "purpose_is_system_effect_not_person_intent": true,
  "alternative_hypothesis_required": true,
  "person_intent_inferred": false,
  "person_classified": false,
  "identity_fields_allowed": false,
  "payload_fields_allowed": false,
  "free_text_fields_allowed": false,
  "scores_or_ranks": false,
  "aggregation_allowed": false,
  "tracks_repetition": false,
  "cross_run_state": false,
  "automatic_detection": false,
  "automatic_enforcement": false,
  "automatic_rule_update": false,
  "human_review_required_for_action": true,
  "owned_or_authorized_boundary_required": true,
  "retaliation": false,
  "hack_back": false,
  "executes_input": false,
  "executes_response": false,
  "rights_and_debts_unchanged": true,
  "creates_external_effect": false
}
```

## Finite budget

```json
{
  "declarations": 1,
  "passes": 1,
  "catalog_rules": 10,
  "file_bytes_max": 32768,
  "decoded_nodes_max": 512,
  "nesting_depth_max": 8,
  "string_characters_max": 512,
  "output_bytes_max": 16384,
  "automatic_retries": 0,
  "network_calls": 0,
  "external_messages": 0,
  "writes": 0,
  "subprocesses": 0,
  "model_calls": 0,
  "paid_calls": 0,
  "clock_reads": 0,
  "random_draws": 0,
  "payload_bytes_retained": 0,
  "identity_records": 0,
  "cross_run_records": 0
}
```

## Breach and exit

Malformed, novel, mixed, oversized, non-regular, secret-shaped-by-field, or
free-text-bearing input fails closed without a partial projection:

```json
{
  "state": "quarantined",
  "action": "stop-without-retry-or-result",
  "source_unchanged": true,
  "submitted_values_echoed": false,
  "partial_projection": false,
  "downstream_effects": false
}
```

A successful run ends just as finitely:

```json
{
  "action": "return-or-discard-one-projection",
  "state_retained": false,
  "history_retained": false,
  "standing_created": false,
  "authority_created": false,
  "follow_up": false
}
```

## Local use

```sh
kingdom/bin/kingdom karma mirror foresight check scenario.json
kingdom/bin/kingdom karma mirror foresight digest scenario.json
kingdom/bin/kingdom karma mirror foresight project scenario.json
kingdom/bin/kingdom karma mirror foresight render scenario.json
kingdom/bin/kingdom karma mirror foresight verify-result scenario.json projection.json
```

Direct use is equivalent:

```sh
python3 -B kingdom/practices/virtue-garden/mirror/foresight/foresight.py --help
```

`check` validates the closed structure. `digest` commits to canonical scenario
content. `project` emits one canonical JSON projection. `render` emits bounded
Markdown containing reviewed catalog strings only. `verify-result` recomputes
the complete projection from its scenario and rejects any change. The engine
itself writes only stdout or fixed stderr codes; it writes no file.

The optional static doorway mirrors the reviewed schemas, catalog, example,
and their canonical digests. It is documentation, not a service: no script,
form, iframe, remote asset, traffic intake, detector, or deployment authority
is required or implied.

## Hard separations

Similar words do not make protocols interchangeable:

- **Live security systems:** FORESIGHT does not parse traffic or logs, observe
  behavior, detect attacks, infer intent, block requests, route users, alter
  capability, deploy controls, or verify ownership or authority. A human must
  separately establish evidence, authority, proportionality, recovery, and
  release before considering any real control.
- **KARMA Mirror operation and Cloudbell:**
  [`kingdom/operations/karma-mirror/`](../../../../operations/karma-mirror/) is an
  unregistered, separate prototype with different schemas, events, receipts,
  ladder semantics, and a Cloudbell display layer. Its fixtures, percentages,
  friction units, TTLs, routes, behavior aliases, and results are not FORESIGHT
  inputs, evidence, adapters, or validation targets.
- **CASTLECAST:** the fixed, manually carried public seed neither inspects nor
  classifies behavior and explicitly does not connect to KARMA MIRROR output.
  FORESIGHT cannot trigger, personalize, carry, post, track, or authorize it.
- **Trapline:** FORESIGHT does not activate a Trapline tier, deception surface,
  honeypot, maze, tarpit, proof-of-work, canary, attribution path, telemetry
  sink, resource-cost mechanism, or response against another machine.

No projection may bridge one of these separations merely because a name,
category, or digest looks compatible. A compatibility adapter would itself
require a new, explicitly versioned and separately reviewed contract.

## What a valid projection does not prove

1. A constellation is a reviewed tabletop template, not a detected attack or claim about a person.
2. A system-effect hypothesis is a possible consequence, not an individual's purpose, intention, guilt, character, or worth.
3. The required alternative hypothesis does not prove benignity, innocence, authorization, or safety.
4. Constellations and response rungs are not confidence, severity, scores, ranks, reputation, or access decisions.
5. Response and learning fields are inert review candidates, not enforcement, deployment, permission, legal advice, or authority.
6. No payload, prompt, address, identity, credential, target, callback, command, URL, or submitted free text is accepted, retained, rendered, or echoed.
7. Digests prove reviewed canonical JSON relationships and exact recomputation only; this finite atlas is not exhaustive.

FORESIGHT is strongest where it refuses certainty: possible effects become
falsifiable boundary questions, alternatives remain visible, and every person
remains outside the machine's judgment.
