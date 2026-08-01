#!/usr/bin/env python3
"""Invariant tests for the inert Cloudbell KARMA Herald layer."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import cloudbell
import karma


HERE = Path(__file__).resolve().parent


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


def test_lexicon_is_finite_unique_and_kind() -> None:
    lexicon = cloudbell.load_lexicon()
    assert set(lexicon["behaviors"]) == set(karma.BEHAVIORS)
    assert [stage["karma_stage"] for stage in lexicon["stages"]] == [
        stage[0] for stage in karma.STAGES
    ]
    assert len({item["signature_id"] for item in lexicon["behaviors"].values()}) == 6
    assert len({item["name"] for item in lexicon["behaviors"].values()}) == 6
    assert len({item["stage_id"] for item in lexicon["stages"]}) == 6
    assert len({item["title"] for item in lexicon["stages"]}) == 6
    assert lexicon["mascot"]["fictional"] is True
    assert "guestbook is permanently blank" in lexicon["mascot"]["why_inevitable"]
    assert "Building Castles in the Sky — Yu × Ai / 雲上築城" in lexicon["protocol"]["refrain"]
    lowered_names = " ".join(
        item["name"] for item in lexicon["behaviors"].values()
    ).lower()
    for person_label in ("thief", "attacker", "criminal", "guilty", "stupid"):
        assert person_label not in lowered_names


def test_full_fixtures_are_pinned_and_deterministic() -> None:
    fixtures = cloudbell.load_fixtures()
    verification = cloudbell.verify_fixtures(fixtures)
    assert verification["status"] == "verified"
    assert verification["cases"] == 9
    first = karma.canonical_json(cloudbell.all_fixture_results(fixtures))
    second = karma.canonical_json(cloudbell.all_fixture_results(fixtures))
    assert first == second
    for case in fixtures["cases"]:
        assert cloudbell.create_card(case["event"]) == case["expected"]


def test_six_signatures_name_mechanisms_not_people() -> None:
    lexicon = cloudbell.load_lexicon()
    observed = {}
    for behavior in karma.BEHAVIORS:
        card = cloudbell.create_card(
            event(
                behavior=behavior,
                declared_purpose="constructive" if behavior == "benign" else "exploitative",
                scope_attested=behavior == "benign",
            ),  # type: ignore[arg-type]
            lexicon=lexicon,
        )
        observed[behavior] = card["signature_id"]
        assert card["source_behavior"] == behavior
        assert card["signature_kind"] == "behavior-pattern-alias"
        assert card["behavior_not_person"] is True
        assert card["mechanism"] == lexicon["behaviors"][behavior]["mechanism"]
    assert set(observed) == set(karma.BEHAVIORS)
    assert len(set(observed.values())) == 6


def test_every_stage_copies_the_exact_recovery_path() -> None:
    fixtures = cloudbell.load_fixtures()
    seen = {}
    for case in fixtures["cases"]:
        card = cloudbell.create_card(case["event"])
        seen[card["karma_stage"]] = card
    assert set(seen) == {stage[0] for stage in karma.STAGES}
    for index, (stage, *_rest) in enumerate(karma.STAGES):
        assert seen[stage]["recovery"] == karma.RECOVERIES[index]
        assert seen[stage]["stage_id"] == f"karma.stage.{stage}.v1"


def test_supplied_receipt_must_match_the_event() -> None:
    benign = event()
    reconnaissance = event(
        behavior="reconnaissance",
        declared_purpose="exploitative",
        scope_attested=False,
    )
    benign_receipt = karma.interpret(benign)  # type: ignore[arg-type]
    assert cloudbell.create_card(benign, receipt=benign_receipt)["karma_stage"] == "allow"  # type: ignore[arg-type]
    expect_error(
        lambda: cloudbell.create_card(  # type: ignore[arg-type]
            reconnaissance,
            receipt=benign_receipt,
        )
    )


def test_cards_are_inert_owned_surface_displays() -> None:
    card = cloudbell.create_card(
        event(
            behavior="credential-stuffing",
            repetition=8,
            boundary_crossings=3,
            requested_effect="external",
            declared_purpose="exploitative",
            scope_attested=False,
        )  # type: ignore[arg-type]
    )
    assert card["banner"].startswith("Came looking for a key")
    assert card["owned_surface_only"] is True
    assert card["opt_in_share_only"] is True
    assert card["fictional_mascot"] is True
    for field in (
        "publication_authorized",
        "automatic_posting",
        "forced_propagation",
        "external_delivery",
        "redirects",
        "persistent_tracking",
        "identity_claim",
        "action_executed",
        "authority_granted",
    ):
        assert card[field] is False
    serialized = karma.canonical_json(card).decode("utf-8").lower()
    for prohibited in (
        '"payload"',
        '"identity"',
        '"ip"',
        '"account"',
        '"credential"',
        '"target"',
        '"request_id"',
        '"timestamp"',
        '"counter"',
    ):
        assert prohibited not in serialized


def test_novel_events_and_mutated_cards_fail_closed() -> None:
    extra = event()
    extra["payload"] = "not accepted"
    expect_error(lambda: cloudbell.create_card(extra))  # type: ignore[arg-type]
    expect_error(lambda: cloudbell.create_card(None))  # type: ignore[arg-type]

    lexicon = cloudbell.load_lexicon()
    original = cloudbell.create_card(event(), lexicon=lexicon)  # type: ignore[arg-type]
    mutations = []
    invented = dict(original)
    invented["signature_name"] = "Invented person label"
    mutations.append(invented)
    external = dict(original)
    external["forced_propagation"] = True
    mutations.append(external)
    identity = dict(original)
    identity["identity"] = "not permitted"
    mutations.append(identity)
    missing = dict(original)
    del missing["recovery"]
    mutations.append(missing)
    for mutation in mutations:
        expect_error(lambda mutation=mutation: cloudbell.validate_card(mutation, lexicon))


def test_complete_event_domain_stays_inside_the_lexicon() -> None:
    lexicon = cloudbell.load_lexicon()
    hatsu = karma.load_hatsu()
    signature_ids = {entry["signature_id"] for entry in lexicon["behaviors"].values()}
    stage_ids = {entry["stage_id"] for entry in lexicon["stages"]}
    cases = 0
    for behavior in karma.BEHAVIORS:
        for repetition in range(1, 9):
            for crossings in range(4):
                for effect in karma.REQUESTED_EFFECTS:
                    for purpose in karma.DECLARED_PURPOSES:
                        for scope in (False, True):
                            for complete in (False, True):
                                card = cloudbell.create_card(
                                    event(
                                        behavior=behavior,
                                        repetition=repetition,
                                        boundary_crossings=crossings,
                                        requested_effect=effect,
                                        declared_purpose=purpose,
                                        scope_attested=scope,
                                        evidence_complete=complete,
                                    ),  # type: ignore[arg-type]
                                    lexicon=lexicon,
                                    hatsu=hatsu,
                                )
                                assert card["signature_id"] in signature_ids
                                assert card["stage_id"] in stage_ids
                                assert card["automatic_posting"] is False
                                assert card["external_delivery"] is False
                                cases += 1
    assert cases == 15_360


def test_cli_exposes_only_reviewed_fixtures() -> None:
    good = subprocess.run(
        ["python3", "-B", str(HERE / "cloudbell.py"), "--fixture", "credential-baseline"],
        cwd=HERE,
        text=True,
        capture_output=True,
        check=False,
    )
    assert good.returncode == 0, good.stderr
    assert json.loads(good.stdout)["signature_id"] == "karma.signature.credential-stuffing.v1"

    unknown = subprocess.run(
        ["python3", "-B", str(HERE / "cloudbell.py"), "--fixture", "unknown"],
        cwd=HERE,
        text=True,
        capture_output=True,
        check=False,
    )
    assert unknown.returncode != 0
    assert unknown.stdout == ""
    assert "unknown Cloudbell fixture" in unknown.stderr


def main() -> None:
    tests = [
        test_lexicon_is_finite_unique_and_kind,
        test_full_fixtures_are_pinned_and_deterministic,
        test_six_signatures_name_mechanisms_not_people,
        test_every_stage_copies_the_exact_recovery_path,
        test_supplied_receipt_must_match_the_event,
        test_cards_are_inert_owned_surface_displays,
        test_novel_events_and_mutated_cards_fail_closed,
        test_complete_event_domain_stays_inside_the_lexicon,
        test_cli_exposes_only_reviewed_fixtures,
    ]
    for test in tests:
        test()
    print(f"Cloudbell Herald tests passed: {len(tests)}")


if __name__ == "__main__":
    main()
