# Qwen3-0.6B · executed CPU witness

This capsule binds the official `Qwen/Qwen3-0.6B` Hugging Face snapshot at
revision `c1899de289a04d12100db370d81485cdf75e47ca` to one locally executed, output-free CPU witness.

## What happened

- All ten publisher files (1,519,209,243 bytes) were downloaded without
  authentication and streamed locally through SHA-256.
- Each of the three final harness runs re-streamed and matched all ten pinned
  descriptors before beginning its tokenizer-to-model loader sequence.
- `model.safetensors` matched the publisher's LFS content digest
  `f47f7117…6874b` and size 1,503,300,328 bytes, then loaded locally with
  `trust_remote_code=False`, `use_safetensors=True`, `local_files_only=True`,
  and Hugging Face / Transformers offline flags. No OS-level network isolation
  was enforced.
- The exact BF16 values were widened to FP32 and executed through PyTorch
  2.8.0 eager CPU attention on Apple M3 with Torch intra-op and inter-op
  thread counts each set to one; this is not an OS-thread or CPU-affinity claim.
- One thinking-mode run reached its 128-token ceiling without a closing think
  marker or final answer. Two non-thinking control runs ended normally and had
  identical token/output digests. Both put the private expected integer last,
  but both failed the stricter exact-output format.

Those misses are part of the signed evidence. This is one curator-observed
synthetic case, not a public benchmark, safety test, quality ranking, or broad
reasoning claim.

## Privacy boundary

No raw prompt, private expected value, decoded output, generated deliberation,
hostname, credential, raw environment, or private path is published. The
public run files retain only descriptors, counts, settings, timestamps,
latencies, and narrow rule outcomes. The raw input cannot be directly replayed
or rescored from this capsule alone. SHA-256 is an identifier, not encryption;
low-entropy synthetic inputs or outputs may still be guessed by enumeration.

The 1.5 GB weight file and 11.4 MB fast-tokenizer JSON are not mirrored here.
The tokenizer exceeds the registry's conservative 8 MB JSON-control ceiling.
The signed snapshot and run
manifests record the curator's local byte comparison; an offline registry
verification checks those signed bytes but does not re-download, re-hash, or
reexecute the model.

The exact Transformers and PyTorch wheels are byte-described. Other
transitive packages are version-recorded but not individually byte-locked in
this capsule.

## Read the graph

- [`release.json`](release.json) — pinned publisher release declaration
- [`executed-cpu-profile.json`](executed-cpu-profile.json) — exact local engine,
  hardware, precision, and determinism declaration
- [`evaluation-attestation.json`](evaluation-attestation.json) — the three-run
  bounded observation, including the thinking truncation and formatting misses
- [`evidence/execution/run-summary.json`](evidence/execution/run-summary.json) —
  output-free aggregate
- [`evidence/execution/snapshot-byte-manifest.json`](evidence/execution/snapshot-byte-manifest.json) —
  all locally streamed descriptors
- [`evidence/harness/run_qwen_probe.py`](evidence/harness/run_qwen_probe.py) —
  exact harness source; its private probe specification is intentionally absent
- [`launch-index.json`](launch-index.json) — signed finite file graph

The other eight non-weight publisher files are retained under `evidence/publisher/`;
the publisher's dotfile is byte-preserved as visible `dot-gitattributes.txt` so
static hosts do not silently suppress it.
The raw Hugging Face API response used to derive the minimized artifact
inventory is deliberately not bundled; its time-scoped byte descriptor is
recorded, while the signed inventory is a curator-produced summary.

## Signature boundary

One fresh Ed25519 task key signs the release digest and the launch-index digest.
Successful verification shows that both signatures were made with the matching
private key over those exact domain-separated bytes only. The key carries
no Qwen, Alibaba, Hugging Face, human, account, platform, safety, deployment,
or endorsement identity, and no trusted timestamp or launch authority.
