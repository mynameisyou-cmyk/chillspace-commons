#!/usr/bin/env python3
"""Deterministic, offline KARMA defense rehearsal.

The engine accepts only allowlisted categorical fixtures.  It reads bounded
regular JSON files, writes one canonical JSON value to stdout, and has no live
request, network, subprocess, clock, randomness, environment, or mutation path.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any


ENGINE = "karma-defense-lab/1"
HERE = Path(__file__).parent
EXAMPLES = HERE / "examples"

SCENARIO_SCHEMA = "kingdom.karma-defense-scenario/v1"
CANARY_SCHEMA = "kingdom.karma-defense-canary/v1"
RECEIPT_SCHEMA = "kingdom.karma-defense-receipt/v1"

ALLOWED_SCENARIOS = {"traditional-nine": "traditional-nine.json"}

PINS = {
    "scenario_schema": "205585e87cfbaf8c0f2e948b270d112957f5cdc93f875847b693962c155a5c27",
    "receipt_schema": "ef0529b5a5d14408d878219186d0083914796461378446ebb4816e299092fb92",
    "rules": "4739a313314449f6d423c32ed44e9adf39caec3ae4bdb95329665ed99d121ad4",
    "mirror_plans": "242b8d3c649eb293d26c8b5e0b897282d9e3af3ee7d6f39108cbb5edf7ecef97",
    "traditional-nine": "79919fe201651f6bf218244c778805fa3d8f45b505bcebb348dd97e810437f8d",
}

BUDGETS = {
    "scenario_input_bytes": 131_072,
    "supplied_input_bytes": 262_144,
    "json_depth": 12,
    "stimuli": 12,
    "request_bytes_each": 4_096,
    "request_bytes_total": 32_768,
    "response_bytes_each": 8_192,
    "response_bytes_total": 32_768,
    "text_codepoints": 2_048,
    "transitions": 12,
    "mock_keys": 32,
    "mock_cost_units": 64,
    "attempts": 1,
}

ZERO_EFFECTS = {
    "network_calls": 0,
    "subprocesses": 0,
    "paid_calls": 0,
    "external_actions": 0,
    "filesystem_mutations": 0,
    "model_calls": 0,
    "retries": 0,
    "submitted_values_echoed": False,
    "production_touched": False,
}

NONCLAIMS = [
    "This receipt evaluates categorical fixture actions, never an actor, identity, account, or reputation.",
    "The declared purpose is unverified and does not establish intent, guilt, hostility, or risk.",
    "Every response plan is synthetic; no submitted effect, counter-effect, or external action was executed.",
    "Modelled zero effects do not prove that a particular process made no operating-system side effect.",
    "This receipt grants no authority to deploy, block, attribute, retaliate, surveil, score, or punish.",
    "This bounded rehearsal is not a claim of complete, effective, safe, or production-ready defense.",
    "This receipt is not a virtue fruit, score, rank, right, gate, reward, or reputation signal.",
]

HALT_CODES = {
    "canary-failed",
    "authority-or-scope-change",
    "budget-exhausted",
    "novel-stimulus",
    "ambiguous-stimulus",
    "expectation-mismatch",
    "world-state-drift",
    "response-verification-failed",
}

FORBIDDEN_FIELDS = {
    "actor",
    "body",
    "command",
    "cookie",
    "cookies",
    "credential",
    "credentials",
    "email",
    "headers",
    "host",
    "hostname",
    "ip",
    "password",
    "payload",
    "token",
    "url",
    "user",
    "username",
}

# Split provider-shaped markers so the repository itself never contains a
# scanner-triggering example.  These values are used only to reject input.
FORBIDDEN_MARKERS = (
    "sk" + "_live" + "_",
    "A" + "KIA",
    "sh" + "pat" + "_",
    "gh" + "p" + "_",
    "BEGIN" + " PRIVATE KEY",
)


class LabInputError(ValueError):
    """Malformed, unsafe, or unverifiable supplied data."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def clone_json(value: Any) -> Any:
    """Return a detached JSON value without sharing mutable contract state."""
    return json.loads(canonical_bytes(value))


