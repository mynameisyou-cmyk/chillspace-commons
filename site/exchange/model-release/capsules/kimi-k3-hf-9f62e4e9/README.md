# Kimi K3 · publisher-sourced release capsule

This is a real, content-addressed **KINGDOM-curated record of publisher-sourced
claims and captured bytes** for Moonshot AI's Kimi K3. It is not an official
Moonshot artifact and carries no vendor endorsement.

## What is here

- `release.json` pins the Hugging Face revision
  `9f62e4e9fffbd0a83ddd60e1c209d828994b3569` and distinguishes 15 captured
  model-card/config/tokenizer/code/license files from the 96 weight shards
  whose hashes remain publisher-claimed.
- `local-reference-profile.json` records one exact vLLM recipe/container
  declaration for 8× NVIDIA B300. KINGDOM did not provision it, download the
  weights, or execute it. The container is pinned by OCI manifest; its own
  image labels disclose no vLLM source commit.
- `hosted-documented-profile.json` records Moonshot's mutable `kimi-k3` API
  alias and a privacy-scrubbed, not-sent request configuration. No paid call
  was made and no returned model, region, fingerprint, prompt, or response was
  observed.
- `release-signature-attestation.json` records a verified detached Ed25519
  signature over the release's canonical digest. `launch-index.json` binds the
  complete capsule file set, records, receipts, and profiles and has its own
  detached signature.
- `evidence/` preserves exact publisher/runtime documents as read-only bytes;
  it is never executed or fetched automatically by the registry verifier.

The captured Hugging Face inventory covers 118 repository files totalling
1,560,998,984,390 bytes. Its 96 published weight shards total
1,560,936,091,448 bytes. Those large shards were not downloaded; their LFS
SHA-256 claims and sizes are preserved in `evidence/publisher/artifact-inventory.json`.
The raw Hugging Face API response is not bundled because it also contained
unrelated dynamic Space and account metadata; its retrieval-time raw hash and
size remain as `source_descriptor` in that minimized inventory. Because those
historical source bytes were deliberately not retained, the offline verifier
does not recompute the 118 rows from the API response; it checks the
curator-signed rows and recomputes their aggregate summary.

## Signature boundary

The public key is a task-specific, identity-free Ed25519 key. Successful
verification proves possession of the matching private key for the exact
domain-separated bytes. It does **not** prove human identity, Moonshot
authorship, a trusted timestamp, private-key destruction, model safety,
behavior, readiness, or launch/deployment authority.

No private key, live credential, user session, or KINGDOM prompt, response, or
reasoning trace is in this capsule. Captured publisher documents retain their
own public illustrative prompts, outputs, reasoning examples, and contact
details as source material; they are not observations from a KINGDOM call.

## Verify locally

From the repository root:

```bash
python3 kingdom/exchange/model-release/validate_registry.py \
  --source kingdom/exchange/model-release \
  --public site/exchange/model-release
```

The verifier is offline. It recomputes the finite raw-file inventory, v1
record receipts, release/profile bindings, the release signature, the launch
index signature, and source-to-public mirror equality. It downloads and runs
nothing from this capsule. Signature verification requires OpenSSL 3.0 or
newer.

No evaluation, build provenance, inference result, or backend observation is
included because none was independently performed.
