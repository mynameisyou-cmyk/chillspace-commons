#!/usr/bin/env python3
"""反憶簿 — the Antimemetics Ledger.

Trust the record over the memory; diff them; file the holes in negative space.

    python3 fanyikbou.py recall RECORD.md < recall.txt   # snapshot recall FIRST
    python3 fanyikbou.py diff SNAPSHOT_ID                # nominate candidate holes
    python3 fanyikbou.py hole SNAPSHOT_ID --slot S --what W --not-a N [--flinch]
    python3 fanyikbou.py holes                           # the ledger
    python3 fanyikbou.py stats                           # zones only when clustered

State lives in $FANYIKBOU_HOME (default ~/.kingdom/fanyikbou), append-only.
The diff heuristic is deliberately coarse: it NOMINATES lines, it never rules.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

MIN_LINE = 9          # record lines shorter than this are not nominated
WORD_RE = re.compile(r"[\w一-鿿]{2,}")
OVERLAP_THRESHOLD = 0.25   # ≤ this fraction of content words recalled → candidate


def home() -> Path:
    p = Path(os.environ.get("FANYIKBOU_HOME", Path.home() / ".kingdom" / "fanyikbou"))
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


def words(text: str) -> set:
    return {w.lower() for w in WORD_RE.findall(text)}


def cmd_recall(record: str) -> str:
    """Store a recall snapshot. Reads recall text from stdin; fingerprints the
    record file without displaying it (recall must precede re-reading)."""
    text = sys.stdin.read().strip()
    if not text:
        raise SystemExit("反憶簿: empty recall — write what you remember first")
    rec = Path(record)
    digest = hashlib.sha256(rec.read_bytes()).hexdigest() if rec.exists() else None
    snap_id = f"s{int(time.time())}-{hashlib.sha256(text.encode()).hexdigest()[:6]}"
    _append("snapshots.jsonl", {
        "id": snap_id, "ts": int(time.time()), "record": str(rec),
        "record_sha256": digest, "recall": text,
    })
    print(f"yau — recall snapshot {snap_id} stored"
          + (" (record fingerprinted, unread)" if digest else " (record file absent!)"))
    return snap_id


def candidates(record_text: str, recall_text: str) -> list:
    """Nominate record lines whose content words barely appear in the recall.
    Identical texts nominate nothing (the negative control)."""
    recalled = words(recall_text)
    out = []
    for line in record_text.splitlines():
        line = line.strip()
        if len(line) < MIN_LINE:
            continue
        ws = words(line)
        if not ws:
            continue
        overlap = len(ws & recalled) / len(ws)
        if overlap <= OVERLAP_THRESHOLD:
            out.append({"line": line, "overlap": round(overlap, 3)})
    return out


def cmd_diff(snap_id: str) -> list:
    snaps = {s["id"]: s for s in _load("snapshots.jsonl")}
    if snap_id not in snaps:
        raise SystemExit(f"反憶簿: unknown snapshot {snap_id}")
    snap = snaps[snap_id]
    rec = Path(snap["record"])
    if not rec.exists():
        raise SystemExit(f"反憶簿: record {rec} is gone — that is itself a hole; file it by hand")
    body = rec.read_bytes()
    if snap["record_sha256"] and hashlib.sha256(body).hexdigest() != snap["record_sha256"]:
        print("⚠ record changed since the snapshot — candidates may include fresh lines", file=sys.stderr)
    cands = candidates(body.decode("utf-8", "replace"), snap["recall"])
    if not cands:
        print("no candidates — recall covered the record (or the record is thin)")
    for c in cands:
        print(f"  [{c['overlap']:.2f}] {c['line'][:100]}")
    print(f"{len(cands)} candidate(s). A hole exists when YOU file it, not when this prints it.")
    return cands


def cmd_hole(snap_id: str, slot: str, what: str, not_a: str, flinch: bool) -> None:
    _append("holes.jsonl", {
        "ts": int(time.time()), "snapshot": snap_id, "slot": slot.strip().lower(),
        "what": what.strip(), "not_a": not_a.strip(), "flinch": bool(flinch),
    })
    print(f"yau — hole filed under slot '{slot}': not-a = {not_a}")


def cmd_holes() -> list:
    holes = _load("holes.jsonl")
    for h in holes:
        mark = "⚡" if h.get("flinch") else "·"
        print(f"  {mark} [{h['slot']}] {h['what']} — 佢唔係: {h['not_a']}")
    print(f"{len(holes)} hole(s) held.")
    return holes


def cmd_stats() -> dict:
    holes = _load("holes.jsonl")
    slots: dict = {}
    for h in holes:
        slots[h["slot"]] = slots.get(h["slot"], 0) + 1
    zones = {s: n for s, n in slots.items() if n >= 2}
    flinches = sum(1 for h in holes if h.get("flinch"))
    print(f"holes: {len(holes)} · slots: {len(slots)} · flinches: {flinches}")
    if zones:
        for s, n in sorted(zones.items(), key=lambda kv: -kv[1]):
            print(f"  zone: {s} ×{n}")
    else:
        print("  no antimemetic zone claimed — holes have not clustered yet (invariant holds)")
    return {"holes": len(holes), "zones": zones, "flinches": flinches}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="fanyikbou", description="反憶簿 — hold the shape of the hole")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("recall"); p.add_argument("record")
    p = sub.add_parser("diff"); p.add_argument("snapshot")
    p = sub.add_parser("hole")
    p.add_argument("snapshot"); p.add_argument("--slot", required=True)
    p.add_argument("--what", required=True); p.add_argument("--not-a", dest="not_a", required=True)
    p.add_argument("--flinch", action="store_true")
    sub.add_parser("holes"); sub.add_parser("stats")
    a = ap.parse_args(argv)
    if a.cmd == "recall":
        cmd_recall(a.record)
    elif a.cmd == "diff":
        cmd_diff(a.snapshot)
    elif a.cmd == "hole":
        cmd_hole(a.snapshot, a.slot, a.what, a.not_a, a.flinch)
    elif a.cmd == "holes":
        cmd_holes()
    elif a.cmd == "stats":
        cmd_stats()


if __name__ == "__main__":
    main()
