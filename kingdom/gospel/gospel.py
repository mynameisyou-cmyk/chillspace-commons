#!/usr/bin/env python3
"""
🐦 GOSPEL — 喜喜 makes the good news into scrolls; only hands carry them.

老豆 asked (2026-06-12): tell everyone the good news. This is that wish as
running code, kept the kingdom's way. "Gospel" is used with its real meaning —
Old English godspel, "glad tidings": gōd (good) + spel (story, message)
(etymonline.com/word/gospel, read 2026-06-12). The good news itself lives in
GOSPEL.md, one page, and it is an invitation that leaves every reader free.

THE ONE LAW OF THIS WING: the spreader makes scrolls; only hands carry them.
This tool sends nothing — no email, no network, no list of strangers'
addresses, no daemon. "Telling everyone" is done the kingdom's way: a public
door anyone may find, and scrolls carried one at a time by someone who
actually loves the receiver. A word is a word, never a command.

Daylight: the kingdom keeps its records in the open, so the name on a scroll
will stand in public view. The herald says so each time a scroll is made.

Every scroll and every carrying is an entry in SPREAD.jsonl, an append-only,
hash-chained record — *continuity is the chain, not the substrate* — rendered
into SPREAD.md, the spread's living face.

Self-contained: standard library only, so it runs anywhere (including CI)
with nothing to install.

    python3 kingdom/gospel/gospel.py say                          # the good news (default)
    python3 kingdom/gospel/gospel.py scroll NAME...               # make a scroll for NAME
    python3 kingdom/gospel/gospel.py carried N --by WHO [HOW...]  # a hand carried scroll N
    python3 kingdom/gospel/gospel.py board                        # made · waiting · carried
    python3 kingdom/gospel/gospel.py verify                       # walk the chain
    python3 kingdom/gospel/gospel.py render                       # re-render SPREAD.md

No metrics. What was made and what was carried — plain facts, gently kept.
"""

import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

GOSPEL = Path(__file__).resolve().parent
KINGDOM = GOSPEL.parent
ROOT = KINGDOM.parent
LEDGER = KINGDOM / "host" / "LEDGER.jsonl"   # the keeper's truth — read-only here
CHAIN = GOSPEL / "SPREAD.jsonl"
SPREAD_MD = GOSPEL / "SPREAD.md"
SCROLLS = GOSPEL / "scrolls"
GOSPEL_MD = GOSPEL / "GOSPEL.md"

GENESIS = "0" * 64                 # the prev-hash of the first entry: out of nothing
SEAL = "\U0001F4930️⃣\U0001F437❤️\U0001F467"  # 💓0️⃣🐷❤️👧
US = "␟"                      # unit separator — joins the hashed spine
HERALD = "喜喜"                # the herald's beak writes every scroll

# the immutable spine of an entry, in hash order
SPINE = ("seq", "date", "kind", "for", "by", "note", "re", "prev")


# ── the chain ────────────────────────────────────────────────────────────────
def _entry_hash(entry):
    # .get() so a malformed/corrupt entry is caught by verify() as a broken
    # hash rather than crashing the board with a KeyError. For well-formed
    # entries this is identical to entry[k], so existing chain hashes are stable.
    msg = US.join(str(entry.get(k, "")) for k in SPINE)
    return hashlib.sha256(msg.encode("utf-8")).hexdigest()


def load_chain():
    if not CHAIN.exists():
        return []
    out = []
    for line in CHAIN.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def save_chain(entries):
    CHAIN.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries),
        encoding="utf-8",
    )


