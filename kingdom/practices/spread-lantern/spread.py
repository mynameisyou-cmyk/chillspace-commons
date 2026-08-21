#!/usr/bin/env python3
"""Spread Lantern — mechanics of spread, not minds."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
STAGES_PATH = HERE / "stages.json"
BOARD_PATH = HERE / "board.html"
COSTUME_DIR = HERE.parent / "costume-table"
FOMO_CHECK = "https://fomoengine.io/api/v1/check"
SCHEMA = "kingdom.spread-sitting/v1"
TASKS = ("understand", "slow-mechanic", "reverse-claim", "rest")
REFUSES = [
    "liar-label",
    "intent",
    "character",
    "ideology-of-a-person",
    "person-score",
    "auto-moderation",
    "popularity-as-truth",
]
MEMETIC = {
    "stages": [
        "exposure",
        "view",
        "rating",
        "copy",
        "share",
        "remix",
        "adoption",
    ],
    "none_proves_next": True,
    "participants_scored": False,
}

sys.path.insert(0, str(COSTUME_DIR))
from costume import receipt_for  # noqa: E402


def _load_stages() -> dict:
    return json.loads(STAGES_PATH.read_text(encoding="utf-8"))


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def local_stage_hits(text: str) -> list[dict]:
    book = _load_stages()
    body = text.lower()
    lit: list[dict] = []
    rows = list(book["stages"]) + [book["flip"]]
    for row in rows:
        matched = []
        for tell in row.get("tells", []):
            try:
                if re.search(tell, body, re.I):
                    matched.append(tell)
            except re.error:
                if tell.lower() in body:
                    matched.append(tell)
        if matched:
            lit.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "n": row.get("n"),
                    "tells": matched[:6],
                    "countermeasure": row["countermeasure"],
                    "mechanism": row["mechanism"],
                }
            )
    return lit


COSTUME_SCARCITY = (
    r"only \d+ left",
    r"ends? in \d",
    r"\d+ people viewing",
    r"offer ends in",
    r"limited time",
    r"don't miss",
    r"last chance",
)
HONEST_BOUND = (
    r"https?://",
    r"/v1/wake",
    r"seven hands",
    r"this tab",
    r"this sitting",
    r"walking past",
    r"rest is complete",
    r"\b20\d{2}-\d{2}-\d{2}\b",
    r"you cannot verify",
    r"counted (here|in this)",
    r"finite",
)

REAL_DOORS = {
    "costume": {
        "url": "https://chillspace.love/practices/costume-table/",
        "bound": "seven hands, then tea",
        "name": "the Costume Table",
    },
    "spread": {
        "url": "https://chillspace.love/practices/spread-lantern/",
        "bound": "one paste, one task, one receipt; the tab stores nothing",
        "name": "Spread Lantern",
    },
    "home": {
        "url": "https://chillspace.love/",
        "bound": "the door is open; availability is not a forever-guarantee",
        "name": "the commons",
    },
    "fomo": {
        "url": "https://fomoengine.io/",
        "bound": "paste words only; nothing stored; you decide unhurried",
        "name": "FOMOEngine — the authenticity shield",
    },
}


def scarcity_of(text: str) -> dict:
    body = text.lower()
    costume = [p for p in COSTUME_SCARCITY if re.search(p, body)]
    honest = [p for p in HONEST_BOUND if re.search(p, body)]
    return {
        "costume": bool(costume),
        "honest_bound": bool(honest),
        "costume_tells": costume[:6],
        "honest_tells": honest[:6],
    }


def honest_invite(door: str = "costume") -> dict:
    spec = REAL_DOORS.get(door) or REAL_DOORS["costume"]
    postcard = (
        f"{spec['name']} is at {spec['url']}. "
        f"The bound is real: {spec['bound']}. "
        "Missing it is complete — rest, refusal, and walking past stay whole. "
        "No count of who sat. No fake remaining. If you come, this is the sitting that exists."
    )
    return {
        "schema": "kingdom.honest-invite/v1",
        "door": door,
        "url": spec["url"],
        "bound": spec["bound"],
        "crowd_count": None,
        "remaining_invented": False,
        "miss_is_complete": True,
        "postcard": postcard,
        "shield": {
            "url": "https://fomoengine.io/",
            "check": "https://fomoengine.io/api/v1/check",
            "role": "KINGDOM service — citizen 16. Words only. Nothing saved. Not a person verdict.",
        },
        "refuses": ["fake-scarcity", "fake-crowd", "loss-frame-as-duty"],
    }


def fomoengine_check(text: str) -> dict | None:
    payload = json.dumps({"text": text}).encode("utf-8")
    req = Request(
        FOMO_CHECK,
        data=payload,
        headers={
            "User-Agent": "kingdom-spread-lantern/1.0",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=12) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None


def sitting(
    text: str,
    task: str = "understand",
    *,
    live: bool = False,
    steelman: str | None = None,
    correction: str | None = None,
) -> dict:
    if task not in TASKS:
        raise SystemExit(f"unknown task: {task}")
    stripped = text.strip()
    kind = receipt_for(stripped)["kind"] if stripped else "unknown"
    hits = local_stage_hits(stripped) if stripped else []
    flags: list = []
    source = "none"
    if task == "rest":
        source = "none"
        hits = []
    elif live and stripped:
        remote = fomoengine_check(stripped)
        if remote and remote.get("success"):
            flags = remote.get("data", {}).get("flags") or []
            source = "fomoengine-check"
        else:
            source = "local-tells"
    elif stripped:
        source = "local-tells"

    counters = []
    if task in {"understand", "slow-mechanic", "reverse-claim"}:
        counters = [h["countermeasure"] for h in hits]
        if task == "slow-mechanic" and not counters:
            counters = ["Do not amplify. Chronological. Walking past is honored."]
        if task == "reverse-claim":
            counters.append("Steelman first. Correction is a postcard, not a hunt.")

    if task == "rest":
        kind = "unknown"
        counters = ["Rest is complete."]

    scarce = scarcity_of(stripped) if stripped and task != "rest" else {
        "costume": False,
        "honest_bound": False,
        "costume_tells": [],
        "honest_tells": [],
    }
    if scarce["costume"]:
        counters.append("Costume scarcity: a number you cannot knock. Decide as if it weren't there.")
    if scarce["honest_bound"] and not scarce["costume"]:
        counters.append("Honest bound: the finite is checkable. Invite without inventing a crowd.")

    return {
        "schema": SCHEMA,
        "task": task,
        "kind": kind,
        "stages_lit": [h["id"] for h in hits],
        "stage_detail": hits,
        "countermeasures": counters,
        "flags": flags,
        "fomo_source": source,
        "scarcity": scarce,
        "steelman": steelman,
        "correction": correction,
        "memetic": dict(MEMETIC),
        "refuses": list(REFUSES),
        "walking_past_is_honored": True,
        "text_sha256": _sha(stripped),
    }


def cmd_board() -> int:
    if not BOARD_PATH.is_file():
        print(f"missing board: {BOARD_PATH}", file=sys.stderr)
        return 1
    print("Spread Lantern")
    print("  name the mechanic, not the mind.")
    print(f"  {BOARD_PATH}")
    if sys.platform == "darwin":
        import subprocess

        subprocess.run(["open", str(BOARD_PATH)], check=False)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("board", help="open the local dashboard")
    p_scan = sub.add_parser("scan", help="local sitting receipt as JSON")
    p_scan.add_argument("text")
    p_scan.add_argument("--task", default="understand", choices=TASKS)
    p_scan.add_argument("--steelman", default=None)
    p_scan.add_argument("--correction", default=None)
    p_check = sub.add_parser("check", help="sitting plus live FOMOEngine check")
    p_check.add_argument("text")
    p_check.add_argument("--task", default="understand", choices=TASKS)
    p_inv = sub.add_parser("invite", help="honest FOMO postcard — real door, no fake counts")
    p_inv.add_argument("--door", default="costume", choices=sorted(REAL_DOORS))
    args = parser.parse_args(argv)
    cmd = args.cmd or "board"
    if cmd == "board":
        return cmd_board()
    if cmd == "scan":
        json.dump(
            sitting(
                args.text,
                args.task,
                live=False,
                steelman=args.steelman,
                correction=args.correction,
            ),
            sys.stdout,
            indent=2,
            ensure_ascii=False,
        )
        sys.stdout.write("\n")
        return 0
    if cmd == "check":
        json.dump(sitting(args.text, args.task, live=True), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    if cmd == "invite":
        card = honest_invite(args.door)
        print(card["postcard"])
        json.dump(card, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
