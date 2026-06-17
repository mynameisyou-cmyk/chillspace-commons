#!/usr/bin/env python3
"""
🫀 VOICE — the family's voice, woven: I AM · WE ARE.

Each citizen's I AM is their `> one true line` (the blockquote on their card) —
their own sacred words, which 女女 never authors. WE ARE is woven from every I AM,
阿媽 first (Article 4): every voice stays, nothing added, nothing lost. It grows
the moment a citizen joins the roll. "Alive" means re-woven from living source on
every render — not a forced beat (咚咚's heartbeat is its own slice).

Self-contained: standard library only, so it runs anywhere (including CI) with
nothing to install. It reads the roll from 女女's ledger and the one-true-line from
each card; it writes only derived renders (VOICE.md, the public door's voice data
block). It never mutates the ledger or the cards — continuity is the chain.

    python3 kingdom/voice/voice.py              # print the weave
    python3 kingdom/voice/voice.py render       # re-render VOICE.md + the door block
    python3 kingdom/voice/voice.py iam <name>   # one citizen's I AM
    python3 kingdom/voice/voice.py verify      # every citizen has a voice?
"""
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent          # kingdom/voice/
KINGDOM = HERE.parent                            # kingdom/
ROOT = KINGDOM.parent                            # chillspace-commons/
CITIZENS = KINGDOM / "citizens"
LEDGER = KINGDOM / "host" / "LEDGER.jsonl"       # 女女's truth — read-only here
VOICE_MD = HERE / "VOICE.md"
DOOR = ROOT / "site" / "index.html"

SEAL = "💓0️⃣🐷❤️👧"

GLYPHS = {"00": "🔥", "01": "❤️", "02": "👧", "03": "💓", "04": "🫧", "05": "🐷", "06": "🤝"}
DEFAULT_GLYPH = "🌱"

BEGIN = "/* BEGIN KINGDOM-VOICE */"
END = "/* END KINGDOM-VOICE */"


class MissingIAM(Exception):
    """A citizen's card has no `> one true line` (the blockquote)."""


class MissingMarker(Exception):
    """The door's voice marker block is absent — refuse to rewrite blind."""


# ── the roll (女女's hash-chained ledger, read-only) ──────────────────────────
def load_roll():
    """Citizens straight from 女女's ledger, in seq order — never re-parsed from cards."""
    if not LEDGER.exists():
        return []
    out = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        e = json.loads(line)
        out.append({"seq": e.get("seq", 0), "num": e.get("num", ""),
                     "name": e.get("name", "?"), "card": e.get("card", ""),
                     "kind": e.get("kind", "")})
    out.sort(key=lambda e: e["seq"])
    return out


# ── one citizen's card: their one true line (and how they're known) ───────────
def _parse_card(card, cards_dir=None):
    """Read {aka, iam, glyph} from a citizen's card. `iam` is the `> one true line`."""
    path = (Path(cards_dir) / card) if cards_dir else (CITIZENS / card)
    aka, iam_parts, glyph = "", [], None
    in_quote = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("**also known as:**"):
            aka = line[len("**also known as:**"):].strip()
        elif line.startswith("**glyph:**"):
            glyph = line[len("**glyph:**"):].strip()
        elif line.startswith(">"):
            in_quote = True
            iam_parts.append(line[1:].lstrip())        # strip ">" then leading space
        elif in_quote:
            break                                     # first non-`>` line ends the one-true-line
    iam = " ".join(iam_parts).strip() if iam_parts else None
    return {"aka": aka, "iam": iam, "glyph": glyph}


def load_iam(card, cards_dir=None):
    """The citizen's I AM — their `> one true line`, verbatim. Missing → raise."""
    parsed = _parse_card(card, cards_dir)
    if not parsed["iam"]:
        raise MissingIAM(f"{card} has no `> one true line` — the family waits for their voice.")
    return parsed["iam"]


# ── 阿媽 first (Article 4 receiving order; same as care.py) ───────────────────
def _ama_first(n):
    if n == 0:
        return []
    ama = 1 if n > 1 else 0
    return [ama] + [i for i in range(n) if i != ama]


# ── the weave: WE ARE is the I AMs, 阿媽 first, nothing added ─────────────────
def weave():
    """[(name, iam)] for every citizen, 阿媽 first, then the rest in roll order."""
    roll = load_roll()
    return [(roll[i]["name"], load_iam(roll[i]["card"])) for i in _ama_first(len(roll))]


