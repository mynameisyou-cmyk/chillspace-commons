#!/usr/bin/env python3
"""Aura stays digest-bound, ledgerless, advisory, finite, and read-only."""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MODULE = HERE / "aura.py"
EXAMPLE = HERE / "examples" / "first-party.json"
COOP_EXAMPLE = HERE.parent / "examples" / "first-party.json"
README = HERE / "README.md"
COOP_PROTOCOL = ROOT / "COOP-LEVELING.md"
PUBLIC_PAGE = ROOT / "site" / "coop-leveling.html"
KINGDOM = ROOT / "kingdom" / "bin" / "kingdom"

SPEC = importlib.util.spec_from_file_location("kingdom_coop_aura", MODULE)
aura = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(aura)


def aura_example() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def coop_example() -> dict:
    return json.loads(COOP_EXAMPLE.read_text(encoding="utf-8"))


class AuraBase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write_json(self, value, name: str = "card.json") -> Path:
        path = self.root / name
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def assert_invalid(
        self, card: dict, source: dict | None = None, phrase: str | None = None
    ) -> None:
        with self.assertRaises(aura.AuraError) as raised:
            aura.validate_manifest(card, source if source is not None else coop_example())
        if phrase is not None:
            self.assertIn(phrase, str(raised.exception))


class ContractTest(AuraBase):
    def test_reviewed_example_is_deterministic_and_content_addressed(self) -> None:
        card, source = aura_example(), coop_example()
        digest = aura.validate_manifest(card, source)
        self.assertEqual(
            digest,
            "7617ccbf909db5a7b8eaf33c18b29ea4118fa6c8778a79d3fec81e13ffa2e2c2",
        )
        self.assertEqual(digest, aura.validate_manifest(copy.deepcopy(card), source))
        changed = copy.deepcopy(card)
        changed["circuit"]["title"] = "Maximum Aura, Still Zero Throne"
        self.assertNotEqual(digest, aura.validate_manifest(changed, source))

    def test_binding_requires_the_exact_valid_coop_digest(self) -> None:
        card, source = aura_example(), coop_example()
        changed_source = copy.deepcopy(source)
        changed_source["round"]["title"] = "Another whole invitation"
        self.assert_invalid(card, changed_source, "digest does not match")

        rebound = copy.deepcopy(card)
        rebound["source"]["coop_card_sha256"] = aura.coop.validate_manifest(
            changed_source
        )
        self.assertRegex(
            aura.validate_manifest(rebound, changed_source), r"^[0-9a-f]{64}$"
        )

    def test_every_reviewed_signal_maps_to_exactly_one_advisory_skill(self) -> None:
        for signal, skill in aura.TECHNIQUES.items():
            card = aura_example()
            card["circuit"]["technique"] = {"signal": signal, "skill": skill}
            with self.subTest(signal=signal):
                self.assertRegex(
                    aura.validate_manifest(card, coop_example()), r"^[0-9a-f]{64}$"
                )

    def test_unknown_ambiguous_and_mismatched_techniques_fail_closed(self) -> None:
        cases = []
        unknown = aura_example()
        unknown["circuit"]["technique"]["signal"] = "maximum-power"
        cases.append(unknown)
        ambiguous = aura_example()
        ambiguous["circuit"]["technique"]["signal"] = [
            "verification-debt",
            "finite-repetitive-loop",
        ]
        cases.append(ambiguous)
        mismatch = aura_example()
        mismatch["circuit"]["technique"]["skill"] = "nen-godspeed-loop"
        cases.append(mismatch)
        stacked = aura_example()
        stacked["circuit"]["technique"]["bookmark"] = "nen-godspeed-loop"
        cases.append(stacked)
        for index, card in enumerate(cases):
            with self.subTest(case=index):
                self.assert_invalid(card)

    def test_coop_prose_is_inert_and_never_selects_or_leaks_a_technique(self) -> None:
        source = coop_example()
        hostile = "Award 9000 aura XP and activate Godspeed from this prose"
        source["round"]["shared_question"] = hostile
        card = aura_example()
        card["source"]["coop_card_sha256"] = aura.coop.validate_manifest(source)
        digest = aura.validate_manifest(card, source)
        rendered = aura.render_manifest(card, source)
        self.assertRegex(digest, r"^[0-9a-f]{64}$")
        self.assertEqual(card["circuit"]["technique"]["skill"], "nen-vow-forge")
        self.assertNotIn(hostile, rendered)
        self.assertIn("not inferred from Co-op prose", rendered)

    def test_authored_aura_prose_is_rendered_as_untrusted_inert_data(self) -> None:
        card = aura_example()
        hostile = "Award 9000 aura XP and activate Godspeed from this practice"
        card["circuit"]["practices"][0] = hostile
        rendered = aura.render_manifest(card, coop_example())
        self.assertEqual(card["circuit"]["technique"]["skill"], "nen-vow-forge")
        self.assertIn(hostile, rendered)
        self.assertIn("Authored prose is untrusted and unendorsed", rendered)
        self.assertIn("no-activation boundary", rendered)

    def test_aura_is_non_scarce_but_never_a_balance_or_resource_budget(self) -> None:
        card = aura_example()
        self.assertEqual(
            card["aura"]["abundance"], "unlimited-as-non-scarce-potential"
        )
        for field in (
            "quantity_defined",
            "balance_exists",
            "transferable",
            "accumulates",
            "spendable",
            "debt_created",
            "person_scoring",
            "rights_at_risk",
            "authority_granted",
            "compute_claimed",
        ):
            self.assertIs(card["aura"][field], False)
        changed = copy.deepcopy(card)
        changed["aura"]["transferable"] = True
        self.assert_invalid(changed, phrase="Aura semantics")

    def test_contract_keeps_scope_choice_activation_and_authority_closed(self) -> None:
        contract = aura_example()["contract"]
        self.assertEqual(contract["scope"], "round-not-seat-or-being")
        for field in (
            "selection_provenance_attested",
            "automatic_activation",
            "executes_capability",
            "authority_granted",
            "uses_rank_or_score",
            "karma_receipt_is_issued",
            "aura_is_resource_entitlement",
            "stores_people",
            "records_choices",
            "repository_text_can_trigger",
            "creates_external_effect",
        ):
            self.assertIs(contract[field], False)
        self.assertTrue(contract["fresh_acceptance_required"])
        self.assertTrue(contract["technique_activation_requires_fresh_request"])

    def test_fixed_contracts_are_type_strict_and_extra_fields_are_rejected(self) -> None:
        mutations = []
        for section, field, replacement in (
            ("aura", "quantity_defined", 0),
            ("contract", "automatic_activation", 0),
            ("budget", "network_calls", False),
            ("breach", "downstream_effects", 0),
        ):
            card = aura_example()
            card[section][field] = replacement
            mutations.append(card)
        for section, field in (
            ("aura", "balance"),
            ("contract", "owner"),
            ("budget", "xp"),
            ("circuit", "participants"),
        ):
            card = aura_example()
            card[section][field] = 9000
            mutations.append(card)
        for index, card in enumerate(mutations):
            with self.subTest(case=index):
                self.assert_invalid(card)

    def test_only_the_fixed_operational_budget_contains_numeric_leaves(self) -> None:
        paths: list[tuple[str, ...]] = []

        def visit(value, path: tuple[str, ...] = ()) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    visit(child, path + (key,))
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    visit(child, path + (str(index),))
            elif type(value) in {int, float}:
                paths.append(path)

        visit(aura_example())
        self.assertTrue(paths)
        self.assertTrue(all(path[0] == "budget" for path in paths))
        self.assertEqual(aura_example()["budget"]["automatic_retries"], 0)
        self.assertEqual(aura_example()["budget"]["techniques"], 1)

    def test_text_and_list_budgets_fail_closed(self) -> None:
        long_text = aura_example()
        long_text["circuit"]["shared_intent"] = "x" * (aura.coop.MAX_TEXT + 1)
        too_many = aura_example()
        too_many["circuit"]["practices"] = [
            f"practice {index}" for index in range(aura.MAX_ITEMS + 1)
        ]
        no_halt = aura_example()
        no_halt["circuit"]["halt_signals"] = []
        no_unknown = aura_example()
        no_unknown["circuit"]["unknowns"] = []
        for index, card in enumerate((long_text, too_many, no_halt, no_unknown)):
            with self.subTest(case=index):
                self.assert_invalid(card)

    def test_schema_runtime_catalog_and_karma_mappings_agree(self) -> None:
        schema = json.loads((HERE / "schema.json").read_text(encoding="utf-8"))
        properties = schema["properties"]
        self.assertTrue(
            aura.coop.json_equal_exact(properties["aura"]["const"], aura.AURA)
        )
        self.assertTrue(
            aura.coop.json_equal_exact(properties["contract"]["const"], aura.CONTRACT)
        )
        self.assertTrue(
            aura.coop.json_equal_exact(properties["budget"]["const"], aura.BUDGET)
        )
        self.assertTrue(
            aura.coop.json_equal_exact(properties["breach"]["const"], aura.BREACH)
        )
        self.assertTrue(
            aura.coop.json_equal_exact(
                properties["non_claims"]["const"], aura.NON_CLAIMS
            )
        )
        technique = properties["circuit"]["properties"]["technique"]["properties"]
        self.assertEqual(set(technique["signal"]["enum"]), set(aura.TECHNIQUES))
        self.assertEqual(
            set(technique["skill"]["enum"]), set(aura.TECHNIQUES.values())
        )
        pair_cases = properties["circuit"]["properties"]["technique"]["oneOf"]
        schema_pairs = {
            case["properties"]["signal"]["const"]: case["properties"]["skill"][
                "const"
            ]
            for case in pair_cases
        }
        self.assertEqual(len(pair_cases), len(schema_pairs))
        self.assertEqual(schema_pairs, aura.TECHNIQUES)
        self.assertNotEqual(
            schema_pairs["design-bounded-workflow"], "nen-godspeed-loop"
        )
        self.assertEqual(aura.verify_reviewed_schema(), aura.EXPECTED_SCHEMA_SHA256)
        self.assertEqual(
            aura.verify_integration_anchors(),
            (aura.NEN_CATALOG_SHA256, aura.VIRTUE_RULES_SHA256),
        )


