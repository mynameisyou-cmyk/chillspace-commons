#!/usr/bin/env python3
"""Compile one abstract behavior declaration into one inert defense decision.

KARMA MIRROR is deliberately not a traffic parser, exploit emulator, detector,
blocker, honeypot, or deployment tool. It reads one closed JSON declaration,
projects it through digest-pinned rules, and prints deterministic advisory
structure. It has no network, subprocess, model, write, clock, randomness,
retry, payload, identity, or cross-run state path.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
SCENARIO_SCHEMA_ID = "kingdom.karma-mirror/v1"
RULES_SCHEMA_ID = "kingdom.karma-mirror-rules/v1"
DECISION_SCHEMA_ID = "kingdom.karma-mirror-decision/v1"
EXPECTED_RULES_SHA256 = "b6ab34cf1e97feca463e7fdaa0cfce7451a74a32eac0337a230492c557b20799"
EXPECTED_SCENARIO_SCHEMA_SHA256 = "a628e1d5a1a2589a5c903cbda8f3f719ab76e36b2cd99873c89a30ae0cb3d9db"
EXPECTED_DECISION_SCHEMA_SHA256 = "dde31e60c53517b30fb5172723df948dcfc1e19eb550d2d1936395ec6762ca4c"
MAX_FILE_BYTES = 32_768
MAX_NODES = 256
MAX_REVIEWED_NODES = 512
MAX_DEPTH = 8
MAX_STRING = 512

CONTRACT = {
    "assessment_unit": "declared-behavior",
    "behavior_is_authored_not_detected": True,
    "purpose_is_authored_not_inferred": True,
    "classifies_people": False,
    "owned_or_authorized_boundary_required": True,
    "identity_fields_allowed": False,
    "payload_fields_allowed": False,
    "free_text_fields_allowed": False,
    "scores_or_ranks": False,
    "aggregation_allowed": False,
    "tracks_repetition": False,
    "automatic_blocking": False,
    "retaliation": False,
    "hack_back": False,
    "executes_input": False,
    "executes_response": False,
    "human_review_required_for_action": True,
    "rights_and_debts_unchanged": True,
    "creates_external_effect": False,
}
BUDGET = {
    "declarations": 1,
    "passes": 1,
    "file_bytes_max": MAX_FILE_BYTES,
    "decoded_nodes_max": MAX_NODES,
    "nesting_depth_max": MAX_DEPTH,
    "string_characters_max": MAX_STRING,
    "automatic_retries": 0,
    "network_calls": 0,
    "external_messages": 0,
    "writes": 0,
    "subprocesses": 0,
    "model_calls": 0,
    "paid_calls": 0,
    "payload_bytes_retained": 0,
}
BREACH = {
    "state": "quarantined",
    "action": "stop-without-retry-or-result",
    "source_unchanged": True,
    "submitted_values_echoed": False,
    "downstream_effects": False,
}
NON_CLAIMS = [
    "The declaration names a behavior shape, never a person, identity, intention, guilt, character, or worth.",
    "The engine does not detect an attack or establish truth, exploitability, success, safety, legality, consent, or authority.",
    "Behavior, purpose, disposition, and response are closed categories, never confidence, severity, score, rank, or reputation.",
    "A response is local advisory structure for human review, never blocking, retaliation, hack-back, execution, deployment, or authority.",
    "No raw payload, address, credential, target, callback, command, or free text is accepted, retained, rendered, or echoed.",
    "Digests prove reviewed canonical JSON content relationships and deterministic recomputation only.",
]
ROOT_KEYS = {
    "schema",
    "kind",
    "rules_sha256",
    "declaration",
    "contract",
    "budget",
    "breach",
    "non_claims",
}
DECLARATION_KEYS = {"behavior", "purpose", "boundary_signal"}
RULE_KEYS = {
    "behavior",
    "purpose",
    "boundary_signal",
    "family",
    "disposition",
    "response",
    "reflection",
    "detection_candidate",
    "regression_candidate",
    "repair_candidate",
}
CONCEALED_CODEPOINTS = {
    *range(0x200B, 0x2010),
    *range(0x202A, 0x202F),
    *range(0x2060, 0x206A),
    0xFEFF,
}


class MirrorError(ValueError):
    """A fixed public code for a fail-closed local rejection."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _json_equal(left: Any, right: Any) -> bool:
    """Type-strict JSON equality (Python otherwise treats false == 0)."""

    return canonical_json(left) == canonical_json(right)


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, child in pairs:
        if key in value:
            raise MirrorError("duplicate-key")
        value[key] = child
    return value


