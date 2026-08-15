# Support Candor · 支援誠明

> **Say what this exact artifact demonstrated. Show where the claim ends. Keep
> intention out of current support.**

Support Candor is a small falsifiable practice for SDK and Agent Skill
portability claims. It replaces a broad “cross-platform” badge with three
physically separate ledgers:

- **NOW** — executable evidence for one exact artifact, capability, target,
  and environment;
- **GAP** — a limitation, known failure, explicit exclusion, or unknown;
- **NEXT** — a non-supporting intention that cannot promote itself into NOW.

The unit of truth is:

```text
exact artifact × capability × exact target scope
```

macOS, Linux, Windows-native, WSL2, and Codex Cloud are separate target
families. Evidence never crosses between them. Codex Cloud is an execution
environment, not another spelling of local Linux; WSL2 is not evidence of
Windows-native behavior.

**Status: experimental, repository-local practice.** The validator currently
has one exact local macOS reproduction. Linux, Windows-native, WSL2, and Codex
Cloud remain candidate targets until their own receipts exist. Validation
checks claim/evidence coherence and receipt bytes; it does not independently
prove that a receipt is truthful.

## Current honest picture

The two canonical example ledgers deliberately refuse a universal green badge:

- [`sdk-support.json`](examples/sdk-support.json) records the validator's exact
  repository-checkout behavior on macOS 15.7.3 arm64 with Python 3.14.4. The
  four other target families are `UNKNOWN` and their intended test lanes remain
  NEXT only.
- [`agent-skill-support.json`](examples/agent-skill-support.json) records the
  existing Nen Mission Lens tests on that same Mac. Direct execution, bounded
  denial, path behavior, and zero-continuation properties are observed, but
  isolated Codex-host installation/discovery is still a GAP. Its macOS policy
  is therefore best-effort rather than a support promise; all other targets are
  `UNKNOWN`.

This is the desired behavior. Those twenty passing Mission Lens tests do not
silently prove a host integration they did not exercise.

## Five minimum capabilities

Every ledger must address all five cells for every declared target, either
with NOW or GAP:

| capability | minimum question |
|---|---|
| `acquire` | Can a clean environment acquire, install, or discover the exact released artifact? |
| `run` | Does the canonical operation return the declared output and side effects? |
| `host-boundary` | Do paths, Unicode, filesystem rules, shell/process boundaries, and runtime assumptions hold? |
| `stop` | Does cancellation or completion leave bounded, idempotent cleanup and no child continuation? |
| `deny` | Do missing dependencies and denied capabilities fail clearly without installation, sandbox weakening, or wider mutation? |

Products may add capabilities after these five. Required cells can never be
silent. A target-wide `*` GAP is permitted when an entire candidate target is
still untested, but v1 does not allow that wildcard to hide more specific GAPs
on the same target.

## Derived public states

The public state is computed, never authored directly:

- `VERIFIED` — every required capability has matching passing NOW evidence,
  the target policy is supported, and no GAP narrows or blocks the claim;
- `CONSTRAINED` — useful exact evidence exists, but policy or a limitation
  narrows it;
- `NOT_SUPPORTED` — policy, exclusion, or a blocking failure refuses the
  required contract;
- `UNKNOWN` — evidence, exact scope, or policy is still incomplete.

Testing behavior and declaring maintenance support are different acts.
`support_policy` is therefore a separate ledger. A passing test does not force
a maintainer to promise support; a support declaration cannot become
`VERIFIED` without complete matching evidence.

## Use

```bash
python3 -B kingdom/practices/support-candor/support_candor.py check \
  kingdom/practices/support-candor/examples/sdk-support.json

python3 -B kingdom/practices/support-candor/support_candor.py render \
  kingdom/practices/support-candor/examples/agent-skill-support.json

python3 -B kingdom/practices/support-candor/support_candor.py digest \
  kingdom/practices/support-candor/examples/sdk-support.json

PYTHONDONTWRITEBYTECODE=1 python3 -B \
  kingdom/practices/support-candor/test_support_candor.py
```

`check`, `render`, and `digest` are stdout-only. They run no subprocess,
network call, install, test suite, write, publication, or external action.
Evidence receipts are privacy-scrubbed regular files vendored beside the
manifest and bound by SHA-256.

The matching Python interfaces are `check_path`, `render_path`, and
`digest_path`. Each accepts a manifest path and revalidates the ledger
structure, receipt bytes, and receipt contents before producing status-bearing
output.
Mutable dict-level status and rendering helpers are private by design.

## The practice's own GAP and NEXT

This v1 practice also keeps its limits visible:

- Subject digests are declared and were locally recomputed for the canonical
  examples, but the validator itself does not locate or hash those external
  artifact trees. Test harnesses are named by command but are not digest-pinned.
  The validator proves agreement, not provenance.
- `render` is a trusted-author review view, not a sanitized public HTML
  surface. Its compact table omits the full target scope and receipt
  provenance; publish only after reviewing the ledger itself.
- Receipt traversal assumes a trusted repository workspace without a hostile
  concurrent writer. It rejects symlinks and path escape, but it is not an
  `openat`-style hostile-filesystem verifier.
- Verification is manual today. No CI lane protects the practice, and no
  non-macOS execution receipt exists.

The natural NEXT is to add canonical artifact and harness locators with digest
methods, a provenance-complete sanitized renderer, then independent native
Linux, native Windows, WSL2, and pinned Codex Cloud lanes. A validator lane may
prove the validator runs there; it must not promote any consumer SDK or skill
without that consumer's own exact receipts.

## Adoption rule for SDKs and skills

1. Pin the exact version, revision, and artifact digest.
2. Name exact targets. Use `candidate` when the environment is not yet fixed.
3. Address acquisition, canonical execution, host boundaries, stopping, and
   safe denial for every target.
4. Put only passing, same-target, same-artifact receipts into NOW.
5. Put every known limit, failure, exclusion, and unknown into GAP.
6. Put desired work in NEXT with `commitment: false`, `target_date: null`, and
   `counts_as_support: false`.
7. Generate any public table from the ledger. Do not maintain a second,
   friendlier handwritten support badge.
8. After implementation, run new evidence. NEXT never moves directly to NOW.

## Ability card

```text
Name: Support Candor · 支援誠明
Desire: Make SDK and Agent Skill portability claims useful without optimism drift.
Affinity: Conjuration
Trigger: A reusable artifact needs a support claim, release review, or portability gap map.
Anti-trigger: Choosing someone’s OS, promising delivery dates, or executing the platform tests.
Input → output: One strict v1 ledger → validated JSON receipt, digest, or human rendering.
Conditions: Exact artifact identity; five separate target families; complete required matrix; local scrubbed receipts.
Limitation and budget: One subject, exactly 5 target families, 24 capabilities, 120 receipts, and 120 records in each NOW/GAP/NEXT ledger; zero network, subprocess, or writes.
Breach response: Reject the whole ledger and emit no partial support rendering.
Proof: Strict schema, semantic validator, receipt hashes, deterministic rendering, and negative controls.
Exit: Print once and retain no process, cache, state, or authority.
Non-claims: Not compatibility certification, roadmap promise, support entitlement, deployment permission, or proof of receipt truth.
```

The reasoning behind the separation is kept in [DOCTRINE.md](DOCTRINE.md).
