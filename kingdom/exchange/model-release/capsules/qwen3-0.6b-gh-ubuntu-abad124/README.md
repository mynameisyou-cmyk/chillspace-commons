# Qwen3-0.6B · GitHub-hosted Ubuntu x64 witness

This is a signed **referrer/witness capsule** for the already sealed
`qwen3-0.6b-hf-c1899de2` release. It does not replace, reopen, or mutate that
release. The witness index anchors its canonical release digest
`sha256:46de8033…3b43fc4` and signed launch-index digest
`sha256:efa50b06…6402bc1`.

## What happened

A fresh GitHub-hosted `ubuntu-24.04` x64 runner downloaded and hashed the same
ten-file `Qwen/Qwen3-0.6B` snapshot at immutable revision
`c1899de289a04d12100db370d81485cdf75e47ca`. One Python process verified the
1,519,209,243-byte snapshot, entered a network namespace whose active interface
list contained only loopback, confirmed that an outbound TCP probe failed,
loaded the tokenizer and FP32-widened BF16 weights locally with
`trust_remote_code=False`, and performed three sequential greedy generations.

The public fixture asks for 37 multiplied by 43 and publishes the expected
answer. The thinking run reached its 96-token ceiling while the reasoning
interface remained open, so it produced no final answer segment. The two
non-thinking runs ended normally with identical continuation-token and decoded-
output digests. Both had the correct last numeric value, but each contained more
than one number and failed the strict exact-output and sole-numeric-answer rules.

One earlier workflow attempt is retained as a bounded failure receipt. Its
snapshot download/hash gate passed, but its interface-observation probe failed
before inference; it created neither an evidence tar nor an artifact attestation.
The one allowed retry changed only that observation method and succeeded.

## Provenance boundary

The successful workflow produced a deterministic 71,680-byte tar with the 11
sanitized evidence files mirrored under `evidence/execution/`. A separate
GitHub Actions job attested that exact tar. `gh` 2.86.0 then verified the local
bundle with the pinned trusted-root snapshot while all proxy routes were forced
to unreachable loopback endpoints, enforcing the repository, signer workflow,
source commit, source ref, and SLSA provenance predicate type.

That verification authenticates the workflow-produced tar under the supplied
trust snapshot. It does **not** independently observe model semantics, make
workflow-controlled claims true, prove which inode the loader consumed, or make
the trust snapshot timeless. The runner is managed by GitHub and the mission was
curated by the same KINGDOM operator as the first capsule; this is not an
independent human, publisher, vendor, or laboratory reproduction.

Offline verification also trusts the locally resolved `gh` executable at
version 2.86.0 or newer. The validator constrains its version, inputs, policy,
and parsed output, but does not authenticate or digest-pin that executable.

## Privacy and scope

The prompt and expected value are public. Decoded-output and generated-
deliberation bytes, model weights, tokenizer bytes, raw environment, hostname,
credentials, and private paths are absent. Output/token fingerprints and public
scoring flags can make low-entropy content guessable; SHA-256 is not encryption.

The frozen-v1 profile sentence that validation captures no raw prompt describes
the validator itself not collecting a prompt during validation. It does not say
that every indexed fixture omits prompts: this capsule deliberately includes the
raw public synthetic probe under `evidence/execution/public-probe.json`.

This public fixture differs from the first capsule's private synthetic probe.
Accordingly, the two runs do not establish cross-machine exact-output
equivalence. One arithmetic fixture is not a benchmark, safety evaluation,
quality ranking, or broad reasoning claim.

## Read and verify the graph

- [`witness-index.json`](witness-index.json) — signed finite graph, base-release
  anchor, tar-member map, and exact GitHub provenance policy
- [`ubuntu-x64-profile.json`](ubuntu-x64-profile.json) — frozen-v1 runtime,
  hardware, engine, determinism, privacy, and evidence declaration
- [`evaluation-attestation.json`](evaluation-attestation.json) — frozen-v1
  curator-observed three-run evaluation, including misses
- [`evidence/execution/run-summary.json`](evidence/execution/run-summary.json) —
  output-free aggregate
- [`evidence/harness/benchmark-manifest.json`](evidence/harness/benchmark-manifest.json)
  and [`scoring-policy.json`](evidence/harness/scoring-policy.json) — public
  fixture and narrow rules
- [`evidence/provenance/github-attestation-bundle.jsonl`](evidence/provenance/github-attestation-bundle.jsonl)
  and [`offline-verification-receipt.json`](evidence/provenance/offline-verification-receipt.json)
  — GitHub/Sigstore bundle and bounded offline check
- [`evidence/provenance/prior-attempt-failure-receipt.json`](evidence/provenance/prior-attempt-failure-receipt.json)
  — the failed pre-inference predecessor

One fresh, identity-free Ed25519 task key signs the raw SHA-256 digest of
`witness-index.json` under the domain `KINGDOM MODEL RELEASE WITNESS INDEX v1`.
Successful verification proves possession of that task key for those exact
bytes only; it grants no human, Qwen, Alibaba, Hugging Face, GitHub, safety,
deployment, endorsement, or independent-reproducer identity or authority.
