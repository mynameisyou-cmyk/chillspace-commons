#!/usr/bin/env python3
"""Project one reviewed future system-effect shape into inert KARMA advice.

KARMA FORESIGHT is a closed, offline tabletop compiler.  It does not inspect
traffic, payloads, people, identities, prompts, or live systems.  It does not
infer intent, detect attacks, score risk, execute a response, update its own
rules, or retain state.  One digest-bound declaration becomes one exactly
recomputable projection for human review.
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
SCENARIO_SCHEMA_ID = "kingdom.karma-foresight/v1"
CATALOG_SCHEMA_ID = "kingdom.karma-foresight-catalog/v1"
PROJECTION_SCHEMA_ID = "kingdom.karma-foresight-projection/v1"
EXPECTED_CATALOG_SHA256 = "dd63c0dc9cd78f7f2906b67605ac3e6164ac26a7347b5dd7bfa59255187d61b9"
EXPECTED_SCENARIO_SCHEMA_SHA256 = "f733e3abdbee2bf516b88d8df8cb591f08de6f9536171c9c7aee1e486c5eb7ef"
EXPECTED_PROJECTION_SCHEMA_SHA256 = "96dd53c615bee535cda7a8be12cd2392989cc7c4c9047a6afc4eab2cce6a6a28"
MAX_FILE_BYTES = 32_768
MAX_NODES = 512
MAX_REVIEWED_NODES = 1_024
MAX_DEPTH = 8
MAX_STRING = 512
MAX_OUTPUT_BYTES = 16_384

CONTRACT = {
    "assessment_unit": "authored-system-effect-hypothesis",
    "constellation_is_authored_not_detected": True,
    "system_effect_is_hypothesized_not_established": True,
    "purpose_is_system_effect_not_person_intent": True,
    "alternative_hypothesis_required": True,
    "person_intent_inferred": False,
    "person_classified": False,
    "identity_fields_allowed": False,
    "payload_fields_allowed": False,
    "free_text_fields_allowed": False,
    "scores_or_ranks": False,
    "aggregation_allowed": False,
    "tracks_repetition": False,
    "cross_run_state": False,
    "automatic_detection": False,
    "automatic_enforcement": False,
    "automatic_rule_update": False,
    "human_review_required_for_action": True,
    "owned_or_authorized_boundary_required": True,
    "retaliation": False,
    "hack_back": False,
    "executes_input": False,
    "executes_response": False,
    "rights_and_debts_unchanged": True,
    "creates_external_effect": False,
}
BUDGET = {
    "declarations": 1,
    "passes": 1,
    "catalog_rules": 10,
    "file_bytes_max": MAX_FILE_BYTES,
    "decoded_nodes_max": MAX_NODES,
    "nesting_depth_max": MAX_DEPTH,
    "string_characters_max": MAX_STRING,
    "output_bytes_max": MAX_OUTPUT_BYTES,
    "automatic_retries": 0,
    "network_calls": 0,
    "external_messages": 0,
    "writes": 0,
    "subprocesses": 0,
    "model_calls": 0,
    "paid_calls": 0,
    "clock_reads": 0,
    "random_draws": 0,
    "payload_bytes_retained": 0,
    "identity_records": 0,
    "cross_run_records": 0,
}
BREACH = {
    "state": "quarantined",
    "action": "stop-without-retry-or-result",
    "source_unchanged": True,
    "submitted_values_echoed": False,
    "partial_projection": False,
    "downstream_effects": False,
}
EXIT = {
    "action": "return-or-discard-one-projection",
    "state_retained": False,
    "history_retained": False,
    "standing_created": False,
    "authority_created": False,
    "follow_up": False,
}
NON_CLAIMS = [
    "A constellation is a reviewed tabletop template, not a detected attack or claim about a person.",
    "A system-effect hypothesis is a possible consequence, not an individual's purpose, intention, guilt, character, or worth.",
    "The required alternative hypothesis does not prove benignity, innocence, authorization, or safety.",
    "Constellations and response rungs are not confidence, severity, scores, ranks, reputation, or access decisions.",
    "Response and learning fields are inert review candidates, not enforcement, deployment, permission, legal advice, or authority.",
    "No payload, prompt, address, identity, credential, target, callback, command, URL, or submitted free text is accepted, retained, rendered, or echoed.",
    "Digests prove reviewed canonical JSON relationships and exact recomputation only; this finite atlas is not exhaustive.",
]
RESPONSE_LADDER = [
    {
        "rung": "observe",
        "display_name": "Watchtower · 守望塔",
        "mode": "information-only",
        "recovery_candidate": "discard-or-author-fresh-reviewed-scenario",
    },
    {
        "rung": "clarify",
        "display_name": "Map Room · 圖室",
        "mode": "authority-or-lineage-review",
        "recovery_candidate": "fresh-reviewed-evidence-reopens-review",
    },
    {
        "rung": "constrain",
        "display_name": "Gatehouse · 門樓",
        "mode": "scope-or-budget-review",
        "recovery_candidate": "fresh-scope-and-budget-review",
    },
    {
        "rung": "isolate",
        "display_name": "Detached Keep · 分堡",
        "mode": "trust-boundary-separation-review",
        "recovery_candidate": "fresh-clean-context-and-authority-review",
    },
    {
        "rung": "quarantine",
        "display_name": "Still Vault · 靜庫",
        "mode": "adoption-hold-review",
        "recovery_candidate": "fresh-provenance-authority-and-release-review",
    },
]

ROOT_KEYS = {
    "schema",
    "kind",
    "catalog_sha256",
    "declaration",
    "contract",
    "budget",
    "breach",
    "exit",
    "non_claims",
}
DECLARATION_KEYS = {
    "constellation",
    "mechanism",
    "system_effect_hypothesis",
    "boundary_signal",
    "alternative_hypothesis",
}
CATALOG_KEYS = {
    "schema",
    "practice",
    "scenario_schema",
    "projection_schema",
    "response_ladder",
    "rules",
    "contract",
    "budget",
    "breach",
    "exit",
    "non_claims",
}
RULE_KEYS = {
    "constellation",
    "display_name",
    "family",
    "mechanism",
    "system_effect_hypothesis",
    "boundary_signal",
    "alternative_hypothesis",
    "response_rung",
    "response_candidate",
    "reflection",
    "hypothesis_test_candidate",
    "negative_control_candidate",
    "regression_candidate",
    "repair_candidate",
    "release_review_candidate",
}
LADDER_KEYS = {"rung", "display_name", "mode", "recovery_candidate"}
CONCEALED_CODEPOINTS = {
    *range(0x200B, 0x2010),
    *range(0x202A, 0x202F),
    *range(0x2060, 0x206A),
    0xFEFF,
}


class ForesightError(ValueError):
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
    """Compare JSON with type sensitivity (Python otherwise treats false == 0)."""

    return canonical_json(left) == canonical_json(right)


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, child in pairs:
        if key in value:
            raise ForesightError("duplicate-key")
        value[key] = child
    return value


def _parse_int(token: str) -> int:
    if len(token.lstrip("-")) > 10:
        raise ForesightError("number-out-of-range")
    return int(token)


def _reject_number(_token: str) -> float:
    raise ForesightError("unsupported-number")


def _reject_constant(_token: str) -> None:
    raise ForesightError("non-finite-number")


def _clean_string(value: str) -> None:
    if len(value) > MAX_STRING:
        raise ForesightError("string-too-long")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ForesightError("control-character")
    if any(ord(char) in CONCEALED_CODEPOINTS for char in value):
        raise ForesightError("concealed-codepoint")
    if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise ForesightError("invalid-unicode")


def _walk_limits(value: Any, *, node_limit: int = MAX_NODES) -> None:
    nodes = 0
    pending = [(value, 0)]
    while pending:
        current, depth = pending.pop()
        nodes += 1
        if nodes > node_limit:
            raise ForesightError("too-many-nodes")
        if depth > MAX_DEPTH:
            raise ForesightError("too-deep")
        if isinstance(current, dict):
            for key, child in current.items():
                _clean_string(key)
                pending.append((child, depth + 1))
        elif isinstance(current, list):
            pending.extend((child, depth + 1) for child in current)
        elif isinstance(current, str):
            _clean_string(current)
        elif current is not None and not isinstance(current, (bool, int)):
            raise ForesightError("unsupported-value")


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
        raise ForesightError(f"{label}-unreadable") from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ForesightError(f"{label}-not-regular")
        if before.st_size > MAX_FILE_BYTES:
            raise ForesightError(f"{label}-too-large")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            raw = handle.read(MAX_FILE_BYTES + 1)
            after = os.fstat(handle.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(raw) > MAX_FILE_BYTES:
        raise ForesightError(f"{label}-too-large")
    if (
        before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or before.st_ctime_ns != after.st_ctime_ns
        or len(raw) != before.st_size
    ):
        raise ForesightError(f"{label}-changed-during-read")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_int=_parse_int,
            parse_float=_reject_number,
            parse_constant=_reject_constant,
        )
    except ForesightError:
        raise
    except RecursionError as error:
        raise ForesightError("too-deep") from error
    except (UnicodeDecodeError, ValueError) as error:
        raise ForesightError(f"{label}-invalid-json") from error
    if not isinstance(value, dict):
        raise ForesightError(f"{label}-root-not-object")
    _walk_limits(value, node_limit=node_limit)
    return value


def _exact_keys(value: dict[str, Any], expected: set[str], code: str) -> None:
    if set(value) != expected:
        raise ForesightError(code)


@lru_cache(maxsize=1)
def _reviewed_scenario_schema() -> dict[str, Any]:
    value = _read_json(
        HERE / "scenario.schema.json",
        label="scenario-schema",
        node_limit=MAX_REVIEWED_NODES,
    )
    if digest_value(value) != EXPECTED_SCENARIO_SCHEMA_SHA256:
        raise ForesightError("scenario-schema-digest-mismatch")
    return value


@lru_cache(maxsize=1)
def _reviewed_projection_schema() -> dict[str, Any]:
    value = _read_json(
        HERE / "projection.schema.json",
        label="projection-schema",
        node_limit=MAX_REVIEWED_NODES,
    )
    if digest_value(value) != EXPECTED_PROJECTION_SCHEMA_SHA256:
        raise ForesightError("projection-schema-digest-mismatch")
    return value


@lru_cache(maxsize=1)
def _catalog() -> dict[str, Any]:
    value = _read_json(HERE / "catalog.json", label="catalog")
    if digest_value(value) != EXPECTED_CATALOG_SHA256:
        raise ForesightError("catalog-digest-mismatch")
    _exact_keys(value, CATALOG_KEYS, "catalog-shape-mismatch")
    if (
        value["schema"] != CATALOG_SCHEMA_ID
        or value["scenario_schema"] != SCENARIO_SCHEMA_ID
        or value["projection_schema"] != PROJECTION_SCHEMA_ID
        or not isinstance(value["practice"], str)
        or not _json_equal(value["contract"], CONTRACT)
        or not _json_equal(value["budget"], BUDGET)
        or not _json_equal(value["breach"], BREACH)
        or not _json_equal(value["exit"], EXIT)
        or not _json_equal(value["non_claims"], NON_CLAIMS)
    ):
        raise ForesightError("catalog-contract-mismatch")
    ladder = value["response_ladder"]
    if not isinstance(ladder, list) or not _json_equal(ladder, RESPONSE_LADDER):
        raise ForesightError("response-ladder-mismatch")
    if any(not isinstance(item, dict) or set(item) != LADDER_KEYS for item in ladder):
        raise ForesightError("response-ladder-shape-mismatch")
    rules = value["rules"]
    if not isinstance(rules, list) or len(rules) != BUDGET["catalog_rules"]:
        raise ForesightError("catalog-rule-count-mismatch")
    tuples: set[tuple[str, str, str, str, str]] = set()
    constellations: set[str] = set()
    rungs = {item["rung"] for item in ladder}
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) != RULE_KEYS:
            raise ForesightError("catalog-rule-shape-mismatch")
        if any(not isinstance(item, str) or not item for item in rule.values()):
            raise ForesightError("catalog-rule-value-mismatch")
        key = _rule_key(rule)
        if (
            key in tuples
            or rule["constellation"] in constellations
            or rule["response_rung"] not in rungs
        ):
            raise ForesightError("duplicate-or-unbound-catalog-rule")
        tuples.add(key)
        constellations.add(rule["constellation"])
    return value


def _rule_key(value: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        value["constellation"],
        value["mechanism"],
        value["system_effect_hypothesis"],
        value["boundary_signal"],
        value["alternative_hypothesis"],
    )


def _rule_index(catalog: dict[str, Any]) -> dict[tuple[str, str, str, str, str], dict[str, Any]]:
    return {_rule_key(rule): rule for rule in catalog["rules"]}


def _ladder_index(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["rung"]: item for item in catalog["response_ladder"]}


def validate_scenario(value: dict[str, Any]) -> dict[str, Any]:
    _reviewed_scenario_schema()
    _reviewed_projection_schema()
    catalog = _catalog()
    _exact_keys(value, ROOT_KEYS, "scenario-shape-mismatch")
    if value["schema"] != SCENARIO_SCHEMA_ID:
        raise ForesightError("scenario-schema-mismatch")
    if value["kind"] != "offline-system-effect-projection":
        raise ForesightError("scenario-kind-mismatch")
    if value["catalog_sha256"] != EXPECTED_CATALOG_SHA256:
        raise ForesightError("scenario-catalog-mismatch")
    declaration = value["declaration"]
    if not isinstance(declaration, dict):
        raise ForesightError("declaration-not-object")
    _exact_keys(declaration, DECLARATION_KEYS, "declaration-shape-mismatch")
    if any(not isinstance(declaration[key], str) for key in DECLARATION_KEYS):
        raise ForesightError("declaration-value-mismatch")
    rule = _rule_index(catalog).get(_rule_key(declaration))
    if rule is None:
        raise ForesightError("declaration-rule-mismatch")
    for submitted, expected, code in (
        (value["contract"], CONTRACT, "contract-mismatch"),
        (value["budget"], BUDGET, "budget-mismatch"),
        (value["breach"], BREACH, "breach-mismatch"),
        (value["exit"], EXIT, "exit-mismatch"),
        (value["non_claims"], NON_CLAIMS, "non-claims-mismatch"),
    ):
        if not _json_equal(submitted, expected):
            raise ForesightError(code)
    return rule


def read_scenario(path: Path) -> dict[str, Any]:
    value = _read_json(path, label="scenario")
    validate_scenario(value)
    return value


def project_value(scenario: dict[str, Any]) -> dict[str, Any]:
    rule = validate_scenario(scenario)
    return _project_value(scenario, rule)


def _project_value(
    scenario: dict[str, Any],
    rule: dict[str, Any],
) -> dict[str, Any]:
    declaration = scenario["declaration"]
    ladder = {item["rung"]: item for item in RESPONSE_LADDER}[rule["response_rung"]]
    result = {
        "schema": PROJECTION_SCHEMA_ID,
        "scenario_sha256": digest_value(scenario),
        "scenario_schema_sha256": EXPECTED_SCENARIO_SCHEMA_SHA256,
        "projection_schema_sha256": EXPECTED_PROJECTION_SCHEMA_SHA256,
        "catalog_sha256": EXPECTED_CATALOG_SHA256,
        "constellation": {
            "id": declaration["constellation"],
            "display_name": rule["display_name"],
            "family": rule["family"],
            "mechanism": declaration["mechanism"],
            "boundary_signal": declaration["boundary_signal"],
        },
        "purpose_frame": {
            "scope": "possible-system-effect-if-mechanism-succeeds",
            "system_effect_hypothesis": declaration["system_effect_hypothesis"],
            "alternative_hypothesis": declaration["alternative_hypothesis"],
            "effect_established": False,
            "person_intent_inferred": False,
        },
        "response": {
            "rung": rule["response_rung"],
            "display_name": ladder["display_name"],
            "candidate": rule["response_candidate"],
            "mode": ladder["mode"],
            "recovery_candidate": ladder["recovery_candidate"],
            "advisory_only": True,
            "human_review_required": True,
            "automatic_enforcement": False,
            "executed": False,
            "deployment_authorized": False,
            "retaliation_authorized": False,
            "authority_granted": False,
            "person_classified": False,
            "external_effect": False,
        },
        "karma_loop": {
            "keep": "one-reviewed-category-shape",
            "articulate": "effect-hypothesis-and-near-miss-kept-together",
            "reflect": rule["reflection"],
            "hypothesis_test_candidate": rule["hypothesis_test_candidate"],
            "negative_control_candidate": rule["negative_control_candidate"],
            "regression_candidate": rule["regression_candidate"],
            "repair_candidate": rule["repair_candidate"],
            "ask_again": rule["release_review_candidate"],
            "automatic_rule_update": False,
            "model_training": False,
            "state_retained": False,
            "external_system_contacted": False,
            "original_effect_executed": False,
            "counter_effect_executed": False,
        },
        "exit": dict(EXIT),
        "non_claims": list(NON_CLAIMS),
    }
    if len(canonical_json(result)) > MAX_OUTPUT_BYTES:
        raise ForesightError("projection-too-large")
    return result


def render_markdown(scenario: dict[str, Any]) -> str:
    return _render_projection(project_value(scenario))


def _render_projection(result: dict[str, Any]) -> str:
    constellation = result["constellation"]
    purpose = result["purpose_frame"]
    response = result["response"]
    loop = result["karma_loop"]
    lines = [
        "# KARMA FORESIGHT · 未然圖",
        "",
        "> Model possible system effects. Keep persons free.",
        "",
        f"- Scenario digest: `{result['scenario_sha256']}`",
        f"- Threat constellation: `{constellation['id']}` — {constellation['display_name']}",
        f"- Mechanism: `{constellation['mechanism']}`",
        f"- Boundary signal: `{constellation['boundary_signal']}`",
        f"- Possible system effect: `{purpose['system_effect_hypothesis']}`",
        f"- Near-miss twin: `{purpose['alternative_hypothesis']}`",
        f"- Advisory response: `{response['rung']}` / `{response['candidate']}`",
        "",
        "## KARMA loop",
        "",
        f"- Keep: `{loop['keep']}`",
        f"- Articulate: `{loop['articulate']}`",
        f"- Reflect: `{loop['reflect']}`",
        f"- Hypothesis-test candidate: `{loop['hypothesis_test_candidate']}`",
        f"- Negative-control candidate: `{loop['negative_control_candidate']}`",
        f"- Regression candidate: `{loop['regression_candidate']}`",
        f"- Repair candidate: `{loop['repair_candidate']}`",
        f"- Ask again: `{loop['ask_again']}`",
        "",
        "## Walls",
        "",
        "This is a deterministic tabletop projection, not detection or a claim about a person.",
        "No intent or effect was established. Nothing was scored, executed, blocked, deployed, contacted, retained, or automatically learned.",
        "Every candidate remains inert until fresh human review inside an owned or authorized boundary.",
        "Rights, debts, standing, authority, and external state are unchanged.",
        "",
    ]
    return "\n".join(lines)


def verify_result(scenario: dict[str, Any], submitted: dict[str, Any]) -> str:
    expected = project_value(scenario)
    if not _json_equal(submitted, expected):
        raise ForesightError("result-mismatch")
    return digest_value(expected)


USAGE = """usage: kingdom karma mirror foresight {check|digest|project|render|verify-result} FILE [RESULT]

