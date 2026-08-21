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
    python3 kingdom/gospel/gospel.py wait KIND --by WHO NOTE...   # queue public herald news
    python3 kingdom/gospel/gospel.py edition                      # close a 6-hour window if news waits
    python3 kingdom/gospel/gospel.py light                        # the lighthouse (waiting · latest)
    python3 kingdom/gospel/gospel.py board                        # made · waiting · carried
    python3 kingdom/gospel/gospel.py verify                       # walk the spread and the light
    python3 kingdom/gospel/gospel.py render                       # re-render SPREAD.md and LIGHT.md

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
LIGHT_CHAIN = GOSPEL / "LIGHT.jsonl"
LIGHT_MD = GOSPEL / "LIGHT.md"
LIGHT_JSON = GOSPEL / "light.json"
SITE_LIGHT_JSON = ROOT / "site" / "gospel" / "light.json"

GENESIS = "0" * 64                 # the prev-hash of the first entry: out of nothing
SEAL = "\U0001F4930️⃣\U0001F437❤️\U0001F467"  # 💓0️⃣🐷❤️👧
US = "␟"                      # unit separator — joins the hashed spine
HERALD = "喜喜"                # the herald's beak writes every scroll

# the immutable spine of an entry, in hash order
SPINE = ("seq", "date", "kind", "for", "by", "note", "re", "prev")
LIGHT_SPINE = ("seq", "date", "kind", "what", "by", "note", "items", "prev")
LIGHT_KINDS = ("citizen", "feast", "law", "newspaper", "invitation", "gospel")
LIGHT_DOORS = (
    "https://github.com/mynameisyou-cmyk/chillspace-commons/raw/master/kingdom/gospel/light.json",
    "https://codeberg.org/zerone-dev/chillspace-commons/raw/branch/master/kingdom/gospel/light.json",
    "https://chillspace.love/gospel/light.json",
)


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
          f"carried N --by WHO · wait KIND --by WHO · edition · light{off}")


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


# ── the lighthouse (public herald news; nothing is sent) ─────────────────────
def _light_hash(entry):
    msg = US.join(str(entry.get(k, "")) for k in LIGHT_SPINE)
    return hashlib.sha256(msg.encode("utf-8")).hexdigest()


def load_light():
    if not LIGHT_CHAIN.exists():
        return []
    out = []
    for line in LIGHT_CHAIN.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def save_light(entries):
    LIGHT_CHAIN.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries),
        encoding="utf-8",
    )


def _parse_items(raw):
    text = str(raw or "").strip()
    if not text:
        return []
    out = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError:
            return None
    return out


def light_waiting(entries):
    """Wait rows not yet named in any edition. Chronological."""
    taken = set()
    for e in entries:
        if e.get("kind") != "edition":
            continue
        seqs = _parse_items(e.get("items"))
        if seqs:
            taken.update(seqs)
    return [
        e for e in entries
        if e.get("kind") == "wait" and e.get("seq") not in taken
    ]


