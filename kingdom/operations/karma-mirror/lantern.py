#!/usr/bin/env python3
"""Compose one inert KARMA Lantern incident-legibility brief.

Lantern receives only the existing normalized event and canonically matching
KARMA and Cloudbell artifacts. It separates truth, proposed response, and
learning without live ingestion, raw evidence, identity, persistence, timing,
network, authority, or action.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any, Iterable

import cloudbell
import karma


HERE = Path(__file__).resolve().parent
LEXICON_PATH = HERE / "lantern.json"
FIXTURE_PATH = HERE / "fixtures" / "lantern-brief.json"

LEXICON_SCHEMA = "karma.lantern/lexicon-v1"
BRIEF_SCHEMA = "karma.lantern/brief-v1"
TRUTH_SCHEMA = "karma.lantern/truth-receipt-v1"
ACTION_SCHEMA = "karma.lantern/action-card-v1"
LEARNING_SCHEMA = "karma.lantern/learning-seed-v1"
FIXTURE_SCHEMA = "karma.lantern/fixtures-v1"

EXPECTED_HATSU_CANONICAL_SHA256 = "9684d491b6dfdab20612b4340d0caef9fd8676e0c8b14c2e7421cc73da1944c9"
EXPECTED_CLOUDBELL_CANONICAL_SHA256 = "aa7b5a42d45b56b8fb1be6e8f0ec68080e490c1f1eb6b20b584f78b4f6b57a49"
EXPECTED_LANTERN_CANONICAL_SHA256 = "39e0443b3f6f03f4bd7c76421df9d1fb2a986ad6d77264813a0e3c392e763a13"

EVENT_FIELD_ORDER = (
    "schema",
    "behavior",
    "repetition",
    "boundary_crossings",
    "requested_effect",
    "declared_purpose",
    "scope_attested",
    "evidence_complete",
)
LEXICON_FIELDS = {
    "schema",
    "ability",
    "epistemic_states",
    "review_roles",
    "review_priorities",
    "causal_steps",
    "policy_trace_glossary",
    "uncertainty_glossary",
    "explicit_unknowns",
    "behaviors",
    "stages",
    "human_escalation_prompts",
    "closure_requirements",
    "provenance",
    "non_claims",
    "boundaries",
}
ABILITY_FIELDS = {
    "id",
    "name",
    "desire",
    "affinity",
    "trigger",
    "anti_trigger",
    "input_output",
    "conditions",
    "limitations",
    "budget",
    "breach_response",
    "proof",
    "exit",
}
AFFINITY_FIELDS = {"primary", "secondary"}
BUDGET_FIELDS = {
    "briefs_per_event",
    "response_options_per_stage",
    "causal_steps",
    "network_calls",
    "storage_writes",
    "external_actions",
}
NAMED_EXPLANATION_FIELDS = {"id", "title", "explanation"}
ROLE_FIELDS = {"id", "title", "description"}
CAUSAL_STEP_FIELDS = {"id", "title", "description", "state"}
BEHAVIOR_FIELDS = {"headline", "learning_target", "architecture_question"}
STAGE_FIELDS = {
    "review_role",
    "review_priority",
    "explanation",
    "response_options",
}
OPTION_FIELDS = {"id", "label", "reason", "reversible"}
TRUE_BOUNDARIES = (
    "behavior_not_person",
    "explanatory_only",
    "owned_surface_only",
    "reversible_options_only",
    "human_decision_required",
    "replay_event_normalized_only",
    "no_time_guarantee",
    "policy_values_advisory_only",
)
FALSE_BOUNDARIES = (
    "live_ingestion",
    "raw_payload_input",
    "identity_processing",
    "person_attribution",
    "persistent_incident_store",
    "automatic_response",
    "automatic_escalation",
    "automatic_test_creation",
    "automatic_policy_mutation",
    "production_monitoring",
    "network_calls",
    "storage_writes",
    "external_delivery",
    "publication_authorized",
    "action_executed",
    "authority_granted",
)
BRIEF_FIELDS = {
    "schema",
    "ability_id",
    "ability_name",
    "source_event_schema",
    "source_receipt_schema",
    "source_cloudbell_schema",
    "source_behavior",
    "source_signature_id",
    "source_stage",
    "headline",
    "mechanism",
    "truth_receipt",
    "action_card",
    "learning_seed",
    "causal_rail",
    "virtues",
    "recovery",
    *TRUE_BOUNDARIES,
    *FALSE_BOUNDARIES,
    "non_claims",
}
TRUTH_FIELDS = {
    "schema",
    "epistemic_id",
    "epistemic_title",
    "epistemic_explanation",
    "normalized_signals",
    "declarations",
    "policy_trace",
    "policy_inferences",
    "uncertainties",
    "explicit_unknowns",
    "provenance",
}
SIGNAL_FIELDS = {
    "behavior",
    "repetition",
    "boundary_crossings",
    "requested_effect",
}
DECLARATION_FIELDS = {
    "declared_purpose",
    "scope_attested",
    "evidence_complete",
}
GLOSS_FIELDS = {"token", "explanation"}
INFERENCE_FIELDS = {"kind", "id", "explanation"}
ACTION_FIELDS = {
    "schema",
    "suggested_review_role_id",
    "suggested_review_role_title",
    "review_priority_id",
    "review_priority_title",
    "review_priority_explanation",
    "policy_stage",
    "advisory_route",
    "advisory_capability_percent",
    "display_friction_units",
    "advisory_recovery_steps",
    "policy_values_advisory_only",
    "options",
    "human_escalation_prompts",
    "recovery",
    "reversible_only",
    "human_decision_required",
    "options_proposed_only",
    "action_executed",
    "authority_granted",
}
LEARNING_FIELDS = {
    "schema",
    "lesson_class_id",
    "replay_event",
    "regression_targets",
    "architecture_questions",
    "closure_requirements",
    "closure_status",
    "future_use",
    "automatic_test_creation",
    "automatic_policy_mutation",
    "persistent_storage",
}

EPISTEMIC_KEYS = (
    "declared-complete",
    "declared-ambiguous",
    "declared-incomplete",
)
ROLE_KEYS = (
    "service-steward",
    "security-reviewer",
    "incident-coordinator",
)
PRIORITY_KEYS = (
    "routine",
    "heightened",
    "critical-human",
)
CAUSAL_IDS = ("normalize", "separate", "interpret", "explain", "respond", "learn")
CAUSAL_STATES = ("available", "available", "available", "available", "proposed", "open")
UNCERTAINTY_TOKENS = {
    "incomplete-evidence",
    "declared-purpose-ambiguous",
    "research-scope-unverified",
    "purpose-behavior-conflict",
}
EXPECTED_NON_CLAIMS = (
    "This brief explains one normalized event and does not prove that a real incident occurred.",
    "It names a behavior pattern, never a person, identity, intent, guilt, worth, affiliation, or reputation.",
    "Its review priorities are posture labels, not clocks, queue positions, elapsed-time measurements, or guarantees.",
    "Its stage, route, capability, friction, and recovery-step values are advisory displays, not evidence that enforcement happened.",
    "Its options are inert proposals and authorize or execute no infrastructure action.",
    "Its replay and learning fields create no stored incident, test, ticket, policy change, or external message.",
    "It provides no monitoring coverage, prevention claim, security guarantee, legal conclusion, or completion claim.",
)


def require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise karma.KarmaError(f"{label} must be non-empty text")
    return value


def require_text_list(value: Any, count: int, label: str) -> list[str]:
    if not isinstance(value, list) or len(value) != count:
        raise karma.KarmaError(f"{label} must contain exactly {count} items")
    for item in value:
        require_text(item, f"{label} item")
    return value


def require_object_list(
    value: Any,
    minimum: int,
    maximum: int,
    fields: set[str],
    label: str,
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        qualifier = f"exactly {minimum}" if minimum == maximum else f"{minimum} to {maximum}"
        raise karma.KarmaError(f"{label} must contain {qualifier} objects")
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise karma.KarmaError(f"{label} item {index} must be an object")
        karma.require_exact_keys(item, fields, f"{label} item {index}")
    return value


def require_reviewed_digest(value: dict[str, Any], expected: str, label: str) -> None:
    actual = hashlib.sha256(karma.canonical_json(value)).hexdigest()
    if actual != expected:
        raise karma.KarmaError(f"{label} differs from the reviewed contract")


def expected_policy_trace_tokens() -> set[str]:
    tokens = {f"behavior:{behavior}" for behavior in karma.BEHAVIORS}
    tokens.update(f"baseline:{baseline}" for baseline in set(karma.BEHAVIORS.values()))
    tokens.update(
        {
            "repeated-pattern",
            "repeated-boundary-crossing",
            "high-effect-request",
            "ambiguity-cap",
            "verified-research-cap",
        }
    )
    return tokens


def validate_lexicon(lexicon: dict[str, Any]) -> None:
    if not isinstance(lexicon, dict):
        raise karma.KarmaError("Lantern lexicon must be an object")
    karma.require_exact_keys(lexicon, LEXICON_FIELDS, "Lantern lexicon")
    if lexicon["schema"] != LEXICON_SCHEMA:
        raise karma.KarmaError("unexpected Lantern lexicon schema")

    ability = lexicon["ability"]
    if not isinstance(ability, dict):
        raise karma.KarmaError("Lantern ability must be an object")
    karma.require_exact_keys(ability, ABILITY_FIELDS, "Lantern ability")
    if ability["id"] != "karma.lantern.v1" or ability["name"] != "KARMA Lantern · 業環明燈":
        raise karma.KarmaError("Lantern ability identity changed")
    for field in ABILITY_FIELDS - {"affinity", "conditions", "limitations", "budget"}:
        require_text(ability[field], f"Lantern ability {field}")
    affinity = ability["affinity"]
    if not isinstance(affinity, dict):
        raise karma.KarmaError("Lantern affinity must be an object")
    karma.require_exact_keys(affinity, AFFINITY_FIELDS, "Lantern affinity")
    if affinity != {"primary": "Conjuration", "secondary": "Transmutation"}:
        raise karma.KarmaError("Lantern affinity changed")
    require_text_list(ability["conditions"], 5, "Lantern conditions")
    require_text_list(ability["limitations"], 6, "Lantern limitations")
    budget = ability["budget"]
    if not isinstance(budget, dict):
        raise karma.KarmaError("Lantern budget must be an object")
    karma.require_exact_keys(budget, BUDGET_FIELDS, "Lantern budget")
    if budget != {
        "briefs_per_event": 1,
        "response_options_per_stage": 3,
        "causal_steps": 6,
        "network_calls": 0,
        "storage_writes": 0,
        "external_actions": 0,
    }:
        raise karma.KarmaError("Lantern budget changed")

    states = lexicon["epistemic_states"]
    if not isinstance(states, dict) or tuple(states) != EPISTEMIC_KEYS:
        raise karma.KarmaError("Lantern epistemic states changed")
    for key, value in states.items():
        if not isinstance(value, dict):
            raise karma.KarmaError(f"Lantern epistemic state {key} must be an object")
        karma.require_exact_keys(value, NAMED_EXPLANATION_FIELDS, f"epistemic state {key}")
        if value["id"] != f"karma.epistemic.{key}.v1":
            raise karma.KarmaError(f"Lantern epistemic id changed for {key}")
        for field in NAMED_EXPLANATION_FIELDS:
            require_text(value[field], f"epistemic state {key} {field}")

    roles = lexicon["review_roles"]
    if not isinstance(roles, dict) or tuple(roles) != ROLE_KEYS:
        raise karma.KarmaError("Lantern review roles changed")
    for key, value in roles.items():
        if not isinstance(value, dict):
            raise karma.KarmaError(f"Lantern role {key} must be an object")
        karma.require_exact_keys(value, ROLE_FIELDS, f"Lantern role {key}")
        if value["id"] != f"karma.role.{key}.v1":
            raise karma.KarmaError(f"Lantern role id changed for {key}")
        for field in ROLE_FIELDS:
            require_text(value[field], f"Lantern role {key} {field}")

    priorities = lexicon["review_priorities"]
    if not isinstance(priorities, dict) or tuple(priorities) != PRIORITY_KEYS:
        raise karma.KarmaError("Lantern review priorities changed")
    for key, value in priorities.items():
        if not isinstance(value, dict):
            raise karma.KarmaError(f"Lantern review priority {key} must be an object")
        karma.require_exact_keys(
            value,
            NAMED_EXPLANATION_FIELDS,
            f"Lantern review priority {key}",
        )
        if value["id"] != f"karma.review-priority.{key}.v1":
            raise karma.KarmaError(f"Lantern review priority id changed for {key}")
        for field in NAMED_EXPLANATION_FIELDS:
            require_text(value[field], f"Lantern review priority {key} {field}")

    causal_steps = lexicon["causal_steps"]
    if not isinstance(causal_steps, list) or len(causal_steps) != len(CAUSAL_IDS):
        raise karma.KarmaError("Lantern causal rail must contain six steps")
    for index, step in enumerate(causal_steps):
        if not isinstance(step, dict):
            raise karma.KarmaError(f"Lantern causal step {index} must be an object")
        karma.require_exact_keys(step, CAUSAL_STEP_FIELDS, f"Lantern causal step {index}")
        if step["id"] != CAUSAL_IDS[index] or step["state"] != CAUSAL_STATES[index]:
            raise karma.KarmaError(f"Lantern causal step order changed at {index}")
        for field in ("id", "title", "description", "state"):
            require_text(step[field], f"Lantern causal step {index} {field}")

    policy_trace = lexicon["policy_trace_glossary"]
    if (
        not isinstance(policy_trace, dict)
        or set(policy_trace) != expected_policy_trace_tokens()
    ):
        raise karma.KarmaError("Lantern policy trace glossary changed")
    for token, explanation in policy_trace.items():
        require_text(token, "Lantern policy trace token")
        require_text(explanation, f"Lantern policy trace explanation {token}")

    uncertainty = lexicon["uncertainty_glossary"]
    if not isinstance(uncertainty, dict) or set(uncertainty) != UNCERTAINTY_TOKENS:
        raise karma.KarmaError("Lantern uncertainty glossary changed")
    for token, explanation in uncertainty.items():
        require_text(token, "Lantern uncertainty token")
        require_text(explanation, f"Lantern uncertainty explanation {token}")

    require_text_list(lexicon["explicit_unknowns"], 4, "Lantern explicit unknowns")
    behaviors = lexicon["behaviors"]
    if not isinstance(behaviors, dict) or set(behaviors) != set(karma.BEHAVIORS):
        raise karma.KarmaError("Lantern behavior vocabulary changed")
    learning_targets: set[str] = set()
    for behavior, value in behaviors.items():
        if not isinstance(value, dict):
            raise karma.KarmaError(f"Lantern behavior {behavior} must be an object")
        karma.require_exact_keys(value, BEHAVIOR_FIELDS, f"Lantern behavior {behavior}")
        for field in BEHAVIOR_FIELDS:
            require_text(value[field], f"Lantern behavior {behavior} {field}")
        learning_targets.add(value["learning_target"])
    if len(learning_targets) != len(behaviors):
        raise karma.KarmaError("Lantern learning targets must be unique")

    stage_names = tuple(stage[0] for stage in karma.STAGES)
    stages = lexicon["stages"]
    if not isinstance(stages, dict) or tuple(stages) != stage_names:
        raise karma.KarmaError("Lantern stage vocabulary changed")
    option_ids: set[str] = set()
    for stage, value in stages.items():
        if not isinstance(value, dict):
            raise karma.KarmaError(f"Lantern stage {stage} must be an object")
        karma.require_exact_keys(value, STAGE_FIELDS, f"Lantern stage {stage}")
        if (
            value["review_role"] not in roles
            or value["review_priority"] not in priorities
        ):
            raise karma.KarmaError(
                f"Lantern stage {stage} references an unknown role or priority"
            )
        require_text(value["explanation"], f"Lantern stage {stage} explanation")
        options = value["response_options"]
        if not isinstance(options, list) or len(options) != 3:
            raise karma.KarmaError(f"Lantern stage {stage} must contain three options")
        for option in options:
            if not isinstance(option, dict):
                raise karma.KarmaError(f"Lantern stage {stage} option must be an object")
            karma.require_exact_keys(option, OPTION_FIELDS, f"Lantern stage {stage} option")
            for field in ("id", "label", "reason"):
                require_text(option[field], f"Lantern stage {stage} option {field}")
            if option["reversible"] is not True:
                raise karma.KarmaError("every Lantern option must remain reversible")
            option_ids.add(option["id"])
    if len(option_ids) != len(stages) * 3:
        raise karma.KarmaError("Lantern option ids must be unique")

    require_text_list(
        lexicon["human_escalation_prompts"],
        3,
        "Lantern human escalation prompts",
    )
    require_text_list(lexicon["closure_requirements"], 4, "Lantern closure requirements")
    require_text(lexicon["provenance"], "Lantern provenance")
    if lexicon["non_claims"] != list(EXPECTED_NON_CLAIMS):
        raise karma.KarmaError("Lantern non-claims changed")
    boundaries = lexicon["boundaries"]
    if not isinstance(boundaries, dict) or set(boundaries) != set(
        TRUE_BOUNDARIES + FALSE_BOUNDARIES
    ):
        raise karma.KarmaError("Lantern boundary fields changed")
    if any(boundaries[field] is not True for field in TRUE_BOUNDARIES):
        raise karma.KarmaError("a required Lantern care boundary became false")
    if any(boundaries[field] is not False for field in FALSE_BOUNDARIES):
        raise karma.KarmaError("a prohibited Lantern effect became enabled")
    require_reviewed_digest(
        lexicon,
        EXPECTED_LANTERN_CANONICAL_SHA256,
        "Lantern lexicon",
    )


def load_lexicon() -> dict[str, Any]:
    lexicon = karma.parse_object(
        karma.read_regular(LEXICON_PATH, "Lantern lexicon"),
        "Lantern lexicon",
    )
    validate_lexicon(lexicon)
    return lexicon


def epistemic_key(event: dict[str, Any]) -> str:
    if event["evidence_complete"] is not True:
        return "declared-incomplete"
    if event["declared_purpose"] == "ambiguous":
        return "declared-ambiguous"
    return "declared-complete"


def reviewed_sources(
    event: dict[str, Any],
    receipt: dict[str, Any] | None = None,
    card: dict[str, Any] | None = None,
    hatsu: dict[str, Any] | None = None,
    cloudbell_lexicon: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    reviewed_hatsu = hatsu if hatsu is not None else karma.load_hatsu()
    if not isinstance(reviewed_hatsu, dict):
        raise karma.KarmaError("KARMA Hatsu must be an object")
    karma.validate_hatsu(reviewed_hatsu)
    require_reviewed_digest(
        reviewed_hatsu,
        EXPECTED_HATSU_CANONICAL_SHA256,
        "KARMA Hatsu",
    )
    reviewed_cloudbell_lexicon = (
        cloudbell_lexicon
        if cloudbell_lexicon is not None
        else cloudbell.load_lexicon()
    )
    if not isinstance(reviewed_cloudbell_lexicon, dict):
        raise karma.KarmaError("Cloudbell lexicon must be an object")
    cloudbell.validate_lexicon(reviewed_cloudbell_lexicon)
    require_reviewed_digest(
        reviewed_cloudbell_lexicon,
        EXPECTED_CLOUDBELL_CANONICAL_SHA256,
        "Cloudbell lexicon",
    )
    actual_receipt = karma.interpret(event, reviewed_hatsu)
    if receipt is not None:
        if not isinstance(receipt, dict):
            raise karma.KarmaError("supplied KARMA receipt must be an object")
        karma.validate_receipt(receipt)
        if karma.canonical_json(receipt) != karma.canonical_json(actual_receipt):
            raise karma.KarmaError("supplied KARMA receipt does not match the normalized event")
    reviewed_receipt = receipt if receipt is not None else actual_receipt
    actual_card = cloudbell.create_card(
        event,
        receipt=reviewed_receipt,
        lexicon=reviewed_cloudbell_lexicon,
        hatsu=reviewed_hatsu,
    )
    if card is not None:
        if not isinstance(card, dict):
            raise karma.KarmaError("supplied Cloudbell card must be an object")
        cloudbell.validate_card(card, cloudbell_lexicon)
        if karma.canonical_json(card) != karma.canonical_json(actual_card):
            raise karma.KarmaError("supplied Cloudbell card does not match the event and receipt")
    return reviewed_receipt, card if card is not None else actual_card


def clone_event(event: dict[str, Any]) -> dict[str, Any]:
    return {field: event[field] for field in EVENT_FIELD_ORDER}


def _compose_reviewed_brief(
    event: dict[str, Any],
    receipt: dict[str, Any],
    card: dict[str, Any],
    lexicon: dict[str, Any],
) -> dict[str, Any]:
    epistemic = lexicon["epistemic_states"][epistemic_key(event)]
    behavior = lexicon["behaviors"][event["behavior"]]
    stage = lexicon["stages"][receipt["stage"]]
    role = lexicon["review_roles"][stage["review_role"]]
    priority = lexicon["review_priorities"][stage["review_priority"]]
    policy_trace = [
        {
            "token": token,
            "explanation": lexicon["policy_trace_glossary"][token],
        }
        for token in receipt["evidence"]
    ]
    uncertainties = [
        {
            "token": token,
            "explanation": lexicon["uncertainty_glossary"][token],
        }
        for token in receipt["uncertainties"]
    ]
    truth_receipt = {
        "schema": TRUTH_SCHEMA,
        "epistemic_id": epistemic["id"],
        "epistemic_title": epistemic["title"],
        "epistemic_explanation": epistemic["explanation"],
        "normalized_signals": {
            "behavior": event["behavior"],
            "repetition": event["repetition"],
            "boundary_crossings": event["boundary_crossings"],
            "requested_effect": event["requested_effect"],
        },
        "declarations": {
            "declared_purpose": event["declared_purpose"],
            "scope_attested": event["scope_attested"],
            "evidence_complete": event["evidence_complete"],
        },
        "policy_trace": policy_trace,
        "policy_inferences": [
            {
                "kind": "karma-stage",
                "id": card["stage_id"],
                "explanation": stage["explanation"],
            },
            {
                "kind": "cloudbell-signature",
                "id": card["signature_id"],
                "explanation": card["mechanism"],
            },
        ],
        "uncertainties": uncertainties,
        "explicit_unknowns": list(lexicon["explicit_unknowns"]),
        "provenance": lexicon["provenance"],
    }
    action_card = {
        "schema": ACTION_SCHEMA,
        "suggested_review_role_id": role["id"],
        "suggested_review_role_title": role["title"],
        "review_priority_id": priority["id"],
        "review_priority_title": priority["title"],
        "review_priority_explanation": priority["explanation"],
        "policy_stage": receipt["stage"],
        "advisory_route": receipt["route"],
        "advisory_capability_percent": receipt["real_capability_percent"],
        "display_friction_units": receipt["friction_units"],
        "advisory_recovery_steps": receipt["ttl_steps"],
        "policy_values_advisory_only": True,
        "options": [
            {
                "id": option["id"],
                "label": option["label"],
                "reason": option["reason"],
                "reversible": option["reversible"],
            }
            for option in stage["response_options"]
        ],
        "human_escalation_prompts": list(lexicon["human_escalation_prompts"]),
        "recovery": receipt["recovery"],
        "reversible_only": True,
        "human_decision_required": True,
        "options_proposed_only": True,
        "action_executed": False,
        "authority_granted": False,
    }
    learning_seed = {
        "schema": LEARNING_SCHEMA,
        "lesson_class_id": (
            f"karma.lesson.{event['behavior']}.{receipt['stage']}.v1"
        ),
        "replay_event": clone_event(event),
        "regression_targets": [
            behavior["learning_target"],
            "stage-recovery-remains-exact",
            "zero-effect-boundaries-remain-false",
        ],
        "architecture_questions": [
            behavior["architecture_question"],
            "Which earlier boundary could make this lesson cheaper to discover and safer to recover from?",
        ],
        "closure_requirements": list(lexicon["closure_requirements"]),
        "closure_status": "open",
        "future_use": "candidate-design-input",
        "automatic_test_creation": False,
        "automatic_policy_mutation": False,
        "persistent_storage": False,
    }
    boundaries = lexicon["boundaries"]
    return {
        "schema": BRIEF_SCHEMA,
        "ability_id": lexicon["ability"]["id"],
        "ability_name": lexicon["ability"]["name"],
        "source_event_schema": karma.EVENT_SCHEMA,
        "source_receipt_schema": karma.RECEIPT_SCHEMA,
        "source_cloudbell_schema": cloudbell.CARD_SCHEMA,
        "source_behavior": event["behavior"],
        "source_signature_id": card["signature_id"],
        "source_stage": receipt["stage"],
        "headline": behavior["headline"],
        "mechanism": card["mechanism"],
        "truth_receipt": truth_receipt,
        "action_card": action_card,
        "learning_seed": learning_seed,
        "causal_rail": [
            {
                "id": step["id"],
                "title": step["title"],
                "description": step["description"],
                "state": step["state"],
            }
            for step in lexicon["causal_steps"]
        ],
        "virtues": list(receipt["virtues"]),
        "recovery": receipt["recovery"],
        **{field: boundaries[field] for field in TRUE_BOUNDARIES},
        **{field: boundaries[field] for field in FALSE_BOUNDARIES},
        "non_claims": list(lexicon["non_claims"]),
    }


def validate_brief(
    brief: dict[str, Any],
    lexicon: dict[str, Any] | None = None,
    hatsu: dict[str, Any] | None = None,
    cloudbell_lexicon: dict[str, Any] | None = None,
) -> None:
    reviewed_lexicon = lexicon if lexicon is not None else load_lexicon()
    validate_lexicon(reviewed_lexicon)
    if not isinstance(brief, dict):
        raise karma.KarmaError("Lantern brief must be an object")
    karma.require_exact_keys(brief, BRIEF_FIELDS, "Lantern brief")
    if brief["schema"] != BRIEF_SCHEMA:
        raise karma.KarmaError("unexpected Lantern brief schema")
    truth = brief["truth_receipt"]
    action = brief["action_card"]
    learning = brief["learning_seed"]
    if not isinstance(truth, dict) or not isinstance(action, dict) or not isinstance(learning, dict):
        raise karma.KarmaError("Lantern nested artifacts must be objects")
    karma.require_exact_keys(truth, TRUTH_FIELDS, "Lantern Truth Receipt")
    karma.require_exact_keys(action, ACTION_FIELDS, "Lantern Action Card")
    karma.require_exact_keys(learning, LEARNING_FIELDS, "Lantern Learning Seed")
    if truth["schema"] != TRUTH_SCHEMA or action["schema"] != ACTION_SCHEMA:
        raise karma.KarmaError("unexpected Lantern truth or action schema")
    if learning["schema"] != LEARNING_SCHEMA:
        raise karma.KarmaError("unexpected Lantern learning schema")
    if not isinstance(truth["normalized_signals"], dict):
        raise karma.KarmaError("Lantern normalized signals must be an object")
    if not isinstance(truth["declarations"], dict):
        raise karma.KarmaError("Lantern declarations must be an object")
    karma.require_exact_keys(
        truth["normalized_signals"], SIGNAL_FIELDS, "Lantern normalized signals"
    )
    karma.require_exact_keys(
        truth["declarations"], DECLARATION_FIELDS, "Lantern declarations"
    )
    require_object_list(
        truth["policy_trace"],
        2,
        7,
        GLOSS_FIELDS,
        "Lantern policy trace",
    )
    require_object_list(
        truth["uncertainties"],
        0,
        4,
        GLOSS_FIELDS,
        "Lantern uncertainties",
    )
    require_object_list(
        truth["policy_inferences"],
        2,
        2,
        INFERENCE_FIELDS,
        "Lantern policy inferences",
    )
    require_object_list(
        action["options"],
        3,
        3,
        OPTION_FIELDS,
        "Lantern action options",
    )
    require_object_list(
        brief["causal_rail"],
        6,
        6,
        CAUSAL_STEP_FIELDS,
        "Lantern causal rail",
    )
    event = learning["replay_event"]
    if not isinstance(event, dict):
        raise karma.KarmaError("Lantern replay event must be an object")
    receipt, card = reviewed_sources(
        event,
        hatsu=hatsu,
        cloudbell_lexicon=cloudbell_lexicon,
    )
    expected = _compose_reviewed_brief(event, receipt, card, reviewed_lexicon)
    if karma.canonical_json(brief) != karma.canonical_json(expected):
        raise karma.KarmaError("Lantern brief differs from its normalized replay")


def create_brief(
    event: dict[str, Any],
    receipt: dict[str, Any] | None = None,
    card: dict[str, Any] | None = None,
    lexicon: dict[str, Any] | None = None,
    hatsu: dict[str, Any] | None = None,
    cloudbell_lexicon: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reviewed_lexicon = lexicon if lexicon is not None else load_lexicon()
    validate_lexicon(reviewed_lexicon)
    reviewed_receipt, reviewed_card = reviewed_sources(
        event,
        receipt=receipt,
        card=card,
        hatsu=hatsu,
        cloudbell_lexicon=cloudbell_lexicon,
    )
    brief = _compose_reviewed_brief(
        event,
        reviewed_receipt,
        reviewed_card,
        reviewed_lexicon,
    )
    validate_brief(
        brief,
        reviewed_lexicon,
        hatsu=hatsu,
        cloudbell_lexicon=cloudbell_lexicon,
    )
    return brief


def load_fixtures() -> dict[str, Any]:
    fixtures = karma.parse_object(
        karma.read_regular(FIXTURE_PATH, "Lantern fixture set"),
        "Lantern fixture set",
    )
    karma.require_exact_keys(fixtures, {"schema", "cases"}, "Lantern fixture set")
    if fixtures["schema"] != FIXTURE_SCHEMA:
        raise karma.KarmaError("unexpected Lantern fixture schema")
    cases = fixtures["cases"]
    if not isinstance(cases, list) or not cases:
        raise karma.KarmaError("Lantern fixtures must contain cases")
    identifiers: set[str] = set()
    lexicon = load_lexicon()
    hatsu = karma.load_hatsu()
    cloudbell_lexicon = cloudbell.load_lexicon()
    for case in cases:
        if not isinstance(case, dict):
            raise karma.KarmaError("Lantern fixture case must be an object")
        karma.require_exact_keys(case, {"id", "event", "expected"}, "Lantern fixture case")
        identifier = require_text(case["id"], "Lantern fixture id")
        if identifier in identifiers:
            raise karma.KarmaError(f"duplicate Lantern fixture id: {identifier}")
        identifiers.add(identifier)
        if not isinstance(case["event"], dict) or not isinstance(case["expected"], dict):
            raise karma.KarmaError(f"Lantern fixture {identifier} must contain objects")
        karma.validate_event(case["event"], hatsu)
        validate_brief(
            case["expected"],
            lexicon,
            hatsu=hatsu,
            cloudbell_lexicon=cloudbell_lexicon,
        )
    return fixtures


def verify_fixtures(fixtures: dict[str, Any] | None = None) -> dict[str, Any]:
    reviewed = fixtures if fixtures is not None else load_fixtures()
    lexicon = load_lexicon()
    hatsu = karma.load_hatsu()
    cloudbell_lexicon = cloudbell.load_lexicon()
    for case in reviewed["cases"]:
        actual = create_brief(
            case["event"],
            lexicon=lexicon,
            hatsu=hatsu,
            cloudbell_lexicon=cloudbell_lexicon,
        )
        if karma.canonical_json(actual) != karma.canonical_json(case["expected"]):
            raise karma.KarmaError(f"Lantern fixture mismatch: {case['id']}")
    return {
        "schema": "karma.lantern/verification-v1",
        "cases": len(reviewed["cases"]),
        "live_ingestion": False,
        "automatic_response": False,
        "automatic_policy_mutation": False,
        "storage_writes": 0,
        "network_calls": 0,
        "external_actions": 0,
        "status": "verified",
    }


def fixture_by_id(identifier: str, fixtures: dict[str, Any]) -> dict[str, Any]:
    matches = [case for case in fixtures["cases"] if case["id"] == identifier]
    if len(matches) != 1:
        raise karma.KarmaError(f"unknown Lantern fixture: {identifier}")
    return matches[0]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render reviewed KARMA Lantern fixtures; ingest and execute nothing."
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--fixture", help="render one reviewed Lantern fixture id")
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
            case = fixture_by_id(args.fixture, fixtures)
            result = create_brief(case["event"], lexicon=lexicon)
        elif args.all_fixtures:
            fixtures = load_fixtures()
            result = {
                "schema": "karma.lantern/results-v1",
                "results": [
                    {
                        "id": case["id"],
                        "brief": create_brief(case["event"], lexicon=lexicon),
                    }
                    for case in fixtures["cases"]
                ],
            }
        elif args.verify_fixtures:
            result = verify_fixtures()
        else:
            result = {
                "schema": "karma.lantern/summary-v1",
                "ability": lexicon["ability"]["name"],
                "epistemic_states": [
                    state["id"] for state in lexicon["epistemic_states"].values()
                ],
                "review_roles": [
                    role["id"] for role in lexicon["review_roles"].values()
                ],
                "causal_steps": [step["id"] for step in lexicon["causal_steps"]],
                "live_ingestion": False,
                "automatic_response": False,
                "action_executed": False,
                "authority_granted": False,
            }
        print(karma.canonical_json(result).decode("utf-8"), end="")
        return 0
    except karma.KarmaError as error:
        parser.exit(2, f"Lantern halted: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