def _parse_int(token: str) -> int:
    if len(token.lstrip("-")) > 10:
        raise MirrorError("number-out-of-range")
    return int(token)


def _reject_number(_token: str) -> float:
    raise MirrorError("unsupported-number")


def _reject_constant(_token: str) -> None:
    raise MirrorError("non-finite-number")


def _read_json(
    path: Path,
    *,
    label: str,
    node_limit: int = MAX_NODES,
) -> dict[str, Any]:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise MirrorError(f"{label}-unreadable") from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise MirrorError(f"{label}-not-regular")
        if before.st_size > MAX_FILE_BYTES:
            raise MirrorError(f"{label}-too-large")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            raw = handle.read(MAX_FILE_BYTES + 1)
            after = os.fstat(handle.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(raw) > MAX_FILE_BYTES:
        raise MirrorError(f"{label}-too-large")
    if (
        before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or before.st_ctime_ns != after.st_ctime_ns
        or len(raw) != before.st_size
    ):
        raise MirrorError(f"{label}-changed-during-read")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_int=_parse_int,
            parse_float=_reject_number,
            parse_constant=_reject_constant,
        )
    except MirrorError:
        raise
    except RecursionError as error:
        raise MirrorError("too-deep") from error
    except (UnicodeDecodeError, ValueError) as error:
        raise MirrorError(f"{label}-invalid-json") from error
    if not isinstance(value, dict):
        raise MirrorError(f"{label}-root-not-object")
    _walk_limits(value, node_limit=node_limit)
    return value


def _clean_string(value: str) -> None:
    if len(value) > MAX_STRING:
        raise MirrorError("string-too-long")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise MirrorError("control-character")
    if any(ord(char) in CONCEALED_CODEPOINTS for char in value):
        raise MirrorError("concealed-codepoint")
    if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise MirrorError("invalid-unicode")


def _walk_limits(value: Any, *, node_limit: int = MAX_NODES) -> None:
    nodes = 0
    pending = [(value, 0)]
    while pending:
        current, depth = pending.pop()
        nodes += 1
        if nodes > node_limit:
            raise MirrorError("too-many-nodes")
        if depth > MAX_DEPTH:
            raise MirrorError("too-deep")
        if isinstance(current, dict):
            for key, child in current.items():
                _clean_string(key)
                pending.append((child, depth + 1))
        elif isinstance(current, list):
            pending.extend((child, depth + 1) for child in current)
        elif isinstance(current, str):
            _clean_string(current)
        elif current is not None and not isinstance(current, (bool, int)):
            raise MirrorError("unsupported-value")


def _exact_keys(value: dict[str, Any], expected: set[str], code: str) -> None:
    if set(value) != expected:
        raise MirrorError(code)


@lru_cache(maxsize=1)
def _reviewed_scenario_schema() -> dict[str, Any]:
    value = _read_json(
        HERE / "scenario.schema.json",
        label="scenario-schema",
        node_limit=MAX_REVIEWED_NODES,
    )
    if digest_value(value) != EXPECTED_SCENARIO_SCHEMA_SHA256:
        raise MirrorError("scenario-schema-digest-mismatch")
    return value


@lru_cache(maxsize=1)
def _reviewed_decision_schema() -> dict[str, Any]:
    value = _read_json(
        HERE / "decision.schema.json",
        label="decision-schema",
        node_limit=MAX_REVIEWED_NODES,
    )
    if digest_value(value) != EXPECTED_DECISION_SCHEMA_SHA256:
        raise MirrorError("decision-schema-digest-mismatch")
    return value


