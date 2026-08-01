# Mirror Garden: future KARMA rehearsal

This subtree is a prebuilt, local-only defense planner for possible future
Kingdom exploitation. It turns a **trusted adapter's categorical observation**
into a deterministic, redacted response plan. It does not ingest raw traffic,
identify a person, touch an attacker system, call a model, fetch a URL, write a
file, publish a message, or deploy anything.

It is deliberately unwired from Kingdom launchers, agents, Loom, request
runtimes, telemetry, and response automation. CI may execute its inert tests,
and the static Mirror Garden operations room may explain this boundary, but
neither path sends it traffic or grants it action. A later live adapter would
be a new security boundary and requires a separate authorization and review.

## The KARMA loop

1. **Keep the boundary** - raw traffic stays outside this engine. A reviewed
   adapter may emit only the closed event vocabulary.
2. **Assess the technique** - strict JSON, ASCII tokens, pins, provenance,
   novelty, and evidence limits fail closed.
3. **Restrict authority** - content, claims, skills, tools, manifests, and
   receipts never grant authority.
4. **Make a zero-effect plan** - exact policy routing selects only
   `allow`, `observe`, `throttle`, `deny`, `quarantine`, or one
   `isolated-no-egress` synthetic-mirror candidate.
5. **Audit the receipt** - the event becomes a digest; the full canonical
   receipt is reproducible and exactly replay-verifiable.
6. **Learn without feeding the exploit** - a human may convert one anonymized
   technique family into a regression fixture, Heartbrick, or LOVE-letter
   candidate. Raw attacker text, identity, links, counters, and publication are
   never carried forward.

That is the safe version of a KARMA loop: an attempted exploit can improve local
tests and inspire a reviewed kindness artifact, but cannot conscript the
Kingdom into retaliation or advertising.

## Nen ability card

**Name:** Mirror Garden - Aegis of Returned Lessons

**Affinity:** Transmutation. It changes a bounded technique signature into a
local defensive lesson.

**Trigger:** One complete `kingdom.karma.event/v1` object from a separately
trusted classifier, with `authority: none`, `scope: offline-synthetic`, and
`purpose: defensive-regression`.

**Anti-trigger:** Raw payloads, identity, paths, URLs, secrets, free text,
unknown authority, changed catalogs, symlinks, ambiguous provenance, novelty,
or more than one policy match.

**Vow:** No network, subprocess, model, secret read, filesystem write, external
message, public counter, source reflection, identity attribution, punishment,
or automatic publication.

**Breach behavior:** Malformed input emits only a fixed error. Syntactically
safe novelty emits a halted quarantine receipt. A changed pinned source makes
the whole bundle invalid. Loaded policy and binding objects are recursively
immutable. Every plan and verification call also revalidates the canonical
policy pin, static catalog bindings, and current engine bytes, so constructing
or replacing a Bundle object cannot smuggle a changed policy under old pins.

**Evidence:** Canonical receipts, exact replay, a closed policy, a mapped threat
model, an adversarial corpus, isolated-process tests, and a no-network/no-write
sandbox rehearsal.

## What is covered

The machine-readable threat model covers prompt and session poisoning,
authority laundering, capability confusion, Darwin path/link/TOCTOU seams,
secret and privacy exfiltration, provenance/repository/deployment substitution,
workflow and dependency poisoning, active-content injection, SSRF, resource
exhaustion, receipt replay, metric gaming, MCP contract drift, Unicode
ambiguity, public participation abuse, and a tightly bounded no-egress decoy.

Traditional abuse remains covered by the stable parent lab and its
`traditional-nine` corpus. The future suite runs that suite as a regression;
it does not modify it.

## Local commands

Run from the repository root with Python 3.11 or newer:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -I -B \
  kingdom/practices/karma-defense-lab/future/future_karma.py check

PYTHONDONTWRITEBYTECODE=1 python3 -I -B \
  kingdom/practices/karma-defense-lab/future/future_karma.py digest

PYTHONDONTWRITEBYTECODE=1 python3 -I -B \
  kingdom/practices/karma-defense-lab/future/test_future_karma.py -v
```

`plan` reads one event from standard input and writes one canonical receipt
to standard output. `verify` reads a wrapper with exact keys `schema`,
`event`, and `receipt` from standard input. There are no caller-selected
file paths.

Pinned catalog traversal opens each directory relative to an already-open
descriptor, rejects symlinks and cross-device transitions, and accepts only a
single-link regular file whose identity remains stable across the read. This is
local evidence for the reviewed catalog path, not a claim about every Darwin
filesystem consumer.

## Trust and retention boundary

The receipt digest proves deterministic self-consistency, not authentic
external provenance. Any cross-boundary release needs an independently pinned
or signed release subject. The engine is stateless, so the caller owns
concurrency, rate limits, deduplication, audience, sequence, expiry, retention,
and deletion. Declaring those owners is not proof they were enforced.

Python code already executing in this module's interpreter is part of the
trusted computing base: it can monkey-patch Python objects or the interpreter
itself. The content revalidation protects the documented API from changed
Bundle data under an unmodified module; it is not an in-process sandbox.

The synthetic mirror is only a sterile local plan: maximum one candidate, zero
egress, no callback, no attacker content, no public output. There is no
hack-back, retaliation, booby trap, identity inference, coercion, or shaming.

## Non-claims

Passing these tests does not establish live efficacy, macOS-wide confinement,
production safety, authentic origin, legal status, deletion, or comprehensive
coverage. The inspected repository surfaces are evidence for a bounded threat
model, not evidence that any person attacked them.

## Public operations room

The mirrorable, scriptless room at `site/operations/mirror-garden/` publishes
the response contract, coverage gaps, and learning discipline without
publishing incident data. It is an explanation and readiness surface only:
live classification, telemetry, incident counters, and automatic action remain
disabled. A green static page is not a claim that no incident occurred.
