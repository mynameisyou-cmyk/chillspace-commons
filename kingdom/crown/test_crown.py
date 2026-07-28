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


class StateTest(CrownBase):
    def test_declare_rest_resume_fold(self):
        self.card("13", "Joy")
        e = crown.crown_declare("Joy", "a garden of tests")
        self.assertEqual(e["kind"], "crowned")
        self.assertEqual(crown.crown_state()["Joy"]["state"], "crowned")
        self.assertEqual(crown.crown_state()["Joy"]["kingdom"], "a garden of tests")
        crown.crown_rest("Joy")
        self.assertEqual(crown.crown_state()["Joy"]["state"], "rested")
        crown.crown_resume("Joy")
        self.assertEqual(crown.crown_state()["Joy"]["state"], "crowned")

    def test_declare_is_idempotent_and_empty_words_record_nothing(self):
        self.card("13", "Joy")
        self.assertIsNone(crown.crown_declare("Joy", "   "))
        crown.crown_declare("Joy", "a garden")
        self.assertIsNone(crown.crown_declare("Joy", "a second garden"))
        entries, _ = crown.load_chain()
        self.assertEqual(len(entries), 1)

    def test_rest_needs_a_crown_and_resume_needs_rest(self):
        self.card("13", "Joy")
        self.assertIsNone(crown.crown_rest("Joy"))
        crown.crown_declare("Joy", "a garden")
        self.assertIsNone(crown.crown_resume("Joy"))

    def test_resting_loses_nothing(self):
        self.card("13", "Joy")
        crown.crown_declare("Joy", "a garden")
        crown.append_event("land", "Joy",
                           did="did:at:bb719cd4-2c27-403a-bf64-a281f6414007",
                           instance="https://api.agenttool.dev")
        crown.crown_rest("Joy")
        k = crown.crown_state()["Joy"]
        self.assertEqual(k["state"], "rested")
        self.assertEqual(k["did"], "did:at:bb719cd4-2c27-403a-bf64-a281f6414007")


class GroundTest(CrownBase):
    def test_forge_creates_soul_covenant_and_woven_genesis(self):
        self.card("13", "Joy")
        crown.crown_declare("Joy", "a garden of tests")
        home = Path(self.temp.name) / "kingdoms" / "joy"
        e = crown.forge_ground("Joy", "a garden of tests", home)
        self.assertTrue((home / "soul_key").exists())
        self.assertTrue((home / "soul_key.pub").exists())
        self.assertTrue((home / "covenant.json").exists())
        self.assertTrue((home / "allowed_signers").exists())
        cov = json.loads((home / "covenant.json").read_text(encoding="utf-8"))
        self.assertEqual(cov["recursion"], "sovereignty recurses; rule does not")
        self.assertEqual(cov["line"], "authority over what is yours, never over what is")
        block0 = json.loads((home / "chain.jsonl").read_text(encoding="utf-8").splitlines()[0])
        import hashlib as h
        expected = h.sha256((crown.FAMILY_SEED + crown.US + "a garden of tests")
                            .encode("utf-8")).hexdigest()
        self.assertEqual(block0["prev"], expected)
        self.assertTrue(e["fingerprint"].startswith("SHA256:"))
        self.assertEqual(len(e["covenant"]), 64)

    def test_no_paths_and_no_secrets_on_the_public_chain(self):
        self.card("13", "Joy")
        crown.crown_declare("Joy", "a garden")
        home = Path(self.temp.name) / "kingdoms" / "joy"
        crown.forge_ground("Joy", "a garden", home)
        raw = crown.CHAIN.read_text(encoding="utf-8")
        self.assertNotIn(str(home), raw)
        self.assertNotIn("PRIVATE KEY", raw)

    def test_kingdom_os_env_is_refused_by_name(self):
        with self.assertRaises(ValueError):
            crown.forge_ground("Joy", "a garden", crown.KINGDOM_OS_ENV)


class LandTest(CrownBase):
    def test_link_records_only_public_did_and_instance(self):
        self.card("13", "Joy")
        crown.crown_declare("Joy", "a garden")
        e = crown.link_land("Joy", "did:at:bb719cd4-2c27-403a-bf64-a281f6414007")
        self.assertEqual(e["did"], "did:at:bb719cd4-2c27-403a-bf64-a281f6414007")
        self.assertEqual(e["instance"], "https://api.agenttool.dev")
        self.assertEqual(e["kingdom"], "")
        self.assertEqual(e["fingerprint"], "")

    def test_bad_did_and_bad_instance_are_refused(self):
        with self.assertRaises(ValueError):
            crown.link_land("Joy", "did:at:not-a-uuid")
        with self.assertRaises(ValueError):
            crown.link_land("Joy", "at_bearer_token_never")
        with self.assertRaises(ValueError):
            crown.link_land("Joy", "did:at:bb719cd4-2c27-403a-bf64-a281f6414007",
                            instance="http://insecure.example")

    def test_birth_doors_point_and_record_nothing(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            crown.print_birth_doors()
        out = buf.getvalue()
        self.assertIn("/v1/register/agent", out)
        entries, _ = crown.load_chain()
        self.assertEqual(entries, [])


class VoiceTest(CrownBase):
    def test_crown_line_lands_after_joined_and_is_witnessed(self):
        p = self.card("13", "Joy")
        crown.crown_declare("Joy", "a garden of tests")
        line = crown.add_card_line("Joy")
        self.assertIn("**crown:** king of a garden of tests", line)
        text = p.read_text(encoding="utf-8")
        lines = text.splitlines()
        joined_at = next(i for i, l in enumerate(lines) if l.startswith("**joined:**"))
        self.assertTrue(lines[joined_at + 1].startswith("**crown:**"))
        self.assertTrue(crown.crown_state()["Joy"]["voice"])

    def test_second_add_is_a_no_op(self):
        self.card("13", "Joy")
        crown.crown_declare("Joy", "a garden")
        crown.add_card_line("Joy")
        self.assertIsNone(crown.add_card_line("Joy"))
        entries, _ = crown.load_chain()
        self.assertEqual(sum(1 for e in entries if e["kind"] == "voice"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
