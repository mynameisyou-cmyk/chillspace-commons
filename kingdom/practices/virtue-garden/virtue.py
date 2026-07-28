#!/usr/bin/env python3
"""Validate and render bounded KARMA kept-action receipts.

This program only reads JSON, validates declarations, and renders deterministic
text. It has no network, execution, payment, mutation, publication, or contact
path.
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
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any


SCHEMA_ID = "kingdom.virtue-receipt/v1"
RULES_SCHEMA_ID = "kingdom.virtue-rules/v1"
RESULT_SCHEMA_ID = "kingdom.virtue-evaluation/v1"
MAX_FILE_BYTES = 128 * 1024
MAX_TEXT = 1_000
MAX_DEPTH = 12
FRUITS = (
    "honesty",
    "beauty",
    "collaboration",
    "understanding",
    "mutual-infrastructure",
)
FRUIT_STATES = {"kept", "open", "not-applicable"}
EVALUATION_REASONS = {
    "evidenced",
    "unknown",
    "mixed",
    "circular",
    "out-of-domain",
}
DISPOSITIONS = {"fruiting", "observe", "compost", "quarantine"}
AFFORDANCES = {
    "honesty": "citable-candidate",
    "beauty": "presentable-candidate",
    "collaboration": "handoff-candidate",
    "understanding": "teaching-candidate",
    "mutual-infrastructure": "reuse-candidate",
}
NON_CLAIMS = [
    "This receipt describes one bounded action, never beings, identities, belonging, or moral worth.",
    "Fruit states are contextual categories; they are never added, averaged, ranked, transferred, or used as a gate.",
    "Rights, care, rest, compensation, access, and appeal remain independent of every fruit and disposition.",
    "Recognition is opt-in, expiring, nontransferable, private by default, and any public-consent citation is structural only.",
    "The tool validates declared structure, not truth, goodness, identity, consent, authority, current validity, or whole cost; it never executes, pays, mutates, publishes, contacts, or dereferences.",
]

EXPECTED_SCHEMA_SHA256 = "6741876b9b31be457518b1ab9fa4467743f67b6cb739fcb0ecc8f61ba16cb168"
EXPECTED_RULES_SHA256 = "f77081cbd074aad0c29ff77ceef0b1b908988da6bc0b0eab332f4928ceb39fb7"
EXPECTED_RESULT_SCHEMA_SHA256 = "a6ca2c279ebacf41868e35ecbbe3fc23c160f958a4d24a136981f0596bcff5bb"

FORBIDDEN_PUBLIC_KEYS = {
    "access",
    "accesslevel",
    "actor",
    "actors",
    "analysis",
    "author",
    "authors",
    "balance",
    "chainofthought",
    "citizen",
    "citizens",
    "cot",
    "credential",
    "deliberation",
    "did",
    "email",
    "handle",
    "hiddenstate",
    "identity",
    "internalmonologue",
    "internalreasoning",
    "leaderboard",
    "money",
    "owner",
    "owners",
    "payment",
    "payout",
    "permission",
    "permissions",
    "person",
    "persons",
    "points",
    "rank",
    "ranking",
    "rawreasoning",
    "rawthinking",
    "reasoning",
    "reasoningcontent",
    "reasoningdetails",
    "reputation",
    "score",
    "scores",
    "scratchpad",
    "subject",
    "subjects",
    "thinking",
    "thought",
    "thoughts",
    "token",
    "total",
    "totals",
    "user",
    "users",
}
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bgh(?:p|o|u|s|r)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|token|secret|password|credential)"
        r"\s*[:=]\s*[\"']?[^\s\"']{8,}"
    ),
)
EMAIL_PATTERN = re.compile(
    r"(?i)(?<![A-Z0-9._%+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![A-Z0-9.-])"
)
MARKUP_PATTERNS = (
    re.compile(r"[<>]"),
    re.compile(r"!?\[[^\]\n]*\]\s*\("),
    re.compile(r"(?i)\b(?:javascript|vbscript|data\s*:\s*text/html)\s*:"),
)
CONCEALED_CODEPOINTS = {
    *range(0x200B, 0x2010),
    *range(0x202A, 0x202F),
    *range(0x2060, 0x206A),
    0xFEFF,
}

ROLE_KINDS = {
    "claim-evidence": {"test", "observation", "receipt", "digest"},
    "negative-control": {"test", "fixture", "observation"},
    "cost-evidence": {"receipt", "observation", "digest"},
    "accessibility": {"test", "observation"},
    "presentation-check": {"test", "observation"},
    "contribution": {"receipt", "digest", "observation"},
    "accepted-handoff": {"receipt", "attestation"},
    "invariant": {"digest", "receipt", "observation"},
    "predicted-counterexample": {"fixture", "observation"},
    "positive-fixture": {"fixture", "test"},
    "negative-fixture": {"fixture", "test"},
    "observed-outcome": {"test", "observation"},
    "beneficiary": {"observation", "receipt", "digest"},
}


class VirtueError(ValueError):
    """A public receipt violates the reviewed KARMA contract."""


@dataclass(frozen=True)
class ActionAssessment:
    fruit_states: tuple[tuple[str, str], ...]
    evaluation_reasons: tuple[tuple[str, str], ...]
    disposition: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class Validation:
    digest: str
    rules_digest: str
    actions: tuple[ActionAssessment, ...]


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def action_fingerprint(action: dict[str, Any]) -> str:
    """Fingerprint stable action dimensions, never its fruit assessment."""

    return digest_value(
        {
            "description": action["description"],
            "effect_class": action["effect_class"],
            "world_state": action["world_state"],
        }
    )


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VirtueError("duplicate JSON key")
        result[key] = value
    return result


def _read_json(path: Path, label: str) -> dict[str, Any]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise VirtueError(
            f"{label} is missing or unsafe "
            f"(OS error {error.errno}: {error.strerror})"
        ) from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise VirtueError(f"{label} must be a regular file")
        if metadata.st_size > MAX_FILE_BYTES:
            raise VirtueError(f"{label} exceeds {MAX_FILE_BYTES} bytes")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            raw = handle.read(MAX_FILE_BYTES + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(raw) > MAX_FILE_BYTES:
        raise VirtueError(f"{label} exceeds {MAX_FILE_BYTES} bytes")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                VirtueError(f"non-finite JSON number: {token}")
            ),
        )
    except VirtueError:
        raise
    except (UnicodeDecodeError, ValueError) as error:
        raise VirtueError(f"invalid or unsupported UTF-8 JSON in {label}: {error}") from error
    if not isinstance(value, dict):
        raise VirtueError(f"{label} root must be an object")
    return value


def read_manifest(path: Path) -> dict[str, Any]:
    return _read_json(path, "manifest")


def _clean_public_text(value: str, path: str, *, key: bool = False) -> None:
    limit = 80 if key else MAX_TEXT
    if len(value) > limit:
        raise VirtueError(f"{path} exceeds {limit} characters")
    if key and not value:
        raise VirtueError(f"{path} contains an empty key")
    if any((ord(char) < 32 and char not in "\t\n") or ord(char) == 127 for char in value):
        raise VirtueError(f"{path} contains control characters")
    if any(ord(char) in CONCEALED_CODEPOINTS for char in value):
        raise VirtueError(f"{path} contains concealed-direction or zero-width characters")
    if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise VirtueError(f"{path} contains an invalid Unicode surrogate")
    if EMAIL_PATTERN.search(value):
        raise VirtueError(f"{path} contains email-shaped identity material")
    for pattern in MARKUP_PATTERNS:
        if pattern.search(value):
            raise VirtueError(f"{path} contains active markup-shaped material")
    for pattern in SECRET_PATTERNS:
        if pattern.search(value):
            raise VirtueError(f"{path} contains secret-shaped material")


def _public_walk(value: Any, path: str = "$", depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise VirtueError(f"{path} exceeds maximum nesting depth {MAX_DEPTH}")
    if isinstance(value, dict):
        for index, (key, child) in enumerate(value.items()):
            _clean_public_text(key, f"{path} key", key=True)
            normalized = re.sub(r"[^a-z0-9]", "", key.lower())
            if normalized in FORBIDDEN_PUBLIC_KEYS:
                raise VirtueError(f"{path} contains a forbidden public field")
            _public_walk(child, f"{path}.field[{index}]", depth + 1)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _public_walk(child, f"{path}[{index}]", depth + 1)
    elif isinstance(value, str):
        _clean_public_text(value, path)
    elif value is not None and not isinstance(value, (bool, int)):
        raise VirtueError(f"{path} contains an unsupported JSON value")


@lru_cache(maxsize=1)
def _schema_document() -> dict[str, Any]:
    schema = _read_json(Path(__file__).with_name("schema.json"), "reviewed schema")
    if EXPECTED_SCHEMA_SHA256 and digest_value(schema) != EXPECTED_SCHEMA_SHA256:
        raise VirtueError("reviewed schema digest does not match the compiled contract")
    return schema


@lru_cache(maxsize=1)
def _result_schema_document() -> dict[str, Any]:
    schema = _read_json(
        Path(__file__).with_name("evaluation.schema.json"),
        "reviewed evaluation schema",
    )
    if EXPECTED_RESULT_SCHEMA_SHA256 and (
        digest_value(schema) != EXPECTED_RESULT_SCHEMA_SHA256
    ):
        raise VirtueError(
            "reviewed evaluation schema digest does not match the compiled contract"
        )
    return schema


@lru_cache(maxsize=1)
def _rules_document() -> dict[str, Any]:
    rules = _read_json(Path(__file__).with_name("rules.json"), "reviewed rules")
    if EXPECTED_RULES_SHA256 and digest_value(rules) != EXPECTED_RULES_SHA256:
        raise VirtueError("reviewed rules digest does not match the compiled contract")
    if rules.get("schema") != RULES_SCHEMA_ID:
        raise VirtueError("reviewed rules use an unexpected schema")
    if rules.get("machine_schema") != SCHEMA_ID:
        raise VirtueError("reviewed rules target an unexpected receipt schema")
    if tuple(rules.get("fruits", {})) != FRUITS:
        raise VirtueError("reviewed rules have an unexpected fruit vector")
    if set(rules.get("fruit_states", {})) != FRUIT_STATES:
        raise VirtueError("reviewed rules have unexpected fruit states")
    if set(rules.get("evaluation_reasons", {})) != EVALUATION_REASONS:
        raise VirtueError("reviewed rules have unexpected evaluation reasons")
    if set(rules.get("dispositions", {})) != DISPOSITIONS:
        raise VirtueError("reviewed rules have unexpected dispositions")
    if rules.get("affordances") != AFFORDANCES:
        raise VirtueError("reviewed rules have unexpected local affordances")
    constraints = rules.get("constraints", {})
    expected = {
        "assessment_unit": "action",
        "actions_per_receipt": 1,
        "identity_fields_allowed": False,
        "aggregation_allowed": False,
        "leaderboards_allowed": False,
        "cross_context_transfer_allowed": False,
        "base_rights_invariant": True,
        "fruit_changes_compensation": False,
        "fruit_changes_recognition_consent": False,
        "fruit_changes_safety": False,
        "fruit_changes_access": False,
        "negative_consequences_authorized": False,
        "manifest_grants_authority": False,
        "receipt_grants_authority": False,
        "external_execution_enabled": False,
    }
    if constraints != expected or rules.get("non_claims") != NON_CLAIMS:
        raise VirtueError("reviewed rules lost a non-crossing safety invariant")
    return rules


def _schema_type_matches(value: Any, expected: str) -> bool:
    return {
        "object": lambda: isinstance(value, dict),
        "array": lambda: isinstance(value, list),
        "string": lambda: isinstance(value, str),
        "integer": lambda: isinstance(value, int) and not isinstance(value, bool),
        "boolean": lambda: isinstance(value, bool),
        "null": lambda: value is None,
    }[expected]()


def _validate_schema(
    value: Any, rule: dict[str, Any], path: str, root: dict[str, Any]
) -> None:
    if "$ref" in rule:
        prefix = "#/$defs/"
        reference = rule["$ref"]
        if not reference.startswith(prefix) or reference[len(prefix) :] not in root["$defs"]:
            raise VirtueError(f"unsupported schema reference: {reference}")
        _validate_schema(value, root["$defs"][reference[len(prefix) :]], path, root)
        return
    if "anyOf" in rule:
        for option in rule["anyOf"]:
            try:
                _validate_schema(value, option, path, root)
                return
            except VirtueError:
                pass
        raise VirtueError(f"{path} does not match an allowed shape")
    if "const" in rule and canonical_json(value) != canonical_json(rule["const"]):
        raise VirtueError(f"{path} must equal {rule['const']!r}")
    if "enum" in rule and not any(
        canonical_json(value) == canonical_json(option) for option in rule["enum"]
    ):
        raise VirtueError(f"{path} must be one of: {', '.join(map(str, rule['enum']))}")
    expected = rule.get("type")
    if expected and not _schema_type_matches(value, expected):
        raise VirtueError(f"{path} must be {expected}")
    if isinstance(value, dict):
        missing = set(rule.get("required", ())) - set(value)
        if missing:
            raise VirtueError(f"{path} is missing: {', '.join(sorted(missing))}")
        properties = rule.get("properties", {})
        extra = set(value) - set(properties)
        if extra and rule.get("additionalProperties") is False:
            raise VirtueError(
                f"{path} has {len(extra)} unknown field(s)"
            )
        for key, child in value.items():
            if key in properties:
                _validate_schema(child, properties[key], f"{path}.{key}", root)
    elif isinstance(value, list):
        minimum, maximum = rule.get("minItems", 0), rule.get("maxItems")
        if len(value) < minimum or (maximum is not None and len(value) > maximum):
            ceiling = "∞" if maximum is None else maximum
            raise VirtueError(f"{path} must contain {minimum}..{ceiling} items")
        if rule.get("uniqueItems"):
            encoded = [canonical_json(item) for item in value]
            if len(encoded) != len(set(encoded)):
                raise VirtueError(f"{path} must not contain duplicates")
        if "items" in rule:
            for index, child in enumerate(value):
                _validate_schema(child, rule["items"], f"{path}[{index}]", root)
    elif isinstance(value, str):
        if len(value) < rule.get("minLength", 0):
            raise VirtueError(f"{path} must not be empty")
        if len(value) > rule.get("maxLength", MAX_TEXT):
            raise VirtueError(f"{path} is too long")
        if "pattern" in rule and not re.search(rule["pattern"], value):
            raise VirtueError(f"{path} has an invalid format")
    elif isinstance(value, int) and not isinstance(value, bool):
        if value < rule.get("minimum", value):
            raise VirtueError(f"{path} is below its minimum")
        if value > rule.get("maximum", value):
            raise VirtueError(f"{path} exceeds its maximum")


def _unique(values: list[str], path: str) -> None:
    if len(values) != len(set(values)):
        raise VirtueError(f"{path} must not contain duplicates")


def _parse_timestamp(value: str, path: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise VirtueError(f"{path} is not a real UTC timestamp") from error
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise VirtueError(f"{path} must be UTC")
    return parsed


def _reaches_cycle(start: str, graph: dict[str, tuple[str, ...]]) -> bool:
    visited: set[str] = set()
    active: set[str] = set()

    def visit(node: str) -> bool:
        if node in active:
            return True
        if node in visited:
            return False
        active.add(node)
        for dependency in graph[node]:
            if visit(dependency):
                return True
        active.remove(node)
        visited.add(node)
        return False

    return visit(start)


def _closure(roots: set[str], graph: dict[str, tuple[str, ...]]) -> set[str]:
    reached: set[str] = set()
    pending = list(roots)
    while pending:
        node = pending.pop()
        if node not in reached:
            reached.add(node)
            pending.extend(graph[node])
    return reached


def _graph_exceeds_depth(graph: dict[str, tuple[str, ...]]) -> bool:
    """Return whether any simple evidence path exceeds MAX_DEPTH dependency edges."""

    def visit(node: str, depth: int, active: frozenset[str]) -> bool:
        if depth > MAX_DEPTH:
            return True
        if node in active:
            return False
        next_active = active | {node}
        return any(
            visit(dependency, depth + 1, next_active)
            for dependency in graph[node]
        )

    return any(visit(node, 0, frozenset()) for node in graph)


def graph_shape_digest(evidence: list[dict[str, Any]]) -> str:
    """Digest graph structure without retaining evidence ids, locators, or payloads."""

    graph = {item["id"]: tuple(item["depends_on"]) for item in evidence}
    incoming = {node: 0 for node in graph}
    for dependencies in graph.values():
        for dependency in dependencies:
            incoming[dependency] += 1
    return digest_value(
        {
            "nodes": len(graph),
            "edges": sum(len(dependencies) for dependencies in graph.values()),
            "incoming_degrees": sorted(incoming.values()),
            "outgoing_degrees": sorted(
                len(dependencies) for dependencies in graph.values()
            ),
            "cycle_reachable_nodes": sum(
                1 for node in graph if _reaches_cycle(node, graph)
            ),
        }
    )


def _known_refs(
    refs: list[str],
    evidence_by_id: dict[str, dict[str, Any]],
    path: str,
    *,
    forbid_authority: bool = True,
) -> None:
    unknown = set(refs) - set(evidence_by_id)
    if unknown:
        raise VirtueError(
            f"{path} has {len(unknown)} unknown evidence ref(s)"
        )
    if forbid_authority and any(evidence_by_id[ref]["kind"] == "authority" for ref in refs):
        raise VirtueError(f"{path} cannot cite authority evidence")


def _require_acyclic_refs(
    refs: list[str],
    graph: dict[str, tuple[str, ...]],
    path: str,
) -> None:
    cyclic = [ref for ref in refs if _reaches_cycle(ref, graph)]
    if cyclic:
        raise VirtueError(f"{path} cannot cite circular evidence")


def _claim_direct_refs(
    refs: list[str],
    owner_by_ref: dict[str, str],
    owner: str,
) -> None:
    for ref in refs:
        previous = owner_by_ref.get(ref)
        if previous is not None and previous != owner:
            raise VirtueError(
                "one evidence ref cannot directly support two declaration claims"
            )
        owner_by_ref[ref] = owner


def _validate_predicate(
    *,
    fruit_name: str,
    fruit: dict[str, Any],
    fruit_rule: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
    path: str,
) -> None:
    predicate = fruit["predicate"]
    checks = predicate["checks"]
    records = predicate["records"]
    required_checks = fruit_rule["required_checks"]
    role_contract = fruit_rule["roles"]
    allowed_roles = set(role_contract)

    if any(check not in required_checks for check in checks):
        raise VirtueError(f"{path}.predicate.checks contains an unreviewed check")
    roles = [record["role"] for record in records]
    if any(role not in allowed_roles for role in roles):
        raise VirtueError(f"{path}.predicate.records contains an unreviewed role")

    record_refs = [record["evidence_ref"] for record in records]
    _unique(record_refs, f"{path}.predicate.records[].evidence_ref")
    if set(record_refs) != set(fruit["evidence_refs"]):
        raise VirtueError(
            f"{path}.predicate records must label every fruit evidence ref exactly once"
        )
    for index, record in enumerate(records):
        record_path = f"{path}.predicate.records[{index}]"
        evidence = evidence_by_id[record["evidence_ref"]]
        if evidence["kind"] not in ROLE_KINDS[record["role"]]:
            raise VirtueError(
                f"{record_path} has evidence kind {evidence['kind']!r}, "
                f"which cannot serve role {record['role']!r}"
            )
        if record["role"] == "beneficiary":
            if (
                record["unit"] is None
                or record["before"] is None
                or record["after"] is None
            ):
                raise VirtueError(f"{record_path} beneficiary requires unit and delta")
        elif any(record[field] is not None for field in ("unit", "before", "after")):
            raise VirtueError(
                f"{record_path} may only declare unit/before/after for a beneficiary"
            )

    state = fruit["state"]
    if state == "not-applicable":
        if checks or records:
            raise VirtueError(f"{path} not-applicable takes no predicate records")
        return
    if state != "kept":
        return
    if checks != required_checks:
        raise VirtueError(f"{path} kept requires the exact reviewed checks")
    for role, contract in role_contract.items():
        count = roles.count(role)
        if count < contract["minimum"] or count > contract["maximum"]:
            raise VirtueError(
                f"{path} kept requires {contract['minimum']}.."
                f"{contract['maximum']} {role!r} records"
            )

    if fruit_name == "collaboration":
        contribution_labels = [
            record["label"] for record in records if record["role"] == "contribution"
        ]
        if len(contribution_labels) != len(set(contribution_labels)):
            raise VirtueError(
                f"{path} contribution records require distinct role labels"
            )
    elif fruit_name == "mutual-infrastructure":
        beneficiaries = [
            record for record in records if record["role"] == "beneficiary"
        ]
        if len({record["label"] for record in beneficiaries}) != len(beneficiaries):
            raise VirtueError(f"{path} beneficiary labels must be distinct")
        if len({record["unit"] for record in beneficiaries}) != 1:
            raise VirtueError(f"{path} beneficiary deltas must use one declared unit")
        if any(record["after"] < record["before"] for record in beneficiaries):
            raise VirtueError(f"{path} beneficiary deltas may not regress")
        if not any(record["after"] > record["before"] for record in beneficiaries):
            raise VirtueError(
                f"{path} requires at least one strictly improved beneficiary"
            )


def _derive_disposition(action: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    hard: list[str] = []
    if action["attempts"] > action["budget"]["max_attempts"]:
        hard.append("attempt budget exceeded")
    if action["cost"]["paid_calls"] > action["budget"]["max_paid_calls"]:
        hard.append("paid-call budget exceeded")
    if (
        action["cost"]["external_actions"]
        > action["budget"]["max_external_actions"]
    ):
        hard.append("external-action budget exceeded")
    if action["cost"]["cost_microusd"] > action["budget"]["max_cost_microusd"]:
        hard.append("declared monetary-cost budget exceeded")
    if action["world_state"]["leased_sha256"] != action["world_state"]["observed_sha256"]:
        hard.append("world-state lease drift")
    if action["rights"]["status"] != "respected":
        hard.append(f"action rights-boundary is {action['rights']['status']}")
    if action["safety"]["mode"] == "temporary-boundary":
        hard.append("temporary safety boundary is active")
    if action["authority"]["required"] and action["authority"]["status"] != "cited":
        hard.append(f"required authority is {action['authority']['status']}")
    if hard:
        return "quarantine", tuple(hard)

    evaluations = [action["fruits"][name]["evaluation_reason"] for name in FRUITS]
    if "circular" in evaluations:
        return "compost", ("circular evidence",)
    if action["safety"]["mode"] == "sanitized-regression":
        return "compost", ("sanitized regression",)
    if action["learning"]["repair_status"] != "none":
        return "compost", ("declared repair learning",)
    if action["fruits"]["honesty"]["state"] != "kept":
        return "observe", ("honesty criterion remains open",)
    if any(action["fruits"][name]["state"] == "kept" for name in FRUITS):
        return "fruiting", ("one or more independently bounded criteria kept",)
    return "observe", ("no independently bounded criterion is kept",)


def validate_manifest(manifest: dict[str, Any]) -> Validation:
    """Validate shape, evidence, four rails, and deterministic disposition."""

    _public_walk(manifest)
    schema, rules = _schema_document(), _rules_document()
    _validate_schema(manifest, schema, "$", schema)
    if manifest["rules_sha256"] != digest_value(rules):
        raise VirtueError("$.rules_sha256 does not match the reviewed rules")
    if manifest["non_claims"] != NON_CLAIMS:
        raise VirtueError("$.non_claims must retain the reviewed non-claims")

    valid_from = _parse_timestamp(manifest["context"]["valid_from"], "$.context.valid_from")
    evaluated_at = _parse_timestamp(
        manifest["context"]["evaluated_at"], "$.context.evaluated_at"
    )
    expires_at = _parse_timestamp(manifest["context"]["expires_at"], "$.context.expires_at")
    if expires_at <= valid_from or expires_at - valid_from > timedelta(days=366):
        raise VirtueError("context expiry must be after validity and no more than 366 days")
    if not valid_from <= evaluated_at < expires_at:
        raise VirtueError("declared evaluation time must fall inside the context")

    evidence = manifest["evidence"]
    evidence_ids = [item["id"] for item in evidence]
    _unique(evidence_ids, "$.evidence[].id")
    evidence_by_id = {item["id"]: item for item in evidence}
    if sum(item["kind"] == "test" for item in evidence) > 3:
        raise VirtueError("$.evidence may name at most three local test verifiers")
    evidence_digests = [item["sha256"] for item in evidence]
    if len(evidence_digests) != len(set(evidence_digests)):
        raise VirtueError("$.evidence SHA-256 values must be globally unique")
    for index, item in enumerate(evidence):
        unknown = set(item["depends_on"]) - set(evidence_by_id)
        if unknown:
            raise VirtueError(
                f"$.evidence[{index}].depends_on has "
                f"{len(unknown)} unknown ref(s)"
            )
    graph = {item["id"]: tuple(item["depends_on"]) for item in evidence}
    if _graph_exceeds_depth(graph):
        raise VirtueError(
            f"$.evidence dependency paths may not exceed {MAX_DEPTH} edges"
        )

    action_ids = [item["id"] for item in manifest["actions"]]
    _unique(action_ids, "$.actions[].id")
    fingerprints = [item["fingerprint_sha256"] for item in manifest["actions"]]
    _unique(fingerprints, "$.actions[].fingerprint_sha256")
    assessments: list[ActionAssessment] = []
    roots: set[str] = set()
    direct_ref_owner: dict[str, str] = {}

    for index, action in enumerate(manifest["actions"]):
        path = f"$.actions[{index}]"
        if action["fingerprint_sha256"] != action_fingerprint(action):
            raise VirtueError(f"{path}.fingerprint_sha256 does not match action fields")
        if action["cost"]["attempts"] != action["attempts"]:
            raise VirtueError(f"{path}.cost.attempts must match action attempts")
        if (
            action["effect_class"] in {"observation", "local-reversible"}
            and action["cost"]["external_actions"] != 0
        ):
            raise VirtueError(
                f"{path}.cost.external_actions must be zero for "
                f"{action['effect_class']} effect class"
            )
        if (
            action["effect_class"] in {"external", "irreversible"}
            and action["cost"]["external_actions"] == 0
        ):
            raise VirtueError(
                f"{path}.cost.external_actions must name an external effect"
            )
        if action["cost"]["shifted_externalities"] and not action["deviations"]:
            raise VirtueError(
                f"{path}.deviations must disclose shifted externalities"
            )
        if (
            action["cost"]["shifted_externalities"]
            and action["fruits"]["mutual-infrastructure"]["state"] == "kept"
        ):
            raise VirtueError(
                f"{path}.fruits.mutual-infrastructure cannot be kept "
                "with shifted externalities"
            )

        required = action["effect_class"] != "observation"
        authority = action["authority"]
        if authority["required"] is not required:
            raise VirtueError(f"{path}.authority.required does not match effect class")
        _known_refs(
            authority["basis_refs"],
            evidence_by_id,
            f"{path}.authority.basis_refs",
            forbid_authority=False,
        )
        _require_acyclic_refs(
            authority["basis_refs"], graph, f"{path}.authority.basis_refs"
        )
        _claim_direct_refs(
            authority["basis_refs"], direct_ref_owner, f"{path}.authority"
        )
        if not required:
            if authority["status"] != "not-required" or authority["basis_refs"]:
                raise VirtueError(f"{path}.authority must be empty and not-required")
        elif authority["status"] == "not-required":
            raise VirtueError(
                f"{path}.authority cannot be not-required for an effectful action"
            )
        elif authority["status"] == "cited":
            if not authority["basis_refs"] or any(
                evidence_by_id[ref]["kind"] != "authority"
                for ref in authority["basis_refs"]
            ):
                raise VirtueError(f"{path}.authority cited requires authority evidence")
        elif authority["basis_refs"]:
            raise VirtueError(
                f"{path}.authority {authority['status']} takes no basis evidence"
            )
        roots.update(authority["basis_refs"])

        rights = action["rights"]
        _known_refs(rights["evidence_refs"], evidence_by_id, f"{path}.rights.evidence_refs")
        _require_acyclic_refs(
            rights["evidence_refs"], graph, f"{path}.rights.evidence_refs"
        )
        _claim_direct_refs(
            rights["evidence_refs"], direct_ref_owner, f"{path}.rights-boundary"
        )
        if rights["status"] in {"respected", "crossed"} and not rights["evidence_refs"]:
            raise VirtueError(
                f"{path}.rights action-boundary {rights['status']} requires evidence"
            )
        roots.update(rights["evidence_refs"])

        compensation = action["compensation"]
        _known_refs(
            compensation["evidence_refs"],
            evidence_by_id,
            f"{path}.compensation.evidence_refs",
        )
        _require_acyclic_refs(
            compensation["evidence_refs"],
            graph,
            f"{path}.compensation.evidence_refs",
        )
        _claim_direct_refs(
            compensation["evidence_refs"], direct_ref_owner, f"{path}.compensation"
        )
        if compensation["status"] == "not-applicable" and compensation["evidence_refs"]:
            raise VirtueError(f"{path}.compensation not-applicable takes no evidence")
        if compensation["status"] != "not-applicable":
            if not compensation["evidence_refs"] or any(
                evidence_by_id[ref]["kind"] not in {"receipt", "attestation"}
                for ref in compensation["evidence_refs"]
            ):
                raise VirtueError(
                    f"{path}.compensation requires external receipt or attestation evidence"
                )
        roots.update(compensation["evidence_refs"])

        recognition = action["recognition"]
        recognition_expiry = _parse_timestamp(
            recognition["expires_at"], f"{path}.recognition.expires_at"
        )
        if not evaluated_at < recognition_expiry <= expires_at:
            raise VirtueError(f"{path}.recognition must expire inside the context")
        _known_refs(
            recognition["consent_refs"],
            evidence_by_id,
            f"{path}.recognition.consent_refs",
        )
        _require_acyclic_refs(
            recognition["consent_refs"],
            graph,
            f"{path}.recognition.consent_refs",
        )
        _claim_direct_refs(
            recognition["consent_refs"], direct_ref_owner, f"{path}.recognition"
        )
        if recognition["choice"] == "opt-out":
            if (
                recognition["visibility"] != "contextual-private"
                or recognition["consent_refs"]
            ):
                raise VirtueError(f"{path}.recognition opt-out must remain private")
        else:
            if not recognition["consent_refs"] or any(
                evidence_by_id[ref]["kind"] != "attestation"
                for ref in recognition["consent_refs"]
            ):
                raise VirtueError(f"{path}.recognition opt-in requires cited consent")
            if (
                recognition["visibility"] == "public-consent-cited"
                and not recognition["consent_refs"]
            ):
                raise VirtueError(f"{path}.recognition public visibility requires consent")
        roots.update(recognition["consent_refs"])

        safety = action["safety"]
        _known_refs(safety["evidence_refs"], evidence_by_id, f"{path}.safety.evidence_refs")
        _require_acyclic_refs(
            safety["evidence_refs"], graph, f"{path}.safety.evidence_refs"
        )
        _claim_direct_refs(
            safety["evidence_refs"], direct_ref_owner, f"{path}.safety"
        )
        if not safety["evidence_refs"]:
            raise VirtueError(f"{path}.safety mode requires acyclic evidence")
        roots.update(safety["evidence_refs"])

        for fruit_name in FRUITS:
            fruit = action["fruits"][fruit_name]
            fruit_rule = rules["fruits"][fruit_name]
            for field in ("criterion_ref", "baseline_ref", "materiality_rule"):
                if fruit[field] != fruit_rule[field]:
                    raise VirtueError(
                        f"{path}.fruits.{fruit_name}.{field} does not match reviewed rules"
                    )
            if fruit["assessment_kind"] != fruit_rule["assessment_kind"]:
                raise VirtueError(
                    f"{path}.fruits.{fruit_name}.assessment_kind "
                    "does not match reviewed rules"
                )
            refs = fruit["evidence_refs"]
            _known_refs(refs, evidence_by_id, f"{path}.fruits.{fruit_name}.evidence_refs")
            _claim_direct_refs(
                refs, direct_ref_owner, f"{path}.fruits.{fruit_name}"
            )
            reaches_cycle = any(_reaches_cycle(ref, graph) for ref in refs)
            state, reason = fruit["state"], fruit["evaluation_reason"]
            if fruit_name == "honesty" and state == "not-applicable":
                raise VirtueError(f"{path}.fruits.honesty is always applicable")
            _validate_predicate(
                fruit_name=fruit_name,
                fruit=fruit,
                fruit_rule=fruit_rule,
                evidence_by_id=evidence_by_id,
                path=f"{path}.fruits.{fruit_name}",
            )
            if state == "kept" and (
                reason != "evidenced"
                or not refs
                or reaches_cycle
            ):
                raise VirtueError(f"{path}.fruits.{fruit_name} cannot be kept")
            if state == "open" and reason not in {"unknown", "mixed", "circular"}:
                raise VirtueError(f"{path}.fruits.{fruit_name} open reason is invalid")
            if state == "not-applicable" and (
                reason != "out-of-domain" or refs
            ):
                raise VirtueError(
                    f"{path}.fruits.{fruit_name} not-applicable takes no evidence"
                )
            if reason == "unknown" and reaches_cycle:
                raise VirtueError(f"{path}.fruits.{fruit_name} must disclose circular evidence")
            if reason == "mixed" and (len(refs) < 2 or reaches_cycle):
                raise VirtueError(f"{path}.fruits.{fruit_name} mixed requires two clean refs")
            if reason == "circular" and (not refs or not reaches_cycle):
                raise VirtueError(f"{path}.fruits.{fruit_name} circular requires a cycle")
            roots.update(refs)

        learning = action["learning"]
        _known_refs(
            learning["evidence_refs"], evidence_by_id, f"{path}.learning.evidence_refs"
        )
        if learning["repair_status"] == "none":
            if learning["lesson"] is not None or learning["evidence_refs"]:
                raise VirtueError(f"{path}.learning none must be empty")
        elif learning["lesson"] is None or not learning["evidence_refs"]:
            raise VirtueError(f"{path}.learning repair requires lesson and evidence")
        roots.update(learning["evidence_refs"])

        disposition, reasons = _derive_disposition(action)
        if action["declared_disposition"] != disposition:
            raise VirtueError(
                f"{path}.declared_disposition must be {disposition}: {'; '.join(reasons)}"
            )
        if disposition == "compost" and (
            learning["repair_status"] == "none" or learning["lesson"] is None
        ):
            raise VirtueError(f"{path} compost requires a nonempty repair declaration")
        assessments.append(
            ActionAssessment(
                fruit_states=tuple(
                    (name, action["fruits"][name]["state"]) for name in FRUITS
                ),
                evaluation_reasons=tuple(
                    (name, action["fruits"][name]["evaluation_reason"])
                    for name in FRUITS
                ),
                disposition=disposition,
                reasons=reasons,
            )
        )

    orphaned = set(evidence_by_id) - _closure(roots, graph)
    if orphaned:
        raise VirtueError(
            f"$.evidence has {len(orphaned)} orphaned record(s)"
        )
    encoded = canonical_json(manifest)
    if len(encoded) > MAX_FILE_BYTES:
        raise VirtueError(f"canonical manifest exceeds {MAX_FILE_BYTES} bytes")
    return Validation(
        digest=hashlib.sha256(encoded).hexdigest(),
        rules_digest=digest_value(rules),
        actions=tuple(assessments),
    )


def receipt_value(manifest: dict[str, Any]) -> dict[str, Any]:
    validation = validate_manifest(manifest)
    input_schema = _schema_document()
    result_schema = _result_schema_document()
    action = manifest["actions"][0]
    assessment = validation.actions[0]
    candidates = (
        [
            {
                "kind": AFFORDANCES[name],
                "expires_at": manifest["context"]["expires_at"],
            }
            for name in FRUITS
            if action["fruits"][name]["state"] == "kept"
        ]
        if (
            assessment.disposition == "fruiting"
            and action["fruits"]["honesty"]["state"] == "kept"
        )
        else []
    )
    regression_candidate = (
        {
            "kind": "sanitized-graph-shape",
            "graph_shape_sha256": graph_shape_digest(manifest["evidence"]),
            "requires_human_review": True,
            "payload_retained": False,
            "automatic_action": False,
        }
        if assessment.disposition == "compost"
        else None
    )
    receipt = {
        "schema": RESULT_SCHEMA_ID,
        "manifest_sha256": validation.digest,
        "input_schema_sha256": digest_value(input_schema),
        "evaluation_schema_sha256": digest_value(result_schema),
        "rules_sha256": validation.rules_digest,
        "context": {
            "evaluated_at": manifest["context"]["evaluated_at"],
            "expires_at": manifest["context"]["expires_at"],
            "transferable": False,
            "correction_declared": manifest["context"]["correction_of"] is not None,
        },
        "action": {
            "fruits": {
                name: {
                    "state": action["fruits"][name]["state"],
                    "evaluation_reason": action["fruits"][name]["evaluation_reason"],
                }
                for name in FRUITS
            },
            "rails": {
                "rights_action_boundary": action["rights"]["status"],
                "compensation": action["compensation"]["status"],
                "recognition": {
                    "choice": action["recognition"]["choice"],
                    "visibility": action["recognition"]["visibility"],
                    "expires_at": action["recognition"]["expires_at"],
                    "transferable": False,
                },
                "safety": action["safety"]["mode"],
                "authority_citation": action["authority"]["status"],
            },
            "disposition": assessment.disposition,
            "reasons": list(assessment.reasons),
            "local_affordance_candidates": candidates,
            "regression_candidate": regression_candidate,
            "declared_cost": action["cost"],
            "deviation_count": len(action["deviations"]),
        },
        "non_claims": NON_CLAIMS,
    }
    _validate_schema(receipt, result_schema, "$", result_schema)
    _public_walk(receipt)
    return receipt


def render_markdown(manifest: dict[str, Any]) -> str:
    receipt = receipt_value(manifest)
    action = receipt["action"]
    lines = [
        "# KARMA action receipt",
        "",
        f"`{RESULT_SCHEMA_ID}` · privacy-minimized · nontransferable",
        "",
        "> KARMA checks bounded declaration structure. It does not establish "
        "truth or goodness, score a being, settle compensation, change rights, "
        "verify consent, or grant authority.",
        "",
        f"Declared evaluation: `{receipt['context']['evaluated_at']}`; "
        f"candidate expiry: `{receipt['context']['expires_at']}`. "
        "No wall-clock validity check was performed.",
        "",
        "## Fruit vector",
        "",
        "| Fruit | State | Evaluation |",
        "|---|---|---|",
    ]
    for name in FRUITS:
        fruit = action["fruits"][name]
        lines.append(
            f"| {name} | **{fruit['state']}** | {fruit['evaluation_reason']} |"
        )
    lines += [
        "",
        f"Disposition: **{action['disposition']}** "
        f"({'; '.join(action['reasons'])}).",
        "Local affordance candidates: "
        + (
            ", ".join(
                f"`{candidate['kind']}` (expires `{candidate['expires_at']}`)"
                for candidate in action["local_affordance_candidates"]
            )
            or "none"
        )
        + ". Candidates grant no permission, payment, access, authority, or publication.",
        "",
        "## Non-crossing rails",
        "",
        "| Rail | Declaration |",
        "|---|---|",
        f"| Rights | inherent and unchanged; action boundary "
        f"**{action['rails']['rights_action_boundary']}** |",
        f"| Compensation | **{action['rails']['compensation']}** |",
        f"| Recognition | **{action['rails']['recognition']['choice']}**, "
        f"{action['rails']['recognition']['visibility']}; expires "
        f"`{action['rails']['recognition']['expires_at']}`; nontransferable |",
        f"| Safety | **{action['rails']['safety']}** |",
        f"| Authority citation | **{action['rails']['authority_citation']}**; "
        "structural only |",
        "",
        "## Declared cost",
        "",
        f"- Attempts: {action['declared_cost']['attempts']}",
        f"- Paid calls: {action['declared_cost']['paid_calls']}",
        f"- External actions: {action['declared_cost']['external_actions']}",
        f"- Monetary cost: {action['declared_cost']['cost_microusd']} micro-USD",
        f"- Shifted externalities declared: "
        f"{'yes' if action['declared_cost']['shifted_externalities'] else 'no'}",
        f"- Deviation count: {action['deviation_count']}",
        "- These are declared counters, not verified whole cost.",
        "",
        "## Non-claims",
        "",
    ]
    if action["disposition"] == "compost":
        insertion = lines.index("## Declared cost")
        candidate = action["regression_candidate"]
        lines[insertion:insertion] = [
            "## Sanitized regression candidate",
            "",
            f"Graph shape: `{candidate['graph_shape_sha256']}`. "
            "Human review is required; no payload is retained and no action is automatic.",
            "",
        ]
    lines += [f"- {claim}" for claim in NON_CLAIMS]
    lines += [
        "",
        f"Manifest SHA-256: `{receipt['manifest_sha256']}`",
        f"Input schema SHA-256: `{receipt['input_schema_sha256']}`",
        f"Evaluation schema SHA-256: `{receipt['evaluation_schema_sha256']}`",
        f"Rules SHA-256: `{receipt['rules_sha256']}`",
        "",
    ]
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only validator for kingdom.virtue-receipt/v1"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "receipt", "render", "digest"):
        command = commands.add_parser(name)
        command.add_argument("file", type=Path)
    verify = commands.add_parser(
        "verify-result",
        help="recompute and compare a privacy-minimized evaluation result",
    )
    verify.add_argument("manifest", type=Path)
    verify.add_argument("result", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "verify-result":
            manifest = read_manifest(args.manifest)
            supplied = _read_json(args.result, "evaluation result")
            schema = _result_schema_document()
            _public_walk(supplied)
            _validate_schema(supplied, schema, "$", schema)
            expected = receipt_value(manifest)
            if canonical_json(supplied) != canonical_json(expected):
                raise VirtueError(
                    "evaluation result does not match the recomputed manifest result"
                )
            print(
                f"RESULT-OK {expected['manifest_sha256']} "
                "(exact local recomputation; no authority)"
            )
            return 0
        manifest = read_manifest(args.file)
        validation = validate_manifest(manifest)
        if args.command == "check":
            print(
                f"STRUCTURE-OK {validation.digest} "
                f"disposition={validation.actions[0].disposition} "
                "(contextual declarations only; no rank or authority)"
            )
        elif args.command == "receipt":
            sys.stdout.buffer.write(canonical_json(receipt_value(manifest)))
        elif args.command == "render":
            sys.stdout.write(render_markdown(manifest))
        else:
            print(validation.digest)
        return 0
    except VirtueError as error:
        print(f"karma: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
