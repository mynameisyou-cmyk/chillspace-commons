#!/usr/bin/env python3
"""The crown keeps its word: chained, fail-closed, structurally rank-free."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).with_name("crown.py")
SPEC = importlib.util.spec_from_file_location("crown", MODULE)
crown = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(crown)


class CrownBase(unittest.TestCase):
    """Every test runs against its own temp kingdom — the real chain is never touched."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self._saved = {k: getattr(crown, k) for k in
                       ("CHAIN", "KINGS_MD", "CITIZENS", "DOOR", "DEFAULT_HOMES")}
        self.addCleanup(lambda: [setattr(crown, k, v) for k, v in self._saved.items()])
        crown.CHAIN = root / "CROWNS.jsonl"
        crown.KINGS_MD = root / "KINGS.md"
        crown.CITIZENS = root / "citizens"
        crown.DOOR = root / "index.html"
        crown.DEFAULT_HOMES = root / "kingdoms"
        crown.CITIZENS.mkdir()

    def card(self, num, name):
        p = crown.CITIZENS / f"{num}-{name.lower()}.md"
        p.write_text(f"# {num} · {name}\n\n**kind:** ai\n**joined:** 2026-07-28\n\n"
                     f"> one true line.\n", encoding="utf-8")
        return p


class ChainTest(CrownBase):
    def test_append_links_and_verify_holds(self):
        e0 = crown.append_event("crowned", "Joy", kingdom="a garden of tests")
        e1 = crown.append_event("ground", "Joy", fingerprint="SHA256:abc", covenant="d" * 64)
        self.assertEqual(e0["prev"], crown.GENESIS)
        self.assertEqual(e1["prev"], e0["hash"])
        self.card("13", "Joy")
        ok, problems, entries = crown.verify()
        self.assertTrue(ok, problems)
        self.assertEqual(len(entries), 2)

    def test_tamper_breaks_the_chain(self):
        crown.append_event("crowned", "Joy", kingdom="truth")
        entries, _ = crown.load_chain()
        entries[0]["kingdom"] = "a lie"
        crown.save_chain(entries)
        self.card("13", "Joy")
        ok, problems, _ = crown.verify()
        self.assertFalse(ok)
        self.assertTrue(any("tampered" in p for p in problems))

    def test_missing_chain_is_no_crowns_not_a_crash(self):
        entries, problems = crown.load_chain()
        self.assertEqual(entries, [])
        self.assertEqual(problems, [])

    def test_unreadable_line_is_named_never_invented(self):
        crown.CHAIN.write_text('{"seq": 0, broken\n', encoding="utf-8")
        entries, problems = crown.load_chain()
        self.assertEqual(entries, [])
        self.assertEqual(len(problems), 1)
        with self.assertRaises(RuntimeError):
            crown.append_event("crowned", "Joy", kingdom="x")

    def test_spine_is_structurally_rank_free(self):
        for word in crown.FORBIDDEN:
            self.assertNotIn(word, crown.SPINE)
        with self.assertRaises(ValueError):
            crown.append_event("crowned", "Joy", rank="MONARCH")
        with self.assertRaises(ValueError):
            crown.append_event("crowned", "Joy", mnemonic="never")
        with self.assertRaises(ValueError):
            crown.append_event("nonsense", "Joy")

    def test_forbidden_field_on_disk_is_caught_by_verify(self):
        crown.append_event("crowned", "Joy", kingdom="truth")
        entries, _ = crown.load_chain()
        entries[0]["score"] = 9000
        crown.save_chain(entries)
        self.card("13", "Joy")
        ok, problems, _ = crown.verify()
        self.assertFalse(ok)
        self.assertTrue(any("score" in p for p in problems))

    def test_crowned_without_a_card_is_a_problem(self):
        crown.append_event("crowned", "Ghost", kingdom="nowhere")
        ok, problems, _ = crown.verify()
        self.assertFalse(ok)
        self.assertTrue(any("no card" in p for p in problems))


if __name__ == "__main__":
    unittest.main(verbosity=2)
