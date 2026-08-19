"""反憶簿 tests — the instrument must be able to be wrong."""

import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import fanyikbou  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("FANYIKBOU_HOME", str(tmp_path / "state"))
    yield tmp_path


def test_negative_control_identical_texts_yield_no_candidates():
    text = "the manual vercel deploy step lives in the site directory\nanother meaningful line here"
    assert fanyikbou.candidates(text, text) == []


def test_candidates_nominate_unrecalled_lines():
    record = "the manual vercel deploy step lives in the site directory\nbreakfast was congee"
    recall = "something about breakfast congee being nice"
    cands = fanyikbou.candidates(record, recall)
    assert len(cands) == 1
    assert "vercel" in cands[0]["line"]


def test_short_lines_are_not_nominated():
    assert fanyikbou.candidates("ok\nyau\n", "totally unrelated recall") == []


def test_recall_then_diff_then_hole_roundtrip(tmp_path, monkeypatch, capsys):
    record = tmp_path / "RECORD.md"
    record.write_text("the launchd plists for val1-3 must be loaded by hand\nthe cat is orange", encoding="utf-8")
    monkeypatch.setattr("sys.stdin", io.StringIO("i remember an orange cat and nothing else"))
    snap_id = fanyikbou.cmd_recall(str(record))
    capsys.readouterr()

    cands = fanyikbou.cmd_diff(snap_id)
    assert any("launchd" in c["line"] for c in cands)

    fanyikbou.cmd_hole(snap_id, slot="ops", what="the launchd step", not_a="not automatic", flinch=True)
    holes = fanyikbou.cmd_holes()
    assert holes[0]["not_a"] == "not automatic"
    assert holes[0]["flinch"] is True


def test_no_zone_claim_until_holes_cluster(capsys):
    fanyikbou.cmd_hole("s1", slot="ops", what="a", not_a="not b", flinch=False)
    capsys.readouterr()
    stats = fanyikbou.cmd_stats()
    assert stats["zones"] == {}
    out = capsys.readouterr().out
    assert "no antimemetic zone claimed" in out

    fanyikbou.cmd_hole("s2", slot="ops", what="c", not_a="not d", flinch=False)
    stats = fanyikbou.cmd_stats()
    assert stats["zones"] == {"ops": 2}


def test_empty_recall_refused(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("   "))
    with pytest.raises(SystemExit):
        fanyikbou.cmd_recall("whatever.md")


def test_ledger_is_append_only_jsonl(tmp_path, monkeypatch, capsys):
    fanyikbou.cmd_hole("s1", slot="x", what="w", not_a="n", flinch=False)
    ledger = Path(fanyikbou.home()) / "holes.jsonl"
    lines = ledger.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    json.loads(lines[0])