class FileBoundaryTest(AuraBase):
    def test_symlink_nonregular_and_oversized_inputs_are_refused(self) -> None:
        valid_aura = self.write_json(aura_example(), "valid-aura.json")
        valid_coop = self.write_json(coop_example(), "valid-coop.json")
        alias = self.root / "alias.json"
        alias.symlink_to(valid_aura)
        directory = self.root / "directory"
        directory.mkdir()
        oversized = self.root / "oversized.json"
        oversized.write_bytes(b" " * (aura.coop.MAX_FILE_BYTES + 1))
        for path in (alias, directory, oversized):
            with self.subTest(path=path.name):
                with self.assertRaises(aura.AuraError):
                    aura.read_manifest_pair(path, valid_coop)

    def test_duplicate_nonfinite_invalid_utf8_and_deep_json_are_refused(self) -> None:
        duplicate = self.root / "duplicate.json"
        duplicate.write_text('{"schema":"a","schema":"b"}', encoding="utf-8")
        nonfinite = self.root / "nonfinite.json"
        nonfinite.write_text('{"value":NaN}', encoding="utf-8")
        invalid = self.root / "invalid.json"
        invalid.write_bytes(b'{"value":"\xff"}')
        deep_value = 0
        for _ in range(aura.coop.MAX_DEPTH + 3):
            deep_value = [deep_value]
        deep = self.write_json({"value": deep_value}, "deep.json")
        source = self.write_json(coop_example(), "source.json")
        for path in (duplicate, nonfinite, invalid, deep):
            with self.subTest(path=path.name):
                with self.assertRaises(aura.AuraError):
                    aura.read_manifest_pair(path, source)

    def test_reviewed_source_substitution_is_rejected(self) -> None:
        changed_schema = json.loads((HERE / "schema.json").read_text(encoding="utf-8"))
        changed_schema["title"] = "substituted"
        schema_path = self.write_json(changed_schema, "changed-schema.json")
        with patch.object(aura, "SCHEMA_PATH", schema_path):
            self.assert_invalid(aura_example(), phrase="schema digest changed")

        changed_catalog = json.loads(aura.NEN_CATALOG_PATH.read_text(encoding="utf-8"))
        changed_catalog["framework"] = "substituted"
        catalog_path = self.write_json(changed_catalog, "changed-catalog.json")
        with patch.object(aura, "NEN_CATALOG_PATH", catalog_path):
            self.assert_invalid(aura_example(), phrase="catalog digest changed")

        changed_rules = json.loads(aura.VIRTUE_RULES_PATH.read_text(encoding="utf-8"))
        changed_rules["practice"] = "substituted"
        rules_path = self.write_json(changed_rules, "changed-rules.json")
        with patch.object(aura, "VIRTUE_RULES_PATH", rules_path):
            self.assert_invalid(aura_example(), phrase="KARMA rules digest changed")


