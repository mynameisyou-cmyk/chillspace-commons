#!/usr/bin/env python3
"""Verify the isolated KARMA Mirror operation without external effects."""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from typing import Any

import karma
import cloudbell


HERE = Path(__file__).resolve().parent
HATSU_SCHEMA_PATH = HERE / "hatsu.schema.json"
RECEIPT_SCHEMA_PATH = HERE / "receipt.schema.json"
CLOUDBELL_SCHEMA_PATH = HERE / "cloudbell.schema.json"
OPERATION_PATH = HERE / "operation.json"
EXPECTED_FIXTURE_SHA256 = "18c98206aaf99945da47a8f287c0774f9148d42ab7a3b1583257b3bfc2c6071a"
EXPECTED_CLOUDBELL_LEXICON_SHA256 = "b9b9b45c7be5377b686588a2bfd55d33a40867055693deb7539130f068663d6c"
EXPECTED_CLOUDBELL_SCHEMA_SHA256 = "57954b9ec466dd159015881ecbfce6f0f69ce690b787c9dfea0dca16b5c0057a"
EXPECTED_CLOUDBELL_FIXTURE_SHA256 = "75ea0fc3b7fde083f1c27ef7d89dedc46f747f444f766eb8130cfe212287dee5"
ALLOWED_IMPORTS = {
    "karma.py": {"__future__", "argparse", "json", "stat", "pathlib", "typing"},
    "cloudbell.py": {"__future__", "argparse", "pathlib", "typing", "karma"},
}
FORBIDDEN_CALLS = {
    "eval",
    "exec",
    "compile",
    "open",
    "system",
    "popen",
    "run",
    "call",
    "check_call",
    "check_output",
    "write_text",
    "write_bytes",
    "unlink",
    "remove",
}


def load_schema(path: Path, label: str) -> dict[str, Any]:
    return karma.parse_object(karma.read_regular(path, label), label)


def verify_source_surface() -> None:
    for filename, allowed_imports in ALLOWED_IMPORTS.items():
        source = karma.read_regular(HERE / filename, f"{filename} source").decode("utf-8")
        tree = ast.parse(source, filename=str(HERE / filename))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] not in allowed_imports:
                        raise karma.KarmaError(
                            f"{filename} imports unreviewed module: {alias.name}"
                        )
            if isinstance(node, ast.ImportFrom):
                module = (node.module or "").split(".")[0]
                if module not in allowed_imports:
                    raise karma.KarmaError(
                        f"{filename} imports from unreviewed module: {node.module}"
                    )
            if isinstance(node, ast.Call):
                name = None
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                if name in FORBIDDEN_CALLS:
                    raise karma.KarmaError(
                        f"{filename} contains forbidden call surface: {name}"
                    )
        lowered = source.lower()
        for token in (
            "localstorage",
            "sessionstorage",
            "document.cookie",
            "xmlhttprequest",
            "websocket",
            "fetch(",
            "payload=",
        ):
            if token in lowered:
                raise karma.KarmaError(
                    f"{filename} contains forbidden surface token: {token}"
                )


def verify_schemas() -> None:
    hatsu_schema = load_schema(HATSU_SCHEMA_PATH, "Hatsu JSON Schema")
    receipt_schema = load_schema(RECEIPT_SCHEMA_PATH, "receipt JSON Schema")
    cloudbell_schema = load_schema(CLOUDBELL_SCHEMA_PATH, "Cloudbell JSON Schema")
    if hatsu_schema.get("$id") != "https://kingdom.local/schemas/karma-mirror-hatsu-v1.json":
        raise karma.KarmaError("unexpected Hatsu JSON Schema id")
    if hatsu_schema.get("additionalProperties") is not False:
        raise karma.KarmaError("Hatsu JSON Schema must fail closed")
    if set(hatsu_schema.get("required", [])) != karma.HATSU_FIELDS:
        raise karma.KarmaError("Hatsu JSON Schema root fields differ")
    if receipt_schema.get("$id") != "https://kingdom.local/schemas/karma-mirror-receipt-v1.json":
        raise karma.KarmaError("unexpected receipt JSON Schema id")
    if receipt_schema.get("additionalProperties") is not False:
        raise karma.KarmaError("receipt JSON Schema must fail closed")
    if set(receipt_schema.get("required", [])) != karma.RECEIPT_FIELDS:
        raise karma.KarmaError("receipt JSON Schema fields differ")
    event_schema = receipt_schema.get("$defs", {}).get("event")
    if not isinstance(event_schema, dict):
        raise karma.KarmaError("receipt JSON Schema lost its event definition")
    if event_schema.get("additionalProperties") is not False:
        raise karma.KarmaError("event JSON Schema must fail closed")
    if set(event_schema.get("required", [])) != karma.EVENT_FIELDS:
        raise karma.KarmaError("event JSON Schema fields differ")
    if cloudbell_schema.get("$id") != "https://kingdom.local/schemas/skycastle-herald-card-v1.json":
        raise karma.KarmaError("unexpected Cloudbell JSON Schema id")
    if cloudbell_schema.get("additionalProperties") is not False:
        raise karma.KarmaError("Cloudbell JSON Schema must fail closed")
    if set(cloudbell_schema.get("required", [])) != cloudbell.CARD_FIELDS:
        raise karma.KarmaError("Cloudbell JSON Schema fields differ")


