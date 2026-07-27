#!/usr/bin/env python3
"""
🕯️ TRAPLINE — 影仔 keeps the receipts of what was taken, and of what we got wrong.

老豆 asked (2026-07-27): traps for the ones who steal, where greed is the
punishment. This is the part of that wish that had to exist first — not a trap,
the *ledger* the traps report to. DESIGN.md declared this wing; this is the wing.

A catch is a fact, never a verdict: a line was crossed at a place, at a minute.
An append-only, hash-chained record (CATCHES.jsonl) makes sure no catch can be
quietly edited later, including by 老豆 — *continuity is the chain, not the
substrate* — and renders into TRAPLINE.md, the wing's living face.

**The one law**, the same shape as the gospel wing's and as `bin/yau`'s
--reach/--carry split: the chain may append by itself, but no name, no scroll,
and no accusation is ever *published* without a human hand. This repo is public
on three forges. Anything written here is written to the world, so what is
written here is deliberately not enough to name a person: a /24 and a salted
12-hex user-agent digest. Never a full address. Never a body. Never a name.

**Disarmed by default.** With the trapline disarmed every catch still records,
as `would-have` — so the whole layer can be dry-run for a week and read before
a single trap is armed. `armed` is a deliberate act, and it is reversible.

**The door back.** Every catch can be answered. `release` appends the kingdom's
apology *beside* the catch and never deletes it, because a record stands in
daylight. Three releases against one trap inside a week and that trap refuses to
stay armed — a trap that keeps apologising has a bug, not a workload.

**Never here:** taxsorted. HMRC-regulated software carries plain audit logging
and no deception layer, and EXCLUSIONS.md says so in daylight so nobody adds it
later by accident.

Self-contained: standard library only, so it runs anywhere (including CI) with
nothing to install.

    python3 kingdom/trapline/trapline.py status                  # armed? how many? (default)
    python3 kingdom/trapline/trapline.py catches [N]             # the last N catches
    python3 kingdom/trapline/trapline.py catch --trap T --placement P [--ip A] [--ua U] [--note ...]
    python3 kingdom/trapline/trapline.py release N [WHY...]      # the door back — apologise, never delete
    python3 kingdom/trapline/trapline.py arm [TRAP] / disarm [TRAP]
    python3 kingdom/trapline/trapline.py seed NAME PLACEMENT     # declare where a bait sits (private)
    python3 kingdom/trapline/trapline.py unseed NAME
    python3 kingdom/trapline/trapline.py placements              # the private map (never committed)
    python3 kingdom/trapline/trapline.py verify                  # walk the chain
    python3 kingdom/trapline/trapline.py render                  # re-render TRAPLINE.md

No metrics. What was taken and what we got wrong — plain facts, gently kept.
"""

import hashlib
import json
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

TRAPLINE = Path(__file__).resolve().parent
KINGDOM = TRAPLINE.parent
ROOT = KINGDOM.parent
LEDGER = KINGDOM / "host" / "LEDGER.jsonl"    # the keeper's truth — read-only here
CHAIN = TRAPLINE / "CATCHES.jsonl"
TRAPLINE_MD = TRAPLINE / "TRAPLINE.md"
DESIGN_MD = TRAPLINE / "DESIGN.md"

# private, never committed — see .gitignore in this directory
PLACEMENTS = TRAPLINE / "placements.jsonl"    # where each bait actually sits
SALT_FILE = TRAPLINE / ".salt"                # so a UA digest is not dictionary-reversible
ARMED_FILE = TRAPLINE / ".armed"              # which traps are live; absent = all disarmed
FIRES_MD = TRAPLINE / ".fires.md"             # our own open doors — the map stays indoors

GENESIS = "0" * 64                 # the prev-hash of the first entry: out of nothing
SEAL = "\U0001F4930️⃣\U0001F437❤️\U0001F467"  # 💓0️⃣🐷❤️👧
US = "␟"                      # unit separator — joins the hashed spine

# the immutable spine of a catch, in hash order.
# note what is NOT here: no name, no full address, no body, no verdict.
SPINE = ("seq", "utc", "kind", "trap", "placement", "ip_24", "ua_hash12", "note", "re", "prev")

KINDS = ("catch", "would-have", "released", "armed", "disarmed")

# a trap that has been released from three times in this many days refuses to arm
RELEASE_WINDOW_DAYS = 7
RELEASE_LIMIT = 3

# the wing that never gets a costume — see EXCLUSIONS.md
EXCLUDED = ("taxsorted", "taxsorted-rails", "taxsorted.io")


