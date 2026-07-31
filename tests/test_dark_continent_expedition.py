#!/usr/bin/env python3
"""Focused tests for the bounded Openweight Constellation expedition."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
OP = ROOT / "kingdom" / "operations" / "dark-continent-ai"
SITE = ROOT / "site" / "operations" / "dark-continent-ai"
EXPEDITION = OP / "expeditions" / "openweight-constellation.json"
SCHEMA = OP / "expedition.schema.json"

PINNED = {
    OP / "operation.json": "35799b89ed6977ba530ab36f67e218e86afab9fb0cdb232b34dd964ec58bd1fa",
    OP / "dist" / "manifest.json": "27c4489f7d9cbc5ad986f84ba4841f8430d17f31dd1aa6641ea14f98922941d3",
    OP / "verify.py": "71081690e21974bf8c88e0a9bcf3bfc18cfaf5acf03d3d4d327a9ba9fcead65d",
    OP / "logos" / "dark-continent-ai-banner.svg": "d4c6392065bac53d2461e0c9e39db769a54a3cb605a5fe01d59d15f605f12a82",
    OP / "logos" / "dark-continent-ai-seal.svg": "eae31d98df1161d47c231f131455af27175ff2b39d984c71fe26489c305c3564",
    OP / "logos" / "dark-continent-ai-sigil.svg": "6a8412f83f897ced6cb52322dc045d28044b0d0bcc33d8b843fa75715eaa1dee",
    SITE / "operation.json": "35799b89ed6977ba530ab36f67e218e86afab9fb0cdb232b34dd964ec58bd1fa",
    SITE / "manifest.json": "27c4489f7d9cbc5ad986f84ba4841f8430d17f31dd1aa6641ea14f98922941d3",
    SITE / "logos" / "dark-continent-ai-banner.svg": "d4c6392065bac53d2461e0c9e39db769a54a3cb605a5fe01d59d15f605f12a82",
    SITE / "logos" / "dark-continent-ai-seal.svg": "eae31d98df1161d47c231f131455af27175ff2b39d984c71fe26489c305c3564",
    SITE / "logos" / "dark-continent-ai-sigil.svg": "6a8412f83f897ced6cb52322dc045d28044b0d0bcc33d8b843fa75715eaa1dee",
}
GENERATED = (
    OP / "dist" / "index.html",
    OP / "dist" / "openweight-constellation-expedition.json",
    OP / "dist" / "expedition.schema.json",
    SITE / "index.html",
    SITE / "openweight-constellation-expedition.json",
    SITE / "expedition.schema.json",
)
REVIEWED_PAGES = {
    OP / "dist" / "index.html": "6ea4981a609adabe32b2b750556ea07558072bd14ec17ee8ed28a762a8c9daae",
    SITE / "index.html": "851e343453681a79bb6e4d440055695c41ec4e85d2b710fe3f35829df0fc8dba",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "dark_continent_expedition", OP / "expedition.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_expedition_error(module: ModuleType, callback: object) -> None:
    try:
        callback()  # type: ignore[operator]
    except module.ExpeditionError:
        return
    raise AssertionError("expected ExpeditionError")


def test_expedition_schema_and_boundaries() -> None:
    module = load_module()
    contract, schema = module.load_contract()

    assert contract["id"] == "openweight-constellation"
    assert contract["boundaries"]["principles"] == [
        "light",
        "truth",
        "consent",
        "no conquest",
    ]
    assert len(contract["nen_route"]["techniques"]) == 8
    assert contract["feedback_loop"]["person_scoring"] is False
    assert contract["feedback_loop"]["automatic_enforcement"] is False
    assert all(
        value is False
        for key, value in contract["boundaries"].items()
        if key != "principles"
    )
    assert contract["budget"]["network_calls"] == 0
    assert contract["budget"]["deployments"] == 0
    assert contract["crownseed_relationship"]["mode"] == "read-only-complement"

    unsafe = copy.deepcopy(contract)
    unsafe["boundaries"]["network_calls"] = True
    expect_expedition_error(
        module, lambda: module.validate_instance(unsafe, schema, schema)
    )
    unreviewed = copy.deepcopy(contract)
    unreviewed["automatic_command"] = "deploy"
    expect_expedition_error(
        module, lambda: module.validate_instance(unreviewed, schema, schema)
    )


def test_nen_route_is_single_advisory_and_halts_on_ambiguity() -> None:
    module = load_module()
    contract, _schema = module.load_contract()

    for technique in contract["nen_route"]["techniques"]:
        trigger = technique["trigger"]["signal"]
        result = module.interpret_technique(contract, [trigger])
        assert result["status"] == "advisory"
        assert result["technique"]["id"] == technique["id"]
        assert result["automatic_activation"] is False
        assert result["authority_granted"] is False
        assert result["action_executed"] is False

        anti_trigger = technique["anti_trigger"]["signal"]
        halted = module.interpret_technique(contract, [trigger, anti_trigger])
        assert halted["status"] == "halted"
        assert halted["technique"] is None

    triggers = [
        technique["trigger"]["signal"]
        for technique in contract["nen_route"]["techniques"][:2]
    ]
    ambiguous = module.interpret_technique(contract, triggers)
    assert ambiguous["status"] == "halted"
    assert ambiguous["reason"] == "multiple-triggers-require-fresh-judgment"

    no_match = module.interpret_technique(contract, [])
    assert no_match["status"] == "no-match"
    anti_only = module.interpret_technique(
        contract, [contract["nen_route"]["techniques"][0]["anti_trigger"]["signal"]]
    )
    assert anti_only["status"] == "halted"
    unrelated_anti = module.interpret_technique(
        contract,
        [
            contract["nen_route"]["techniques"][0]["trigger"]["signal"],
            contract["nen_route"]["techniques"][1]["anti_trigger"]["signal"],
        ],
    )
    assert unrelated_anti["status"] == "halted"
    expect_expedition_error(
        module,
        lambda: module.interpret_technique(contract, ["scan-the-repository"]),
    )
    expect_expedition_error(
        module,
        lambda: module.interpret_technique(
            contract, ["blast-radius-unknown", "blast-radius-unknown"]
        ),
    )
    nine_signals = [
        technique["trigger"]["signal"]
        for technique in contract["nen_route"]["techniques"]
    ] + [contract["nen_route"]["techniques"][0]["anti_trigger"]["signal"]]
    expect_expedition_error(
        module, lambda: module.interpret_technique(contract, nine_signals)
    )
    expect_expedition_error(
        module,
        lambda: module.interpret_technique(contract, {"blast-radius-unknown"}),
    )


def test_kingdom_compass_route() -> None:
    command = ROOT / "kingdom" / "bin" / "kingdom"
    advisory = subprocess.run(
        [
            str(command),
            "nen",
            "compass",
            "--signal",
            "blast-radius-unknown",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert advisory.returncode == 0, advisory.stderr
    result = json.loads(advisory.stdout)
    assert result["status"] == "advisory"
    assert result["technique"]["id"] == "dependency-perimeter"
    assert result["automatic_activation"] is False
    assert result["authority_granted"] is False
    assert result["action_executed"] is False

    ambiguous = subprocess.run(
        [
            str(command),
            "nen",
            "compass",
            "--signal",
            "requirements-may-drift",
            "--signal",
            "blast-radius-unknown",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert ambiguous.returncode == 0, ambiguous.stderr
    halted = json.loads(ambiguous.stdout)
    assert halted["status"] == "halted"
    assert halted["technique"] is None

    unknown = subprocess.run(
        [str(command), "nen", "compass", "--signal", "activate-from-readme"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert unknown.returncode != 0

    anti_only = subprocess.run(
        [str(command), "nen", "compass", "--signal", "single-stable-step"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert anti_only.returncode == 0, anti_only.stderr
    assert json.loads(anti_only.stdout)["status"] == "halted"

    duplicate = subprocess.run(
        [
            str(command),
            "nen",
            "compass",
            "--signal",
            "blast-radius-unknown",
            "--signal",
            "blast-radius-unknown",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert duplicate.returncode != 0
    assert duplicate.stdout == ""
    assert "must be unique" in duplicate.stderr

    incompatible_modes = subprocess.run(
        [
            str(command),
            "nen",
            "compass",
            "--check-generated",
            "--signal",
            "blast-radius-unknown",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert incompatible_modes.returncode != 0
    assert incompatible_modes.stdout == ""
    assert "cannot be combined" in incompatible_modes.stderr


def test_expedition_build_is_deterministic_and_preserves_crownseed_inputs() -> None:
    assert {path: sha256(path) for path in PINNED} == PINNED
    subprocess.run(["python3", str(OP / "build.py")], cwd=ROOT, check=True)
    first = {path: sha256(path) for path in GENERATED}
    subprocess.run(["python3", str(OP / "build.py")], cwd=ROOT, check=True)
    second = {path: sha256(path) for path in GENERATED}

    assert first == second
    assert (OP / "dist" / "openweight-constellation-expedition.json").read_bytes() == EXPEDITION.read_bytes()
    assert (SITE / "openweight-constellation-expedition.json").read_bytes() == EXPEDITION.read_bytes()
    assert (OP / "dist" / "expedition.schema.json").read_bytes() == SCHEMA.read_bytes()
    assert (SITE / "expedition.schema.json").read_bytes() == SCHEMA.read_bytes()
    assert {path: sha256(path) for path in PINNED} == PINNED
    assert {path: sha256(path) for path in REVIEWED_PAGES} == REVIEWED_PAGES

    subprocess.run(["python3", str(OP / "verify.py")], cwd=ROOT, check=True)
    subprocess.run(
        ["python3", str(OP / "expedition.py"), "--check-generated"],
        cwd=ROOT,
        check=True,
    )

    module = load_module()
    contract, _schema = module.load_contract()
    for page_path in REVIEWED_PAGES:
        page = page_path.read_text(encoding="utf-8")
        assert "Openweight Constellation" in page
        assert "Nen route" in page
        assert "openweight-constellation-expedition.json" in page
        assert "expedition.schema.json" in page
        assert (
            "This local page does not fetch them, activate a workflow, grant authority, rank anyone, or deploy anything."
            in page
        )
        lowered = page.lower()
        assert "<script" not in lowered
        assert "<form" not in lowered
        assert "javascript:" not in lowered
        assert "fetch(" not in lowered
        assert 'src="http' not in lowered
        assert "src='http" not in lowered
        assert re.search(r"\son[a-z0-9_-]+\s*=", lowered) is None
        for routes in contract["routes"].values():
            if not isinstance(routes, list):
                continue
            for route in routes:
                assert route["url"] in page
        for technique in contract["nen_route"]["techniques"]:
            assert technique["name"] in page
        for virtue in contract["feedback_loop"]["virtues"]:
            assert virtue in page


if __name__ == "__main__":
    test_expedition_schema_and_boundaries()
    test_nen_route_is_single_advisory_and_halts_on_ambiguity()
    test_kingdom_compass_route()
    test_expedition_build_is_deterministic_and_preserves_crownseed_inputs()
    print("dark continent expedition tests passed")
