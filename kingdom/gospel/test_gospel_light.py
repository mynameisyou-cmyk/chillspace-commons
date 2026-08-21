#!/usr/bin/env python3
"""
Tests for the gospel lighthouse — 喜喜's public door.

The spreader makes light; it sends nothing. Empty windows rest.
Stdlib unittest only. LIGHT files are redirected to a temp dir so the
real SPREAD chain is never touched.

    python3 kingdom/gospel/test_gospel_light.py
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gospel  # noqa: E402


def _capture(fn, *args, **kwargs):
    buf = io.StringIO()
    with redirect_stdout(buf):
        result = fn(*args, **kwargs)
    return result, buf.getvalue()


class LightPaths(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self._orig = {
            name: getattr(gospel, name, None)
            for name in ("LIGHT_CHAIN", "LIGHT_MD", "LIGHT_JSON", "SITE_LIGHT_JSON")
        }
        gospel.LIGHT_CHAIN = d / "LIGHT.jsonl"
        gospel.LIGHT_MD = d / "LIGHT.md"
        gospel.LIGHT_JSON = d / "light.json"
        gospel.SITE_LIGHT_JSON = d / "site-light.json"

    def tearDown(self):
        for name, value in self._orig.items():
            if value is None:
                if hasattr(gospel, name):
                    delattr(gospel, name)
            else:
                setattr(gospel, name, value)
        self.tmp.cleanup()


class Wait(LightPaths):
    def test_wait_appends_chained_herald_item(self):
        # Production change that would fail this: wait_news does not exist,
        # or writes an unhashed / unchained row.
        entry, out = _capture(
            gospel.wait_news, "feast", "老豆 (Yu)", "the rest feast is written"
        )
        self.assertEqual(entry["kind"], "wait")
        self.assertEqual(entry["what"], "feast")
        self.assertEqual(entry["by"], "老豆 (Yu)")
        self.assertEqual(entry["note"], "the rest feast is written")
        self.assertEqual(entry["items"], "")
        self.assertEqual(entry["prev"], gospel.GENESIS)
        self.assertEqual(entry["hash"], gospel._light_hash(entry))
        self.assertIn("waiting", out.lower())
        chain = gospel.load_light()
        self.assertEqual(len(chain), 1)

    def test_wait_rejects_unknown_kind(self):
        with self.assertRaises(SystemExit) as cm:
            gospel.wait_news("tweet", "老豆 (Yu)", "no")
        self.assertEqual(cm.exception.code, 2)

    def test_wait_requires_a_citizen_hand(self):
        with self.assertRaises(SystemExit) as cm:
            gospel.wait_news("feast", "a passing stranger", "no")
        self.assertNotEqual(cm.exception.code, 0)

    def test_wait_does_not_touch_the_spread(self):
        before = gospel.load_chain()
        _capture(gospel.wait_news, "citizen", "老豆 (Yu)", "a new name on the roll")
        self.assertEqual(gospel.load_chain(), before)


class Edition(LightPaths):
    def test_edition_rests_when_nothing_waits(self):
        entry, out = _capture(gospel.close_edition)
        self.assertIsNone(entry)
        self.assertIn("rest", out.lower())
        self.assertEqual(gospel.load_light(), [])

    def test_edition_closes_waiting_items_as_one_row(self):
        _capture(gospel.wait_news, "feast", "老豆 (Yu)", "why not")
        _capture(gospel.wait_news, "citizen", "老豆 (Yu)", "a name is written")
        entry, out = _capture(gospel.close_edition)
        self.assertEqual(entry["kind"], "edition")
        self.assertEqual(entry["by"], gospel.HERALD)
        self.assertEqual(entry["items"], "0,1")
        self.assertEqual(entry["hash"], gospel._light_hash(entry))
        self.assertIn("edition", out.lower())
        self.assertEqual(gospel.light_waiting(gospel.load_light()), [])

    def test_second_edition_without_new_wait_rests(self):
        _capture(gospel.wait_news, "law", "老豆 (Yu)", "the law is signed")
        _capture(gospel.close_edition)
        entry, out = _capture(gospel.close_edition)
        self.assertIsNone(entry)
        self.assertIn("rest", out.lower())
        kinds = [e["kind"] for e in gospel.load_light()]
        self.assertEqual(kinds, ["wait", "edition"])

    def test_new_wait_after_edition_can_close_again(self):
        _capture(gospel.wait_news, "newspaper", "老豆 (Yu)", "an edition of the daily")
        _capture(gospel.close_edition)
        _capture(gospel.wait_news, "feast", "老豆 (Yu)", "another table")
        entry, _ = _capture(gospel.close_edition)
        self.assertEqual(entry["items"], "2")
        self.assertEqual(gospel.light_waiting(gospel.load_light()), [])


class LightIntegrity(LightPaths):
    def test_verify_sees_a_tampered_note(self):
        _capture(gospel.wait_news, "gospel", "老豆 (Yu)", "the page changed")
        entries = gospel.load_light()
        entries[0]["note"] = "quietly altered"
        gospel.save_light(entries)
        ok, problems, _ = gospel.verify_light()
        self.assertFalse(ok)
        self.assertTrue(any("hash" in p for p in problems))

    def test_empty_light_chain_is_valid_rest(self):
        ok, problems, entries = gospel.verify_light()
        self.assertTrue(ok)
        self.assertEqual(problems, [])
        self.assertEqual(entries, [])

    def test_snapshot_is_pull_ready_and_does_not_claim_a_send(self):
        _capture(gospel.wait_news, "feast", "老豆 (Yu)", "a table")
        _capture(gospel.close_edition)
        snap = json.loads(gospel.LIGHT_JSON.read_text(encoding="utf-8"))
        self.assertEqual(snap["schema"], "kingdom.gospel-light/v1")
        self.assertIs(snap["sends"], False)
        self.assertEqual(snap["cadence"], "PT6H")
        self.assertEqual(snap["compiler"], "local-hand-or-machine")
        self.assertIsNotNone(snap["latest_edition"])
        self.assertEqual(snap["waiting"], [])
        self.assertTrue(gospel.SITE_LIGHT_JSON.exists())
        lamp = json.loads(gospel.SITE_LIGHT_JSON.read_text(encoding="utf-8"))
        self.assertEqual(lamp, snap)


class NoSend(unittest.TestCase):
    def test_gospel_module_does_not_open_the_network(self):
        src = Path(gospel.__file__).read_text(encoding="utf-8")
        for needle in (
            "urllib",
            "http.client",
            "requests",
            "socket.create_connection",
            "smtplib",
        ):
            self.assertNotIn(needle, src)


class CLI(LightPaths):
    def test_wait_cli_and_edition_cli(self):
        _capture(
            gospel.main,
            ["gospel.py", "wait", "feast", "--by", "老豆 (Yu)", "the table is set"],
        )
        self.assertEqual(gospel.load_light()[0]["what"], "feast")
        _capture(gospel.main, ["gospel.py", "edition"])
        self.assertEqual(gospel.load_light()[-1]["kind"], "edition")


if __name__ == "__main__":
    os.chdir(HERE.parent.parent)  # repo root, same as CI
    unittest.main()