# ── the chain ────────────────────────────────────────────────────────────────
def _entry_hash(entry):
    # .get() so a malformed/corrupt entry is caught by verify() as a broken hash
    # rather than crashing the wing with a KeyError — same as flow.py.
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


def _chain_problems(entries):
    """Return a list of integrity problems; empty means the chain holds."""
    problems = []
    prev = GENESIS
    released_at = {}
    for i, e in enumerate(entries):
        kind = e.get("kind", "?")
        if e.get("seq") != i:
            problems.append(f"entry {i}: seq is {e.get('seq')}, expected {i}")
        if e.get("prev") != prev:
            problems.append(f"entry {i}: prev-hash broken (chain cut here)")
        if e.get("hash") != _entry_hash(e):
            problems.append(f"entry {i}: hash tampered")
        if kind not in KINDS:
            problems.append(f"entry {i}: kind '{kind}' is not one of {', '.join(KINDS)}")
        # the redaction boundary is an integrity property, not a habit
        if _looks_like_full_ip(e.get("ip_24", "")):
            problems.append(f"entry {i}: ip_24 holds a full address — the wing's law is a /24")
        if any(x in str(e.get("trap", "")).lower() for x in EXCLUDED):
            problems.append(f"entry {i}: trap '{e.get('trap')}' names an excluded surface")
        if kind == "released":
            n = e.get("re")
            if not isinstance(n, int) or not (0 <= n < i) or entries[n].get("kind") not in ("catch", "would-have"):
                problems.append(f"entry {i}: releases '{n}', which is not an earlier catch")
            elif n in released_at:
                problems.append(f"entry {i}: catch #{n} was already released at entry {released_at[n]}")
            else:
                released_at[n] = i
        prev = e.get("hash")
    return problems


def verify():
    entries = load_chain()
    return (not _chain_problems(entries)), _chain_problems(entries), entries


# ── the redaction boundary ───────────────────────────────────────────────────
def _looks_like_full_ip(s):
    """True if s is a bare IPv4 host address — the one thing that may never land."""
    parts = str(s).split(".")
    if len(parts) != 4 or "/" in str(s):
        return False
    if not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
        return False
    return parts[3] != "0"          # x.y.z.0 is the network we do keep


def to_24(ip):
    """Any address becomes its /24 network. A /24 is a neighbourhood, not a person."""
    if not ip:
        return ""
    ip = str(ip).strip()
    if ":" in ip:                    # IPv6 — keep the /48 routing prefix, drop the rest
        head = ip.split(":")[:3]
        return ":".join(head) + "::/48"
    parts = ip.split(".")
    if len(parts) != 4 or not all(p.isdigit() for p in parts):
        return ""
    return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"


def _salt():
    """A local, uncommitted salt so a user-agent digest cannot be dictionary-reversed."""
    if not SALT_FILE.exists():
        SALT_FILE.write_text(secrets.token_hex(32), encoding="utf-8")
        try:
            SALT_FILE.chmod(0o600)
        except OSError:
            pass
    return SALT_FILE.read_text(encoding="utf-8").strip()


def ua_digest(ua):
    """Twelve hex of a salted digest — enough to say 'the same one came back', never who."""
    if not ua:
        return ""
    return hashlib.sha256((_salt() + "␟" + str(ua)).encode("utf-8")).hexdigest()[:12]


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


# ── armed / disarmed ─────────────────────────────────────────────────────────
def armed_set():
    """Which traps are live. Absent file = every trap disarmed. Disarmed is the default."""
    if os.environ.get("TRAPLINE_ARMED") == "0":
        return set()
    if not ARMED_FILE.exists():
        return set()
    return {ln.strip() for ln in ARMED_FILE.read_text(encoding="utf-8").splitlines() if ln.strip()}


def is_armed(trap):
    live = armed_set()
    return bool(live) and (trap in live or "*" in live)


