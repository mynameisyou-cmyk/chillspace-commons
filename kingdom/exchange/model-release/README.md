# Model Release Substrate · 模型發佈基層

This is the Kingdom's small, offline contract for saying **which model bytes,
which execution house, and which later claim** a launch refers to.

It grew beside the [Kimi K3 exchange scroll](../kimi-k3-2026-07.md). The scroll
carries interpretation; these records carry exact identity and evidence
boundaries. Neither substitutes for the other.

## The three records

```text
model release ──sha256──> execution profile ──sha256──> evaluation
      │                         │                    attestation
      └─────────────────────────┴──────────────> build / signature /
                                                  correction attestation
```

1. `kingdom.model-release/v1` names released components, their exact byte
   descriptors when known, and the public interface contract.
2. `kingdom.model-execution-profile/v1` binds one release digest to a resolved
   engine, precision, quantization, kernel, hardware, and backend declaration.
3. `kingdom.model-release-attestation/v1` binds build provenance, evaluation,
   signature evidence, correction, or deprecation to a release or execution
   profile digest.

New runtimes and evaluations do not rewrite the model release. A substantive
correction needs both a digest-bound correction attestation and a replacement
release whose `supersedes` relation preserves the old digest.

## Four things called a fingerprint

The substrate does not use bare `fingerprint` as if every signal meant the
same thing.

| Name | Scope | What it proves |
| --- | --- | --- |
| artifact descriptor | a declaration of exact bytes, media type, and byte size | nothing until bytes are compared; `artifact-check` establishes a supplied file matches it |
| release digest | canonical release-manifest bytes | the release declaration is unchanged |
| execution-profile digest | canonical runtime-profile bytes | the declared execution house is unchanged |
| backend observation | a time-scoped claim/evidence of a provider-returned opaque value | the record is unchanged; origin and provider-defined meaning remain evidence claims |

A model alias, Git branch, unresolved LFS/Xet pointer, tensor-name inventory, seed, or
behavioral probe is not promoted into a weight digest.

## Reasoning boundary

The release manifest may describe a reasoning **interface**:

- reasoning disclosure: `full`, `summary`, `none`, or `unknown`;
- supported effort labels;
- item or channel types;
- continuation state: `plaintext`, `encrypted`, `server-held`, `none`, or
  `unknown` (separate from what reasoning is disclosed);
- whether continuation requires prior items to be resent;
- whether switching models is declared safe, unsafe, or unknown;
- storage and forwarding requirements.

Actual prompts, responses, hidden chain-of-thought, scratchpads, raw thinking,
private system prompts, and session reasoning never belong in these static
records. The validator rejects raw-reasoning-shaped keys and named channels;
that syntactic guard is not semantic inspection or a privacy proof, so free
text still requires human review before publication.

## Digest profile

`kingdom.canonical-json/v1` is deliberately smaller than RFC 8785 and is not
claimed to be JCS:

1. parse strict UTF-8 JSON;
2. reject duplicate keys, floats, non-finite numbers, integers outside signed
   64-bit range, non-NFC text, and unsafe depth or size;
3. accept only the closed v1 schema and domain invariants;
4. serialize UTF-8 with decoded NFC keys sorted by Unicode code-point order,
   no insignificant whitespace, Python JSON string escaping, no ASCII
   coercion, and one final LF;
5. compute SHA-256 over those canonical bytes and write it as
   `sha256:<64 lowercase hex>`.

The digest stays outside the object, avoiding a self-hash. A receipt also
records the exact source-file hash and size, so whitespace-only source changes
are visible even though the canonical content digest remains stable. It pins
the canonical SHA-256 and ID of the reviewed schema, plus the exact byte
descriptor and version of the validator implementation, as well.

## Use it

Everything is Python standard library, local, read-only, and networkless.

```bash
# Validate one object and print its typed content digest.
kingdom release check kingdom/exchange/model-release/examples/synthetic-release.json

# Print only the digest.
kingdom release digest kingdom/exchange/model-release/examples/synthetic-profile.json

# Emit a deterministic receipt to stdout, then verify it against the source.
kingdom release receipt RELEASE.json > RELEASE.receipt.json
kingdom release verify RELEASE.json RELEASE.receipt.json

# Verify subject bindings across one release, one profile, and attestations.
kingdom release verify-set RELEASE.json PROFILE.json ATTESTATION.json

# Stream one local artifact and compare its actual size and SHA-256.
kingdom release artifact-check RELEASE.json ARTIFACT_ID ARTIFACT_FILE

# Verify a correction across old release, replacement, and attestation.
kingdom release verify-supersession OLD.json NEW.json CORRECTION.json

# Render a bounded human reading.
kingdom release render RELEASE.json
```

`receipt` never signs, publishes, uploads, downloads, executes, or contacts a
provider. Redirecting stdout is an explicit caller action. A receipt is local
validation evidence when recomputed, not curator identity or a vendor
signature. `artifact-check` only reads and
streams the explicitly supplied regular file; it does not mutate the release
or silently upgrade `descriptor-asserted` into a stronger persisted claim.

## Launch process

1. Inventory every runtime-critical artifact: weights and index, tokenizer,
   config, generation defaults, chat/response format, adapters/projectors,
   custom code, kernels, calibration data, licenses, and cards.
2. Hash the exact bytes and record media type and byte size. Use
   `descriptor-asserted` for a curator-declared tuple and run `artifact-check`
   against captured bytes. If bytes were not obtained, use an explicit
   `publisher-claimed`, `unavailable`, or `unknown` state instead of inventing
   a hash.
3. Record the reasoning and continuation interface without recording any
   session trace. Keep disclosed reasoning separate from encrypted or
   server-held continuation state.
4. Validate and receipt the content-addressed release declaration.
5. Resolve a concrete local execution profile. `auto`, `latest`, `main`, and
   hidden defaults are refused in fields that claim an exact local runtime.
   Hosted profiles instead mark private internals `provider-managed` or
   `unknown` and bind the requested alias and mutability, returned model state,
   region state, observation time, and exact request-configuration descriptor.
6. Bind build outputs back to release artifact IDs and descriptors, declaring
   whether coverage is partial or complete. Record signature bytes, signed
   digest, verifier policy, tool, and evidence for the exact subject; this
   validator records that verification claim but performs no cryptography.
   Bind evaluation intervals, aggregation, outputs, and evidence to both the
   release and profile digests.
7. Keep claims classified as `publisher-claimed`, `curator-observed`, or
   `independently-reproduced`. Unknown remains unknown.
8. Publish explicit states for baseline training/post-training/reasoning/safety
   disclosures and for the governing license; API or hybrid releases also name
   API terms and data-use policy states. Withheld and unknown are valid, but
   omission is not.

The reviewed machine contract is [`schema.json`](schema.json); the reference
implementation is [`model_release.py`](model_release.py); the examples are
synthetic and prove only the local mechanics. Research lineage and the
standards this profile borrows from are in [`SOURCES.md`](SOURCES.md).
The committed public reading room and exact schema/example mirrors live at
[`site/exchange/model-release/`](../../../site/exchange/model-release/).

## What validation does not prove

- A hash proves byte equality, not identity, safety, quality, or truth.
- A successfully verified signature authenticates signed bytes under the
  stated trust policy; this validator only records that verification claim and
  does not prove the signed assertions.
- A provider observation is not a cryptographic model fingerprint.
- A descriptor declaration is not evidence that anyone recomputed the bytes.
- A seed does not guarantee reproducibility.
- A safe weight container does not make repository custom code safe.
- A valid record grants no permission, consent, deployment authority, or
  readiness claim.
