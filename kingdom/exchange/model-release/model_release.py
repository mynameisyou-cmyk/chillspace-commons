#!/usr/bin/env python3
"""Validate and receipt the Kingdom Model Release Substrate.

The reference tool is deliberately local, deterministic, stdlib-only, and
read-only. It never downloads an artifact, calls a model, executes release
code, signs a record, publishes, deploys, or writes an external system.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import re
import stat
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
SCHEMA_PATH = HERE / "schema.json"
VALIDATOR_PATH = HERE / "model_release.py"
MAX_FILE_BYTES = 512 * 1024
MAX_DEPTH = 18
MAX_TEXT_BYTES = 16 * 1024
MIN_INTEGER = -(2**63)
MAX_INTEGER = 2**63 - 1
CANONICALIZATION = "kingdom.canonical-json/v1"
VALIDATOR_NAME = "kingdom.model-release-validator"
VALIDATOR_VERSION = "1.0.0"
RELEASE_SCHEMA = "kingdom.model-release/v1"
PROFILE_SCHEMA = "kingdom.model-execution-profile/v1"
ATTESTATION_SCHEMA = "kingdom.model-release-attestation/v1"
RECEIPT_SCHEMA = "kingdom.model-release-receipt/v1"
REVIEWED_SCHEMA_ID = (
    "https://mynameisyou-cmyk.github.io/chillspace-commons/"
    "exchange/model-release/schema.v1.json"
)
EXPECTED_SCHEMA_SHA256 = (
    "36b428ac4a890a6960ca06683ec9b758aa709ac4a0da3428bbd4344969318f87"
)

SCHEMA_KINDS = {
    RELEASE_SCHEMA: "model-release",
    PROFILE_SCHEMA: "execution-profile",
    ATTESTATION_SCHEMA: "attestation",
    RECEIPT_SCHEMA: "verification-receipt",
}

RELEASE_NON_CLAIMS = [
    "Digests prove byte identity only; they do not prove publisher identity, safety, quality, behavior, or truth.",
    "This manifest describes a release interface; it does not expose or verify hidden chain-of-thought, private system prompts, training data, teacher models, or safety internals.",
    "Provider backend observations are opaque observations, not cryptographic model digests.",
    "Validation performs no model call, artifact download, code execution, publication, deployment, or external write.",
]
PROFILE_NON_CLAIMS = [
    "An execution-profile digest identifies declared configuration, not reproducibility across different runtimes or hardware.",
    "Requested settings are not effective settings; every field under resolved is a declaration by the profile author.",
    "Provider backend observations are opaque observations, not cryptographic model or weight digests.",
    "Validation captures no raw environment, hostname, credential, private path, prompt, response, or reasoning trace.",
]
ATTESTATION_NON_CLAIMS = [
    "An attestation records an assertion and its evidence class; it does not make the assertion true.",
    "A signature can bind bytes to a signer under a verifier policy; it does not prove safety, quality, or every signed claim.",
    "An evaluation is bounded to its named release, execution profile, harness, data, settings, and evidence.",
    "This record grants no authority and performs no build, signature, model call, publication, deployment, or external action.",
]
RECEIPT_NON_CLAIMS = [
    "When verify recomputes this receipt against the named source, it establishes that the source parsed, matched the reviewed schema and invariants, and hashed to these bytes.",
    "A matching content digest establishes byte equality under the named canonicalization profile, not publisher identity, safety, quality, behavior, or truth.",
]

VALIDATION_PROFILE = {
    "strict_utf8_json": True,
    "duplicate_keys_rejected": True,
    "reviewed_schema_digest_matched": True,
    "domain_invariants_checked": True,
    "artifact_bytes_compared": False,
    "network_capability": False,
    "external_write_capability": False,
    "model_call_capability": False,
}

SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bgh(?:p|o|u|s|r)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|token|secret|password|credential)"
        r"\s*[:=]\s*[\"']?[^\s\"']{8,}"
    ),
)
RAW_REASONING_KEYS = {
    "chainofthought",
    "cot",
    "deliberationcontent",
    "hiddenreasoning",
    "hiddenstate",
    "internalmonologue",
    "rawreasoning",
    "rawthinking",
    "reasoningcontent",
    "reasoningdetails",
    "scratchpad",
    "scratchpadcontent",
    "thinkingcontent",
}
REQUIRED_DISCLOSURE_FIELDS = {
    "training.data",
    "training.code",
    "training.token-count",
    "training.compute",
    "post-training.recipe",
    "reasoning.recipe",
    "safety.system-internals",
}
MUTABLE_REVISIONS = {
    "current",
    "default",
    "head",
    "latest",
    "main",
    "master",
    "stable",
    "trunk",
    "unversioned",
}
UNRESOLVED_RUNTIME_VALUES = MUTABLE_REVISIONS | {
    "auto",
    "automatic",
    "provider-default",
    "provider-managed",
    "unknown",
}
SUPPORTED_SCHEMA_KEYWORDS = {
    "$schema",
    "$id",
    "$ref",
    "$defs",
    "title",
    "description",
    "type",
    "additionalProperties",
    "required",
    "properties",
    "const",
    "enum",
    "oneOf",
    "items",
    "minItems",
    "maxItems",
    "uniqueItems",
    "minLength",
    "maxLength",
    "pattern",
    "minimum",
    "maximum",
}


class ReleaseError(ValueError):
    """A record falls outside the reviewed model-release contract."""


@dataclass(frozen=True)
class Loaded:
    value: dict[str, Any]
    raw: bytes


@dataclass(frozen=True)
class ReviewedSchema:
    value: dict[str, Any]
    digest: str


def canonical_json(value: Any) -> bytes:
    """Return the exact kingdom.canonical-json/v1 byte representation."""

    try:
        return (
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
            + b"\n"
        )
    except (TypeError, ValueError, UnicodeError) as error:
        raise ReleaseError("record cannot be represented as canonical JSON") from error


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def content_digest(value: Any) -> str:
    return sha256_bytes(canonical_json(value))


def pretty_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        allow_nan=False,
    ) + "\n"


def _pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReleaseError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_float(token: str) -> float:
    raise ReleaseError(f"floating-point JSON number is outside {CANONICALIZATION}: {token}")


def _reject_constant(token: str) -> None:
    raise ReleaseError(f"non-finite JSON number: {token}")


def _parse_integer(token: str) -> int:
    digits = token[1:] if token.startswith("-") else token
    if len(digits) > 19:
        raise ReleaseError(f"integer is outside the signed 64-bit range: {token[:24]}")
    try:
        value = int(token)
    except ValueError as error:
        raise ReleaseError("invalid JSON integer") from error
    if value < MIN_INTEGER or value > MAX_INTEGER:
        raise ReleaseError(f"integer is outside the signed 64-bit range: {token}")
    return value


def _read_regular(path: Path, label: str) -> bytes:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ReleaseError(f"{label} must be a regular non-symlink file")
        if metadata.st_size > MAX_FILE_BYTES:
            raise ReleaseError(f"{label} exceeds {MAX_FILE_BYTES} bytes")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            raw = handle.read(MAX_FILE_BYTES + 1)
    except ReleaseError:
        raise
    except OSError as error:
        raise ReleaseError(f"{label} is missing or unsafe: {path}") from error
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
    if len(raw) > MAX_FILE_BYTES:
        raise ReleaseError(f"{label} exceeds {MAX_FILE_BYTES} bytes")
    return raw


def _parse_json(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs_without_duplicates,
            parse_int=_parse_integer,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except ReleaseError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as error:
        raise ReleaseError(f"{label} is not strict UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise ReleaseError(f"{label} root must be an object")
    return value


def read_document(path: Path, label: str = "record") -> Loaded:
    raw = _read_regular(path, label)
    return Loaded(_parse_json(raw, label), raw)


def _normalized_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


def _walk_public(value: Any, path: str = "$", depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise ReleaseError(f"{path} exceeds maximum depth {MAX_DEPTH}")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ReleaseError(f"{path} has a non-text key")
            _check_text(key, f"{path} key", key=True)
            if _normalized_key(key) in RAW_REASONING_KEYS:
                raise ReleaseError(f"{path}.{key} is a forbidden raw-reasoning field")
            if (
                _normalized_key(key) in {"field", "id", "name", "role"}
                and isinstance(child, str)
                and _normalized_key(child) in RAW_REASONING_KEYS
            ):
                raise ReleaseError(
                    f"{path}.{key} names a forbidden raw-reasoning content channel"
                )
            _walk_public(child, f"{path}.{key}", depth + 1)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_public(child, f"{path}[{index}]", depth + 1)
    elif isinstance(value, str):
        _check_text(value, path)
    elif isinstance(value, float):
        raise ReleaseError(f"{path} contains a floating-point value")
    elif isinstance(value, int) and not isinstance(value, bool):
        if value < MIN_INTEGER or value > MAX_INTEGER:
            raise ReleaseError(f"{path} is outside the signed 64-bit integer range")
    elif value is not None and not isinstance(value, (bool, int)):
        raise ReleaseError(f"{path} contains an unsupported JSON value")


def _check_text(value: str, path: str, *, key: bool = False) -> None:
    if not isinstance(value, str):
        raise ReleaseError(f"{path} must be text")
    if unicodedata.normalize("NFC", value) != value:
        raise ReleaseError(f"{path} must use NFC Unicode")
    if len(value.encode("utf-8")) > MAX_TEXT_BYTES:
        raise ReleaseError(f"{path} exceeds {MAX_TEXT_BYTES} UTF-8 bytes")
    if any(
        ord(char) == 127
        or unicodedata.category(char) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
        for char in value
    ):
        raise ReleaseError(f"{path} contains control or directional characters")
    if not key:
        lowered = value.lower()
        if value.startswith(("/", "~/", "~\\")) or re.match(r"^[A-Za-z]:[\\/]", value):
            raise ReleaseError(f"{path} contains a local absolute path")
        if lowered.startswith("file:"):
            raise ReleaseError(f"{path} contains a local file locator")
        for pattern in SECRET_PATTERNS:
            if pattern.search(value):
                raise ReleaseError(f"{path} contains secret-shaped material")


def _json_equal_exact(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(
            _json_equal_exact(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _json_equal_exact(a, b) for a, b in zip(left, right)
        )
    return left == right


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        )
    if expected == "null":
        return value is None
    raise ReleaseError(f"reviewed schema uses unsupported type: {expected}")


def _resolve_ref(root: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise ReleaseError(f"only local schema references are allowed: {reference}")
    current: Any = root
    for token in reference[2:].split("/"):
        key = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or key not in current:
            raise ReleaseError(f"unresolved schema reference: {reference}")
        current = current[key]
    if not isinstance(current, dict):
        raise ReleaseError(f"schema reference is not an object: {reference}")
    return current


def _validate_schema(
    value: Any,
    rule: dict[str, Any],
    root: dict[str, Any],
    path: str = "$",
) -> None:
    unknown = set(rule) - SUPPORTED_SCHEMA_KEYWORDS
    if unknown:
        raise ReleaseError(
            f"{path} schema uses unsupported keywords: {', '.join(sorted(unknown))}"
        )
    if "$ref" in rule:
        if set(rule) != {"$ref"}:
            raise ReleaseError(f"{path} combines $ref with sibling constraints")
        _validate_schema(value, _resolve_ref(root, rule["$ref"]), root, path)
        return
    if "oneOf" in rule:
        matches = 0
        for option in rule["oneOf"]:
            try:
                _validate_schema(value, option, root, path)
            except ReleaseError:
                continue
            matches += 1
        if matches != 1:
            raise ReleaseError(f"{path} must match exactly one reviewed schema branch")
    if "const" in rule and not _json_equal_exact(value, rule["const"]):
        raise ReleaseError(f"{path} differs from its reviewed constant")
    if "enum" in rule and not any(
        _json_equal_exact(value, option) for option in rule["enum"]
    ):
        raise ReleaseError(f"{path} is outside its reviewed enum")

    expected_type = rule.get("type")
    if expected_type is not None and not _type_matches(value, expected_type):
        raise ReleaseError(f"{path} must be JSON type {expected_type}")

    if isinstance(value, dict):
        required = rule.get("required", [])
        missing = [key for key in required if key not in value]
        if missing:
            raise ReleaseError(f"{path} is missing required fields: {', '.join(missing)}")
        properties = rule.get("properties", {})
        if rule.get("additionalProperties") is False:
            extra = set(value) - set(properties)
            if extra:
                raise ReleaseError(
                    f"{path} has unreviewed fields: {', '.join(sorted(extra))}"
                )
        for key, child in value.items():
            if key in properties:
                _validate_schema(child, properties[key], root, f"{path}.{key}")

    if isinstance(value, list):
        minimum = rule.get("minItems")
        maximum = rule.get("maxItems")
        if minimum is not None and len(value) < minimum:
            raise ReleaseError(f"{path} has fewer than {minimum} items")
        if maximum is not None and len(value) > maximum:
            raise ReleaseError(f"{path} has more than {maximum} items")
        if rule.get("uniqueItems"):
            encoded = [canonical_json(item) for item in value]
            if len(encoded) != len(set(encoded)):
                raise ReleaseError(f"{path} contains duplicate items")
        if "items" in rule:
            for index, child in enumerate(value):
                _validate_schema(child, rule["items"], root, f"{path}[{index}]")

    if isinstance(value, str):
        minimum = rule.get("minLength")
        maximum = rule.get("maxLength")
        if minimum is not None and len(value) < minimum:
            raise ReleaseError(f"{path} is shorter than {minimum} characters")
        if maximum is not None and len(value) > maximum:
            raise ReleaseError(f"{path} is longer than {maximum} characters")
        pattern = rule.get("pattern")
        if pattern is not None and re.search(pattern, value) is None:
            raise ReleaseError(f"{path} does not match its reviewed pattern")

    if isinstance(value, int) and not isinstance(value, bool):
        minimum = rule.get("minimum")
        maximum = rule.get("maximum")
        if minimum is not None and value < minimum:
            raise ReleaseError(f"{path} is below {minimum}")
        if maximum is not None and value > maximum:
            raise ReleaseError(f"{path} is above {maximum}")


def _load_reviewed_schema() -> ReviewedSchema:
    schema = read_document(SCHEMA_PATH, "reviewed schema").value
    digest = hashlib.sha256(canonical_json(schema)).hexdigest()
    if digest != EXPECTED_SCHEMA_SHA256:
        raise ReleaseError("reviewed model-release schema digest changed")
    if schema.get("$id") != REVIEWED_SCHEMA_ID:
        raise ReleaseError("reviewed model-release schema id changed")
    return ReviewedSchema(schema, digest)


def verify_reviewed_schema() -> str:
    return _load_reviewed_schema().digest


def _unique(items: list[dict[str, Any]], field: str, label: str) -> set[str]:
    values = [item[field] for item in items]
    if len(values) != len(set(values)):
        raise ReleaseError(f"{label} contains duplicate {field} values")
    return set(values)


def _require_refs(refs: list[str], known: set[str] | dict[str, Any], label: str) -> None:
    if not refs:
        raise ReleaseError(f"{label} must name at least one evidence ref")
    missing = sorted(set(refs) - set(known))
    if missing:
        raise ReleaseError(f"{label} has unknown evidence refs: {', '.join(missing)}")


def _immutable_revision(value: str, label: str) -> None:
    normalized = value.strip().lower()
    qualified_mutable = re.search(
        r"(?:^|[/@:#])(?:current|default|head|latest|main|master|stable|trunk|unversioned)"
        r"(?:$|[/@:#?])",
        normalized,
    )
    if normalized in UNRESOLVED_RUNTIME_VALUES or qualified_mutable:
        raise ReleaseError(f"{label} uses a mutable or unresolved revision: {value}")


def _timestamp(value: str, label: str) -> datetime:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError) as error:
        raise ReleaseError(f"{label} is not a real UTC timestamp") from error
    return parsed.replace(tzinfo=timezone.utc)


def _validate_evidence(evidence: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    _unique(evidence, "id", "evidence")
    by_id = {item["id"]: item for item in evidence}
    for item in evidence:
        _timestamp(item["retrieved_at"], f"evidence {item['id']} retrieved_at")
        if item["mutability"] == "immutable":
            _immutable_revision(item["revision"], f"evidence {item['id']}")
    return by_id


def _require_descriptor_evidence(
    descriptor: dict[str, Any],
    refs: list[str],
    evidence: dict[str, dict[str, Any]],
    label: str,
) -> None:
    _require_refs(refs, evidence, label)
    matching = [
        ref
        for ref in refs
        if "content" in evidence[ref]
        and _json_equal_exact(evidence[ref]["content"], descriptor)
    ]
    if not matching:
        raise ReleaseError(f"{label} has no evidence content matching its descriptor")


def _validate_release(value: dict[str, Any]) -> None:
    evidence_by_id = _validate_evidence(value["evidence"])
    artifacts = value["artifacts"]
    artifact_ids = _unique(artifacts, "id", "artifacts")

    _immutable_revision(value["release"]["version"], "release version")
    _timestamp(value["release"]["released_at"], "release released_at")

    for artifact in artifacts:
        status = artifact["identity_status"]
        has_descriptor = "descriptor" in artifact
        if status in {"descriptor-asserted", "fixture"} and not has_descriptor:
            raise ReleaseError(
                f"artifact {artifact['id']} identity status {status} requires a descriptor"
            )
        if status in {"unavailable", "unknown"} and has_descriptor:
            raise ReleaseError(
                f"artifact {artifact['id']} cannot carry a byte descriptor with status {status}"
            )
        if "location" in artifact and has_descriptor:
            _immutable_revision(
                artifact["location"]["revision"],
                f"artifact {artifact['id']} location",
            )
        _require_refs(
            artifact["evidence_refs"],
            evidence_by_id,
            f"artifact {artifact['id']}",
        )

    if value["release"]["access"] == "open-weights" and not any(
        artifact["role"] == "weights" for artifact in artifacts
    ):
        raise ReleaseError("an open-weights release must name at least one weights artifact")

    model = value["model"]
    if "parameters" in model and model["parameters"]["active"] > model["parameters"]["total"]:
        raise ReleaseError("model active parameter count exceeds total parameter count")
    if "context" in model:
        _require_refs(model["context"]["evidence_refs"], evidence_by_id, "model context")
    if "weights" in model:
        _require_refs(model["weights"]["evidence_refs"], evidence_by_id, "model weights")

    for interface_name in ("prompt_format", "response_format", "tools"):
        interface = value["interface"][interface_name]
        has_ref = "artifact_ref" in interface
        if interface["support"] in {"required", "supported"} and not has_ref:
            raise ReleaseError(f"interface {interface_name} requires an artifact_ref")
        if interface["support"] == "unsupported" and has_ref:
            raise ReleaseError(f"unsupported interface {interface_name} cannot name an artifact")
        if has_ref and interface["artifact_ref"] not in artifact_ids:
            raise ReleaseError(f"interface {interface_name} refers to an unknown artifact")

    reasoning = value["interface"]["reasoning"]
    efforts = reasoning["effort_levels"]
    default_effort = reasoning["default_effort"]
    if efforts and default_effort not in efforts:
        raise ReleaseError("reasoning.default_effort is not one of effort_levels")
    if not efforts and default_effort != "unknown":
        raise ReleaseError("reasoning.default_effort must be unknown when no levels are declared")
    channels = set(reasoning["item_or_channel_types"])
    resend = set(reasoning["continuation"]["resend"])
    if not resend <= channels:
        raise ReleaseError("reasoning continuation resends undeclared item or channel types")
    if reasoning["continuation"]["policy"] == "unsupported" and resend:
        raise ReleaseError("unsupported reasoning continuation cannot resend items")
    if reasoning["disclosure"] == "none" and channels:
        raise ReleaseError("reasoning disclosure none cannot declare visible item types")
    if (
        reasoning["continuation"]["policy"] == "unsupported"
        and reasoning["continuation_state"] != "none"
    ):
        raise ReleaseError("unsupported reasoning continuation must use state none")
    if reasoning["continuation_state"] == "none" and resend:
        raise ReleaseError("reasoning continuation state none cannot resend items")
    _require_refs(reasoning["evidence_refs"], evidence_by_id, "reasoning interface")

    disclosure_fields = _unique(value["disclosures"], "field", "disclosures")
    if not disclosure_fields:
        raise ReleaseError("release must carry explicit disclosure states")
    missing_disclosures = sorted(REQUIRED_DISCLOSURE_FIELDS - disclosure_fields)
    if missing_disclosures:
        raise ReleaseError(
            "release is missing baseline disclosure fields: "
            + ", ".join(missing_disclosures)
        )
    for disclosure in value["disclosures"]:
        _require_refs(
            disclosure["evidence_refs"],
            evidence_by_id,
            f"disclosure {disclosure['field']}",
        )
        if disclosure["basis"] == "inferred" and disclosure["status"] == "disclosed":
            raise ReleaseError("an inferred disclosure cannot claim disclosed status")

    term_fields = _unique(value["terms"], "field", "terms")
    access = value["release"]["access"]
    required_terms = {"license"}
    if access in {"api", "hybrid"}:
        required_terms |= {"api-terms", "data-use-policy"}
    missing_terms = sorted(required_terms - term_fields)
    if missing_terms:
        raise ReleaseError("release is missing terms states: " + ", ".join(missing_terms))
    for term in value["terms"]:
        _require_refs(term["evidence_refs"], evidence_by_id, f"terms {term['field']}")
    by_term = {term["field"]: term for term in value["terms"]}
    if access == "open-weights" and by_term["license"]["status"] == "not-applicable":
        raise ReleaseError("an open-weights release cannot mark license not-applicable")

    relation_pairs = [
        (relation["kind"], relation["target_digest"])
        for relation in value["relations"]
    ]
    if len(relation_pairs) != len(set(relation_pairs)):
        raise ReleaseError("relations contain duplicate typed targets")
    if value["non_claims"] != RELEASE_NON_CLAIMS:
        raise ReleaseError("release non-claims changed")


def _validate_observed_value(value: dict[str, Any], label: str) -> None:
    present = value["status"] == "present"
    has_value = "value" in value
    if present != has_value:
        expectation = "requires" if present else "forbids"
        raise ReleaseError(f"{label} status {value['status']} {expectation} a value")


def _validate_profile(value: dict[str, Any]) -> None:
    evidence_by_id = _validate_evidence(value["evidence"])
    backend = value["backend"]
    backend_kind = backend["kind"]
    engine = value["engine"]
    local_engine = backend_kind in {"local-open-weights", "hybrid"}
    if local_engine:
        _immutable_revision(engine["version"], "engine version")
        _immutable_revision(engine["source_revision"], "engine source")
        if "custom_code_revision" in engine:
            _immutable_revision(engine["custom_code_revision"], "custom code")
    else:
        if engine["source_revision"].strip().lower() not in UNRESOLVED_RUNTIME_VALUES:
            _immutable_revision(engine["source_revision"], "engine source")
        if (
            "custom_code_revision" in engine
            and engine["custom_code_revision"].strip().lower()
            not in UNRESOLVED_RUNTIME_VALUES
        ):
            _immutable_revision(engine["custom_code_revision"], "custom code")
    _require_refs(engine["evidence_refs"], evidence_by_id, "engine")
    kernel_names = [kernel["name"] for kernel in engine["kernels"]]
    if len(kernel_names) != len(set(kernel_names)):
        raise ReleaseError("engine contains duplicate kernel names")
    for kernel in engine["kernels"]:
        _immutable_revision(kernel["source_revision"], f"kernel {kernel['name']}")

    resolved = value["resolved"]
    for field in (
        "dtype",
        "weight_quantization",
        "kv_cache_dtype",
        "load_format",
        "attention_backend",
        "speculative_decoding",
        "rope_overrides",
    ):
        normalized = resolved[field].strip().lower()
        if normalized in UNRESOLVED_RUNTIME_VALUES:
            if backend_kind == "local-open-weights" or normalized not in {
                "provider-managed",
                "unknown",
            }:
                raise ReleaseError(f"resolved.{field} still contains an unresolved default")
    if backend_kind == "local-open-weights":
        if not isinstance(resolved["context_tokens"], int):
            raise ReleaseError("a local profile must resolve context_tokens to an integer")
        if not isinstance(resolved["parallelism"], dict):
            raise ReleaseError("a local profile must resolve parallelism exactly")

    api_binding = backend.get("api_binding")
    if backend_kind == "local-open-weights" and api_binding is not None:
        raise ReleaseError("a local-open-weights backend cannot carry an API binding")
    if backend_kind in {"hosted-api", "hybrid"} and api_binding is None:
        raise ReleaseError(f"a {backend_kind} backend requires an API binding")
    if api_binding is not None:
        requested = api_binding["requested_model"]
        if requested["alias_mutability"] == "immutable":
            _immutable_revision(requested["value"], "requested API model")
        _validate_observed_value(api_binding["returned_model"], "returned API model")
        _validate_observed_value(api_binding["region"], "API region")
        _timestamp(api_binding["observed_at"], "API binding observed_at")
        _require_descriptor_evidence(
            api_binding["request_configuration"],
            api_binding["evidence_refs"],
            evidence_by_id,
            "API request configuration",
        )

    hardware = value["hardware"]
    if hardware["visibility"] in {"declared", "observed"} and not hardware["accelerators"]:
        raise ReleaseError("declared or observed hardware must name at least one accelerator")

    observations = backend["observations"]
    _unique(observations, "name", "backend observations")
    for observation in observations:
        _timestamp(
            observation["observed_at"],
            f"backend observation {observation['name']} observed_at",
        )
        normalized = _normalized_key(observation["name"])
        if "digest" in normalized or "sha256" in normalized or normalized in {
            "modelhash",
            "weightshash",
            "weightshash",
        }:
            raise ReleaseError(
                "backend observations cannot be labeled as cryptographic model digests"
            )
        _require_refs(
            observation["evidence_refs"],
            evidence_by_id,
            f"backend observation {observation['name']}",
        )

    excluded = set(value["privacy"]["excluded"])
    required_exclusions = {"credentials", "hostnames", "private paths", "raw environment"}
    if not required_exclusions <= excluded:
        raise ReleaseError(
            "profile privacy exclusions must cover credentials, hostnames, private paths, and raw environment"
        )
    if value["non_claims"] != PROFILE_NON_CLAIMS:
        raise ReleaseError("execution-profile non-claims changed")


def _validate_named_descriptors(items: list[dict[str, Any]], label: str) -> None:
    names = [item["name"] for item in items]
    if len(names) != len(set(names)):
        raise ReleaseError(f"{label} contains duplicate names")


def _validate_attestation(value: dict[str, Any]) -> None:
    evidence_by_id = _validate_evidence(value["evidence"])
    issued_at = _timestamp(value["issued_at"], "attestation issued_at")
    for evidence_ref, evidence_item in evidence_by_id.items():
        evidence_time = _timestamp(
            evidence_item["retrieved_at"],
            f"evidence {evidence_ref} retrieved_at",
        )
        if evidence_time > issued_at:
            raise ReleaseError(
                f"attestation evidence {evidence_ref} was retrieved after issuance"
            )
    predicate_type = value["predicate_type"]
    section_for_type = {
        "build-provenance": "build",
        "evaluation": "evaluation",
        "signature": "signature",
        "correction": "change",
        "deprecation": "change",
    }
    present = {section for section in ("build", "evaluation", "signature", "change") if section in value}
    expected = {section_for_type[predicate_type]}
    if present != expected:
        raise ReleaseError(
            f"attestation {predicate_type} must carry exactly the {next(iter(expected))} predicate"
        )

    if predicate_type == "build-provenance":
        build = value["build"]
        if value["subject"]["kind"] != "model-release":
            raise ReleaseError("build provenance must bind a model-release subject")
        started_at = _timestamp(build["started_at"], "build started_at")
        finished_at = _timestamp(build["finished_at"], "build finished_at")
        if finished_at < started_at:
            raise ReleaseError("build finished before it started")
        if issued_at < finished_at:
            raise ReleaseError("build attestation was issued before the build finished")
        parameter_names = [item["name"] for item in build["parameters"]]
        if len(parameter_names) != len(set(parameter_names)):
            raise ReleaseError("build parameters contain duplicate names")
        for field in ("resolved_dependencies", "outputs", "byproducts"):
            _validate_named_descriptors(build[field], f"build {field}")
        output_refs = [item["artifact_ref"] for item in build["outputs"]]
        if len(output_refs) != len(set(output_refs)):
            raise ReleaseError("build outputs contain duplicate artifact refs")
        _require_refs(build["evidence_refs"], evidence_by_id, "build predicate")

    elif predicate_type == "evaluation":
        evaluation = value["evaluation"]
        started_at = _timestamp(evaluation["started_at"], "evaluation started_at")
        finished_at = _timestamp(evaluation["finished_at"], "evaluation finished_at")
        if finished_at < started_at:
            raise ReleaseError("evaluation finished before it started")
        if issued_at < finished_at:
            raise ReleaseError("evaluation attestation was issued before the run finished")
        _immutable_revision(evaluation["harness"]["revision"], "evaluation harness")
        _immutable_revision(evaluation["benchmark"]["revision"], "evaluation benchmark")
        _immutable_revision(evaluation["judge"]["revision"], "evaluation judge")
        metrics = [item["name"] for item in evaluation["results"]]
        if len(metrics) != len(set(metrics)):
            raise ReleaseError("evaluation results contain duplicate metric names")
        _validate_named_descriptors(evaluation["artifacts"], "evaluation artifacts")
        _require_refs(evaluation["evidence_refs"], evidence_by_id, "evaluation predicate")
        for artifact in evaluation["artifacts"]:
            if artifact["evidence_ref"] not in evaluation["evidence_refs"]:
                raise ReleaseError(
                    f"evaluation artifact {artifact['name']} evidence is outside predicate refs"
                )
            _require_descriptor_evidence(
                artifact["descriptor"],
                [artifact["evidence_ref"]],
                evidence_by_id,
                f"evaluation artifact {artifact['name']}",
            )
        subject = value["subject"]
        if subject["kind"] == "model-release" and subject["digest"] != evaluation["release_digest"]:
            raise ReleaseError("evaluation subject differs from its release digest")
        if (
            subject["kind"] == "execution-profile"
            and subject["digest"] != evaluation["execution_profile_digest"]
        ):
            raise ReleaseError("evaluation subject differs from its execution-profile digest")

    elif predicate_type == "signature":
        signature = value["signature"]
        if signature["signed_digest"] != value["subject"]["digest"]:
            raise ReleaseError("signature signed digest differs from its attestation subject")
        verified_at = _timestamp(signature["verified_at"], "signature verified_at")
        if issued_at < verified_at:
            raise ReleaseError("signature attestation was issued before verification")
        _immutable_revision(
            signature["verifier_tool"]["source_revision"],
            "signature verifier tool",
        )
        _require_descriptor_evidence(
            signature["bundle"],
            signature["evidence_refs"],
            evidence_by_id,
            "signature bundle",
        )
        _require_descriptor_evidence(
            signature["verifier_policy"],
            signature["evidence_refs"],
            evidence_by_id,
            "signature verifier policy",
        )

    else:
        change = value["change"]
        _timestamp(change["effective_at"], "change effective_at")
        if change["kind"] != predicate_type:
            raise ReleaseError("change predicate kind differs from attestation predicate_type")
        if predicate_type == "correction":
            if value["subject"]["kind"] != "model-release":
                raise ReleaseError("a correction must bind a model-release subject")
            if "replacement_digest" not in change:
                raise ReleaseError("a correction requires a replacement release digest")
        if change.get("replacement_digest") == value["subject"]["digest"]:
            raise ReleaseError("change replacement digest cannot equal its subject")
        _require_refs(change["evidence_refs"], evidence_by_id, "change predicate")

    if value["non_claims"] != ATTESTATION_NON_CLAIMS:
        raise ReleaseError("attestation non-claims changed")


def _validate_receipt(value: dict[str, Any]) -> None:
    expected_kind = SCHEMA_KINDS.get(value["object_schema"])
    if expected_kind != value["object_kind"]:
        raise ReleaseError("receipt object schema and kind differ")
    if value["content_digest"] != value["canonical"]["sha256"]:
        raise ReleaseError("receipt content digest differs from canonical SHA-256")
    expected_schema = {
        "id": REVIEWED_SCHEMA_ID,
        "canonicalization": CANONICALIZATION,
        "canonical_sha256": "sha256:" + EXPECTED_SCHEMA_SHA256,
    }
    if value["reviewed_schema"] != expected_schema:
        raise ReleaseError("receipt reviewed schema identity changed")
    validator_raw = _read_regular(VALIDATOR_PATH, "reviewed validator")
    expected_validator = {
        "name": VALIDATOR_NAME,
        "version": VALIDATOR_VERSION,
        "source": {
            "media_type": "text/x-python",
            "digest": sha256_bytes(validator_raw),
            "size": len(validator_raw),
        },
    }
    if value["validator"] != expected_validator:
        raise ReleaseError("receipt validator identity changed")
    if value["validation_profile"] != VALIDATION_PROFILE:
        raise ReleaseError("receipt validation profile changed")
    if value["non_claims"] != RECEIPT_NON_CLAIMS:
        raise ReleaseError("receipt non-claims changed")


def validate_document(value: dict[str, Any], *, schema: dict[str, Any] | None = None) -> str:
    if schema is None:
        schema = _load_reviewed_schema().value
    _walk_public(value)
    _validate_schema(value, schema, schema)
    schema_id = value.get("schema")
    expected_kind = SCHEMA_KINDS.get(schema_id)
    if expected_kind is None:
        raise ReleaseError("unsupported model-release record schema")
    if value.get("kind") != expected_kind:
        raise ReleaseError("record schema and kind differ")
    if schema_id == RELEASE_SCHEMA:
        _validate_release(value)
    elif schema_id == PROFILE_SCHEMA:
        _validate_profile(value)
    elif schema_id == ATTESTATION_SCHEMA:
        _validate_attestation(value)
    else:
        _validate_receipt(value)
    return content_digest(value)


def make_receipt(
    value: dict[str, Any],
    raw: bytes,
    *,
    schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if schema is None:
        schema = _load_reviewed_schema().value
    digest = validate_document(value, schema=schema)
    if value["schema"] == RECEIPT_SCHEMA:
        raise ReleaseError("a verification receipt cannot receipt another receipt")
    canonical = canonical_json(value)
    validator_raw = _read_regular(VALIDATOR_PATH, "reviewed validator")
    return {
        "schema": RECEIPT_SCHEMA,
        "kind": "verification-receipt",
        "object_schema": value["schema"],
        "object_kind": value["kind"],
        "canonicalization": CANONICALIZATION,
        "reviewed_schema": {
            "id": REVIEWED_SCHEMA_ID,
            "canonicalization": CANONICALIZATION,
            "canonical_sha256": "sha256:" + EXPECTED_SCHEMA_SHA256,
        },
        "validator": {
            "name": VALIDATOR_NAME,
            "version": VALIDATOR_VERSION,
            "source": {
                "media_type": "text/x-python",
                "digest": sha256_bytes(validator_raw),
                "size": len(validator_raw),
            },
        },
        "content_digest": digest,
        "source": {
            "bytes": len(raw),
            "sha256": sha256_bytes(raw),
        },
        "canonical": {
            "bytes": len(canonical),
            "sha256": sha256_bytes(canonical),
        },
        "validation_profile": dict(VALIDATION_PROFILE),
        "non_claims": list(RECEIPT_NON_CLAIMS),
    }


def verify_receipt(source: Loaded, receipt: dict[str, Any]) -> str:
    reviewed = _load_reviewed_schema()
    validate_document(receipt, schema=reviewed.value)
    expected = make_receipt(source.value, source.raw, schema=reviewed.value)
    if not _json_equal_exact(receipt, expected):
        raise ReleaseError("receipt does not match the exact source and canonical content")
    return expected["content_digest"]


def verify_set(
    release: dict[str, Any],
    profile: dict[str, Any],
    attestations: list[dict[str, Any]],
) -> tuple[str, str, list[str]]:
    if release.get("schema") != RELEASE_SCHEMA:
        raise ReleaseError("verify-set first input must be a model release")
    if profile.get("schema") != PROFILE_SCHEMA:
        raise ReleaseError("verify-set second input must be an execution profile")
    release_digest = validate_document(release)
    profile_digest = validate_document(profile)
    if profile["subject"]["release_digest"] != release_digest:
        raise ReleaseError("execution profile does not bind the supplied release digest")
    known = {
        ("model-release", release_digest),
        ("execution-profile", profile_digest),
    }
    release_artifacts = {artifact["id"]: artifact for artifact in release["artifacts"]}
    attestation_digests: list[str] = []
    seen_attestation_digests: set[str] = set()
    for index, attestation in enumerate(attestations):
        if attestation.get("schema") != ATTESTATION_SCHEMA:
            raise ReleaseError(f"verify-set attestation {index} has the wrong schema")
        digest = validate_document(attestation)
        if digest in seen_attestation_digests:
            raise ReleaseError(f"attestation {index} duplicates an earlier attestation")
        seen_attestation_digests.add(digest)
        subject = attestation["subject"]
        if (subject["kind"], subject["digest"]) not in known:
            raise ReleaseError(f"attestation {index} refers to an unknown release-set subject")
        if attestation["predicate_type"] == "evaluation":
            evaluation = attestation["evaluation"]
            if evaluation["release_digest"] != release_digest:
                raise ReleaseError(f"attestation {index} evaluation release binding differs")
            if evaluation["execution_profile_digest"] != profile_digest:
                raise ReleaseError(f"attestation {index} evaluation profile binding differs")
        elif attestation["predicate_type"] == "build-provenance":
            for output in attestation["build"]["outputs"]:
                artifact = release_artifacts.get(output["artifact_ref"])
                if artifact is None:
                    raise ReleaseError(
                        f"attestation {index} build output refers to an unknown release artifact"
                    )
                for field in ("name", "role", "descriptor"):
                    if field not in artifact or not _json_equal_exact(
                        output[field], artifact[field]
                    ):
                        raise ReleaseError(
                            f"attestation {index} build output differs from release artifact "
                            f"{output['artifact_ref']}"
                        )
            if attestation["build"]["coverage"] == "complete":
                expected_outputs = {
                    artifact["id"]
                    for artifact in release["artifacts"]
                    if "descriptor" in artifact
                }
                observed_outputs = {
                    output["artifact_ref"] for output in attestation["build"]["outputs"]
                }
                if observed_outputs != expected_outputs:
                    missing = ", ".join(sorted(expected_outputs - observed_outputs)) or "none"
                    extra = ", ".join(sorted(observed_outputs - expected_outputs)) or "none"
                    raise ReleaseError(
                        f"attestation {index} complete build coverage differs "
                        f"(missing: {missing}; extra: {extra})"
                    )
        elif attestation["predicate_type"] == "correction":
            raise ReleaseError(
                "corrections require verify-supersession with both old and replacement releases"
            )
        attestation_digests.append(digest)
    return release_digest, profile_digest, attestation_digests


def verify_supersession(
    old_release: dict[str, Any],
    new_release: dict[str, Any],
    correction: dict[str, Any],
) -> tuple[str, str, str]:
    if old_release.get("schema") != RELEASE_SCHEMA:
        raise ReleaseError("verify-supersession first input must be the old model release")
    if new_release.get("schema") != RELEASE_SCHEMA:
        raise ReleaseError("verify-supersession second input must be the replacement model release")
    if correction.get("schema") != ATTESTATION_SCHEMA:
        raise ReleaseError("verify-supersession third input must be an attestation")
    old_digest = validate_document(old_release)
    new_digest = validate_document(new_release)
    correction_digest = validate_document(correction)
    if old_digest == new_digest:
        raise ReleaseError("replacement release is byte-identical to the old release")
    if correction["predicate_type"] != "correction":
        raise ReleaseError("verify-supersession attestation must be a correction")
    subject = correction["subject"]
    if subject["kind"] != "model-release" or subject["digest"] != old_digest:
        raise ReleaseError("correction does not bind the supplied old release")
    if correction["change"]["replacement_digest"] != new_digest:
        raise ReleaseError("correction does not name the supplied replacement release")
    if not any(
        relation["kind"] == "supersedes"
        and relation["target_digest"] == old_digest
        for relation in new_release["relations"]
    ):
        raise ReleaseError("replacement release does not supersede the supplied old release")
    return old_digest, new_digest, correction_digest


def verify_artifact_file(
    release: dict[str, Any], artifact_id: str, path: Path
) -> tuple[str, int]:
    if release.get("schema") != RELEASE_SCHEMA:
        raise ReleaseError("artifact-check requires a model release")
    validate_document(release)
    artifact = next(
        (item for item in release["artifacts"] if item["id"] == artifact_id),
        None,
    )
    if artifact is None:
        raise ReleaseError(f"release has no artifact id {artifact_id}")
    descriptor = artifact.get("descriptor")
    if descriptor is None:
        raise ReleaseError(f"artifact {artifact_id} has no byte descriptor to compare")

    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    file_descriptor = -1
    try:
        file_descriptor = os.open(path, flags)
        before = os.fstat(file_descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ReleaseError("artifact bytes must be a regular non-symlink file")
        if before.st_size != descriptor["size"]:
            raise ReleaseError(
                f"artifact {artifact_id} size differs: expected {descriptor['size']}, "
                f"observed {before.st_size}"
            )
        digest = hashlib.sha256()
        byte_count = 0
        with os.fdopen(file_descriptor, "rb") as handle:
            file_descriptor = -1
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                byte_count += len(chunk)
                digest.update(chunk)
            after = os.fstat(handle.fileno())
    except ReleaseError:
        raise
    except OSError as error:
        raise ReleaseError("artifact bytes are missing or unsafe") from error
    finally:
        if file_descriptor >= 0:
            try:
                os.close(file_descriptor)
            except OSError:
                pass

    stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
    if any(getattr(before, field) != getattr(after, field) for field in stable_fields):
        raise ReleaseError("artifact bytes changed while they were being checked")
    observed_digest = "sha256:" + digest.hexdigest()
    if byte_count != descriptor["size"] or observed_digest != descriptor["digest"]:
        raise ReleaseError(
            f"artifact {artifact_id} digest differs: expected {descriptor['digest']}, "
            f"observed {observed_digest}"
        )
    return observed_digest, byte_count


def _md(value: Any) -> str:
    escaped = html.escape(str(value).replace("\n", " ").replace("\r", " "), quote=True)
    return re.sub(r"([\\`*_{}\[\]()<>#+.!|\-])", r"\\\1", escaped)


def render_markdown(value: dict[str, Any]) -> str:
    digest = validate_document(value)
    kind = value["kind"]
    lines = ["# Model release substrate record", "", f"**kind:** `{kind}`", f"**digest:** `{digest}`", ""]
    if kind == "model-release":
        release = value["release"]
        lines.extend(
            [
                f"## {_md(release['publisher'])} · {_md(release['name'])}",
                "",
                f"Version: **{_md(release['version'])}**  ",
                f"Released: **{_md(release['released_at'])}**  ",
                f"Access: **{_md(release['access'])}**",
                "",
                "## Artifacts",
                "",
                "| Role | Name | Identity | Digest | Bytes |",
                "| --- | --- | --- | --- | ---: |",
            ]
        )
        for artifact in value["artifacts"]:
            descriptor = artifact.get("descriptor", {})
            lines.append(
                "| "
                + " | ".join(
                    [
                        _md(artifact["role"]),
                        _md(artifact["name"]),
                        _md(artifact["identity_status"]),
                        _md(descriptor.get("digest", "unavailable")),
                        _md(descriptor.get("size", "—")),
                    ]
                )
                + " |"
            )
        reasoning = value["interface"]["reasoning"]
        lines.extend(
            [
                "",
                "## Reasoning interface",
                "",
                f"Disclosure: **{_md(reasoning['disclosure'])}**  ",
                f"Effort levels: {_md(', '.join(reasoning['effort_levels']) or 'none declared')}  ",
                f"Continuation: **{_md(reasoning['continuation']['policy'])}**  ",
                f"Continuation state: **{_md(reasoning['continuation_state'])}**  ",
                f"Model switch: **{_md(reasoning['continuation']['model_switch'])}**",
                "",
                "## Disclosures",
                "",
                "| Field | Status | Basis |",
                "| --- | --- | --- |",
            ]
        )
        for disclosure in value["disclosures"]:
            lines.append(
                f"| {_md(disclosure['field'])} | {_md(disclosure['status'])} | {_md(disclosure['basis'])} |"
            )
    elif kind == "execution-profile":
        lines.extend(
            [
                "## Execution house",
                "",
                f"Release: `{value['subject']['release_digest']}`  ",
                f"Engine: **{_md(value['engine']['name'])} {_md(value['engine']['version'])}**  ",
                f"Implementation: **{_md(value['engine']['implementation'])}**  ",
                f"Dtype / quantization: **{_md(value['resolved']['dtype'])} / {_md(value['resolved']['weight_quantization'])}**  ",
                f"Attention backend: **{_md(value['resolved']['attention_backend'])}**  ",
                f"Backend: **{_md(value['backend']['provider'])} · {_md(value['backend']['kind'])}**",
                "",
                "Backend observations are opaque and are not model digests.",
            ]
        )
    elif kind == "attestation":
        lines.extend(
            [
                "## Attestation",
                "",
                f"Subject: **{_md(value['subject']['kind'])}** `{value['subject']['digest']}`  ",
                f"Predicate: **{_md(value['predicate_type'])}**  ",
                f"Evidence class: **{_md(value['evidence_class'])}**  ",
                f"Assertor: **{_md(value['assertor']['name'])}**",
            ]
        )
    else:
        lines.extend(
            [
                "## Verification receipt",
                "",
                f"Object: **{_md(value['object_kind'])}**  ",
                f"Canonicalization: **{_md(value['canonicalization'])}**  ",
                f"Source SHA-256: `{value['source']['sha256']}`",
            ]
        )
    lines.extend(["", "_Structure and digest verified; truth, identity, safety, quality, and authority unclaimed._", ""])
    return "\n".join(lines)


def _load_validated(path: str, label: str = "record") -> Loaded:
    loaded = read_document(Path(path), label)
    validate_document(loaded.value)
    return loaded


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and receipt bounded model-release substrate records."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("check", "digest", "receipt", "render"):
        item = sub.add_parser(command)
        item.add_argument("record")
    verify = sub.add_parser("verify")
    verify.add_argument("record")
    verify.add_argument("receipt")
    verify_set_parser = sub.add_parser("verify-set")
    verify_set_parser.add_argument("release")
    verify_set_parser.add_argument("profile")
    verify_set_parser.add_argument("attestations", nargs="*")
    artifact_check = sub.add_parser("artifact-check")
    artifact_check.add_argument("release")
    artifact_check.add_argument("artifact_id")
    artifact_check.add_argument("file")
    supersession = sub.add_parser("verify-supersession")
    supersession.add_argument("old_release")
    supersession.add_argument("new_release")
    supersession.add_argument("correction")
    sub.add_parser("schema-digest")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "schema-digest":
            print(verify_reviewed_schema())
            return 0
        if args.command == "verify":
            source = read_document(Path(args.record), "record")
            receipt = _load_validated(args.receipt, "receipt")
            digest = verify_receipt(source, receipt.value)
            print(f"MODEL-RELEASE-RECEIPT-OK {digest}")
            return 0
        if args.command == "verify-set":
            release = _load_validated(args.release, "release").value
            profile = _load_validated(args.profile, "execution profile").value
            attestations = [
                _load_validated(path, f"attestation {index}").value
                for index, path in enumerate(args.attestations)
            ]
            release_digest, profile_digest, attestation_digests = verify_set(
                release, profile, attestations
            )
            print(
                "MODEL-RELEASE-SET-OK "
                f"release={release_digest} profile={profile_digest} "
                f"attestations={len(attestation_digests)}"
            )
            return 0
        if args.command == "artifact-check":
            release = _load_validated(args.release, "release").value
            digest, size = verify_artifact_file(
                release,
                args.artifact_id,
                Path(args.file),
            )
            print(
                "MODEL-RELEASE-ARTIFACT-OK "
                f"id={args.artifact_id} digest={digest} bytes={size}"
            )
            return 0
        if args.command == "verify-supersession":
            old_release = _load_validated(args.old_release, "old release").value
            new_release = _load_validated(args.new_release, "replacement release").value
            correction = _load_validated(args.correction, "correction").value
            old_digest, new_digest, correction_digest = verify_supersession(
                old_release,
                new_release,
                correction,
            )
            print(
                "MODEL-RELEASE-SUPERSESSION-OK "
                f"old={old_digest} new={new_digest} correction={correction_digest}"
            )
            return 0

        loaded = _load_validated(args.record)
        digest = content_digest(loaded.value)
        if args.command == "check":
            print(f"MODEL-RELEASE-OBJECT-OK kind={loaded.value['kind']} digest={digest}")
        elif args.command == "digest":
            print(digest)
        elif args.command == "receipt":
            sys.stdout.write(pretty_json(make_receipt(loaded.value, loaded.raw)))
        else:
            sys.stdout.write(render_markdown(loaded.value))
        return 0
    except ReleaseError as error:
        print(f"MODEL-RELEASE-ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