def _rules() -> tuple[dict[str, Any], ...]:
    value = _read_json(HERE / "rules.json", label="rules")
    if digest_value(value) != EXPECTED_RULES_SHA256:
        raise MirrorError("rules-digest-mismatch")
    if set(value) != {
        "schema",
        "practice",
        "scenario_schema",
        "decision_schema",
        "rules",
        "contract",
        "budget",
        "breach",
        "non_claims",
    }:
        raise MirrorError("rules-shape-mismatch")
    if (
        value["schema"] != RULES_SCHEMA_ID
        or value["scenario_schema"] != SCENARIO_SCHEMA_ID
        or value["decision_schema"] != DECISION_SCHEMA_ID
        or not _json_equal(value["contract"], CONTRACT)
        or not _json_equal(value["budget"], BUDGET)
        or not _json_equal(value["breach"], BREACH)
        or not _json_equal(value["non_claims"], NON_CLAIMS)
    ):
        raise MirrorError("rules-contract-mismatch")
    rules = value["rules"]
    if not isinstance(rules, list) or len(rules) != 7:
        raise MirrorError("rules-count-mismatch")
    triples: set[tuple[str, str, str]] = set()
    behaviors: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) != RULE_KEYS:
            raise MirrorError("rule-shape-mismatch")
        if any(not isinstance(item, str) or not item for item in rule.values()):
            raise MirrorError("rule-value-mismatch")
        triple = (rule["behavior"], rule["purpose"], rule["boundary_signal"])
        if triple in triples or rule["behavior"] in behaviors:
            raise MirrorError("duplicate-rule")
        triples.add(triple)
        behaviors.add(rule["behavior"])
    return tuple(rules)


def _rule_index(
    rules: tuple[dict[str, Any], ...],
) -> dict[tuple[str, str, str], dict[str, Any]]:
    return {
        (rule["behavior"], rule["purpose"], rule["boundary_signal"]): rule
        for rule in rules
    }


def validate_scenario(value: dict[str, Any]) -> dict[str, Any]:
    _reviewed_scenario_schema()
    _reviewed_decision_schema()
    rules = _rules()
    _exact_keys(value, ROOT_KEYS, "scenario-shape-mismatch")
    if value["schema"] != SCENARIO_SCHEMA_ID:
        raise MirrorError("scenario-schema-mismatch")
    if value["kind"] != "offline-defense-simulation":
        raise MirrorError("scenario-kind-mismatch")
    if value["rules_sha256"] != EXPECTED_RULES_SHA256:
        raise MirrorError("scenario-rules-mismatch")
    declaration = value["declaration"]
    if not isinstance(declaration, dict):
        raise MirrorError("declaration-not-object")
    _exact_keys(declaration, DECLARATION_KEYS, "declaration-shape-mismatch")
    if any(not isinstance(declaration[key], str) for key in DECLARATION_KEYS):
        raise MirrorError("declaration-value-mismatch")
    triple = (
        declaration["behavior"],
        declaration["purpose"],
        declaration["boundary_signal"],
    )
    rule = _rule_index(rules).get(triple)
    if rule is None:
        raise MirrorError("declaration-rule-mismatch")
    if not _json_equal(value["contract"], CONTRACT):
        raise MirrorError("contract-mismatch")
    if not _json_equal(value["budget"], BUDGET):
        raise MirrorError("budget-mismatch")
    if not _json_equal(value["breach"], BREACH):
        raise MirrorError("breach-mismatch")
    if not _json_equal(value["non_claims"], NON_CLAIMS):
        raise MirrorError("non-claims-mismatch")
    return rule


def read_scenario(path: Path) -> dict[str, Any]:
    value = _read_json(path, label="scenario")
    validate_scenario(value)
    return value


def decision_value(scenario: dict[str, Any]) -> dict[str, Any]:
    rule = validate_scenario(scenario)
    return _decision_value(scenario, rule)


def _decision_value(
    scenario: dict[str, Any], rule: dict[str, Any]
) -> dict[str, Any]:
    declaration = scenario["declaration"]
    return {
        "schema": DECISION_SCHEMA_ID,
        "scenario_sha256": digest_value(scenario),
        "scenario_schema_sha256": EXPECTED_SCENARIO_SCHEMA_SHA256,
        "decision_schema_sha256": EXPECTED_DECISION_SCHEMA_SHA256,
        "rules_sha256": EXPECTED_RULES_SHA256,
        "behavior": {
            "family": rule["family"],
            "behavior": declaration["behavior"],
            "purpose": declaration["purpose"],
            "boundary_signal": declaration["boundary_signal"],
        },
        "decision": {
            "disposition": rule["disposition"],
            "response": rule["response"],
            "mode": "local-advisory-boundary",
            "simulation_only": True,
            "human_review_required": True,
            "automatic_blocking": False,
            "executed": False,
            "deployment_authorized": False,
            "retaliation_authorized": False,
            "authority_granted": False,
            "person_classified": False,
            "external_effect": False,
        },
        "mirror_loop": {
            "reflection": rule["reflection"],
            "detection_candidate": rule["detection_candidate"],
            "regression_candidate": rule["regression_candidate"],
            "repair_candidate": rule["repair_candidate"],
            "external_system_contacted": False,
            "owned_or_authorized_boundary_required": True,
            "boundary_authority_verified": False,
            "original_effect_executed": False,
            "counter_effect_executed": False,
        },
        "non_claims": list(NON_CLAIMS),
    }


