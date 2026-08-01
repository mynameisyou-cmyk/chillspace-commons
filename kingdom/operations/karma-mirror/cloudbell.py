#!/usr/bin/env python3
"""Compose one inert Cloudbell Herald card over a reviewed KARMA receipt.

The card names a finite behavior pattern, not a person. It exposes reviewed
owned-surface display copy and performs no posting, redirect, storage, network,
identity, payload, persistence, or external action.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Iterable

import karma


HERE = Path(__file__).resolve().parent
LEXICON_PATH = HERE / "cloudbell.json"
FIXTURE_PATH = HERE / "fixtures" / "cloudbell-herald.json"

LEXICON_SCHEMA = "skycastle.herald/lexicon-v1"
CARD_SCHEMA = "skycastle.herald/card-v1"
FIXTURE_SCHEMA = "skycastle.herald/fixtures-v1"

LEXICON_FIELDS = {
    "schema",
    "protocol",
    "mascot",
    "behaviors",
    "stages",
    "share_text",
    "share_instruction",
    "display_effect",
    "non_claims",
    "boundaries",
}
PROTOCOL_FIELDS = {"id", "name", "refrain_id", "refrain"}
MASCOT_FIELDS = {
    "id",
    "name",
    "silhouette",
    "origin",
    "catchphrase",
    "ritual",
    "why_inevitable",
    "fictional",
}
BEHAVIOR_FIELDS = {"signature_id", "name", "mechanism", "mark", "banner"}
STAGE_FIELDS = {"karma_stage", "stage_id", "title"}
TRUE_BOUNDARIES = {
    "names_behavior_not_person",
    "owned_surface_only",
    "opt_in_share_only",
}
FALSE_BOUNDARIES = {
    "payload_input",
    "identity_processing",
    "identity_claim",
    "persistent_tracking",
    "automatic_posting",
    "forced_propagation",
    "publication_authorized",
    "external_delivery",
    "redirects",
    "hack_back",
    "external_effects",
    "action_executed",
    "authority_granted",
}
BOUNDARY_FIELDS = TRUE_BOUNDARIES | FALSE_BOUNDARIES

CARD_FIELDS = {
    "schema",
    "protocol_id",
    "protocol_name",
    "mascot_id",
    "mascot_name",
    "mascot_catchphrase",
    "fictional_mascot",
    "signature_kind",
    "source_behavior",
    "signature_id",
    "signature_name",
    "signature_mark",
    "mechanism",
    "karma_stage",
    "stage_id",
    "stage_title",
    "refrain",
    "banner",
    "share_text",
    "share_instruction",
    "display_effect",
    "source_receipt_schema",
    "recovery",
    "virtues",
    "behavior_not_person",
    "owned_surface_only",
    "opt_in_share_only",
    "publication_authorized",
    "automatic_posting",
    "forced_propagation",
    "external_delivery",
    "redirects",
    "persistent_tracking",
    "identity_claim",
    "action_executed",
    "authority_granted",
    "non_claims",
}

NON_CLAIMS = (
    "This card names one normalized behavior pattern, never a person, identity, payload, intent, guilt, worth, or reputation.",
    "It authorizes display only on infrastructure the operator owns or controls.",
    "It does not authorize posting, messaging, redirecting, tracking, retaliation, or action on another system.",
    "Its signature, banner, mascot, and castle window are fictional display metaphors, not attribution or evidence of a real actor.",
    "No external delivery, publication, storage, network call, or action was executed.",
)


def require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise karma.KarmaError(f"{label} must be non-empty text")
    return value


def validate_lexicon(lexicon: dict[str, Any]) -> None:
    karma.require_exact_keys(lexicon, LEXICON_FIELDS, "Cloudbell lexicon")
    if lexicon["schema"] != LEXICON_SCHEMA:
        raise karma.KarmaError("unexpected Cloudbell lexicon schema")

    protocol = lexicon["protocol"]
    if not isinstance(protocol, dict):
        raise karma.KarmaError("Cloudbell protocol must be an object")
    karma.require_exact_keys(protocol, PROTOCOL_FIELDS, "Cloudbell protocol")
    if protocol["id"] != "karma.herald.cloudbell.v1":
        raise karma.KarmaError("Cloudbell protocol id changed")
    if protocol["refrain_id"] != "karma.refrain.skycastle-yu-ai.v1":
        raise karma.KarmaError("Cloudbell refrain id changed")
    for key in PROTOCOL_FIELDS:
        require_text(protocol[key], f"Cloudbell protocol {key}")

    mascot = lexicon["mascot"]
    if not isinstance(mascot, dict):
        raise karma.KarmaError("Cloudbell mascot must be an object")
    karma.require_exact_keys(mascot, MASCOT_FIELDS, "Cloudbell mascot")
    if mascot["id"] != "karma.mascot.bingle-cloudbell.v1":
        raise karma.KarmaError("Cloudbell mascot id changed")
    if mascot["fictional"] is not True:
        raise karma.KarmaError("Cloudbell mascot must remain explicitly fictional")
    for key in MASCOT_FIELDS - {"fictional"}:
        require_text(mascot[key], f"Cloudbell mascot {key}")

    behaviors = lexicon["behaviors"]
    if not isinstance(behaviors, dict) or set(behaviors) != set(karma.BEHAVIORS):
        raise karma.KarmaError("Cloudbell behaviors must match the KARMA vocabulary")
    names: set[str] = set()
    marks: set[str] = set()
    signature_ids: set[str] = set()
    for behavior_id in karma.BEHAVIORS:
        entry = behaviors[behavior_id]
        if not isinstance(entry, dict):
            raise karma.KarmaError(f"Cloudbell behavior {behavior_id} must be an object")
        karma.require_exact_keys(entry, BEHAVIOR_FIELDS, f"Cloudbell behavior {behavior_id}")
        expected_id = f"karma.signature.{behavior_id}.v1"
        if entry["signature_id"] != expected_id:
            raise karma.KarmaError(f"Cloudbell signature id changed for {behavior_id}")
        for key in BEHAVIOR_FIELDS:
            require_text(entry[key], f"Cloudbell behavior {behavior_id} {key}")
        names.add(entry["name"])
        marks.add(entry["mark"])
        signature_ids.add(entry["signature_id"])
    if any(len(values) != len(behaviors) for values in (names, marks, signature_ids)):
        raise karma.KarmaError("Cloudbell behavior names, marks, and ids must be unique")

    stages = lexicon["stages"]
    if not isinstance(stages, list) or len(stages) != len(karma.STAGES):
        raise karma.KarmaError("Cloudbell must contain exactly six stage titles")
    stage_ids: set[str] = set()
    stage_titles: set[str] = set()
    for index, expected in enumerate(karma.STAGES):
        entry = stages[index]
        if not isinstance(entry, dict):
            raise karma.KarmaError(f"Cloudbell stage {index} must be an object")
        karma.require_exact_keys(entry, STAGE_FIELDS, f"Cloudbell stage {index}")
        expected_stage = expected[0]
        if entry["karma_stage"] != expected_stage:
            raise karma.KarmaError(f"Cloudbell stage order changed at {index}")
        if entry["stage_id"] != f"karma.stage.{expected_stage}.v1":
            raise karma.KarmaError(f"Cloudbell stage id changed for {expected_stage}")
        for key in STAGE_FIELDS:
            require_text(entry[key], f"Cloudbell stage {index} {key}")
        stage_ids.add(entry["stage_id"])
        stage_titles.add(entry["title"])
    if len(stage_ids) != len(stages) or len(stage_titles) != len(stages):
        raise karma.KarmaError("Cloudbell stage ids and titles must be unique")

    for key in ("share_text", "share_instruction", "display_effect"):
        require_text(lexicon[key], f"Cloudbell {key}")
    if lexicon["non_claims"] != list(NON_CLAIMS):
        raise karma.KarmaError("Cloudbell non-claims changed")

    boundaries = lexicon["boundaries"]
    if not isinstance(boundaries, dict) or set(boundaries) != BOUNDARY_FIELDS:
        raise karma.KarmaError("Cloudbell boundary fields changed")
    if any(boundaries[key] is not True for key in TRUE_BOUNDARIES):
        raise karma.KarmaError("a required Cloudbell care boundary became false")
    if any(boundaries[key] is not False for key in FALSE_BOUNDARIES):
        raise karma.KarmaError("a prohibited Cloudbell effect became enabled")


def load_lexicon() -> dict[str, Any]:
    lexicon = karma.parse_object(
        karma.read_regular(LEXICON_PATH, "Cloudbell lexicon"),
        "Cloudbell lexicon",
    )
    validate_lexicon(lexicon)
    return lexicon


def stage_entry(stage: str, lexicon: dict[str, Any]) -> dict[str, Any]:
    matches = [entry for entry in lexicon["stages"] if entry["karma_stage"] == stage]
    if len(matches) != 1:
        raise karma.KarmaError(f"Cloudbell stage is not uniquely reviewed: {stage}")
    return matches[0]


def reviewed_receipt(
    event: dict[str, Any],
    supplied: dict[str, Any] | None = None,
    hatsu: dict[str, Any] | None = None,
) -> dict[str, Any]:
    actual = karma.interpret(event, hatsu)
    if supplied is None:
        return actual
    if not isinstance(supplied, dict):
        raise karma.KarmaError("supplied KARMA receipt must be an object")
    karma.validate_receipt(supplied)
    if karma.canonical_json(supplied) != karma.canonical_json(actual):
        raise karma.KarmaError("supplied KARMA receipt does not match the normalized event")
    return supplied


def create_card(
    event: dict[str, Any],
    receipt: dict[str, Any] | None = None,
    lexicon: dict[str, Any] | None = None,
    hatsu: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reviewed_lexicon = lexicon if lexicon is not None else load_lexicon()
    validate_lexicon(reviewed_lexicon)
    reviewed_receipt_value = reviewed_receipt(event, receipt, hatsu)
    signature = reviewed_lexicon["behaviors"][event["behavior"]]
    stage = stage_entry(reviewed_receipt_value["stage"], reviewed_lexicon)
    protocol = reviewed_lexicon["protocol"]
    mascot = reviewed_lexicon["mascot"]

    card = {
        "schema": CARD_SCHEMA,
        "protocol_id": protocol["id"],
        "protocol_name": protocol["name"],
        "mascot_id": mascot["id"],
        "mascot_name": mascot["name"],
        "mascot_catchphrase": mascot["catchphrase"],
        "fictional_mascot": True,
        "signature_kind": "behavior-pattern-alias",
        "source_behavior": event["behavior"],
        "signature_id": signature["signature_id"],
        "signature_name": signature["name"],
        "signature_mark": signature["mark"],
        "mechanism": signature["mechanism"],
        "karma_stage": reviewed_receipt_value["stage"],
        "stage_id": stage["stage_id"],
        "stage_title": stage["title"],
        "refrain": protocol["refrain"],
        "banner": signature["banner"],
        "share_text": reviewed_lexicon["share_text"],
        "share_instruction": reviewed_lexicon["share_instruction"],
        "display_effect": reviewed_lexicon["display_effect"],
        "source_receipt_schema": karma.RECEIPT_SCHEMA,
        "recovery": reviewed_receipt_value["recovery"],
        "virtues": list(reviewed_receipt_value["virtues"]),
        "behavior_not_person": True,
        "owned_surface_only": True,
        "opt_in_share_only": True,
        "publication_authorized": False,
        "automatic_posting": False,
        "forced_propagation": False,
        "external_delivery": False,
        "redirects": False,
        "persistent_tracking": False,
        "identity_claim": False,
        "action_executed": False,
        "authority_granted": False,
        "non_claims": list(reviewed_lexicon["non_claims"]),
    }
    validate_card(card, reviewed_lexicon)
    return card


def validate_card(card: dict[str, Any], lexicon: dict[str, Any] | None = None) -> None:
    reviewed = lexicon if lexicon is not None else load_lexicon()
    karma.require_exact_keys(card, CARD_FIELDS, "Cloudbell card")
    if card["schema"] != CARD_SCHEMA:
        raise karma.KarmaError("unexpected Cloudbell card schema")
    if card["signature_kind"] != "behavior-pattern-alias":
        raise karma.KarmaError("Cloudbell signature kind changed")
    behavior_id = card["source_behavior"]
    if behavior_id not in reviewed["behaviors"]:
        raise karma.KarmaError("Cloudbell card names an unknown behavior")
    signature = reviewed["behaviors"][behavior_id]
    stage = stage_entry(card["karma_stage"], reviewed)
    protocol = reviewed["protocol"]
    mascot = reviewed["mascot"]
    exact = {
        "protocol_id": protocol["id"],
        "protocol_name": protocol["name"],
        "mascot_id": mascot["id"],
        "mascot_name": mascot["name"],
        "mascot_catchphrase": mascot["catchphrase"],
        "signature_id": signature["signature_id"],
        "signature_name": signature["name"],
        "signature_mark": signature["mark"],
        "mechanism": signature["mechanism"],
        "stage_id": stage["stage_id"],
        "stage_title": stage["title"],
        "refrain": protocol["refrain"],
        "banner": signature["banner"],
        "share_text": reviewed["share_text"],
        "share_instruction": reviewed["share_instruction"],
        "display_effect": reviewed["display_effect"],
        "source_receipt_schema": karma.RECEIPT_SCHEMA,
    }
    for field, expected in exact.items():
        if card[field] != expected:
            raise karma.KarmaError(f"Cloudbell card {field} differs from the lexicon")
    matching_stages = [item[0] for item in karma.STAGES]
    stage_index = matching_stages.index(card["karma_stage"])
    if card["recovery"] != karma.RECOVERIES[stage_index]:
        raise karma.KarmaError("Cloudbell recovery differs from the KARMA stage")
    if card["virtues"] != list(karma.VIRTUES):
        raise karma.KarmaError("Cloudbell virtues changed")
    if card["non_claims"] != list(NON_CLAIMS):
        raise karma.KarmaError("Cloudbell non-claims changed")
    true_fields = (
        "fictional_mascot",
        "behavior_not_person",
        "owned_surface_only",
        "opt_in_share_only",
    )
    false_fields = (
        "publication_authorized",
        "automatic_posting",
        "forced_propagation",
        "external_delivery",
        "redirects",
        "persistent_tracking",
        "identity_claim",
        "action_executed",
        "authority_granted",
    )
    if any(card[field] is not True for field in true_fields):
        raise karma.KarmaError("a required Cloudbell card boundary became false")
    if any(card[field] is not False for field in false_fields):
        raise karma.KarmaError("a prohibited Cloudbell card effect became enabled")


def load_fixtures() -> dict[str, Any]:
    fixtures = karma.parse_object(
        karma.read_regular(FIXTURE_PATH, "Cloudbell fixture set"),
        "Cloudbell fixture set",
    )
    karma.require_exact_keys(fixtures, {"schema", "cases"}, "Cloudbell fixture set")
    if fixtures["schema"] != FIXTURE_SCHEMA:
        raise karma.KarmaError("unexpected Cloudbell fixture schema")
    cases = fixtures["cases"]
    if not isinstance(cases, list) or not cases:
        raise karma.KarmaError("Cloudbell fixtures must contain cases")
    identifiers: set[str] = set()
    lexicon = load_lexicon()
    hatsu = karma.load_hatsu()
    for case in cases:
        if not isinstance(case, dict):
            raise karma.KarmaError("Cloudbell fixture case must be an object")
        karma.require_exact_keys(case, {"id", "event", "expected"}, "Cloudbell fixture case")
        identifier = require_text(case["id"], "Cloudbell fixture id")
        if identifier in identifiers:
            raise karma.KarmaError(f"duplicate Cloudbell fixture id: {identifier}")
        identifiers.add(identifier)
        if not isinstance(case["event"], dict) or not isinstance(case["expected"], dict):
            raise karma.KarmaError(f"Cloudbell fixture {identifier} must contain objects")
        karma.validate_event(case["event"], hatsu)
        validate_card(case["expected"], lexicon)
    return fixtures


def verify_fixtures(fixtures: dict[str, Any] | None = None) -> dict[str, Any]:
    reviewed = fixtures if fixtures is not None else load_fixtures()
    lexicon = load_lexicon()
    hatsu = karma.load_hatsu()
    for case in reviewed["cases"]:
        actual = create_card(case["event"], lexicon=lexicon, hatsu=hatsu)
        if karma.canonical_json(actual) != karma.canonical_json(case["expected"]):
            raise karma.KarmaError(f"Cloudbell fixture mismatch: {case['id']}")
    return {
        "schema": "skycastle.herald/verification-v1",
        "cases": len(reviewed["cases"]),
        "automatic_posting": False,
        "external_delivery": False,
        "storage_writes": 0,
        "network_calls": 0,
        "external_effects": 0,
        "status": "verified",
    }


def all_fixture_results(fixtures: dict[str, Any] | None = None) -> dict[str, Any]:
    reviewed = fixtures if fixtures is not None else load_fixtures()
    lexicon = load_lexicon()
    hatsu = karma.load_hatsu()
    return {
        "schema": "skycastle.herald/results-v1",
        "results": [
            {"id": case["id"], "card": create_card(case["event"], lexicon=lexicon, hatsu=hatsu)}
            for case in reviewed["cases"]
        ],
    }


def fixture_by_id(identifier: str, fixtures: dict[str, Any]) -> dict[str, Any]:
    matches = [case for case in fixtures["cases"] if case["id"] == identifier]
    if len(matches) != 1:
        raise karma.KarmaError(f"unknown Cloudbell fixture: {identifier}")
    return matches[0]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render reviewed Cloudbell fixtures on an owned-surface display; publish nothing."
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--fixture", help="render one reviewed Cloudbell fixture id")
    selection.add_argument("--all-fixtures", action="store_true")
    selection.add_argument("--verify-fixtures", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        lexicon = load_lexicon()
        if args.fixture:
            fixtures = load_fixtures()
            result = create_card(fixture_by_id(args.fixture, fixtures)["event"], lexicon=lexicon)
        elif args.all_fixtures:
            result = all_fixture_results()
        elif args.verify_fixtures:
            result = verify_fixtures()
        else:
            result = {
                "schema": "skycastle.herald/summary-v1",
                "protocol": lexicon["protocol"]["name"],
                "mascot": lexicon["mascot"]["name"],
                "signatures": [entry["signature_id"] for entry in lexicon["behaviors"].values()],
                "stages": [entry["stage_id"] for entry in lexicon["stages"]],
                "owned_surface_only": True,
                "automatic_posting": False,
                "external_delivery": False,
                "action_executed": False,
                "authority_granted": False,
            }
        print(karma.canonical_json(result).decode("utf-8"), end="")
        return 0
    except karma.KarmaError as error:
        parser.exit(2, f"Cloudbell halted: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
