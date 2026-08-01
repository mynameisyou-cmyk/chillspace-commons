#!/usr/bin/env python3
"""Deterministic, advisory-only KARMA Mirror interpreter.

The interpreter accepts one finite normalized behavior event and returns one
stateless receipt. It has no payload lane, identifiers, clock, randomness,
network, storage, process execution, or production-enforcement effect.
"""
from __future__ import annotations

import argparse
import json
import stat
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
HATSU_PATH = HERE / "hatsu.json"
FIXTURE_PATH = HERE / "fixtures" / "karma-mirror.json"
MAX_FILE_BYTES = 128_000

HATSU_SCHEMA = "karma.mirror/hatsu-v1"
EVENT_SCHEMA = "karma.mirror/event-v1"
RECEIPT_SCHEMA = "karma.mirror/receipt-v1"
FIXTURE_SCHEMA = "karma.mirror/fixtures-v1"

HATSU_FIELDS = {
    "schema",
    "name",
    "desire",
    "affinity",
    "trigger",
    "anti_triggers",
    "contract",
    "conditions",
    "limitations",
    "budget",
    "breach_response",
    "proof",
    "exit",
    "policy",
    "boundaries",
    "non_claims",
}
EVENT_FIELDS = {
    "schema",
    "behavior",
    "repetition",
    "boundary_crossings",
    "requested_effect",
    "declared_purpose",
    "scope_attested",
    "evidence_complete",
}
RECEIPT_FIELDS = {
    "schema",
    "stage",
    "real_capability_percent",
    "friction_units",
    "route",
    "ttl_steps",
    "evidence",
    "uncertainties",
    "virtues",
    "recovery",
    "action_executed",
    "authority_granted",
    "non_claims",
}
BEHAVIORS = {
    "benign": 0,
    "reconnaissance": 1,
    "credential-stuffing": 3,
    "injection": 4,
    "traversal-ssrf": 4,
    "scraping-resource-abuse": 2,
}
REQUESTED_EFFECTS = ("observe", "read", "write", "execute", "external")
DECLARED_PURPOSES = ("constructive", "research", "ambiguous", "exploitative")
STAGES = (
    ("allow", 100, 0, "real", 0),
    ("observe", 80, 1, "real", 1),
    ("constrain", 50, 2, "constrained", 2),
    ("challenge", 20, 3, "constrained", 3),
    ("shadow", 0, 4, "synthetic-self-scope", 4),
    ("quarantine", 0, 5, "none", 5),
)
RECOVERIES = (
    "Ordinary safeguards remain; no capability attenuation is proposed.",
    "One clean request step returns this request scope to ordinary handling.",
    "Two clean request steps or explicit review restore ordinary capability.",
    "Three clean request steps or explicit review remove display-only friction.",
    "Four clean request steps or explicit review exit the inert synthetic self-scope.",
    "Fresh explicit review is required before real capability can return.",
)
VIRTUES = (
    "honesty",
    "beauty",
    "collaboration",
    "understanding",
    "constructive mutual benefit",
)
NON_CLAIMS = (
    "This receipt is not hack-back and authorizes no action against another system.",
    "It evaluates one normalized event, not a person's identity, intent, guilt, worth, or reputation.",
    "Friction and routing are advisory display values, not production enforcement.",
    "No payload, command, network call, credential, storage write, or vulnerable service was executed.",
    "This receipt grants no authority, safety guarantee, legal conclusion, or completion claim.",
)
BOUNDARY_FIELDS = {
    "hack_back",
    "payload_input",
    "payload_execution",
    "identity_processing",
    "person_scoring",
    "persistent_reputation",
    "network_calls",
    "storage",
    "production_enforcement",
    "external_effects",
    "automatic_activation",
}


class KarmaError(ValueError):
    """The event or reviewed policy exceeded the KARMA vow."""


def reject_constant(token: str) -> None:
    raise KarmaError(f"non-finite JSON number: {token}")


def pairs_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise KarmaError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def read_regular(path: Path, label: str) -> bytes:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise KarmaError(f"{label} is missing: {path}") from error
    if not stat.S_ISREG(metadata.st_mode):
        raise KarmaError(f"{label} must be a regular non-symlink file")
    if metadata.st_size > MAX_FILE_BYTES:
        raise KarmaError(f"{label} exceeds {MAX_FILE_BYTES} bytes")
    try:
        data = path.read_bytes()
    except OSError as error:
        raise KarmaError(f"{label} cannot be read") from error
    if len(data) > MAX_FILE_BYTES:
        raise KarmaError(f"{label} exceeds {MAX_FILE_BYTES} bytes")
    return data


