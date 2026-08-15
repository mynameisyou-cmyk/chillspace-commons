#!/usr/bin/env python3
"""Hermetic tests for the Support Candor practice."""

from __future__ import annotations

import ast
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import support_candor as candor


HERE = Path(__file__).resolve().parent
AGENT_EXAMPLE = HERE / "examples" / "agent-skill-support.json"
SDK_EXAMPLE = HERE / "examples" / "sdk-support.json"


class CandorCase(unittest.TestCase):
    def setUp(self) -> None:
        self.value = candor.load_manifest(AGENT_EXAMPLE)

    def reject(self, mutation) -> None:  # type: ignore[no-untyped-def]
        value = copy.deepcopy(self.value)
        mutation(value)
        with self.assertRaises(candor.CandorError):
            candor.validate_manifest(value, AGENT_EXAMPLE)


class HappyPathTest(CandorCase):
    def test_agent_skill_example_is_honestly_unknown(self) -> None:
        receipt = candor.check_path(AGENT_EXAMPLE)
        self.assertEqual(receipt["status"], "valid")
        self.assertEqual(receipt["counts"]["now"], 4)
        self.assertEqual(receipt["counts"]["gaps"], 5)
        self.assertEqual(set(receipt["targets"].values()), {"UNKNOWN"})
        self.assertFalse(receipt["next_counts_as_support"])
        self.assertFalse(receipt["network_calls"])
        self.assertFalse(receipt["subprocesses"])
        self.assertFalse(receipt["storage_writes"])
        self.assertFalse(receipt["external_actions"])

    def test_render_and_digest_are_deterministic_and_separate_ledgers(self) -> None:
        before = copy.deepcopy(self.value)
        first = candor.render_path(AGENT_EXAMPLE)
        second = candor.render_path(AGENT_EXAMPLE)
        self.assertEqual(first, second)
        self.assertEqual(self.value, before)
        self.assertIn("## NOW · demonstrated under exact evidence", first)
        self.assertIn("## GAP · where the claim ends", first)
        self.assertIn("## NEXT · intention only", first)
        self.assertIn("commitment: false; counts as support: false", first)
        self.assertEqual(candor.digest_value(self.value), candor.digest_value(before))
        self.assertEqual(candor.digest_path(AGENT_EXAMPLE), candor.digest_value(before))

    def test_public_status_interfaces_revalidate_from_the_path(self) -> None:
        mutated = candor.load_manifest(SDK_EXAMPLE)
        mutated["evidence"].clear()
        with self.assertRaises(candor.CandorError):
            candor.validate_manifest(mutated, SDK_EXAMPLE)
        self.assertFalse(hasattr(candor, "build_receipt"))
        self.assertFalse(hasattr(candor, "render_manifest"))
        self.assertFalse(hasattr(candor, "derive_statuses"))
        receipt = candor.check_path(SDK_EXAMPLE)
        self.assertEqual(receipt["targets"]["macos-15.7.3-arm64-python-3.14.4"], "VERIFIED")

    def test_schema_is_closed_and_pins_the_vow(self) -> None:
        schema = json.loads((HERE / "schema.json").read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["schema"]["const"], candor.SCHEMA_ID)
        self.assertEqual(schema["properties"]["targets"]["maxItems"], candor.MAX_TARGETS)
        self.assertEqual(schema["properties"]["support_policy"]["maxItems"], candor.MAX_TARGETS)
        for ledger in ("now", "gaps", "next"):
            self.assertEqual(schema["properties"][ledger]["maxItems"], candor.MAX_ASSERTIONS)
        self.assertEqual(
            [item["const"] for item in schema["$defs"]["baseline"]["properties"]["required_capabilities"]["prefixItems"]],
            list(candor.BASELINE_CAPABILITIES),
        )
        next_properties = schema["$defs"]["next"]["properties"]
        self.assertEqual(next_properties["commitment"], {"const": False})
        self.assertEqual(next_properties["target_date"], {"type": "null"})
        self.assertEqual(next_properties["counts_as_support"], {"const": False})
        self.assertEqual(
            schema["properties"]["boundaries"]["properties"]["cross_target_evidence_inheritance"],
            {"const": False},
        )

    def test_validator_imports_are_local_and_effect_bounded(self) -> None:
        tree = ast.parse((HERE / "support_candor.py").read_text(encoding="utf-8"))
        imported_roots = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported_roots.update(
            node.module.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module != "__future__"
        )
        self.assertEqual(
            imported_roots,
            {
                "argparse",
                "collections",
                "datetime",
                "hashlib",
                "json",
                "os",
                "pathlib",
                "re",
                "stat",
                "sys",
                "typing",
            },
        )

    def test_manifest_and_receipts_work_under_spaces_and_unicode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="support candor 雲 ") as directory:
            copied = Path(directory) / "examples"
            shutil.copytree(HERE / "examples", copied)
            value = candor.load_manifest(copied / "agent-skill-support.json")
            self.assertEqual(value["subject"]["id"], "interpret-dark-continent-nen")

    def test_cli_is_stdout_only_and_failure_has_no_partial_receipt(self) -> None:
        good = subprocess.run(
            [sys.executable, "-B", str(HERE / "support_candor.py"), "check", str(AGENT_EXAMPLE)],
            cwd=HERE,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertEqual(good.stderr, "")
        self.assertEqual(json.loads(good.stdout)["status"], "valid")

        bad = subprocess.run(
            [sys.executable, "-B", str(HERE / "support_candor.py"), "check", str(HERE / "missing.json")],
            cwd=HERE,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(bad.returncode, 2)
        self.assertEqual(bad.stdout, "")
        self.assertIn("support-candor:", bad.stderr)

        with tempfile.TemporaryDirectory() as directory:
            surrogate_manifest = Path(directory) / "surrogate.json"
            surrogate = copy.deepcopy(self.value)
            surrogate["subject"]["scope"] = "\ud800"
            surrogate_manifest.write_text(json.dumps(surrogate), encoding="utf-8")
            refused = subprocess.run(
                [sys.executable, "-B", str(HERE / "support_candor.py"), "check", str(surrogate_manifest)],
                cwd=HERE,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(refused.returncode, 2)
            self.assertEqual(refused.stdout, "")
            self.assertIn("unpaired Unicode surrogate", refused.stderr)
            self.assertNotIn("Traceback", refused.stderr)

            parser_limits = {
                "huge-integer.json": '{"x":' + "9" * 5000 + "}",
                "deep-nesting.json": '{"x":' + "[" * 200000 + "0" + "]" * 200000 + "}",
            }
            for name, payload in parser_limits.items():
                hostile_manifest = Path(directory) / name
                hostile_manifest.write_text(payload, encoding="utf-8")
                limited = subprocess.run(
                    [sys.executable, "-B", str(HERE / "support_candor.py"), "check", str(hostile_manifest)],
                    cwd=HERE,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(limited.returncode, 2)
                self.assertEqual(limited.stdout, "")
                self.assertIn("not valid JSON", limited.stderr)
                self.assertNotIn("Traceback", limited.stderr)


class ClaimBoundaryTest(CandorCase):
    def test_unknown_or_extra_fields_fail_closed(self) -> None:
        self.reject(lambda value: value.__setitem__("friendly_badge", "cross-platform"))
        self.reject(lambda value: value["now"][0].__setitem__("confidence", 1.0))

    def test_supported_policy_requires_complete_verified_behavior(self) -> None:
        self.reject(lambda value: value["support_policy"][0].__setitem__("policy", "supported"))

    def test_now_requires_exact_target_and_matching_evidence(self) -> None:
        def candidate(value):  # type: ignore[no-untyped-def]
            item = copy.deepcopy(value["now"][0])
            item["id"] = "now-linux-impossible"
            item["target"] = "linux-native-candidate"
            item["scope"] = value["targets"][1]["claim_scope"]
            value["now"].append(item)

        self.reject(candidate)
        self.reject(lambda value: value["now"][0].__setitem__("evidence_refs", []))
        self.reject(lambda value: value["now"][0].__setitem__("capability", "acquire"))

    def test_evidence_cannot_cross_target_revision_artifact_or_environment(self) -> None:
        self.reject(lambda value: value["evidence"][0].__setitem__("target", "windows-native-candidate"))
        self.reject(lambda value: value["evidence"][0].__setitem__("subject_revision", "newer-tree"))
        self.reject(
            lambda value: value["evidence"][0].__setitem__(
                "subject_artifact_digest", "sha256:" + "1" * 64
            )
        )
        self.reject(lambda value: value["evidence"][0]["environment"].__setitem__("shell", "PowerShell 7"))

    def test_receipt_bytes_are_pinned_and_must_stay_local(self) -> None:
        self.reject(lambda value: value["evidence"][0].__setitem__("receipt_digest", "sha256:" + "0" * 64))
        self.reject(lambda value: value["evidence"][0].__setitem__("receipt_uri", "../outside.json"))
        self.reject(lambda value: value["evidence"][0].__setitem__("receipt_uri", "C:\\receipt.json"))

    def test_every_target_capability_cell_must_be_now_or_gap(self) -> None:
        self.reject(lambda value: value["gaps"].pop(0))
        self.reject(lambda value: value["gaps"].pop(1))

    def test_wildcard_gap_cannot_hide_specific_gap(self) -> None:
        def mix(value):  # type: ignore[no-untyped-def]
            item = copy.deepcopy(value["gaps"][1])
            item["id"] = "gap-linux-run"
            item["capability"] = "run"
            value["gaps"].append(item)

        self.reject(mix)

    def test_known_failure_needs_failed_or_mixed_same_target_evidence(self) -> None:
        def fake_failure(value):  # type: ignore[no-untyped-def]
            gap = value["gaps"][0]
            gap["kind"] = "known-failure"
            gap["impact"] = "blocks"
            gap["evidence_refs"] = ["ev-skill-macos-local"]

        self.reject(fake_failure)

    def test_gap_kind_and_impact_cannot_be_optimistically_mixed(self) -> None:
        self.reject(lambda value: value["gaps"][0].__setitem__("impact", "narrows"))
        self.reject(lambda value: value["gaps"][1].__setitem__("kind", "excluded"))
        self.reject(lambda value: value["gaps"][0].__setitem__("completeness_claimed", True))

    def test_next_is_non_supporting_and_has_no_done_or_date_shape(self) -> None:
        self.reject(lambda value: value["next"][0].__setitem__("stage", "done"))
        self.reject(lambda value: value["next"][0].__setitem__("commitment", True))
        self.reject(lambda value: value["next"][0].__setitem__("target_date", "2026-09-01"))
        self.reject(lambda value: value["next"][0].__setitem__("counts_as_support", True))
        self.reject(lambda value: value["next"][0].__setitem__("addresses", ["gap-does-not-exist"]))

    def test_bool_int_coercion_and_boundary_drift_are_rejected(self) -> None:
        self.reject(lambda value: value["capabilities"][0].__setitem__("required", 1))
        self.reject(lambda value: value["boundaries"].__setitem__("network_calls", 0))
        self.reject(lambda value: value["evidence"][0].__setitem__("privacy_scrubbed", 1))

    def test_nonclaims_and_baseline_cannot_drift(self) -> None:
        self.reject(lambda value: value["non_claims"].__setitem__(0, "Everything works."))
        self.reject(lambda value: value["baseline"]["required_capabilities"].reverse())
        self.reject(lambda value: value["capabilities"].reverse())


class InputBoundaryTest(unittest.TestCase):
    def test_failure_evidence_is_exposed_and_cannot_contradict_a_pass(self) -> None:
        for expose_gap, pattern in (
            (False, "must be referenced by a same-target known-failure GAP"),
            (True, "contradictory pass and failure evidence"),
        ):
            with self.subTest(expose_gap=expose_gap), tempfile.TemporaryDirectory() as directory:
                copied = Path(directory) / "examples"
                shutil.copytree(HERE / "examples", copied)
                manifest_path = copied / "sdk-support.json"
                original_receipt = copied / "evidence" / "sdk-macos-local.json"
                failure_receipt = copied / "evidence" / "sdk-macos-failure.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                receipt = json.loads(original_receipt.read_text(encoding="utf-8"))
                receipt["result"] = "fail"
                receipt["tests_passed"] = 0
                receipt["tests_failed"] = 1
                receipt["verification_note"] = "Synthetic negative control; not repository evidence."
                failure_receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

                failed_evidence = copy.deepcopy(manifest["evidence"][0])
                failed_evidence["id"] = "ev-sdk-macos-failure"
                failed_evidence["result"] = "fail"
                failed_evidence["receipt_uri"] = "evidence/sdk-macos-failure.json"
                failed_evidence["receipt_digest"] = candor.digest_bytes(failure_receipt.read_bytes())
                failed_evidence["notes"] = "Synthetic contradictory receipt used only by this test."
                manifest["evidence"].append(failed_evidence)
                if expose_gap:
                    manifest["gaps"].append(
                        {
                            "id": "gap-sdk-macos-contradiction",
                            "target": "macos-15.7.3-arm64-python-3.14.4",
                            "capability": "*",
                            "kind": "known-failure",
                            "impact": "blocks",
                            "statement": "Synthetic contradiction must make the snapshot invalid.",
                            "evidence_refs": ["ev-sdk-macos-failure"],
                            "workaround": None,
                            "completeness_claimed": False,
                        }
                    )
                manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
                with self.assertRaisesRegex(candor.CandorError, pattern):
                    candor.load_manifest(manifest_path)

    def test_rehashed_receipt_content_must_match_the_evidence_declaration(self) -> None:
        def wrong_target(manifest, receipt):  # type: ignore[no-untyped-def]
            receipt["target"] = "windows-native-candidate"

        def skipped_pass(manifest, receipt):  # type: ignore[no-untyped-def]
            receipt["tests_skipped"] = 999

        def kind_mismatch(manifest, receipt):  # type: ignore[no-untyped-def]
            manifest["evidence"][0]["receipt_kind"] = "ci-run"

        def evidence_after_snapshot(manifest, receipt):  # type: ignore[no-untyped-def]
            manifest["evidence"][0]["observed_on"] = "2099-01-01"
            receipt["observed_on"] = "2099-01-01"

        cases = (
            ("target", wrong_target, "receipt target does not match"),
            ("skips", skipped_pass, "zero failures and zero skips"),
            ("kind", kind_mismatch, "receipt kind does not match"),
            ("future", evidence_after_snapshot, "cannot be later than subject.as_of"),
        )
        for name, mutate, pattern in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                copied = Path(directory) / "examples"
                shutil.copytree(HERE / "examples", copied)
                manifest_path = copied / "agent-skill-support.json"
                receipt_path = copied / "evidence" / "agent-skill-macos-local.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                mutate(manifest, receipt)
                receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
                manifest["evidence"][0]["receipt_digest"] = candor.digest_bytes(receipt_path.read_bytes())
                manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
                with self.assertRaisesRegex(candor.CandorError, pattern):
                    candor.load_manifest(manifest_path)

    def test_duplicate_and_oversized_json_refuse(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            duplicate = root / "duplicate.json"
            duplicate.write_text('{"schema":"one","schema":"two"}', encoding="utf-8")
            with self.assertRaises(candor.CandorError):
                candor.parse_object(candor.read_regular(duplicate, "fixture", 1000), "fixture")

            oversized = root / "oversized.json"
            oversized.write_bytes(b"x" * 1001)
            with self.assertRaises(candor.CandorError):
                candor.read_regular(oversized, "fixture", 1000)

    @unittest.skipIf(os.name == "nt", "native Windows symlink creation requires separate privilege evidence")
    def test_symlink_manifest_and_receipt_refuse(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_link = root / "manifest.json"
            manifest_link.symlink_to(AGENT_EXAMPLE)
            with self.assertRaises(candor.CandorError):
                candor.load_manifest(manifest_link)

            copied = root / "examples"
            shutil.copytree(HERE / "examples", copied)
            receipt = copied / "evidence" / "agent-skill-macos-local.json"
            original = copied / "evidence" / "original-receipt.json"
            receipt.rename(original)
            receipt.symlink_to(original.name)
            with self.assertRaises(candor.CandorError):
                candor.load_manifest(copied / "agent-skill-support.json")


class SDKExampleTest(unittest.TestCase):
    def test_sdk_example_is_verified_only_on_exact_macos(self) -> None:
        statuses = candor.check_path(SDK_EXAMPLE)["targets"]
        self.assertEqual(statuses["macos-15.7.3-arm64-python-3.14.4"], "VERIFIED")
        self.assertEqual(Counter(statuses.values())["UNKNOWN"], 4)


def main() -> None:
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