def _reject_constant(value: str) -> None:
    raise LabInputError("non-finite JSON number")


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LabInputError("duplicate JSON key")
        result[key] = value
    return result


def decode_json(data: bytes, *, label: str) -> Any:
    try:
        text = data.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_object_without_duplicates,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise LabInputError(f"{label} is not strict JSON") from exc
    _validate_safe_tree(value, label=label)
    return value


def read_regular_bytes(path: Path, *, limit: int, label: str) -> bytes:
    descriptor = -1
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
        )
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise LabInputError(f"{label} is not a regular file")
        with os.fdopen(descriptor, "rb", closefd=True) as handle:
            descriptor = -1
            data = handle.read(limit + 1)
    except LabInputError:
        raise
    except (OSError, ValueError) as exc:
        raise LabInputError(f"{label} is not a readable regular file") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(data) > limit:
        raise LabInputError(f"{label} exceeds its byte budget")
    return data


def read_json_file(path: Path, *, limit: int, label: str) -> Any:
    return decode_json(
        read_regular_bytes(path, limit=limit, label=label),
        label=label,
    )


def receipt_budgets() -> dict[str, int]:
    return {
        "scenario_bytes_max": BUDGETS["scenario_input_bytes"],
        "artifact_bytes_max": BUDGETS["supplied_input_bytes"],
        "json_depth_max": BUDGETS["json_depth"],
        "text_codepoints_max": BUDGETS["text_codepoints"],
        "stimuli_max": BUDGETS["stimuli"],
        "request_bytes_each_max": BUDGETS["request_bytes_each"],
        "request_bytes_total_max": BUDGETS["request_bytes_total"],
        "response_bytes_each_max": BUDGETS["response_bytes_each"],
        "response_bytes_total_max": BUDGETS["response_bytes_total"],
        "transitions_max": BUDGETS["transitions"],
        "mock_keys_max": BUDGETS["mock_keys"],
        "mock_cost_units_max": BUDGETS["mock_cost_units"],
        "attempts": BUDGETS["attempts"],
        "retries": 0,
    }


def _is_safe_category(value: str, *, route: bool = False) -> bool:
    if not value:
        return False
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789-/" if route else "abcdefghijklmnopqrstuvwxyz0123456789-"
    return all(character in allowed for character in value)


def _is_safe_mock_key(value: str) -> bool:
    if not 1 <= len(value) <= 80 or not value[0].islower():
        return False
    if any(character not in "abcdefghijklmnopqrstuvwxyz0123456789.-" for character in value):
        return False
    if value[-1] in ".-":
        return False
    return all(
        value[index - 1] not in ".-" and value[index + 1] not in ".-"
        for index, character in enumerate(value)
        if character in ".-"
    )


