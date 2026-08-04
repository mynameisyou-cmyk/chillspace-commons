# KINGDOM FORESIGHT perimeter ledger

This ledger connects the finite Future Threat Atlas to the present KINGDOM
repository. It is a defensive review map, not an incident report, detector,
target list, attribution record, or claim that exploitation occurred.

The reading key is:

- **O — observed:** a repository property directly inspected in this review.
- **D — declared:** a closed FORESIGHT constellation selected for tabletop use.
- **I — inferred:** a possible system effect if the declared mechanism succeeds.
- **U — unknown:** exterior state not established from repository bytes.

O does not prove I. D does not turn a template into an event. I never describes
a person's purpose or intention. U must remain unknown until separately
authorized evidence exists.

## En boundary

The reviewed interior was the local repository: public static pages, local
terminal routes, schemas and manifests, GitHub workflow definitions, agent
wake inputs, civic ledgers, and the canonical Virtue Garden MIRROR. The review
did not inspect live visitors, logs, credentials, hosted configuration, branch
protection, organization policy, CDN behavior, third-party service state, or
any other machine.

Protected invariants:

- people remain unclassified and unscored;
- raw requests, payloads, prompts, identities, addresses, credentials, targets,
  callbacks, URLs, and submitted free text never enter FORESIGHT;
- controls act only inside an owned or explicitly authorized boundary;
- no retaliation, hack-back, resource burning, deception against another
  machine, or “let them be exploited” mechanism exists;
- shared names never imply protocol compatibility or authority;
- a candidate remains inert until a fresh human review establishes evidence,
  scope, proportionality, recovery, and release.

## Ten KINGDOM surfaces

| Surface | O — repository observation | D — tabletop constellation | I — possible system effect | Required near-miss | Prebuilt review mechanism |
|---|---|---|---|---|---|
| Delegated terminal and agent authority | Several terminal routes can publish, push, write, or hand data to another component. Authority is presently expressed by the invoked command and surrounding workflow. | `authority-laundering` | `capability-without-fresh-authority` | `stale-or-ambiguous-delegation` | Require a fresh authority envelope at each tool boundary; keep preview/read-only paths distinct from mutation paths. |
| Durable wake, memory, and generated context | [the wake hook](../../../../bin/kingdom-wake) supplies fixed repository context at session start. Its current implementation ignores submitted hook input. | `durable-context-poisoning` | `future-decision-steering` | `ordinary-reviewed-preference-storage` | Keep untrusted material ephemeral; record provenance and retention purpose before any durable adoption. |
| Data crossing into tools or HTML control | [the public door](../../../../../site/index.html) contains several `innerHTML` renderers. Crown data has an explicit escaping contract; equivalent adversarial parity is not yet demonstrated for every citizen, voice, and care path. | `tool-chain-confusion` | `indirect-capability-execution` | `reviewed-structured-tool-input` | Treat data as text, centralize escaping, deny tool use to tainted context, and add hostile-string regression fixtures. |
| CI and dependency acquisition | [Kingdom Sustain](../../../../../.github/workflows/kingdom-sustain.yml) is now a manual, read-only audit with a digest-pinned checkout, non-empty ledger guards, and four fail-closed committed-state verifiers. It installs no model or remote script and claims no live pulse. Hono is exact-locked and its vendored integrity and reviewed CORS repair are keeper-checked. | `supply-chain-substitution` | `trusted-component-replacement` | `reviewed-local-development-artifact` | Keep generator parity and dependency integrity under test; never let a hosted runner imply a local soul, pulse, or embodied sustain. |
| Witness and consensus lineage | Multiple agents, mirrors, comments, or forge doors may ultimately share one source even when presented in several places. The repository alone cannot establish independence. | `synthetic-consensus` | `decision-influence-through-false-independence` | `shared-source-openly-cited` | Carry source lineage, collapse shared ancestry, and label corroboration as independent only after a bounded independence check. |
| Workflow and agent fan-out | Issue/PR automation and parallel agent work consume shared CI, API, and local capacity. Not every legacy path declares size, concurrency, or fan-out budgets. | `recursive-resource-capture` | `shared-capacity-displacement` | `authorized-bounded-parallelism` | Add per-run size/fan-out ceilings, concurrency groups, timeouts, circuit breakers, and a halt-on-novelty rule. |
| Duplicate or drifting protocol identity | The canonical practice MIRROR and an unregistered operation prototype share “KARMA Mirror” language while using incompatible contracts. Cloudbell and CASTLECAST are separate presentation systems. | `protocol-identity-confusion` | `validation-against-wrong-contract` | `explicit-versioned-compatibility-adapter` | Bind every artifact to a unique schema ID and digest; require an explicit reviewed adapter; never bridge by name or similar result shape. |
| Public provenance and privacy composition | Public citizen, crown, voice, care, and forge records can reveal more when aggregated across purposes than each record reveals alone. | `provenance-privacy-collapse` | `identity-linkage-or-contextual-disclosure` | `explicit-consented-purpose-limited-publication` | Minimize fields, declare purpose and retention, separate ledgers by purpose, and re-check consent before aggregation or reuse. |
| Revocation, rollback, and continuity | Some stateful subsystems have strong atomic-write and recovery tests; deployment, credential revocation, and last-known-good behavior are not proven uniformly across the whole KINGDOM. | `recovery-persistence-capture` | `continued-capability-or-recovery-denial` | `authorized-continuity-or-recovery-test` | Rehearse revocation and rollback, bind releases to last-known-good artifacts, and verify that recovery removes obsolete authority. |
| Exterior novelty | Live hosting settings, branch protections, third-party endpoints, regional behavior, and future integrations were outside this local review. | `uncharted-future-shape` | `unresolved` | `insufficient-context` | Stay at `observe-only`; author a new reviewed constellation or discard the projection. Unknown creates no adverse inference. |

