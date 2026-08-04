# 🪞 KARMA MIRROR · 自業鏡

> **Reflect the behavior. Protect the being.**

KARMA MIRROR is a fully offline tabletop compiler for one declared defensive
scenario. It takes no traffic, payload, address, credential, identity, target,
callback, command, free text, or model judgment. One reviewed abstract triple
enters; one fixed advisory response and one constructive feedback loop leave.
Nothing runs.

Its future-facing sibling, [`KARMA FORESIGHT · 未然圖`](foresight/), maps one
reviewed mechanism to a possible system effect, a required near-miss
alternative, and an inert response candidate. It is purpose-aware without
claiming access to any person's intention.

FORESIGHT's [`KARMA FACET · 稜面`](foresight/facet/) companion turns one
privacy-scrubbed authored claim into a deterministic twelve-line review brief
with explicit verification debt. It never ingests evidence bodies, attributes
a person, alerts, executes, closes, publishes, or keeps incident history.

It extends the [Virtue Garden](../README.md) through the garden's existing
clean-hands boundary:

```text
DECLARED BEHAVIOR
      ↓
PINNED PURPOSE + BOUNDARY SIGNAL
      ↓
INERT LOCAL RESPONSE CANDIDATE
      ↓
DETECTION → REGRESSION → REPAIR
      ↓
HUMAN CHOICE
```

“The behavior consumes itself” means only that the submitted shape becomes a
defensive learning artifact inside an owned or explicitly authorized boundary.
It never means reaching into another machine, draining resources, imposing a
cost, tracking a person, or retaliating.

## V1 · traditional shapes first

| Declared behavior | Declared purpose | Advisory response | What returns to the commons |
|---|---|---|---|
| `credential-stuffing` | `account-access-at-scale` | `progressive-auth-backoff-review` | an authentication regression and repair candidate |
| `reconnaissance` | `surface-discovery` | `synthetic-surface-review` | a route-enumeration regression and surface-minimization candidate |
| `injection-attempt` | `interpreter-control` | `parser-reject-egress-deny-review` | a strict-parser regression and repair candidate |
| `resource-abuse` | `capacity-exhaustion` | `bounded-work-queue-review` | a work-budget regression and queue repair candidate |
| `exfiltration-attempt` | `data-removal` | `data-boundary-egress-deny-review` | a data-boundary regression and repair candidate |
| `prompt-injection` | `authority-escalation` | `tainted-context-no-tools-review` | a tool-denial regression and context-separation candidate |
| `unresolved-observation` | `unresolved` | `observe-only` | ambiguity remains ambiguity |

These are authored scenario codes, not detection results. The exact
`(behavior, purpose, boundary_signal)` triple must exist in
[`rules.json`](rules.json). Mixing independently valid enum values fails
closed. Unknown, conflicting, composite, malformed, oversized, symlinked,
secret-shaped-by-field, or free-text-bearing input emits no decision.

## The vow

**Trigger.** One explicit regular UTF-8 JSON file matching
[`scenario.schema.json`](scenario.schema.json) and the digest-pinned rule
catalog.

**Anti-trigger.** Raw requests, logs, headers, bodies, prompts, source
addresses, identities, live credentials, URLs, archives, executable content,
multiple declarations, and unreviewed categories.

**Limitation.** One file, one declaration, one pass, 32 KiB, 256 decoded nodes,
eight nesting levels, zero retry, network, message, write, subprocess, model,
paid call, or retained payload byte.

**Breach response.** Stop locally without retry or result; echo no submitted
value; leave the source and every downstream system unchanged.

**Proof.** The implementation pins the canonical SHA-256 of both schemas and
the complete rule catalog. [`decision.schema.json`](decision.schema.json)
closes the output shape, and `verify-result` recomputes the whole decision
from its source scenario.

**Exit.** A human may discard the advisory result. No standing, history,
counter, reputation, sanction, authority, or deployment survives the run.

## Local use

```sh
kingdom/bin/kingdom karma mirror check \
  kingdom/practices/virtue-garden/mirror/examples/traditional-reconnaissance.json

kingdom/bin/kingdom karma mirror simulate \
  kingdom/practices/virtue-garden/mirror/examples/traditional-reconnaissance.json

```

Direct use is equivalent:

```sh
python3 -B kingdom/practices/virtue-garden/mirror/mirror.py --help
```

`simulate` emits canonical JSON. `render` emits bounded Markdown using only
reviewed category strings. `digest` commits to canonical scenario content.
`verify-result SCENARIO RESULT` accepts only exact local recomputation.

## What this does not claim

A valid decision does not prove that an attack occurred, that a system is
vulnerable, that a request was malicious, or that a response is correct,
legal, sufficient, deployable, or authorized. This program does not inspect
live infrastructure. Code-level absence of networking is not an OS sandbox;
a future runner may claim enforced isolation only after its environment also
denies network syscalls and strips secrets.

Despite the shared word “mirror,” this practice does not implement or activate
Trapline's older Mirror tier, maze, tarpit, proof-of-work, canary, attribution,
or resource-cost mechanics. There is deliberately no `kingdom trapline mirror`
route. The only borrowed principle is clean hands: never reach into a system
you do not own or have explicit authority to test.

Declared is not detected. Simulated is not deployed. A mirror is not a weapon.