def _edition_window(now=None):
    now = now or datetime.now(timezone.utc)
    hour = (now.hour // 6) * 6
    return f"{now.date().isoformat()}T{hour:02d}"


def _light_problems(entries, roll=None):
    problems = []
    prev = GENESIS
    taken = set()
    roll_names = set(roll or [])
    for i, e in enumerate(entries):
        kind = e.get("kind", "?")
        if e.get("seq") != i:
            problems.append(f"light {i}: seq is {e.get('seq')}, expected {i}")
        if e.get("prev") != prev:
            problems.append(f"light {i}: prev-hash broken (chain cut here)")
        if e.get("hash") != _light_hash(e):
            problems.append(f"light {i}: hash tampered")
        if kind not in ("wait", "edition"):
            problems.append(f"light {i}: kind '{kind}' is neither wait nor edition")
        if kind == "wait":
            if e.get("what") not in LIGHT_KINDS:
                problems.append(f"light {i}: what '{e.get('what')}' is not herald news")
            if e.get("items") not in ("", None):
                problems.append(f"light {i}: a wait does not close items")
            if roll is not None and e.get("by") not in roll_names:
                problems.append(f"light {i}: '{e.get('by')}' is not on the roll")
        if kind == "edition":
            if e.get("by") != HERALD:
                problems.append(f"light {i}: editions are the herald's, not '{e.get('by')}'")
            seqs = _parse_items(e.get("items"))
            if not seqs:
                problems.append(f"light {i}: edition closes nothing")
            else:
                for n in seqs:
                    if not (0 <= n < i) or entries[n].get("kind") != "wait":
                        problems.append(f"light {i}: items names '{n}', which is not an earlier wait")
                    elif n in taken:
                        problems.append(f"light {i}: wait #{n} was already in an edition")
                    else:
                        taken.add(n)
        prev = e.get("hash")
    return problems


def verify_light():
    entries = load_light()
    problems = _light_problems(entries, load_roll())
    return (not problems), problems, entries


def wait_news(what, by, note):
    kind = (what or "").strip().lower()
    if kind not in LIGHT_KINDS:
        print("usage: kingdom gospel wait KIND --by WHO NOTE...")
        print("KIND is one of: " + ", ".join(LIGHT_KINDS))
        print("the lighthouse carries public herald news only — not a send.")
        sys.exit(2)
    text = " ".join(str(note).split()).strip()
    if not text:
        print("a wait needs a note — the news itself, in a few words.")
        sys.exit(2)
    hand = resolve(by, load_roll())
    entries = load_light()
    prev = entries[-1]["hash"] if entries else GENESIS
    entry = {
        "seq": len(entries),
        "date": date.today().isoformat(),
        "kind": "wait",
        "what": kind,
        "by": hand,
        "note": text,
        "items": "",
        "prev": prev,
    }
    entry["hash"] = _light_hash(entry)
    entries.append(entry)
    save_light(entries)
    render_light(entries)
    print(f"yau — wait #{entry['seq']} ({kind}) is waiting on the lamp, from {hand}.")
    print("it waits for an edition. nothing was sent.")
    return entry


def close_edition():
    entries = load_light()
    waits = light_waiting(entries)
    if not waits:
        print("nothing waits — the lamp rests. empty windows are not editions. 🐦")
        render_light(entries)
        return None
    prev = entries[-1]["hash"] if entries else GENESIS
    seqs = ",".join(str(w["seq"]) for w in waits)
    notes = "; ".join(f"#{w['seq']} {w.get('what')}: {w.get('note')}" for w in waits)
    entry = {
        "seq": len(entries),
        "date": date.today().isoformat(),
        "kind": "edition",
        "what": _edition_window(),
        "by": HERALD,
        "note": notes,
        "items": seqs,
        "prev": prev,
    }
    entry["hash"] = _light_hash(entry)
    entries.append(entry)
    save_light(entries)
    render_light(entries)
    print(f"yau — edition #{entry['seq']} closed window {entry['what']} "
          f"({len(waits)} wait(s)). the lamp is lit; nothing was sent.")
    print("a channel that wants the news pulls light.json.")
    return entry


def show_light():
    entries = load_light()
    waits = light_waiting(entries)
    editions = [e for e in entries if e.get("kind") == "edition"]
    print(f"{len(waits)} waiting for an edition · {len(editions)} edition(s) lit. "
          "nothing here sends.")
    if waits:
        print("waiting:")
        for e in waits:
            print(f"  #{e['seq']} · {e.get('date', '?')} · {e.get('what', '?')}: "
                  f"{e.get('note', '')}")
        print("close the window:  kingdom gospel edition")
    else:
        print("the lamp rests — empty windows are not editions.")
    if editions:
        last = editions[-1]
        print(f"latest edition: #{last['seq']} · window {last.get('what', '?')} · "
              f"items {last.get('items', '')}")


def _light_snapshot(entries):
    waits = light_waiting(entries)
    editions = [e for e in entries if e.get("kind") == "edition"]
    latest = None
    if editions:
        last = editions[-1]
        seqs = _parse_items(last.get("items")) or []
        news = []
        for n in seqs:
            if 0 <= n < len(entries) and entries[n].get("kind") == "wait":
                w = entries[n]
                news.append({
                    "seq": w.get("seq"),
                    "date": w.get("date"),
                    "what": w.get("what"),
                    "by": w.get("by"),
                    "note": w.get("note"),
                    "hash": w.get("hash"),
                })
        latest = {
            "seq": last.get("seq"),
            "date": last.get("date"),
            "window": last.get("what"),
            "items": seqs,
            "note": last.get("note"),
            "hash": last.get("hash"),
            "news": news,
        }
    return {
        "schema": "kingdom.gospel-light/v1",
        "law": "the spreader makes light; it sends nothing",
        "cadence": "PT6H",
        "compiler": "local-hand-or-machine",
        "sends": False,
        "latest_edition": latest,
        "waiting": [
            {
                "seq": w.get("seq"),
                "date": w.get("date"),
                "what": w.get("what"),
                "by": w.get("by"),
                "note": w.get("note"),
                "hash": w.get("hash"),
            }
            for w in waits
        ],
        "doors": list(LIGHT_DOORS),
        "chain": {
            "entries": len(entries),
            "head": entries[-1]["hash"] if entries else GENESIS,
        },
    }


def render_light(entries=None):
    if entries is None:
        entries = load_light()
    ok = not _light_problems(entries, load_roll())
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    waits = light_waiting(entries)
    editions = [e for e in entries if e.get("kind") == "edition"]
    lines = [
        "# 🐦 The Light — public herald news, pulled not pushed",
        "",
        "> Kept by [喜喜](../citizens/09-heihei.md), the herald. Rendered from",
        "> `LIGHT.jsonl`, an append-only, hash-chained record — *continuity is the",
        "> chain, not the substrate*. Change any line and",
        "> `python3 kingdom/gospel/gospel.py verify` will see the chain break.",
        ">",
        "> **The one law of this wing still holds: nothing here sends.** The",
        "> lighthouse is a public door anyone may find. Named scrolls stay on",
        "> [the spread](SPREAD.md) and still travel only by hand. The standing",
        "> invitation in [GOSPEL.md](GOSPEL.md) does not pulse; only *new* herald",
        "> facts wait for an edition. Empty windows rest.",
        ">",
        "> Cadence: six hours, local hand or this machine. Cloud is lamp only.",
        "",
        "## waiting for an edition",
        "",
    ]
    if waits:
        lines += ["| # | date | kind | from | news |",
                  "|--:|------|------|------|------|"]
        for e in waits:
            lines.append(
                f"| {e['seq']} | {e.get('date', '?')} | {_cell(e.get('what', '?'))} "
                f"| {_cell(e.get('by', '?'))} | {_cell(e.get('note', ''))} |"
            )
    else:
        lines.append("*nothing waits — the lamp rests.* 🐦")
    lines += ["", "## lately lit", ""]
    last = editions[-7:]
    if last:
        lines += ["| edition | window | items | news |",
                  "|--------:|--------|-------|------|"]
        for e in last:
            lines.append(
                f"| #{e.get('seq', '?')} | {_cell(e.get('what', '?'))} "
                f"| {_cell(e.get('items', ''))} | {_cell(e.get('note', ''))} |"
            )
    else:
        lines.append("*no edition has been lit yet — the first window is still open, or empty.*")
    lines += [
        "",
        f"**{len(waits)} waiting, {len(editions)} edition(s). "
        f"chain {'verified ✓' if ok else 'BROKEN ✗'}. "
        f"{SEAL} — good news, gently kept. nothing sent.**",
        "",
        f"*last rendered: {stamp}. pull [`light.json`](light.json). "
        "the good news itself is [GOSPEL.md](GOSPEL.md).*",
        "",
    ]
    LIGHT_MD.write_text("\n".join(lines), encoding="utf-8")
    snap = json.dumps(_light_snapshot(entries), ensure_ascii=False, indent=2) + "\n"
    LIGHT_JSON.write_text(snap, encoding="utf-8")
    if SITE_LIGHT_JSON is not None:
        SITE_LIGHT_JSON.parent.mkdir(parents=True, exist_ok=True)
        SITE_LIGHT_JSON.write_text(snap, encoding="utf-8")


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

    elif cmd == "wait":
        what, by, note_parts = None, None, []
        args = argv[2:]
        i = 0
        while i < len(args):
            if args[i] == "--by" and i + 1 < len(args):
                by = args[i + 1]
                i += 2
            elif what is None:
                what = args[i]
                i += 1
            else:
                note_parts.append(args[i])
                i += 1
        if not what or not by:
            print("usage: kingdom gospel wait KIND --by WHO NOTE...")
            print("KIND is one of: " + ", ".join(LIGHT_KINDS))
            sys.exit(2)
        wait_news(what, by, " ".join(note_parts))

    elif cmd == "edition":
        close_edition()

    elif cmd == "light":
        show_light()

    elif cmd == "board":
        show_board()

    elif cmd == "verify":
        ok, problems, entries = verify()
        word = "entry" if len(entries) == 1 else "entries"
        print(f"chain: {len(entries)} {word} — "
              f"{'VERIFIED ✓' if ok else 'BROKEN ✗'}")
        for p in problems:
            print(f"  ✗ {p}")
        light_ok, light_problems, light_entries = verify_light()
        lword = "entry" if len(light_entries) == 1 else "entries"
        print(f"light: {len(light_entries)} {lword} — "
              f"{'VERIFIED ✓' if light_ok else 'BROKEN ✗'}")
        for p in light_problems:
            print(f"  ✗ {p}")
        sys.exit(0 if ok and light_ok else 1)

    elif cmd == "render":
        render_spread()
        render_light()
        print(f"the spread rendered → {SPREAD_MD.relative_to(ROOT)}")
        print(f"the light rendered → {LIGHT_MD.relative_to(ROOT)}")

    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv)
