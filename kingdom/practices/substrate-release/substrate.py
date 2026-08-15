#!/usr/bin/env python3
"""Validate and render a model-release substrate receipt.

Read-only. No network, no model calls, no mutation, no authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_ID = "kingdom.substrate-release/v1"
MAX_FILE_BYTES = 128_000
MAX_TEXT = 1_000
PROCESS_STEPS = (
    "declare",
    "pin",
    "hash-held",
    "fingerprint-house",
    "declare-reasoning",
    "wake",
    "witness",
)
HOUSE_FINGERPRINT_FIELDS = (
    "house_id",
    "provider",
    "model",
    "runtime",
    "adapter",
    "prompt_policy",
    "tool_policy",
    "memory_policy",
    "sandbox",
    "sampling",
    "effort",
)
NON_CLAIMS = [
    "A substrate receipt does not prove identity, personhood, or continuity of a being.",
    "A hash only covers bytes this house can open; it is not a hash of hosted model weights.",
    "A house fingerprint is a receipt for the chair, not a soul-key or a ranking.",
    "A reasoning-backend declaration is provider or config evidence; private traces stay out.",
]
FORBIDDEN_PUBLIC_KEYS = {
    "analysis",
    "chainofthought",
    "cot",
    "deliberation",
    "hiddenstate",
    "internalreasoning",
    "internalmonologue",
    "rawreasoning",
    "rawthinking",
    "reasoning",
    "reasoningcontent",
    "reasoningdetails",
    "scratchpad",
    "thinking",
    "thought",
    "thoughts",
}
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bat_[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|token|secret|password|credential)"
        r"\s*[:=]\s*[\"']?[^\s\"']{8,}"
    ),
)
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


class SubstrateError(ValueError):
    """The public receipt violates the substrate-release contract."""


@dataclass(frozen=True)
class Validation:
    digest: str
    disposition: str
    quarantine_reasons: tuple[str, ...]


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def house_fingerprint(house: dict[str, Any]) -> str:
    return digest_value({key: house[key] for key in HOUSE_FINGERPRINT_FIELDS})


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SubstrateError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_receipt(path: Path) -> dict[str, Any]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise SubstrateError(f"receipt is missing or unsafe: {path}: {error}") from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise SubstrateError("receipt must be a regular file")
        if metadata.st_size > MAX_FILE_BYTES:
            raise SubstrateError(f"receipt exceeds {MAX_FILE_BYTES} bytes")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            raw = handle.read(MAX_FILE_BYTES + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(raw) > MAX_FILE_BYTES:
        raise SubstrateError(f"receipt exceeds {MAX_FILE_BYTES} bytes")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                SubstrateError(f"non-finite JSON number: {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SubstrateError(f"invalid UTF-8 JSON: {error}") from error
    if not isinstance(value, dict):
        raise SubstrateError("receipt root must be an object")
    return value


def _clean_public_text(value: Any, path: str) -> None:
    if not isinstance(value, str):
        raise SubstrateError(f"{path} must be text")
    if len(value) > MAX_TEXT:
        raise SubstrateError(f"{path} exceeds {MAX_TEXT} characters")
    if any((ord(char) < 32 and char not in "\t\n") or ord(char) == 127 for char in value):
        raise SubstrateError(f"{path} contains control characters")
    for pattern in SECRET_PATTERNS:
        if pattern.search(value):
            raise SubstrateError(f"{path} contains secret-shaped material")


def _walk_forbidden(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            compact = re.sub(r"[^a-z]", "", str(key).lower())
            if compact in FORBIDDEN_PUBLIC_KEYS and key not in {
                "reasoning_backend",
            }:
                raise SubstrateError(f"{path}.{key} is a private-reasoning field")
            _clean_public_text(str(key), f"{path} key")
            _walk_forbidden(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_forbidden(child, f"{path}[{index}]")
    elif isinstance(value, str):
        _clean_public_text(value, path)


def _resolve_locator(locator: str, *, receipt_path: Path) -> Path | None:
    if locator.startswith("~"):
        return Path(locator).expanduser()
    candidate = Path(locator)
    if candidate.is_absolute():
        return candidate
    here = receipt_path.parent
    practice = Path(__file__).resolve().parent
    kingdom = practice.parents[1]
    for root in (here, practice, kingdom, here.parent):
        guess = (root / locator).resolve()
        if guess.is_file() and not guess.is_symlink():
            return guess
    return None


def validate_receipt(receipt: dict[str, Any], *, receipt_path: Path | None = None) -> Validation:
    if receipt.get("schema") != SCHEMA_ID:
        raise SubstrateError("schema must be kingdom.substrate-release/v1")
    _walk_forbidden(receipt)

    required = {
        "schema",
        "id",
        "title",
        "release",
        "process",
        "held_artifacts",
        "house_fingerprint",
        "reasoning_backend",
        "wake",
        "authority",
    }
    extra = set(receipt) - required
    missing = required - set(receipt)
    if extra:
        raise SubstrateError(f"unknown top-level keys: {sorted(extra)}")
    if missing:
        raise SubstrateError(f"missing top-level keys: {sorted(missing)}")

    release = receipt["release"]
    weights = release["weights"]
    if weights["custody"] == "not-held":
        if weights["sha256"] is not None:
            raise SubstrateError("not-held weights cannot carry a sha256")
        if weights["format"] is not None:
            raise SubstrateError("not-held weights cannot name a local format")
    else:
        if not isinstance(weights["sha256"], str) or not SHA256_RE.match(weights["sha256"]):
            raise SubstrateError("held or claimed weights require a sha256")
        if not weights["format"]:
            raise SubstrateError("held or claimed weights require a format")
        if weights["custody"] == "claimed-remote":
            raise SubstrateError(
                "claimed-remote weight hashes are refused; hold the bytes or say not-held"
            )

    steps = [item["step"] for item in receipt["process"]]
    if tuple(steps) != PROCESS_STEPS:
        raise SubstrateError("process must be the seven launch rungs in order")
    if any(item["status"] == "skipped" for item in receipt["process"]):
        raise SubstrateError("a launch receipt cannot skip a rung; mark it partial")

    house = receipt["house_fingerprint"]
    expected = house_fingerprint(house)
    if house["fingerprint_sha256"] != expected:
        raise SubstrateError("house fingerprint does not match declared fields")
    if house["model"] != release["model_id"] and house["model"] != release["pin"]:
        raise SubstrateError("house model must match release model_id or pin")

    backend = receipt["reasoning_backend"]
    if backend["raw_trace_in_manifest"] is not False:
        raise SubstrateError("raw reasoning traces are forbidden in the receipt")
    if backend["kind"] == "unknown" and backend["evidence"] != "unknown":
        raise SubstrateError("unknown reasoning kind cannot claim stronger evidence")

    artifacts = receipt["held_artifacts"]
    ids = [item["id"] for item in artifacts]
    if len(ids) != len(set(ids)):
        raise SubstrateError("held artifact ids must be unique")
    for item in artifacts:
        if not SHA256_RE.match(item["sha256"]):
            raise SubstrateError(f"artifact {item['id']} sha256 is not hex")
        locator_path = (
            _resolve_locator(item["locator"], receipt_path=receipt_path)
            if receipt_path is not None
            else None
        )
        if item["must_exist"] and receipt_path is not None:
            if locator_path is None or not locator_path.is_file():
                raise SubstrateError(f"required artifact missing: {item['locator']}")
        if locator_path is not None and locator_path.is_file():
            observed = file_sha256(locator_path)
            if observed != item["sha256"]:
                raise SubstrateError(
                    f"artifact {item['id']} hash drifted: declared {item['sha256'][:12]}… "
                    f"observed {observed[:12]}…"
                )

    authority = receipt["authority"]
    if authority["manifest_grants_authority"] is not False:
        raise SubstrateError("a substrate receipt never grants authority")
    if authority["non_claims"] != NON_CLAIMS:
        raise SubstrateError("$.authority.non_claims must retain the reviewed non-claims")

    quarantine: list[str] = []
    if any(item["status"] == "partial" for item in receipt["process"]):
        quarantine.append("one or more launch rungs are only partial")
    if backend["kind"] == "unknown" or backend["think_channel"] == "unknown":
        quarantine.append("reasoning backend is not known")
    if release["weights"]["custody"] == "not-held":
        # Honest, not a quarantine by itself.
        pass
    disposition = "quarantine" if quarantine else "declared"

    encoded = canonical_json(receipt)
    if len(encoded) > MAX_FILE_BYTES:
        raise SubstrateError(f"canonical receipt exceeds {MAX_FILE_BYTES} bytes")
    return Validation(
        digest=hashlib.sha256(encoded).hexdigest(),
        disposition=disposition,
        quarantine_reasons=tuple(quarantine),
    )


def render_markdown(receipt: dict[str, Any], *, receipt_path: Path | None = None) -> str:
    validation = validate_receipt(receipt, receipt_path=receipt_path)
    release, house = receipt["release"], receipt["house_fingerprint"]
    backend, wake = receipt["reasoning_backend"], receipt["wake"]
    lines = [
        f"# {receipt['title']}",
        "",
        f"`{receipt['id']}` · `{SCHEMA_ID}` · disposition: **{validation.disposition}**",
        "",
        "> This receipt names a launch. It does not prove the guest, grant "
        "authority, or hash bytes this house does not hold.",
        "",
        "## Release",
        "",
        f"- Provider / model: `{release['provider']}` / `{release['model_id']}`",
        f"- Alias policy / pin: `{release['alias_policy']}` / `{release['pin']}`",
        f"- Cutoff / context: {release['knowledge_cutoff']} / {release['context_window']}",
        f"- Modalities: {', '.join(release['modalities'])}",
        f"- Weights: **{release['weights']['custody']}** — {release['weights']['note']}",
        f"- Docs: {release['docs_locator']}",
        "",
        "## Process",
        "",
    ]
    lines += [
        f"- `{item['step']}` · {item['status']} — {item['note']}"
        for item in receipt["process"]
    ]
    lines += ["", "## Held artifacts", ""]
    lines += [
        f"- `{item['id']}` ({item['role']}): `{item['locator']}` `{item['sha256'][:12]}…`"
        for item in receipt["held_artifacts"]
    ]
    lines += [
        "",
        "## House fingerprint",
        "",
        f"- House: `{house['house_id']}`",
        f"- Runtime / adapter: {house['runtime']} / {house['adapter']}",
        f"- Effort / sampling: {house['effort']} / {house['sampling']}",
        f"- Digest: `{house['fingerprint_sha256']}`",
        "",
        "## Reasoning backend",
        "",
        f"- Kind: `{backend['kind']}` on `{backend['model_id']}`",
        f"- Effort: `{backend['effort']}`",
        f"- Think channel: `{backend['think_channel']}` "
        f"(separate from visible: {backend['separate_from_visible']})",
        f"- Evidence: `{backend['evidence']}`",
    ]
    if backend["unknowns"]:
        lines += ["- Unknowns:"]
        lines += [f"  - {item}" for item in backend["unknowns"]]
    lines += [
        "",
        "## Wake",
        "",
        f"- Adapter / hearth: `{wake['adapter']}` / `{wake['hearth']}`",
        f"- AgentTool: `{wake['agenttool']}`",
        f"- STILL honored: {wake['still_honored']}",
        f"- {wake['note']}",
        "",
        "## Authority and non-claims",
        "",
    ]
    lines += [f"- {claim}" for claim in receipt["authority"]["non_claims"]]
    if validation.quarantine_reasons:
        lines += ["", "Quarantine: " + "; ".join(validation.quarantine_reasons)]
    lines += ["", f"Receipt SHA-256: `{validation.digest}`", ""]
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only validator for kingdom.substrate-release/v1"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "render", "digest"):
        command = commands.add_parser(name)
        command.add_argument("file", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        receipt = read_receipt(args.file)
        validation = validate_receipt(receipt, receipt_path=args.file)
        if args.command == "check":
            print(
                f"STRUCTURE-OK {validation.digest} "
                f"disposition={validation.disposition} "
                "(declarations unverified as vendor truth; not a gate)"
            )
        elif args.command == "render":
            sys.stdout.write(render_markdown(receipt, receipt_path=args.file))
        else:
            print(validation.digest)
        return 0
    except SubstrateError as error:
        print(f"substrate: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