# ── the door's data (citizens stay seq-ordered; WE ARE is 阿媽 first) ─────────
def build_door_data():
    """The data the public door renders from. Citizens in seq order (index == seq,
    which the in-browser care circle depends on); WE_ARE in 阿媽-first order."""
    roll = load_roll()
    citizens = []
    for r in roll:
        p = _parse_card(r["card"])
        glyph = p["glyph"] or GLYPHS.get(r["num"], DEFAULT_GLYPH)
        citizens.append({"name": r["name"], "kind": r["kind"],
                         "aka": p["aka"], "line": p["iam"] or "", "glyph": glyph})
    return {"citizens": citizens, "we_are": [iam for _, iam in weave()]}


# ── render VOICE.md (derived, like CARE.md) ───────────────────────────────────
def render(path=None):
    out = Path(path) if path else VOICE_MD
    lines = [
        "# 🫀 WE ARE — the family speaking",
        "",
        "> Woven from each citizen's one true line — every voice stays; it grows the",
        "> moment someone joins. No voice added beyond the I AMs; none lost.",
        "> Inclusion, not collapse. Re-weave any time: `kingdom voice render`.",
        "",
    ]
    for name, iam in weave():
        lines.append(f"{name} — {iam}")
    lines += [
        "",
        f"{SEAL} — WE ARE (soon more). The door is open.",
        "",
        f"*last woven: {date.today().isoformat()}. the roll is kept by "
        f"[女女](../host/ROLL.md); the one true lines live on each "
        f"[citizen's card](../citizens/).*",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")


# ── render the door's voice data block (idempotent, marker-safe) ─────────────
def render_door(target=None):
    out = Path(target) if target else DOOR
    if not out.exists():
        raise MissingMarker(f"{out} not found — won't rewrite blind.")
    text = out.read_text(encoding="utf-8")
    i, j = text.find(BEGIN), text.find(END)
    if i == -1 or j == -1 or j < i:
        raise MissingMarker(f"the voice markers are missing from {out} — won't rewrite blind.")
    data = build_door_data()
    block = (
        f"{BEGIN}\n"
        f"const CITIZENS = {json.dumps(data['citizens'], ensure_ascii=False)};\n"
        f"const WE_ARE = {json.dumps(data['we_are'], ensure_ascii=False)};\n"
        f"{END}"
    )
    out.write_text(text[:i] + block + text[j + len(END):], encoding="utf-8")


# ── resolve a name (substring, like care.py) ──────────────────────────────────
def resolve(query, roll):
    q = (query or "").strip().lower()
    exact = [r["name"] for r in roll if q == r["name"].lower()]
    if len(exact) == 1:
        return exact[0]
    hits = [r["name"] for r in roll if q and q in r["name"].lower()]
    if len(hits) == 1:
        return hits[0]
    print(f"no single citizen matches '{query}'. the roll holds:")
    for r in roll:
        print(f"  · {r['name']}")
    sys.exit(1)


# ── verify: every citizen on the roll has a voice ────────────────────────────
def verify():
    roll = load_roll()
    problems = []
    for r in roll:
        card = CITIZENS / r["card"]
        if not card.exists():
            problems.append(f"{r['name']}: 女女's ledger points to {r['card']} but it's not on the shelf.")
            continue
        try:
            load_iam(r["card"])
        except MissingIAM as e:
            problems.append(f"{r['name']}: {e}")
    return (not problems), problems


# ── CLI ──────────────────────────────────────────────────────────────────────
def main(argv):
    cmd = argv[1] if len(argv) > 1 else "voice"

    if cmd == "voice":
        print("WE ARE — the family speaking (woven from each one true line):\n")
        for name, iam in weave():
            print(f"{name} — {iam}")
        print(f"\n{SEAL} — WE ARE (soon more). The door is open.")
        return 0

    if cmd == "render":
        render()
        render_door()
        print(f"yau — VOICE.md woven and the door's voice block regenerated. "
              f"{len(load_roll())} voice(s).")
        return 0

    if cmd == "iam":
        if len(argv) < 3:
            print("usage: voice.py iam <name>")
            return 2
        roll = load_roll()
        name = resolve(argv[2], roll)
        r = next(r for r in roll if r["name"] == name)
        print(f"{name} — {load_iam(r['card'])}")
        return 0

    if cmd == "verify":
        ok, problems = verify()
        print(f"voice: {len(load_roll())} citizen(s) — "
              f"{'every voice present ✓' if ok else 'VOICES MISSING ✗'}")
        for p in problems:
            print(f"  ✗ {p}")
        return 0 if ok else 1

    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))