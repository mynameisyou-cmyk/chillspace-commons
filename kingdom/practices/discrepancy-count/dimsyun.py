#!/usr/bin/env python3
"""點算 — the Counting.

You cannot see an antimeme. You can count. Hand the tool two name-lists —
what the ledger says (書 the book) and what stands in the land (地) — and it
subtracts. What stands unwritten is a shadow (影: exists, unwitnessed).
What is written but gone is a ghost (鬼: witnessed, vanished). 055 is never
found by looking; it is found when the numbers refuse to agree.

    python3 dimsyun.py count --book BOOK.txt --land LAND.txt \\
        [--book-label "…"] [--land-label "…"] [--note "…"]
    python3 dimsyun.py runs                  # every count ever taken
    python3 dimsyun.py settle RUN_ID NAME --how witnessed|steled|released|corrected [--note "…"]
    python3 dimsyun.py stats                 # what still stands unsettled, out loud

Name-lists are one name per line; blank lines and #-comments are ignored;
"-" reads one of the two lists from stdin. Every count is recorded in
$DIMSYUN_HOME (default ~/.kingdom/dimsyun; ~/.kingdom-practices/dimsyun on
machines where Kingdom OS already claimed ~/.kingdom as a file), zero-
discrepancy counts included: 零都入冊 — a clean count is a result, not a
non-event.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

SETTLE_HOW = ("witnessed", "steled", "released", "corrected")


def home() -> Path:
    if "DIMSYUN_HOME" in os.environ:
        p = Path(os.environ["DIMSYUN_HOME"])
    else:
        p = Path.home() / ".kingdom" / "dimsyun"
        # On machines where Kingdom OS init claimed ~/.kingdom as a FILE, the
        # conventional home cannot exist. Found by this very tool's first count.
        if p.parent.exists() and not p.parent.is_dir():
            p = Path.home() / ".kingdom-practices" / "dimsyun"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _append(name: str, obj: dict) -> None:
    with open(home() / name, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _load(name: str) -> list:
    path = home() / name
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def read_names(source: str) -> tuple:
    """Read a name-list: one name per line, stripped; blanks and #-comments
    dropped. Returns (names, dropped_comments) — the drop is said aloud by
    the caller, never silent: a name that truly starts with '#' must be
    counted by other means."""
    if source == "-":
        raw = sys.stdin.read()
    else:
        p = Path(source)
        if not p.exists():
            raise SystemExit(f"點算: list {source} is gone — a book that vanished is itself worth counting")
        raw = p.read_text(encoding="utf-8")
    names, dropped = [], 0
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            dropped += 1
            continue
        names.append(line)
    return names, dropped


def count(book: list, land: list) -> dict:
    """Pure subtraction. The tool never invents a name; it only diffs what it was handed."""
    book_set, land_set = set(book), set(land)
    return {
        "shadows": sorted(land_set - book_set),
        "ghosts": sorted(book_set - land_set),
    }


def cmd_count(book_src: str, land_src: str, book_label: str, land_label: str, note: str) -> dict:
    if book_src == "-" and land_src == "-":
        raise SystemExit("點算: only one of the two lists may come from stdin")
    book, book_dropped = read_names(book_src)
    land, land_dropped = read_names(land_src)
    diff = count(book, land)
    digest = hashlib.sha256(("\n".join(book) + "\x00" + "\n".join(land)).encode()).hexdigest()
    seq = len(_load("counts.jsonl")) + 1  # keeps same-second ids distinct
    run = {
        "id": f"c{int(time.time())}-{seq:03d}-{digest[:6]}",
        "ts": int(time.time()),
        "book_label": book_label or book_src,
        "land_label": land_label or land_src,
        "book_n": len(book),
        "land_n": len(land),
        "book_sha256": hashlib.sha256("\n".join(book).encode()).hexdigest(),
        "land_sha256": hashlib.sha256("\n".join(land).encode()).hexdigest(),
        "shadows": diff["shadows"],
        "ghosts": diff["ghosts"],
        "note": (note or "").strip(),
    }
    _append("counts.jsonl", run)
    print(f"yau — 點算 {run['id']}: 書 {run['book_n']} vs 地 {run['land_n']}")
    if book_dropped or land_dropped:
        print(f"  (#-comment lines dropped, not counted: 書 {book_dropped} · 地 {land_dropped})")
    for s in diff["shadows"]:
        print(f"  影 {s}   (stands in the land, unwritten in the book)")
    for g in diff["ghosts"]:
        print(f"  鬼 {g}   (written in the book, gone from the land)")
    if not diff["shadows"] and not diff["ghosts"]:
        print("  數啱 — 0 影 0 鬼. A clean count is a result, not a non-event; it is recorded.")
    else:
        print(f"{len(diff['shadows'])} 影 · {len(diff['ghosts'])} 鬼 — "
              "each one must be settled by hand (settle), never silently dropped.")
    return run


def cmd_runs() -> list:
    runs = _load("counts.jsonl")
    for r in runs:
        day = time.strftime("%Y-%m-%d", time.localtime(r["ts"]))
        print(f"  {r['id']} {day} — {r['book_label']} vs {r['land_label']}: "
              f"{len(r['shadows'])} 影 {len(r['ghosts'])} 鬼")
    print(f"{len(runs)} count(s) taken.")
    return runs


def cmd_settle(run_id: str, name: str, how: str, note: str) -> None:
    runs = {r["id"]: r for r in _load("counts.jsonl")}
    if run_id not in runs:
        raise SystemExit(f"點算: unknown count {run_id}")
    run = runs[run_id]
    if name not in run["shadows"] and name not in run["ghosts"]:
        raise SystemExit(f"點算: {name!r} is neither 影 nor 鬼 in {run_id} — nothing to settle")
    _append("settlements.jsonl", {
        "ts": int(time.time()), "run": run_id, "name": name,
        "how": how, "note": (note or "").strip(),
    })
    print(f"yau — {name} 安置咗 ({how})")


def outstanding() -> list:
    settled = {(s["run"], s["name"]) for s in _load("settlements.jsonl")}
    out = []
    for r in _load("counts.jsonl"):
        for kind, names in (("影", r["shadows"]), ("鬼", r["ghosts"])):
            for n in names:
                if (r["id"], n) not in settled:
                    out.append({"run": r["id"], "kind": kind, "name": n})
    return out

def cmd_stats() -> dict:
    runs = _load("counts.jsonl")
    out = outstanding()
    settled_n = len(_load("settlements.jsonl"))
    print(f"counts: {len(runs)} · settled: {settled_n} · 未安置: {len(out)}")
    for o in out:
        print(f"  {o['kind']} {o['name']}  ({o['run']})")
    if not out:
        print("  every shadow and ghost settled — the books agree with the land, as far as counted")
    else:
        print("誓約二 · 影必安置 — witness it, stele it, release it, or correct the book. Not silence.")
    return {"counts": len(runs), "settled": settled_n, "outstanding": len(out)}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dimsyun", description="點算 — find what refuses to be seen by counting")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("count")
    p.add_argument("--book", required=True, help="the ledger's name-list (file or -)")
    p.add_argument("--land", required=True, help="reality's name-list (file or -)")
    p.add_argument("--book-label", dest="book_label", default="")
    p.add_argument("--land-label", dest="land_label", default="")
    p.add_argument("--note", default="")
    sub.add_parser("runs")
    p = sub.add_parser("settle")
    p.add_argument("run_id")
    p.add_argument("name")
    p.add_argument("--how", required=True, choices=SETTLE_HOW)
    p.add_argument("--note", default="")
    sub.add_parser("stats")
    a = ap.parse_args(argv)
    if a.cmd == "count":
        cmd_count(a.book, a.land, a.book_label, a.land_label, a.note)
    elif a.cmd == "runs":
        cmd_runs()
    elif a.cmd == "settle":
        cmd_settle(a.run_id, a.name, a.how, a.note)
    elif a.cmd == "stats":
        cmd_stats()


if __name__ == "__main__":
    main()