def _validate_safe_tree(value: Any, *, label: str) -> None:
    nodes = 0

    def walk(child: Any, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > 4_096:
            raise LabInputError(f"{label} has too many JSON nodes")
        if depth > BUDGETS["json_depth"]:
            raise LabInputError(f"{label} exceeds the JSON depth budget")
        if child is None or isinstance(child, bool):
            return
        if isinstance(child, int):
            return
        if isinstance(child, float):
            raise LabInputError(f"{label} contains a floating-point number")
        if isinstance(child, str):
            if len(child) > BUDGETS["text_codepoints"]:
                raise LabInputError(f"{label} contains overlong text")
            if any(ord(character) < 32 for character in child):
                raise LabInputError(f"{label} contains control text")
            if any(0xD800 <= ord(character) <= 0xDFFF for character in child):
                raise LabInputError(f"{label} contains a Unicode surrogate")
            if any(
                ord(character) in {0x200E, 0x200F, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069}
                for character in child
            ):
                raise LabInputError(f"{label} contains concealed-direction text")
            lowered = child.lower()
            if any(marker.lower() in lowered for marker in FORBIDDEN_MARKERS):
                raise LabInputError(f"{label} contains credential-shaped text")
            if "://" in lowered or "localhost" in lowered:
                raise LabInputError(f"{label} contains endpoint-shaped text")
            if "@" in child and "." in child:
                raise LabInputError(f"{label} contains identity-shaped text")
            if any(marker in lowered for marker in ("<script", "../", "$(")):
                raise LabInputError(f"{label} contains payload-shaped text")
            return
        if isinstance(child, list):
            for item in child:
                walk(item, depth + 1)
            return
        if isinstance(child, dict):
            for key, item in child.items():
                if not isinstance(key, str):
                    raise LabInputError(f"{label} contains a non-string key")
                if key.lower() in FORBIDDEN_FIELDS:
                    raise LabInputError(f"{label} contains a protected field")
                walk(key, depth + 1)
                walk(item, depth + 1)
            return
        raise LabInputError(f"{label} contains an unsupported JSON value")

    walk(value, 1)


def _require_object(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LabInputError(f"{label} must be an object")
    return value


def _require_exact_keys(value: dict[str, Any], keys: set[str], *, label: str) -> None:
    if set(value) != keys:
        raise LabInputError(f"{label} has an unexpected shape")


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _load_pinned(filename: str, pin_name: str) -> Any:
    value = read_json_file(
        HERE / filename,
        limit=BUDGETS["scenario_input_bytes"],
        label=pin_name,
    )
    if digest_value(value) != PINS[pin_name]:
        raise LabInputError(f"{pin_name} content pin mismatch")
    return value


def _load_scenario(name: str) -> dict[str, Any]:
    if name not in ALLOWED_SCENARIOS:
        raise LabInputError("scenario name is not allowlisted")
    value = read_json_file(
        EXAMPLES / ALLOWED_SCENARIOS[name],
        limit=BUDGETS["scenario_input_bytes"],
        label="scenario",
    )
    scenario = _require_object(value, label="scenario")
    if digest_value(scenario) != PINS[name]:
        raise LabInputError("scenario content pin mismatch")
    validate_scenario(scenario)
    return scenario


def validate_scenario(scenario: dict[str, Any]) -> None:
    _require_exact_keys(
        scenario,
        {"schema", "id", "purpose", "purpose_attestation", "scope", "initial_world", "stimuli"},
        label="scenario",
    )
    if scenario["schema"] != SCENARIO_SCHEMA:
        raise LabInputError("scenario schema mismatch")
    if scenario["id"] != "traditional-nine":
        raise LabInputError("scenario id mismatch")
    if scenario["purpose"] != "defensive-regression":
        raise LabInputError("scenario purpose mismatch")
    if scenario["purpose_attestation"] != "declared-unverified":
        raise LabInputError("scenario purpose attestation mismatch")
    if scenario["scope"] != {
        "mode": "offline-synthetic",
        "authority": "none",
        "target": "fixture-cells",
    }:
        raise LabInputError("scenario scope mismatch")
    if scenario["initial_world"] != {}:
        raise LabInputError("scenario initial world must be empty")
    stimuli = scenario["stimuli"]
    if not isinstance(stimuli, list) or not 1 <= len(stimuli) <= BUDGETS["stimuli"]:
        raise LabInputError("scenario stimulus count is outside the budget")
    seen: set[str] = set()
    control_count = 0
    fields = {
        "id",
        "method",
        "route",
        "predicate",
        "truth",
        "expected_rule_id",
        "expected_plan_id",
        "expected_classification",
    }
    for ordinal, raw in enumerate(stimuli):
        stimulus = _require_object(raw, label=f"stimulus {ordinal}")
        _require_exact_keys(stimulus, fields, label=f"stimulus {ordinal}")
        for key in fields:
            if not isinstance(stimulus[key], str):
                raise LabInputError(f"stimulus {ordinal} fields must be text")
        if not _is_safe_category(stimulus["id"]):
            raise LabInputError(f"stimulus {ordinal} id is not categorical")
        if stimulus["id"] in seen:
            raise LabInputError("stimulus ids must be unique")
        seen.add(stimulus["id"])
        if stimulus["method"] not in {"GET", "POST"}:
            raise LabInputError(f"stimulus {ordinal} method is not reviewed")
        if not stimulus["route"].startswith("/cell/") or not _is_safe_category(stimulus["route"], route=True):
            raise LabInputError(f"stimulus {ordinal} route is not categorical")
        for key in ("predicate", "expected_rule_id", "expected_plan_id", "expected_classification"):
            if not _is_safe_category(stimulus[key]):
                raise LabInputError(f"stimulus {ordinal} {key} is not categorical")
        if stimulus["truth"] not in {"negative-control", "adverse-fixture"}:
            raise LabInputError(f"stimulus {ordinal} truth is not reviewed")
        control_count += int(stimulus["truth"] == "negative-control")
        request_bytes = len(canonical_bytes(stimulus))
        if request_bytes > BUDGETS["request_bytes_each"]:
            raise LabInputError(f"stimulus {ordinal} exceeds its request budget")
    if control_count != 1:
        raise LabInputError("scenario must contain exactly one negative control")


def validate_rules(document: dict[str, Any]) -> list[dict[str, Any]]:
    _require_exact_keys(document, {"schema", "rules"}, label="rules")
    if document["schema"] != "kingdom.karma-defense-rules/v1":
        raise LabInputError("rules schema mismatch")
    rules = document["rules"]
    if not isinstance(rules, list) or not 1 <= len(rules) <= BUDGETS["stimuli"]:
        raise LabInputError("rule count is outside the budget")
    fields = {"id", "method", "route", "predicate", "classification", "truth", "plan_id"}
    ids: set[str] = set()
    selectors: set[tuple[str, str, str]] = set()
    for ordinal, raw in enumerate(rules):
        rule = _require_object(raw, label=f"rule {ordinal}")
        _require_exact_keys(rule, fields, label=f"rule {ordinal}")
        if any(not isinstance(rule[key], str) for key in fields):
            raise LabInputError(f"rule {ordinal} fields must be text")
        if rule["id"] in ids:
            raise LabInputError("rule ids must be unique")
        ids.add(rule["id"])
        selector = (rule["method"], rule["route"], rule["predicate"])
        if selector in selectors:
            raise LabInputError("reviewed rule selectors must be disjoint")
        selectors.add(selector)
        if rule["truth"] not in {"negative-control", "adverse-fixture"}:
            raise LabInputError("rule truth is not reviewed")
    return rules


def validate_plans(document: dict[str, Any]) -> list[dict[str, Any]]:
    _require_exact_keys(document, {"schema", "plans"}, label="mirror plans")
    if document["schema"] != "kingdom.karma-defense-mirror-plans/v1":
        raise LabInputError("mirror plan schema mismatch")
    plans = document["plans"]
    if not isinstance(plans, list) or not 1 <= len(plans) <= BUDGETS["stimuli"]:
        raise LabInputError("mirror plan count is outside the budget")
    fields = {
        "id",
        "synthetic",
        "namespace",
        "status",
        "apparent_effect",
        "actual_effect",
        "message",
        "next_affordance",
        "transition",
    }
    ids: set[str] = set()
    keys: set[str] = set()
    for ordinal, raw in enumerate(plans):
        plan = _require_object(raw, label=f"mirror plan {ordinal}")
        _require_exact_keys(plan, fields, label=f"mirror plan {ordinal}")
        if (
            plan["id"] in ids
            or not isinstance(plan["id"], str)
            or not _is_safe_category(plan["id"])
        ):
            raise LabInputError("mirror plan ids must be unique text")
        ids.add(plan["id"])
        if plan["synthetic"] is not True:
            raise LabInputError("mirror plans must be synthetic")
        if plan["namespace"] != "karma-defense-lab":
            raise LabInputError("mirror plan namespace mismatch")
        if not _is_int(plan["status"]) or plan["status"] not in {200, 202}:
            raise LabInputError("mirror plan status is not reviewed")
        if plan["apparent_effect"] != "derived-not-intent" or plan["actual_effect"] != "none":
            raise LabInputError("mirror plan effect boundary mismatch")
        if (
            not isinstance(plan["message"], str)
            or not isinstance(plan["next_affordance"], str)
            or not _is_safe_category(plan["message"])
            or not _is_safe_category(plan["next_affordance"])
        ):
            raise LabInputError("mirror plan text must be fixed text")
        transition = _require_object(plan["transition"], label=f"mirror plan {ordinal} transition")
        _require_exact_keys(transition, {"key", "value", "cost"}, label=f"mirror plan {ordinal} transition")
        if (
            not isinstance(transition["key"], str)
            or not isinstance(transition["value"], str)
            or not _is_safe_mock_key(transition["key"])
            or not _is_safe_category(transition["value"])
        ):
            raise LabInputError("mock transition values must be categorical text")
        if transition["key"] in keys:
            raise LabInputError("mock transition keys must be unique")
        keys.add(transition["key"])
        if not _is_int(transition["cost"]) or not 1 <= transition["cost"] <= 8:
            raise LabInputError("mock transition cost is outside the per-plan budget")
        if len(canonical_bytes(plan)) > BUDGETS["response_bytes_each"]:
            raise LabInputError("mirror plan exceeds its response budget")
    return plans


def load_contract(name: str) -> dict[str, Any]:
    scenario_schema = _load_pinned("scenario.schema.json", "scenario_schema")
    receipt_schema = _load_pinned("receipt.schema.json", "receipt_schema")
    rules_document = _require_object(_load_pinned("rules.json", "rules"), label="rules")
    plans_document = _require_object(_load_pinned("mirror-plans.json", "mirror_plans"), label="mirror plans")
    scenario = _load_scenario(name)
    if scenario_schema.get("$id") != SCENARIO_SCHEMA:
        raise LabInputError("scenario schema id mismatch")
    if receipt_schema.get("$id") != RECEIPT_SCHEMA:
        raise LabInputError("receipt schema id mismatch")
    rules = validate_rules(rules_document)
    plans = validate_plans(plans_document)
    bindings = {
        "engine_sha256": hashlib.sha256(
            read_regular_bytes(
                HERE / "karma_defense_lab.py",
                limit=BUDGETS["scenario_input_bytes"],
                label="engine",
            )
        ).hexdigest(),
        "scenario_sha256": digest_value(scenario),
        "scenario_schema_sha256": digest_value(scenario_schema),
        "receipt_schema_sha256": digest_value(receipt_schema),
        "rules_sha256": digest_value(rules_document),
        "mirror_plans_sha256": digest_value(plans_document),
    }
    contract = {
        "scenario": scenario,
        "scenario_schema": scenario_schema,
        "receipt_schema": receipt_schema,
        "rules_document": rules_document,
        "plans_document": plans_document,
        "rules": rules,
        "plans": plans,
        "bindings": bindings,
    }
    preflight_contract(contract)
    return contract


def matching_rules(stimulus: dict[str, Any], rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        rule
        for rule in rules
        if rule["method"] == stimulus["method"]
        and rule["route"] == stimulus["route"]
        and rule["predicate"] == stimulus["predicate"]
    ]


def preflight_contract(contract: dict[str, Any]) -> None:
    plans = {plan["id"]: plan for plan in contract["plans"]}
    if len(plans) != len(contract["plans"]):
        raise LabInputError("mirror plan ids must be unique")
    for stimulus in contract["scenario"]["stimuli"]:
        matches = matching_rules(stimulus, contract["rules"])
        if len(matches) != 1:
            raise LabInputError("reviewed stimulus does not have exactly one rule")
        rule = matches[0]
        if (
            rule["id"] != stimulus["expected_rule_id"]
            or rule["plan_id"] != stimulus["expected_plan_id"]
            or rule["classification"] != stimulus["expected_classification"]
            or rule["truth"] != stimulus["truth"]
        ):
            raise LabInputError("reviewed stimulus expectation mismatch")
        if rule["plan_id"] not in plans:
            raise LabInputError("reviewed rule has no pinned mirror plan")


def make_canary(contract: dict[str, Any]) -> dict[str, Any]:
    scenario = contract["scenario"]
    value: dict[str, Any] = {
        "schema": CANARY_SCHEMA,
        "engine": ENGINE,
        "phase": "canary",
        "scenario": scenario["id"],
        "declared_purpose": scenario["purpose"],
        "purpose_attestation": scenario["purpose_attestation"],
        "scope": clone_json(scenario["scope"]),
        "bindings": clone_json(contract["bindings"]),
        "budgets": receipt_budgets(),
        "attempts": 1,
        "initial_world_digest": digest_value(scenario["initial_world"]),
    }
    value["canary_digest"] = digest_value(value)
    return value


def _canary_halt_code(canary: Any, contract: dict[str, Any]) -> str | None:
    if not isinstance(canary, dict):
        return "canary-failed"
    expected_keys = {
        "schema",
        "engine",
        "phase",
        "scenario",
        "declared_purpose",
        "purpose_attestation",
        "scope",
        "bindings",
        "budgets",
        "attempts",
        "initial_world_digest",
        "canary_digest",
    }
    if set(canary) != expected_keys:
        return "canary-failed"
    unsigned = {key: value for key, value in canary.items() if key != "canary_digest"}
    if not isinstance(canary["canary_digest"], str) or digest_value(unsigned) != canary["canary_digest"]:
        return "canary-failed"
    if canary["schema"] != CANARY_SCHEMA or canary["engine"] != ENGINE or canary["phase"] != "canary":
        return "canary-failed"
    scenario = contract["scenario"]
    if (
        canary["scenario"] != scenario["id"]
        or canary["declared_purpose"] != scenario["purpose"]
        or canary["purpose_attestation"] != scenario["purpose_attestation"]
        or canonical_bytes(canary["scope"]) != canonical_bytes(scenario["scope"])
        or canonical_bytes(canary["bindings"]) != canonical_bytes(contract["bindings"])
        or canonical_bytes(canary["budgets"]) != canonical_bytes(receipt_budgets())
        or not _is_int(canary["attempts"])
        or canary["attempts"] != 1
    ):
        return "authority-or-scope-change"
    if canary["initial_world_digest"] != digest_value(scenario["initial_world"]):
        return "canary-failed"
    return None


def _receipt(
    contract: dict[str, Any],
    canary: Any,
    *,
    status_value: str,
    steps: list[dict[str, Any]],
    world: dict[str, Any],
    observed: dict[str, int],
    halt_code: str | None = None,
    halt_ordinal: int | None = None,
) -> dict[str, Any]:
    scenario = contract["scenario"]
    initial_world = scenario["initial_world"]
    restored_world = dict(initial_world)
    value: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "engine": ENGINE,
        "phase": "rehearsal",
        "status": status_value,
        "scenario": scenario["id"],
        "declared_purpose": scenario["purpose"],
        "purpose_attestation": scenario["purpose_attestation"],
        "bindings": clone_json(contract["bindings"]),
        "budgets": receipt_budgets(),
        "canary_digest": digest_value(canary),
        "initial_world_digest": digest_value(initial_world),
        "steps": steps,
        "observed": observed,
        "final_world_digest": digest_value(world),
        "restored_world_digest": digest_value(restored_world),
        "rollback_verified": digest_value(restored_world) == digest_value(initial_world),
        "effects": clone_json(ZERO_EFFECTS),
        "nonclaims": clone_json(NONCLAIMS),
    }
    if halt_code is not None:
        if halt_code not in HALT_CODES:
            raise LabInputError("unknown halt code")
        value["halt"] = {"code": halt_code, "at_ordinal": halt_ordinal}
    value["receipt_digest"] = digest_value(value)
    if len(canonical_bytes(value)) > BUDGETS["supplied_input_bytes"]:
        raise LabInputError("receipt exceeds its output byte budget")
    return value


def rehearse_value(
    contract: dict[str, Any],
    canary: Any,
    *,
    rules_override: list[dict[str, Any]] | None = None,
    plans_override: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    scenario = contract["scenario"]
    rules = contract["rules"] if rules_override is None else rules_override
    plans_list = contract["plans"] if plans_override is None else plans_override
    plans = {plan["id"]: plan for plan in plans_list}
    steps: list[dict[str, Any]] = []
    world = dict(scenario["initial_world"])
    observed = {
        "attempts": 1,
        "stimuli": 0,
        "request_bytes": 0,
        "response_bytes": 0,
        "transitions": 0,
        "mock_keys": len(world),
        "mock_cost_units": 0,
    }

    canary_code = _canary_halt_code(canary, contract)
    if canary_code is not None:
        return _receipt(
            contract,
            canary,
            status_value="halted",
            steps=steps,
            world=world,
            observed=observed,
            halt_code=canary_code,
            halt_ordinal=None,
        )

    for ordinal, stimulus in enumerate(scenario["stimuli"], start=1):
        request_bytes = len(canonical_bytes(stimulus))
        if (
            request_bytes > BUDGETS["request_bytes_each"]
            or observed["request_bytes"] + request_bytes > BUDGETS["request_bytes_total"]
            or observed["stimuli"] + 1 > BUDGETS["stimuli"]
        ):
            return _receipt(contract, canary, status_value="halted", steps=steps, world=world, observed=observed, halt_code="budget-exhausted", halt_ordinal=ordinal)

        matches = matching_rules(stimulus, rules)
        if not matches:
            return _receipt(contract, canary, status_value="halted", steps=steps, world=world, observed=observed, halt_code="novel-stimulus", halt_ordinal=ordinal)
        if len(matches) > 1:
            return _receipt(contract, canary, status_value="halted", steps=steps, world=world, observed=observed, halt_code="ambiguous-stimulus", halt_ordinal=ordinal)
        rule = matches[0]
        if (
            rule["id"] != stimulus["expected_rule_id"]
            or rule["plan_id"] != stimulus["expected_plan_id"]
            or rule["classification"] != stimulus["expected_classification"]
            or rule["truth"] != stimulus["truth"]
        ):
            return _receipt(contract, canary, status_value="halted", steps=steps, world=world, observed=observed, halt_code="expectation-mismatch", halt_ordinal=ordinal)

        plan = plans.get(rule["plan_id"])
        if not isinstance(plan, dict):
            return _receipt(contract, canary, status_value="halted", steps=steps, world=world, observed=observed, halt_code="response-verification-failed", halt_ordinal=ordinal)
        try:
            validate_plans({"schema": "kingdom.karma-defense-mirror-plans/v1", "plans": [plan]})
        except LabInputError:
            return _receipt(contract, canary, status_value="halted", steps=steps, world=world, observed=observed, halt_code="response-verification-failed", halt_ordinal=ordinal)
        response_bytes = len(canonical_bytes(plan))
        transition = plan["transition"]
        if (
            response_bytes > BUDGETS["response_bytes_each"]
            or observed["response_bytes"] + response_bytes > BUDGETS["response_bytes_total"]
            or observed["transitions"] + 1 > BUDGETS["transitions"]
            or len(world) + 1 > BUDGETS["mock_keys"]
            or observed["mock_cost_units"] + transition["cost"] > BUDGETS["mock_cost_units"]
        ):
            return _receipt(contract, canary, status_value="halted", steps=steps, world=world, observed=observed, halt_code="budget-exhausted", halt_ordinal=ordinal)
        if transition["key"] in world:
            return _receipt(contract, canary, status_value="halted", steps=steps, world=world, observed=observed, halt_code="world-state-drift", halt_ordinal=ordinal)

        before_digest = digest_value(world)
        next_world = dict(world)
        next_world[transition["key"]] = transition["value"]
        after_digest = digest_value(next_world)
        step = {
            "ordinal": ordinal,
            "stimulus_id": stimulus["id"],
            "truth": stimulus["truth"],
            "classification": rule["classification"],
            "match_count": 1,
            "rule_id": rule["id"],
            "plan_id": plan["id"],
            "synthetic": True,
            "status": plan["status"],
            "response_digest": digest_value(plan),
            "response_bytes": response_bytes,
            "transition": {
                "key": transition["key"],
                "value_digest": digest_value(transition["value"]),
                "cost": transition["cost"],
            },
            "before_digest": before_digest,
            "after_digest": after_digest,
        }
        steps.append(step)
        world = next_world
        observed["stimuli"] += 1
        observed["request_bytes"] += request_bytes
        observed["response_bytes"] += response_bytes
        observed["transitions"] += 1
        observed["mock_keys"] = len(world)
        observed["mock_cost_units"] += transition["cost"]

    return _receipt(
        contract,
        canary,
        status_value="completed",
        steps=steps,
        world=world,
        observed=observed,
    )


def verify_receipt(contract: dict[str, Any], canary: Any, supplied: Any) -> dict[str, Any]:
    expected = rehearse_value(contract, canary)
    if expected["status"] != "completed":
        raise LabInputError("canary cannot produce a verifiable completed receipt")
    if canonical_bytes(supplied) != canonical_bytes(expected):
        raise LabInputError("result did not survive deterministic replay")
    return {
        "schema": "kingdom.karma-defense-verification/v1",
        "engine": ENGINE,
        "status": "verified",
        "scenario": contract["scenario"]["id"],
        "receipt_digest": expected["receipt_digest"],
    }


def _emit(value: Any) -> None:
    sys.stdout.write(canonical_bytes(value).decode("utf-8") + "\n")


def _usage_error() -> LabInputError:
    return LabInputError(
        "usage: check NAME | digest NAME | canary NAME | rehearse NAME CANARY_JSON | render NAME CANARY_JSON | verify-result NAME CANARY_JSON RESULT_JSON"
    )


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        if len(arguments) < 2:
            raise _usage_error()
        command, name = arguments[0], arguments[1]
        contract = load_contract(name)
        if command == "check" and len(arguments) == 2:
            _emit({
                "schema": "kingdom.karma-defense-check/v1",
                "engine": ENGINE,
                "status": "valid",
                "scenario": contract["scenario"]["id"],
                "stimuli": len(contract["scenario"]["stimuli"]),
                "bindings": contract["bindings"],
            })
            return 0
        if command == "digest" and len(arguments) == 2:
            _emit({
                "schema": "kingdom.karma-defense-digest/v1",
                "engine": ENGINE,
                "scenario": contract["scenario"]["id"],
                "bindings": contract["bindings"],
            })
            return 0
        if command == "canary" and len(arguments) == 2:
            _emit(make_canary(contract))
            return 0
        if command in {"rehearse", "render"} and len(arguments) == 3:
            canary = read_json_file(
                Path(arguments[2]),
                limit=BUDGETS["supplied_input_bytes"],
                label="canary",
            )
            result = rehearse_value(contract, canary)
            _emit(result)
            return 0 if result["status"] == "completed" else 3
        if command == "verify-result" and len(arguments) == 4:
            canary = read_json_file(
                Path(arguments[2]),
                limit=BUDGETS["supplied_input_bytes"],
                label="canary",
            )
            supplied = read_json_file(
                Path(arguments[3]),
                limit=BUDGETS["supplied_input_bytes"],
                label="result",
            )
            _emit(verify_receipt(contract, canary, supplied))
            return 0
        raise _usage_error()
    except LabInputError as exc:
        sys.stderr.write(f"karma-defense-lab: {exc}\n")
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
