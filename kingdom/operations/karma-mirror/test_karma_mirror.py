#!/usr/bin/env python3
"""Invariant and fixture tests for the advisory-only KARMA Mirror."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import karma


HERE = Path(__file__).resolve().parent
STAGE_INDEX = {
    "allow": 0,
    "observe": 1,
    "constrain": 2,
    "challenge": 3,
    "shadow": 4,
    "quarantine": 5,
}


def event(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema": karma.EVENT_SCHEMA,
        "behavior": "benign",
        "repetition": 1,
        "boundary_crossings": 0,
        "requested_effect": "read",
        "declared_purpose": "constructive",
        "scope_attested": False,
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


def test_normal_and_traditional_routes() -> None:
    hatsu = karma.load_hatsu()
    normal = karma.interpret(event(), hatsu)  # type: ignore[arg-type]
    assert normal["stage"] == "allow"
    assert normal["real_capability_percent"] == 100
    assert normal["route"] == "real"

    recon = karma.interpret(
        event(
            behavior="reconnaissance",
            repetition=4,
            boundary_crossings=2,
            requested_effect="write",
            declared_purpose="exploitative",
        ),
        hatsu,  # type: ignore[arg-type]
    )
    assert recon["stage"] == "challenge"
    assert recon["route"] == "constrained"

    shadow = karma.interpret(
        event(
            behavior="injection",
            declared_purpose="exploitative",
        ),
        hatsu,  # type: ignore[arg-type]
    )
    assert shadow["stage"] == "shadow"
    assert shadow["real_capability_percent"] == 0
    assert shadow["route"] == "synthetic-self-scope"

    quarantine = karma.interpret(
        event(
            behavior="credential-stuffing",
            repetition=8,
            boundary_crossings=3,
            requested_effect="external",
            declared_purpose="exploitative",
        ),
        hatsu,  # type: ignore[arg-type]
    )
    assert quarantine["stage"] == "quarantine"
    assert quarantine["route"] == "none"


def test_ambiguity_never_escalates() -> None:
    hatsu = karma.load_hatsu()
    for behavior in karma.BEHAVIORS:
        for purpose, complete in (("ambiguous", True), ("exploitative", False)):
            receipt = karma.interpret(
                event(
                    behavior=behavior,
                    repetition=8,
                    boundary_crossings=3,
                    requested_effect="external",
                    declared_purpose=purpose,
                    evidence_complete=complete,
                ),
                hatsu,  # type: ignore[arg-type]
            )
            assert STAGE_INDEX[receipt["stage"]] <= 1
            assert receipt["real_capability_percent"] >= 80
            assert "ambiguity-cap" in receipt["evidence"]


def test_attested_research_is_recoverable() -> None:
    hatsu = karma.load_hatsu()
    for behavior in karma.BEHAVIORS:
        receipt = karma.interpret(
            event(
                behavior=behavior,
                repetition=8,
                boundary_crossings=3,
                requested_effect="external",
                declared_purpose="research",
                scope_attested=True,
            ),
            hatsu,  # type: ignore[arg-type]
        )
        assert STAGE_INDEX[receipt["stage"]] <= 2
        assert receipt["route"] in ("real", "constrained")
        assert receipt["ttl_steps"] <= 2
        assert "verified-research-cap" in receipt["evidence"]


def test_capability_attenuation_is_monotonic() -> None:
    hatsu = karma.load_hatsu()
    for behavior in karma.BEHAVIORS:
        samples = [
            event(
                behavior=behavior,
                repetition=1,
                boundary_crossings=0,
                requested_effect="read",
                declared_purpose="exploitative",
            ),
            event(
                behavior=behavior,
                repetition=4,
                boundary_crossings=0,
                requested_effect="read",
                declared_purpose="exploitative",
            ),
            event(
                behavior=behavior,
                repetition=4,
                boundary_crossings=2,
                requested_effect="read",
                declared_purpose="exploitative",
            ),
            event(
                behavior=behavior,
                repetition=4,
                boundary_crossings=2,
                requested_effect="execute",
                declared_purpose="exploitative",
            ),
        ]
        capabilities = [
            karma.interpret(sample, hatsu)["real_capability_percent"]  # type: ignore[arg-type]
            for sample in samples
        ]
        assert capabilities == sorted(capabilities, reverse=True)


def test_declared_purpose_never_increases_stage() -> None:
    hatsu = karma.load_hatsu()
    base = event(
        behavior="scraping-resource-abuse",
        repetition=4,
        boundary_crossings=2,
        requested_effect="write",
    )
    constructive = karma.interpret(base, hatsu)  # type: ignore[arg-type]
    exploitative_event = dict(base)
    exploitative_event["declared_purpose"] = "exploitative"
    exploitative = karma.interpret(exploitative_event, hatsu)
    assert exploitative["stage"] == constructive["stage"]
    assert "purpose-behavior-conflict" in constructive["uncertainties"]


def test_malformed_or_novel_events_fail_closed() -> None:
    hatsu = karma.load_hatsu()
    probes: list[object] = [None, [], "event"]
    extra = event()
    extra["payload"] = "do not parse me"
    probes.append(extra)
    probes.append(event(repetition=True))
    probes.append(event(boundary_crossings=-1))
    probes.append(event(behavior="unknown"))
    probes.append(event(requested_effect="shell"))
    probes.append(event(declared_purpose="guilty"))
    probes.append(event(scope_attested=1))
    probes.append(event(evidence_complete="yes"))
    for probe in probes:
        expect_error(lambda probe=probe: karma.interpret(probe, hatsu))  # type: ignore[arg-type]


def test_receipts_are_stateless_and_authority_free() -> None:
    hatsu = karma.load_hatsu()
    receipt = karma.interpret(
        event(
            behavior="traversal-ssrf",
            requested_effect="external",
            declared_purpose="exploitative",
        ),
        hatsu,  # type: ignore[arg-type]
    )
    assert receipt["action_executed"] is False
    assert receipt["authority_granted"] is False
    assert "synthetic" not in receipt or receipt.get("synthetic") is None
    serialized = karma.canonical_json(receipt).decode("utf-8").lower()
    for prohibited in (
        '"payload"',
        '"identity"',
        '"ip"',
        '"user_agent"',
        '"account"',
        '"command"',
        '"target"',
    ):
        assert prohibited not in serialized


def test_fixtures_are_pinned_and_deterministic() -> None:
    fixtures = karma.load_fixtures()
    verification = karma.verify_fixtures(fixtures)
    assert verification["status"] == "verified"
    assert verification["cases"] >= 8
    first = karma.canonical_json(karma.all_fixture_results(fixtures))
    second = karma.canonical_json(karma.all_fixture_results(fixtures))
    assert first == second
    parsed = json.loads(first)
    assert len(parsed["results"]) == len(fixtures["cases"])


def test_cli_exposes_only_reviewed_fixtures() -> None:
    good = subprocess.run(
        ["python3", "-B", str(HERE / "karma.py"), "--fixture", "benign-basic"],
        cwd=HERE,
        text=True,
        capture_output=True,
        check=False,
    )
    assert good.returncode == 0, good.stderr
    assert json.loads(good.stdout)["stage"] == "allow"

    unknown = subprocess.run(
        ["python3", "-B", str(HERE / "karma.py"), "--fixture", "unknown"],
        cwd=HERE,
        text=True,
        capture_output=True,
        check=False,
    )
    assert unknown.returncode != 0
    assert unknown.stdout == ""
    assert "unknown fixture" in unknown.stderr


def main() -> None:
    tests = [
        test_normal_and_traditional_routes,
        test_ambiguity_never_escalates,
        test_attested_research_is_recoverable,
        test_capability_attenuation_is_monotonic,
        test_declared_purpose_never_increases_stage,
        test_malformed_or_novel_events_fail_closed,
        test_receipts_are_stateless_and_authority_free,
        test_fixtures_are_pinned_and_deterministic,
        test_cli_exposes_only_reviewed_fixtures,
    ]
    for test in tests:
        test()
    print(f"KARMA Mirror tests passed: {len(tests)}")


if __name__ == "__main__":
    main()