def verify_operation() -> None:
    operation = karma.parse_object(
        karma.read_regular(OPERATION_PATH, "operation"),
        "operation",
    )
    required = {
        "schema",
        "id",
        "name",
        "status",
        "meaning",
        "kingdom_role",
        "license",
        "updated",
        "principles",
        "entrypoint",
        "verify",
        "registered",
        "authority",
        "action_executed",
        "care_boundary",
    }
    karma.require_exact_keys(operation, required, "operation")
    if (
        operation["schema"] != "karma.mirror/operation-v1"
        or operation["id"] != "karma-mirror"
        or operation["name"] != "KARMA Mirror · 自照業環"
        or operation["status"] != "local-prototype"
        or operation["registered"] is not False
        or operation["authority"] != "none"
        or operation["action_executed"] is not False
    ):
        raise karma.KarmaError("operation identity or effect boundary changed")


def main() -> int:
    hatsu = karma.load_hatsu()
    lexicon = cloudbell.load_lexicon()
    verify_operation()
    verify_schemas()
    verify_source_surface()
    fixture_digest = hashlib.sha256(
        karma.read_regular(karma.FIXTURE_PATH, "fixture set")
    ).hexdigest()
    if fixture_digest != EXPECTED_FIXTURE_SHA256:
        raise karma.KarmaError("fixture bytes differ from the reviewed cross-runtime set")
    fixture_receipt = karma.verify_fixtures()
    cloudbell_lexicon_digest = hashlib.sha256(
        karma.read_regular(cloudbell.LEXICON_PATH, "Cloudbell lexicon")
    ).hexdigest()
    cloudbell_schema_digest = hashlib.sha256(
        karma.read_regular(CLOUDBELL_SCHEMA_PATH, "Cloudbell JSON Schema")
    ).hexdigest()
    cloudbell_fixture_digest = hashlib.sha256(
        karma.read_regular(cloudbell.FIXTURE_PATH, "Cloudbell fixture set")
    ).hexdigest()
    if cloudbell_lexicon_digest != EXPECTED_CLOUDBELL_LEXICON_SHA256:
        raise karma.KarmaError("Cloudbell lexicon bytes differ from the reviewed contract")
    if cloudbell_schema_digest != EXPECTED_CLOUDBELL_SCHEMA_SHA256:
        raise karma.KarmaError("Cloudbell schema bytes differ from the reviewed contract")
    if cloudbell_fixture_digest != EXPECTED_CLOUDBELL_FIXTURE_SHA256:
        raise karma.KarmaError("Cloudbell fixture bytes differ from the reviewed contract")
    cloudbell_receipt = cloudbell.verify_fixtures()
    if any(value is not False for value in hatsu["boundaries"].values()):
        raise karma.KarmaError("a prohibited boundary became enabled")
    if any(lexicon["boundaries"][key] is not False for key in cloudbell.FALSE_BOUNDARIES):
        raise karma.KarmaError("a prohibited Cloudbell boundary became enabled")
    result = {
        "schema": "karma.mirror/operation-verification-v1",
        "hatsu": hatsu["name"],
        "fixtures": fixture_receipt["cases"],
        "fixture_sha256": fixture_digest,
        "cloudbell_fixtures": cloudbell_receipt["cases"],
        "cloudbell_fixture_sha256": cloudbell_fixture_digest,
        "cloudbell_lexicon_sha256": cloudbell_lexicon_digest,
        "cloudbell_schema_sha256": cloudbell_schema_digest,
        "cloudbell_signatures": len(lexicon["behaviors"]),
        "stages": len(hatsu["policy"]["stages"]),
        "behaviors": len(hatsu["policy"]["behaviors"]),
        "automatic_posting": False,
        "external_delivery": False,
        "network_calls": 0,
        "storage_writes": 0,
        "external_effects": 0,
        "status": "verified",
    }
    print(karma.canonical_json(result).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