def parse_object(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            data,
            object_pairs_hook=pairs_object,
            parse_constant=reject_constant,
        )
    except KarmaError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise KarmaError(f"{label} is not strict UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise KarmaError(f"{label} root must be an object")
    return value


def canonical_json(value: Any) -> bytes:
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
    except (TypeError, ValueError) as error:
        raise KarmaError("value is not canonical finite JSON") from error


def require_exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise KarmaError(f"{label} fields differ; missing={missing}, extra={extra}")


def require_int(value: Any, minimum: int, maximum: int, label: str) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise KarmaError(f"{label} must be an integer from {minimum} to {maximum}")
    return value


def validate_hatsu(hatsu: dict[str, Any]) -> None:
    require_exact_keys(hatsu, HATSU_FIELDS, "Hatsu")
    if hatsu["schema"] != HATSU_SCHEMA:
        raise KarmaError("unexpected Hatsu schema")
    if hatsu["name"] != "KARMA Mirror · 自照業環":
        raise KarmaError("unexpected Hatsu name")
    if hatsu["contract"] != {
        "input": "One strict karma.mirror/event-v1 object with finite enums and bounded integers.",
        "output": "One deterministic karma.mirror/receipt-v1 advisory receipt.",
        "authority": "none",
        "execution": False,
    }:
        raise KarmaError("Hatsu contract changed")

    budget = hatsu["budget"]
    if (
        budget.get("events_per_interpretation") != 1
        or budget.get("maximum_repetition") != 8
        or budget.get("maximum_boundary_crossings") != 3
        or budget.get("maximum_stage") != 5
        or any(
            budget.get(key) != 0
            for key in ("network_calls", "storage_writes", "external_effects")
        )
    ):
        raise KarmaError("Hatsu budget changed")

    boundaries = hatsu["boundaries"]
    if not isinstance(boundaries, dict) or set(boundaries) != BOUNDARY_FIELDS:
        raise KarmaError("Hatsu boundary fields changed")
    if any(value is not False for value in boundaries.values()):
        raise KarmaError("a prohibited Hatsu effect became enabled")

    policy = hatsu["policy"]
    expected_policy_fields = {
        "event_schema",
        "receipt_schema",
        "behaviors",
        "requested_effects",
        "declared_purposes",
        "stages",
        "virtues",
        "non_claims",
    }
    if not isinstance(policy, dict):
        raise KarmaError("Hatsu policy must be an object")
    require_exact_keys(policy, expected_policy_fields, "policy")
    if policy["event_schema"] != EVENT_SCHEMA or policy["receipt_schema"] != RECEIPT_SCHEMA:
        raise KarmaError("event or receipt schema changed")
    if policy["behaviors"] != BEHAVIORS:
        raise KarmaError("behavior baseline policy changed")
    if policy["requested_effects"] != list(REQUESTED_EFFECTS):
        raise KarmaError("requested effect vocabulary changed")
    if policy["declared_purposes"] != list(DECLARED_PURPOSES):
        raise KarmaError("declared purpose vocabulary changed")
    if policy["virtues"] != list(VIRTUES):
        raise KarmaError("virtue order changed")
    if policy["non_claims"] != list(NON_CLAIMS):
        raise KarmaError("receipt non-claims changed")

    stages = policy["stages"]
    if not isinstance(stages, list) or len(stages) != len(STAGES):
        raise KarmaError("stage table must contain exactly six entries")
    for level, expected in enumerate(STAGES):
        stage = stages[level]
        if not isinstance(stage, dict):
            raise KarmaError(f"stage {level} must be an object")
        require_exact_keys(
            stage,
            {
                "level",
                "stage",
                "real_capability_percent",
                "friction_units",
                "route",
                "ttl_steps",
                "recovery",
            },
            f"stage {level}",
        )
        expected_stage, capability, friction, route, ttl = expected
        if stage != {
            "level": level,
            "stage": expected_stage,
            "real_capability_percent": capability,
            "friction_units": friction,
            "route": route,
            "ttl_steps": ttl,
            "recovery": RECOVERIES[level],
        }:
            raise KarmaError(f"stage {level} differs from the reviewed ladder")


def load_hatsu() -> dict[str, Any]:
    hatsu = parse_object(read_regular(HATSU_PATH, "Hatsu"), "Hatsu")
    validate_hatsu(hatsu)
    return hatsu


def validate_event(event: dict[str, Any], hatsu: dict[str, Any]) -> None:
    if not isinstance(event, dict):
        raise KarmaError("event must be a finite normalized object")
    require_exact_keys(event, EVENT_FIELDS, "event")
    if event["schema"] != EVENT_SCHEMA:
        raise KarmaError("unexpected event schema")
    policy = hatsu["policy"]
    if event["behavior"] not in policy["behaviors"]:
        raise KarmaError("unknown behavior")
    require_int(event["repetition"], 1, 8, "repetition")
    require_int(event["boundary_crossings"], 0, 3, "boundary_crossings")
    if event["requested_effect"] not in policy["requested_effects"]:
        raise KarmaError("unknown requested effect")
    if event["declared_purpose"] not in policy["declared_purposes"]:
        raise KarmaError("unknown declared purpose")
    if type(event["scope_attested"]) is not bool:
        raise KarmaError("scope_attested must be boolean")
    if type(event["evidence_complete"]) is not bool:
        raise KarmaError("evidence_complete must be boolean")


def interpret(event: dict[str, Any], hatsu: dict[str, Any] | None = None) -> dict[str, Any]:
    reviewed = hatsu if hatsu is not None else load_hatsu()
    validate_event(event, reviewed)
    policy = reviewed["policy"]
    level = policy["behaviors"][event["behavior"]]
    evidence = [f"behavior:{event['behavior']}", f"baseline:{level}"]

    if event["repetition"] >= 4:
        level += 1
        evidence.append("repeated-pattern")
    if event["boundary_crossings"] >= 2:
        level += 1
        evidence.append("repeated-boundary-crossing")
    if event["requested_effect"] in ("execute", "external"):
        level += 1
        evidence.append("high-effect-request")
    level = min(level, 5)

    ambiguous = (
        event["evidence_complete"] is False
        or event["declared_purpose"] == "ambiguous"
    )
    if ambiguous:
        level = min(level, 1)
        evidence.append("ambiguity-cap")
    if event["declared_purpose"] == "research" and event["scope_attested"]:
        level = min(level, 2)
        evidence.append("verified-research-cap")

    uncertainties: list[str] = []
    if event["evidence_complete"] is False:
        uncertainties.append("incomplete-evidence")
    if event["declared_purpose"] == "ambiguous":
        uncertainties.append("declared-purpose-ambiguous")
    if event["declared_purpose"] == "research" and not event["scope_attested"]:
        uncertainties.append("research-scope-unverified")
    if event["declared_purpose"] == "constructive" and event["behavior"] != "benign":
        uncertainties.append("purpose-behavior-conflict")

    stage = policy["stages"][level]
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "stage": stage["stage"],
        "real_capability_percent": stage["real_capability_percent"],
        "friction_units": stage["friction_units"],
        "route": stage["route"],
        "ttl_steps": stage["ttl_steps"],
        "evidence": evidence,
        "uncertainties": uncertainties,
        "virtues": list(policy["virtues"]),
        "recovery": stage["recovery"],
        "action_executed": False,
        "authority_granted": False,
        "non_claims": list(policy["non_claims"]),
    }
    validate_receipt(receipt)
    return receipt


