#!/usr/bin/env python3
"""Compile one privacy-scrubbed incident claim into one inert FACET brief.

FACET is not an incident detector, log, evidence store, alerting system,
responder, closer, or publisher.  It binds one closed card to one exactly
recomputed KARMA FORESIGHT pair, exposes verification debt, and prints fixed
review candidates.  It has no network, subprocess, write, clock, randomness,
retry, model, identity, raw-evidence, or cross-run state path.
"""

from __future__ import annotations

import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import foresight as foresight_core


HERE = Path(__file__).resolve().parent
FACET_DIR = HERE / "facet"
FACET_SCHEMA_ID = "kingdom.karma-facet/v1"
BRIEF_SCHEMA_ID = "kingdom.karma-facet-brief/v1"
CATALOG_SCHEMA_ID = "kingdom.karma-facet-catalog/v1"
PLAYBOOK_SCHEMA_ID = "kingdom.karma-facet-playbook/v1"
EXPECTED_CATALOG_SHA256 = "ee751c456b3d2c7cf9f82a5b97698fbdf9b319e9ddf990b1440756ec1414dbc2"
EXPECTED_PLAYBOOK_SHA256 = "5753ac3dc00a9c8b262808b846b380c4dbd184e24452bb521dacb9052c85d5d7"
EXPECTED_FACET_SCHEMA_SHA256 = "8cf120b340600631ded53fc9a36fbbfed9f9a73836cf596305150a48bf05d84e"
EXPECTED_BRIEF_SCHEMA_SHA256 = "66970d1ec2ec18c83d41733b637e177c6add44df14328441610968f9202dc096"
MAX_FILE_BYTES = 32_768
MAX_NODES = 512
MAX_REVIEWED_NODES = 2_048
MAX_DEPTH = 8
MAX_STRING = 256
MAX_OUTPUT_BYTES = 16_384

STIMULI = [
    "authority-or-scope-change-requested",
    "playbook-drift-observed",
    "volume-budget-crossed",
    "privacy-release-risk",
    "claim-contested",
    "recovery-evidence-missing",
    "closure-review-requested",
    "new-authored-claim",
    "unresolved-novelty",
]
REVIEW_REQUESTS = [
    "triage",
    "investigation",
    "mitigation-review",
    "recovery-review",
    "closure-review",
]
CONDITION_STATES = ["met", "not-met", "unknown"]
RECEIPT_STATUSES = ["receipt-cited", "contested"]
RECEIPT_METHODS = [
    "canonical-byte-check",
    "deterministic-local-reproduction",
    "negative-control",
    "authority-envelope-review",
    "recovery-rehearsal",
    "independent-human-review",
    "sanitized-system-record",
]
RECEIPT_LINEAGES = [
    "single-source",
    "shared-source",
    "unknown",
    "independence-claimed",
]
RECEIPT_SLOTS = [
    "occurrence",
    "scope-authority",
    "evidence-integrity",
    "source-lineage",
    "counterevidence",
    "containment",
    "recovery",
    "privacy-release",
]