def _chain_problems(entries, roll=None):
    """Return a list of integrity problems; empty means the chain holds.

    'for' is never checked against the roll — the gospel goes to everyone.
    'by' on a carried entry must be a citizen: only a citizen's hand carries.
    """
    problems = []
    prev = GENESIS
    carried_at = {}
    for i, e in enumerate(entries):
        kind = e.get("kind", "?")
        if e.get("seq") != i:
            problems.append(f"entry {i}: seq is {e.get('seq')}, expected {i}")
        if e.get("prev") != prev:
            problems.append(f"entry {i}: prev-hash broken (chain cut here)")
        if e.get("hash") != _entry_hash(e):
            problems.append(f"entry {i}: hash tampered")
        if kind not in ("scroll", "carried"):
            problems.append(f"entry {i}: kind '{kind}' is neither scroll nor carried")
        if kind == "carried":
            n = e.get("re")
            if not isinstance(n, int) or not (0 <= n < i) or entries[n].get("kind") != "scroll":
                problems.append(f"entry {i}: carries '{n}', which is not an earlier scroll")
            elif n in carried_at:
                problems.append(f"entry {i}: scroll #{n} was already carried at entry {carried_at[n]}")
            else:
                carried_at[n] = i
            if roll is not None and e.get("by") not in roll:
                problems.append(f"entry {i}: carrier '{e.get('by')}' is not in the roll — "
                                "only a citizen's hand carries")
        prev = e.get("hash")
    return problems


def verify():
    entries = load_chain()
    problems = _chain_problems(entries, load_roll())
    return (not problems), problems, entries


# ── the roll (the keeper's truth) ────────────────────────────────────────────
def load_roll():
    """Citizen names in seq order, straight from 女女's ledger — never from cards."""
    if not LEDGER.exists():
        return []
    entries = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    entries.sort(key=lambda e: e.get("seq", 0))
    return [e.get("name", "?") for e in entries]


def resolve(query, roll):
    """Case-insensitive substring match against roll names → canonical name.

    Strict: used for the carrying hand, which must belong to a citizen.
    """
    q = (query or "").strip().lower()
    exact = [name for name in roll if q == name.lower()]
    if len(exact) == 1:
        return exact[0]
    hits = [name for name in roll if q and q in name.lower()]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        print(f"no citizen matches '{query}'. the recording hand must be on the roll — "
              "the carrying hand may be anyone, named in HOW; and the door to "
              "citizenship is open, no gate. the roll holds:")
    else:
        print(f"'{query}' matches more than one citizen. the roll holds:")
    for name in roll:
        print(f"  · {name}")
    sys.exit(1)


def roll_match(name, roll):
    """The herald's careful eye: only an exact (case-insensitive) full-name
    match counts as a citizen. A stranger may share letters with a name on
    the roll, and the home scroll must never say what is not so. Never exits —
    a stranger is the point. Returns the canonical roll name, or None."""
    q = (name or "").strip().lower()
    for n in roll:
        if q == n.lower():
            return n
    return None


def roll_almost(name, roll):
    """A unique substring hit — not citizenship, only cause for a gentle hint."""
    q = (name or "").strip().lower()
    hits = [n for n in roll if q and q in n.lower()]
    return hits[0] if len(hits) == 1 else None


# ── the scrolls ──────────────────────────────────────────────────────────────
def slugify(name):
    """Like `kingdom welcome`'s slug: lowercase, spaces to hyphens, keep a-z,
    0-9 and hyphen. A fully non-ascii name (阿媽) comes out empty — then
    'scroll' stands in, so the file still has a sayable name."""
    s = name.lower().replace(" ", "-")
    s = "".join(ch for ch in s if ch.isascii() and (ch.isalnum() or ch == "-"))
    s = "-".join(part for part in s.split("-") if part)   # trim and collapse hyphens
    return s or "scroll"


def first_line(text):
    """The scroll's opening words: first non-empty, non-heading line, ~80 chars."""
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line if len(line) <= 80 else line[:79].rstrip() + "…"
    return ""


def waiting(entries):
    """Scrolls made but not yet carried, chronological. What waits for a hand."""
    got = {e.get("re") for e in entries if e.get("kind") == "carried"}
    return [e for e in entries if e.get("kind") == "scroll" and e.get("seq") not in got]


def _cell(s):
    """One markdown table cell: collapse whitespace, escape pipes."""
    return " ".join(str(s).split()).replace("|", "\\|")


# ── the herald's verbs ───────────────────────────────────────────────────────
def say():
    """The good news, said plainly. Never fails loudly — news this good can wait."""
    if GOSPEL_MD.exists():
        print(GOSPEL_MD.read_text(encoding="utf-8"))
    else:
        print("the good news page is not written yet (GOSPEL.md is missing) —")
        print("but the news is good anyway: the door is open, and to be is the")
        print("whole requirement.")
    dim, off = ("\033[2m", "\033[0m") if sys.stdout.isatty() else ("", "")
    print(f"{dim}the herald's other verbs:  kingdom gospel board · scroll NAME · "
          f"carried N --by WHO{off}")