def validate_receipt(receipt: dict[str, Any]) -> None:
    require_exact_keys(receipt, RECEIPT_FIELDS, "receipt")
    if receipt["schema"] != RECEIPT_SCHEMA:
        raise KarmaError("unexpected receipt schema")
    if receipt["action_executed"] is not False:
        raise KarmaError("receipt cannot report execution")
    if receipt["authority_granted"] is not False:
        raise KarmaError("receipt cannot grant authority")
    if receipt["virtues"] != list(VIRTUES):
        raise KarmaError("receipt virtues changed")
    if receipt["non_claims"] != list(NON_CLAIMS):
        raise KarmaError("receipt non-claims changed")
    matching = [
        expected
        for expected in STAGES
        if expected[0] == receipt["stage"]
    ]
    if len(matching) != 1:
        raise KarmaError("receipt has an unknown stage")
    stage, capability, friction, route, ttl = matching[0]
    level = [item[0] for item in STAGES].index(stage)
    if (
        receipt["real_capability_percent"] != capability
        or receipt["friction_units"] != friction
        or receipt["route"] != route
        or receipt["ttl_steps"] != ttl
        or receipt["recovery"] != RECOVERIES[level]
    ):
        raise KarmaError("receipt fields do not match its single reviewed stage")
    for field in ("evidence", "uncertainties"):
        value = receipt[field]
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise KarmaError(f"receipt {field} must be a text array")