CONTRACT = {
    "assessment_unit": "one-authored-system-incident-claim",
    "incident_is_authored_not_detected": True,
    "occurrence_established": False,
    "source_authenticity_verified": False,
    "latest_state_established": False,
    "person_intent_inferred": False,
    "person_attributed": False,
    "identity_fields_allowed": False,
    "raw_evidence_allowed": False,
    "free_text_fields_allowed": False,
    "scores_or_severity": False,
    "automatic_detection": False,
    "automatic_alerting": False,
    "automatic_ticketing": False,
    "automatic_enforcement": False,
    "automatic_closure": False,
    "automatic_rule_update": False,
    "human_review_required_for_action": True,
    "owned_or_authorized_boundary_required": True,
    "retaliation": False,
    "hack_back": False,
    "executes_input": False,
    "executes_response": False,
    "publishes_output": False,
    "creates_external_effect": False,
}
BUDGET = {
    "cards": 1,
    "stimuli": 1,
    "passes": 1,
    "observations_max": 4,
    "unknowns_max": 5,
    "precommits_max": 3,
    "receipt_slots": 8,
    "debt_entries": 8,
    "file_bytes_max": MAX_FILE_BYTES,
    "decoded_nodes_max": MAX_NODES,
    "nesting_depth_max": MAX_DEPTH,
    "string_characters_max": MAX_STRING,
    "output_bytes_max": MAX_OUTPUT_BYTES,
    "automatic_retries": 0,
    "clock_reads": 0,
    "random_draws": 0,
    "network_calls": 0,
    "external_messages": 0,
    "writes": 0,
    "subprocesses": 0,
    "model_calls": 0,
    "paid_calls": 0,
    "alerts": 0,
    "tickets": 0,
    "enforcements": 0,
    "publications": 0,
    "payload_bytes_retained": 0,
    "raw_evidence_bytes_retained": 0,
    "identity_records": 0,
    "cross_run_records": 0,
}
BREACH = {
    "state": "quarantined",
    "action": "stop-without-retry-or-result",
    "source_unchanged": True,
    "submitted_values_echoed": False,
    "submitted_paths_echoed": False,
    "partial_brief": False,
    "downstream_effects": False,
}
EXIT = {
    "action": "return-or-discard-one-brief",
    "state_retained": False,
    "history_retained": False,
    "standing_created": False,
    "authority_created": False,
    "closure_created": False,
    "publication_created": False,
    "follow_up": False,
}
NON_CLAIMS = [
    "A Facet Brief is one bounded current declaration, not a complete incident record, log, timeline, alert, report, or source of truth.",
    "The O plane names an authored receipt shape; the compiler does not observe reality or verify that an event occurred.",
    "The compiler does not establish occurrence, source authenticity, effect, impact, cause, chronology, latest state, or root cause.",
    "The D and I planes do not prove intent, guilt, attribution, blame, identity, or any person's character or worth.",
    "The U plane is not adverse evidence; declared unknowns are finite and cannot establish that no other unknown exists.",
    "Safety Shims are reversible review candidates, not authorization, execution, enforcement, deployment, publication, or legal advice.",
    "Open Angles are system verification debt, never person debt, punishment, balance, score, rank, access, trust, or reputation; receipt-cited is not paid.",
    "A receipt digest can be correlating or a low-entropy oracle and is not proof of privacy, provenance, independence, truth, or custody.",
    "Return Fit and Repair Grain fields do not prove recovery, closure, recurrence, learning, adoption, or future conduct.",
    "No raw payload, evidence body, log, trace, prompt, address, identity, credential, target, command, URL, timestamp, free text, or cross-run profile is accepted or emitted.",
]