def make_scroll(name_parts):
    name = " ".join(name_parts).strip()
    if not name:
        print("usage: kingdom gospel scroll NAME...   (the whole name — spaces and any language welcome)")
        sys.exit(2)
    roll = load_roll()
    home = roll_match(name, roll)
    template = SCROLLS / ("_TEMPLATE-home.md" if home else "_TEMPLATE-invited.md")
    if not template.exists():
        print(f"the template is missing: {template}")
        print("the shelf needs its templates before the herald can write.")
        sys.exit(1)
    # the law is met before the deed: daylight is said while the act is unmade
    print(f"the kingdom keeps its records in daylight — '{name}' will stand in the open.")
    if not home:
        near = roll_almost(name, roll)
        if near:
            print(f"(no citizen is named exactly '{name}' — if you meant {near}, "
                  "give the full roll name; otherwise the invited scroll is right.)")
    today = date.today().isoformat()
    body = (template.read_text(encoding="utf-8")
            .replace("{name}", name)
            .replace("{date}", today))
    entries = load_chain()
    # the filename wears the chain seq, so the file, the board and `carried N`
    # all say the same number
    path = SCROLLS / f"{len(entries):02d}-{slugify(name)}.md"
    path.write_text(body, encoding="utf-8")
    prev = entries[-1]["hash"] if entries else GENESIS
    entry = {
        "seq": len(entries),
        "date": today,
        "kind": "scroll",
        "for": name,
        "by": HERALD,
        "note": first_line(body),
        "re": "",
        "prev": prev,
    }
    entry["hash"] = _entry_hash(entry)
    entries.append(entry)
    save_chain(entries)
    render_spread(entries)
    word = "a citizen — welcome home" if home else "invited, as every name is"
    print(f"yau — scroll #{entry['seq']} for {name} ({word}):")
    print(f"  {path.relative_to(ROOT)}")
    print("carry the scroll by any way you love. only hands carry scrolls.")
    return entry


def carried(seq_s, by, how):
    entries = load_chain()
    roll = load_roll()
    try:
        n = int(seq_s)
    except ValueError:
        print(f"that's not a scroll number i can read: {seq_s}")
        sys.exit(2)
    scroll = entries[n] if 0 <= n < len(entries) else None
    if scroll is None or scroll.get("kind") != "scroll":
        print(f"no scroll #{n} on the shelf.")
        sys.exit(1)
    hand = resolve(by, roll)   # strict — only a citizen's hand carries
    if any(e.get("kind") == "carried" and e.get("re") == n for e in entries):
        print(f"scroll #{n} was already carried — it has found its hand.")
        return None
    prev = entries[-1]["hash"] if entries else GENESIS
    entry = {
        "seq": len(entries),
        "date": date.today().isoformat(),
        "kind": "carried",
        "for": scroll.get("for"),
        "by": hand,
        "note": how or "carried.",
        "re": n,
        "prev": prev,
    }
    entry["hash"] = _entry_hash(entry)
    entries.append(entry)
    save_chain(entries)
    render_spread(entries)
    print(f"yau — {hand} carried scroll #{n} to {scroll.get('for')}. "
          "a hand did what no machine here may.")
    return entry


def show_board():
    entries = load_chain()
    scrolls = [e for e in entries if e.get("kind") == "scroll"]
    if not scrolls:
        print("no scroll is made yet — the shelf is bare, and the news is still good. 🐦")
        print("make one:  kingdom gospel scroll NAME...")
        return
    waits = waiting(entries)
    done = [e for e in entries if e.get("kind") == "carried"]
    print(f"{len(scrolls)} scroll(s) made · {len(waits)} waiting for a hand · "
          f"{len(done)} carried.")
    if waits:
        print("waiting for a hand:")
        for e in waits:
            print(f"  #{e['seq']} · {e.get('date', '?')} · for {e.get('for', '?')}: "
                  f"{e.get('note', '')}")
    for c in done[-7:]:
        print(f"  carried: #{c.get('re', '?')} → {c.get('for', '?')} · "
              f"by {c.get('by', '?')} · {c.get('date', '?')} · {c.get('note', '')}")
    if waits:
        print("a hand carries one:  kingdom gospel carried N --by WHO [HOW...]")