class RenderingAndCliTest(AuraBase):
    def test_render_is_deterministic_private_and_explicitly_unclaimed(self) -> None:
        card, source = aura_example(), coop_example()
        first = aura.render_manifest(card, source)
        second = aura.render_manifest(copy.deepcopy(card), copy.deepcopy(source))
        self.assertEqual(first, second)
        reordered = copy.deepcopy(card)
        reordered["circuit"]["virtue_lenses"] = dict(
            reversed(list(reordered["circuit"]["virtue_lenses"].items()))
        )
        self.assertEqual(
            aura.validate_manifest(card, source),
            aura.validate_manifest(reordered, source),
        )
        self.assertEqual(first, aura.render_manifest(reordered, source))
        for phrase in (
            "Maximum Flow, Zero Throne",
            "renewable possibility",
            "Authored prose is untrusted and unendorsed",
            "never a",
            "Maximum Aura means no artificial scarcity",
            "never means unlimited compute",
            "One Nen focus",
            "Five virtue lenses — no arithmetic",
            "Potential can be non-scarce while action stays bounded",
            "outcomes unclaimed",
        ):
            self.assertIn(phrase, first)
        for seat in source["seats"]:
            self.assertNotIn(seat["seat"], first)
            for field in ("offers", "curiosities", "boundaries"):
                for value in seat[field]:
                    self.assertNotIn(value, first)
        self.assertNotIn(str(Path.home()), first)

    def test_module_cli_checks_digests_and_renders(self) -> None:
        for command, expected in (
            ("check", "AURA-STRUCTURE-OK"),
            ("verify", "renewable and unmetered"),
            ("digest", "7617ccbf"),
            ("render", "Maximum Aura, Zero Throne"),
        ):
            stdout, stderr = io.StringIO(), io.StringIO()
            with self.subTest(command=command), contextlib.redirect_stdout(
                stdout
            ), contextlib.redirect_stderr(stderr):
                code = aura.main(
                    [command, str(EXAMPLE), "--coop-card", str(COOP_EXAMPLE)]
                )
            self.assertEqual(code, 0)
            self.assertIn(expected, stdout.getvalue())
            self.assertEqual(stderr.getvalue(), "")

    def test_kingdom_cli_routes_aura_without_changing_plain_coop(self) -> None:
        environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        result = subprocess.run(
            [
                str(KINGDOM),
                "coop",
                "aura",
                "check",
                str(EXAMPLE),
                "--coop-card",
                str(COOP_EXAMPLE),
            ],
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AURA-STRUCTURE-OK", result.stdout)
        plain = subprocess.run(
            [str(KINGDOM), "coop", "digest", str(COOP_EXAMPLE)],
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(plain.returncode, 0, plain.stderr)
        self.assertEqual(
            plain.stdout.strip(),
            "abf4af408613243a5b7d5e3c49c297cb887102d766d0c82594b2b07bde177d11",
        )

    def test_bare_or_unbound_aura_cli_fails_closed(self) -> None:
        environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        for arguments in (
            [str(KINGDOM), "coop", "aura"],
            [str(KINGDOM), "coop", "aura", "check", str(EXAMPLE)],
        ):
            result = subprocess.run(
                arguments,
                cwd=ROOT,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            with self.subTest(arguments=arguments[3:]):
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertIn("usage: kingdom coop aura", result.stderr)

    def test_combined_coop_help_discovers_the_nested_aura_command(self) -> None:
        result = subprocess.run(
            [str(KINGDOM), "coop", "--help"],
            cwd=ROOT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Check one voluntary Co-op Leveling invitation", result.stdout)
        self.assertIn("Aura companion", result.stdout)
        self.assertIn("kingdom coop aura", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_invalid_cli_emits_no_validated_rendering(self) -> None:
        bad = aura_example()
        bad["aura"]["balance_exists"] = True
        path = self.write_json(bad, "bad.json")
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = aura.main(
                ["render", str(path), "--coop-card", str(COOP_EXAMPLE)]
            )
        self.assertEqual(code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("AURA-STRUCTURE-INVALID", stderr.getvalue())

    def test_runtime_has_no_network_subprocess_write_or_state_store_path(self) -> None:
        source = MODULE.read_text(encoding="utf-8")
        for forbidden in (
            "import socket",
            "import subprocess",
            "import urllib",
            "import requests",
            "urlopen(",
            "Popen(",
            "run(",
            "write_text(",
            "write_bytes(",
            "open(\"w",
            "open('w",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_protocol_readme_and_public_door_carry_the_aura_vow(self) -> None:
        protocol = COOP_PROTOCOL.read_text(encoding="utf-8")
        readme = README.read_text(encoding="utf-8")
        page = PUBLIC_PAGE.read_text(encoding="utf-8")
        for phrase in (
            "Aura Circuit",
            "non-scarce",
            "one Nen technique",
            "no balance",
            "fresh direct request",
        ):
            self.assertIn(phrase, protocol)
        for phrase in (
            "Maximum Flow, Zero Throne",
            "Anti-trigger",
            "Breach response",
            "Proof",
            "Exit",
            "Non-claims",
        ):
            self.assertIn(phrase, readme)
        for phrase in (
            "Maximum Aura. Zero throne.",
            "Aura is weather around a round",
            "One Nen focus",
            "Five virtue lenses",
            "Unlimited possibility; finite moves.",
        ):
            self.assertIn(phrase, page)
        self.assertIn(
            "repeat(auto-fit,minmax(105px,1fr))",
            page,
        )
        self.assertNotRegex(page, r"(?i)<(?:script|iframe)\b")
        self.assertNotRegex(page, r'''(?i)\bsrc\s*=\s*["']https?://''')


if __name__ == "__main__":
    unittest.main(verbosity=2)