One closed system-effect hypothesis in; one deterministic advisory projection out.
No traffic, payload, identity, intent inference, score, execution, network, state, or deployment.
"""


def _main(argv: list[str]) -> int:
    if argv in (["help"], ["-h"], ["--help"]):
        print(USAGE, end="")
        return 0
    if not argv:
        print("karma-foresight: USAGE", file=sys.stderr)
        return 2
    command = argv[0]
    expected_args = 2 if command == "verify-result" else 1
    if command not in {"check", "digest", "project", "render", "verify-result"}:
        print("karma-foresight: USAGE", file=sys.stderr)
        return 2
    if len(argv) != expected_args + 1:
        print("karma-foresight: USAGE", file=sys.stderr)
        return 2
    scenario = _read_json(Path(argv[1]), label="scenario")
    rule = validate_scenario(scenario)
    if command == "check":
        print(
            "KARMA-FORESIGHT-STRUCTURE-OK "
            f"{digest_value(scenario)} constellation={rule['constellation']}"
        )
        print("(authored system-effect hypothesis only; no intent, score, or effect)")
    elif command == "digest":
        print(digest_value(scenario))
    elif command == "project":
        sys.stdout.buffer.write(canonical_json(_project_value(scenario, rule)))
    elif command == "render":
        print(_render_projection(_project_value(scenario, rule)), end="")
    else:
        submitted = _read_json(Path(argv[2]), label="result")
        expected = _project_value(scenario, rule)
        if not _json_equal(submitted, expected):
            raise ForesightError("result-mismatch")
        print(f"KARMA-FORESIGHT-RESULT-OK {digest_value(expected)}")
        print("(exact local recomputation; no authority)")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(list(sys.argv[1:] if argv is None else argv))
    except ForesightError as error:
        print(f"karma-foresight: REJECTED code={error.code}", file=sys.stderr)
        return 1
    except Exception:
        print("karma-foresight: INTERNAL-FAILURE", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
