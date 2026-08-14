#!/usr/bin/env python3
"""Run one private Qwen3 probe and emit content-minimized descriptors."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import resource
import sys
import time
from datetime import datetime, timezone

if os.environ.get("PYTHONHASHSEED") != "0":
    raise RuntimeError("PYTHONHASHSEED=0 must be inherited at interpreter startup")
for variable, expected in {
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "TOKENIZERS_PARALLELISM": "false",
}.items():
    observed = os.environ.setdefault(variable, expected)
    if observed != expected:
        raise RuntimeError(f"{variable} must equal {expected!r}")

import torch
from safetensors import safe_open
from transformers import AutoModelForCausalLM, AutoTokenizer


ROOT = Path(__file__).resolve().parent
SNAPSHOT = ROOT / "snapshot"
SPEC_PATH = ROOT / "probe-spec.json"
RESULT_PATH = Path(os.environ.get("KINGDOM_RESULT_PATH", ROOT / "run-result.json"))
EXPECTED_REVISION = "c1899de289a04d12100db370d81485cdf75e47ca"
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
CLOSE_THINK_TOKEN_ID = 151668


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def raw_descriptor(path: Path, media_type: str) -> dict[str, object]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
            size += len(block)
    return {
        "media_type": media_type,
        "digest": "sha256:" + digest.hexdigest(),
        "size": size,
    }


def token_descriptor(token_ids: list[int]) -> dict[str, object]:
    raw = json.dumps(token_ids, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    return {"digest": sha256_bytes(raw), "count": len(token_ids), "canonical_size": len(raw)}


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def installed_versions() -> dict[str, str]:
    names = [
        "accelerate",
        "huggingface-hub",
        "numpy",
        "safetensors",
        "tokenizers",
        "torch",
        "transformers",
    ]
    return {name: importlib.metadata.version(name) for name in names}


def main() -> int:
    spec_raw = SPEC_PATH.read_bytes()
    spec = json.loads(spec_raw)
    actual_paths = sorted(path.name for path in SNAPSHOT.iterdir())
    expected_paths = sorted(row[0] for row in EXPECTED_SNAPSHOT)
    if actual_paths != expected_paths:
        raise RuntimeError("pinned snapshot file set mismatch")
    snapshot_files = []
    for name, media_type, expected_size, expected_sha256 in EXPECTED_SNAPSHOT:
        path = SNAPSHOT / name
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"pinned snapshot entry is not a regular file: {name}")
        observed = raw_descriptor(path, media_type)
        if observed["digest"] != "sha256:" + expected_sha256 or observed["size"] != expected_size:
            raise RuntimeError(f"pinned snapshot descriptor mismatch: {name}")
        snapshot_files.append({"path": name, "descriptor": observed})
    snapshot_set_raw = (
        json.dumps(snapshot_files, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        + b"\n"
    )
    snapshot_verification = {
        "revision": EXPECTED_REVISION,
        "file_count": len(snapshot_files),
        "total_bytes": sum(item["descriptor"]["size"] for item in snapshot_files),
        "descriptor_set": {
            "media_type": "application/json",
            "digest": sha256_bytes(snapshot_set_raw),
            "size": len(snapshot_set_raw),
        },
        "checked_before_loader_sequence": True,
    }
    weight = next(
        item["descriptor"] for item in snapshot_files if item["path"] == "model.safetensors"
    )

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(spec["generation"]["seed"])

    started_at = timestamp()
    started = time.perf_counter_ns()
    tokenizer = AutoTokenizer.from_pretrained(
        SNAPSHOT,
        local_files_only=True,
        trust_remote_code=False,
    )
    rendered = tokenizer.apply_chat_template(
        spec["messages"],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=spec["enable_thinking"],
    )
    inputs = tokenizer(rendered, return_tensors="pt")

    model = AutoModelForCausalLM.from_pretrained(
        SNAPSHOT,
        local_files_only=True,
        trust_remote_code=False,
        use_safetensors=True,
        dtype=torch.float32,
        attn_implementation="eager",
    )
    model.eval()
    generation = spec["generation"]
    generation_arguments = {
        "do_sample": generation["do_sample"],
        "max_new_tokens": generation["max_new_tokens"],
        "pad_token_id": tokenizer.pad_token_id,
        "eos_token_id": model.generation_config.eos_token_id,
    }
    if generation["do_sample"]:
        generation_arguments.update({
            "temperature": generation["temperature"],
            "top_p": generation["top_p"],
            "top_k": generation["top_k"],
        })
    with torch.inference_mode():
        generated = model.generate(**inputs, **generation_arguments)
    finished = time.perf_counter_ns()
    finished_at = timestamp()

    input_ids = inputs["input_ids"][0].tolist()
    continuation_ids = generated[0][len(input_ids):].tolist()
    try:
        close_position = len(continuation_ids) - continuation_ids[::-1].index(CLOSE_THINK_TOKEN_ID)
    except ValueError:
        close_position = None
    if spec["enable_thinking"] and close_position is None:
        private_segment = continuation_ids
        final_segment = []
    else:
        split_position = close_position or 0
        private_segment = continuation_ids[:split_position]
        final_segment = continuation_ids[split_position:]
    decoded_final = tokenizer.decode(final_segment, skip_special_tokens=True).strip()
    strict_exact = decoded_final == spec["expected_final"]
    numeric_answers = re.findall(r"(?<!\d)-?\d+(?!\d)", decoded_final)
    sole_numeric_answer_match = numeric_answers == [spec["expected_final"]]
    last_numeric_answer_match = numeric_answers[-1:] == [spec["expected_final"]]

    eos_ids = model.generation_config.eos_token_id
    if isinstance(eos_ids, int):
        eos_ids = [eos_ids]
    if continuation_ids and continuation_ids[-1] in eos_ids:
        stop_reason = "eos-token"
    elif len(continuation_ids) == generation["max_new_tokens"]:
        stop_reason = "max-new-tokens"
    else:
        stop_reason = "runtime-other"

    with safe_open(SNAPSHOT / "model.safetensors", framework="pt", device="cpu") as handle:
        stored_tensor_count = len(handle.keys())

    result = {
        "format": "kingdom.private-output-free-model-run/v1",
        "claim_boundary": {
            "class": "curator-observed-local-execution",
            "raw_prompt_retained_publicly": False,
            "raw_output_retained_publicly": False,
            "raw_deliberation_retained_publicly": False,
            "offline_verifier_reexecutes_model": False,
            "offline_verifier_proves_loaded_weight_path": False,
        },
        "model": {
            "repository": "Qwen/Qwen3-0.6B",
            "revision": EXPECTED_REVISION,
            "weight_file": weight,
            "snapshot_verification": snapshot_verification,
            "loader_class": type(model).__name__,
            "tokenizer_class": type(tokenizer).__name__,
            "stored_tensor_count": stored_tensor_count,
            "unique_parameter_count": sum(parameter.numel() for parameter in model.parameters()),
            "dtype": "float32 widened exactly from bfloat16 source values",
            "trust_remote_code": False,
        },
        "runtime": {
            "python": platform.python_version(),
            "packages": installed_versions(),
            "os": "macOS 15.7.3 build 24G419",
            "architecture": platform.machine(),
            "processor": "Apple M3 CPU",
            "device": "cpu",
            "attention": "PyTorch eager",
            "intraop_threads": torch.get_num_threads(),
            "interop_threads": torch.get_num_interop_threads(),
            "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
            "python_hash_seed": os.environ["PYTHONHASHSEED"],
            "offline_loading_flags": {
                "HF_HUB_OFFLINE": os.environ["HF_HUB_OFFLINE"],
                "TRANSFORMERS_OFFLINE": os.environ["TRANSFORMERS_OFFLINE"],
            },
        },
        "probe": {
            "case_id": spec["case_id"],
            "private_spec": {
                "media_type": "application/json",
                "digest": sha256_bytes(spec_raw),
                "size": len(spec_raw),
            },
            "message_json_sha256": sha256_bytes(
                json.dumps(spec["messages"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
            ),
            "rendered_template": {
                "digest": sha256_bytes(rendered.encode("utf-8")),
                "size": len(rendered.encode("utf-8")),
            },
            "input_tokens": token_descriptor(input_ids),
            "continuation_tokens": token_descriptor(continuation_ids),
            "private_segment_tokens": token_descriptor(private_segment),
            "private_segment_closed": close_position is not None,
            "final_segment_tokens": token_descriptor(final_segment),
            "decoded_final": {
                "digest": sha256_bytes(decoded_final.encode("utf-8")),
                "size": len(decoded_final.encode("utf-8")),
            },
            "stop_reason": stop_reason,
        },
        "sampling": {
            "strategy": "seeded multinomial" if generation["do_sample"] else "greedy",
            "do_sample": generation["do_sample"],
            "temperature": str(generation["temperature"]) if generation["do_sample"] else "not-applied",
            "top_p": str(generation["top_p"]) if generation["do_sample"] else "not-applied",
            "top_k": generation["top_k"] if generation["do_sample"] else 0,
            "max_new_tokens": generation["max_new_tokens"],
            "seed": str(generation["seed"]),
            "enable_thinking": spec["enable_thinking"],
        },
        "observation": {
            "started_at": started_at,
            "finished_at": finished_at,
            "latency_ms": (finished - started) // 1_000_000,
            "max_resident_set_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "strict_final_exact_match": strict_exact,
            "sole_numeric_answer_match": sole_numeric_answer_match,
            "last_numeric_answer_match": last_numeric_answer_match,
            "numeric_answer_count": len(numeric_answers),
            "cases": 1,
        },
        "non_claims": [
            "This sanitized record is a curator observation, not independently reproduced execution evidence.",
            "The public capsule does not contain the prompt, decoded output, generated deliberation, or model weight bytes.",
            "A signature binds this record to a task key; it does not prove the model loaded the named local path or establish safety, quality, publisher identity, endorsement, or broad capability.",
            "One private synthetic case is not a benchmark or a general model evaluation.",
        ],
    }
    RESULT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "ok": last_numeric_answer_match,
        "result": str(RESULT_PATH),
        "latency_ms": result["observation"]["latency_ms"],
        "continuation_tokens": result["probe"]["continuation_tokens"]["count"],
        "private_segment_tokens": result["probe"]["private_segment_tokens"]["count"],
        "final_segment_tokens": result["probe"]["final_segment_tokens"]["count"],
        "stop_reason": stop_reason,
    }, sort_keys=True))
    return 0 if last_numeric_answer_match else 2


if __name__ == "__main__":
    raise SystemExit(main())
