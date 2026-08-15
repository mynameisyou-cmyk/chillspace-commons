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

The v1 record commands below use only the Python standard library and are
local, read-only, and networkless.

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

## Curated capsule registry

[`registry.json`](registry.json) names the finite set of curated release
capsules published from this directory. The first entry,
[`capsules/kimi-k3-hf-9f62e4e9/`](capsules/kimi-k3-hf-9f62e4e9/), is a real
KINGDOM-curated, publisher-sourced Kimi K3 release record. It captures selected
official metadata, code, and license bytes. The weight-shard digests remain
`publisher-claimed`: the capsule did not download the weights. Its local
reference and hosted documented profiles are explicit declarations and were
not executed; no model/API call, evaluation, or build was performed.

The second entry,
[`capsules/qwen3-0.6b-hf-c1899de2/`](capsules/qwen3-0.6b-hf-c1899de2/), binds
Qwen3-0.6B at one immutable Hugging Face revision to a curator-observed local
CPU execution. All ten publisher files were downloaded and streamed through
SHA-256 locally. The 1.5 GB weight file and 11.4 MB `tokenizer.json` are not
bundled in this repository; the other eight publisher files and an output-free
execution record are retained.

That bounded witness contains three runs. One thinking attempt reached its
128-token ceiling without a closing think marker or final segment. Two
non-thinking controls produced identical continuation-token and decoded-output
SHA-256 values, and both matched the private expected integer under the last-numeric
rule while failing the stricter exact-output format. No raw prompt, expected
value, decoded output, or generated deliberation is published. This is not a
benchmark, safety test, quality assessment, or broad reasoning claim.

The third entry,
[`capsules/qwen3-0.6b-gh-ubuntu-abad124/`](capsules/qwen3-0.6b-gh-ubuntu-abad124/),
is a signed witness/referrer attached to that same release capsule, not a new
release declaration. It records a second-machine run on a GitHub-managed
Ubuntu x64 runner. The release revision, ten-file snapshot descriptor set, and
snapshot byte total match the local capsule; the public arithmetic fixture is
different from the prior private fixture, so cross-platform output equality is
not claimed. This remains `curator-observed`: the same curator authored and
started the workflow, and the runner is not an independent human, vendor, or
publisher authority.

The first GitHub attempt failed before inference because the namespace probe
read a parent interface view; its failure receipt remains in the capsule. In
the successful run, the thinking variant remained open at its 96-token limit
and produced no final answer. The two non-thinking runs were token-identical,
matched the public expected integer under the last-numeric rule, and failed
strict output formatting. Raw decoded output and generated deliberation are
omitted; their fingerprints are public, and low-entropy result semantics are
inferable from the scoring flags. The omitted bytes are not thereby
reproduced, and hashes are not encryption.

The release capsules' signed `launch-index.json` files and the Ubuntu
witness's signed `witness-index.json` are set-level verification wrappers, not
additional v1 substrate records. A task-key signature makes indexed bytes
cryptographically checkable but does not establish publisher identity, vendor
endorsement, a trusted timestamp, safety, readiness, or launch authority. The
Ubuntu capsule additionally retains the workflow-produced evidence tar and a
GitHub/Sigstore attestation bundle. Offline `gh attestation verify`, constrained
to the repository, signer workflow, source commit and branch, predicate type,
and GitHub-hosted runner, authenticates the attested tar as a workflow product;
it does not prove the evaluation semantics or which model-file inode the
loader consumed.

Offline registry verification checks every registered signed public file graph
and, for the Ubuntu witness, runs that bounded `gh` verification using the
committed bundle and trusted root while forcing HTTP proxy routes to
unreachable loopback. It does not re-stream the publisher snapshot or
reexecute inference. Registry verification requires local OpenSSL and, while a
GitHub witness is registered, GitHub CLI 2.86.0 or newer. That local `gh`
executable is part of the verifier's trusted computing base: the registry
validator checks its reported version and verification result, but does not
authenticate or digest-pin the executable itself.

Validate the registry, its receipts and signatures, its finite file set, and
the exact public mirrors with:

```bash
python3 kingdom/exchange/model-release/validate_registry.py \
  --source kingdom/exchange/model-release \
  --public site/exchange/model-release
```

The public registry and capsule tree at
[`site/exchange/model-release/`](../../../site/exchange/model-release/) must
remain byte-for-byte mirrors of their source counterparts.

## Launch process

1. Inventory every runtime-critical artifact: weights and index, tokenizer,
   config, generation defaults, chat/response format, adapters/projectors,
   custom code, kernels, calibration data, licenses, and cards.
2. Hash the exact bytes and record media type and byte size. Use
   `descriptor-asserted` for a curator-declared tuple and run `artifact-check`
   against captured bytes. If bytes were not obtained, use an explicit
   `publisher-claimed`, `unavailable`, or `unknown` state instead of inventing
   a hash. A later curator-observed byte-streaming or execution attestation can
   add evidence without rewriting the original release declaration.
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
The committed public reading room and exact schema, example, registry, and
capsule mirrors live at
[`site/exchange/model-release/`](../../../site/exchange/model-release/).

## What validation does not prove

- A hash proves byte equality, not identity, safety, quality, or truth.
- A successfully verified signature authenticates signed bytes under the
  stated trust policy; this validator only records that verification claim and
  does not prove the signed assertions.
- A provider observation is not a cryptographic model fingerprint.
- A descriptor declaration is not evidence that anyone recomputed the bytes.
- An offline registry check does not rerun inference or independently prove
  which local artifact path a prior loader consumed.
- A seed does not guarantee reproducibility.
- A safe weight container does not make repository custom code safe.
- A valid record grants no permission, consent, deployment authority, or
  readiness claim.
