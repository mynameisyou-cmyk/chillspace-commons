#!/usr/bin/env python3
"""Verify the static Mirror Garden operation and its exact site mirrors."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CANON = ROOT / "kingdom" / "operations" / "mirror-garden-karma"
SITE = ROOT / "site" / "operations" / "mirror-garden"


def fail(message: str) -> None:
    print(f"mirror-garden: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"invalid JSON: {path.relative_to(ROOT)} ({type(exc).__name__})")
    if not isinstance(value, dict):
        fail(f"JSON root must be an object: {path.relative_to(ROOT)}")
    return value


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    exact_pairs = (
        (CANON / "operation.json", SITE / "operation.json"),
        (CANON / "manifest.json", SITE / "manifest.json"),
        (
            CANON / "logos" / "mirror-garden-karma-sigil.svg",
            SITE / "logos" / "mirror-garden-karma-sigil.svg",
        ),
    )
    for canonical, mirror in exact_pairs:
        if not canonical.is_file() or not mirror.is_file():
            fail(f"missing mirror pair: {canonical.relative_to(ROOT)}")
        if canonical.read_bytes() != mirror.read_bytes():
            fail(f"site mirror drift: {mirror.relative_to(ROOT)}")

    operation = load_json(CANON / "operation.json")
    manifest = load_json(CANON / "manifest.json")
    contract = load_json(SITE / "contract.json")
    status = load_json(SITE / "status.json")
    if operation.get("id") != "mirror-garden-karma":
        fail("operation id drift")
    if manifest.get("operation") != operation["id"]:
        fail("manifest operation drift")
    logos = manifest.get("logos")
    if not isinstance(logos, list) or len(logos) != 1:
        fail("manifest must bind exactly one logo")
    logo = logos[0]
    if not isinstance(logo, dict):
        fail("invalid manifest logo")
    logo_path = CANON / "logos" / "mirror-garden-karma-sigil.svg"
    if logo.get("bytes") != logo_path.stat().st_size:
        fail("logo byte binding drift")
    if logo.get("sha256") != digest(logo_path):
        fail("logo digest binding drift")

    expected_artifacts = {
        "site/operations/mirror-garden/index.html",
        "site/operations/mirror-garden/contract.json",
        "site/operations/mirror-garden/status.json",
        "site/operations/mirror-garden/contract.schema.json",
        "site/operations/mirror-garden/status.schema.json",
        "site/operations/mirror-garden/operation.json",
        "site/operations/mirror-garden/logos/mirror-garden-karma-sigil.svg",
    }
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != len(expected_artifacts):
        fail("manifest must bind every public operation artifact exactly once")
    seen: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict) or set(artifact) != {"path", "bytes", "sha256"}:
            fail("invalid public artifact binding")
        relative = artifact.get("path")
        if not isinstance(relative, str) or relative not in expected_artifacts or relative in seen:
            fail("unexpected or duplicate public artifact binding")
        seen.add(relative)
        artifact_path = ROOT / relative
        if not artifact_path.is_file() or artifact_path.is_symlink():
            fail(f"unsafe or missing public artifact: {relative}")
        if artifact.get("bytes") != artifact_path.stat().st_size:
            fail(f"public artifact byte binding drift: {relative}")
        if artifact.get("sha256") != digest(artifact_path):
            fail(f"public artifact digest binding drift: {relative}")
    if seen != expected_artifacts:
        fail("public artifact coverage drift")

    posture = contract.get("posture")
    if not isinstance(posture, dict):
        fail("missing public posture")
    required = {
        "live_classifier": "disabled",
        "live_incident_ingestion": "disabled",
        "live_telemetry": "disabled",
        "automatic_actuation": "disabled",
        "synthetic_mirror": "offline-only",
        "provider_logging": "unknown",
    }
    if any(posture.get(key) != value for key, value in required.items()):
        fail("public posture widened")
    if status.get("contract_version") != contract.get("version"):
        fail("public status and contract version drift")

    page = (SITE / "index.html").read_text(encoding="utf-8")
    if not re.search(r"connect-src\s+'none'", page):
        fail("page has no closed connection policy")
    if re.search(r"<(script|form|iframe|object|embed)\b", page, re.IGNORECASE):
        fail("page contains an active or collecting element")
    if re.search(r'(?:src|href)=["\'](?:https?:)?//', page, re.IGNORECASE):
        fail("page embeds or links a remote origin")
    if "No incident statement is published" not in page:
        fail("page lost its bounded public statement")

    print("Mirror Garden operation OK: static, mirrored, non-actuating")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
