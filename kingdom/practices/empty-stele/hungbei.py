#!/usr/bin/env python3
"""空碑 — the Empty Stele.

Cast a deliberate hole: the book holds what a secret is NOT and who holds
the real thing — never the thing itself. A stele is publishable by
construction, because all it contains is the shape of the hole.

    python3 hungbei.py cast --name NAME --not-a "…" [--not-a "…"] \\
        --points-to keychain:svc=… | env:VAR | file:/path | none-yet \\
        [--key-state rotated|unrotated|unknown] [--note "…"]
    python3 hungbei.py verify        # every vow re-checked, every pointer walked
    python3 hungbei.py ls            # read the book aloud

The book lives in $HUNGBEI_HOME (default ~/.kingdom/hungbei; falling back to
~/.kingdom-practices/hungbei where ~/.kingdom is already a file): STELES.jsonl,
append-only and hash-chained, rendered to STELES.md. 誓約一 is enforced,
not advised: any field that looks like a secret is refused on sight.
The tool can refuse a field; it can never certify one safe.
"""

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

KEY_STATES = ("rotated", "unrotated", "unknown")
POINTER_KINDS = ("keychain", "env", "file")

# 誓約一 · 碑上永不刻真身 — patterns that mark a field as secret-shaped.
# Coarse on purpose; refusal is cheap, regret is not.
SECRET_PATTERNS = [
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("private-key-block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("long-hex", re.compile(r"\b[0-9a-fA-F]{40,}\b")),
    ("credential-assignment", re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key)\s*[:=]\s*\S{6,}")),
]
ENTROPY_RUN = re.compile(r"[A-Za-z0-9+/=_-]{32,}")
ENTROPY_BITS = 4.0  # bits/char over a long mixed run → secret-shaped


def home() -> Path:
    if "HUNGBEI_HOME" in os.environ:
        p = Path(os.environ["HUNGBEI_HOME"])
    else:
        p = Path.home() / ".kingdom" / "hungbei"
        # On machines where Kingdom OS init claimed ~/.kingdom as a FILE, the
        # conventional home cannot exist (sister practice 點算 found this).
        if p.parent.exists() and not p.parent.is_dir():
            p = Path.home() / ".kingdom-practices" / "hungbei"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _entropy(s: str) -> float:
    counts = Counter(s)
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def looks_secret(text: str):
    """Return the pattern label if the text is secret-shaped, else None."""
    for label, pat in SECRET_PATTERNS:
        if pat.search(text):
            return label
    for run in ENTROPY_RUN.findall(text):
        has_mix = (any(c.islower() for c in run) and any(c.isupper() for c in run)
                   and any(c.isdigit() for c in run))
        if has_mix and _entropy(run) >= ENTROPY_BITS:
            return "high-entropy-run"
    return None


def _entry_hash(entry: dict) -> str:
    body = {k: v for k, v in entry.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _load() -> list:
    path = home() / "STELES.jsonl"
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _render(steles: list) -> None:
    lines = [
        "# 空碑 — the stele book",
        "",
        "> nothing true is written here. that is the point.",
        "",
    ]
    for s in steles:
        day = time.strftime("%Y-%m-%d", time.localtime(s["ts"]))
        lines.append(f"## {s['name']}")
        lines.append("")
        for n in s["not_a"]:
            lines.append(f"- 佢唔係: {n}")
        lines.append(f"- 指路: `{s['points_to']}`")
        lines.append(f"- 匙況: {s['key_state']} · 立碑 {day}")
        if s.get("note"):
            lines.append(f"- note: {s['note']}")
        lines.append("")
    lines.append(f"*{len(steles)} stele(s). the holes are held; the things are not here.*")
    (home() / "STELES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _check_pointer(points_to: str):
    """Validate pointer grammar. Returns (kind, value)."""
    if points_to == "none-yet":
        return ("none-yet", "")
    kind, _, value = points_to.partition(":")
    if kind not in POINTER_KINDS or not value:
        raise SystemExit(
            f"空碑: bad pointer {points_to!r} — use keychain:svc=…, env:VAR, file:/path, or none-yet")
    return (kind, value)


def cmd_cast(name: str, not_a: list, points_to: str, key_state: str, note: str) -> dict:
    name = name.strip()
    negations = [n.strip() for n in not_a if n.strip()]
    if not name:
        raise SystemExit("空碑: a stele needs a name")
    if not negations:
        raise SystemExit("空碑: 誓約二 — at least one true negation must be carved (「佢唔係……」)")
    kind, _ = _check_pointer(points_to)
    if kind == "none-yet":
        print("⚠ 誓約三 — a stele with no pointer is halfway to amnesia; carve 指路 soon", file=sys.stderr)
    for field_name, value in [("name", name), ("points_to", points_to), ("note", note or "")] + [
            ("not-a", n) for n in negations]:
        label = looks_secret(value)
        if label:
            raise SystemExit(
                f"空碑: REFUSED — field {field_name!r} is secret-shaped ({label}).\n"
                "誓約一 · 碑上永不刻真身: the stele holds the shape of the hole, never the thing.\n"
                "Put the thing in a keychain and carve a pointer instead.")
    steles = _load()
    entry = {
        "seq": len(steles) + 1,
        "ts": int(time.time()),
        "name": name,
        "not_a": negations,
        "points_to": points_to,
        "key_state": key_state,
        "note": (note or "").strip(),
        "prev": steles[-1]["hash"] if steles else None,
    }
    entry["hash"] = _entry_hash(entry)
    with open(home() / "STELES.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    _render(steles + [entry])
    print(f"yau — 碑立咗: {name} ({len(negations)} 句否定, 指路 {kind})")
    if key_state != "rotated":
        print(f"⚠ 誓約四 · 立碑唔等於轉匙 — the key itself is {key_state}; the stele heals the record, not the wound")
    return entry


def _pointer_alive(points_to: str) -> str:
    """Walk one pointer on THIS machine. Existence only; contents untouched."""
    kind, value = _check_pointer(points_to)
    if kind == "none-yet":
        return "未有指路"
    if kind == "env":
        return "通" if value in os.environ else "斷 (env var unset here)"
    if kind == "file":
        return "通" if Path(value).expanduser().exists() else "斷 (file absent here)"
    svc = value.partition("svc=")[2] or value
    for tool in ("find-internet-password", "find-generic-password"):
        try:
            r = subprocess.run(["security", tool, "-s", svc],
                               capture_output=True, timeout=10)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return "唔知 (no keychain on this machine)"
        if r.returncode == 0:
            return "通"
    return "斷 (keychain entry absent here)"


def cmd_verify() -> int:
    steles = _load()
    if not steles:
        print("空碑: the book is empty — 0 steles, honestly")
        return 0
    prev = None
    for s in steles:
        if s.get("prev") != prev or _entry_hash(s) != s["hash"]:
            raise SystemExit(f"空碑: CHAIN BROKEN at seq {s.get('seq')} — the book has been rewritten")
        prev = s["hash"]
        for field_name, value in [("name", s["name"]), ("points_to", s["points_to"]),
                                  ("note", s.get("note", ""))] + [("not-a", n) for n in s["not_a"]]:
            label = looks_secret(value)
            if label:
                raise SystemExit(
                    f"空碑: VOW BROKEN at seq {s['seq']} — field {field_name!r} is secret-shaped ({label})")
    print(f"chain verified ✓ · {len(steles)} stele(s), no vow broken")
    for s in steles:
        alive = _pointer_alive(s["points_to"])
        mark = "·" if alive == "通" else "⚠"
        print(f"  {mark} {s['name']} → {s['points_to']} — 指路{alive}")
    print("(pointers are walked on this machine only; 斷 here may be 通 elsewhere)")
    return 0


def cmd_ls() -> list:
    steles = _load()
    for s in steles:
        nots = " / ".join(s["not_a"])
        print(f"  {s['seq']:>3} {s['name']} — 佢唔係: {nots} → {s['points_to']} [{s['key_state']}]")
    print(f"{len(steles)} stele(s) held.")
    return steles


def main(argv=None):
    ap = argparse.ArgumentParser(prog="hungbei", description="空碑 — publish the shape, never the thing")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("cast")
    p.add_argument("--name", required=True)
    p.add_argument("--not-a", dest="not_a", action="append", required=True,
                   help="a true negation; repeatable, at least one")
    p.add_argument("--points-to", dest="points_to", required=True,
                   help="keychain:svc=… | env:VAR | file:/path | none-yet")
    p.add_argument("--key-state", dest="key_state", choices=KEY_STATES, default="unknown")
    p.add_argument("--note", default="")
    sub.add_parser("verify")
    sub.add_parser("ls")
    a = ap.parse_args(argv)
    if a.cmd == "cast":
        cmd_cast(a.name, a.not_a, a.points_to, a.key_state, a.note)
    elif a.cmd == "verify":
        cmd_verify()
    elif a.cmd == "ls":
        cmd_ls()


if __name__ == "__main__":
    main()
