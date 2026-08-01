#!/usr/bin/env python3
"""Invariant tests for the inert KARMA Lantern legibility layer."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import cloudbell
import karma
import lantern


HERE = Path(__file__).resolve().parent
EXPECTED_LEXICON_SHA256 = "528dab807ef6e624524c5f75b093ad7cc1585240457cbdaff4b62968e05179da"
EXPECTED_SCHEMA_SHA256 = "bdec7f36435536eeab75d3aa8c39eb6fbf4ef3bb8b445024bdeab16ace9f767c"
EXPECTED_FIXTURE_SHA256 = "fbc035d89acd149f568a82aa85afc6d60a0d82e4ea54b2ca155e0f527bc12f5a"
EXPECTED_DOMAIN_SHA256 = "fbbc221ae65b5b5c7518b7542b8257b2162ec31212929a86451324419219fda2"


def event(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema": karma.EVENT_SCHEMA,
        "behavior": "benign",
        "repetition": 1,
        "boundary_crossings": 0,
        "requested_effect": "read",
        "declared_purpose": "constructive",
        "scope_attested": True,
        "evidence_complete": True,
    }
    value.update(changes)
    return value


def expect_error(callback: object) -> None:
    try:
        callback()  # type: ignore[operator]
    except karma.KarmaError:
        return
    raise AssertionError("expected KarmaError")


def clone(value: object) -> object:
    return json.loads(json.dumps(value, ensure_ascii=False))


def digest(path: Path) -> str:
    return hashlib.sha256(karma.read_regular(path, path.name)).hexdigest()


def test_vow_is_finite_and_effect_free() -> None:
    lexicon = lantern.load_lexicon()
    ability = lexicon["ability"]
    assert ability["id"] == "karma.lantern.v1"
    assert ability["budget"] == {
        "briefs_per_event": 1,
        "response_options_per_stage": 3,
        "causal_steps": 6,
        "network_calls": 0,
        "storage_writes": 0,
        "external_actions": 0,
    }
    assert len(ability["conditions"]) == 5
    assert len(ability["limitations"]) == 6
    breach_response = ability["breach_response"].lower()
    assert "reject" in breach_response
    assert "no partial brief" in breach_response
    assert "execute nothing" in breach_response
    assert set(lexicon["epistemic_states"]) == set(lantern.EPISTEMIC_KEYS)
    assert set(lexicon["review_roles"]) == set(lantern.ROLE_KEYS)
    assert set(lexicon["review_priorities"]) == set(lantern.PRIORITY_KEYS)
    assert [step["id"] for step in lexicon["causal_steps"]] == list(lantern.CAUSAL_IDS)
    assert all(lexicon["boundaries"][field] is True for field in lantern.TRUE_BOUNDARIES)
    assert all(lexicon["boundaries"][field] is False for field in lantern.FALSE_BOUNDARIES)
    assert not hasattr(lantern, "compose_brief")


def test_schema_pins_finite_semantics_and_names_runtime_limit() -> None:
    schema = karma.parse_object(
        karma.read_regular(HERE / "lantern.schema.json", "Lantern JSON Schema"),
        "Lantern JSON Schema",
    )
    assert "Canonical lantern.validate_brief" in schema["$comment"]
    assert len(schema["allOf"]) == 37
    causal = schema["properties"]["causal_rail"]
    assert causal["items"] is False
    assert [entry["const"]["id"] for entry in causal["prefixItems"]] == list(
        lantern.CAUSAL_IDS
    )
    trace_tokens = set(
        schema["$defs"]["policyTrace"]["properties"]["token"]["enum"]
    )
    assert trace_tokens == lantern.expected_policy_trace_tokens()
    assert "identity:alice" not in trace_tokens
    assert len(schema["$defs"]["truth"]["allOf"]) == 3


def test_reviewed_artifacts_are_pinned_and_deterministic() -> None:
    assert digest(lantern.LEXICON_PATH) == EXPECTED_LEXICON_SHA256
    assert digest(HERE / "lantern.schema.json") == EXPECTED_SCHEMA_SHA256
    assert digest(lantern.FIXTURE_PATH) == EXPECTED_FIXTURE_SHA256
    fixtures = lantern.load_fixtures()
    assert lantern.verify_fixtures(fixtures)["status"] == "verified"
    assert len(fixtures["cases"]) == 9
    assert {case["expected"]["source_stage"] for case in fixtures["cases"]} == {
        stage[0] for stage in karma.STAGES
    }
    for case in fixtures["cases"]:
        first = lantern.create_brief(case["event"])
        second = lantern.create_brief(case["event"])
        assert first == second == case["expected"]


def test_truth_separates_signal_declaration_inference_and_unknown() -> None:
    complete = lantern.create_brief(event())  # type: ignore[arg-type]
    ambiguous = lantern.create_brief(
        event(declared_purpose="ambiguous")  # type: ignore[arg-type]
    )
    incomplete = lantern.create_brief(
        event(declared_purpose="ambiguous", evidence_complete=False)  # type: ignore[arg-type]
    )
    assert complete["truth_receipt"]["epistemic_id"] == (
        "karma.epistemic.declared-complete.v1"
    )
    assert ambiguous["truth_receipt"]["epistemic_id"] == (
        "karma.epistemic.declared-ambiguous.v1"
    )
    assert incomplete["truth_receipt"]["epistemic_id"] == (
        "karma.epistemic.declared-incomplete.v1"
    )
    truth = incomplete["truth_receipt"]
    assert set(truth["normalized_signals"]) == lantern.SIGNAL_FIELDS
    assert set(truth["declarations"]) == lantern.DECLARATION_FIELDS
    assert [item["kind"] for item in truth["policy_inferences"]] == [
        "karma-stage",
        "cloudbell-signature",
    ]
    assert len(truth["explicit_unknowns"]) == 4
    assert all(
        item["token"] in lantern.expected_policy_trace_tokens()
        for item in truth["policy_trace"]
    )
    assert "incomplete-evidence" in {
        item["token"] for item in truth["uncertainties"]
    }


def test_supplied_sources_must_match_canonically() -> None:
    benign = event()
    injection = event(
        behavior="injection",
        declared_purpose="exploitative",
        scope_attested=False,
    )
    benign_receipt = karma.interpret(benign)  # type: ignore[arg-type]
    benign_card = cloudbell.create_card(benign, receipt=benign_receipt)  # type: ignore[arg-type]
    assert lantern.create_brief(
        benign, receipt=benign_receipt, card=benign_card  # type: ignore[arg-type]
    )["source_stage"] == "allow"
    expect_error(
        lambda: lantern.create_brief(  # type: ignore[arg-type]
            injection,
            receipt=benign_receipt,
        )
    )
    expect_error(
        lambda: lantern.create_brief(  # type: ignore[arg-type]
            injection,
            card=benign_card,
        )
    )


def test_action_card_is_bounded_reversible_and_human_owned() -> None:
    for case in lantern.load_fixtures()["cases"]:
        brief = lantern.create_brief(case["event"])
        receipt = karma.interpret(case["event"])
        card = cloudbell.create_card(case["event"], receipt=receipt)
        action = brief["action_card"]
        assert len(action["options"]) == 3
        assert all(option["reversible"] is True for option in action["options"])
        assert action["options_proposed_only"] is True
        assert action["human_decision_required"] is True
        assert action["policy_values_advisory_only"] is True
        assert action["policy_stage"] == receipt["stage"]
        assert action["advisory_route"] == receipt["route"]
        assert action["advisory_capability_percent"] == receipt["real_capability_percent"]
        assert action["display_friction_units"] == receipt["friction_units"]
        assert action["advisory_recovery_steps"] == receipt["ttl_steps"]
        assert action["action_executed"] is False
        assert action["authority_granted"] is False
        assert brief["recovery"] == action["recovery"] == receipt["recovery"]
        assert brief["recovery"] == card["recovery"]


def test_learning_seed_is_normalized_open_and_non_automatic() -> None:
    source = event(
        behavior="scraping-resource-abuse",
        repetition=8,
        boundary_crossings=3,
        requested_effect="external",
        declared_purpose="exploitative",
        scope_attested=False,
    )
    brief = lantern.create_brief(source)  # type: ignore[arg-type]
    seed = brief["learning_seed"]
    assert seed["replay_event"] == source
    assert tuple(seed["replay_event"]) == lantern.EVENT_FIELD_ORDER
    assert seed["closure_status"] == "open"
    assert seed["future_use"] == "candidate-design-input"
    assert len(seed["regression_targets"]) == 3
    assert len(seed["architecture_questions"]) == 2
    assert len(seed["closure_requirements"]) == 4
    assert seed["automatic_test_creation"] is False
    assert seed["automatic_policy_mutation"] is False
    assert seed["persistent_storage"] is False


def test_briefs_are_behavior_not_person_and_have_no_effect_surface() -> None:
    brief = lantern.create_brief(
        event(
            behavior="credential-stuffing",
            repetition=8,
            boundary_crossings=3,
            requested_effect="external",
            declared_purpose="exploitative",
            scope_attested=False,
        )  # type: ignore[arg-type]
    )
    assert brief["behavior_not_person"] is True
    assert brief["explanatory_only"] is True
    assert brief["owned_surface_only"] is True
    assert brief["no_time_guarantee"] is True
    assert all(brief[field] is False for field in lantern.FALSE_BOUNDARIES)
    serialized = karma.canonical_json(brief).decode("utf-8").lower()
    for prohibited in (
        '"payload"',
        '"identity"',
        '"ip"',
        '"account"',
        '"credential"',
        '"target"',
        '"timestamp"',
        '"request_id"',
    ):
        assert prohibited not in serialized


def test_novel_inputs_and_mutated_briefs_fail_closed() -> None:
    extra = event()
    extra["payload"] = "never accepted"
    expect_error(lambda: lantern.create_brief(extra))  # type: ignore[arg-type]
    expect_error(lambda: lantern.create_brief(None))  # type: ignore[arg-type]
    original = lantern.create_brief(event())  # type: ignore[arg-type]
    mutations = []

    enabled = clone(original)
    assert isinstance(enabled, dict)
    enabled["network_calls"] = True
    mutations.append(enabled)

    extra_field = clone(original)
    assert isinstance(extra_field, dict)
    extra_field["actor"] = "invented"
    mutations.append(extra_field)

    changed_recovery = clone(original)
    assert isinstance(changed_recovery, dict)
    changed_recovery["recovery"] = "Never recover."
    mutations.append(changed_recovery)

    invented_option = clone(original)
    assert isinstance(invented_option, dict)
    invented_option["action_card"]["options"][0]["label"] = "Automatic retaliation"
    mutations.append(invented_option)

    stored_replay = clone(original)
    assert isinstance(stored_replay, dict)
    stored_replay["learning_seed"]["persistent_storage"] = True
    mutations.append(stored_replay)

    for mutation in mutations:
        expect_error(lambda mutation=mutation: lantern.validate_brief(mutation))

    malformed_fields = (
        ("truth_receipt", "policy_trace"),
        ("truth_receipt", "uncertainties"),
        ("truth_receipt", "policy_inferences"),
        ("action_card", "options"),
    )
    for parent, field in malformed_fields:
        malformed = clone(original)
        assert isinstance(malformed, dict)
        malformed[parent][field] = None
        expect_error(lambda malformed=malformed: lantern.validate_brief(malformed))
    malformed_rail = clone(original)
    assert isinstance(malformed_rail, dict)
    malformed_rail["causal_rail"] = None
    expect_error(lambda: lantern.validate_brief(malformed_rail))


def test_dependency_contracts_are_semantically_pinned() -> None:
    source = event()
    expect_error(lambda: lantern.create_brief(source, hatsu=[]))  # type: ignore[arg-type]
    expect_error(
        lambda: lantern.create_brief(source, cloudbell_lexicon=[])  # type: ignore[arg-type]
    )
    expect_error(
        lambda: lantern.create_brief(source, lexicon=[])  # type: ignore[arg-type]
    )

    hatsu = clone(karma.load_hatsu())
    assert isinstance(hatsu, dict)
    hatsu["desire"] = "A novel but structurally valid desire."
    expect_error(lambda: lantern.create_brief(source, hatsu=hatsu))  # type: ignore[arg-type]

    cloudbell_lexicon = clone(cloudbell.load_lexicon())
    assert isinstance(cloudbell_lexicon, dict)
    cloudbell_lexicon["behaviors"]["benign"]["mechanism"] = (
        "Attribute this pattern to a person."
    )
    expect_error(
        lambda: lantern.create_brief(  # type: ignore[arg-type]
            source,
            cloudbell_lexicon=cloudbell_lexicon,
        )
    )

    lantern_lexicon = clone(lantern.load_lexicon())
    assert isinstance(lantern_lexicon, dict)
    lantern_lexicon["stages"]["allow"]["response_options"][0]["reason"] = (
        "Execute an irreversible external action."
    )
    expect_error(
        lambda: lantern.create_brief(  # type: ignore[arg-type]
            source,
            lexicon=lantern_lexicon,
        )
    )


def test_quarantine_is_explicitly_advisory_not_enforcement() -> None:
    brief = lantern.create_brief(
        event(
            behavior="credential-stuffing",
            repetition=8,
            boundary_crossings=3,
            requested_effect="external",
            declared_purpose="exploitative",
            scope_attested=False,
        )  # type: ignore[arg-type]
    )
    action = brief["action_card"]
    assert action["policy_stage"] == "quarantine"
    assert action["advisory_route"] == "none"
    assert action["advisory_capability_percent"] == 0
    assert action["policy_values_advisory_only"] is True
    assert action["action_executed"] is False
    assert action["authority_granted"] is False
    assert any(
        "not evidence that enforcement happened" in non_claim
        for non_claim in brief["non_claims"]
    )


def test_cli_bytes_ignore_python_hash_seed() -> None:
    outputs = []
    for seed in ("1", "2", "99"):
        result = subprocess.run(
            ["python3", "-B", str(HERE / "lantern.py"), "--fixture", "benign-basic"],
            cwd=HERE,
            env={**os.environ, "PYTHONHASHSEED": seed},
            text=False,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr.decode("utf-8")
        outputs.append(result.stdout)
    assert outputs[0] == outputs[1] == outputs[2]


def test_complete_event_domain_stays_bounded_and_legible() -> None:
    lexicon = lantern.load_lexicon()
    hatsu = karma.load_hatsu()
    cloudbell_lexicon = cloudbell.load_lexicon()
    epistemic_ids = {
        value["id"] for value in lexicon["epistemic_states"].values()
    }
    role_ids = {value["id"] for value in lexicon["review_roles"].values()}
    priority_ids = {
        value["id"] for value in lexicon["review_priorities"].values()
    }
    domain_digest = hashlib.sha256()
    cases = 0
    for behavior in karma.BEHAVIORS:
        for repetition in range(1, 9):
            for crossings in range(4):
                for effect in karma.REQUESTED_EFFECTS:
                    for purpose in karma.DECLARED_PURPOSES:
                        for scope in (False, True):
                            for complete in (False, True):
                                source = event(
                                    behavior=behavior,
                                    repetition=repetition,
                                    boundary_crossings=crossings,
                                    requested_effect=effect,
                                    declared_purpose=purpose,
                                    scope_attested=scope,
                                    evidence_complete=complete,
                                )
                                receipt = karma.interpret(source, hatsu)  # type: ignore[arg-type]
                                card = cloudbell.create_card(
                                    source,  # type: ignore[arg-type]
                                    receipt=receipt,
                                    lexicon=cloudbell_lexicon,
                                    hatsu=hatsu,
                                )
                                brief = lantern.create_brief(
                                    source,  # type: ignore[arg-type]
                                    receipt=receipt,
                                    card=card,
                                    lexicon=lexicon,
                                    hatsu=hatsu,
                                    cloudbell_lexicon=cloudbell_lexicon,
                                )
                                truth = brief["truth_receipt"]
                                action = brief["action_card"]
                                assert truth["epistemic_id"] in epistemic_ids
                                assert action["suggested_review_role_id"] in role_ids
                                assert action["review_priority_id"] in priority_ids
                                assert len(action["options"]) == 3
                                assert len(brief["causal_rail"]) == 6
                                assert brief["recovery"] == receipt["recovery"]
                                assert all(
                                    brief[field] is False
                                    for field in lantern.FALSE_BOUNDARIES
                                )
                                domain_digest.update(
                                    karma.canonical_json(
                                        {
                                            "event": source,
                                            "receipt": receipt,
                                            "cloudbell": card,
                                            "lantern": brief,
                                        }
                                    )
                                )
                                cases += 1
    assert cases == 15_360
    assert domain_digest.hexdigest() == EXPECTED_DOMAIN_SHA256


def test_cli_exposes_only_reviewed_fixtures() -> None:
    good = subprocess.run(
        ["python3", "-B", str(HERE / "lantern.py"), "--fixture", "injection-baseline"],
        cwd=HERE,
        text=True,
        capture_output=True,
        check=False,
    )
    assert good.returncode == 0, good.stderr
    rendered = json.loads(good.stdout)
    assert rendered["source_signature_id"] == "karma.signature.injection.v1"
    assert rendered["source_stage"] == "shadow"

    unknown = subprocess.run(
        ["python3", "-B", str(HERE / "lantern.py"), "--fixture", "unknown"],
        cwd=HERE,
        text=True,
        capture_output=True,
        check=False,
    )
    assert unknown.returncode != 0
    assert unknown.stdout == ""
    assert "unknown Lantern fixture" in unknown.stderr


def main() -> None:
    tests = [
        test_vow_is_finite_and_effect_free,
        test_schema_pins_finite_semantics_and_names_runtime_limit,
        test_reviewed_artifacts_are_pinned_and_deterministic,
        test_truth_separates_signal_declaration_inference_and_unknown,
        test_supplied_sources_must_match_canonically,
        test_action_card_is_bounded_reversible_and_human_owned,
        test_learning_seed_is_normalized_open_and_non_automatic,
        test_briefs_are_behavior_not_person_and_have_no_effect_surface,
        test_novel_inputs_and_mutated_briefs_fail_closed,
        test_dependency_contracts_are_semantically_pinned,
        test_quarantine_is_explicitly_advisory_not_enforcement,
        test_cli_bytes_ignore_python_hash_seed,
        test_complete_event_domain_stays_bounded_and_legible,
        test_cli_exposes_only_reviewed_fixtures,
    ]
    for test in tests:
        test()
    print(f"KARMA Lantern tests passed: {len(tests)}")


if __name__ == "__main__":
    main()