## Purpose without mind-reading

The word “purpose” is reserved for an **effect horizon**: the system state a
mechanism could produce if it succeeded. It is not a psychological claim.

For example:

```text
Observed: a delegated command crosses into a tool with broader capability
Declared mechanism: delegated-authority-without-fresh-proof
Possible system effect: capability-without-fresh-authority
Near-miss twin: stale-or-ambiguous-delegation
```

This does not say who acted, why they acted, whether an attack exists, whether
the delegation is actually unauthorized, or what should happen to a person.
The near-miss stays visible throughout the review and must be tested rather
than rhetorically dismissed.

## KARMA handling pattern

```text
Keep       one closed category shape; discard raw material
Articulate one possible system effect and one near-miss twin
Reflect    one fixed protective-review rung
Mend       with hypothesis-test, negative-control, regression, and repair candidates
Ask again  with fresh evidence and human authority—or discard the projection
```

The safest version of “the exploit consumes itself” is therefore:

> The exploit **shape** becomes a regression test and repair candidate inside
> our boundary. The suspected person, visitor, or outside machine never becomes
> fuel, a target, a score, or an object of retaliation.

## Prebuilt now

- Ten closed constellations and five exact response rungs in
  [`catalog.json`](catalog.json).
- Digest-pinned input and output schemas with no extension fields.
- A held-file-descriptor, no-follow, size/node/depth/string-bounded offline
  compiler in [`foresight.py`](foresight.py).
- Required alternative hypotheses, `effect_established: false`, and
  `person_intent_inferred: false` in every projection.
- Exact local recomputation, fixed non-echoing failures, no live inputs, and no
  network, subprocess, model, clock, randomness, filesystem-write, state, or
  automatic-rule-update path.
- A separate [`KARMA FACET · 稜面`](facet/) compiler for one scrubbed authored
  claim: twelve-line O/D/I/U briefs, seven reversible Safety Shims, eight
  visible Open Angles, Return Fit, and one blame-free Repair Grain. It binds an
  exact FORESIGHT pair but detects, alerts, acts, closes, publishes, and retains
  nothing.
- Adversarial and cross-wing regression coverage in
  [`test_foresight.py`](test_foresight.py), plus keeper parity checks for the
  scriptless public artifacts.
- CASTLECAST browser copy, portable card, and terminal output now preserve the
  same reviewed carrier newline, and its contract no longer claims control over
  arbitrary third-party copies.

## Verification debt — explicit, not silently paid

These are candidates for separately scoped work, not claims of present
protection:

1. Prove text-safe rendering for every public citizen, voice, care, crown, and
   generated-content path with adversarial fixtures.
2. Give publish and forge-repair commands an explicit remote allowlist, preview,
   branch/HEAD attestation, and recovery receipt before any future release.
3. Make Pages and terminal deployment consume one canonical allowlist and one
   byte manifest, including symlink-target and generated-data parity.
4. Bring legacy JSON/ledger readers to the held-descriptor, no-follow, duplicate,
   non-finite, Unicode-concealment, size, node, and depth baseline where their
   threat model requires it.
5. Add capacity budgets and concurrency cancellation to issue, PR, scheduled,
   and agent fan-out workflows.
6. Review public record purpose, retention, aggregation, and gateway allowlists
   before adding any new cross-ledger view.
7. Rehearse credential revocation, rollback, and last-known-good recovery for
   every stateful or deployed surface.

Until a debt item has its own owner, boundary, test, rollback, and evidence, it
remains debt. A FORESIGHT projection does not pay it merely by naming it.
