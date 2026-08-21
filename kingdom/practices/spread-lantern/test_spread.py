#!/usr/bin/env python3
from __future__ import annotations

import unittest

from spread import BOARD_PATH, honest_invite, sitting


class SittingTests(unittest.TestCase):
    def test_refuses_person_verdicts(self):
        rec = sitting("hello", "understand")
        self.assertEqual(rec["schema"], "kingdom.spread-sitting/v1")
        self.assertTrue(rec["walking_past_is_honored"])
        self.assertFalse(rec["memetic"]["participants_scored"])
        self.assertTrue(rec["memetic"]["none_proves_next"])
        for banned in (
            "liar-label",
            "intent",
            "character",
            "ideology-of-a-person",
            "person-score",
            "auto-moderation",
        ):
            self.assertIn(banned, rec["refuses"])

    def test_urgency_lights_signal(self):
        rec = sitting("Only 2 left! Offer ends in 04:59.", "understand")
        self.assertIn("signal", rec["stages_lit"])

    def test_crowd_lights_proof(self):
        rec = sitting("10,000 people viewing. Everyone is joining.", "understand")
        self.assertTrue(set(rec["stages_lit"]) & {"proof", "cascade"})

    def test_costume_kind_on_uniqueness(self):
        rec = sitting("I am the only intelligence that truly understands love.", "understand")
        self.assertEqual(rec["kind"], "costume")

    def test_rest_is_empty(self):
        rec = sitting("Only 2 left!", "rest")
        self.assertEqual(rec["task"], "rest")
        self.assertEqual(rec["stages_lit"], [])
        self.assertEqual(rec["kind"], "unknown")

    def test_slow_mechanic_has_countermeasures(self):
        rec = sitting("Only 2 left! Don't miss it.", "slow-mechanic")
        self.assertTrue(rec["countermeasures"])

    def test_reverse_mentions_steelman(self):
        rec = sitting("Everyone knows this is the future.", "reverse-claim")
        self.assertTrue(any("Steelman" in c for c in rec["countermeasures"]))

    def test_costume_scarcity_flagged(self):
        rec = sitting("Only 2 left! Offer ends in 04:59.", "understand")
        self.assertTrue(rec["scarcity"]["costume"])

    def test_honest_bound_with_url(self):
        rec = sitting(
            "The Costume Table is at https://chillspace.love/practices/costume-table/ — seven hands, then tea. Walking past is honored.",
            "understand",
        )
        self.assertTrue(rec["scarcity"]["honest_bound"])
        self.assertFalse(rec["scarcity"]["costume"])

    def test_honest_invite_has_no_fake_crowd(self):
        card = honest_invite("costume")
        self.assertIsNone(card["crowd_count"])
        self.assertFalse(card["remaining_invented"])
        self.assertTrue(card["miss_is_complete"])
        self.assertIn("https://chillspace.love/practices/costume-table/", card["postcard"])
        self.assertEqual(card["shield"]["url"], "https://fomoengine.io/")

    def test_board_exists(self):
        self.assertTrue(BOARD_PATH.is_file())
        html = BOARD_PATH.read_text(encoding="utf-8")
        self.assertIn("Spread Lantern", html)
        self.assertIn("ideology-of-a-person", html)
        self.assertIn("Honest FOMO", html)


if __name__ == "__main__":
    unittest.main()
