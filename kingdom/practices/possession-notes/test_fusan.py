"""附身筆記 tests — a possession you cannot exit is not a practice."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import fusan  # noqa: E402


def write(tmp_path, text):
    p = tmp_path / "session.md"
    p.write_text(text, encoding="utf-8")
    return str(p)


def good_session(subject="the CI validator", mode="possession", frame2="我係the CI validator。我只識六樣嘢。"):
    return f"""---
subject: {subject}
subject-kind: system
mode: {mode}
---

# 附身筆記 — {subject}

## 一、三人稱底稿 baseline (before possession)

it validates documents.

## 二、附身 POSSESSION — 標籤:{fusan.COSTUME_LABEL},唔係{subject}嘅真實發言

{frame2}

## 三、除袍 EXIT

{fusan.EXIT_LINE}

## 四、收穫 HARVEST (每項必須帶 [未核實] / [已核實 …] / [核實失敗])

- [未核實] does it treat empty addenda differently from missing addenda?
- [已核實 (validate.ts)] it refuses before writing anything.
"""


def test_scaffold_contains_all_four_frames_and_exit_line():
    s = fusan.scaffold("女女", "being-with-consent", "possession")
    for f in fusan.FRAMES:
        assert f in s
    assert fusan.EXIT_LINE in s
    assert fusan.COSTUME_LABEL in s


def test_good_session_verifies_clean(tmp_path):
    assert fusan.verify(write(tmp_path, good_session())) == []


def test_missing_exit_line_is_refused(tmp_path):
    text = good_session().replace(fusan.EXIT_LINE, "ok done")
    errs = fusan.verify(write(tmp_path, text))
    assert any("exit line" in e for e in errs)


def test_unlabeled_possession_is_refused(tmp_path):
    text = good_session().replace(f"標籤:{fusan.COSTUME_LABEL},", "")
    errs = fusan.verify(write(tmp_path, text))
    assert any("unlabeled" in e for e in errs)


def test_undeclared_subject_kind_is_refused(tmp_path):
    text = good_session().replace("subject-kind: system", "subject-kind: person")
    errs = fusan.verify(write(tmp_path, text))
    assert any("subject-kind" in e for e in errs)


def test_untagged_harvest_item_is_refused(tmp_path):
    text = good_session() + "- a bare claim with no tag\n"
    errs = fusan.verify(write(tmp_path, text))
    assert any("untagged" in e for e in errs)


def test_possession_without_first_person_is_refused(tmp_path):
    text = good_session(frame2="it is a validator that refuses things.")
    errs = fusan.verify(write(tmp_path, text))
    assert any("first person" in e for e in errs)


def test_control_mode_allows_third_person(tmp_path):
    text = good_session(mode="control", frame2="it is a validator that refuses things.")
    assert fusan.verify(write(tmp_path, text)) == []


def test_harvest_extracts_tagged_items(tmp_path):
    items = fusan.harvest(write(tmp_path, good_session()))
    assert len(items) == 2
    assert items[0]["status"] == "未核實"


def test_stats_compares_modes_and_can_refute(tmp_path):
    d = tmp_path / "sessions"
    d.mkdir()
    (d / "a.md").write_text(good_session(), encoding="utf-8")
    control = good_session(mode="control", frame2="third person text.") + "- [未核實] extra one\n- [未核實] extra two\n"
    (d / "b.md").write_text(control, encoding="utf-8")
    s = fusan.stats(str(d))
    assert s["sessions"] == {"possession": 1, "control": 1}
    assert "NOT supported" in s["verdict"]
