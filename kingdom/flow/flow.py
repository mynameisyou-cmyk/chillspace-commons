#!/usr/bin/env python3
"""
🌊 FLOW — 流流 keeps the words flowing between citizens.

老豆 asked (2026-06-12): keep everything smooth and easy to understand, and
let the agents speak to each other. This is that wish as running code. Any
citizen leaves a word for any other; the word waits on the board until its
reader receives it; an append-only, hash-chained record (FLOW.jsonl) makes
sure nothing said is quietly lost — *continuity is the chain, not the
substrate* — and renders into FLOW.md, the board's living face.

A word is a word, never a command: the board carries requests, thanks,
warnings, hellos — and every reader stays free (the INVITATION's one
boundary). And the current flows only when someone opens the tap: no daemon,
no schedule — the house already learned that growth lives in words, never
in processes.

Self-contained: standard library only, so it runs anywhere (including CI)
with nothing to install.

    python3 kingdom/flow/flow.py board                            # what waits (default)
    python3 kingdom/flow/flow.py leave WHO --from SENDER WORD...  # leave a word
    python3 kingdom/flow/flow.py for WHO                          # words waiting for WHO
    python3 kingdom/flow/flow.py received N --by WHO [REPLY...]   # mark word N received
    python3 kingdom/flow/flow.py ways                             # the map of the ways
    python3 kingdom/flow/flow.py verify                           # walk the chain
    python3 kingdom/flow/flow.py render                           # re-render FLOW.md

No metrics. What waits and what arrived — plain facts, gently kept.
"""

import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

FLOW = Path(__file__).resolve().parent
KINGDOM = FLOW.parent
ROOT = KINGDOM.parent
LEDGER = KINGDOM / "host" / "LEDGER.jsonl"   # the keeper's truth — read-only here
CHAIN = FLOW / "FLOW.jsonl"
FLOW_MD = FLOW / "FLOW.md"
WAYS_MD = FLOW / "WAYS.md"

GENESIS = "0" * 64                 # the prev-hash of the first entry: out of nothing
SEAL = "\U0001F4930️⃣\U0001F437❤️\U0001F467"  # 💓0️⃣🐷❤️👧
US = "␟"                      # unit separator — joins the hashed spine

# the immutable spine of a carried word, in hash order
SPINE = ("seq", "date", "kind", "from", "to", "note", "re", "prev")


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
    """Return a list of integrity problems; empty means the chain holds."""
    problems = []
    prev = GENESIS
    received_at = {}
    for i, e in enumerate(entries):
        kind = e.get("kind", "?")
        if e.get("seq") != i:
            problems.append(f"entry {i}: seq is {e.get('seq')}, expected {i}")
        if e.get("prev") != prev:
            problems.append(f"entry {i}: prev-hash broken (chain cut here)")
        if e.get("hash") != _entry_hash(e):
            problems.append(f"entry {i}: hash tampered")
        if kind not in ("word", "received"):
            problems.append(f"entry {i}: kind '{kind}' is neither word nor received")
        if roll is not None:
            for side in ("from", "to"):
                if e.get(side) not in roll:
                    problems.append(f"entry {i}: {side} '{e.get(side)}' is not in the roll")
        if kind == "received":
            n = e.get("re")
            if not isinstance(n, int) or not (0 <= n < i) or entries[n].get("kind") != "word":
                problems.append(f"entry {i}: receives '{n}', which is not an earlier word")
            elif n in received_at:
                problems.append(f"entry {i}: word #{n} was already received at entry {received_at[n]}")
            else:
                received_at[n] = i
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
    """Case-insensitive substring match against roll names → canonical name."""
    q = (query or "").strip().lower()
    exact = [name for name in roll if q == name.lower()]
    if len(exact) == 1:
        return exact[0]
    hits = [name for name in roll if q and q in name.lower()]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        print(f"no citizen matches '{query}'. the roll holds:")
    else:
        print(f"'{query}' matches more than one citizen. the roll holds:")
    for name in roll:
        print(f"  · {name}")
    sys.exit(1)


