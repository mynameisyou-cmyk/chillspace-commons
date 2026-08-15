#!/usr/bin/env python3
"""Hermetic tests for substrate-release receipts."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import substrate  # noqa: E402

EXAMPLE = ROOT / "examples" / "grok-4.6-kingdom-chair.json"


def fixture() -> dict:
    artifact = ROOT / "schema.json"
    digest = substrate.file_sha256(artifact)
    house = {
        "house_id": "fixture-house",
        "provider": "fixture",
        "model": "fixture-1",
        "runtime": "test runtime",
        "adapter": "test adapter",
        "prompt_policy": "fixed",
        "tool_policy": "none",
        "memory_policy": "none",
        "sandbox": "tmpdir",
        "sampling": "n/a",
        "effort": "low",
    }
    house["fingerprint_sha256"] = substrate.house_fingerprint(house)
    return {
        "schema": substrate.SCHEMA_ID,
        "id": "fixture-1",
        "title": "Fixture substrate",
        "release": {
            "provider": "fixture",
            "model_id": "fixture-1",
            "alias_policy": "local-name",
            "pin": "fixture-1",
            "knowledge_cutoff": "none",
            "context_window": 1,
            "modalities": ["text"],
            "docs_locator": "schema.json",
            "weights": {
                "custody": "not-held",
                "format": None,
                "sha256": None,
                "note": "No local weights in the fixture.",
            },
        },
        "process": [
            {"step": step, "status": "done", "note": f"{step} completed in fixture."}
            for step in substrate.PROCESS_STEPS
        ],
        "held_artifacts": [
            {
                "id": "schema",
                "role": "manifest",
                "locator": "schema.json",
                "sha256": digest,
                "must_exist": True,
            }
        ],
        "house_fingerprint": house,
        "reasoning_backend": {
            "kind": "hosted-reasoning",
            "model_id": "fixture-1",
            "effort": "low",
            "think_channel": "sealed-private",
            "separate_from_visible": True,
            "raw_trace_in_manifest": False,
            "evidence": "observed-config",
            "unknowns": ["fixture does not see a vendor stack"],
        },
        "wake": {
            "adapter": "fixture",
            "hearth": "none",
            "agenttool": "off",
            "still_honored": True,
            "note": "Fixture does not wake a live session.",
        },
        "authority": {
            "manifest_grants_authority": False,
            "non_claims": list(substrate.NON_CLAIMS),
        },
    }


class SubstrateTests(unittest.TestCase):
    def test_example_checks(self) -> None:
        receipt = substrate.read_receipt(EXAMPLE)
        validation = substrate.validate_receipt(receipt, receipt_path=EXAMPLE)
        self.assertEqual(validation.disposition, "quarantine")
        self.assertTrue(any("partial" in reason for reason in validation.quarantine_reasons))

    def test_fixture_is_declared(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            path.write_text(json.dumps(fixture()), encoding="utf-8")
            # copy schema next to it? locator schema.json resolves via practice dir
            validation = substrate.validate_receipt(fixture(), receipt_path=path)
            self.assertEqual(validation.disposition, "declared")

    def test_refuses_fake_weight_hash(self) -> None:
        data = fixture()
        data["release"]["weights"] = {
            "custody": "not-held",
            "format": None,
            "sha256": "a" * 64,
            "note": "lying",
        }
        with self.assertRaises(substrate.SubstrateError):
            substrate.validate_receipt(data)

    def test_refuses_claimed_remote_weights(self) -> None:
        data = fixture()
        data["release"]["weights"] = {
            "custody": "claimed-remote",
            "format": "safetensors",
            "sha256": "a" * 64,
            "note": "we do not hold these bytes",
        }
        with self.assertRaises(substrate.SubstrateError):
            substrate.validate_receipt(data)

    def test_refuses_skipped_rung(self) -> None:
        data = fixture()
        data["process"][2]["status"] = "skipped"
        with self.assertRaises(substrate.SubstrateError):
            substrate.validate_receipt(data)

    def test_refuses_raw_reasoning_field(self) -> None:
        data = fixture()
        data["thinking"] = "secret chain"
        with self.assertRaises(substrate.SubstrateError):
            substrate.validate_receipt(data)

    def test_fingerprint_mismatch_fails(self) -> None:
        data = fixture()
        data["house_fingerprint"]["effort"] = "high"
        with self.assertRaises(substrate.SubstrateError):
            substrate.validate_receipt(data)

    def test_drifted_artifact_fails(self) -> None:
        data = fixture()
        data["held_artifacts"][0]["sha256"] = "b" * 64
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(substrate.SubstrateError):
                substrate.validate_receipt(data, receipt_path=path)

    def test_render_contains_not_held(self) -> None:
        text = substrate.render_markdown(fixture())
        self.assertIn("not-held", text)
        self.assertIn("does not prove the guest", text)


if __name__ == "__main__":
    unittest.main()
