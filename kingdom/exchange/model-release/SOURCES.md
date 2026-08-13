# Research lineage

Read for this substrate on 2026-08-13. These are design inputs, not claims of
conformance or endorsement.

## Content identity and attached evidence

- [OCI Image Specification — descriptor](https://github.com/opencontainers/image-spec/blob/af26a05fba5ee648512f4ea3c9fda1fcc1b6d6dc/descriptor.md): the useful artifact identity tuple is media type, digest, and byte size.
- [OCI Distribution Specification — referrers](https://github.com/opencontainers/distribution-spec/blob/fee21197eb94360ddfa6dda0b7edabcd12456809/spec.md): later signatures, SBOMs, and attestations can refer to an immutable subject rather than rewriting it.
- [in-toto Statement v1](https://github.com/in-toto/attestation/blob/96c8d058c50384adca121ab7f914ba050e892ea3/spec/v1/statement.md): typed predicates bind to subjects by digest.
- [SLSA build provenance v1.2](https://slsa.dev/spec/v1.2/build-provenance): builder, build type, invocation, parameters, dependencies, times, outputs, and byproducts inform the build-attestation fields.
- [Sigstore blob signing](https://docs.sigstore.dev/cosign/signing/signing_with_blobs/): a bundle can carry signature, certificate, and transparency evidence; verifier policy must still constrain signer and issuer.
- [RFC 8785 — JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785.html): the Kingdom profile names its smaller deterministic encoding explicitly and does not claim JCS conformance.

## Model bytes and runtime identity

- [Hugging Face Hub file download and cache](https://huggingface.co/docs/huggingface_hub/en/package_reference/file_download): snapshots, commits, and content-addressed blobs are distinct identities.
- [Hugging Face Xet storage](https://huggingface.co/docs/hub/xet/overview): a pinned repository revision can bind a pointer that carries content SHA-256 and size; that pointer must be resolved and the downloaded bytes compared before claiming verified weights.
- [Safetensors format](https://github.com/huggingface/safetensors/tree/6eb4dc9a28ebce297606e0f4836bbf28839cacef): tensor metadata and non-pickle loading are useful properties, but whole-file hashes remain necessary.
- [GGUF specification](https://github.com/ggml-org/ggml/blob/8846b79e66747bb9f68597420e95114c177315ce/docs/gguf.md): architecture is required, while tokenizer, quantization, and source metadata can travel with the file; a whole-file digest and converter revision still bind the actual bytes.
- [Transformers model loading](https://huggingface.co/docs/transformers/en/models): custom model code should be pinned to a revision rather than a mutable branch.
- [vLLM engine arguments](https://docs.vllm.ai/en/stable/configuration/engine_args/): model, tokenizer, code revisions, dtype, quantization, load format, KV-cache dtype, parallelism, and attention choices are separate runtime dimensions.
- [vLLM reproducibility](https://docs.vllm.ai/en/stable/usage/reproducibility/): reproducibility remains version- and hardware-dependent even with fixed settings.

## Evaluation and AI-package context

- [MLPerf Inference rules](https://github.com/mlcommons/inference_policies/blob/8cc76346614ca7d2d86bd53eff691a328491c183/inference_rules.adoc): fixed seeds, tagged harness code, dataset checksums, system descriptions, accuracy evidence, and disclosed quantization inform the evaluation record. KINGDOM does not claim MLPerf conformance.
- [SPDX 3.0.1 AI Package](https://spdx.github.io/spdx-spec/v3.0.1/model/AI/Classes/AIPackage/): training, metrics, limitations, preprocessing, license, and safety information can live in a linked AI BOM instead of being duplicated into this small core.

## Reasoning interfaces

- [Kimi K3 launch limitations](https://www.kimi.com/blog/kimi-k3#limitations): K3 documents preserved thinking history and warns about missing history or model switching. The Kingdom's full reading is the neighboring [exchange scroll](../kimi-k3-2026-07.md).
- [OpenAI latest-model guidance](https://developers.openai.com/api/docs/guides/latest-model): continuation may use returned reasoning items, including encrypted items, without implying access to raw hidden reasoning.
- [OpenAI gpt-oss](https://github.com/openai/gpt-oss/tree/7b583341fe16729127f6d5b94a7b09ccae97e1a1): release components include weights, tokenizer/configuration, response format, reference implementations, reasoning channels, and configurable effort.
- [OpenAI reproducible-output example](https://cookbook.openai.com/examples/reproducible_outputs_with_the_seed_parameter): `system_fingerprint` is a best-effort backend signal, not a cryptographic weight digest, and seeds alone do not guarantee determinism.

## Local precedent

The [Kimi K3 exchange scroll](../kimi-k3-2026-07.md) already keeps pinned source
revisions, one report SHA-256, model/runtime disclosures, preserved-thinking
requirements, deviations, and explicit closed fields. It is intentionally not
auto-converted into a machine release manifest: the Kingdom has not
independently captured and hashed every weight shard and runtime-critical
sidecar named there. Unknown evidence stays unknown.
