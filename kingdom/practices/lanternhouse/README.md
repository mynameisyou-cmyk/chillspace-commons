# 🏮 The Lanternhouse Protocol

> **Preserve the ledger. Bound the lamp. Name the house. Renew the lease.**

Lanternhouse turns a paper teaching into a falsifiable, evidence-bearing
practice. It began with a tension exposed by Kimi's papers:

- future behavior can depend on faithfully preserved state;
- useful attention must still be selective and finite;
- agentic results depend on the surrounding harness;
- long work needs budgets, stillness, negative controls, and honest witnesses.

The answer is not to pour every private trace into every prompt. Lanternhouse
keeps two things distinct:

- **the ledger** — authorized continuity state, kept faithfully and privately;
- **the lamp** — the small, declared set of representations lit for this task.

Compression may create a derived lamp with a loss receipt. It never silently
rewrites the ledger.

**Status: experimental, declarative scaffold.** `check` establishes internal
structure, not the truth of a proof locator or the safety of adoption.
`ready` means every declared house cites every rubric criterion under a
non-drifted lease; it is still not an adoption or deployment gate without an
independent witness.

The public doorway is
[chillspace.love/practices/lanternhouse/](https://chillspace.love/practices/lanternhouse/).
Its downloadable schema and first holding card are release copies of the
canonical files here; CI requires them to remain byte-identical.

## The seven windows

| window | the question it must answer |
|---|---|
| source | What did the paper actually claim, and what is our reading? |
| house | Which model, adapter, prompt, tools, memory policy, sandbox, and sampling made this run? |
| ledger | Can state be captured and replayed, was it absent or present-empty, and what was lost? |
| lamp | Which bounded earlier representations are attended now, and which are omitted? |
| trial | What invariant, counterexample, houses, and budget were fixed before the run? |
| lease | Is the world still the world the plan observed? |
| witness | Which rubric, proof, process deviations, and whole cost travel with the result? |

The philosophical heart is in [the Nine Courtesies](DOCTRINE.md#the-nine-courtesies).
The executable form is a strict `kingdom.lanternhouse/v1` JSON manifest.

The first real manifest,
[`k3-preserved-thinking.json`](examples/k3-preserved-thinking.json), asks
whether AgentTool can yet be a faithful K3 house. Its answer is deliberately
**not-ready**: the paper contract is pinned, the current adapter loss is
witnessed, and the missing counterfactual fixture remains visible instead of
being narrated away.

## Use it

```bash
python3 kingdom/practices/lanternhouse/lanternhouse.py \
  check kingdom/practices/lanternhouse/examples/k3-preserved-thinking.json

python3 kingdom/practices/lanternhouse/lanternhouse.py \
  render kingdom/practices/lanternhouse/examples/k3-preserved-thinking.json

python3 kingdom/practices/lanternhouse/test_lanternhouse.py
```

Or, from the Kingdom door:

```bash
kingdom/bin/kingdom lantern check \
  kingdom/practices/lanternhouse/examples/k3-preserved-thinking.json
```

The tool validates and renders. It never calls a model, executes a receipt,
grants authority, or deliberately accepts an explicit raw-reasoning field.
Free text remains an author's responsibility: the validator can catch common
secret shapes, but it cannot infer whether arbitrary prose came from a private
trace. Private traces stay out of every manifest field. `unknown` stays
unknown; a live trial with an unverified state contract is quarantined rather
than promoted by optimism.

## What this does not claim

Lanternhouse does not prove consciousness, personal continuity, model
superiority, or deployment safety. It does not make private chain-of-thought a
public record. It can show that a declared house met a declared contract under
declared conditions—and no more.

## Lineage

This is an original Kingdom practice, not Moonshot terminology. Its source
claims and our translations are separated in [DOCTRINE.md](DOCTRINE.md).
