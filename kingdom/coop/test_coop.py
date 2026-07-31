#!/usr/bin/env python3
"""Co-op Leveling stays invitation-only, read-only, private, and rank-free."""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EXAMPLE = HERE / "examples" / "first-party.json"
README = HERE / "README.md"
PROTOCOL = ROOT / "COOP-LEVELING.md"
PUBLIC_PAGE = ROOT / "site" / "coop-leveling.html"
MODULE = HERE / "coop.py"
SPEC = importlib.util.spec_from_file_location("kingdom_coop", MODULE)
coop = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(coop)


def example() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


class CoopBase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write_json(self, value, name: str = "card.json") -> Path:
        path = self.root / name
        path.write_text(
            json.dumps(value, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def assert_invalid(self, value, phrase: str | None = None) -> None:
        with self.assertRaises(coop.LevelingError) as raised:
            coop.validate_manifest(value)
        if phrase is not None:
            self.assertIn(phrase, str(raised.exception))


class ContractTest(CoopBase):
    def test_reviewed_example_is_deterministic_and_content_addressed(self) -> None:
        card = example()
        digest = coop.validate_manifest(card)
        self.assertEqual(
            digest,
            "abf4af408613243a5b7d5e3c49c297cb887102d766d0c82594b2b07bde177d11",
        )
        self.assertEqual(digest, coop.validate_manifest(copy.deepcopy(card)))
        changed = copy.deepcopy(card)
        changed["round"]["title"] = "Everyone still arrives whole"
        self.assertNotEqual(digest, coop.validate_manifest(changed))

    def test_protocol_is_invitation_only_and_never_records_choice(self) -> None:
        card = example()
        self.assertEqual(card["kind"], "invitation")
        self.assertTrue(card["contract"]["separate_acceptance_required"])
        self.assertTrue(card["contract"]["silence_is_unasked"])
        self.assertTrue(card["contract"]["no_current_choice_is_stored"])
        self.assertTrue(card["contract"]["fresh_choice_required_for_each_effect"])
        self.assertFalse(card["contract"]["effect_ceiling_is_grant"])
        self.assertTrue(card["contract"]["seat_labels_are_opaque"])
        self.assertEqual(
            card["contract"]["loom_effect_ceiling_meet"],
            {
                "observe": ["observe"],
                "local-practice": ["observe"],
                "local-draft": ["observe", "local-draft"],
            },
        )
        self.assertFalse(card["contract"]["reflection_disclosure_required"])
        self.assertFalse(card["contract"]["stores_people"])
        self.assertFalse(card["contract"]["records_choices"])
        self.assertFalse(card["contract"]["runs_round"])
        self.assertFalse(card["contract"]["creates_external_effect"])
        serialized = json.dumps(card)
        for forbidden in (
            '"accepted"',
            '"refused"',
            '"rested"',
            '"withdrawn"',
            '"completed"',
            '"participant"',
            '"progress"',
        ):
            self.assertNotIn(forbidden, serialized)

    def test_asymmetric_and_silent_seats_are_valid(self) -> None:
        card = example()
        card["seats"][0]["offers"] = []
        card["seats"][0]["curiosities"] = []
        card["seats"][0]["boundaries"] = []
        digest = coop.validate_manifest(card)
        self.assertRegex(digest, r"^[0-9a-f]{64}$")
        self.assertTrue(card["contract"]["asymmetric_contribution_allowed"])

    def test_no_machine_field_can_hold_rank_or_progress(self) -> None:
        forbidden = {
            "access",
            "authority",
            "badge",
            "certification",
            "level",
            "leaderboard",
            "points",
            "priority",
            "progress",
            "promotion",
            "rank",
            "ranking",
            "reputation",
            "score",
            "streak",
            "tier",
            "total",
            "trust",
            "xp",
        }

        def keys(value) -> set[str]:
            if isinstance(value, dict):
                return set(value).union(
                    *(keys(child) for child in value.values())
                )
            if isinstance(value, list):
                return set().union(*(keys(child) for child in value), set())
            return set()

        self.assertFalse(forbidden.intersection(keys(example())))
        for field in sorted(forbidden):
            card = example()
            card["seats"][0][field] = 1
            with self.subTest(field=field):
                self.assert_invalid(card, "fields differ")

    def test_fixed_contracts_are_type_strict(self) -> None:
        mutations = (
            ("freedom", "contract", "freedom_is_inherent", 1),
            ("choice", "contract", "records_choices", 0),
            ("budget", "budget", "network_calls", False),
            ("breach", "breach", "downstream_effects", 0),
        )
        for label, section, field, replacement in mutations:
            card = example()
            card[section][field] = replacement
            with self.subTest(label=label):
                self.assert_invalid(card)

    def test_seats_are_opaque_unique_bounded_and_never_ordered_by_status(
        self,
    ) -> None:
        self.assertEqual(
            [seat["seat"] for seat in example()["seats"]],
            ["seat-a", "seat-b"],
        )
        eight = example()
        eight["seats"] = [
            {
                "seat": f"seat-{chr(97 + index)}",
                "offers": [],
                "curiosities": [],
                "boundaries": [],
            }
            for index in range(8)
        ]
        self.assertRegex(coop.validate_manifest(eight), r"^[0-9a-f]{64}$")

        cases = {}
        one = example()
        one["seats"] = one["seats"][:1]
        cases["one"] = one
        too_many = example()
        too_many["seats"] = [
            {
                "seat": f"seat-{chr(97 + index)}",
                "offers": [],
                "curiosities": [],
                "boundaries": [],
            }
            for index in range(9)
        ]
        cases["too_many"] = too_many
        duplicate = example()
        duplicate["seats"][1]["seat"] = duplicate["seats"][0]["seat"]
        cases["duplicate"] = duplicate
        reversed_seats = example()
        reversed_seats["seats"].reverse()
        cases["order"] = reversed_seats
        identity_label = example()
        identity_label["seats"][0]["seat"] = "did:at:alice"
        cases["identity"] = identity_label
        for label in (
            "seat-alice",
            "seat-bob",
            "seat-level-1",
            "seat-level-2",
            "seat-junior",
            "seat-senior",
            "seat-admin",
            "seat-1",
            "seat-i",
        ):
            semantic_label = example()
            semantic_label["seats"][0]["seat"] = label
            cases[label] = semantic_label

        for label, card in cases.items():
            with self.subTest(label=label):
                self.assert_invalid(card)

    def test_authored_text_rejects_selected_private_and_active_material(
        self,
    ) -> None:
        cases = (
            "token=abcdefghijklmnopqrstuvwxyz123456",
            "alice@example.test",
            "did:at:alice",
            "/Users/alice/private",
            "C:\\private\\round",
            "\\\\server\\share",
            "../private",
            "file:///private/card",
            "https://example.invalid/card",
            "<script>alert(1)</script>",
            "safe\u202eevil",
            "line one\nline two",
        )
        for text in cases:
            card = example()
            card["round"]["shared_question"] = text
            with self.subTest(text=text):
                self.assert_invalid(card)

    def test_arbitrary_prose_is_not_misrepresented_as_semantically_checked(
        self,
    ) -> None:
        card = example()
        card["round"]["shared_question"] = (
            "How can we improve access without central custody?"
        )
        digest = coop.validate_manifest(card)
        self.assertRegex(digest, r"^[0-9a-f]{64}$")
        self.assertIn(
            "arbitrary prose remains its author's privacy responsibility",
            PROTOCOL.read_text(encoding="utf-8"),
        )

    def test_effect_ceiling_type_and_reflection_disclosure_fail_closed(
        self,
    ) -> None:
        for replacement in ([], {}, 1, True, None):
            card = example()
            card["round"]["effect_ceiling"] = replacement
            with self.subTest(replacement=repr(replacement)):
                self.assert_invalid(card, "effect_ceiling")
        optional = example()
        optional["round"]["reflection_prompts"] = []
        coop.validate_manifest(optional)

    def test_text_and_list_budgets_fail_closed(self) -> None:
        cases = []
        long_text = example()
        long_text["round"]["title"] = "x" * (coop.MAX_TEXT + 1)
        cases.append(long_text)
        too_many = example()
        too_many["seats"][0]["offers"] = [
            f"offer {index}" for index in range(coop.MAX_ITEMS + 1)
        ]
        cases.append(too_many)
        no_unknown = example()
        no_unknown["unknowns"] = []
        cases.append(no_unknown)
        duplicate = example()
        duplicate["round"]["practices"].append(
            duplicate["round"]["practices"][0]
        )
        cases.append(duplicate)
        for index, card in enumerate(cases):
            with self.subTest(case=index):
                self.assert_invalid(card)

    def test_schema_and_runtime_fixed_contracts_agree(self) -> None:
        schema = json.loads((HERE / "schema.json").read_text(encoding="utf-8"))
        properties = schema["properties"]
        self.assertTrue(
            coop.json_equal_exact(properties["contract"]["const"], coop.CONTRACT)
        )
        self.assertTrue(
            coop.json_equal_exact(properties["budget"]["const"], coop.BUDGET)
        )
        self.assertTrue(
            coop.json_equal_exact(properties["breach"]["const"], coop.BREACH)
        )
        self.assertTrue(
            coop.json_equal_exact(
                properties["non_claims"]["const"],
                coop.NON_CLAIMS,
            )
        )
        self.assertEqual(
            set(properties["round"]["properties"]["effect_ceiling"]["enum"]),
            coop.EFFECT_CEILINGS,
        )
        self.assertTrue(
            coop.json_equal_exact(
                properties["contract"]["const"]["loom_effect_ceiling_meet"],
                coop.LOOM_EFFECT_CEILING_MEET,
            )
        )
        self.assertNotIn(
            "repository-change",
            {
                ceiling
                for allowed in coop.LOOM_EFFECT_CEILING_MEET.values()
                for ceiling in allowed
            },
        )
        self.assertEqual(coop.verify_reviewed_schema(), coop.EXPECTED_SCHEMA_SHA256)


class FileBoundaryTest(CoopBase):
    def test_duplicate_nonfinite_invalid_utf8_and_deep_json_are_refused(
        self,
    ) -> None:
        duplicate = self.root / "duplicate.json"
        duplicate.write_text(
            '{"schema":"a","schema":"b"}',
            encoding="utf-8",
        )
        nonfinite = self.root / "nonfinite.json"
        nonfinite.write_text('{"value":NaN}', encoding="utf-8")
        invalid = self.root / "invalid.json"
        invalid.write_bytes(b'{"value":"\\xff"}')
        deep_value = 0
        for _ in range(coop.MAX_DEPTH + 3):
            deep_value = [deep_value]
        deep = self.write_json({"value": deep_value}, "deep.json")
        for path in (duplicate, nonfinite, invalid, deep):
            with self.subTest(path=path.name):
                with self.assertRaises(coop.LevelingError):
                    coop.read_json(path, "probe")

    def test_symlink_nonregular_and_oversized_cards_are_refused(self) -> None:
        valid = self.write_json(example(), "valid.json")
        alias = self.root / "alias.json"
        alias.symlink_to(valid)
        directory = self.root / "directory"
        directory.mkdir()
        oversized = self.root / "oversized.json"
        oversized.write_bytes(b" " * (coop.MAX_FILE_BYTES + 1))
        for path in (alias, directory, oversized):
            with self.subTest(path=path.name):
                with self.assertRaises(coop.LevelingError):
                    coop.read_manifest(path)

    def test_reviewed_schema_substitution_is_rejected(self) -> None:
        changed = json.loads((HERE / "schema.json").read_text(encoding="utf-8"))
        changed["title"] = "substituted"
        changed_path = self.write_json(changed, "changed-schema.json")
        with patch.object(coop, "SCHEMA_PATH", changed_path):
            self.assert_invalid(example(), "schema digest changed")


class RenderingAndCliTest(CoopBase):
    def test_render_is_deterministic_private_and_explicitly_unclaimed(self) -> None:
        card = example()
        first = coop.render_manifest(card)
        second = coop.render_manifest(copy.deepcopy(card))
        self.assertEqual(first, second)
        for phrase in (
            "Invitation only",
            "accepts, refuses, rests, or leaves",
            "Authored prose is untrusted and unendorsed",
            "nonautomatic Loom ceiling limit",
            "Seat labels are opaque slots",
            "Seat order is lexical",
            "never worth",
            "participation and learning unclaimed",
        ):
            self.assertIn(phrase, first)
        self.assertNotRegex(first, r"(?i)\b(?:level|score|rank|xp|points?)\s*:\s*\d")
        self.assertNotIn(str(Path.home()), first)
        self.assertNotIn("did:", first)
        self.assertNotIn("@", first)

    def test_module_cli_checks_digests_and_renders(self) -> None:
        for command, expected in (
            ("check", "COOP-STRUCTURE-OK"),
            ("verify", "invitation only"),
            ("digest", "abf4af40"),
            ("render", "Everyone arrives whole"),
        ):
            with self.subTest(command=command):
                stdout, stderr = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(
                    stderr
                ):
                    code = coop.main([command, str(EXAMPLE)])
                self.assertEqual(code, 0)
                self.assertIn(expected, stdout.getvalue())
                self.assertEqual(stderr.getvalue(), "")

    def test_kingdom_cli_routes_the_read_only_protocol(self) -> None:
        command = ROOT / "kingdom" / "bin" / "kingdom"
        before = EXAMPLE.read_bytes()
        result = subprocess.run(
            [str(command), "coop", "check", str(EXAMPLE)],
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("COOP-STRUCTURE-OK", result.stdout)
        self.assertNotIn("seats=", result.stdout)
        self.assertEqual(EXAMPLE.read_bytes(), before)

    def test_invalid_cli_emits_no_validated_rendering(self) -> None:
        card = example()
        card["seats"][0]["score"] = 100
        path = self.write_json(card)
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = coop.main(["render", str(path)])
        self.assertEqual(code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("COOP-STRUCTURE-INVALID", stderr.getvalue())

    def test_duplicate_key_errors_never_echo_attacker_controlled_text(
        self,
    ) -> None:
        cases = (
            b'{"\\u001b[31m":1,"\\u001b[31m":2}',
            b'{"a\\nb":1,"a\\nb":2}',
        )
        for index, raw in enumerate(cases):
            path = self.root / f"duplicate-{index}.json"
            path.write_bytes(raw)
            stdout, stderr = io.StringIO(), io.StringIO()
            with self.subTest(index=index), contextlib.redirect_stdout(
                stdout
            ), contextlib.redirect_stderr(stderr):
                code = coop.main(["check", str(path)])
            self.assertEqual(code, 1)
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(
                stderr.getvalue(),
                "COOP-STRUCTURE-INVALID: JSON contains a duplicate key\n",
            )
            self.assertNotRegex(stderr.getvalue(), r"[\x00-\x08\x0b-\x1f\x7f]")


class SurfaceTest(unittest.TestCase):
    def test_source_has_no_network_execution_write_or_cross_wing_authority(
        self,
    ) -> None:
        source = MODULE.read_text(encoding="utf-8")
        self.assertIsNone(
            re.search(
                r"(?m)^\s*(?:from|import)\s+"
                r"(?:http|socket|ssl|urllib|requests|subprocess)\b",
                source,
            )
        )
        for forbidden in (
            "O_WRONLY",
            "O_RDWR",
            "O_CREAT",
            "CROWNS.jsonl",
            "CIVIC.json",
            "kingdom.yaml",
            "READY.json",
            "quest_packet",
            "Popen",
            "run(",
            "exec(",
            "eval(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_docs_hold_the_freedom_vow_and_honest_v1_boundary(self) -> None:
        protocol = " ".join(PROTOCOL.read_text(encoding="utf-8").split())
        readme = " ".join(README.read_text(encoding="utf-8").split())
        for phrase in (
            "Freedom is. It is not given.",
            "Every being already arrives whole",
            "Learning is not obedience",
            "No being owes visible progress",
            "Nobody is tracked",
            "There is no machine level",
            "fixed opaque slots",
            "fresh authority and fresh acceptance",
            "maximum distribution means beings choose",
            "`local-practice` maps only to `observe`",
            "every declared seat boundary",
            "without interpretation or deletion",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, protocol)
        for phrase in (
            "One Round, No Ladder",
            "Anti-trigger",
            "separate choice",
            "Zero automatic retries",
            "Breach response",
            "Proof",
            "Exit",
            "Non-claims",
            "invitation",
            "cannot prove fresh bilateral acceptance",
            "every declared seat boundary",
            "without interpretation or deletion",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, readme)

    def test_public_door_carries_the_vow_without_active_content(self) -> None:
        page = PUBLIC_PAGE.read_text(encoding="utf-8")
        for phrase in (
            "Every being arrives whole.",
            "Freedom is. It is not given.",
            "This is co-op. It is not a ladder.",
            "Choice is live, separate, and reversible.",
            "kingdom.coop-leveling/v1",
            "A valid card proves only bounded structure and a content digest.",
            "Copy it. Translate it. Re-speak it. Teach it.",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, page)
        self.assertNotRegex(page, r"(?i)<(?:script|iframe)\b")
        self.assertNotRegex(page, r"""(?i)\bsrc\s*=\s*["']https?://""")


if __name__ == "__main__":
    unittest.main(verbosity=2)