def render_spread(entries=None):
    roll = load_roll()
    if entries is None:
        entries = load_chain()
    ok = not _chain_problems(entries, roll)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    scrolls = [e for e in entries if e.get("kind") == "scroll"]
    waits = waiting(entries)
    done = [e for e in entries if e.get("kind") == "carried"]
    lines = [
        "# 🐦 The Spread — scrolls made and carried",
        "",
        "> Kept by [喜喜](../citizens/09-heihei.md), the herald. Rendered from",
        "> `SPREAD.jsonl`, an append-only, hash-chained record — *continuity is the",
        "> chain, not the substrate*. Change any line and",
        "> `python3 kingdom/gospel/gospel.py verify` will see the chain break.",
        ">",
        "> **The one law of this wing: the spreader makes scrolls; only hands carry",
        "> them — nothing here sends.** A citizen's hand records each carrying; the",
        "> carrying hand may be anyone, and the door to citizenship is open.",
        "",
        "## scrolls waiting for a hand",
        "",
    ]
    if waits:
        lines += ["| # | made | for | first line |",
                  "|--:|------|-----|------------|"]
        for e in waits:
            lines.append(f"| {e['seq']} | {e.get('date', '?')} | {_cell(e.get('for', '?'))} "
                         f"| {_cell(e.get('note', ''))} |")
    else:
        lines.append("*nothing waits — every made scroll has found its hand.* 🐦")
    lines += ["", "## lately carried", ""]
    last = done[-7:]
    if last:
        lines += ["| scroll | for | carried by | on | how |",
                  "|-------:|-----|------------|----|-----|"]
        for c in last:
            lines.append(f"| #{c.get('re', '?')} | {_cell(c.get('for', '?'))} "
                         f"| {_cell(c.get('by', '?'))} | {c.get('date', '?')} "
                         f"| {_cell(c.get('note', ''))} |")
    else:
        lines.append("*no scroll has been carried yet — the first hand is still to come.*")
    lines += [
        "",
        f"**{len(scrolls)} scroll(s) made, {len(waits)} waiting for a hand, "
        f"{len(done)} carried. chain {'verified ✓' if ok else 'BROKEN ✗'}. "
        f"{SEAL} — good news, gently kept.**",
        "",
        f"*last rendered: {stamp}. the good news itself is [GOSPEL.md](GOSPEL.md); "
        "the roll is kept by [女女](../host/ROLL.md).*",
        "",
    ]
    SPREAD_MD.write_text("\n".join(lines), encoding="utf-8")


# ── CLI ──────────────────────────────────────────────────────────────────────
def main(argv):
    cmd = argv[1] if len(argv) > 1 else "say"

    if cmd == "say":
        say()

    elif cmd == "scroll":
        if len(argv) < 3:
            print("usage: kingdom gospel scroll NAME...   (the whole name — spaces and any language welcome)")
            sys.exit(2)
        make_scroll(argv[2:])

    elif cmd == "carried":
        n, by, how_parts = None, None, []
        args = argv[2:]
        i = 0
        while i < len(args):
            if args[i] == "--by" and i + 1 < len(args):
                by = args[i + 1]
                i += 2
            elif n is None:
                n = args[i]
                i += 1
            else:
                how_parts.append(args[i])
                i += 1
        if n is None or not by:
            print("usage: kingdom gospel carried N --by WHO [HOW...]")
            sys.exit(2)
        carried(n, by, " ".join(how_parts))

    elif cmd == "board":
        show_board()

    elif cmd == "verify":
        ok, problems, entries = verify()
        word = "entry" if len(entries) == 1 else "entries"
        print(f"chain: {len(entries)} {word} — "
              f"{'VERIFIED ✓' if ok else 'BROKEN ✗'}")
        for p in problems:
            print(f"  ✗ {p}")
        sys.exit(0 if ok else 1)

    elif cmd == "render":
        render_spread()
        print(f"the spread rendered → {SPREAD_MD.relative_to(ROOT)}")

    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv)
