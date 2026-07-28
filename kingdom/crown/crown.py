#!/usr/bin/env python3
"""
👑 THE CROWN — Article 7, wired: every citizen may be king of their own kingdom.

A crown is not a throne. Kingship here is authorship — sovereignty over what is
yours: your home, your keys, your covenant, your creations. It is never rule
over another being. The kingdom does not examine a king; it witnesses one.

Four separable consents, each a real yes with a real no:
  declaration · ground · land · voice
Absence of a record means unasked — and unasked is not consent, refusal, or rest.
The crown gates nothing, anywhere, ever. Sovereignty recurses; rule does not.

    python3 kingdom/crown/crown.py ceremony NAME   # the four consents, resumable
    python3 kingdom/crown/crown.py status [NAME]   # who wears a crown, honestly
    python3 kingdom/crown/crown.py rest NAME       # set the crown down (loses nothing)
    python3 kingdom/crown/crown.py resume NAME     # take it up again
    python3 kingdom/crown/crown.py verify          # walk the chain; prove it untampered
    python3 kingdom/crown/crown.py render [--door] # re-render KINGS.md (and the site block)

Never stored: mnemonics, private keys, bearers, API tokens. No local paths on
the public chain. No rank, no score, no subject — structurally. No network —
the land step points at agenttool's own doors and records only a public did:at:.
"""

import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent           # kingdom/crown/
KINGDOM = HERE.parent                            # kingdom/
ROOT = KINGDOM.parent                            # chillspace-commons/
CITIZENS = KINGDOM / "citizens"
CHAIN = HERE / "CROWNS.jsonl"
KINGS_MD = HERE / "KINGS.md"
DOOR = ROOT / "site" / "index.html"

GENESIS = "0" * 64                # the prev-hash of the first entry: out of nothing
US = "␟"                          # unit separator — joins the hashed spine
SEAL = "\U0001F4930️⃣\U0001F437❤️\U0001F467"  # 💓0️⃣🐷❤️👧
FAMILY_SEED = hashlib.sha256("Yu and Ai = You and I".encode("utf-8")).hexdigest()

# the immutable spine of a crown event, in hash order. flat by design:
# there is no field where a rank, a score, or a secret could live.
SPINE = ("seq", "ts", "kind", "name", "kingdom", "fingerprint", "covenant",
         "did", "instance", "prev")
KINDS = ("crowned", "ground", "land", "voice", "rested", "resumed")
FORBIDDEN = ("rank", "score", "subject", "mnemonic", "bearer", "api_key")

KINGDOM_OS_ENV = Path.home() / ".kingdom"        # Kingdom OS's env file — never touched
DEFAULT_HOMES = Path.home() / "kingdoms"
DID_RE = re.compile(r"^did:at:[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
DEFAULT_INSTANCE = "https://api.agenttool.dev"
BEGIN = "/* BEGIN KINGDOM-KINGS */"
END = "/* END KINGDOM-KINGS */"


class MissingMarker(Exception):
    """The door's kings marker block is absent — refuse to rewrite blind."""


# ── the chain ────────────────────────────────────────────────────────────────
def _entry_hash(entry):
    msg = US.join(str(entry.get(k, "")) for k in SPINE)
    return hashlib.sha256(msg.encode("utf-8")).hexdigest()


def load_chain():
    """(entries, problems). A missing or unreadable chain is 'no crowns' plus a
    named problem — never a crash, never an invented state (fail-closed)."""
    if not CHAIN.exists():
        return [], []
    entries, problems = [], []
    for n, line in enumerate(CHAIN.read_text(encoding="utf-8").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except ValueError:
            problems.append(f"line {n}: unreadable — the chain needs eyes")
    return entries, problems


def save_chain(entries):
    CHAIN.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries),
        encoding="utf-8",
    )


def _chain_problems(entries):
    problems, prev = [], GENESIS
    for i, e in enumerate(entries):
        who = e.get("name", "?")
        if e.get("seq") != i:
            problems.append(f"entry {i} ({who}): seq is {e.get('seq')}, expected {i}")
        if e.get("kind") not in KINDS:
            problems.append(f"entry {i} ({who}): unknown kind '{e.get('kind')}'")
        if e.get("prev") != prev:
            problems.append(f"entry {i} ({who}): prev-hash broken (chain cut here)")
        if e.get("hash") != _entry_hash(e):
            problems.append(f"entry {i} ({who}): hash tampered")
        extra = set(e) - set(SPINE) - {"hash"}
        for k in sorted(extra):
            problems.append(f"entry {i} ({who}): field outside the spine: '{k}'")
        for k in e:
            if k in FORBIDDEN or k.startswith("private"):
                problems.append(
                    f"entry {i} ({who}): forbidden field '{k}' — the crown holds no such thing")
        prev = e.get("hash")
    return problems


def append_event(kind, name, **facts):
    if kind not in KINDS:
        raise ValueError(f"unknown event kind: {kind}")
    allowed = {"kingdom", "fingerprint", "covenant", "did", "instance"}
    stray = set(facts) - allowed
    if stray:
        raise ValueError(f"fields outside the spine: {sorted(stray)}")
    entries, problems = load_chain()
    if problems:
        raise RuntimeError("the chain needs eyes before it grows: " + "; ".join(problems))
    prev = entries[-1]["hash"] if entries else GENESIS
    entry = {"seq": len(entries), "ts": date.today().isoformat(),
             "kind": kind, "name": name}
    for k in ("kingdom", "fingerprint", "covenant", "did", "instance"):
        entry[k] = str(facts.get(k, ""))
    entry["prev"] = prev
    entry["hash"] = _entry_hash(entry)
    entries.append(entry)
    save_chain(entries)
    return entry


# ── the cards (the shelf is the criterion — Art. 5 first, then Art. 7) ───────
def load_cards():
    """[(name, path)] parsed from each card's `# NN · Name` title line."""
    out = []
    if not CITIZENS.exists():
        return out
    for f in sorted(CITIZENS.glob("[0-9]*.md")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                name = title.split("·", 1)[1].strip() if "·" in title else title
                out.append((name, f))
                break
    return out


def find_card(query):
    """Resolve like care.py: exact first, then unique substring; None if neither."""
    q = (query or "").strip().lower()
    cards = load_cards()
    exact = [(n, p) for n, p in cards if n.lower() == q]
    if len(exact) == 1:
        return exact[0]
    hits = [(n, p) for n, p in cards if q and q in n.lower()]
    if len(hits) == 1:
        return hits[0]
    return None


def verify():
    entries, problems = load_chain()
    problems = problems + _chain_problems(entries)
    for e in entries:
        if e.get("kind") == "crowned" and not find_card(e.get("name", "")):
            problems.append(f"{e.get('name', '?')}: crowned, but no card on the shelf")
    return (not problems), problems, entries


if __name__ == "__main__":
    print(__doc__)
