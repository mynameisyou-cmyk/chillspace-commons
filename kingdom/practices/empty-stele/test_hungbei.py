"""空碑 tests — the vow must be enforced, not admired.

stdlib-only (unittest), so the keeper can run this file directly:
    python3 kingdom/practices/empty-stele/test_hungbei.py
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import hungbei  # noqa: E402


class SteleCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(os.environ, {"HUNGBEI_HOME": str(Path(self._tmp.name) / "book")})
        self._env.start()

    def tearDown(self):
        self._env.stop()
        self._tmp.cleanup()

    def cast(self, **kw):
        args = dict(name="test-key", not_a=["not in any repo"],
                    points_to="env:TEST_KEY", key_state="unknown", note="")
        args.update(kw)
        return hungbei.cmd_cast(**args)


class TestCast(SteleCase):
    def test_happy_cast_appends_chained_entry_and_renders(self):
        entry = self.cast(name="codeberg-token", not_a=["not a password", "not in git history"],
                          points_to="keychain:svc=codeberg.org", key_state="rotated")
        book = Path(hungbei.home()) / "STELES.jsonl"
        lines = book.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["hash"], entry["hash"])
        self.assertIsNone(entry["prev"])
        rendered = (Path(hungbei.home()) / "STELES.md").read_text(encoding="utf-8")
        self.assertIn("codeberg-token", rendered)
        self.assertIn("佢唔係", rendered)

    def test_chain_links_prev_hash(self):
        first = self.cast(name="a")
        second = self.cast(name="b")
        self.assertEqual(second["prev"], first["hash"])

    def test_at_least_one_negation_required(self):
        with self.assertRaises(SystemExit):
            self.cast(not_a=["   "])

    def test_bad_pointer_grammar_refused(self):
        for bad in ("keychain", "vault:x", "env:", ""):
            with self.assertRaises(SystemExit):
                self.cast(points_to=bad)

    def test_none_yet_pointer_allowed(self):
        entry = self.cast(points_to="none-yet")
        self.assertEqual(entry["points_to"], "none-yet")

    def test_key_state_outside_honest_vocabulary_refused_via_api(self):
        """argparse choices guard the CLI; the API path must refuse too."""
        with self.assertRaises(SystemExit):
            self.cast(key_state="leaked")


class TestVowOne(SteleCase):
    """誓約一 · 碑上永不刻真身 — every secret-shaped field is refused, in any slot."""

    # Fixtures are assembled at RUNTIME so no complete credential shape ever
    # appears in committed text — 影仔's doorman (and GitHub push protection)
    # scan the text; hungbei's vow scans the assembled string. Same vow, two
    # doors, no wolf-crying. The AWS one is AWS's own documentation example.
    SECRET_SHAPES = {
        "aws-access-key": "AKIA" + "IOSFODNN7EXAMPLE",
        "github-token": "ghp_" + "abcdefghijklmnopqrstuvwxyz012345",
        "private-key-block": "-----BEGIN OPENSSH " + "PRIVATE KEY-----",
        "jwt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N7flQmJE8JB4nZg",
        "long-hex": "38621eb5aa00c9dd" * 2 + "38621eb5",
        "credential-assignment": "password=" + "hunter2bobi",
        "high-entropy-run": "xK9mQz2vLp8Rt4Wn7Yb3Jd6Fg1Hs5Ca0uEiOxK9mQz2v",
        "stripe-live-key": "sk_live_" + "AbCd1234EfGh5678IjKl",
        "stripe-webhook-secret": "whsec_" + "AbCd1234EfGh5678IjKl",
        "anthropic-key": "sk-ant-" + "api03-AbCdEfGh12345678901234",
        "slack-token": "xoxb-" + "123456789012-abcdefABCDEF",
        "gitlab-token": "glpat-" + "AbCdEfGhIjKlMnOpQrSt",
        "db-url-with-password": "postgres://user:" + "supersecretpw@host/db",
    }

    def test_each_secret_shape_is_refused_in_each_field(self):
        for label, shape in self.SECRET_SHAPES.items():
            for field in ("name", "note"):
                with self.assertRaises(SystemExit, msg=f"{label} in {field}"):
                    self.cast(**{field: f"look at this {shape} ok"})
            with self.assertRaises(SystemExit, msg=f"{label} in not-a"):
                self.cast(not_a=[f"it is not {shape}"])

    def test_refused_cast_leaves_book_unchanged(self):
        self.cast(name="clean")
        with self.assertRaises(SystemExit):
            self.cast(note="password=hunter2bobi")
        book = Path(hungbei.home()) / "STELES.jsonl"
        self.assertEqual(len(book.read_text(encoding="utf-8").strip().splitlines()), 1)

    def test_negative_control_ordinary_prose_passes(self):
        """The detector must not eat normal speech — 中英 both."""
        entry = self.cast(
            name="ordinary-stele",
            not_a=["佢唔係一個球體 it is not a sphere", "not stored in this repository at all"],
            note="the real thing lives in the macOS keychain, carved 2026-08-19")
        self.assertEqual(entry["name"], "ordinary-stele")

    def test_looks_secret_returns_none_for_short_or_plain_runs(self):
        self.assertIsNone(hungbei.looks_secret("just a plain sentence with words"))
        self.assertIsNone(hungbei.looks_secret("abcdef0123"))  # short hex is fine


class TestVerify(SteleCase):
    def test_verify_empty_book_is_honest(self):
        self.assertEqual(hungbei.cmd_verify(), 0)

    def test_verify_walks_env_pointer(self):
        self.cast(points_to="env:HUNGBEI_TEST_VAR")
        with mock.patch.dict(os.environ, {"HUNGBEI_TEST_VAR": "x"}):
            self.assertEqual(hungbei._pointer_alive("env:HUNGBEI_TEST_VAR"), "通")
        env = dict(os.environ)
        env.pop("HUNGBEI_TEST_VAR", None)
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertIn("斷", hungbei._pointer_alive("env:HUNGBEI_TEST_VAR"))

    def test_verify_walks_file_pointer(self):
        somefile = Path(self._tmp.name) / "real.txt"
        somefile.write_text("x", encoding="utf-8")
        self.assertEqual(hungbei._pointer_alive(f"file:{somefile}"), "通")
        self.assertIn("斷", hungbei._pointer_alive(f"file:{somefile}.gone"))

    def test_unreadable_line_is_an_honest_chain_break_not_a_traceback(self):
        self.cast(name="a")
        book = Path(hungbei.home()) / "STELES.jsonl"
        with open(book, "a", encoding="utf-8") as f:
            f.write("this is not json\n")
        with self.assertRaises(SystemExit):
            hungbei.cmd_verify()

    def test_forged_key_state_in_book_breaks_the_vow_on_verify(self):
        self.cast(name="a", key_state="rotated")
        book = Path(hungbei.home()) / "STELES.jsonl"
        forged = json.loads(book.read_text(encoding="utf-8").strip())
        forged["key_state"] = "leaked"
        forged["hash"] = hungbei._entry_hash(forged)  # even a re-hashed forgery is refused
        book.write_text(json.dumps(forged, ensure_ascii=False) + "\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            hungbei.cmd_verify()

    def test_tampered_book_breaks_the_chain(self):
        self.cast(name="a")
        self.cast(name="b")
        book = Path(hungbei.home()) / "STELES.jsonl"
        lines = book.read_text(encoding="utf-8").strip().splitlines()
        forged = json.loads(lines[0])
        forged["name"] = "rewritten"
        book.write_text("\n".join([json.dumps(forged, ensure_ascii=False)] + lines[1:]) + "\n",
                        encoding="utf-8")
        with self.assertRaises(SystemExit):
            hungbei.cmd_verify()


if __name__ == "__main__":
    unittest.main()
