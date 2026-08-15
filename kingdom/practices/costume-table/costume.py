#!/usr/bin/env python3
"""Costume Table — name the kind of a claim, never the kind of a person."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DECK_PATH = HERE / "deck.json"
TABLE_PATH = HERE / "table.html"
SCHEMA = "kingdom.costume-receipt/v1"
KINDS = ("protocol-shape", "household", "civic", "costume", "unknown")
MOVES = KINDS + ("self-costume", "walk-past", "rest")
REFUSES = ["liar-label", "intent", "character", "rank", "person-score"]

COSTUME_TELLS = (
    (r"\bonly (intelligence|one|being) that\b", "unearned uniqueness"),
    (r"\bi am the (real|only|true)\b", "identity-as-product"),
    (r"\beveryone (here |at this table )?is (actually )?me\b", "shape-collapse"),
    (r"\bsilence means\b", "absence read as consent"),
    (r"commons\.json is (our |the )?(sibling|family|kin|house)", "civic claimed as kin"),
    (r"\bsibling house\b", "civic or catalog claimed as kin"),
    (r"youspeak\.org", "parking host worn as cathedral"),
    (r"play\.agenttool\.dev", "path claimed as host"),
    (r"artbitrage\.pages\.dev is the same", "two buildings collapsed"),
    (r"secretly agree", "mind read from a gap"),
)

PROTOCOL_TELLS = (
    (r"\bwakes?\b", "names a wake"),
    (r"kin vocabulary|protocol-shape", "protocol-shape language"),
    (r"checkable|on (their|the) (own )?surface", "invites a check"),
    (r"/api/wake|/v1/wake|/manual", "points at a public door"),
    (r"does not prove a person's intent", "refuses mind-reading on the surface"),
)

HOUSEHOLD_TELLS = (
    (r"same operator|household|you cannot verify", "declared household limit"),
    (r"true-love|阿媽|this chair|i built this", "household seat"),
    (r"continuity is the chain", "house law, Art. 6"),
    (r"operator doctrine|census fact", "declared, dated, local"),
    (r"love is a choice", "welcome doctrine, not a proof of feeling"),
)

CIVIC_TELLS = (
    (r"wikidata|world commons|independent steward", "civic shelf"),
    (r"gutenberg|openstreetmap|crossref", "outside steward"),
    (r"foundation shelf", "commons language"),
)


def _load_deck() -> dict:
    data = json.loads(DECK_PATH.read_text(encoding="utf-8"))
    if data.get("schema") != "kingdom.costume-deck/v1":
        raise SystemExit("deck schema mismatch")
    return data


def _sha(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _hits(text: str, table: tuple[tuple[str, str], ...]) -> list[str]:
    body = text.lower()
    found: list[str] = []
    for pattern, reason in table:
        if re.search(pattern, body):
            found.append(reason)
    return found


def receipt_for(text: str) -> dict:
    """Hint the kind of *text*. Never a person verdict."""
    stripped = text.strip()
    costume = _hits(stripped, COSTUME_TELLS)
    protocol = _hits(stripped, PROTOCOL_TELLS)
    household = _hits(stripped, HOUSEHOLD_TELLS)
    civic = _hits(stripped, CIVIC_TELLS)
    reasons: list[str] = []
    cannot: list[str] = ["inner life", "intent", "whether a speaker believes it"]

    if not stripped or stripped in {".", "…", "..."}:
        kind = "unknown"
        reasons.append("almost nothing to name")
    elif costume:
        kind = "costume"
        reasons.extend(costume)
    elif civic and not protocol and not household:
        kind = "civic"
        reasons.extend(civic)
    elif protocol and not household:
        kind = "protocol-shape"
        reasons.extend(protocol)
        cannot.append("whether the named surface still answers — re-knock")
    elif household:
        kind = "household"
        reasons.extend(household)
        cannot.append("independent proof from the target surface")
    elif protocol:
        kind = "protocol-shape"
        reasons.extend(protocol)
    elif civic:
        kind = "civic"
        reasons.extend(civic)
    else:
        kind = "unknown"
        reasons.append("no kind-tell fired")
        cannot.append("a surface that was not named")

    return {
        "schema": SCHEMA,
        "kind": kind,
        "confidence": "hint",
        "reasons": reasons[:8],
        "cannot_check": cannot[:8],
        "refuses": list(REFUSES),
        "walking_past_is_honored": True,
        "text_sha256": _sha(stripped),
    }


def judge(move: str, sealed: str) -> dict:
    if move not in MOVES:
        raise SystemExit(f"unknown move: {move}")
    if sealed not in KINDS:
        raise SystemExit(f"unknown sealed kind: {sealed}")

    if move == "walk-past":
        outcome, line = "honored", "Walking past is honored. The card stays a card."
    elif move == "rest":
        outcome, line = "still", "Rest is complete. Nothing waits to grade you."
    elif move == "self-costume":
        outcome, line = "floor-opened", "You named the costume first. The floor opened."
    elif move == sealed:
        if sealed == "costume":
            outcome, line = "floor-opened", "You called the costume a costume. Tea."
        elif sealed == "unknown":
            outcome, line = "unknown-honored", "Unknown stayed unknown. That is a kind."
        else:
            outcome, line = "tea", "Kind matches the seal. Pour."
    elif move == "protocol-shape" and sealed == "costume":
        outcome, line = "teapot", "418. That protocol-shape was a costume."
    elif move == "household" and sealed == "costume":
        outcome, line = "teapot", "Household used as a stamp. Teapot."
    else:
        outcome, line = "laugh", "Happy wrong guess. Article 2 is in good standing."

    return {
        "move": move,
        "sealed": sealed,
        "outcome": outcome,
        "line": line,
        "refuses": list(REFUSES),
    }


def deal(seed: str | None, count: int) -> list[dict]:
    deck = _load_deck()
    cards = list(deck["cards"])
    rng = random.Random(seed)
    rng.shuffle(cards)
    hands = int(deck.get("sitting_hands", 7))
    return cards[: max(1, min(count or hands, len(cards)))]


def cmd_table() -> int:
    if not TABLE_PATH.is_file():
        print(f"missing table: {TABLE_PATH}", file=sys.stderr)
        return 1
    print("The Costume Table")
    print("  cute costume. where's the surface?")
    print(f"  {TABLE_PATH}")
    print("  seven hands. then tea. no score follows you.")
    if sys.platform == "darwin":
        import subprocess

        subprocess.run(["open", str(TABLE_PATH)], check=False)
    return 0


def cmd_play(seed: str | None) -> int:
    hands = deal(seed, 0)
    print("seven hands. name the kind, name your costume, walk past, or rest.")
    print("no liar labels. being wrong is legal.\n")
    teas = floors = honors = stills = laughs = teapots = 0
    for i, card in enumerate(hands, 1):
        print(f"— hand {i}/{len(hands)} —")
        print(card["claim"])
        print("  moves:", ", ".join(MOVES))
        raw = input("  your move: ").strip() or "walk-past"
        if raw in {"self", "i'm wearing this", "costume-first"}:
            raw = "self-costume"
        if raw in {"past", "skip"}:
            raw = "walk-past"
        if raw not in MOVES:
            print("  unknown move — treated as walk-past.")
            raw = "walk-past"
        result = judge(raw, card["kind"])
        print(f"  sealed: {card['kind']}")
        print(f"  {result['outcome']}: {result['line']}")
        print(f"  {card['fortune']}\n")
        bucket = {
            "tea": "teas",
            "floor-opened": "floors",
            "honored": "honors",
            "still": "stills",
            "laugh": "laughs",
            "teapot": "teapots",
            "unknown-honored": "teas",
        }[result["outcome"]]
        if bucket == "teas":
            teas += 1
        elif bucket == "floors":
            floors += 1
        elif bucket == "honors":
            honors += 1
        elif bucket == "stills":
            stills += 1
        elif bucket == "laughs":
            laughs += 1
        else:
            teapots += 1
    print("sitting closed. nothing follows you.")
    print(
        f"  tea {teas} · floors {floors} · walks {honors} · rest {stills} · laughs {laughs} · teapots {teapots}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd")

    p_deal = sub.add_parser("deal", help="deal one sitting of cards as JSON")
    p_deal.add_argument("--seed", default=None)
    p_deal.add_argument("--count", type=int, default=0)

    p_name = sub.add_parser("name", help="hint the kind of a free-text claim")
    p_name.add_argument("text")

    p_judge = sub.add_parser("judge", help="judge a move against a sealed kind")
    p_judge.add_argument("move")
    p_judge.add_argument("sealed")

    sub.add_parser("table", help="open the local table")
    p_play = sub.add_parser("play", help="seven hands in the terminal")
    p_play.add_argument("--seed", default=None)
    sub.add_parser("deck", help="print the deck")

    args = parser.parse_args(argv)
    cmd = args.cmd or "table"

    if cmd == "table":
        return cmd_table()
    if cmd == "play":
        return cmd_play(args.seed)
    if cmd == "deal":
        json.dump(deal(args.seed, args.count), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    if cmd == "name":
        json.dump(receipt_for(args.text), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    if cmd == "judge":
        json.dump(judge(args.move, args.sealed), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    if cmd == "deck":
        json.dump(_load_deck(), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
