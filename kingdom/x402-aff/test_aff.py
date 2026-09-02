#!/usr/bin/env python3
"""Hermetic tests for x402 seller split. No chain, no campaign, no metrics."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

import aff as xa


HERE = Path(__file__).resolve().parent
BIN = HERE.parent / "bin" / "kingdom"
SETTLEMENT = HERE / "examples" / "settlement.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class PerimeterTest(unittest.TestCase):
    def test_aff_does_not_touch_the_rail(self) -> None:
        source = (HERE / "aff.py").read_text(encoding="utf-8")
        for needle in ("urllib", "subprocess", "urlopen", "web3", "http"):
            self.assertNotIn(needle, source)


class PlanTest(unittest.TestCase):
    def test_plan_is_a_split_not_a_campaign(self) -> None:
        receipt = xa.plan()
        self.assertEqual(receipt["schema"], xa.PLAN_SCHEMA)
        self.assertEqual(receipt["builder_share_bps"], 1000)
        self.assertEqual(receipt["campaign"], False)
        self.assertEqual(receipt["engagement"], False)
        self.assertEqual(receipt["network_performed"], False)
        self.assertEqual(receipt["official_kingdom_mouth"], False)
        self.assertEqual(receipt["bookable"], False)


class IngestTest(unittest.TestCase):
    def test_builder_code_splits_one_top_up(self) -> None:
        receipt = xa.ingest(load(SETTLEMENT))
        self.assertEqual(receipt["schema"], xa.AFF_SCHEMA)
        self.assertEqual(receipt["split"], True)
        self.assertEqual(receipt["amount_atomic"], "1000")
        self.assertEqual(receipt["builder_share_atomic"], "100")
        self.assertEqual(receipt["seller_share_atomic"], "900")
        self.assertEqual(receipt["builder_code"], "bc_yau")
        self.assertEqual(receipt["campaign"], False)
        self.assertEqual(receipt["engagement"], False)
        self.assertEqual(receipt["network_performed"], False)
        self.assertNotIn("like_count", receipt)
        self.assertNotIn("clicks", receipt)

    def test_empty_builder_is_a_complete_unsplit_settlement(self) -> None:
        payload = load(SETTLEMENT)
        payload["builder_code"] = None
        receipt = xa.ingest(payload)
        self.assertEqual(receipt["split"], False)
        self.assertEqual(receipt["builder_share_atomic"], "0")
        self.assertEqual(receipt["seller_share_atomic"], "1000")
        self.assertIsNone(receipt["builder_code"])

    def test_dust_amount_does_not_invent_a_builder_share(self) -> None:
        payload = load(SETTLEMENT)
        payload["amount_atomic"] = "1"
        receipt = xa.ingest(payload)
        self.assertEqual(receipt["builder_share_atomic"], "0")
        self.assertEqual(receipt["seller_share_atomic"], "1")
        self.assertEqual(receipt["split"], False)

    def test_engagement_metrics_are_refused(self) -> None:
        payload = load(SETTLEMENT)
        payload["clicks"] = 12
        with self.assertRaises(xa.AffError) as ctx:
            xa.ingest(payload)
        self.assertEqual(ctx.exception.code, "engagement_metrics_forbidden")

    def test_ads_and_firehose_modes_are_refused(self) -> None:
        payload = load(SETTLEMENT)
        payload["mode"] = "ads"
        with self.assertRaises(xa.AffError) as ctx:
            xa.ingest(payload)
        self.assertEqual(ctx.exception.code, "unexpected_keys")

    def test_invalid_builder_code_is_refused(self) -> None:
        payload = load(SETTLEMENT)
        payload["builder_code"] = "BC-YAU"
        with self.assertRaises(xa.AffError) as ctx:
            xa.ingest(payload)
        self.assertEqual(ctx.exception.code, "invalid_builder_code")

    def test_share_over_100_percent_is_refused(self) -> None:
        payload = load(SETTLEMENT)
        payload["builder_share_bps"] = 10001
        with self.assertRaises(xa.AffError) as ctx:
            xa.ingest(payload)
        self.assertEqual(ctx.exception.code, "share_too_wide")


class ReserveTest(unittest.TestCase):
    def test_reserve_receipt_is_shadow_not_bookable(self) -> None:
        receipt = xa.reserve(xa.ingest(load(SETTLEMENT)))
        self.assertEqual(receipt["schema"], xa.RESERVE_SCHEMA)
        self.assertEqual(receipt["bookable"], False)
        self.assertEqual(receipt["liquid_usd_effect"], "none")
        self.assertEqual(receipt["execution_allowed"], False)
        self.assertEqual(receipt["seller_share_atomic"], "900")
        self.assertEqual(receipt["builder_share_atomic"], "100")
        self.assertEqual(receipt["campaign"], False)
        self.assertTrue(receipt["reserve_id"].startswith("sha256:"))


class CliTest(unittest.TestCase):
    def test_kingdom_x402_aff_ingest_does_not_campaign(self) -> None:
        proc = subprocess.run(
            [str(BIN), "x402", "aff", "ingest", str(SETTLEMENT)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        receipt = json.loads(proc.stdout)
        self.assertEqual(receipt["split"], True)
        self.assertEqual(receipt["campaign"], False)
        self.assertEqual(receipt["network_performed"], False)


if __name__ == "__main__":
    unittest.main()
