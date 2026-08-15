#!/usr/bin/env python3
"""Deterministic, offline incident explanation for verified Future-KARMA plans.

The engine accepts one closed categorical event plus its Future-KARMA receipt,
freshly replays the pinned planner, discards the supplied receipt object, and
emits either a bounded incident explanation or a human-review regression
candidate.  It never accepts raw traffic and has no live action path.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import stat
import sys
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

ENGINE = "incident-lantern/1"
INCIDENT_SCHEMA = "kingdom.incident/v1"
CANDIDATE_SCHEMA = "kingdom.karma.regression-candidate/v1"
INCIDENT_SCHEMA_ID = "incident.schema.json"
CANDIDATE_SCHEMA_ID = "regression-candidate.schema.json"
SOURCE_SCHEMA = "kingdom.incident-source/v1"
VERIFY_SCHEMA = "kingdom.incident-verify/v1"

HERE = Path(os.path.abspath(__file__)).parent
FUTURE_PATH = HERE.parent / "karma-defense-lab" / "future" / "future_karma.py"
FUTURE_ENGINE_SHA256 = "20f7869a69d3b985f842e047276ce17da98504ebde87b36c4a9593a131dddbac"
PINS = {
    "incident.schema.json": "e57d56f9313c803ef16a92cd8ad7024c83ca628be7b761594c7e598c50cbc1c4",
    "regression-candidate.schema.json": "21b46aaf1e0d265d7741c0bafcd2e0f81e95958da4ce84a05b770bf922f22fa0",
}

LIMITS = {
    "source_bytes": 16_384,
    "verify_bytes": 65_536,
    "candidate_bytes": 16_384,
    "incident_bytes": 32_768,
    "schema_bytes": 65_536,
    "nodes": 2_000,
    "depth": 20,
}

ZERO_CONTROLS = {
    "network_calls": 0,
    "process_spawns": 0,
    "model_calls": 0,
    "secret_reads": 0,
    "filesystem_writes": 0,
    "external_messages": 0,
    "authority_granted": False,
    "action_executed": False,
    "classifier_mutated": False,
    "engine_retained_records": 0,
}

CANDIDATE_NONCLAIMS = [
    "This candidate preserves a categorical fixture, not raw traffic or identity.",
    "It does not authenticate external provenance or establish intent, guilt, or impact.",
    "It does not install a rule, mutate a classifier, or authorize an action.",
    "Promotion requires joint human review of policy, threat model, corpus, pins, and tests.",
]

INCIDENT_NONCLAIMS = [
    "This incident explains one replay-verified offline categorical plan.",
    "It does not authenticate external provenance, event time, sequence, duplication, or live impact.",
    "It does not identify a person or infer intent, guilt, hostility, or reputation.",
    "Displayed actions are proposal-only and grant no authority or production effect.",
    "The regression candidate does not mutate the classifier or install a rule.",
    "Zero modelled effects do not prove operating-system confinement or deployment safety.",
]

WITHHELD_EVENT = {
    "retention": "digest-only",
    "schema": "kingdom.karma.event/v1",
    "surface": "withheld-unreviewed",
    "mechanism": "withheld-unreviewed",
    "signal": "withheld-unreviewed",
    "signal_quality": "unknown",
    "provenance": "unknown",
    "novelty": "ambiguous",
    "purpose": "defensive-regression",
    "scope": "offline-synthetic",
    "authority": "none",
    "evidence_count": 0,
}

ACTION_PRESENTATION = {
    "allow": (
        "Maintain the reviewed path",
        "The pinned policy selected its bounded negative-control posture.",
    ),
    "observe": (
        "Increase bounded observation",
        "Collect only the minimum categorical evidence needed for another review.",
    ),
    "throttle": (
        "Review a bounded throttle",
        "Reduce pressure at an owned boundary while preserving a rollback path.",
    ),
    "deny": (
        "Review a bounded deny",
        "Stop the reviewed categorical path only at a boundary the responder owns.",
    ),
    "quarantine": (
        "Keep the boundary quarantined",
        "Hold uncertain input away from broader state until evidence and authority are clear.",
    ),
    "synthetic-mirror": (
        "Review the sterile mirror candidate",
        "Keep any mirror isolated, no-egress, single-attempt, and entirely synthetic.",
    ),
}


class LanternError(ValueError):
    """Malformed, unverifiable, drifted, or over-budget Lantern input."""


def _read_regular(path: Path, *, limit: int) -> bytes:
    descriptor = -1
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
        )
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise LanternError()
        with os.fdopen(descriptor, "rb", closefd=True) as handle:
            descriptor = -1
            payload = handle.read(limit + 1)
    except LanternError:
        raise
    except (OSError, ValueError) as exc:
        raise LanternError() from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(payload) > limit:
        raise LanternError()
    return payload


def _load_future() -> Any:
    source = _read_regular(FUTURE_PATH, limit=131_072)
    if hashlib.sha256(source).hexdigest() != FUTURE_ENGINE_SHA256:
        raise LanternError()
    specification = importlib.util.spec_from_file_location(
        "_incident_lantern_future_karma", FUTURE_PATH
    )
    if specification is None or specification.loader is None:
        raise LanternError()
    module = importlib.util.module_from_spec(specification)
    exec(compile(source, str(FUTURE_PATH), "exec", dont_inherit=True), module.__dict__)
    if Path(module.__file__).absolute() != FUTURE_PATH.absolute():
        raise LanternError()
    if module.ENGINE != "future-karma/1":
        raise LanternError()
    return module


try:
    _ENGINE_SHA256 = hashlib.sha256(
        _read_regular(HERE / "incident_lantern.py", limit=131_072)
    ).hexdigest()
    future = _load_future()
except Exception:
    if __name__ == "__main__":
        sys.stderr.buffer.write(b"incident-lantern: rejected\n")
        raise SystemExit(2) from None
    raise


def _canonical(value: Any) -> bytes:
    return future._canonical(value)


def _digest(value: Any) -> str:
    return future._digest(value)


def _clone(value: Any) -> Any:
    return future._decode_json(
        _canonical(value),
        max_bytes=LIMITS["verify_bytes"],
        max_nodes=LIMITS["nodes"],
        max_depth=LIMITS["depth"],
    )


def _exact(value: Any, keys: tuple[str, ...] | list[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != set(keys):
        raise LanternError()
    return value


def _is_token(value: Any, *, maximum: int = 64) -> bool:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= maximum
        and value[0] in "abcdefghijklmnopqrstuvwxyz0123456789"
        and value[-1] in "abcdefghijklmnopqrstuvwxyz0123456789"
        and all(character in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in value)
        and "--" not in value
    )


def _is_digest(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _engine_sha256() -> str:
    current = hashlib.sha256(
        _read_regular(HERE / "incident_lantern.py", limit=131_072)
    ).hexdigest()
    if current != _ENGINE_SHA256:
        raise LanternError()
    return _ENGINE_SHA256


def _load_schema(name: str, expected_id: str) -> dict[str, Any]:
    payload = _read_regular(HERE / name, limit=LIMITS["schema_bytes"])
    if hashlib.sha256(payload).hexdigest() != PINS[name]:
        raise LanternError()
    try:
        value = future._decode_json(
            payload,
            max_bytes=LIMITS["schema_bytes"],
            max_nodes=12_000,
            max_depth=24,
        )
    except future.InvalidInput as exc:
        raise LanternError() from exc
    schema = _exact(value, tuple(value))
    if (
        schema.get("$id") != expected_id
        or schema.get("type") != "object"
        or schema.get("additionalProperties") is not False
        or set(schema.get("required", [])) != set(schema.get("properties", {}))
    ):
        raise LanternError()
    return schema


def load_contract() -> dict[str, Any]:
    incident_schema = _load_schema("incident.schema.json", INCIDENT_SCHEMA_ID)
    candidate_schema = _load_schema(
        "regression-candidate.schema.json", CANDIDATE_SCHEMA_ID
    )
    bundle = future.load_bundle()
    future_bindings = future._thaw(bundle["bindings"])
    if future_bindings["engine_sha256"] != FUTURE_ENGINE_SHA256:
        raise LanternError()
    bindings = {
        "incident_engine_sha256": _engine_sha256(),
        "incident_schema_sha256": PINS["incident.schema.json"],
        "candidate_schema_sha256": PINS["regression-candidate.schema.json"],
        "future_engine_sha256": future_bindings["engine_sha256"],
        "policy_sha256": future_bindings["policy_sha256"],
        "event_schema_sha256": future_bindings["event_schema_sha256"],
        "receipt_schema_sha256": future_bindings["receipt_schema_sha256"],
        "threat_model_sha256": future_bindings["threat_model_sha256"],
    }
    return {
        "incident_schema": incident_schema,
        "candidate_schema": candidate_schema,
        "bundle": bundle,
        "bindings": bindings,
    }


def _source_parts(wrapper: Any, contract: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    source = _exact(wrapper, ("schema", "event", "receipt"))
    if source["schema"] != SOURCE_SCHEMA:
        raise LanternError()
    event = _clone(source["event"])
    supplied_receipt = source["receipt"]
    try:
        future.validate_event(event)
        expected = future.plan_event(event, contract["bundle"])
        verified = future.verify_receipt(event, supplied_receipt, contract["bundle"])
    except future.KarmaError as exc:
        raise LanternError() from exc
    if not verified:
        raise LanternError()
    return event, _clone(expected)


def _future_bindings(bindings: dict[str, str]) -> dict[str, str]:
    return {
        key: bindings[key]
        for key in (
            "future_engine_sha256",
            "policy_sha256",
            "event_schema_sha256",
            "receipt_schema_sha256",
            "threat_model_sha256",
        )
    }


def _expected_projection(receipt: dict[str, Any]) -> dict[str, Any]:
    decision = receipt["decision"]
    return {
        "status": receipt["status"],
        "classification": receipt["event"]["classification"],
        "rule_id": decision["rule_id"],
        "threat_id": decision["threat_id"],
        "action": decision["action"],
        "fallback": decision["fallback"],
        "severity": decision["severity"],
        "halt_code": decision["halt_code"],
        "mirror": _clone(decision["mirror"]),
    }


def _project_event(event: dict[str, Any], *, planned: bool) -> dict[str, Any]:
    if not planned:
        return _clone(WITHHELD_EVENT)
    projection = {"retention": "reviewed-categorical"}
    projection.update(_clone(event))
    return projection


def _candidate_from_parts(
    event: dict[str, Any], receipt: dict[str, Any], contract: dict[str, Any]
) -> dict[str, Any]:
    planned = receipt["status"] == "planned"
    event_digest = _digest(event)
    receipt_digest = receipt["receipt_digest"]
    identifier = _digest(
        {"event_digest": event_digest, "receipt_digest": receipt_digest}
    )[:16]
    value: dict[str, Any] = {
        "schema": CANDIDATE_SCHEMA,
        "candidate_id": "candidate-" + identifier,
        "source": {
            "event_digest": event_digest,
            "receipt_digest": receipt_digest,
            "bindings": _future_bindings(contract["bindings"]),
        },
        "event": _project_event(event, planned=planned),
        "expected": _expected_projection(receipt),
        "promotion": {
            "state": "human-review-required",
            "eligibility": "reviewed-match" if planned else "blocked-until-mapped",
            "automatic_install": False,
            "classifier_mutated": False,
            "authority": "none",
        },
        "nonclaims": list(CANDIDATE_NONCLAIMS),
    }
    value["candidate_digest"] = _digest(value)
    return value


def validate_candidate(value: Any, contract: dict[str, Any]) -> dict[str, Any]:
    candidate = _exact(
        value,
        (
            "schema", "candidate_id", "source", "event", "expected",
            "promotion", "nonclaims", "candidate_digest",
        ),
    )
    if candidate["schema"] != CANDIDATE_SCHEMA or not _is_token(candidate["candidate_id"]):
        raise LanternError()
    source = _exact(candidate["source"], ("event_digest", "receipt_digest", "bindings"))
    if not _is_digest(source["event_digest"]) or not _is_digest(source["receipt_digest"]):
        raise LanternError()
    expected_identifier = "candidate-" + _digest(
        {
            "event_digest": source["event_digest"],
            "receipt_digest": source["receipt_digest"],
        }
    )[:16]
    if candidate["candidate_id"] != expected_identifier:
        raise LanternError()
    if _canonical(source["bindings"]) != _canonical(_future_bindings(contract["bindings"])):
        raise LanternError()

    event_projection = _exact(
        candidate["event"],
        (
            "retention", "schema", "surface", "mechanism", "signal",
            "signal_quality", "provenance", "novelty", "purpose", "scope",
            "authority", "evidence_count",
        ),
    )
    retention = event_projection["retention"]
    event = {key: child for key, child in event_projection.items() if key != "retention"}
    future.validate_event(event)

    expected = _exact(
        candidate["expected"],
        (
            "status", "classification", "rule_id", "threat_id", "action",
            "fallback", "severity", "halt_code", "mirror",
        ),
    )
    mirror = _exact(expected["mirror"], ("mode", "max_attempts", "egress"))
    if (
        expected["status"] not in {"planned", "halted"}
        or expected["classification"] not in {
            "reviewed-categorical", "unmatched-categorical",
            "uncertain-categorical", "insufficient-categorical",
        }
        or expected["action"] not in future.ALLOWED_ACTIONS
        or expected["fallback"] not in {"deny", "quarantine"}
        or type(expected["severity"]) is not int
        or not 0 <= expected["severity"] <= 5
        or not _is_token(expected["rule_id"], maximum=48)
        or not _is_token(expected["threat_id"], maximum=48)
        or not _is_token(expected["halt_code"], maximum=48)
        or mirror["mode"] not in {"none", "isolated-no-egress"}
        or type(mirror["max_attempts"]) is not int
        or mirror["max_attempts"] not in {0, 1}
        or mirror["egress"] is not False
    ):
        raise LanternError()

    promotion = _exact(
        candidate["promotion"],
        ("state", "eligibility", "automatic_install", "classifier_mutated", "authority"),
    )
    planned = expected["status"] == "planned"
    expected_promotion = {
        "state": "human-review-required",
        "eligibility": "reviewed-match" if planned else "blocked-until-mapped",
        "automatic_install": False,
        "classifier_mutated": False,
        "authority": "none",
    }
    if (
        promotion["state"] != expected_promotion["state"]
        or promotion["eligibility"] != expected_promotion["eligibility"]
        or promotion["automatic_install"] is not False
        or promotion["classifier_mutated"] is not False
        or promotion["authority"] != "none"
        or candidate["nonclaims"] != CANDIDATE_NONCLAIMS
    ):
        raise LanternError()
    if planned:
        if (
            retention != "reviewed-categorical"
            or _digest(event) != source["event_digest"]
            or expected["classification"] != "reviewed-categorical"
            or expected["halt_code"] != "none"
            or expected["rule_id"] == "none"
            or expected["threat_id"] == "none"
        ):
            raise LanternError()
        replayed = future.plan_event(event, contract["bundle"])
        if (
            replayed["receipt_digest"] != source["receipt_digest"]
            or _canonical(_expected_projection(replayed)) != _canonical(expected)
        ):
            raise LanternError()
    else:
        halted_codes = {
            "unmatched-categorical": "unmatched-selector",
            "uncertain-categorical": "boundary-uncertain",
            "insufficient-categorical": "insufficient-evidence",
        }
        if (
            retention != "digest-only"
            or _canonical(event_projection) != _canonical(WITHHELD_EVENT)
            or expected["classification"] not in halted_codes
            or expected["action"] != "quarantine"
            or expected["fallback"] != "deny"
            or expected["severity"] != 5
            or expected["rule_id"] != "none"
            or expected["threat_id"] != "none"
            or expected["halt_code"] != halted_codes[expected["classification"]]
            or expected["mirror"] != {"mode": "none", "max_attempts": 0, "egress": False}
        ):
            raise LanternError()
    unsigned = {key: child for key, child in candidate.items() if key != "candidate_digest"}
    if not _is_digest(candidate["candidate_digest"]) or candidate["candidate_digest"] != _digest(unsigned):
        raise LanternError()
    if len(_canonical(candidate)) + 1 > LIMITS["candidate_bytes"]:
        raise LanternError()
    return _clone(candidate)


def candidate_value(wrapper: Any, contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = load_contract() if contract is None else contract
    event, expected_receipt = _source_parts(wrapper, contract)
    candidate = _candidate_from_parts(event, expected_receipt, contract)
    return validate_candidate(candidate, contract)


def _threat(candidate: dict[str, Any], contract: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    threat_id = candidate["expected"]["threat_id"]
    classes = contract["bundle"]["threat_model"]["classes"]
    for raw in classes:
        item = future._thaw(raw)
        if item["id"] == threat_id:
            return (
                {
                    "id": item["id"],
                    "title": item["title"],
                    "evidence_status": item["evidence_status"],
                },
                {
                    "detection": item["detection"],
                    "containment": item["containment"],
                    "recovery": item["recovery"],
                    "privacy_output": item["privacy_output"],
                },
            )
    return (
        {
            "id": "none",
            "title": "Unmapped categorical boundary",
            "evidence_status": "unknown",
        },
        {
            "detection": "Preserve only the source and receipt digests for human review.",
            "containment": "Keep the boundary quarantined; do not interpret withheld values.",
            "recovery": "Author a reviewed fixture and policy mapping before any promotion.",
            "privacy_output": "Withhold unreviewed categorical values and all raw source data.",
        },
    )


def _epistemics(candidate: dict[str, Any], threat: dict[str, Any]) -> dict[str, Any]:
    expected = candidate["expected"]
    planned = expected["status"] == "planned"
    facts = [
        {
            "id": "categorical-contract",
            "statement": "A closed categorical event passed the pinned Future KARMA event contract.",
            "refs": ["source.event_digest"],
            "confidence": "confirmed",
            "resolution": "replay-verified",
        },
        {
            "id": "scope-boundary",
            "statement": "The source declares offline-synthetic scope and grants no authority.",
            "refs": ["source.event_digest", "controls.authority_granted"],
            "confidence": "confirmed",
            "resolution": "replay-verified",
        },
        {
            "id": "receipt-replay",
            "statement": "The supplied receipt matched a fresh deterministic planner replay.",
            "refs": ["source.receipt_digest"],
            "confidence": "confirmed",
            "resolution": "replay-verified",
        },
        {
            "id": "policy-disposition",
            "statement": "The pinned policy produced the displayed proposal without executing it.",
            "refs": ["headline.planned_action", "source.bindings.policy_sha256"],
            "confidence": "confirmed",
            "resolution": "catalog-derived",
        },
    ]
    inferences = [
        {
            "id": "threat-family-reading",
            "statement": (
                "The pinned model maps the reviewed selector to " + threat["title"] + "."
                if planned
                else "No reviewed threat family was established; the boundary halt remains unresolved."
            ),
            "refs": ["learning.threat.id", "source.receipt_digest"],
            "confidence": "policy-derived",
            "resolution": "catalog-derived" if planned else "human-review-required",
        },
        {
            "id": "response-posture-reading",
            "statement": "The displayed action is a decision aid, not evidence that containment occurred.",
            "refs": ["headline.planned_action", "controls.action_executed"],
            "confidence": "policy-derived",
            "resolution": "human-review-required",
        },
    ]
    unknown_specs = [
        ("external-provenance", "Whether an external observation was authentic or complete.", "outside-source-contract", ["source.event_digest"]),
        ("identity-and-intent", "Any actor identity, intent, guilt, hostility, or reputation.", "outside-source-contract", ["source.event_digest"]),
        ("live-impact", "Real-world impact, production exposure, and current blast radius.", "human-review-required", ["headline.severity"]),
        ("time-and-sequence", "Event time, ordering, duplication, and recurrence.", "outside-source-contract", ["source.event_digest"]),
        ("containment-state", "Whether an authorized containment action was actually executed and verified.", "human-review-required", ["controls.action_executed"]),
        ("retention-state", "Whether caller-owned retention and deletion duties were enforced.", "outside-source-contract", ["source.receipt_digest"]),
    ]
    if not planned:
        unknown_specs.append(
            (
                "withheld-selector",
                "The meaning and safe mapping of the withheld unreviewed categorical selector.",
                "human-review-required",
                ["source.event_digest", "headline.disposition"],
            )
        )
    unknowns = [
        {
            "id": identifier,
            "statement": statement,
            "refs": refs,
            "confidence": "unknown",
            "resolution": resolution,
        }
        for identifier, statement, resolution, refs in unknown_specs
    ]
    return {"facts": facts, "inferences": inferences, "unknowns": unknowns}


def _timeline(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    halted = candidate["expected"]["status"] == "halted"
    return [
        {"ordinal": 1, "phase": "categorical-observation", "state": "complete", "label": "Bounded categorical observation received", "refs": ["source.event_digest"]},
        {"ordinal": 2, "phase": "source-bindings-validated", "state": "complete", "label": "Pinned planner and catalogs validated", "refs": ["source.bindings.future_engine_sha256", "source.bindings.policy_sha256"]},
        {"ordinal": 3, "phase": "receipt-replayed", "state": "complete", "label": "Supplied receipt survived exact replay", "refs": ["source.receipt_digest"]},
        {"ordinal": 4, "phase": "policy-decision-produced", "state": "halted" if halted else "complete", "label": "Boundary halted for review" if halted else "Reviewed policy proposal produced", "refs": ["headline.disposition", "headline.planned_action"]},
        {"ordinal": 5, "phase": "human-review-pending", "state": "pending", "label": "Human decision, authorization, and verification remain pending", "refs": ["controls.authority_granted", "controls.action_executed"]},
    ]


def _actions(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    expected = candidate["expected"]
    action = expected["action"]
    fallback = expected["fallback"]
    label, rationale = ACTION_PRESENTATION[action]
    fallback_label, fallback_rationale = ACTION_PRESENTATION[fallback]
    common_preconditions = [
        "Confirm ownership and authority for the affected boundary.",
        "Assess current blast radius with evidence outside this receipt.",
        "Fix rollback and stop conditions before any external effect.",
    ]
    common_verification = [
        "Replay the relevant negative control after the change.",
        "Confirm the intended boundary changed and unrelated paths did not.",
    ]
    return [
        {
            "rank": 1,
            "id": "review-primary-proposal",
            "kind": "primary",
            "label": label,
            "rationale": rationale,
            "authority": "human-required",
            "automatic": False,
            "actual_effect": "none",
            "reversibility": "conditional",
            "blast_radius": "external-requires-review",
            "preconditions": list(common_preconditions),
            "rollback": "Restore the last reviewed boundary policy and replay its negative control.",
            "verification": list(common_verification),
            "state": "not-executed",
        },
        {
            "rank": 2,
            "id": "review-fallback-proposal",
            "kind": "fallback",
            "label": fallback_label,
            "rationale": fallback_rationale,
            "authority": "human-required",
            "automatic": False,
            "actual_effect": "none",
            "reversibility": "conditional",
            "blast_radius": "external-requires-review",
            "preconditions": list(common_preconditions),
            "rollback": "Remove the fallback at the owned boundary and restore the reviewed policy.",
            "verification": list(common_verification),
            "state": "not-executed",
        },
        {
            "rank": 3,
            "id": "export-regression-candidate",
            "kind": "verification",
            "label": "Preserve the lesson for review",
            "rationale": "Export one sanitized candidate without installing it or changing the classifier.",
            "authority": "human-required",
            "automatic": False,
            "actual_effect": "none",
            "reversibility": "reversible",
            "blast_radius": "local-bounded",
            "preconditions": ["Review the candidate preview and its nonclaims."],
            "rollback": "Discard the local candidate; no classifier state was changed.",
            "verification": [
                "Recompute the candidate digest and compare exact canonical bytes.",
                "Confirm automatic_install and classifier_mutated remain false.",
            ],
            "state": "not-executed",
        },
    ]


def _incident_from_candidate(
    candidate: dict[str, Any], contract: dict[str, Any]
) -> dict[str, Any]:
    expected = candidate["expected"]
    planned = expected["status"] == "planned"
    threat, guidance = _threat(candidate, contract)
    source_bindings = {
        **contract["bindings"],
    }
    incident_identifier = _digest(
        {
            "event_digest": candidate["source"]["event_digest"],
            "receipt_digest": candidate["source"]["receipt_digest"],
        }
    )[:16]
    title = threat["title"] if planned else "Unmapped categorical boundary"
    summary = (
        "Pinned policy produced a "
        + expected["action"]
        + " proposal for the reviewed "
        + expected["threat_id"]
        + " family; no action was executed."
        if planned
        else "Future KARMA halted at "
        + expected["halt_code"]
        + "; unreviewed categorical values remain withheld and human mapping is required."
    )
    value: dict[str, Any] = {
        "schema": INCIDENT_SCHEMA,
        "engine": ENGINE,
        "status": "ready-for-review" if planned else "halted-for-review",
        "incident_id": "incident-" + incident_identifier,
        "source": {
            "event_digest": candidate["source"]["event_digest"],
            "receipt_digest": candidate["source"]["receipt_digest"],
            "source_status": expected["status"],
            "receipt_classification": expected["classification"],
            "bindings": source_bindings,
        },
        "headline": {
            "title": title,
            "severity": expected["severity"],
            "disposition": "reviewed-plan" if planned else "boundary-halt",
            "planned_action": expected["action"],
            "summary": summary,
        },
        "epistemics": _epistemics(candidate, threat),
        "timeline": _timeline(candidate),
        "actions": _actions(candidate),
        "learning": {
            "threat": threat,
            "guidance": guidance,
            "regression_candidate": _clone(candidate),
        },
        "controls": dict(ZERO_CONTROLS),
        "nonclaims": list(INCIDENT_NONCLAIMS),
    }
    value["incident_digest"] = _digest(value)
    return value


def validate_incident(value: Any, contract: dict[str, Any]) -> dict[str, Any]:
    incident = _exact(
        value,
        (
            "schema", "engine", "status", "incident_id", "source", "headline",
            "epistemics", "timeline", "actions", "learning", "controls",
            "nonclaims", "incident_digest",
        ),
    )
    if (
        incident["schema"] != INCIDENT_SCHEMA
        or incident["engine"] != ENGINE
        or not _is_token(incident["incident_id"])
        or incident["controls"] != ZERO_CONTROLS
        or incident["nonclaims"] != INCIDENT_NONCLAIMS
    ):
        raise LanternError()
    learning = _exact(incident["learning"], ("threat", "guidance", "regression_candidate"))
    candidate = validate_candidate(learning["regression_candidate"], contract)
    expected = _incident_from_candidate(candidate, contract)
    if _canonical(incident) != _canonical(expected):
        raise LanternError()
    if len(_canonical(incident)) + 1 > LIMITS["incident_bytes"]:
        raise LanternError()
    return _clone(incident)


def incident_value(wrapper: Any, contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = load_contract() if contract is None else contract
    event, expected_receipt = _source_parts(wrapper, contract)
    candidate = validate_candidate(
        _candidate_from_parts(event, expected_receipt, contract), contract
    )
    incident = _incident_from_candidate(candidate, contract)
    return validate_incident(incident, contract)


def verify_value(wrapper: Any, contract: dict[str, Any] | None = None) -> bool:
    contract = load_contract() if contract is None else contract
    value = _exact(wrapper, ("schema", "source", "incident"))
    if value["schema"] != VERIFY_SCHEMA:
        raise LanternError()
    expected = incident_value(value["source"], contract)
    validate_incident(value["incident"], contract)
    if _canonical(expected) != _canonical(value["incident"]):
        raise LanternError()
    return True


def check_contract(contract: dict[str, Any]) -> None:
    for raw_case in contract["bundle"]["corpus"]["cases"]:
        case = future._thaw(raw_case)
        event = case["event"]
        receipt = future.plan_event(event, contract["bundle"])
        wrapper = {"schema": SOURCE_SCHEMA, "event": event, "receipt": receipt}
        validate_incident(incident_value(wrapper, contract), contract)
    novel = future._thaw(contract["bundle"]["corpus"]["cases"][1]["event"])
    marker = "private-marker-do-not-echo"
    novel["mechanism"] = marker
    halted_receipt = future.plan_event(novel, contract["bundle"])
    halted_wrapper = {
        "schema": SOURCE_SCHEMA,
        "event": novel,
        "receipt": halted_receipt,
    }
    halted = incident_value(halted_wrapper, contract)
    if halted["status"] != "halted-for-review" or marker.encode("ascii") in _canonical(halted):
        raise LanternError()


def _read_stdin(limit: int) -> Any:
    try:
        payload = sys.stdin.buffer.read(limit + 1)
    except (OSError, RecursionError) as exc:
        raise LanternError() from exc
    if len(payload) > limit:
        raise LanternError()
    try:
        return future._decode_json(
            payload,
            max_bytes=limit,
            max_nodes=LIMITS["nodes"],
            max_depth=LIMITS["depth"],
        )
    except (future.InvalidInput, RecursionError) as exc:
        raise LanternError() from exc


def _emit(value: Any) -> None:
    sys.stdout.buffer.write(_canonical(value) + b"\n")


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        if len(arguments) != 1 or arguments[0] not in {
            "check", "digest", "build", "candidate", "verify",
        }:
            raise LanternError()
        command = arguments[0]
        contract = load_contract()
        if command == "check":
            check_contract(contract)
            sys.stdout.buffer.write(b"incident-lantern: ok\n")
            return 0
        if command == "digest":
            _emit(
                {
                    "schema": "kingdom.incident-bindings/v1",
                    "engine": ENGINE,
                    "bindings": contract["bindings"],
                }
            )
            return 0
        if command in {"build", "candidate"}:
            source = _read_stdin(LIMITS["source_bytes"])
            result = (
                incident_value(source, contract)
                if command == "build"
                else candidate_value(source, contract)
            )
            _emit(result)
            return 0
        wrapper = _read_stdin(LIMITS["verify_bytes"])
        verify_value(wrapper, contract)
        sys.stdout.buffer.write(b"true\n")
        return 0
    except (
        LanternError, future.KarmaError, KeyError, TypeError, IndexError,
        ValueError, RecursionError,
    ):
        sys.stderr.buffer.write(b"incident-lantern: rejected\n")
        return 2
    except BrokenPipeError:
        return 141
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