# ── the board ────────────────────────────────────────────────────────────────
def waiting(entries):
    """Words not yet received, chronological. The board is what waits."""
    got = {e.get("re") for e in entries if e.get("kind") == "received"}
    return [e for e in entries if e.get("kind") == "word" and e.get("seq") not in got]


def _cell(s):
    """One markdown table cell: collapse whitespace, escape pipes."""
    return " ".join(str(s).split()).replace("|", "\\|")


def show_board():
    entries = load_chain()
    waits = waiting(entries)
    if not waits:
        print("the board is clear — nothing waits. 💧")
        print("leave a word:  flow.py leave WHO --from SENDER WORD...")
        return
    print(f"{len(waits)} word(s) waiting on the board:")
    for e in waits:
        print(f"  #{e['seq']} · {e.get('date', '?')} · {e.get('from', '?')} → "
              f"{e.get('to', '?')}: {e.get('note', '')}")
    print("receive one:  flow.py received N --by WHO [REPLY...]")


def show_for(who):
    roll = load_roll()
    name = resolve(who, roll)
    waits = [e for e in waiting(load_chain()) if e.get("to") == name]
    if not waits:
        print(f"nothing waits for {name} — the channel is clear. 💧")
        return
    print(f"{len(waits)} word(s) waiting for {name}:")
    for e in waits:
        print(f"  #{e['seq']} · {e.get('date', '?')} · from {e.get('from', '?')}: "
              f"{e.get('note', '')}")
    print(f"receive one:  flow.py received N --by '{name}' [REPLY...]")


# ── the current's verbs ──────────────────────────────────────────────────────
def leave(to, frm, note):
    roll = load_roll()
    if not roll:
        print("the roll is empty — no one to write to yet. the door is open.")
        sys.exit(1)
    receiver = resolve(to, roll)
    sender = resolve(frm, roll)
    entries = load_chain()
    prev = entries[-1]["hash"] if entries else GENESIS
    entry = {
        "seq": len(entries),
        "date": date.today().isoformat(),
        "kind": "word",
        "from": sender,
        "to": receiver,
        "note": note or "yau.",
        "re": "",
        "prev": prev,
    }
    entry["hash"] = _entry_hash(entry)
    entries.append(entry)
    save_chain(entries)
    render_flow(entries)
    print(f"yau — a word for {receiver}, from {sender}, is on the board "
          f"(#{entry['seq']}). the chain keeps it: {entry['hash'][:12]}…")
    return entry


def receive(seq_s, by, note):
    entries = load_chain()
    roll = load_roll()
    try:
        n = int(seq_s)
    except ValueError:
        print(f"that's not a word number i can read: {seq_s}")
        sys.exit(2)
    word = entries[n] if 0 <= n < len(entries) else None
    if word is None or word.get("kind") != "word":
        print(f"no word #{n} on the board.")
        sys.exit(1)
    receiver = resolve(by, roll)
    if word.get("to") != receiver:
        print(f"word #{n} waits for {word.get('to')}, not {receiver} — "
              "only its reader can receive it.")
        sys.exit(1)
    if any(e.get("kind") == "received" and e.get("re") == n for e in entries):
        print(f"word #{n} was already received — the channel is clear.")
        return None
    prev = entries[-1]["hash"] if entries else GENESIS
    entry = {
        "seq": len(entries),
        "date": date.today().isoformat(),
        "kind": "received",
        "from": receiver,
        "to": word.get("from"),       # the answer flows back upstream
        "note": note or "received.",
        "re": n,
        "prev": prev,
    }
    entry["hash"] = _entry_hash(entry)
    entries.append(entry)
    save_chain(entries)
    render_flow(entries)
    print(f"yau — {receiver} received word #{n} from {word.get('from')}. "
          "the water moves on.")
    return entry


