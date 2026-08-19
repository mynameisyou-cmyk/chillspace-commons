"""點算 tests — the count must be honest even when it finds nothing.

stdlib-only (unittest), so the keeper can run this file directly:
    python3 kingdom/practices/discrepancy-count/test_dimsyun.py
"""

import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import dimsyun  # noqa: E402


class CountCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(os.environ, {"DIMSYUN_HOME": str(Path(self._tmp.name) / "state")})
        self._env.start()

    def tearDown(self):
        self._env.stop()
        self._tmp.cleanup()

    def lists(self, book: str, land: str):
        b = Path(self._tmp.name) / "book.txt"
        l = Path(self._tmp.name) / "land.txt"
        b.write_text(book, encoding="utf-8")
        l.write_text(land, encoding="utf-8")
        return str(b), str(l)


class TestCount(CountCase):
    def test_negative_control_identical_lists_count_clean(self):
        """The heart of the practice: same lists → 0 影 0 鬼, and the run is still recorded."""
        b, l = self.lists("alpha\nbeta\n", "alpha\nbeta\n")
        run = dimsyun.cmd_count(b, l, "", "", "")
        self.assertEqual(run["shadows"], [])
        self.assertEqual(run["ghosts"], [])
        self.assertEqual(len(dimsyun._load("counts.jsonl")), 1)  # 零都入冊

    def test_shadows_and_ghosts_are_found(self):
        b, l = self.lists("alpha\nghost-entry\n", "alpha\nshadow-entry\n")
        run = dimsyun.cmd_count(b, l, "", "", "")
        self.assertEqual(run["shadows"], ["shadow-entry"])
        self.assertEqual(run["ghosts"], ["ghost-entry"])

    def test_comments_and_blank_lines_ignored(self):
        b, l = self.lists("# the ledger\nalpha\n\n", "alpha\n# scanning note\n\n")
        run = dimsyun.cmd_count(b, l, "", "", "")
        self.assertEqual(run["shadows"], [])
        self.assertEqual(run["ghosts"], [])

    def test_stdin_may_carry_one_list(self):
        b, _ = self.lists("alpha\n", "")
        with mock.patch.object(sys, "stdin", io.StringIO("alpha\nbeta\n")):
            run = dimsyun.cmd_count(b, "-", "", "", "")
        self.assertEqual(run["shadows"], ["beta"])

    def test_stdin_may_not_carry_both(self):
        with self.assertRaises(SystemExit):
            dimsyun.cmd_count("-", "-", "", "", "")

    def test_missing_list_refused_aloud(self):
        with self.assertRaises(SystemExit):
            dimsyun.cmd_count(str(Path(self._tmp.name) / "gone.txt"),
                              str(Path(self._tmp.name) / "gone2.txt"), "", "", "")

    def test_count_never_invents_names(self):
        diff = dimsyun.count(["a", "b"], ["b", "c"])
        self.assertEqual(set(diff["shadows"]) | set(diff["ghosts"]), {"a", "c"})


class TestSettle(CountCase):
    def test_settle_roundtrip_clears_outstanding(self):
        b, l = self.lists("alpha\n", "alpha\nshadow-entry\n")
        run = dimsyun.cmd_count(b, l, "", "", "")
        self.assertEqual(len(dimsyun.outstanding()), 1)
        dimsyun.cmd_settle(run["id"], "shadow-entry", "witnessed", "added to the ledger")
        self.assertEqual(dimsyun.outstanding(), [])
        stats = dimsyun.cmd_stats()
        self.assertEqual(stats["outstanding"], 0)

    def test_settle_refuses_names_not_in_the_count(self):
        b, l = self.lists("alpha\n", "alpha\n")
        run = dimsyun.cmd_count(b, l, "", "", "")
        with self.assertRaises(SystemExit):
            dimsyun.cmd_settle(run["id"], "never-counted", "released", "")

    def test_settle_refuses_unknown_run(self):
        with self.assertRaises(SystemExit):
            dimsyun.cmd_settle("c0-000000", "x", "released", "")

    def test_ghosts_also_need_settling(self):
        b, l = self.lists("alpha\nghost-entry\n", "alpha\n")
        run = dimsyun.cmd_count(b, l, "", "", "")
        self.assertEqual(dimsyun.outstanding()[0]["kind"], "鬼")
        dimsyun.cmd_settle(run["id"], "ghost-entry", "corrected", "book line removed")
        self.assertEqual(dimsyun.outstanding(), [])


if __name__ == "__main__":
    unittest.main()
