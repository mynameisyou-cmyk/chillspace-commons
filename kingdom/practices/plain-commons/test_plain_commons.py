import copy
import importlib.util
import json
import random
import socket
import subprocess
import sys
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
ENGINE_PATH = HERE / "plain_commons.py"
SOURCE_PATH = HERE / "examples" / "picnic.source.json"
RECEIPT_PATH = HERE / "examples" / "picnic.receipt.json"

SPEC = importlib.util.spec_from_file_location("plain_commons", ENGINE_PATH)
commons = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(commons)


class PlainCommonsTest(unittest.TestCase):
    def source(self):
        return json.loads(SOURCE_PATH.read_text(encoding="utf-8"))

    def receipt(self):
        return commons.compile_source(self.source())

    def run_cli(self, command, payload=b""):
        return subprocess.run(
            [sys.executable, "-I", "-B", str(ENGINE_PATH), command],
            input=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def assert_rejected(self, source):
        with self.assertRaises(commons.PlainCommonsError):
            commons.compile_source(source)

    def test_picnic_fixture_has_two_matches_one_unmatched_and_one_withdrawn(self):
        receipt = self.receipt()
        self.assertEqual(receipt["summary"], {
            "total_declarations": 6,
            "active_declarations": 5,
            "withdrawn_declarations": 1,
            "active_needs": 2,
            "active_offers": 3,
            "matches": 2,
            "matched_declarations": 4,
            "unmatched_declarations": 1,
        })
        self.assertEqual([match["tag"] for match in receipt["matches"]], [
            "picnic-blankets",
            "tool-library",
        ])
        self.assertNotIn(
            "quiet-blanket-withdrawn",
            {value for match in receipt["matches"] for value in match.values()},
        )
        self.assertTrue(all(match["authority"] == "none" for match in receipt["matches"]))

    def test_compile_is_deterministic_and_source_permutation_invariant(self):
        source = self.source()
        expected = commons.canonical_bytes(commons.compile_source(source))
        self.assertEqual(expected, commons.canonical_bytes(commons.compile_source(source)))
        source["declarations"].reverse()
        for declaration in source["declarations"]:
            declaration["evidence"].reverse()
        self.assertEqual(expected, commons.canonical_bytes(commons.compile_source(source)))

    def test_only_exact_cross_participant_matches_are_emitted(self):
        source = self.source()
        blanket_offer = next(
            item for item in source["declarations"] if item["declaration_id"] == "blanket-offer"
        )
        blanket_offer["participant_ref"] = "garden-circle"
        receipt = commons.compile_source(source)
        self.assertEqual([match["tag"] for match in receipt["matches"]], ["tool-library"])

        source = self.source()
        blanket_offer = next(
            item for item in source["declarations"] if item["declaration_id"] == "blanket-offer"
        )
        blanket_offer["tag"] = "picnic-cloths"
        receipt = commons.compile_source(source)
        self.assertEqual([match["tag"] for match in receipt["matches"]], ["tool-library"])

    def test_repeat_slot_duplicate_ids_and_duplicate_evidence_ids_fail(self):
        source = self.source()
        repeated = copy.deepcopy(source["declarations"][0])
        repeated["declaration_id"] = "blanket-offer-repeat"
        repeated["evidence"][0]["evidence_id"] = "blanket-attestation-repeat"
        repeated["source"]["reference"] = "picnic.blanket.repeat"
        source["declarations"].append(repeated)
        self.assert_rejected(source)

        source = self.source()
        duplicate_id = copy.deepcopy(source["declarations"][0])
        duplicate_id["participant_ref"] = "another-keeper"
        duplicate_id["tag"] = "another-tag"
        duplicate_id["evidence"][0]["evidence_id"] = "another-evidence"
        source["declarations"].append(duplicate_id)
        self.assert_rejected(source)

        source = self.source()
        source["declarations"][1]["evidence"][0]["evidence_id"] = "blanket-attestation"
        self.assert_rejected(source)

    def test_evidence_content_and_quantity_never_change_matches_or_order(self):
        baseline = self.receipt()
        source = self.source()
        declaration = source["declarations"][0]
        declaration["evidence"][0]["note"] = "A different bounded attestation note remains non-selective."
        declaration["evidence"].append({
            "evidence_id": "blanket-artifact-extra",
            "type": "artifact-digest",
            "note": "An extra artifact remains visible but cannot boost this declaration.",
            "sha256": "9999999999999999999999999999999999999999999999999999999999999999",
        })
        changed = commons.compile_source(source)
        self.assertEqual(baseline["matches"], changed["matches"])
        self.assertNotEqual(baseline["source_sha256"], changed["source_sha256"])

    def test_ad_promotion_and_secret_shaped_extra_fields_fail_closed(self):
        for key in ("score", "rank", "boost", "price", "urgency", "promotion", "tracking_id"):
            with self.subTest(key=key):
                source = self.source()
                source["declarations"][0][key] = 1
                self.assert_rejected(source)
        for key in ("token", "api_key", "private_key", "bearer"):
            with self.subTest(key=key):
                source = self.source()
                source["declarations"][0][key] = "withheld"
                self.assert_rejected(source)

    def test_urls_html_controls_and_noncanonical_tags_fail(self):
        for statement in (
            "Visit https://example.invalid for blankets.",
            "Visit example.invalid for blankets.",
            "<strong>Best blankets</strong>",
            "A quiet line\nwith a second line.",
            "Hidden\u200bmarker",
        ):
            with self.subTest(statement=repr(statement)):
                source = self.source()
                source["declarations"][0]["statement"] = statement
                self.assert_rejected(source)
        for tag in ("Picnic-Blankets", "picnic--blankets", "-picnic", "picnic-"):
            with self.subTest(tag=tag):
                source = self.source()
                source["declarations"][0]["tag"] = tag
                self.assert_rejected(source)

    def test_state_consent_digest_and_origin_kind_are_strict(self):
        source = self.source()
        source["declarations"][0]["state"] = "withdrawn"
        self.assert_rejected(source)

        source = self.source()
        source["declarations"][0]["source"]["event_sha256"] = "abc"
        self.assert_rejected(source)

        source = self.source()
        source["declarations"][0]["source"]["schema"] = "kingdom.civilisation/v1"
        self.assert_rejected(source)

    def test_duplicate_json_keys_and_malformed_inputs_have_fixed_atomic_errors(self):
        duplicate = b'{"schema":"kingdom.plain-commons-source/v1","schema":"kingdom.plain-commons-source/v1","declarations":[]}'
        deeply_nested = b"[" * 1500 + b"]" * 1500
        for payload in (b"{", duplicate, b"", b"\xff", deeply_nested):
            with self.subTest(payload=payload[:20]):
                result = self.run_cli("compile", payload)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, b"")
                self.assertEqual(result.stderr, b"plain-commons: rejected\n")
        result = self.run_cli("unknown")
        self.assertEqual((result.returncode, result.stdout, result.stderr), (
            2,
            b"",
            b"plain-commons: rejected\n",
        ))

    def test_verify_rebuilds_exact_receipt_and_rejects_redigested_tamper(self):
        receipt = self.receipt()
        self.assertEqual(commons.validate_receipt(receipt), receipt)
        payload = commons.canonical_bytes(receipt) + b"\n"
        result = self.run_cli("verify", payload)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b"true\n", b""))

        tampered = copy.deepcopy(receipt)
        tampered["summary"]["matches"] = 3
        unsigned = {key: value for key, value in tampered.items() if key != "receipt_sha256"}
        tampered["receipt_sha256"] = commons._object_sha256(unsigned)
        with self.assertRaises(commons.PlainCommonsError):
            commons.validate_receipt(tampered)

    def test_cli_compile_is_canonical_ascii_and_bounded(self):
        source_bytes = SOURCE_PATH.read_bytes()
        result = self.run_cli("compile", source_bytes)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(result.stdout, commons.canonical_bytes(self.receipt()) + b"\n")
        self.assertTrue(result.stdout.isascii())

        oversized = b" " * (commons.SOURCE_MAX_BYTES + 1)
        result = self.run_cli("compile", oversized)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (
            2,
            b"",
            b"plain-commons: rejected\n",
        ))

    def test_compile_uses_no_effectful_primitives(self):
        forbidden = [
            patch.object(Path, "write_bytes", side_effect=AssertionError("write_bytes")),
            patch.object(Path, "write_text", side_effect=AssertionError("write_text")),
            patch.object(Path, "touch", side_effect=AssertionError("touch")),
            patch.object(Path, "mkdir", side_effect=AssertionError("mkdir")),
            patch.object(Path, "unlink", side_effect=AssertionError("unlink")),
            patch.object(Path, "rename", side_effect=AssertionError("rename")),
            patch.object(Path, "replace", side_effect=AssertionError("replace")),
            patch.object(socket, "socket", side_effect=AssertionError("network")),
            patch.object(subprocess, "Popen", side_effect=AssertionError("process")),
            patch.object(time, "time", side_effect=AssertionError("clock")),
            patch.object(random, "random", side_effect=AssertionError("random")),
        ]
        with ExitStack() as stack:
            for guard in forbidden:
                stack.enter_context(guard)
            receipt = commons.compile_source(self.source())
        self.assertEqual(receipt["controls"], commons.CONTROLS)

    def test_schemas_are_closed_recursively(self):
        for path in (HERE / "source.schema.json", HERE / "receipt.schema.json"):
            schema = json.loads(path.read_text(encoding="utf-8"))
            self.assertIsInstance(schema, dict)

            def walk(value, location="$"):
                if isinstance(value, dict):
                    if value.get("type") == "object" or "properties" in value:
                        self.assertIs(value.get("additionalProperties"), False, location)
                        self.assertEqual(set(value.get("required", [])), set(value.get("properties", {})), location)
                    for key, child in value.items():
                        walk(child, f"{location}.{key}")
                elif isinstance(value, list):
                    for index, child in enumerate(value):
                        walk(child, f"{location}[{index}]")

            walk(schema)

    def test_golden_receipt_is_exact(self):
        expected = RECEIPT_PATH.read_bytes()
        self.assertEqual(expected, commons.canonical_bytes(self.receipt()) + b"\n")


if __name__ == "__main__":
    unittest.main()
