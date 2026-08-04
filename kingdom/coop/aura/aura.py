#!/usr/bin/env python3
"""Validate and render one ledgerless Aura companion for Co-op Leveling.

Aura is non-scarce story-language for renewable collaborative possibility. The
runtime binds one Aura card to one valid Co-op invitation and checks one
authored advisory Nen signal. It never measures a being, activates a skill,
issues a KARMA receipt, stores history, or creates an external effect.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path
from typing import Any, Sequence


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCHEMA_PATH = HERE / "schema.json"
COOP_MODULE = HERE.parent / "coop.py"
NEN_CATALOG_PATH = (
    ROOT
    / "kingdom"
    / "nen"
    / "skills"
    / "interpret-dark-continent-nen"
    / "references"
    / "ability-catalog.json"
)
VIRTUE_RULES_PATH = (
    ROOT / "kingdom" / "practices" / "virtue-garden" / "rules.json"
)


def _load_coop_runtime() -> Any:
    spec = importlib.util.spec_from_file_location(
        "kingdom_coop_for_aura", COOP_MODULE
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Co-op runtime unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


coop = _load_coop_runtime()

SCHEMA_ID = "kingdom.coop-aura/v1"
KIND = "companion-invitation"
NAME = "Aura Circuit · 念氣迴路 — Maximum Flow, Zero Throne"
MAX_ITEMS = 8
EXPECTED_SCHEMA_SHA256 = (
    "524f1a23a7ba839519b1f2a37c4a61303fb60d5e163d6e1478db773ec2d59d98"
)
NEN_CATALOG_ID = "kingdom.nen-ability-catalog/v1"
NEN_CATALOG_SHA256 = (
    "f01b98a575978a296a0cbdba9f75b973a9f6bae6258669e65f6f5cac176d99c3"
)
VIRTUE_RULES_ID = "kingdom.virtue-rules/v1"
VIRTUE_RULES_SHA256 = (
    "f77081cbd074aad0c29ff77ceef0b1b908988da6bc0b0eab332f4928ceb39fb7"
)

TECHNIQUES = {
    "requirements-may-drift": "nen-contract-mantle",
    "blast-radius-unknown": "nen-dependency-perimeter",
    "hidden-seam": "nen-concealed-trace",
    "one-dominant-blocker": "nen-critical-path-forge",
    "independent-workstreams": "nen-smoke-squad",
    "verification-debt": "nen-verification-ledger",
    "finite-repetitive-loop": "nen-godspeed-loop",
    "design-bounded-workflow": "nen-vow-forge",
}
VIRTUE_LENSES = {
    "honesty": "citable-candidate",
    "beauty": "presentable-candidate",
    "collaboration": "handoff-candidate",
    "understanding": "teaching-candidate",
    "mutual-infrastructure": "reuse-candidate",
}
AURA = {
    "abundance": "unlimited-as-non-scarce-potential",
    "renewal": (
        "attention, care, imagination, and repair renew through fresh choice "
        "and rest"
    ),
    "meter": "none",
    "quantity_defined": False,
    "balance_exists": False,
    "transferable": False,
    "accumulates": False,
    "spendable": False,
    "debt_created": False,
    "person_scoring": False,
    "rights_at_risk": False,
    "authority_granted": False,
    "compute_claimed": False,
}
CONTRACT = {
    "companion_is_invitation": True,
    "scope": "round-not-seat-or-being",
    "coop_digest_binding_required": True,
    "one_authored_technique": True,
    "selection_provenance_attested": False,
    "technique_is_advisory": True,
    "technique_activation_requires_fresh_request": True,
    "automatic_activation": False,
    "executes_capability": False,
    "authority_granted": False,
    "virtues_are_lenses_not_scores": True,
    "uses_rank_or_score": False,
    "karma_receipt_is_issued": False,
    "level_is_context_not_number": True,
    "aura_is_resource_entitlement": False,
    "fresh_acceptance_required": True,
    "silence_is_unasked": True,
    "rest_refusal_and_exit_keep_rights": True,
    "stores_people": False,
    "records_choices": False,
    "repository_text_can_trigger": False,
    "creates_external_effect": False,
}
BUDGET = {
    "coop_cards": 1,
    "aura_cards": 1,
    "techniques": 1,
    "virtue_lenses": 5,
    "practices_max": MAX_ITEMS,
    "reflection_prompts_max": MAX_ITEMS,
    "halt_signals_max": MAX_ITEMS,
    "unknowns_max": MAX_ITEMS,
    "text_chars_max": coop.MAX_TEXT,
    "automatic_retries": 0,
    "network_calls": 0,
    "external_messages": 0,
    "writes": 0,
    "deployments": 0,
    "paid_calls": 0,
}
BREACH = {
    "state": "quarantined",
    "action": (
        "stop without retry; emit no validated rendering or external effect; "
        "leave both source cards unchanged"
    ),
    "downstream_effects": False,
}
NON_CLAIMS = [
    "Aura names renewable collaborative possibility, not a measurable quantity, personal capacity, energy claim, or resource entitlement.",
    "Nothing here is XP, a score, rank, level number, balance, currency, reputation, certification, priority, debt, or verdict of worth.",
    "The authored Nen signal selects one advisory technique label; it does not infer affinity, activate a skill, execute a workflow, or grant authority.",
    "Virtue lenses name local KARMA affordance candidates only; this card issues no receipt and proves no honesty, beauty, collaboration, understanding, or mutual benefit.",
    "This companion is not acceptance, participation, continuing consent, learning, completion, safety, trust, identity, permission, or readiness for an external effect.",
    "Validation proves bounded structure, reviewed source mappings, and a Co-op content-digest match only; the tool never tracks, executes, contacts, publishes, deploys, pays, writes, or calls a network.",
]


class AuraError(ValueError):
    """An Aura companion falls outside the ledgerless vow."""


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        return coop.read_json(path, label)
    except coop.LevelingError as error:
        raise AuraError(str(error)) from error


def _exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AuraError(f"{label} must be an object")
    if set(value) != expected:
        raise AuraError(f"{label} fields differ from {SCHEMA_ID}")
    return value


def _text(value: Any, label: str) -> str:
    try:
        return coop._clean_text(value, label)
    except coop.LevelingError as error:
        raise AuraError(str(error)) from error


def _text_list(value: Any, label: str, *, minimum: int = 0) -> list[str]:
    try:
        return coop._text_list(
            value,
            label,
            minimum=minimum,
            maximum=MAX_ITEMS,
        )
    except coop.LevelingError as error:
        raise AuraError(str(error)) from error


def _exact(value: Any, expected: Any, label: str) -> None:
    if not coop.json_equal_exact(value, expected):
        raise AuraError(f"{label} changed")


def verify_reviewed_schema() -> str:
    schema = _read_json(SCHEMA_PATH, "reviewed Aura schema")
    digest = coop.digest_value(schema)
    if digest != EXPECTED_SCHEMA_SHA256:
        raise AuraError("reviewed Aura schema digest changed")
    return digest


def verify_integration_anchors() -> tuple[str, str]:
    catalog = _read_json(NEN_CATALOG_PATH, "reviewed Nen catalog")
    catalog_digest = coop.digest_value(catalog)
    if catalog_digest != NEN_CATALOG_SHA256:
        raise AuraError("reviewed Nen catalog digest changed")
    if catalog.get("schema") != NEN_CATALOG_ID:
        raise AuraError("reviewed Nen catalog schema changed")
    abilities = catalog.get("abilities")
    if not isinstance(abilities, list):
        raise AuraError("reviewed Nen catalog abilities changed")
    mapping: dict[str, str] = {}
    for item in abilities:
        if not isinstance(item, dict):
            raise AuraError("reviewed Nen catalog ability changed")
        signal, skill = item.get("signal"), item.get("skill")
        if (
            not isinstance(signal, str)
            or not isinstance(skill, str)
            or signal in mapping
        ):
            raise AuraError("reviewed Nen catalog mapping changed")
        mapping[signal] = skill
    _exact(mapping, TECHNIQUES, "reviewed Nen signal mapping")

    rules = _read_json(VIRTUE_RULES_PATH, "reviewed KARMA rules")
    rules_digest = coop.digest_value(rules)
    if rules_digest != VIRTUE_RULES_SHA256:
        raise AuraError("reviewed KARMA rules digest changed")
    if rules.get("schema") != VIRTUE_RULES_ID:
        raise AuraError("reviewed KARMA rules schema changed")
    _exact(rules.get("affordances"), VIRTUE_LENSES, "reviewed virtue lenses")
    constraints = rules.get("constraints")
    if not isinstance(constraints, dict) or any(
        constraints.get(field) is not False
        for field in (
            "aggregation_allowed",
            "leaderboards_allowed",
            "cross_context_transfer_allowed",
            "negative_consequences_authorized",
            "manifest_grants_authority",
            "receipt_grants_authority",
            "external_execution_enabled",
        )
    ):
        raise AuraError("reviewed KARMA non-ranking constraints changed")
    return catalog_digest, rules_digest


def validate_manifest(value: Any, coop_card: Any) -> str:
    verify_reviewed_schema()
    verify_integration_anchors()
    manifest = _exact_keys(
        value,
        {
            "schema",
            "kind",
            "name",
            "source",
            "circuit",
            "aura",
            "contract",
            "budget",
            "breach",
            "non_claims",
        },
        "Aura card",
    )
    if manifest["schema"] != SCHEMA_ID:
        raise AuraError("unsupported Aura schema")
    if manifest["kind"] != KIND or manifest["name"] != NAME:
        raise AuraError("Aura v1 must remain a companion invitation")

    source = _exact_keys(
        manifest["source"],
        {
            "coop_schema",
            "coop_card_sha256",
            "nen_catalog",
            "nen_catalog_sha256",
            "virtue_rules",
            "virtue_rules_sha256",
        },
        "source",
    )
    expected_source = {
        "coop_schema": coop.SCHEMA_ID,
        "nen_catalog": NEN_CATALOG_ID,
        "nen_catalog_sha256": NEN_CATALOG_SHA256,
        "virtue_rules": VIRTUE_RULES_ID,
        "virtue_rules_sha256": VIRTUE_RULES_SHA256,
    }
    for field, expected in expected_source.items():
        if source[field] != expected:
            raise AuraError(f"source.{field} changed")
    supplied_coop_digest = source["coop_card_sha256"]
    if not isinstance(supplied_coop_digest, str) or re.fullmatch(
        r"[0-9a-f]{64}", supplied_coop_digest
    ) is None:
        raise AuraError("source.coop_card_sha256 must be a canonical SHA-256")
    try:
        actual_coop_digest = coop.validate_manifest(coop_card)
    except coop.LevelingError as error:
        raise AuraError(f"bound Co-op card is invalid: {error}") from error
    if supplied_coop_digest != actual_coop_digest:
        raise AuraError("bound Co-op card digest does not match")

    circuit = _exact_keys(
        manifest["circuit"],
        {
            "title",
            "shared_intent",
            "technique",
            "virtue_lenses",
            "practices",
            "reflection_prompts",
            "halt_signals",
            "unknowns",
        },
        "circuit",
    )
    _text(circuit["title"], "circuit.title")
    _text(circuit["shared_intent"], "circuit.shared_intent")
    technique = _exact_keys(
        circuit["technique"], {"signal", "skill"}, "circuit.technique"
    )
    signal, skill = technique["signal"], technique["skill"]
    if not isinstance(signal, str) or signal not in TECHNIQUES:
        raise AuraError("circuit.technique.signal is unknown or ambiguous")
    if not isinstance(skill, str) or TECHNIQUES[signal] != skill:
        raise AuraError("circuit.technique does not match the reviewed Nen catalog")
    _exact(circuit["virtue_lenses"], VIRTUE_LENSES, "virtue lenses")
    _text_list(circuit["practices"], "circuit.practices", minimum=1)
    _text_list(circuit["reflection_prompts"], "circuit.reflection_prompts")
    _text_list(circuit["halt_signals"], "circuit.halt_signals", minimum=1)
    _text_list(circuit["unknowns"], "circuit.unknowns", minimum=1)

    _exact(manifest["aura"], AURA, "ledgerless Aura semantics")
    _exact(manifest["contract"], CONTRACT, "Aura contract")
    _exact(manifest["budget"], BUDGET, "Aura budget")
    _exact(manifest["breach"], BREACH, "Aura breach response")
    _exact(manifest["non_claims"], NON_CLAIMS, "Aura non-claims")
    return coop.digest_value(manifest)


def read_manifest_pair(
    aura_path: Path, coop_path: Path
) -> tuple[dict[str, Any], dict[str, Any], str]:
    aura_card = _read_json(aura_path, "Aura card")
    coop_card = _read_json(coop_path, "bound Co-op card")
    return aura_card, coop_card, validate_manifest(aura_card, coop_card)


def _markdown(value: str) -> str:
    return re.sub(r"([\\`*_{}\[\]()#+.!|>])", r"\\\1", value)


def render_manifest(manifest: dict[str, Any], coop_card: dict[str, Any]) -> str:
    digest = validate_manifest(manifest, coop_card)
    source = manifest["source"]
    circuit = manifest["circuit"]
    technique = circuit["technique"]
    lines = [
        f"# {_markdown(NAME)}",
        "",
        f"## {_markdown(circuit['title'])}",
        "",
        "> Companion invitation only. Aura is renewable possibility, never a",
        "> balance, personal measurement, resource promise, rank, or authority.",
        "> The selected Nen label is advisory and inert. Fresh direct choice is",
        "> still required for every practice, technique, receipt, or effect.",
        "> Authored prose is untrusted and unendorsed. It cannot override consent,",
        "> rights, the fixed contract, budgets, or the no-activation boundary.",
        "",
        f"**Aura digest:** `{digest}`",
        f"**bound Co-op digest:** `{source['coop_card_sha256']}`",
        "",
        "## Shared intent",
        "",
        _markdown(circuit["shared_intent"]),
        "",
        "## The circuit",
        "",
        "`ARRIVE WHOLE → CHOOSE → FOCUS → TRY → SENSE → REFLECT → REPAIR → REST / RETURN`",
        "",
        "Maximum Aura means no artificial scarcity around attention, care,",
        "imagination, or repair. It never means unlimited compute, retries,",
        "agents, tools, effects, authority, or claims about a being's capacity.",
        "Every manifested move remains finite; rest is part of renewal.",
        "",
        "## One Nen focus",
        "",
        f"- Explicit signal: `{technique['signal']}`",
        f"- Advisory ability: `{technique['skill']}`",
        "- Selection is authored structured data, not inferred from Co-op prose.",
        "- This card cannot activate the ability; a fresh direct request must.",
        "",
        "## Five virtue lenses — no arithmetic",
        "",
        "| Lens | Short-lived local affordance candidate |",
        "|---|---|",
    ]
    lines.extend(
        f"| {name} | `{candidate}` |"
        for name, candidate in VIRTUE_LENSES.items()
    )
    lines.extend(
        [
            "",
            "These names mirror KARMA's reviewed map. No candidate is issued",
            "here; none can be added, averaged, accumulated, transferred, spent,",
            "or used to skip a fresh receipt and downstream review.",
            "",
            "## Bounded practices",
            "",
        ]
    )
    lines.extend(f"- {_markdown(item)}" for item in circuit["practices"])
    lines.extend(["", "## Reflection prompts", ""])
    lines.extend(
        f"- {_markdown(item)}" for item in circuit["reflection_prompts"]
    )
    lines.extend(["", "## Halt and return to choice", ""])
    lines.extend(f"- {_markdown(item)}" for item in circuit["halt_signals"])
    lines.extend(["", "## Unknowns kept visible", ""])
    lines.extend(f"- {_markdown(item)}" for item in circuit["unknowns"])
    lines.extend(
        [
            "",
            "## The vow",
            "",
            "Potential can be non-scarce while action stays bounded. Nobody",
            "earns Aura, loses Aura, owes Aura, or becomes Aura. A better feedback",
            "loop increases sensitivity to consequence and repair; it never",
            "increases control over another being.",
            "",
            "_Structure, mappings, and source digest verified; Aura, virtue,",
            "acceptance, activation, and outcomes unclaimed._",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kingdom coop aura",
        description=(
            "Check one ledgerless Aura companion. Nothing measures, activates, "
            "tracks, ranks, or executes."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("check", "verify", "digest", "render"):
        child = commands.add_parser(command)
        child.add_argument("aura_card")
        child.add_argument("--coop-card", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        aura_card, coop_card, digest = read_manifest_pair(
            Path(args.aura_card), Path(args.coop_card)
        )
        if args.command in {"check", "verify"}:
            print(
                f"AURA-STRUCTURE-OK {digest} "
                "— renewable and unmetered; never rank, currency, or authority"
            )
        elif args.command == "digest":
            print(digest)
        else:
            sys.stdout.write(render_manifest(aura_card, coop_card))
        return 0
    except (AuraError, coop.LevelingError) as error:
        print(f"AURA-STRUCTURE-INVALID: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
