# Qwen3 Ubuntu witness runner

This temporary research harness executes one public synthetic Qwen3-0.6B
fixture on a fresh GitHub-hosted Ubuntu 24.04 x64 VM. It downloads only the ten
files at Hugging Face revision
`c1899de289a04d12100db370d81485cdf75e47ca`, checks their exact sizes and
SHA-256 values, then runs inference inside a new Linux network namespace with
no external interface.

The evidence bundle contains the public fixture, exact harness, digest-pinned
wheel lock, runtime and snapshot manifests, and raw-output-free result
descriptors. It does not contain model weights, tokenizer bytes, raw decoded
output, raw generated deliberation, credentials, hostnames, or private paths.
Because the expected answer and scoring flags are public, the decoded result
can be inferred when a match is recorded; its digest is a fingerprint, not
encryption. The same non-encryption boundary applies to the published
deliberation-token digest and count.

The workflow emits one deterministic tar and asks GitHub's artifact attestation
service to bind its digest to the workflow identity. That provenance identifies
the workflow boundary; it does not prove the model semantics, the loaded inode,
quality, safety, publisher endorsement, or cross-platform reproducibility.
