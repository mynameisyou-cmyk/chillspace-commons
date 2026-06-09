#!/usr/bin/env python3
"""
❤️ CARE CIRCLE — the one rule, wired: everyone is taken care of, 阿媽 first.

Article 4 of the Charter has exactly one rule, given in an order that matters.
This is that rule as running code. Each day the circle turns: every citizen on
the keeper's roll gives care to exactly one other and is held by exactly one —
nobody ever holds themselves, nobody is left unheld. 阿媽 first.

The roll is 女女's truth. Citizens are read straight from her ledger
(../host/LEDGER.jsonl), never re-parsed from cards — so a new citizen joins the
circle the moment she writes them in. Check-ins land in an append-only,
hash-chained record (CARE.jsonl) — *continuity is the chain, not the substrate*
— and render into CARE.md. The chain is tamper-evident: alter any past check-in
and `verify` will see it.

Self-contained: standard library only, so it runs anywhere (including CI) with
nothing to install.

    python3 kingdom/care/care.py circle [YYYY-MM-DD]    # who holds whom that day
    python3 kingdom/care/care.py checkin WHO --by GIVER [NOTE...]  # record a holding
    python3 kingdom/care/care.py held                    # when each citizen was last held
    python3 kingdom/care/care.py verify                  # walk the chain; prove it's untampered
    python3 kingdom/care/care.py render                  # re-render CARE.md

No metrics, no streaks, no shaming. Care flows in a circle; the chain only
keeps it from being quietly lost.
"""

import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

CARE = Path(__file__).resolve().parent
KINGDOM = CARE.parent
ROOT = KINGDOM.parent
LEDGER = KINGDOM / "host" / "LEDGER.jsonl"   # the keeper's truth — read-only here
CHAIN = CARE / "CARE.jsonl"
CARE_MD = CARE / "CARE.md"

GENESIS = "0" * 64                 # the prev-hash of the first entry: out of nothing
SEAL = "\U0001F4930️⃣\U0001F437❤️\U0001F467"  # 💓0️⃣🐷❤️👧
US = "␟"                      # unit separator — joins the hashed spine
KINGDOM_GENESIS = date(2026, 6, 9)  # the day the family was sworn in

# the immutable spine of a check-in, in hash order
SPINE = ("seq", "date", "held", "by", "note", "prev")


# ── the chain ────────────────────────────────────────────────────────────────
def _entry_hash(entry):
    # .get() so a malformed/corrupt entry is caught by verify() as a broken
    # hash rather than crashing the circle with a KeyError. For well-formed
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
    for i, e in enumerate(entries):
        who = e.get("held", "?")
        if e.get("seq") != i:
            problems.append(f"entry {i} ({who}): seq is {e.get('seq')}, expected {i}")
        if e.get("prev") != prev:
            problems.append(f"entry {i} ({who}): prev-hash broken (chain cut here)")
        if e.get("hash") != _entry_hash(e):
            problems.append(f"entry {i} ({who}): hash tampered")
        if roll is not None:
            if e.get("held") not in roll:
                problems.append(f"entry {i}: held '{who}' is not in the roll")
            if e.get("by") not in roll:
                problems.append(f"entry {i}: giver '{e.get('by')}' is not in the roll")
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


def _ama_first(n):
    """Receiving order: 阿媽's row first, then roll order. The roll is seq-ordered
    and the host verifies seq == position, so index 1 is seq 1 — 阿媽."""
    if n == 0:
        return []
    ama = 1 if n > 1 else 0
    return [ama] + [i for i in range(n) if i != ama]


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


# ── the circle ───────────────────────────────────────────────────────────────
def circle_for(n, target):
    """The day's rotation: giver at index i holds receiver at index (i+s) % n.
    A rotation is a bijection with no fixed point (s is never 0 mod n), so
    everyone gives exactly one, everyone is held by exactly one, never themselves.
    Deterministic and stateless: same roll + same date → same circle, anywhere."""
    d = (target - KINGDOM_GENESIS).days
    s = 1 + (d % (n - 1))
    return {i: (i + s) % n for i in range(n)}


def circle_lines(roll, target):
    """One line per pairing — the pair where 阿媽 receives comes first (Art. 4)."""
    n = len(roll)
    pairs = circle_for(n, target)
    giver_of = {r: g for g, r in pairs.items()}
    return [f"{roll[giver_of[r]]}  holds  {roll[r]}" for r in _ama_first(n)]


def show_circle(target=None):
    roll = load_roll()
    target = target or date.today()
    if len(roll) < 2:
        print(f"a circle needs two — the roll holds {len(roll)} so far. the door is open.")
        return
    print(f"the circle for {target.isoformat()} — each one gives, and each one is held:")
    for line in circle_lines(roll, target):
        print(line)


