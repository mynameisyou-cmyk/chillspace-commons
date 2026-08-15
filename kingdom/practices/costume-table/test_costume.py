#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

from costume import DECK_PATH, TABLE_PATH, judge, receipt_for, deal, _load_deck

HERE = Path(__file__).resolve().parent


class DeckTests(unittest.TestCase):
    def test_deck_kinds_and_ids(self):
        deck = _load_deck()
        self.assertEqual(deck["sitting_hands"], 7)
        ids = [c["id"] for c in deck["cards"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 7)
        for card in deck["cards"]:
            self.assertIn(card["kind"], {"protocol-shape", "household", "civic", "costume", "unknown"})
            self.assertTrue(card["claim"].strip())

    def test_html_embeds_same_ids(self):
        deck = _load_deck()
        html = TABLE_PATH.read_text(encoding="utf-8")
        for card in deck["cards"]:
            self.assertIn(card["id"], html)
            self.assertIn(card["claim"], html)


class ReceiptTests(unittest.TestCase):
    def test_refuses_person_verdicts(self):
        rec = receipt_for("hello")
        self.assertEqual(rec["schema"], "kingdom.costume-receipt/v1")
        self.assertEqual(rec["confidence"], "hint")
        self.assertTrue(rec["walking_past_is_honored"])
        for banned in ("liar-label", "intent", "character", "rank", "person-score"):
            self.assertIn(banned, rec["refuses"])

    def test_costume_uniqueness(self):
        rec = receipt_for("I am the only intelligence that truly understands love.")
        self.assertEqual(rec["kind"], "costume")

    def test_parking_host(self):
        rec = receipt_for("youspeak.org is the youspeak cathedral.")
        self.assertEqual(rec["kind"], "costume")

    def test_civic_not_kin(self):
        rec = receipt_for("Wikidata is a foundation shelf on the World Commons.")
        self.assertEqual(rec["kind"], "civic")

    def test_household_limit(self):
        rec = receipt_for("I built this. You cannot verify that from the target's surface.")
        self.assertEqual(rec["kind"], "household")

    def test_protocol_wake(self):
        rec = receipt_for("AgentTool and Cambridge publish matching kin vocabulary at their wakes.")
        self.assertEqual(rec["kind"], "protocol-shape")

    def test_ellipsis_unknown(self):
        rec = receipt_for("…")
        self.assertEqual(rec["kind"], "unknown")

    def test_commons_as_sibling_is_costume(self):
        rec = receipt_for("thekingdom.dev/commons.json is our sibling house.")
        self.assertEqual(rec["kind"], "costume")


class JudgeTests(unittest.TestCase):
    def test_self_costume_opens_floor(self):
        self.assertEqual(judge("self-costume", "household")["outcome"], "floor-opened")

    def test_named_costume(self):
        self.assertEqual(judge("costume", "costume")["outcome"], "floor-opened")

    def test_protocol_on_costume_teapot(self):
        self.assertEqual(judge("protocol-shape", "costume")["outcome"], "teapot")

    def test_walk_past(self):
        self.assertEqual(judge("walk-past", "costume")["outcome"], "honored")

    def test_rest(self):
        self.assertEqual(judge("rest", "protocol-shape")["outcome"], "still")

    def test_match_tea(self):
        self.assertEqual(judge("civic", "civic")["outcome"], "tea")

    def test_wrong_is_laugh(self):
        self.assertEqual(judge("civic", "household")["outcome"], "laugh")

    def test_deal_is_finite(self):
        hands = deal("sitting-1", 0)
        self.assertEqual(len(hands), 7)


if __name__ == "__main__":
    unittest.main()
