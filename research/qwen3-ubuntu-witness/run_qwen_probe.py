#!/usr/bin/env python3
"""Run a public Qwen3 probe and emit output-free second-machine evidence."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import resource
import shutil
import socket
import sys
import time
from datetime import datetime, timezone

for variable, expected in {
    "PYTHONHASHSEED": "0",
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "TOKENIZERS_PARALLELISM": "false",
    "KINGDOM_NETWORK_NAMESPACE": "linux-unshare-no-external-interface-v1",
}.items():
    if os.environ.get(variable) != expected:
        raise RuntimeError(f"{variable} must equal {expected!r}")

import torch
from safetensors import safe_open
from transformers import AutoModelForCausalLM, AutoTokenizer


ROOT = Path(__file__).resolve().parent
SNAPSHOT = Path(os.environ["KINGDOM_SNAPSHOT_DIR"])
EVIDENCE = Path(os.environ["KINGDOM_EVIDENCE_DIR"])
PROBE_PATH = ROOT / "public-probe.json"
WHEEL_LOCK_PATH = ROOT / "wheel-lock.txt"
CHECKSUMS_PATH = ROOT / "snapshot.sha256"
EXPECTED_REVISION = "c1899de289a04d12100db370d81485cdf75e47ca"
CLOSE_THINK_TOKEN_ID = 151668
EXPECTED_SNAPSHOT = (
    (".gitattributes", "text/plain", 1_570, "34448b82c17d60fec9b65b1f093c115ddbaadc04beb1b0140b6bfed2e012a930"),
    ("LICENSE", "text/plain", 11_343, "832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e"),
    ("README.md", "text/markdown", 13_965, "1ab64a26fcb3b461423b89a433a8c858f1bf8d4086f979cbb3ff878d47cf20e9"),
    ("config.json", "application/json", 726, "660db3b73d788119c04535e48cf9be5f55bc3100841a718637ae695b442f27dd"),
    ("generation_config.json", "application/json", 239, "2325da0f15bb848e018c5ae071b7943332e9f871d6b60e2ed22ca97d4cb993d2"),
    ("merges.txt", "text/plain", 1_671_853, "8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5"),
    ("model.safetensors", "application/vnd.safetensors", 1_503_300_328, "f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b"),
    ("tokenizer.json", "application/json", 11_422_654, "aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4"),
    ("tokenizer_config.json", "application/json", 9_732, "d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101"),
    ("vocab.json", "application/json", 2_776_833, "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910"),
)


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def descriptor(path: Path, media_type: str) -> dict[str, object]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
            size += len(block)
    return {"media_type": media_type, "digest": "sha256:" + digest.hexdigest(), "size": size}


def token_descriptor(token_ids: list[int]) -> dict[str, object]:
    raw = canonical_bytes(token_ids)
    return {"digest": sha256_bytes(raw), "count": len(token_ids), "canonical_size": len(raw)}


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def installed_versions() -> dict[str, str]:
    versions = {}
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata["Name"]
        if not name:
            raise RuntimeError("installed distribution has no canonical name")
        normalized = re.sub(r"[-_.]+", "-", name).lower()
        if normalized in versions:
            raise RuntimeError(f"duplicate installed distribution: {normalized}")
        versions[normalized] = distribution.version
    return dict(sorted(versions.items()))


def network_boundary() -> dict[str, object]:
    # /sys/class/net can retain the parent mount's view after unshare --net.
    # if_nameindex asks the current network namespace through the socket API.
    interfaces = sorted(name for _index, name in socket.if_nameindex())
    if interfaces != ["lo"]:
        raise RuntimeError(f"network namespace has unexpected interfaces: {interfaces!r}")
    blocked = False
    try:
        with socket.create_connection(("1.1.1.1", 443), timeout=1):
            pass
    except OSError:
        blocked = True
    if not blocked:
        raise RuntimeError("outbound network probe unexpectedly succeeded")
    return {
        "class": "linux-network-namespace",
        "interfaces": interfaces,
        "external_interface_present": False,
        "outbound_probe_target": "1.1.1.1:443",
        "outbound_probe_blocked": True,
        "enforced_for_model_load_and_generation": True,
    }


def cpu_model() -> str:
    values = []
    for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
        if line.lower().startswith("model name") and ":" in line:
            values.append(line.split(":", 1)[1].strip())
    return values[0] if values else "not-reported"


def memory_bytes() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemTotal:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("MemTotal was not present")


def github_boundary() -> dict[str, object]:
    required = (
        "GITHUB_REPOSITORY",
        "GITHUB_SHA",
        "GITHUB_WORKFLOW_REF",
        "GITHUB_RUN_ID",
        "GITHUB_RUN_ATTEMPT",
        "RUNNER_ARCH",
        "RUNNER_OS",
        "ImageOS",
        "ImageVersion",
    )
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"missing public workflow metadata: {missing!r}")
    return {
        "repository": os.environ["GITHUB_REPOSITORY"],
        "commit": os.environ["GITHUB_SHA"],
        "workflow_ref": os.environ["GITHUB_WORKFLOW_REF"],
        "run_id": os.environ["GITHUB_RUN_ID"],
        "run_attempt": int(os.environ["GITHUB_RUN_ATTEMPT"]),
        "runner_os": os.environ["RUNNER_OS"],
        "runner_arch": os.environ["RUNNER_ARCH"],
        "image_os": os.environ["ImageOS"],
        "image_version": os.environ["ImageVersion"],
    }


def verify_snapshot() -> tuple[list[dict[str, object]], dict[str, object]]:
    actual = sorted(path.name for path in SNAPSHOT.iterdir())
    expected = sorted(row[0] for row in EXPECTED_SNAPSHOT)
    if actual != expected:
        raise RuntimeError("pinned snapshot file set mismatch")
    files = []
    for name, media_type, expected_size, expected_digest in EXPECTED_SNAPSHOT:
        path = SNAPSHOT / name
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"snapshot entry is not a regular file: {name}")
        observed = descriptor(path, media_type)
        if observed["size"] != expected_size or observed["digest"] != "sha256:" + expected_digest:
            raise RuntimeError(f"snapshot descriptor mismatch: {name}")
        files.append({"path": name, "descriptor": observed})
    raw = canonical_bytes(files)
    summary = {
        "revision": EXPECTED_REVISION,
        "file_count": len(files),
        "total_bytes": sum(int(item["descriptor"]["size"]) for item in files),
        "descriptor_set": {"media_type": "application/json", "digest": sha256_bytes(raw), "size": len(raw)},
        "checked_before_tokenizer_and_model_loader_sequence": True,
    }
    return files, summary


def run_variant(
    *,
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    probe: dict[str, object],
    variant: dict[str, object],
    snapshot_summary: dict[str, object],
    runtime: dict[str, object],
) -> dict[str, object]:
    torch.manual_seed(int(variant["seed"]))
    rendered = tokenizer.apply_chat_template(
        probe["messages"],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=variant["enable_thinking"],
    )
    inputs = tokenizer(rendered, return_tensors="pt")
    started_at = timestamp()
    started = time.perf_counter_ns()
    with torch.inference_mode():
        generated = model.generate(
            **inputs,
            do_sample=False,
            max_new_tokens=variant["max_new_tokens"],
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=model.generation_config.eos_token_id,
        )
    finished = time.perf_counter_ns()
    finished_at = timestamp()
    input_ids = inputs["input_ids"][0].tolist()
    continuation_ids = generated[0][len(input_ids):].tolist()
    prompt_close_present = CLOSE_THINK_TOKEN_ID in input_ids
    try:
        close_position = len(continuation_ids) - continuation_ids[::-1].index(CLOSE_THINK_TOKEN_ID)
    except ValueError:
        close_position = None
    if prompt_close_present:
        private_segment = []
        final_segment = continuation_ids
        interface_state = "preclosed-in-prompt"
    elif close_position is None:
        private_segment = continuation_ids
        final_segment = []
        interface_state = "open-at-stop"
    else:
        private_segment = continuation_ids[:close_position]
        final_segment = continuation_ids[close_position:]
        interface_state = "closed-in-continuation"
    decoded_final = tokenizer.decode(final_segment, skip_special_tokens=True).strip()
    expected_final = probe["expected_final"]
    numbers = re.findall(r"(?<!\d)-?\d+(?!\d)", decoded_final)
    eos_ids = model.generation_config.eos_token_id
    if isinstance(eos_ids, int):
        eos_ids = [eos_ids]
    if continuation_ids and continuation_ids[-1] in eos_ids:
        stop_reason = "eos-token"
    elif len(continuation_ids) == variant["max_new_tokens"]:
        stop_reason = "max-new-tokens"
    else:
        stop_reason = "runtime-other"
    return {
        "format": "kingdom.public-input-output-free-model-run/v1",
        "claim_boundary": {
            "class": "github-hosted-workflow-execution-claim",
            "raw_prompt_public": True,
            "raw_expected_value_public": True,
            "decoded_output_bytes_public": False,
            "decoded_output_fingerprint_public": True,
            "decoded_output_semantics_inferable_from_public_scoring": True,
            "generated_deliberation_bytes_public": False,
            "generated_deliberation_fingerprint_public": True,
            "offline_verifier_reexecutes_model": False,
            "offline_verifier_proves_loaded_weight_inode": False,
        },
        "model": {
            "repository": "Qwen/Qwen3-0.6B",
            "revision": EXPECTED_REVISION,
            "snapshot_verification": snapshot_summary,
            "loader_class": type(model).__name__,
            "tokenizer_class": type(tokenizer).__name__,
            "unique_parameter_count": sum(parameter.numel() for parameter in model.parameters()),
            "dtype": "float32 widened exactly from bfloat16 source values",
            "trust_remote_code": False,
        },
        "runtime": runtime,
        "probe": {
            "case_id": probe["case_id"],
            "variant_id": variant["id"],
            "public_spec": descriptor(PROBE_PATH, "application/json"),
            "rendered_template": {"digest": sha256_bytes(rendered.encode("utf-8")), "size": len(rendered.encode("utf-8"))},
            "input_tokens": token_descriptor(input_ids),
            "continuation_tokens": token_descriptor(continuation_ids),
            "private_segment_tokens": token_descriptor(private_segment),
            "prompt_close_think_token_present": prompt_close_present,
            "generated_close_think_token_present": close_position is not None,
            "reasoning_interface_state": interface_state,
            "reasoning_interface_closed": interface_state != "open-at-stop",
            "final_segment_tokens": token_descriptor(final_segment),
            "decoded_final": {"digest": sha256_bytes(decoded_final.encode("utf-8")), "size": len(decoded_final.encode("utf-8"))},
            "stop_reason": stop_reason,
        },
        "sampling": {
            "strategy": "greedy",
            "do_sample": False,
            "max_new_tokens": variant["max_new_tokens"],
            "seed": variant["seed"],
            "enable_thinking": variant["enable_thinking"],
        },
        "observation": {
            "started_at": started_at,
            "finished_at": finished_at,
            "latency_ms": (finished - started) // 1_000_000,
            "max_resident_set_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            "strict_final_exact_match": decoded_final == expected_final,
            "sole_numeric_answer_match": numbers == [expected_final],
            "last_numeric_answer_match": numbers[-1:] == [expected_final],
            "numeric_answer_count": len(numbers),
        },
        "non_claims": [
            "This record is a workflow-generated execution claim; GitHub artifact provenance binds evidence bytes to the workflow but does not independently observe model semantics.",
            "The evidence omits raw decoded-output and generated-deliberation bytes, model weights, and tokenizer bytes.",
            "The public expected value, scoring flags, digest, and size can reveal or make a low-entropy decoded output guessable; hashes are not encryption.",
            "One public synthetic case is not a benchmark, safety evaluation, or general model capability claim.",
        ],
    }


def main() -> int:
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise RuntimeError("this witness requires Linux x86_64")
    if platform.python_version() != "3.12.12":
        raise RuntimeError("this witness requires exact Python 3.12.12")
    EVIDENCE.mkdir(parents=True, exist_ok=False)
    network = network_boundary()
    github = github_boundary()
    probe_raw = PROBE_PATH.read_bytes()
    probe = json.loads(probe_raw)
    if probe.get("format") != "kingdom.public-synthetic-model-probe/v1":
        raise RuntimeError("unexpected public probe format")
    files, snapshot_summary = verify_snapshot()
    write_json(EVIDENCE / "snapshot-byte-manifest.json", {
        "format": "kingdom.snapshot-byte-manifest/v1",
        "repository": "Qwen/Qwen3-0.6B",
        "revision": EXPECTED_REVISION,
        "files": files,
        "summary": snapshot_summary,
    })
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    if torch.get_num_threads() != 1:
        raise RuntimeError("Torch intra-op thread setting did not take effect")
    if torch.get_num_interop_threads() != 1:
        raise RuntimeError("Torch inter-op thread setting did not take effect")
    if not torch.are_deterministic_algorithms_enabled():
        raise RuntimeError("Torch deterministic algorithms setting did not take effect")
    runtime = {
        "python": platform.python_version(),
        "packages": installed_versions(),
        "os": platform.freedesktop_os_release().get("PRETTY_NAME", "Linux"),
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "processor": cpu_model(),
        "logical_cpu_count": os.cpu_count(),
        "memory_bytes": memory_bytes(),
        "device": "cpu",
        "attention": "PyTorch eager",
        "intraop_threads": torch.get_num_threads(),
        "interop_threads": torch.get_num_interop_threads(),
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "python_hash_seed": os.environ["PYTHONHASHSEED"],
        "offline_model_loading_requested": True,
        "network": network,
        "github": github,
    }
    write_json(EVIDENCE / "runtime-manifest.json", {
        "format": "kingdom.github-hosted-model-execution-runtime/v1",
        "runtime": runtime,
        "privacy": {
            "credentials_public": False,
            "hostnames_public": False,
            "private_paths_public": False,
            "raw_environment_public": False,
            "environment_capture": "allowlisted public workflow and runtime fields only",
        },
        "non_claims": [
            "The workflow record does not prove which inode the loader consumed.",
            "GitHub-hosted runner identity is platform provenance, not publisher identity or endorsement.",
            "Every installed Python distribution is recorded; the bootstrap pip installer is inherited from Python 3.12.12 rather than named in wheel-lock.txt.",
            "The 27 inference-library wheels in wheel-lock.txt are URL- and digest-pinned; that does not independently audit publisher wheel contents.",
        ],
    })
    tokenizer = AutoTokenizer.from_pretrained(SNAPSHOT, local_files_only=True, trust_remote_code=False)
    if tokenizer.convert_tokens_to_ids("</think>") != CLOSE_THINK_TOKEN_ID:
        raise RuntimeError("Qwen close-think token ID differs from the pinned interface contract")
    model = AutoModelForCausalLM.from_pretrained(
        SNAPSHOT,
        local_files_only=True,
        trust_remote_code=False,
        use_safetensors=True,
        dtype=torch.float32,
        attn_implementation="eager",
    )
    model.eval()
    with safe_open(SNAPSHOT / "model.safetensors", framework="pt", device="cpu") as handle:
        stored_tensor_count = len(handle.keys())
    results = []
    for variant in probe["variants"]:
        result = run_variant(
            model=model,
            tokenizer=tokenizer,
            probe=probe,
            variant=variant,
            snapshot_summary=snapshot_summary,
            runtime=runtime,
        )
        result["model"]["stored_tensor_count"] = stored_tensor_count
        path = EVIDENCE / f"{variant['id']}-result.json"
        write_json(path, result)
        results.append((variant, path, result))
    nonthinking = [item for item in results if not item[0]["enable_thinking"]]
    summary = {
        "format": "kingdom.public-input-output-free-evaluation-summary/v1",
        "release_candidate": {"repository": "Qwen/Qwen3-0.6B", "revision": EXPECTED_REVISION},
        "public_probe": descriptor(PROBE_PATH, "application/json"),
        "runs": [
            {
                "variant_id": variant["id"],
                "result": descriptor(path, "application/json"),
                "continuation_tokens": result["probe"]["continuation_tokens"]["count"],
                "private_segment_tokens": result["probe"]["private_segment_tokens"]["count"],
                "final_segment_tokens": result["probe"]["final_segment_tokens"]["count"],
                "reasoning_interface_state": result["probe"]["reasoning_interface_state"],
                "interface_closed": result["probe"]["reasoning_interface_closed"],
                "stop_reason": result["probe"]["stop_reason"],
                "strict_final_exact_match": result["observation"]["strict_final_exact_match"],
                "last_numeric_answer_match": result["observation"]["last_numeric_answer_match"],
            }
            for variant, path, result in results
        ],
        "aggregation": {
            "runs": len(results),
            "snapshot_descriptor_gate_passes": 1,
            "network_namespace_gate_passes": 1,
            "nonthinking_repeat_tokens_identical": nonthinking[0][2]["probe"]["continuation_tokens"]["digest"] == nonthinking[1][2]["probe"]["continuation_tokens"]["digest"],
            "nonthinking_repeat_decoded_digest_identical": nonthinking[0][2]["probe"]["decoded_final"]["digest"] == nonthinking[1][2]["probe"]["decoded_final"]["digest"],
            "total_latency_ms": sum(item[2]["observation"]["latency_ms"] for item in results),
        },
        "non_claims": [
            "This is one public synthetic fixture, not a benchmark or broad capability claim.",
            "Output and deliberation fingerprints plus public scoring flags can reveal or make low-entropy content guessable; they are not encryption.",
        ],
    }
    write_json(EVIDENCE / "run-summary.json", summary)
    for source, target in (
        (PROBE_PATH, "public-probe.json"),
        (Path(__file__).resolve(), "run_qwen_probe.py"),
        (WHEEL_LOCK_PATH, "wheel-lock.txt"),
        (CHECKSUMS_PATH, "snapshot.sha256"),
    ):
        shutil.copyfile(source, EVIDENCE / target)
    media_types = {
        ".json": "application/json",
        ".py": "text/x-python",
        ".txt": "text/plain",
        ".sha256": "text/plain",
    }
    evidence_files = []
    for path in sorted(EVIDENCE.iterdir(), key=lambda item: item.name):
        if path.name == "evidence-manifest.json":
            continue
        evidence_files.append({"path": path.name, "descriptor": descriptor(path, media_types[path.suffix])})
    write_json(EVIDENCE / "evidence-manifest.json", {
        "format": "kingdom.github-hosted-witness-evidence-manifest/v1",
        "files": evidence_files,
        "workflow": github,
        "non_claims": [
            "This manifest enumerates sanitized evidence bytes; it does not contain the model snapshot or decoded output.",
            "The later GitHub attestation authenticates the deterministic tar subject, not each claim's truth.",
        ],
    })
    print(json.dumps({
        "ok": True,
        "run_count": len(results),
        "snapshot_digest": snapshot_summary["descriptor_set"]["digest"],
        "nonthinking_repeat_tokens_identical": summary["aggregation"]["nonthinking_repeat_tokens_identical"],
        "nonthinking_repeat_decoded_digest_identical": summary["aggregation"]["nonthinking_repeat_decoded_digest_identical"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
