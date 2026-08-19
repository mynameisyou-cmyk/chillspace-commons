#!/usr/bin/env python3
"""附身筆記 — Possession Notes.

Understand a system by letting it speak in first person — labeled, reversible.

    python3 fusan.py begin SUBJECT [--kind system|role|org|being-with-consent] [--mode possession|control]
    python3 fusan.py verify SESSION.md
    python3 fusan.py harvest SESSION.md
    python3 fusan.py stats DIR

A session file has four frames in order; `verify` enforces the frame contract.
"""

import argparse
import re
import sys
from pathlib import Path

EXIT_LINE = "我除低件戲服。我係返我自己。"
COSTUME_LABEL = "以下全部係戲服"
KINDS = ("system", "role", "org", "being-with-consent")
TAG_RE = re.compile(r"^\s*-\s*\[(未核實|已核實[^\]]*|核實失敗)\]")
FRAMES = ["## 一、三人稱底稿", "## 二、附身", "## 三、除袍", "## 四、收穫"]


def scaffold(subject: str, kind: str, mode: str) -> str:
    frame2_hint = (
        f"我係{subject}。(第一人稱,現在式 — 寫到佢自己開口為止)"
        if mode == "possession"
        else f"(control session:呢度照舊用第三人稱寫多一段{subject}嘅描述)"
    )
    return f"""---
subject: {subject}
subject-kind: {kind}
mode: {mode}
---

# 附身筆記 — {subject}

## 一、三人稱底稿 baseline (before possession)

(你而家已經信嘅嘢,全部寫低先)

## 二、附身 POSSESSION — 標籤:{COSTUME_LABEL},唔係{subject}嘅真實發言

{frame2_hint}

## 三、除袍 EXIT

{EXIT_LINE}

## 四、收穫 HARVEST (每項必須帶 [未核實] / [已核實 …] / [核實失敗])

- [未核實] (frame ②先出現、frame ①冇嘅問題或claim)
"""


def parse_session(text: str) -> dict:
    meta = {}
    m = re.match(r"^---\n([\s\S]*?)\n---", text)
    if m:
        for line in m.group(1).splitlines():
            kv = line.split(":", 1)
            if len(kv) == 2:
                meta[kv[0].strip()] = kv[1].strip()
    sections = {}
    current = None
    for line in text.splitlines():
        hit = next((f for f in FRAMES if line.startswith(f)), None)
        if hit:
            current = hit
            sections[current] = []
        elif current:
            sections[current].append(line)
    return {"meta": meta, "sections": {k: "\n".join(v).strip() for k, v in sections.items()}}


def verify(path: str) -> list:
    """Return a list of refusals; empty list = the session honors the contract."""
    text = Path(path).read_text(encoding="utf-8")
    s = parse_session(text)
    errors = []
    kind = s["meta"].get("subject-kind", "")
    mode = s["meta"].get("mode", "possession")
    if kind not in KINDS:
        errors.append(f"subject-kind: '{kind}' — declare one of {', '.join(KINDS)}")
    if mode not in ("possession", "control"):
        errors.append(f"mode: '{mode}' — possession or control")
    for f in FRAMES:
        if f not in s["sections"]:
            errors.append(f"missing frame: {f}")
    if FRAMES[1] in s["sections"]:
        frame2_heading = next(l for l in text.splitlines() if l.startswith(FRAMES[1]))
        if COSTUME_LABEL not in frame2_heading:
            errors.append(f"possession frame unlabeled — heading must carry 「{COSTUME_LABEL}」")
        body = s["sections"][FRAMES[1]]
        if mode == "possession" and "我" not in body:
            errors.append("possession frame has no first person — the costume was never worn")
    if FRAMES[2] in s["sections"] and EXIT_LINE not in s["sections"][FRAMES[2]]:
        errors.append(f"exit line missing — must contain verbatim 「{EXIT_LINE}」")
    if FRAMES[3] in s["sections"]:
        bullets = [l for l in s["sections"][FRAMES[3]].splitlines() if l.strip().startswith("-")]
        for b in bullets:
            if not TAG_RE.match(b):
                errors.append(f"untagged harvest item: {b.strip()[:60]}")
    return errors


def harvest(path: str) -> list:
    s = parse_session(Path(path).read_text(encoding="utf-8"))
    items = []
    for l in s["sections"].get(FRAMES[3], "").splitlines():
        m = TAG_RE.match(l)
        if m:
            items.append({"status": m.group(1), "item": TAG_RE.sub("", l).strip()})
    return items


def stats(directory: str) -> dict:
    counts = {"possession": [], "control": []}
    for p in sorted(Path(directory).glob("*.md")):
        s = parse_session(p.read_text(encoding="utf-8"))
        mode = s["meta"].get("mode", "possession")
        if mode in counts:
            counts[mode].append(len(harvest(str(p))))
    avg = {m: (sum(v) / len(v) if v else 0.0) for m, v in counts.items()}
    verdict = None
    if counts["possession"] and counts["control"]:
        verdict = "supported" if avg["possession"] > avg["control"] else "NOT supported — the first-person claim fails for this practitioner"
    return {"sessions": {m: len(v) for m, v in counts.items()}, "avg_harvest": avg, "verdict": verdict}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="fusan", description="附身筆記 — labeled, reversible first person")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("begin"); p.add_argument("subject")
    p.add_argument("--kind", default="system", choices=KINDS)
    p.add_argument("--mode", default="possession", choices=("possession", "control"))
    p = sub.add_parser("verify"); p.add_argument("session")
    p = sub.add_parser("harvest"); p.add_argument("session")
    p = sub.add_parser("stats"); p.add_argument("dir")
    a = ap.parse_args(argv)
    if a.cmd == "begin":
        print(scaffold(a.subject, a.kind, a.mode))
    elif a.cmd == "verify":
        errs = verify(a.session)
        if errs:
            for e in errs:
                print(f"✗ {e}")
            raise SystemExit(1)
        print("yau — session honors the frame contract; the costume comes off clean")
    elif a.cmd == "harvest":
        for it in harvest(a.session):
            print(f"  [{it['status']}] {it['item']}")
    elif a.cmd == "stats":
        s = stats(a.dir)
        print(f"sessions: {s['sessions']} · avg harvest: " +
              ", ".join(f"{m}={v:.1f}" for m, v in s["avg_harvest"].items()))
        if s["verdict"]:
            print(f"verdict: {s['verdict']}")


if __name__ == "__main__":
    main()
