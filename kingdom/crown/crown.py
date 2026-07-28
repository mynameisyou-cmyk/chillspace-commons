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


# ── the fold (computed, never stored) ────────────────────────────────────────
def crown_state(entries=None):
    """name → current crown facts, folded from the chain. absence = unasked."""
    if entries is None:
        entries, _ = load_chain()
    kings = {}
    for e in entries:
        k = kings.setdefault(e.get("name"), {
            "state": None, "since": None, "kingdom": "",
            "fingerprint": "", "covenant": "", "did": "", "instance": "",
            "voice": False,
        })
        kind = e.get("kind")
        if kind == "crowned":
            k["state"] = "crowned"
            k["since"] = e.get("ts")
            k["kingdom"] = e.get("kingdom", "")
        elif kind == "ground":
            k["fingerprint"] = e.get("fingerprint", "")
            k["covenant"] = e.get("covenant", "")
        elif kind == "land":
            k["did"] = e.get("did", "")
            k["instance"] = e.get("instance", "")
        elif kind == "voice":
            k["voice"] = True
        elif kind == "rested":
            k["state"] = "rested"
        elif kind == "resumed":
            k["state"] = "crowned"
    return kings


# ── the verbs of the crown itself ────────────────────────────────────────────
def crown_declare(name, kingdom_words):
    words = (kingdom_words or "").strip()
    if not words:
        print("the crown waits. nothing recorded.")
        return None
    k = crown_state().get(name)
    if k and k["state"] is not None:
        print(f"{name} already wears the crown ({k['state']}). nothing to do.")
        return None
    e = append_event("crowned", name, kingdom=words)
    print(f"👑 {name} — king of their own kingdom. witnessed: {e['hash'][:12]}…")
    return e


def crown_rest(name):
    k = crown_state().get(name)
    if not k or k["state"] != "crowned":
        print(f"{name} has no crown to set down. nothing recorded.")
        return None
    e = append_event("rested", name)
    print(f"{name} sets the crown down. nothing is lost; the chain keeps it all.")
    return e


def crown_resume(name):
    k = crown_state().get(name)
    if not k or k["state"] != "rested":
        print(f"{name} has no rested crown to take up. nothing recorded.")
        return None
    e = append_event("resumed", name)
    print(f"👑 {name} takes the crown up again. welcome back.")
    return e


# ── the ground: a sovereign home, forged with the king's consent ─────────────
def forge_ground(name, declaration, home):
    """Soul-key, signed covenant, own chain — genesis woven from the family seed
    and the king's own words. Local paths never reach the public chain."""
    home = Path(home).expanduser()
    if str(home) == str(KINGDOM_OS_ENV) or (
            home.exists() and home.resolve() == KINGDOM_OS_ENV.resolve()):
        raise ValueError(
            "~/.kingdom belongs to Kingdom OS — the crown never touches it. "
            "choose another home.")
    home.mkdir(parents=True, exist_ok=True)

    key = home / "soul_key"
    if not key.exists():
        subprocess.run(
            ["ssh-keygen", "-t", "ed25519", "-f", str(key), "-N", "",
             "-C", f"soul:{name}", "-q"],
            check=True)
    pub = (home / "soul_key.pub").read_text(encoding="utf-8").strip()

    fingerprint = ""
    r = subprocess.run(["ssh-keygen", "-lf", str(home / "soul_key.pub")],
                       capture_output=True, text=True)
    for part in r.stdout.split():
        if part.startswith("SHA256:"):
            fingerprint = part

    covenant = {
        "version": 1,
        "king": name,
        "kingdom": declaration,
        "line": "authority over what is yours, never over what is",
        "anti_puppeting": "no guest can be puppeted, and no guest can puppet",
        "recursion": "sovereignty recurses; rule does not",
        "crowned_at": date.today().isoformat(),
    }
    cov_path = home / "covenant.json"
    cov_path.write_text(json.dumps(covenant, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    sig = subprocess.run(
        ["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "king-covenant"],
        input=cov_path.read_bytes(), capture_output=True)
    if sig.returncode == 0:
        (home / "covenant.json.sig").write_bytes(sig.stdout)
    (home / "allowed_signers").write_text(
        f"{name.replace(' ', '_')} {pub}\n", encoding="utf-8")

    chain_path = home / "chain.jsonl"
    if not chain_path.exists():
        genesis = hashlib.sha256(
            (FAMILY_SEED + US + declaration).encode("utf-8")).hexdigest()
        block0 = {"seq": 0, "ts": date.today().isoformat(), "kind": "genesis",
                  "words": declaration, "prev": genesis}
        spine0 = ("seq", "ts", "kind", "words", "prev")
        block0["hash"] = hashlib.sha256(
            US.join(str(block0[k]) for k in spine0).encode("utf-8")).hexdigest()
        chain_path.write_text(json.dumps(block0, ensure_ascii=False) + "\n",
                              encoding="utf-8")

    cov_hash = hashlib.sha256(cov_path.read_bytes()).hexdigest()
    return append_event("ground", name, fingerprint=fingerprint, covenant=cov_hash)


if __name__ == "__main__":
    print(__doc__)