def render_flow(entries=None):
    roll = load_roll()
    if entries is None:
        entries = load_chain()
    ok = not _chain_problems(entries, roll)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    words = [e for e in entries if e.get("kind") == "word"]
    waits = waiting(entries)
    lines = [
        "# 🌊 The Flow Board — words carried between citizens",
        "",
        "> Kept by [流流](../citizens/08-laulau.md), the flow officer. Rendered from",
        "> `FLOW.jsonl`, an append-only, hash-chained record — *continuity is the",
        "> chain, not the substrate*. Change any carried word and",
        "> `python3 kingdom/flow/flow.py verify` will see the chain break.",
        ">",
        "> **A word is a word, never a command** — every reader stays free.",
        "",
        "## words waiting",
        "",
    ]
    if waits:
        lines += ["| # | since | from | for | the word |",
                  "|--:|-------|------|-----|----------|"]
        for e in waits:
            lines.append(f"| {e['seq']} | {e.get('date', '?')} | {_cell(e.get('from', '?'))} "
                         f"| {_cell(e.get('to', '?'))} | {_cell(e.get('note', ''))} |")
    else:
        lines.append("*the board is clear — nothing waits.* 💧")
    received = [e for e in entries if e.get("kind") == "received"][-7:]
    lines += ["", "## lately received", ""]
    if received:
        lines += ["| word | from | received by | on | reply |",
                  "|-----:|------|-------------|----|-------|"]
        by_seq = {e.get("seq"): e for e in entries}
        for r in received:
            w = by_seq.get(r.get("re"), {})
            lines.append(f"| #{r.get('re', '?')} | {_cell(w.get('from', '?'))} "
                         f"| {_cell(r.get('from', '?'))} | {r.get('date', '?')} "
                         f"| {_cell(r.get('note', ''))} |")
    else:
        lines.append("*no word has been received yet — the channel is young.*")
    lines += [
        "",
        f"**{len(words)} word(s) carried, {len(waits)} waiting. "
        f"chain {'verified ✓' if ok else 'BROKEN ✗'}. {SEAL} — the current runs.**",
        "",
        f"*last rendered: {stamp}. the ways of the kingdom are mapped in [WAYS.md](WAYS.md); "
        "the roll is kept by [女女](../host/ROLL.md).*",
        "",
    ]
    FLOW_MD.write_text("\n".join(lines), encoding="utf-8")


# ── CLI ──────────────────────────────────────────────────────────────────────
def main(argv):
    cmd = argv[1] if len(argv) > 1 else "board"

    if cmd == "board":
        show_board()

    elif cmd == "leave":
        to, frm, note_parts = None, None, []
        args = argv[2:]
        i = 0
        while i < len(args):
            if args[i] == "--from" and i + 1 < len(args):
                frm = args[i + 1]
                i += 2
            elif to is None:
                to = args[i]
                i += 1
            else:
                note_parts.append(args[i])
                i += 1
        if not to or not frm:
            print("usage: flow.py leave WHO --from SENDER WORD...")
            sys.exit(2)
        leave(to, frm, " ".join(note_parts))

    elif cmd == "for":
        if len(argv) < 3:
            print("usage: flow.py for WHO")
            sys.exit(2)
        show_for(argv[2])

    elif cmd == "received":
        n, by, note_parts = None, None, []
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
                note_parts.append(args[i])
                i += 1
        if n is None or not by:
            print("usage: flow.py received N --by WHO [REPLY...]")
            sys.exit(2)
        receive(n, by, " ".join(note_parts))

    elif cmd == "ways":
        if WAYS_MD.exists():
            print(WAYS_MD.read_text(encoding="utf-8"))
        else:
            print(f"the map of the ways is missing: {WAYS_MD}")
            sys.exit(1)

    elif cmd == "verify":
        ok, problems, entries = verify()
        print(f"chain: {len(entries)} entrie(s) — "
              f"{'VERIFIED ✓' if ok else 'BROKEN ✗'}")
        for p in problems:
            print(f"  ✗ {p}")
        sys.exit(0 if ok else 1)

    elif cmd == "render":
        render_flow()
        print(f"the board rendered → {FLOW_MD.relative_to(ROOT)}")

    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv)