ROOT_KEYS = {
    "schema", "kind", "catalog_sha256", "playbook_sha256", "lineage",
    "foresight_binding", "stimulus", "review_request", "planes", "precommit",
    "receipts", "contract", "budget", "breach", "exit", "non_claims",
}
RULE_KEYS = {
    "constellation", "response_rung", "scope_code", "fact_code",
    "system_effect_hypothesis", "alternative_hypothesis", "repair_grain",
}
OBSERVED_KEYS = {"fact_code", "evidence_shape", "check_state"}
DECLARED_KEYS = {"scope_code", "constellation", "alternative_hypothesis"}
INFERRED_KEYS = {"system_effect_hypothesis", "effect_established", "person_intent_inferred"}
PRECOMMIT_KEYS = {"safety_shim_code", "condition_state"}
RECEIPT_KEYS = {"status", "sanitized_receipt_sha256", "method", "lineage"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class FacetError(ValueError):
    """One fixed public rejection code; never includes submitted material."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


canonical_json = foresight_core.canonical_json
digest_value = foresight_core.digest_value


def _json_equal(left: Any, right: Any) -> bool:
    return canonical_json(left) == canonical_json(right)


def _exact_keys(value: dict[str, Any], expected: set[str], code: str) -> None:
    if set(value) != expected:
        raise FacetError(code)


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _walk_facet_limits(value: Any) -> None:
    nodes = 0
    pending = [(value, 0)]
    while pending:
        current, depth = pending.pop()
        nodes += 1
        if nodes > MAX_NODES:
            raise FacetError("too-many-nodes")
        if depth > MAX_DEPTH:
            raise FacetError("too-deep")
        if isinstance(current, dict):
            for key, child in current.items():
                if len(key) > MAX_STRING:
                    raise FacetError("string-too-long")
                pending.append((child, depth + 1))
        elif isinstance(current, list):
            pending.extend((child, depth + 1) for child in current)
        elif isinstance(current, str) and len(current) > MAX_STRING:
            raise FacetError("string-too-long")


def _read_json(path: Path, *, label: str, node_limit: int = MAX_NODES) -> dict[str, Any]:
    try:
        value = foresight_core._read_json(path, label=label, node_limit=node_limit)
    except foresight_core.ForesightError as error:
        raise FacetError(error.code) from error
    if node_limit == MAX_NODES:
        _walk_facet_limits(value)
    return value


@lru_cache(maxsize=1)
def _reviewed_facet_schema() -> dict[str, Any]:
    value = _read_json(FACET_DIR / "facet.schema.json", label="facet-schema", node_limit=MAX_REVIEWED_NODES)
    if digest_value(value) != EXPECTED_FACET_SCHEMA_SHA256:
        raise FacetError("facet-schema-digest-mismatch")
    return value


@lru_cache(maxsize=1)
def _reviewed_brief_schema() -> dict[str, Any]:
    value = _read_json(FACET_DIR / "brief.schema.json", label="brief-schema", node_limit=MAX_REVIEWED_NODES)
    if digest_value(value) != EXPECTED_BRIEF_SCHEMA_SHA256:
        raise FacetError("brief-schema-digest-mismatch")
    return value


@lru_cache(maxsize=1)
def _catalog() -> dict[str, Any]:
    value = _read_json(FACET_DIR / "catalog.json", label="facet-catalog", node_limit=MAX_REVIEWED_NODES)
    if digest_value(value) != EXPECTED_CATALOG_SHA256:
        raise FacetError("catalog-digest-mismatch")
    _exact_keys(value, {
        "schema", "name", "foresight_catalog_sha256", "facet_schema", "brief_schema",
        "evidence_shapes", "check_states", "unknown_codes", "rules", "contract", "budget",
        "breach", "exit", "non_claims",
    }, "catalog-shape-mismatch")
    if (
        value["schema"] != CATALOG_SCHEMA_ID
        or value["foresight_catalog_sha256"] != foresight_core.EXPECTED_CATALOG_SHA256
        or value["facet_schema"] != FACET_SCHEMA_ID
        or value["brief_schema"] != BRIEF_SCHEMA_ID
        or not _json_equal(value["contract"], CONTRACT)
        or not _json_equal(value["budget"], BUDGET)
        or not _json_equal(value["breach"], BREACH)
        or not _json_equal(value["exit"], EXIT)
        or not _json_equal(value["non_claims"], NON_CLAIMS)
    ):
        raise FacetError("catalog-contract-mismatch")
    rules = value["rules"]
    if not isinstance(rules, list) or len(rules) != 10:
        raise FacetError("catalog-rule-count-mismatch")
    constellations: set[str] = set()
    facts: set[str] = set()
    scopes: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) != RULE_KEYS:
            raise FacetError("catalog-rule-shape-mismatch")
        if any(not isinstance(child, str) or not child for child in rule.values()):
            raise FacetError("catalog-rule-value-mismatch")
        if (
            rule["constellation"] in constellations
            or rule["fact_code"] in facts
            or rule["scope_code"] in scopes
        ):
            raise FacetError("duplicate-catalog-rule")
        constellations.add(rule["constellation"])
        facts.add(rule["fact_code"])
        scopes.add(rule["scope_code"])
    foresight_rules = {rule["constellation"]: rule for rule in foresight_core._catalog()["rules"]}
    if set(foresight_rules) != constellations:
        raise FacetError("foresight-catalog-coverage-mismatch")
    for rule in rules:
        source = foresight_rules[rule["constellation"]]
        if (
            rule["response_rung"] != source["response_rung"]
            or rule["system_effect_hypothesis"] != source["system_effect_hypothesis"]
            or rule["alternative_hypothesis"] != source["alternative_hypothesis"]
        ):
            raise FacetError("foresight-catalog-binding-mismatch")
    return value


@lru_cache(maxsize=1)
def _playbook() -> dict[str, Any]:
    value = _read_json(FACET_DIR / "playbook.json", label="facet-playbook", node_limit=MAX_REVIEWED_NODES)
    if digest_value(value) != EXPECTED_PLAYBOOK_SHA256:
        raise FacetError("playbook-digest-mismatch")
    _exact_keys(value, {
        "schema", "name", "stimuli", "review_requests", "condition_states",
        "receipt_statuses", "receipt_methods", "receipt_lineages", "safety_shims",
        "rung_allowlists", "response_table", "debt_slots",
    }, "playbook-shape-mismatch")
    if (
        value["schema"] != PLAYBOOK_SCHEMA_ID
        or value["stimuli"] != STIMULI
        or value["review_requests"] != REVIEW_REQUESTS
        or value["condition_states"] != CONDITION_STATES
        or value["receipt_statuses"] != RECEIPT_STATUSES
        or value["receipt_methods"] != RECEIPT_METHODS
        or value["receipt_lineages"] != RECEIPT_LINEAGES
    ):
        raise FacetError("playbook-contract-mismatch")
    shims = value["safety_shims"]
    if not isinstance(shims, list) or len(shims) != 7:
        raise FacetError("safety-shim-count-mismatch")
    shim_codes: set[str] = set()
    for shim in shims:
        if not isinstance(shim, dict) or set(shim) != {"code", "condition", "rollback", "proof_required"}:
            raise FacetError("safety-shim-shape-mismatch")
        if any(not isinstance(child, str) or not child for child in shim.values()) or shim["code"] in shim_codes:
            raise FacetError("safety-shim-value-mismatch")
        shim_codes.add(shim["code"])
    allowlists = value["rung_allowlists"]
    if not isinstance(allowlists, list) or len(allowlists) != 5:
        raise FacetError("rung-allowlist-mismatch")
    for item in allowlists:
        if not isinstance(item, dict) or set(item) != {"rung", "allowed"}:
            raise FacetError("rung-allowlist-shape-mismatch")
        if not isinstance(item["allowed"], list) or not set(item["allowed"]).issubset(shim_codes):
            raise FacetError("rung-allowlist-value-mismatch")
    table = value["response_table"]
    if not isinstance(table, list) or len(table) != 10:
        raise FacetError("response-table-count-mismatch")
    for item in table:
        if not isinstance(item, dict) or set(item) != {
            "order", "stimulus", "guard", "candidate", "verification_candidate", "halt_if"
        }:
            raise FacetError("response-table-shape-mismatch")
        if item["stimulus"] not in STIMULI or any(not isinstance(child, str) or not child for child in item.values()):
            raise FacetError("response-table-value-mismatch")
    debts = value["debt_slots"]
    if not isinstance(debts, list) or [item.get("slot") for item in debts if isinstance(item, dict)] != RECEIPT_SLOTS:
        raise FacetError("debt-slot-mismatch")
    for item in debts:
        if set(item) != {"slot", "risk", "interest_trigger", "payment_required", "closure_blocking"}:
            raise FacetError("debt-slot-shape-mismatch")
        if item["risk"] not in {"critical", "high", "medium", "low"} or not isinstance(item["closure_blocking"], bool):
            raise FacetError("debt-slot-value-mismatch")
    return value


def _rule_index() -> dict[str, dict[str, Any]]:
    return {rule["constellation"]: rule for rule in _catalog()["rules"]}


def _shim_index() -> dict[str, dict[str, Any]]:
    return {shim["code"]: shim for shim in _playbook()["safety_shims"]}


def _allowed_shims() -> dict[str, set[str]]:
    return {item["rung"]: set(item["allowed"]) for item in _playbook()["rung_allowlists"]}


def validate_card(value: dict[str, Any]) -> dict[str, Any]:
    _reviewed_facet_schema()
    _reviewed_brief_schema()
    catalog = _catalog()
    playbook = _playbook()
    _walk_facet_limits(value)
    _exact_keys(value, ROOT_KEYS, "card-shape-mismatch")
    if value["schema"] != FACET_SCHEMA_ID or value["kind"] != "offline-incident-legibility":
        raise FacetError("card-identity-mismatch")
    if value["catalog_sha256"] != EXPECTED_CATALOG_SHA256 or value["playbook_sha256"] != EXPECTED_PLAYBOOK_SHA256:
        raise FacetError("card-reviewed-digest-mismatch")
    lineage = value["lineage"]
    if not isinstance(lineage, dict) or set(lineage) != {"mode", "previous_snapshot_sha256"}:
        raise FacetError("lineage-shape-mismatch")
    if lineage["mode"] == "genesis":
        if lineage["previous_snapshot_sha256"] is not None:
            raise FacetError("lineage-value-mismatch")
    elif lineage["mode"] == "successor":
        if not _sha256(lineage["previous_snapshot_sha256"]):
            raise FacetError("lineage-value-mismatch")
    else:
        raise FacetError("lineage-value-mismatch")
    binding = value["foresight_binding"]
    if not isinstance(binding, dict) or set(binding) != {"scenario_sha256", "projection_sha256", "constellation", "response_rung"}:
        raise FacetError("foresight-binding-shape-mismatch")
    if not _sha256(binding["scenario_sha256"]) or not _sha256(binding["projection_sha256"]):
        raise FacetError("foresight-binding-digest-mismatch")
    rule = _rule_index().get(binding["constellation"])
    if rule is None or binding["response_rung"] != rule["response_rung"]:
        raise FacetError("foresight-binding-category-mismatch")
    if value["stimulus"] not in playbook["stimuli"] or value["review_request"] not in playbook["review_requests"]:
        raise FacetError("review-shape-mismatch")
    if (binding["constellation"] == "uncharted-future-shape") != (value["stimulus"] == "unresolved-novelty"):
        raise FacetError("novelty-binding-mismatch")
    planes = value["planes"]
    if not isinstance(planes, dict) or set(planes) != {"observed", "declared", "inferred", "unknown"}:
        raise FacetError("planes-shape-mismatch")
    observed = planes["observed"]
    if not isinstance(observed, list) or not 1 <= len(observed) <= BUDGET["observations_max"]:
        raise FacetError("observed-count-mismatch")
    seen_observations: set[bytes] = set()
    for item in observed:
        if not isinstance(item, dict) or set(item) != OBSERVED_KEYS:
            raise FacetError("observed-shape-mismatch")
        if (
            item["fact_code"] != rule["fact_code"]
            or item["evidence_shape"] not in catalog["evidence_shapes"]
            or item["check_state"] not in catalog["check_states"]
            or (
                item["evidence_shape"] == "none"
                and item["check_state"] != "unresolved"
            )
        ):
            raise FacetError("observed-value-mismatch")
        encoded = canonical_json(item)
        if encoded in seen_observations:
            raise FacetError("duplicate-observation")
        seen_observations.add(encoded)
    declared = planes["declared"]
    if not isinstance(declared, dict) or set(declared) != DECLARED_KEYS or not _json_equal(declared, {
        "scope_code": rule["scope_code"],
        "constellation": rule["constellation"],
        "alternative_hypothesis": rule["alternative_hypothesis"],
    }):
        raise FacetError("declared-plane-mismatch")
    inferred = planes["inferred"]
    if not isinstance(inferred, dict) or set(inferred) != INFERRED_KEYS or not _json_equal(inferred, {
        "system_effect_hypothesis": rule["system_effect_hypothesis"],
        "effect_established": False,
        "person_intent_inferred": False,
    }):
        raise FacetError("inferred-plane-mismatch")
    unknown = planes["unknown"]
    if (
        not isinstance(unknown, list)
        or not 1 <= len(unknown) <= BUDGET["unknowns_max"]
        or len(set(unknown)) != len(unknown)
        or any(not isinstance(item, str) or item not in catalog["unknown_codes"] for item in unknown)
    ):
        raise FacetError("unknown-plane-mismatch")
    precommit = value["precommit"]
    if not isinstance(precommit, list) or not 1 <= len(precommit) <= BUDGET["precommits_max"]:
        raise FacetError("precommit-count-mismatch")
    seen_shims: set[str] = set()
    allowed = _allowed_shims()[rule["response_rung"]]
    for item in precommit:
        if not isinstance(item, dict) or set(item) != PRECOMMIT_KEYS:
            raise FacetError("precommit-shape-mismatch")
        code = item["safety_shim_code"]
        if code not in allowed or code in seen_shims or item["condition_state"] not in playbook["condition_states"]:
            raise FacetError("precommit-value-mismatch")
        seen_shims.add(code)
    receipts = value["receipts"]
    if not isinstance(receipts, dict) or set(receipts) != set(RECEIPT_SLOTS):
        raise FacetError("receipt-slots-mismatch")
    digest_receipts: dict[str, list[dict[str, Any]]] = {}
    for slot in RECEIPT_SLOTS:
        receipt = receipts[slot]
        if receipt is None:
            continue
        if not isinstance(receipt, dict) or set(receipt) != RECEIPT_KEYS:
            raise FacetError("receipt-shape-mismatch")
        if (
            receipt["status"] not in playbook["receipt_statuses"]
            or not _sha256(receipt["sanitized_receipt_sha256"])
            or receipt["method"] not in playbook["receipt_methods"]
            or receipt["lineage"] not in playbook["receipt_lineages"]
        ):
            raise FacetError("receipt-value-mismatch")
        digest_receipts.setdefault(receipt["sanitized_receipt_sha256"], []).append(receipt)
    for group in digest_receipts.values():
        if len(group) > 1 and any(item["lineage"] == "independence-claimed" for item in group):
            raise FacetError("receipt-independence-conflict")
    for submitted, expected, code in (
        (value["contract"], CONTRACT, "contract-mismatch"),
        (value["budget"], BUDGET, "budget-mismatch"),
        (value["breach"], BREACH, "breach-mismatch"),
        (value["exit"], EXIT, "exit-mismatch"),
        (value["non_claims"], NON_CLAIMS, "non-claims-mismatch"),
    ):
        if not _json_equal(submitted, expected):
            raise FacetError(code)
    return rule


def read_card(path: Path) -> dict[str, Any]:
    value = _read_json(path, label="facet-card")
    validate_card(value)
    return value


def _verify_foresight_binding(card: dict[str, Any], scenario: dict[str, Any], projection: dict[str, Any]) -> None:
    try:
        foresight_core.validate_scenario(scenario)
        foresight_core.verify_result(scenario, projection)
    except (foresight_core.ForesightError, KeyError, TypeError) as error:
        raise FacetError("foresight-binding-invalid") from error
    binding = card["foresight_binding"]
    if (
        digest_value(scenario) != binding["scenario_sha256"]
        or digest_value(projection) != binding["projection_sha256"]
        or scenario["declaration"]["constellation"] != binding["constellation"]
        or projection["constellation"]["id"] != binding["constellation"]
        or projection["response"]["rung"] != binding["response_rung"]
    ):
        raise FacetError("foresight-binding-mismatch")


def _receipt_state(receipt: Any) -> str:
    return "open" if receipt is None else receipt["status"]


def _debt_value(card: dict[str, Any], playbook: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], bool, bool]:
    receipts = card["receipts"]
    cited_digests = [
        receipt["sanitized_receipt_sha256"]
        for receipt in receipts.values()
        if receipt is not None and receipt["status"] == "receipt-cited"
    ]
    counts = {digest: cited_digests.count(digest) for digest in set(cited_digests)}
    debts: list[dict[str, Any]] = []
    critical_open: list[str] = []
    for definition in playbook["debt_slots"]:
        slot = definition["slot"]
        receipt = receipts[slot]
        state = _receipt_state(receipt)
        shared = bool(
            receipt is not None
            and receipt["status"] == "receipt-cited"
            and counts.get(receipt["sanitized_receipt_sha256"], 0) > 1
        )
        debt = {
            "slot": slot,
            "risk": definition["risk"],
            "state": state,
            "lineage": "none" if receipt is None else receipt["lineage"],
            "interest_trigger": definition["interest_trigger"],
            "payment_required": definition["payment_required"],
            "closure_blocking": definition["closure_blocking"],
            "receipt_cites_shared_digest": shared,
            "compiler_can_pay": False,
            "external_fact_established": False,
        }
        debts.append(debt)
        if definition["risk"] == "critical" and (state != "receipt-cited" or shared):
            critical_open.append(slot)
    all_cited = all(_receipt_state(receipts[slot]) == "receipt-cited" for slot in RECEIPT_SLOTS)
    distinct = len(cited_digests) == len(set(cited_digests)) == len(RECEIPT_SLOTS)
    return debts, critical_open, all_cited, distinct


def _response_value(card: dict[str, Any], playbook: dict[str, Any], closeout_ready: bool) -> dict[str, Any]:
    stimulus = card["stimulus"]
    candidates = [item for item in playbook["response_table"] if item["stimulus"] == stimulus]
    if stimulus == "closure-review-requested":
        selected = next(item for item in candidates if item["order"] == ("g6b" if closeout_ready else "g6a"))
    else:
        if len(candidates) != 1:
            raise FacetError("response-table-ambiguous")
        selected = candidates[0]
    return {
        "rule": selected["order"],
        "guard": selected["guard"],
        "candidate": selected["candidate"],
        "verification_candidate": selected["verification_candidate"],
        "halt_if": selected["halt_if"],
        "advisory_only": True,
        "human_review_required": True,
        "automatic_alert": False,
        "automatic_ticket": False,
        "automatic_enforcement": False,
        "execution_authorized": False,
        "executed": False,
        "closure_authorized": False,
        "publication_authorized": False,
        "authority_granted": False,
        "person_classified": False,
        "external_effect": False,
    }


def brief_value(card: dict[str, Any], scenario: dict[str, Any], projection: dict[str, Any]) -> dict[str, Any]:
    rule = validate_card(card)
    _verify_foresight_binding(card, scenario, projection)
    playbook = _playbook()
    debts, critical_open, all_cited, distinct = _debt_value(card, playbook)
    closeout_ready = (
        card["stimulus"] == "closure-review-requested"
        and card["review_request"] == "closure-review"
        and not critical_open
        and all_cited
        and distinct
    )
    shim_index = _shim_index()
    shims = []
    for declared in card["precommit"]:
        shim = shim_index[declared["safety_shim_code"]]
        shims.append({
            "code": shim["code"],
            "condition": shim["condition"],
            "condition_state": declared["condition_state"],
            "rollback": shim["rollback"],
            "proof_required": shim["proof_required"],
            "reversible": True,
            "human_activation_required": True,
            "execution_authorized": False,
            "executed": False,
            "external_effect": False,
        })
    result = {
        "schema": BRIEF_SCHEMA_ID,
        "card_sha256": digest_value(card),
        "card_schema_sha256": EXPECTED_FACET_SCHEMA_SHA256,
        "brief_schema_sha256": EXPECTED_BRIEF_SCHEMA_SHA256,
        "catalog_sha256": EXPECTED_CATALOG_SHA256,
        "playbook_sha256": EXPECTED_PLAYBOOK_SHA256,
        "foresight_binding": {
            **card["foresight_binding"],
            "exact_recomputation": True,
        },
        "lineage_claim": {
            "mode": card["lineage"]["mode"],
            "previous_snapshot_sha256": card["lineage"]["previous_snapshot_sha256"],
            "predecessor_verified": False,
            "chronology_established": False,
            "latest_state_established": False,
        },
        "incident_claim": {
            "stimulus": card["stimulus"],
            "review_request": card["review_request"],
            "incident_occurrence_established": False,
            "source_authenticity_verified": False,
            "system_effect_established": False,
            "cause_established": False,
            "person_intent_inferred": False,
            "person_attributed": False,
        },
        "brief": {
            "title": "KARMA FACET · 60-second incident brief",
            "read_seconds_target": 60,
            "line_budget": 12,
            "structural_state": "one-scrubbed-claim-compiled",
        },
        "planes": {
            "observed": [dict(item) for item in card["planes"]["observed"]],
            "declared": dict(card["planes"]["declared"]),
            "inferred": dict(card["planes"]["inferred"]),
            "unknown": list(card["planes"]["unknown"]),
        },
        "response": _response_value(card, playbook, closeout_ready),
        "safety_shims": shims,
        "evidence_debt": debts,
        "readiness": {
            "structure_valid": True,
            "critical_open_slots": critical_open,
            "all_receipt_shapes_cited": all_cited,
            "distinct_receipt_commitments": distinct,
            "fresh_human_closure_review_candidate": closeout_ready,
            "incident_truth_verified": False,
            "authenticity_verified": False,
            "privacy_release_authorized": False,
            "closure_authorized": False,
        },
        "return_fit": {
            "recovery_receipt_state": _receipt_state(card["receipts"]["recovery"]),
            "negative_control_receipt_state": _receipt_state(card["receipts"]["counterevidence"]),
            "proof_shape_complete": (
                _receipt_state(card["receipts"]["recovery"]) == "receipt-cited"
                and _receipt_state(card["receipts"]["counterevidence"]) == "receipt-cited"
            ),
            "recovery_established": False,
            "human_release_review_required": True,
        },
        "lessons": [{
            "repair_grain": rule["repair_grain"],
            "state": "candidate",
            "current_brief_only": True,
            "blame_assigned": False,
            "person_generalization": False,
            "recurrence_claimed": False,
            "automatic_adoption": False,
        }],
        "exit": dict(EXIT),
        "non_claims": list(NON_CLAIMS),
    }
    if len(canonical_json(result)) > MAX_OUTPUT_BYTES:
        raise FacetError("brief-too-large")
    return result


def render_markdown(card: dict[str, Any], scenario: dict[str, Any], projection: dict[str, Any]) -> str:
    result = brief_value(card, scenario, projection)
    planes = result["planes"]
    observed = ", ".join(
        f"{item['fact_code']}:{item['check_state']}" for item in planes["observed"]
    )
    unknown = ", ".join(planes["unknown"])
    shims = ", ".join(item["code"] for item in result["safety_shims"])
    debt = ", ".join(f"{item['slot']}={item['state']}" for item in result["evidence_debt"])
    return_fit = result["return_fit"]
    lines = [
        "# KARMA FACET · 稜面 — 60-second incident brief",
        f"O · {observed}",
        f"D · {planes['declared']['scope_code']} / {planes['declared']['constellation']}",
        f"D-alt · {planes['declared']['alternative_hypothesis']}",
        f"I · {planes['inferred']['system_effect_hypothesis']} (not established)",
        f"U · {unknown}",
        (
            f"Response · {result['incident_claim']['stimulus']} → {result['response']['candidate']} "
            f"(guard: {result['response']['guard']}; "
            f"review={result['incident_claim']['review_request']}; advisory; "
            f"halt: {result['response']['halt_if']})"
        ),
        f"Safety Shims · {shims} (human activation only)",
        f"Open Angles · {debt}",
        f"Return Fit · recovery={return_fit['recovery_receipt_state']} negative-control={return_fit['negative_control_receipt_state']} (not proof)",
        f"Repair Grain · {result['lessons'][0]['repair_grain']} (candidate only)",
        "Walls · no detection, identity, blame, alert, action, closure, publication, memory, or external effect.",
        "",
    ]
    return "\n".join(lines)


def verify_result(card: dict[str, Any], scenario: dict[str, Any], projection: dict[str, Any], submitted: dict[str, Any]) -> str:
    expected = brief_value(card, scenario, projection)
    if not _json_equal(submitted, expected):
        raise FacetError("result-mismatch")
    return digest_value(expected)


def verify_link(previous: dict[str, Any], current: dict[str, Any]) -> str:
    validate_card(previous)
    validate_card(current)
    if current["lineage"]["mode"] != "successor" or current["lineage"]["previous_snapshot_sha256"] != digest_value(previous):
        raise FacetError("snapshot-link-mismatch")
    return digest_value(current)


USAGE = """usage:
  kingdom incident {check|digest|brief|render} CARD FORESIGHT_SCENARIO FORESIGHT_PROJECTION
  kingdom incident verify-result CARD FORESIGHT_SCENARIO FORESIGHT_PROJECTION BRIEF
  kingdom incident verify-link PREVIOUS_CARD CURRENT_CARD

One scrubbed claim in; one deterministic 60-second FACET brief out.
No logs, evidence bodies, identity, alert, action, closure, publication, clock, or state.
"""


def _main(argv: list[str]) -> int:
    if argv in (["help"], ["-h"], ["--help"]):
        print(USAGE, end="")
        return 0
    if not argv:
        print("karma-facet: USAGE", file=sys.stderr)
        return 2
    command = argv[0]
    if command == "verify-link":
        if len(argv) != 3:
            print("karma-facet: USAGE", file=sys.stderr)
            return 2
        previous = _read_json(Path(argv[1]), label="previous-card")
        current = _read_json(Path(argv[2]), label="current-card")
        print(f"KARMA-FACET-LINK-OK {verify_link(previous, current)}")
        print("(canonical predecessor relation only; no chronology, latest state, truth, or authority)")
        return 0
    if command not in {"check", "digest", "brief", "render", "verify-result"}:
        print("karma-facet: USAGE", file=sys.stderr)
        return 2
    expected_length = 5 if command == "verify-result" else 4
    if len(argv) != expected_length:
        print("karma-facet: USAGE", file=sys.stderr)
        return 2
    card = _read_json(Path(argv[1]), label="facet-card")
    scenario = _read_json(Path(argv[2]), label="foresight-scenario")
    projection = _read_json(Path(argv[3]), label="foresight-projection")
    validate_card(card)
    _verify_foresight_binding(card, scenario, projection)
    if command == "check":
        print(
            "KARMA-FACET-STRUCTURE-OK "
            f"{digest_value(card)} constellation={card['foresight_binding']['constellation']}"
        )
        print("(authored incident claim only; no occurrence, identity, action, or closure)")
    elif command == "digest":
        print(digest_value(card))
    elif command == "brief":
        sys.stdout.buffer.write(canonical_json(brief_value(card, scenario, projection)))
    elif command == "render":
        print(render_markdown(card, scenario, projection), end="")
    else:
        submitted = _read_json(Path(argv[4]), label="facet-brief")
        print(f"KARMA-FACET-RESULT-OK {verify_result(card, scenario, projection, submitted)}")
        print("(exact local recomputation; no incident truth, recovery, closure, or authority)")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(list(sys.argv[1:] if argv is None else argv))
    except FacetError as error:
        print(f"karma-facet: REJECTED code={error.code}", file=sys.stderr)
        return 1
    except Exception:
        print("karma-facet: INTERNAL-FAILURE", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