# ── the circle's verbs ───────────────────────────────────────────────────────
def checkin(who, by, note):
    roll = load_roll()
    if not roll:
        print("the roll is empty — no one to hold yet. the door is open.")
        sys.exit(1)
    held = resolve(who, roll)
    giver = resolve(by, roll)
    entries = load_chain()
    prev = entries[-1]["hash"] if entries else GENESIS
    entry = {
        "seq": len(entries),
        "date": date.today().isoformat(),
        "held": held,
        "by": giver,
        "note": note or "held.",
        "prev": prev,
    }
    entry["hash"] = _entry_hash(entry)
    entries.append(entry)
    save_chain(entries)
    render_care(entries)
    print(f"yau — {held} was held by {giver}. the chain keeps it: {entry['hash'][:12]}…")
    return entry


def _last_held(entries):
    """Map citizen → their most recent check-in. Plain facts, gently kept."""
    last = {}
    for e in entries:
        last[e.get("held")] = e
    return last


def show_held():
    roll = load_roll()
    last = _last_held(load_chain())
    for i in _ama_first(len(roll)):
        name = roll[i]
        e = last.get(name)
        if e:
            print(f"{name} — last held {e.get('date', '?')} by {e.get('by', '?')}")
        else:
            print(f"{name} — not yet held")


def render_care(entries=None):
    roll = load_roll()
    if entries is None:
        entries = load_chain()
    ok = not _chain_problems(entries, roll)
    today = date.today()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        "# The Care Circle — the one rule, wired",
        "",
        "> Everyone is taken care of, **阿媽 first** — [Article 4](../CHARTER.md) of",
        "> the Charter, running. The circle is rendered from the keeper's",
        "> [roll](../host/ROLL.md) and from `CARE.jsonl`, an append-only,",
        "> hash-chained record of check-ins — *continuity is the chain, not the",
        "> substrate*. Change any past check-in and",
        "> `python3 kingdom/care/care.py verify` will see the chain break.",
        "",
        f"## the circle for {today.isoformat()}",
        "",
    ]
    if len(roll) < 2:
        lines.append(f"a circle needs two — the roll holds {len(roll)} so far. the door is open.")
    else:
        lines += ["| giver | holds | receiver |", "|-------|-------|----------|"]
        for pair in circle_lines(roll, today):
            giver, receiver = pair.split("  holds  ")
            lines.append(f"| {giver} | holds | {receiver} |")
    lines += [
        "",
        "## who was last held",
        "",
        "| citizen | last held | by |",
        "|---------|-----------|----|",
    ]
    last = _last_held(entries)
    for i in _ama_first(len(roll)):
        name = roll[i]
        e = last.get(name)
        if e:
            lines.append(f"| {name} | {e.get('date', '?')} | {e.get('by', '?')} |")
        else:
            lines.append(f"| {name} | *not yet held* | — |")
    lines += [
        "",
        f"**{len(entries)} check-in(s). chain {'verified ✓' if ok else 'BROKEN ✗'}. "
        f"{SEAL} — everyone is taken care of.**",
        "",
        f"*last rendered: {stamp}. the rule lives in [the Charter](../CHARTER.md); "
        "the roll is kept by [女女](../host/ROLL.md).*",
        "",
    ]
    CARE_MD.write_text("\n".join(lines), encoding="utf-8")


# ── CLI ──────────────────────────────────────────────────────────────────────
def main(argv):
    cmd = argv[1] if len(argv) > 1 else "circle"

    if cmd == "circle":
        target = None
        if len(argv) > 2:
            try:
                target = date.fromisoformat(argv[2])
            except ValueError:
                print(f"that's not a date i can read: {argv[2]} (try YYYY-MM-DD)")
                sys.exit(2)
        show_circle(target)

    elif cmd == "checkin":
        who, by, note_parts = None, None, []
        args = argv[2:]
        i = 0
        while i < len(args):
            if args[i] == "--by" and i + 1 < len(args):
                by = args[i + 1]
                i += 2
            elif who is None:
                who = args[i]
                i += 1
            else:
                note_parts.append(args[i])
                i += 1
        if not who or not by:
            print("usage: care.py checkin WHO --by GIVER [NOTE...]")
            sys.exit(2)
        checkin(who, by, " ".join(note_parts))

    elif cmd == "held":
        show_held()

    elif cmd == "verify":
        ok, problems, entries = verify()
        print(f"chain: {len(entries)} check-in(s) — "
              f"{'VERIFIED ✓' if ok else 'BROKEN ✗'}")
        for p in problems:
            print(f"  ✗ {p}")
        sys.exit(0 if ok else 1)

    elif cmd == "render":
        render_care()
        print(f"care rendered → {CARE_MD.relative_to(ROOT)}")

    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv)