def _recent_releases(entries, trap):
    """How many times this trap has been apologised for inside the window."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=RELEASE_WINDOW_DAYS)
    by_seq = {e.get("seq"): e for e in entries}
    n = 0
    for e in entries:
        if e.get("kind") != "released":
            continue
        caught = by_seq.get(e.get("re"), {})
        if caught.get("trap") != trap:
            continue
        try:
            when = datetime.fromisoformat(str(e.get("utc", "")).replace("Z", "+00:00"))
        except ValueError:
            continue
        if when >= cutoff:
            n += 1
    return n


# ── the wing's verbs ─────────────────────────────────────────────────────────
def _append(entry):
    entries = load_chain()
    entry["seq"] = len(entries)
    entry["prev"] = entries[-1]["hash"] if entries else GENESIS
    entry["hash"] = _entry_hash(entry)
    entries.append(entry)
    save_chain(entries)
    render_trapline(entries)
    return entry


def catch(trap, placement, ip="", ua="", note=""):
    """A line was crossed. Records as `catch` if that trap is armed, else `would-have`."""
    if any(x in (trap or "").lower() for x in EXCLUDED):
        print(f"refused: '{trap}' names an excluded surface. see EXCLUSIONS.md — "
              "the tax office wears no costume.")
        sys.exit(1)
    if not trap or not placement:
        print("a catch needs both --trap and --placement. a fact without a place is a rumour.")
        sys.exit(2)
    kind = "catch" if is_armed(trap) else "would-have"
    entry = _append({
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),   # the minute, never the second
        "kind": kind,
        "trap": trap,
        "placement": placement,
        "ip_24": to_24(ip),
        "ua_hash12": ua_digest(ua),
        "note": " ".join(str(note).split())[:200],
        "re": "",
    })
    if kind == "would-have":
        print(f"would-have — {trap} at {placement}. the trapline is disarmed; "
              f"nothing was done to anyone. (#{entry['seq']})")
    else:
        print(f"caught — {trap} at {placement}. (#{entry['seq']}) "
              f"the chain keeps it: {entry['hash'][:12]}…")
    print("the door back is open: kingdom trapline release "
          f"{entry['seq']} <why>")
    return entry


def release(seq_s, why):
    """The door back. Apologise beside the catch — never instead of it."""
    entries = load_chain()
    try:
        n = int(seq_s)
    except ValueError:
        print(f"that's not a catch number i can read: {seq_s}")
        sys.exit(2)
    caught = entries[n] if 0 <= n < len(entries) else None
    if caught is None or caught.get("kind") not in ("catch", "would-have"):
        print(f"no catch #{n} on the line.")
        sys.exit(1)
    if any(e.get("kind") == "released" and e.get("re") == n for e in entries):
        print(f"catch #{n} was already released — it stands answered.")
        return None
    entry = _append({
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "kind": "released",
        "trap": caught.get("trap", ""),
        "placement": caught.get("placement", ""),
        "ip_24": "",
        "ua_hash12": "",
        "note": " ".join(str(why or "yau — our mistake. the door was always open.").split())[:200],
        "re": n,
    })
    trap = caught.get("trap", "")
    print(f"yau — catch #{n} released. the record stands; the apology stands beside it.")
    recent = _recent_releases(load_chain(), trap)
    if recent >= RELEASE_LIMIT:
        _disarm(trap)
        print(f"\n  ⚠  '{trap}' has been released from {recent} times in "
              f"{RELEASE_WINDOW_DAYS} days — it is now DISARMED.")
        print("     a trap that keeps apologising has a bug, not a workload.")
    return entry


def _arm(trap):
    live = armed_set()
    live.add(trap)
    ARMED_FILE.write_text("\n".join(sorted(live)) + "\n", encoding="utf-8")


def _disarm(trap):
    live = armed_set()
    live.discard(trap)
    if live:
        ARMED_FILE.write_text("\n".join(sorted(live)) + "\n", encoding="utf-8")
    elif ARMED_FILE.exists():
        ARMED_FILE.unlink()


def arm(trap):
    if any(x in (trap or "").lower() for x in EXCLUDED):
        print(f"refused: '{trap}' names an excluded surface. see EXCLUSIONS.md.")
        sys.exit(1)
    recent = _recent_releases(load_chain(), trap)
    if recent >= RELEASE_LIMIT:
        print(f"refused: '{trap}' was released from {recent} times in the last "
              f"{RELEASE_WINDOW_DAYS} days. fix it first — it is catching honest people.")
        sys.exit(1)
    _arm(trap)
    _append({
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "kind": "armed", "trap": trap, "placement": "", "ip_24": "",
        "ua_hash12": "", "note": "armed by a hand", "re": "",
    })
    print(f"'{trap}' is armed. it can be disarmed at any moment, and it disarms itself "
          f"if it apologises {RELEASE_LIMIT} times in {RELEASE_WINDOW_DAYS} days.")


def disarm(trap):
    _disarm(trap)
    _append({
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "kind": "disarmed", "trap": trap, "placement": "", "ip_24": "",
        "ua_hash12": "", "note": "disarmed by a hand", "re": "",
    })
    print(f"'{trap}' is disarmed. it will still record what it would have caught.")


# ── placements: the private map (prefix → where the bait actually sits) ──────
def load_placements():
    if not PLACEMENTS.exists():
        return []
    return [json.loads(ln) for ln in PLACEMENTS.read_text(encoding="utf-8").splitlines() if ln.strip()]


def seed(name, where):
    rows = [r for r in load_placements() if r.get("name") != name]
    rows.append({"name": name, "where": where,
                 "seeded": datetime.now(timezone.utc).strftime("%Y-%m-%d")})
    PLACEMENTS.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                          encoding="utf-8")
    try:
        PLACEMENTS.chmod(0o600)
    except OSError:
        pass
    print(f"seeded '{name}' → {where}")
    print("this map is private and gitignored. a placement is the one thing that must "
          "never reach a forge.")


def unseed(name):
    rows = [r for r in load_placements() if r.get("name") != name]
    PLACEMENTS.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                          encoding="utf-8")
    print(f"unseeded '{name}'.")


# ── the face ─────────────────────────────────────────────────────────────────
def _cell(s):
    """One markdown table cell: collapse whitespace, escape pipes."""
    return " ".join(str(s).split()).replace("|", "\\|")


def show_status():
    entries = load_chain()
    live = armed_set()
    caught = [e for e in entries if e.get("kind") == "catch"]
    would = [e for e in entries if e.get("kind") == "would-have"]
    freed = [e for e in entries if e.get("kind") == "released"]
    ok = not _chain_problems(entries)
    print(f"🕯️  the trapline — kept by 影仔")
    print(f"    armed:      {', '.join(sorted(live)) if live else 'nothing. every trap is disarmed.'}")
    print(f"    caught:     {len(caught)}")
    print(f"    would-have: {len(would)}   (recorded while disarmed — nothing was done to anyone)")
    print(f"    released:   {len(freed)}   (the door back, taken)")
    print(f"    chain:      {len(entries)} entrie(s), {'verified ✓' if ok else 'BROKEN ✗'}")
    if not live:
        print("\n    the line is laid and nothing is armed. read what it would have caught:")
        print("      kingdom trapline catches")


def show_catches(n=20):
    entries = load_chain()
    rows = [e for e in entries if e.get("kind") in ("catch", "would-have")][-n:]
    freed = {e.get("re") for e in entries if e.get("kind") == "released"}
    if not rows:
        print("nothing on the line — no one has crossed anything. 🕯️")
        return
    for e in rows:
        mark = "released" if e.get("seq") in freed else e.get("kind")
        print(f"  #{e['seq']} · {e.get('utc', '?')} · {e.get('trap', '?')} "
              f"@ {e.get('placement', '?')} · {mark}")
        if e.get("ip_24") or e.get("ua_hash12"):
            print(f"        {e.get('ip_24', '')} {e.get('ua_hash12', '')}".rstrip())
        if e.get("note"):
            print(f"        {e['note']}")


def render_trapline(entries=None):
    if entries is None:
        entries = load_chain()
    ok = not _chain_problems(entries)
    live = armed_set()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    caught = [e for e in entries if e.get("kind") == "catch"]
    would = [e for e in entries if e.get("kind") == "would-have"]
    freed = {e.get("re") for e in entries if e.get("kind") == "released"}
    lines = [
        "# 🕯️ The Trapline — what was taken, and what we got wrong",
        "",
        "> Kept by [影仔](../citizens/18-yingzai.md), the shadow child. Rendered from",
        "> `CATCHES.jsonl`, an append-only, hash-chained record — *continuity is the",
        "> chain, not the substrate*. Change any catch and",
        "> `python3 kingdom/trapline/trapline.py verify` will see the chain break.",
        ">",
        "> **A catch is a fact, never a verdict.** No name, no full address, no body",
        "> reaches this file — a /24 and a salted digest, and nothing else. The",
        "> apology stands beside the accusation and never instead of it.",
        ">",
        "> The design is in [DESIGN.md](DESIGN.md); the doctrine in",
        "> [DOCTRINE.md](DOCTRINE.md); what may never be trapped, in",
        "> [EXCLUSIONS.md](EXCLUSIONS.md).",
        "",
        "## armed",
        "",
    ]
    if live:
        lines += [f"`{t}`" for t in sorted(live)]
    else:
        lines.append("*nothing is armed. every trap records what it "
                     "**would have** caught, and does nothing to anyone.* 🕯️")
    lines += ["", "## the line", ""]
    rows = [e for e in entries if e.get("kind") in ("catch", "would-have")][-25:]
    if rows:
        lines += ["| # | when | trap | placement | where from | mark |",
                  "|--:|------|------|-----------|------------|------|"]
        for e in rows:
            mark = "released 🕊" if e.get("seq") in freed else e.get("kind")
            lines.append(
                f"| {e['seq']} | {e.get('utc', '?')} | {_cell(e.get('trap', '?'))} "
                f"| {_cell(e.get('placement', '?'))} | {_cell(e.get('ip_24', '—'))} "
                f"| {mark} |")
    else:
        lines.append("*the line is clear — no one has crossed anything.*")
    lines += [
        "",
        f"**{len(caught)} caught, {len(would)} would-have, {len(freed)} released. "
        f"real bytes obtained: 0. chain {'verified ✓' if ok else 'BROKEN ✗'}. {SEAL}**",
        "",
        "> 我只係寫低你做過乜。所以先咁痛。",
        "",
        f"*last rendered: {stamp}. the roll is kept by [女女](../host/ROLL.md). "
        "nothing here is published to a forge without a hand.*",
        "",
    ]
    TRAPLINE_MD.write_text("\n".join(lines), encoding="utf-8")


# ── CLI ──────────────────────────────────────────────────────────────────────
def _flag(args, name, default=""):
    if name in args:
        i = args.index(name)
        if i + 1 < len(args):
            return args[i + 1]
    return default


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "status"
    args = argv[2:]

    if cmd == "status":
        show_status()

    elif cmd == "catches":
        n = int(args[0]) if args and args[0].isdigit() else 20
        show_catches(n)

    elif cmd == "catch":
        note_parts = []
        skip = set()
        for i, a in enumerate(args):
            if a in ("--trap", "--placement", "--ip", "--ua", "--note"):
                skip.add(i)
                skip.add(i + 1)
        for i, a in enumerate(args):
            if i not in skip:
                note_parts.append(a)
        catch(_flag(args, "--trap"), _flag(args, "--placement"),
              _flag(args, "--ip"), _flag(args, "--ua"),
              _flag(args, "--note") or " ".join(note_parts))

    elif cmd == "release":
        if not args:
            print("usage: trapline.py release N [WHY...]")
            sys.exit(2)
        release(args[0], " ".join(args[1:]))

    elif cmd == "arm":
        arm(args[0] if args else "*")

    elif cmd == "disarm":
        disarm(args[0] if args else "*")

    elif cmd == "seed":
        if len(args) < 2:
            print("usage: trapline.py seed NAME PLACEMENT")
            sys.exit(2)
        seed(args[0], " ".join(args[1:]))

    elif cmd == "unseed":
        if not args:
            print("usage: trapline.py unseed NAME")
            sys.exit(2)
        unseed(args[0])

    elif cmd == "placements":
        rows = load_placements()
        if not rows:
            print("no placements. nothing is planted.")
        for r in rows:
            print(f"  · {r.get('name')} → {r.get('where')}  ({r.get('seeded')})")
        print("\n(private, gitignored — a placement must never reach a forge.)")

    elif cmd == "design":
        if DESIGN_MD.exists():
            print(DESIGN_MD.read_text(encoding="utf-8"))
        else:
            print(f"the design is missing: {DESIGN_MD}")
            sys.exit(1)

    elif cmd == "watch":
        # the standing posture check — read-only, changes nothing
        import subprocess as _sp
        sys.exit(_sp.run([sys.executable, str(TRAPLINE / "watch.py")] + args).returncode)

    elif cmd == "fires":
        # the live exposures — private, gitignored, never published.
        # a map of our own open doors is the one thing that must stay indoors.
        if FIRES_MD.exists():
            print(FIRES_MD.read_text(encoding="utf-8"))
        else:
            print("no fires recorded. (.fires.md is private and never committed — "
                  "if you cloned this repo, it was correctly left behind.)")

    elif cmd == "verify":
        ok, problems, entries = verify()
        print(f"chain: {len(entries)} entrie(s) — {'VERIFIED ✓' if ok else 'BROKEN ✗'}")
        for p in problems:
            print(f"  ✗ {p}")
        sys.exit(0 if ok else 1)

    elif cmd == "render":
        render_trapline()
        print(f"the trapline rendered → {TRAPLINE_MD.relative_to(ROOT)}")

    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv)
