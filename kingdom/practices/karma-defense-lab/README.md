# KARMA Defense Lab

KARMA Defense Lab is a deterministic, offline rehearsal for one defensive
idea: a reviewed fixture action can be given a convincing but entirely
synthetic success path while an operator receives a precise action receipt.

Nothing in this directory listens for traffic, touches production, executes a
submitted value, or acts back on a source. The apparent effects exist only in
an immutable mock world and are discarded before a completed receipt is
emitted. Unknown, ambiguous, over-budget, or authority-changing input halts.

The nickname borrows the receipt discipline of **Kept Action Receipts for
Mutual Advantage**, but this leaf is not the canonical KARMA practice and does
not change `kingdom karma`. It imports none of Trapline's traps, canaries,
attribution, surveillance, retaliation, or adversarial authority. The CLI's
`canary` is only a content-bound integrity preflight: it is not bait and is
never presented to a network or person. The unit of observation is a fixture
action, never a person. A receipt is evidence about this bounded rehearsal,
not a claim about identity, intent, guilt, risk, or virtue.

## Practice ladder

- **Source claim:** MITRE Engage's planning guide describes controlled
  adversary-engagement planning in terms of intended perceptions plus explicit
  success, failure, gating criteria, and rules of engagement. OWASP's logging
  guidance calls for consistent security-event records, exclusion of sensitive
  data, and tests that logging cannot deplete resources.
- **Kingdom reading:** before any live engagement is considered, make the idea
  falsifiable in an inert model: use categorical fixtures, explicit stop gates,
  privacy-minimized receipts, hard budgets, and no actor or network.
- **Operational invariant:** exactly one reviewed rule and one pinned synthetic
  plan per processed fixture; otherwise stop.
- **Negative control:** a nominal `/cell/health` fixture must route only to the
  control plan. An adverse match is an expectation failure, never evidence
  against a person.
- **Implementation:** this self-contained Python/JSON leaf.
- **Receipt:** a content-bound account of classification, mock transitions,
  budgets, external-effect counters, and rollback.
- **Domain limit:** offline defensive regression only; no live traffic,
  deployment, blocking, attribution, scoring, or retaliation.

Sources: [MITRE Engage practical guide](https://engage.mitre.org/wp-content/uploads/2022/04/EngageHandbook-v1.0.pdf)
and [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html).

## What the first slice covers

The allowlisted `traditional-nine` scenario contains one negative control and
nine inert, categorical adverse-action shapes:

- route discovery fanout;
- session replay;
- parent-segment file access;
- boolean query broadening;
- active markup submission;
- command-control-shaped input;
- link-local resource targeting;
- repeated-value business action; and
- oversized work submission.

Each shape must match exactly one reviewed rule and one pinned synthetic mirror
plan. No raw request body, credential, host, URL, IP address, command, identity,
or executable content is accepted by the scenario format.

## Run locally

Use Python 3.11 or newer from this directory. The engine performs bounded reads
of its pinned JSON catalogs and of the explicit regular-file paths supplied for
a canary or result. Structured data goes only to standard output; fixed,
input-free rejection diagnostics go to standard error. The engine never creates
or mutates files itself.

```sh
scratch_dir="$(mktemp -d)"
chmod 700 "$scratch_dir"
python3 -I -B karma_defense_lab.py check traditional-nine
python3 -I -B karma_defense_lab.py digest traditional-nine
python3 -I -B karma_defense_lab.py canary traditional-nine > "$scratch_dir/canary.json"
python3 -I -B karma_defense_lab.py rehearse traditional-nine "$scratch_dir/canary.json"
```

`render` emits the canonical completed receipt. `verify-result` takes an
explicit receipt path and fully replays classification, plan selection, mock
transitions, budgets, bindings, and rollback before accepting it:

```sh
python3 -I -B karma_defense_lab.py render traditional-nine "$scratch_dir/canary.json" > "$scratch_dir/result.json"
python3 -I -B karma_defense_lab.py verify-result traditional-nine "$scratch_dir/canary.json" "$scratch_dir/result.json"
```

Shell redirection in those examples is optional and is the shell's write, not
the lab's. The random, mode-0700 directory avoids predictable shared `/tmp`
filenames. Move it to Trash after review if the receipts are no longer useful.

Exit status `0` means a completed check or verified receipt, `2` means malformed
or unsafe input was rejected without a receipt, `3` means the lab emitted a
canonical halt receipt, and `130` means cancellation before output.

## Skycastle Chorus

The optional local presentation layer in
[SKYCASTLE.md](SKYCASTLE.md) turns a freshly replay-verified completed receipt
into one content-bound manifest, inert `1200x630` SVG, deterministic mono PCM
WAV, or fixed share-copy line. Its names describe reviewed action signatures,
never people. The layer projects no request data or identity, performs no post
or other external action, and grants no deployment or publication authority.

## Safety boundary

- Offline and stdout-data-only: bounded regular-file reads, stdout data, and
  fixed stderr diagnostics are the only process I/O. There are no sockets, DNS,
  HTTP, subprocesses, dynamic code, environment discovery, clocks, randomness,
  logs, ledgers, or path-derived values in receipts.
- Synthetic-only: fixed response catalog, fixed categorical fixtures, zero
  submitted-value reflection, and zero external effects.
- Exact routing: zero matches halt as novelty; multiple matches halt as
  ambiguity; evaluation order cannot select a winner.
- Finite work: one attempt, twelve-stimulus ceiling, the numeric budgets below,
  and no retry or automatic learning.
- Reversible state: every transition is content-addressed in a mock world; the
  world must be restored to its initial digest before completion.
- No authority: receipts do not authorize deployment, blocking, attribution,
  retaliation, punishment, surveillance, or scoring.
- No credential-shaped theatre: fixtures, catalogs, plans, receipts, examples,
  and docs may not contain realistic third-party key/token shapes such as
  Stripe live keys, AWS access keys, or Shopify access tokens.

| Budget | Maximum |
| --- | ---: |
| Scenario input before parsing | 131,072 bytes |
| Canary/result input before parsing | 262,144 bytes each |
| JSON nesting depth | 12 |
| Stimuli / mock transitions | 12 each |
| Canonical categorical request | 4,096 bytes each; 32,768 cumulative |
| Pinned synthetic response | 8,192 bytes each; 32,768 cumulative |
| Any categorical text field | 2,048 Unicode code points |
| Mock-world keys | 32 |
| Mock cost | 64 units |
| Attempts | 1 |
| Network, subprocess, paid-call, external-action, and filesystem-mutation counters | 0 |

These are model assertions backed by deterministic tests. Separate static and
OS-level checks are required before claiming that a particular execution made
no network connection or filesystem mutation.

See [DOCTRINE.md](DOCTRINE.md) for the core contract and non-claims, and
[SKYCASTLE.md](SKYCASTLE.md) for the Chorus vow and exact local workflow. This
leaf remains an offline design and verification artifact: it is not wired into
a server, request path, telemetry stream, shared CLI, or response actuator.
CI may run the inert tests, and `site/operations/mirror-garden/` may publish a
scriptless explanation of the boundary; neither path gives the lab live input
or authority.