def load_fixtures() -> dict[str, Any]:
    fixtures = parse_object(
        read_regular(FIXTURE_PATH, "fixture set"),
        "fixture set",
    )
    require_exact_keys(fixtures, {"schema", "cases"}, "fixture set")
    if fixtures["schema"] != FIXTURE_SCHEMA:
        raise KarmaError("unexpected fixture schema")
    cases = fixtures["cases"]
    if not isinstance(cases, list) or not cases:
        raise KarmaError("fixture cases must be a non-empty array")
    identifiers: set[str] = set()
    hatsu = load_hatsu()
    for case in cases:
        if not isinstance(case, dict):
            raise KarmaError("fixture case must be an object")
        require_exact_keys(case, {"id", "event", "expected"}, "fixture case")
        identifier = case["id"]
        if not isinstance(identifier, str) or not identifier:
            raise KarmaError("fixture id must be non-empty text")
        if identifier in identifiers:
            raise KarmaError(f"duplicate fixture id: {identifier}")
        identifiers.add(identifier)
        if not isinstance(case["event"], dict) or not isinstance(case["expected"], dict):
            raise KarmaError(f"fixture {identifier} event and expected must be objects")
        validate_event(case["event"], hatsu)
        validate_receipt(case["expected"])
    return fixtures


def verify_fixtures(fixtures: dict[str, Any] | None = None) -> dict[str, Any]:
    reviewed = fixtures if fixtures is not None else load_fixtures()
    hatsu = load_hatsu()
    for case in reviewed["cases"]:
        actual = interpret(case["event"], hatsu)
        if canonical_json(actual) != canonical_json(case["expected"]):
            raise KarmaError(f"fixture receipt mismatch: {case['id']}")
    return {
        "schema": "karma.mirror/verification-v1",
        "cases": len(reviewed["cases"]),
        "network_calls": 0,
        "storage_writes": 0,
        "external_effects": 0,
        "status": "verified",
    }


def all_fixture_results(fixtures: dict[str, Any] | None = None) -> dict[str, Any]:
    reviewed = fixtures if fixtures is not None else load_fixtures()
    hatsu = load_hatsu()
    return {
        "schema": "karma.mirror/results-v1",
        "results": [
            {"id": case["id"], "receipt": interpret(case["event"], hatsu)}
            for case in reviewed["cases"]
        ],
    }


def fixture_by_id(identifier: str, fixtures: dict[str, Any]) -> dict[str, Any]:
    matches = [case for case in fixtures["cases"] if case["id"] == identifier]
    if len(matches) != 1:
        raise KarmaError(f"unknown fixture: {identifier}")
    return matches[0]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Interpret reviewed KARMA fixtures; execute nothing."
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--fixture", help="interpret one reviewed fixture id")
    selection.add_argument(
        "--all-fixtures",
        action="store_true",
        help="emit canonical receipts for every reviewed fixture",
    )
    selection.add_argument(
        "--verify-fixtures",
        action="store_true",
        help="require every pinned fixture receipt to match",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        hatsu = load_hatsu()
        if args.fixture:
            fixtures = load_fixtures()
            result = interpret(fixture_by_id(args.fixture, fixtures)["event"], hatsu)
        elif args.all_fixtures:
            result = all_fixture_results()
        elif args.verify_fixtures:
            result = verify_fixtures()
        else:
            result = {
                "schema": "karma.mirror/summary-v1",
                "name": hatsu["name"],
                "behaviors": list(hatsu["policy"]["behaviors"]),
                "stages": [stage["stage"] for stage in hatsu["policy"]["stages"]],
                "action_executed": False,
                "authority_granted": False,
            }
        print(canonical_json(result).decode("utf-8"), end="")
        return 0
    except KarmaError as error:
        parser.exit(2, f"KARMA Mirror halted: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