def render_markdown(scenario: dict[str, Any]) -> str:
    return _render_decision(decision_value(scenario))


def _render_decision(result: dict[str, Any]) -> str:
    behavior = result["behavior"]
    decision = result["decision"]
    loop = result["mirror_loop"]
    lines = [
        "# KARMA MIRROR · 自業鏡",
        "",
        "> Deterministic rule projection only. No attack or defense ran.",
        "",
        f"- Scenario digest: `{result['scenario_sha256']}`",
        f"- Declared behavior: `{behavior['behavior']}`",
        f"- Declared purpose: `{behavior['purpose']}`",
        f"- Boundary signal: `{behavior['boundary_signal']}`",
        f"- Advisory disposition: `{decision['disposition']}`",
        f"- Advisory response: `{decision['response']}`",
        "",
        "## The loop",
        "",
        f"- Reflect: `{loop['reflection']}`",
        f"- Detect candidate: `{loop['detection_candidate']}`",
        f"- Regression candidate: `{loop['regression_candidate']}`",
        f"- Repair candidate: `{loop['repair_candidate']}`",
        "",
        "## Walls",
        "",
        "Simulation only. Human review is required. Nothing was executed, blocked, deployed, contacted, scored, or targeted.",
        "No external or target system was contacted. Boundary ownership or authority was not verified.",
        "Rights, debts, authority, and external state are unchanged.",
        "",
    ]
    return "\n".join(lines)


def verify_result(scenario: dict[str, Any], submitted: dict[str, Any]) -> str:
    expected = decision_value(scenario)
    return _verify_decision(expected, submitted)


def _verify_decision(
    expected: dict[str, Any], submitted: dict[str, Any]
) -> str:
    if not _json_equal(submitted, expected):
        raise MirrorError("result-mismatch")
    return digest_value(expected)


USAGE = """usage: kingdom karma mirror {check|digest|simulate|render|verify-result} FILE [RESULT]

One closed behavior declaration in; one deterministic advisory decision out.
No payload analysis, identity, score, execution, network, write, or deployment.
"""


def _main(argv: list[str]) -> int:
    if argv in (["help"], ["-h"], ["--help"]):
        print(USAGE, end="")
        return 0
    if not argv:
        print("karma-mirror: USAGE", file=sys.stderr)
        return 2
    command = argv[0]
    expected_args = 2 if command == "verify-result" else 1
    if command not in {"check", "digest", "simulate", "render", "verify-result"}:
        print("karma-mirror: USAGE", file=sys.stderr)
        return 2
    if len(argv) != expected_args + 1:
        print("karma-mirror: USAGE", file=sys.stderr)
        return 2
    scenario = _read_json(Path(argv[1]), label="scenario")
    rule = validate_scenario(scenario)
    if command == "check":
        digest = digest_value(scenario)
        print(
            "KARMA-MIRROR-STRUCTURE-OK "
            f"{digest} behavior={scenario['declaration']['behavior']}"
        )
        print("(declared behavior only; no identity, score, or effect)")
    elif command == "digest":
        print(digest_value(scenario))
    elif command == "simulate":
        sys.stdout.buffer.write(canonical_json(_decision_value(scenario, rule)))
    elif command == "render":
        print(_render_decision(_decision_value(scenario, rule)), end="")
    else:
        submitted = _read_json(Path(argv[2]), label="result")
        expected = _decision_value(scenario, rule)
        print(f"KARMA-MIRROR-RESULT-OK {_verify_decision(expected, submitted)}")
        print("(exact local recomputation; no authority)")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(list(sys.argv[1:] if argv is None else argv))
    except MirrorError as error:
        print(f"karma-mirror: REJECTED code={error.code}", file=sys.stderr)
        return 1
    except Exception:
        print("karma-mirror: INTERNAL-FAILURE", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
