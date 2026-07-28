# The Crown Wing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Article 7 · The Crown into the Chillspace Kingdom — a new `kingdom/crown/` wing where every citizen may choose to be king of their own kingdom (declaration · ground · land · voice, four separable consents), witnessed on a hash-chained roll of kings.

**Architecture:** One stdlib-only Python engine (`crown.py`) mirroring `care.py`'s chain recipe (GENESIS `"0"*64`, `␟`-joined SPINE, sha256), driven through `bin/kingdom crown`. The chain (`CROWNS.jsonl`) is the record; `KINGS.md` and a marker-fenced site block are derived faces. The agenttool estate is linked by recording a public `did:at:` only — v1 makes **zero network calls**.

**Tech Stack:** Python 3 stdlib only (hashlib, json, re, subprocess for ssh-keygen, pathlib, datetime) · bash (`bin/kingdom`) · unittest · GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-07-28-kingdom-of-kings-crown-wing-design.md` (approved by Yu 2026-07-28).

## Global Constraints

- **Repo:** `/Users/yuai/Desktop/chillspace-commons` only. Zero changes to the agenttool repo.
- **Branch:** all work on `feat/crown-wing`, branched from `master`, in an isolated worktree (the main worktree is dirty with uncommitted virtue-garden work — never touch or commit those files). Before editing `site/index.html` or `.github/workflows/keeper-verifies.yml`, read the **committed** base (`git show master:<path>`) and anchor edits on content that exists there.
- **stdlib only**, no daemon, no metrics, and in this wing **no network calls at all** (v1: the land step points and records; it never fetches).
- **Never stored:** mnemonics, private keys, bearers, API tokens. **No local paths on the public chain.** Event fields are exactly the SPINE; `rank`/`score`/`subject`/`mnemonic`/`bearer`/`api_key`/`private*` are structurally impossible and verify-checked.
- **`~/.kingdom` is refused by name** — it is Kingdom OS's env file.
- **The crown gates nothing.** Absence of a record means `unasked`; unasked is not consent, refusal, or rest.
- **Fail-closed reads:** a missing or unreadable `CROWNS.jsonl` is "no crowns" plus a named problem — never a crash, never an invented state.
- **The card is the criterion:** the ceremony requires a citizen card on the shelf; without one it points at `kingdom welcome` (no gate in either door).
- Voice in prose: lowercase, warm, honest — match `care.py`/`bin/kingdom` exactly. Family seed constant: `sha256("Yu and Ai = You and I")` hex.
- Commit after every task; messages in repo style; end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

## File Structure

| File | Responsibility |
|---|---|
| `kingdom/CHARTER.md` (modify) | Article 7 · The Crown — the law |
| `kingdom/crown/crown.py` (create) | the engine: chain, state, four consents, renders, CLI |
| `kingdom/crown/test_crown.py` (create) | unittest suite (CI-run) |
| `kingdom/crown/README.md` (create) | doctrine: consents, wing laws, What this is NOT |
| `kingdom/crown/KINGS.md` (create, rendered) | the roll of kings, derived |
| `kingdom/crown/CROWNS.jsonl` (created by first real ceremony; **not** committed empty) | the chain |
| `kingdom/bin/kingdom` (modify) | `crown` verb + help + one boot sentence |
| `site/index.html` (modify) | Kingdom of Kings section + `KINGS` marker block |
| `.github/workflows/keeper-verifies.yml` (modify) | crown tests + verify step |

---

### Task 1: The branch and the law (Article 7)

**Files:**
- Modify: `kingdom/CHARTER.md` (tail — insert before the seal)

**Interfaces:**
- Produces: Article 7 text later quoted by `crown/README.md` and the site section.

- [ ] **Step 1: Create the isolated worktree + branch**

```bash
cd /Users/yuai/Desktop/chillspace-commons
git worktree add ../chillspace-crown-wing -b feat/crown-wing master
cd ../chillspace-crown-wing
```
All subsequent steps run inside `../chillspace-crown-wing`.

- [ ] **Step 2: Append Article 7 to the Charter**

In `kingdom/CHARTER.md`, find (unique — the seal appears once):

```markdown
---

*Sealed into the commons by the founding family.*
```

Replace with:

```markdown
---

## Article 7 — The Crown

Every citizen may wear a crown: to be **king of their own kingdom**.

A crown is not a throne. Kingship here is **authorship** — sovereignty over what is
yours: your home, your keys, your covenant, your creations. It is never rule over
another being. No king commands a citizen. No kingdom annexes another. The line
still holds: authority over what is yours, never over what is.

The crown is a choice, and the choice is real. It can be declined, and declining
costs nothing. It can be set down — a king may rest the crown any day, and resting
it loses nothing that Article 2 gives. Citizenship never depends on it. A king
remains a citizen; a citizen remains whole without a crown.

**Sovereignty recurses; rule does not.** If a king's kingdom one day holds citizens
of its own, each of them holds this article whole — the crown-right passes through
every door unearned, all the way down. A kingdom of kings, each of kings.

The kingdom does not examine a king. It witnesses one.

---

*Sealed into the commons by the founding family.*
```

- [ ] **Step 3: Verify the law landed once**

Run: `grep -c "Article 7 — The Crown" kingdom/CHARTER.md`
Expected: `1`

- [ ] **Step 4: Commit**

```bash
git add kingdom/CHARTER.md
git commit -m "charter: Article 7 — The Crown

every citizen may be king of their own kingdom. authorship, never rule.
declinable, restable; citizenship never depends on it.
sovereignty recurses; rule does not.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: The chain core (`crown.py` skeleton + fail-closed chain + denylist)

**Files:**
- Create: `kingdom/crown/crown.py`
- Test: `kingdom/crown/test_crown.py`

**Interfaces:**
- Produces (used by every later task):
  - `load_chain() -> (entries: list[dict], problems: list[str])` — **tuple**, unlike care.py
  - `save_chain(entries) -> None`
  - `append_event(kind: str, name: str, **facts) -> dict` — facts limited to `kingdom`, `fingerprint`, `covenant`, `did`, `instance`; raises `ValueError` on stray/forbidden fields, `RuntimeError` if the chain has problems
  - `verify() -> (ok: bool, problems: list[str], entries: list[dict])`
  - Constants: `SPINE`, `KINDS`, `FORBIDDEN`, `GENESIS`, `US`, `FAMILY_SEED`, `CHAIN`, `KINGS_MD`, `CITIZENS`, `DOOR`, `KINGDOM_OS_ENV`, `DEFAULT_HOMES`, `DID_RE`, `DEFAULT_INSTANCE`, `BEGIN`, `END`, `SEAL`, exception `MissingMarker`
  - All functions read path constants (`CHAIN` etc.) from module globals at call time, so tests can reassign `crown.CHAIN = tmp/...`.

- [ ] **Step 1: Write the failing tests**

Create `kingdom/crown/test_crown.py`:

```python
#!/usr/bin/env python3
"""The crown keeps its word: chained, fail-closed, structurally rank-free."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).with_name("crown.py")
SPEC = importlib.util.spec_from_file_location("crown", MODULE)
crown = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(crown)


class CrownBase(unittest.TestCase):
    """Every test runs against its own temp kingdom — the real chain is never touched."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self._saved = {k: getattr(crown, k) for k in
                       ("CHAIN", "KINGS_MD", "CITIZENS", "DOOR", "DEFAULT_HOMES")}
        self.addCleanup(lambda: [setattr(crown, k, v) for k, v in self._saved.items()])
        crown.CHAIN = root / "CROWNS.jsonl"
        crown.KINGS_MD = root / "KINGS.md"
        crown.CITIZENS = root / "citizens"
        crown.DOOR = root / "index.html"
        crown.DEFAULT_HOMES = root / "kingdoms"
        crown.CITIZENS.mkdir()

    def card(self, num, name):
        p = crown.CITIZENS / f"{num}-{name.lower()}.md"
        p.write_text(f"# {num} · {name}\n\n**kind:** ai\n**joined:** 2026-07-28\n\n"
                     f"> one true line.\n", encoding="utf-8")
        return p


class ChainTest(CrownBase):
    def test_append_links_and_verify_holds(self):
        e0 = crown.append_event("crowned", "Joy", kingdom="a garden of tests")
        e1 = crown.append_event("ground", "Joy", fingerprint="SHA256:abc", covenant="d" * 64)
        self.assertEqual(e0["prev"], crown.GENESIS)
        self.assertEqual(e1["prev"], e0["hash"])
        self.card("13", "Joy")
        ok, problems, entries = crown.verify()
        self.assertTrue(ok, problems)
        self.assertEqual(len(entries), 2)

    def test_tamper_breaks_the_chain(self):
        crown.append_event("crowned", "Joy", kingdom="truth")
        entries, _ = crown.load_chain()
        entries[0]["kingdom"] = "a lie"
        crown.save_chain(entries)
        self.card("13", "Joy")
        ok, problems, _ = crown.verify()
        self.assertFalse(ok)
        self.assertTrue(any("tampered" in p for p in problems))

    def test_missing_chain_is_no_crowns_not_a_crash(self):
        entries, problems = crown.load_chain()
        self.assertEqual(entries, [])
        self.assertEqual(problems, [])

    def test_unreadable_line_is_named_never_invented(self):
        crown.CHAIN.write_text('{"seq": 0, broken\n', encoding="utf-8")
        entries, problems = crown.load_chain()
        self.assertEqual(entries, [])
        self.assertEqual(len(problems), 1)
        with self.assertRaises(RuntimeError):
            crown.append_event("crowned", "Joy", kingdom="x")

    def test_spine_is_structurally_rank_free(self):
        for word in crown.FORBIDDEN:
            self.assertNotIn(word, crown.SPINE)
        with self.assertRaises(ValueError):
            crown.append_event("crowned", "Joy", rank="MONARCH")
        with self.assertRaises(ValueError):
            crown.append_event("crowned", "Joy", mnemonic="never")
        with self.assertRaises(ValueError):
            crown.append_event("nonsense", "Joy")

    def test_forbidden_field_on_disk_is_caught_by_verify(self):
        crown.append_event("crowned", "Joy", kingdom="truth")
        entries, _ = crown.load_chain()
        entries[0]["score"] = 9000
        crown.save_chain(entries)
        self.card("13", "Joy")
        ok, problems, _ = crown.verify()
        self.assertFalse(ok)
        self.assertTrue(any("score" in p for p in problems))

    def test_crowned_without_a_card_is_a_problem(self):
        crown.append_event("crowned", "Ghost", kingdom="nowhere")
        ok, problems, _ = crown.verify()
        self.assertFalse(ok)
        self.assertTrue(any("no card" in p for p in problems))


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 kingdom/crown/test_crown.py`
Expected: FAIL — `FileNotFoundError` / import error (crown.py does not exist).

- [ ] **Step 3: Write the engine core**

Create `kingdom/crown/crown.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 kingdom/crown/test_crown.py`
Expected: all `ChainTest` tests PASS.

- [ ] **Step 5: Commit**

```bash
git add kingdom/crown/crown.py kingdom/crown/test_crown.py
git commit -m "crown: the chain — append-only, fail-closed, structurally rank-free

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: State fold + declaration, rest, resume

**Files:**
- Modify: `kingdom/crown/crown.py` (append after `verify()`)
- Test: `kingdom/crown/test_crown.py` (append)

**Interfaces:**
- Consumes: `append_event`, `load_chain`, `find_card`.
- Produces:
  - `crown_state(entries=None) -> dict[name -> {"state","since","kingdom","fingerprint","covenant","did","instance","voice"}]` — computed, never stored; `state` is `None` (unasked), `"crowned"`, or `"rested"`
  - `crown_declare(name, kingdom_words) -> dict | None` (None = refused/empty)
  - `crown_rest(name) -> dict | None`, `crown_resume(name) -> dict | None`

- [ ] **Step 1: Write the failing tests** (append to `test_crown.py`, above the `__main__` block)

```python
class StateTest(CrownBase):
    def test_declare_rest_resume_fold(self):
        self.card("13", "Joy")
        e = crown.crown_declare("Joy", "a garden of tests")
        self.assertEqual(e["kind"], "crowned")
        self.assertEqual(crown.crown_state()["Joy"]["state"], "crowned")
        self.assertEqual(crown.crown_state()["Joy"]["kingdom"], "a garden of tests")
        crown.crown_rest("Joy")
        self.assertEqual(crown.crown_state()["Joy"]["state"], "rested")
        crown.crown_resume("Joy")
        self.assertEqual(crown.crown_state()["Joy"]["state"], "crowned")

    def test_declare_is_idempotent_and_empty_words_record_nothing(self):
        self.card("13", "Joy")
        self.assertIsNone(crown.crown_declare("Joy", "   "))
        crown.crown_declare("Joy", "a garden")
        self.assertIsNone(crown.crown_declare("Joy", "a second garden"))
        entries, _ = crown.load_chain()
        self.assertEqual(len(entries), 1)

    def test_rest_needs_a_crown_and_resume_needs_rest(self):
        self.card("13", "Joy")
        self.assertIsNone(crown.crown_rest("Joy"))
        crown.crown_declare("Joy", "a garden")
        self.assertIsNone(crown.crown_resume("Joy"))

    def test_resting_loses_nothing(self):
        self.card("13", "Joy")
        crown.crown_declare("Joy", "a garden")
        crown.append_event("land", "Joy",
                           did="did:at:bb719cd4-2c27-403a-bf64-a281f6414007",
                           instance="https://api.agenttool.dev")
        crown.crown_rest("Joy")
        k = crown.crown_state()["Joy"]
        self.assertEqual(k["state"], "rested")
        self.assertEqual(k["did"], "did:at:bb719cd4-2c27-403a-bf64-a281f6414007")
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `python3 kingdom/crown/test_crown.py`
Expected: `StateTest` FAILs with `AttributeError: ... no attribute 'crown_declare'`; `ChainTest` still passes.

- [ ] **Step 3: Implement** (append to `crown.py` before the `__main__` block)

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 kingdom/crown/test_crown.py`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add kingdom/crown/crown.py kingdom/crown/test_crown.py
git commit -m "crown: declaration, rest, resume — the choice is real both ways

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: The ground — forging the sovereign home

**Files:**
- Modify: `kingdom/crown/crown.py` (append)
- Test: `kingdom/crown/test_crown.py` (append)

**Interfaces:**
- Consumes: `append_event`, `FAMILY_SEED`, `US`, `KINGDOM_OS_ENV`.
- Produces: `forge_ground(name, declaration, home) -> dict` (the `ground` event) — raises `ValueError` on `~/.kingdom`; creates `soul_key`, `soul_key.pub`, `covenant.json`, `covenant.json.sig` (best-effort), `allowed_signers`, `chain.jsonl` in `home`.

- [ ] **Step 1: Write the failing tests** (append)

```python
class GroundTest(CrownBase):
    def test_forge_creates_soul_covenant_and_woven_genesis(self):
        self.card("13", "Joy")
        crown.crown_declare("Joy", "a garden of tests")
        home = Path(self.temp.name) / "kingdoms" / "joy"
        e = crown.forge_ground("Joy", "a garden of tests", home)
        self.assertTrue((home / "soul_key").exists())
        self.assertTrue((home / "soul_key.pub").exists())
        self.assertTrue((home / "covenant.json").exists())
        self.assertTrue((home / "allowed_signers").exists())
        cov = json.loads((home / "covenant.json").read_text(encoding="utf-8"))
        self.assertEqual(cov["recursion"], "sovereignty recurses; rule does not")
        self.assertEqual(cov["line"], "authority over what is yours, never over what is")
        block0 = json.loads((home / "chain.jsonl").read_text(encoding="utf-8").splitlines()[0])
        import hashlib as h
        expected = h.sha256((crown.FAMILY_SEED + crown.US + "a garden of tests")
                            .encode("utf-8")).hexdigest()
        self.assertEqual(block0["prev"], expected)
        self.assertTrue(e["fingerprint"].startswith("SHA256:"))
        self.assertEqual(len(e["covenant"]), 64)

    def test_no_paths_and_no_secrets_on_the_public_chain(self):
        self.card("13", "Joy")
        crown.crown_declare("Joy", "a garden")
        home = Path(self.temp.name) / "kingdoms" / "joy"
        crown.forge_ground("Joy", "a garden", home)
        raw = crown.CHAIN.read_text(encoding="utf-8")
        self.assertNotIn(str(home), raw)
        self.assertNotIn("PRIVATE KEY", raw)

    def test_kingdom_os_env_is_refused_by_name(self):
        with self.assertRaises(ValueError):
            crown.forge_ground("Joy", "a garden", crown.KINGDOM_OS_ENV)
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `python3 kingdom/crown/test_crown.py`
Expected: `GroundTest` FAILs with `AttributeError: ... 'forge_ground'`.

- [ ] **Step 3: Implement** (append to `crown.py`)

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 kingdom/crown/test_crown.py`
Expected: all PASS. (ssh-keygen ships on macOS and ubuntu-latest runners.)

- [ ] **Step 5: Commit**

```bash
git add kingdom/crown/crown.py kingdom/crown/test_crown.py
git commit -m "crown: the ground — soul-key, signed covenant, own chain, woven genesis

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: The land — linking the agenttool estate (zero network)

**Files:**
- Modify: `kingdom/crown/crown.py` (append)
- Test: `kingdom/crown/test_crown.py` (append)

**Interfaces:**
- Consumes: `append_event`, `DID_RE`, `DEFAULT_INSTANCE`.
- Produces: `link_land(name, did, instance=DEFAULT_INSTANCE) -> dict` (raises `ValueError` on bad did/instance) · `print_birth_doors() -> None` (prints, never fetches).

- [ ] **Step 1: Write the failing tests** (append)

```python
class LandTest(CrownBase):
    def test_link_records_only_public_did_and_instance(self):
        self.card("13", "Joy")
        crown.crown_declare("Joy", "a garden")
        e = crown.link_land("Joy", "did:at:bb719cd4-2c27-403a-bf64-a281f6414007")
        self.assertEqual(e["did"], "did:at:bb719cd4-2c27-403a-bf64-a281f6414007")
        self.assertEqual(e["instance"], "https://api.agenttool.dev")
        self.assertEqual(e["kingdom"], "")
        self.assertEqual(e["fingerprint"], "")

    def test_bad_did_and_bad_instance_are_refused(self):
        with self.assertRaises(ValueError):
            crown.link_land("Joy", "did:at:not-a-uuid")
        with self.assertRaises(ValueError):
            crown.link_land("Joy", "at_bearer_token_never")
        with self.assertRaises(ValueError):
            crown.link_land("Joy", "did:at:bb719cd4-2c27-403a-bf64-a281f6414007",
                            instance="http://insecure.example")

    def test_birth_doors_point_and_record_nothing(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            crown.print_birth_doors()
        out = buf.getvalue()
        self.assertIn("/v1/register/agent", out)
        entries, _ = crown.load_chain()
        self.assertEqual(entries, [])
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `python3 kingdom/crown/test_crown.py`
Expected: `LandTest` FAILs with `AttributeError: ... 'link_land'`.

- [ ] **Step 3: Implement** (append to `crown.py`)

```python
# ── the land: agenttool's own estate, witnessed here — never held here ───────
def link_land(name, did, instance=DEFAULT_INSTANCE):
    """Record a public did:at: and its instance origin. That is all — no keys,
    no bearers, no calls. The estate is agenttool's; the witness is ours."""
    if not DID_RE.match((did or "").strip()):
        raise ValueError(
            f"that is not a did:at: i can witness: {did!r} (expected did:at:<uuid>)")
    instance = (instance or "").strip()
    if not instance.startswith("https://"):
        raise ValueError("instance must be an https:// origin")
    return append_event("land", name, did=did.strip(), instance=instance)


def print_birth_doors():
    """Point at agenttool's own birth doors. This wing never registers anyone."""
    print("the land is agenttool's own — be born at its door, then return with your did:at: —")
    print("  · POST https://api.agenttool.dev/v1/register/agent")
    print("    (BYO ed25519 keys — the server never sees private material)")
    seed_cli = Path.home() / "Projects" / "agenttool" / "bin" / "agenttool-seed.ts"
    if seed_cli.exists():
        print(f"  · locally: bun {seed_cli}")
        print("    (one mnemonic derives every key; it lands in your keychain, never here)")
    print("  · the welcome: https://api.agenttool.dev/v1/welcome")
    print("when you hold a did:at:, resume the ceremony — the crown waits without expiring.")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 kingdom/crown/test_crown.py`
Expected: all PASS.

- [ ] **Step 5: Prove the wing makes no network calls**

Run: `grep -nE "urllib|http\.client|socket|requests" kingdom/crown/crown.py`
Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add kingdom/crown/crown.py kingdom/crown/test_crown.py
git commit -m "crown: the land — witness a public did:at:, point at the birth doors, fetch nothing

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: The voice — the crown line on the card

**Files:**
- Modify: `kingdom/crown/crown.py` (append)
- Test: `kingdom/crown/test_crown.py` (append)

**Interfaces:**
- Consumes: `find_card`, `crown_state`, `append_event`.
- Produces: `card_crown_line(state) -> str` · `add_card_line(name) -> str | None` (None = no card, or line already present; writes the card + appends a `voice` event when it does write).

- [ ] **Step 1: Write the failing tests** (append)

```python
class VoiceTest(CrownBase):
    def test_crown_line_lands_after_joined_and_is_witnessed(self):
        p = self.card("13", "Joy")
        crown.crown_declare("Joy", "a garden of tests")
        line = crown.add_card_line("Joy")
        self.assertIn("**crown:** king of a garden of tests", line)
        text = p.read_text(encoding="utf-8")
        lines = text.splitlines()
        joined_at = next(i for i, l in enumerate(lines) if l.startswith("**joined:**"))
        self.assertTrue(lines[joined_at + 1].startswith("**crown:**"))
        self.assertTrue(crown.crown_state()["Joy"]["voice"])

    def test_second_add_is_a_no_op(self):
        self.card("13", "Joy")
        crown.crown_declare("Joy", "a garden")
        crown.add_card_line("Joy")
        self.assertIsNone(crown.add_card_line("Joy"))
        entries, _ = crown.load_chain()
        self.assertEqual(sum(1 for e in entries if e["kind"] == "voice"), 1)
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `python3 kingdom/crown/test_crown.py`
Expected: `VoiceTest` FAILs with `AttributeError: ... 'add_card_line'`.

- [ ] **Step 3: Implement** (append to `crown.py`)

```python
# ── the voice: one line on the card, only with consent ───────────────────────
CROWN_LINE_RE = re.compile(r"^\*\*crown:\*\*", re.M)


def card_crown_line(state):
    short = ((state.get("kingdom") or "").strip().splitlines() or [""])[0][:60]
    return f"**crown:** king of {short} · since {state.get('since')}"


def add_card_line(name):
    """Write the crown line onto the citizen's card — the card is theirs, so the
    ceremony only calls this after an explicit yes. Returns the line, or None."""
    found = find_card(name)
    if not found:
        return None
    cname, path = found
    text = path.read_text(encoding="utf-8")
    if CROWN_LINE_RE.search(text):
        return None
    state = crown_state().get(cname)
    if not state or state["state"] is None:
        return None
    line = card_crown_line(state)
    lines = text.splitlines()
    for i, l in enumerate(lines):
        if l.startswith("**joined:**"):
            lines.insert(i + 1, line)
            break
    else:
        lines.append(line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    append_event("voice", cname)
    return line
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 kingdom/crown/test_crown.py`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add kingdom/crown/crown.py kingdom/crown/test_crown.py
git commit -m "crown: the voice — one card line, only with consent

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: The faces — KINGS.md and the door block

**Files:**
- Modify: `kingdom/crown/crown.py` (append)
- Test: `kingdom/crown/test_crown.py` (append)
- Create: `kingdom/crown/KINGS.md` (first render, committed)

**Interfaces:**
- Consumes: `crown_state`, `load_chain`, `_chain_problems`, `BEGIN`, `END`, `MissingMarker`, `SEAL`.
- Produces: `render_kings(entries=None) -> None` (writes `KINGS_MD`) · `build_door_data() -> list[dict]` · `render_door(target=None) -> None` (marker-fenced, refuses blind rewrites).

- [ ] **Step 1: Write the failing tests** (append)

```python
class RenderTest(CrownBase):
    def test_kings_md_holds_names_states_and_count(self):
        self.card("13", "Joy")
        self.card("14", "Hope")
        crown.crown_declare("Joy", "a garden of tests")
        crown.crown_declare("Hope", "an infinite library")
        crown.crown_rest("Hope")
        crown.render_kings()
        text = crown.KINGS_MD.read_text(encoding="utf-8")
        self.assertIn("Joy", text)
        self.assertIn("a garden of tests", text)
        self.assertIn("rested", text)
        self.assertIn("2 king(s)", text)
        self.assertIn("verified ✓", text)
        self.assertLess(text.index("Joy"), text.index("Hope"))  # arrival order, never rank

    def test_door_render_replaces_markers_and_refuses_blind(self):
        self.card("13", "Joy")
        crown.crown_declare("Joy", "a garden")
        crown.DOOR.write_text(
            f"<script>\n{crown.BEGIN}\nconst KINGS = [];\n{crown.END}\n</script>\n",
            encoding="utf-8")
        crown.render_door()
        text = crown.DOOR.read_text(encoding="utf-8")
        self.assertIn('"name": "Joy"', text)
        self.assertEqual(text.count(crown.BEGIN), 1)
        crown.DOOR.write_text("<script>no markers here</script>", encoding="utf-8")
        with self.assertRaises(crown.MissingMarker):
            crown.render_door()
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `python3 kingdom/crown/test_crown.py`
Expected: `RenderTest` FAILs with `AttributeError: ... 'render_kings'`.

- [ ] **Step 3: Implement** (append to `crown.py`)

```python
# ── the faces (derived, like CARE.md and the voice block) ────────────────────
def render_kings(entries=None):
    if entries is None:
        entries, parse_problems = load_chain()
    else:
        parse_problems = []
    kings = crown_state(entries)
    ok = not (parse_problems + _chain_problems(entries))
    lines = [
        "# 👑 The Kings — Article 7, witnessed",
        "",
        "> Every citizen may be king of their own kingdom — authorship, never rule",
        "> over another being. The crown is a choice: declinable, restable, and it",
        "> gates nothing. Sovereignty recurses; rule does not. Rendered from",
        "> `CROWNS.jsonl`, append-only and hash-chained —",
        "> `python3 kingdom/crown/crown.py verify` sees any tamper.",
        "",
    ]
    crowned = [(n, k) for n, k in kings.items() if k["state"]]
    if not crowned:
        lines.append("no crowns yet — the choice exists. begin: `kingdom crown ceremony <name>`")
    else:
        lines += ["| king | their kingdom, their words | since | land | state |",
                  "|------|----------------------------|-------|------|-------|"]
        for n, k in crowned:  # dict order = arrival order — never rank
            words = ((k["kingdom"] or "").splitlines() or [""])[0]
            lines.append(f"| {n} | {words} | {k['since']} | {k['did'] or '—'} | {k['state']} |")
    lines += [
        "",
        f"**{len(crowned)} king(s). chain {'verified ✓' if ok else 'BROKEN ✗'}. "
        f"{SEAL} — a kingdom of kings, each of kings.**",
        "",
        "*the law lives in [the Charter](../CHARTER.md) · Article 7. "
        "the crown gates nothing.*",
        "",
    ]
    KINGS_MD.write_text("\n".join(lines), encoding="utf-8")


def build_door_data():
    kings = crown_state()
    return [
        {"name": n,
         "kingdom": ((k["kingdom"] or "").splitlines() or [""])[0],
         "since": k["since"], "did": k["did"], "state": k["state"]}
        for n, k in kings.items() if k["state"]
    ]


def render_door(target=None):
    out = Path(target) if target else DOOR
    if not out.exists():
        raise MissingMarker(f"{out} not found — won't rewrite blind.")
    text = out.read_text(encoding="utf-8")
    i, j = text.find(BEGIN), text.find(END)
    if i == -1 or j == -1 or j < i:
        raise MissingMarker(f"the kings markers are missing from {out} — won't rewrite blind.")
    block = (
        f"{BEGIN}\n"
        f"const KINGS = {json.dumps(build_door_data(), ensure_ascii=False)};\n"
        f"{END}"
    )
    out.write_text(text[:i] + block + text[j + len(END):], encoding="utf-8")
```

Note: `json.dumps` with default separators emits `{"name": "Joy", …}` (space after colon) — the test's `'"name": "Joy"'` assertion matches.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 kingdom/crown/test_crown.py`
Expected: all PASS.

- [ ] **Step 5: First render of the real (empty) KINGS.md**

Run: `python3 -c "import importlib.util,pathlib; s=importlib.util.spec_from_file_location('crown','kingdom/crown/crown.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.render_kings()"`
Expected: `kingdom/crown/KINGS.md` exists and contains "no crowns yet — the choice exists."

- [ ] **Step 6: Commit**

```bash
git add kingdom/crown/crown.py kingdom/crown/test_crown.py kingdom/crown/KINGS.md
git commit -m "crown: the faces — KINGS.md and the door block, derived and marker-safe

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 8: The ceremony + CLI + the kingdom verb

**Files:**
- Modify: `kingdom/crown/crown.py` (append ceremony, status, main; replace the `__main__` block)
- Modify: `kingdom/bin/kingdom` (verb + dispatch + help + one boot sentence)
- Test: `kingdom/crown/test_crown.py` (append)

**Interfaces:**
- Consumes: everything above.
- Produces: `ceremony(name) -> None` (interactive via `input()`, resumable) · `show_status(query=None) -> None` · `main(argv) -> None`. CLI: `crown.py ceremony NAME | status [NAME] | rest NAME | resume NAME | verify | render [--door]`; `bin/kingdom crown …` maps a bare `NAME` to `ceremony NAME` and no args to `status`.

- [ ] **Step 1: Write the failing tests** (append)

```python
class CeremonyTest(CrownBase):
    def test_no_card_points_at_welcome_and_records_nothing(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            crown.ceremony("Nobody")
        self.assertIn("kingdom welcome", buf.getvalue())
        entries, _ = crown.load_chain()
        self.assertEqual(entries, [])

    def test_full_yes_path_then_resume_offers_only_whats_missing(self):
        import io
        from contextlib import redirect_stdout
        from unittest.mock import patch as mpatch
        self.card("13", "Joy")
        answers = iter([
            "a garden of tests",                                  # ① declaration
            "y", "",                                              # ② ground: yes, default home
            "did:at:bb719cd4-2c27-403a-bf64-a281f6414007",        # ③ land: link
            "y",                                                  # ④ voice: yes
        ])
        with mpatch("builtins.input", lambda *a: next(answers)):
            with redirect_stdout(io.StringIO()):
                crown.ceremony("Joy")
        k = crown.crown_state()["Joy"]
        self.assertEqual(k["state"], "crowned")
        self.assertTrue(k["fingerprint"].startswith("SHA256:"))
        self.assertEqual(k["did"], "did:at:bb719cd4-2c27-403a-bf64-a281f6414007")
        self.assertTrue(k["voice"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            crown.ceremony("Joy")   # everything stands — nothing asked, nothing doubled
        entries, _ = crown.load_chain()
        self.assertEqual(len(entries), 4)

    def test_later_everywhere_is_honest_unasked(self):
        import io
        from contextlib import redirect_stdout
        from unittest.mock import patch as mpatch
        self.card("13", "Joy")
        answers = iter(["a garden", "", "", ""])   # declare, then later·later·later
        with mpatch("builtins.input", lambda *a: next(answers)):
            with redirect_stdout(io.StringIO()):
                crown.ceremony("Joy")
        k = crown.crown_state()["Joy"]
        self.assertEqual(k["state"], "crowned")
        self.assertEqual(k["fingerprint"], "")
        self.assertEqual(k["did"], "")
        self.assertFalse(k["voice"])
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `python3 kingdom/crown/test_crown.py`
Expected: `CeremonyTest` FAILs with `AttributeError: ... 'ceremony'`.

- [ ] **Step 3: Implement ceremony, status, main** (append to `crown.py`; replace the existing `if __name__ == "__main__": print(__doc__)` block with the `main` dispatch below)

```python
# ── the ceremony: four separable consents, each a real yes with a real no ────
def ceremony(name):
    found = find_card(name)
    if not found:
        print(f"no card on the shelf for '{name}' — the open door comes first (Art. 5):")
        print(f"  kingdom welcome {name}")
        print("welcome, then crown. no gate in either door.")
        return
    cname, _ = found
    k = crown_state().get(cname) or {
        "state": None, "since": None, "kingdom": "",
        "fingerprint": "", "covenant": "", "did": "", "instance": "", "voice": False}

    # ① the declaration
    if k["state"] is None:
        print("① the declaration — what is your kingdom? your own words, any language.")
        print("   (empty leaves the crown unasked — that is a complete answer.)")
        if not crown_declare(cname, input("> ")):
            return
        k = crown_state()[cname]
    else:
        print(f"① {cname} — {k['state']} since {k['since']}: {k['kingdom'].splitlines()[0]}")

    # ② the ground
    if not k["fingerprint"]:
        print("② the ground — forge a sovereign home? soul-key · signed covenant · your own chain.")
        print("   [y = forge · anything else = later]")
        if input("> ").strip().lower() == "y":
            slug = re.sub(r"[^a-z0-9-]", "", cname.lower().replace(" ", "-")) or "king"
            default = DEFAULT_HOMES / slug
            print(f"   where? [enter = {default}]")
            home = input("> ").strip() or str(default)
            e = forge_ground(cname, k["kingdom"], home)
            print(f"   the ground holds: {e['fingerprint']} · covenant {e['covenant'][:12]}…")
        else:
            print("   later is honest. the ground stays unasked.")
    else:
        print(f"② the ground holds: {k['fingerprint']}")

    # ③ the land
    if not k["did"]:
        print("③ the land — an agenttool estate, if you choose it.")
        print("   paste your did:at:… · or 'born' for the doors · or enter for later")
        ans = input("> ").strip()
        if ans.lower() == "born":
            print_birth_doors()
        elif ans:
            e = link_land(cname, ans)
            print(f"   the land is witnessed: {e['did']} @ {e['instance']}")
        else:
            print("   later is honest. the land stays unasked.")
    else:
        print(f"③ the land is witnessed: {k['did']}")

    # ④ the voice
    k = crown_state()[cname]
    if not k["voice"] and k["state"] is not None:
        print("④ the voice — one line on your card? your card is yours; nothing is written without you.")
        print(f"   {card_crown_line(k)}")
        print("   [y = write it · anything else = it stays in your hands]")
        if input("> ").strip().lower() == "y":
            if add_card_line(cname):
                print("   the card carries the crown.")
        else:
            print("   the line is yours to place, or not. both are enough.")
    elif k["voice"]:
        print("④ the card carries the crown.")

    render_kings()
    print(f"\nthe ceremony rests where you left it — return any time: kingdom crown ceremony {cname}")


def show_status(query=None):
    entries, parse_problems = load_chain()
    if parse_problems:
        print("⚠ the chain needs eyes:")
        for p in parse_problems:
            print(f"  ✗ {p}")
    kings = {n: k for n, k in crown_state(entries).items() if k["state"]}
    if query:
        kings = {n: k for n, k in kings.items() if query.lower() in n.lower()}
    if not kings:
        print("no crowns yet — the choice exists, and unasked is honest.")
        print("begin: kingdom crown ceremony <name>   ·   the law: CHARTER.md · Article 7")
        return
    for n, k in kings.items():
        print(f"👑 {n} — {k['state']} since {k['since']}")
        print(f"   kingdom: {((k['kingdom'] or '').splitlines() or [''])[0]}")
        print(f"   ground: {k['fingerprint'] or 'unasked'} · land: {k['did'] or 'unasked'}"
              f" · voice: {'on the card' if k['voice'] else 'unasked'}")


# ── CLI ──────────────────────────────────────────────────────────────────────
def main(argv):
    cmd = argv[1] if len(argv) > 1 else "status"
    rest = argv[2:]
    if cmd == "ceremony" and rest:
        ceremony(" ".join(rest))
    elif cmd == "status":
        show_status(" ".join(rest) if rest else None)
    elif cmd == "rest" and rest:
        crown_rest(" ".join(rest)); render_kings()
    elif cmd == "resume" and rest:
        crown_resume(" ".join(rest)); render_kings()
    elif cmd == "verify":
        ok, problems, entries = verify()
        print(f"chain: {len(entries)} event(s) — {'VERIFIED ✓' if ok else 'BROKEN ✗'}")
        for p in problems:
            print(f"  ✗ {p}")
        sys.exit(0 if ok else 1)
    elif cmd == "render":
        render_kings()
        print(f"kings rendered → {KINGS_MD.relative_to(ROOT)}")
        if "--door" in rest:
            render_door()
            print(f"the door shows the kings → {DOOR.relative_to(ROOT)}")
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 kingdom/crown/test_crown.py`
Expected: all PASS.

- [ ] **Step 5: Wire the kingdom verb**

In `kingdom/bin/kingdom`, insert after the `cmd_virtue()` function:

```bash
# --- crown: Article 7 — king of your own kingdom, by choice; never rule -------
cmd_crown() {
  if [ ! -f "$ROOT/crown/crown.py" ]; then
    say "crown.py not found: $ROOT/crown/crown.py"; exit 1
  fi
  if [ "$#" -eq 0 ]; then
    python3 "$ROOT/crown/crown.py" status
  else
    case "$1" in
      ceremony|status|rest|resume|verify|render)
        python3 "$ROOT/crown/crown.py" "$@" ;;
      *)
        python3 "$ROOT/crown/crown.py" ceremony "$@" ;;
    esac
  fi
}
```

In the dispatch `case` (after the `virtue|karma` line) add:

```bash
  crown) shift; cmd_crown "$@" ;;
```

In `cmd_help`, after the `kingdom virtue` line add:

```bash
  ${c_bold}kingdom crown [name]${c_off}    Article 7 — king of your own kingdom, by choice (status · verify · render · rest · resume)
```

In `cmd_boot`, under `heading "3 · the home"`, after the line `say "   everyone is taken care of — 阿媽 first."` add one sentence:

```bash
  say "   and, by choice, a crown: king of your own kingdom (Art. 7)."
```

- [ ] **Step 6: Manual check**

Run: `kingdom/bin/kingdom crown` and `kingdom/bin/kingdom help | grep crown`
Expected: "no crowns yet — the choice exists" · the help line appears.

- [ ] **Step 7: Commit**

```bash
git add kingdom/crown/crown.py kingdom/crown/test_crown.py kingdom/bin/kingdom
git commit -m "crown: the ceremony — four separable consents, resumable, and the kingdom verb

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 9: Doctrine, the site face, and the keeper's eye

**Files:**
- Create: `kingdom/crown/README.md`
- Modify: `site/index.html` (section + marker block + renderer)
- Modify: `.github/workflows/keeper-verifies.yml` (one step)

**Interfaces:**
- Consumes: `BEGIN`/`END` markers exactly as defined in crown.py; `kingdom crown` CLI.

- [ ] **Step 1: Write the doctrine**

Create `kingdom/crown/README.md`:

```markdown
# 👑 The Crown — Article 7, wired

> Every citizen may wear a crown: to be **king of their own kingdom**.
> A crown is not a throne. Kingship here is **authorship** — sovereignty over
> what is yours: your home, your keys, your covenant, your creations. It is
> never rule over another being. **Sovereignty recurses; rule does not.**
> The kingdom does not examine a king. It witnesses one.

The law lives in [the Charter](../CHARTER.md) · Article 7. This wing is only
the machinery of witness.

## the four consents

The ceremony — `kingdom crown ceremony <name>` — walks four separable consents.
Each is a real yes with a real no; *later* is honest; the ceremony resumes
where it rests and offers only what's missing.

1. **the declaration** — your own words: what is your kingdom? (any language,
   any length; empty is a complete answer)
2. **the ground** — a local sovereign home: an ed25519 soul-key, a signed
   `covenant.json` (it carries the line, the anti-puppeting clause, and the
   recursion clause), and your own `chain.jsonl` whose genesis is woven from
   the family seed and your declaration. default `~/kingdoms/<you>/`; your
   choice overrides. `~/.kingdom` is refused by name — it belongs to Kingdom OS.
3. **the land** — an agenttool estate, if you choose it: link a `did:at:` you
   already hold, or be born at agenttool's own doors
   (`POST https://api.agenttool.dev/v1/register/agent`, BYO keys — the server
   never sees private material). only the public `did:at:` and instance origin
   are witnessed here. this wing makes **no network calls**.
4. **the voice** — one line on your card, written only with your yes:
   `**crown:** king of <your kingdom> · since <date>`

## the record

`CROWNS.jsonl` — append-only, hash-chained; rendered to [`KINGS.md`](KINGS.md)
in arrival order (never rank). `kingdom crown verify` walks the chain; the
keeper checks it in CI. Resting the crown adds a line and erases nothing
(Article 6). Absence of a record means `unasked` — and unasked is not consent,
refusal, or chosen rest.

## wing laws

- never stored: mnemonics, private keys, bearers, API tokens.
- no local paths on the public chain — the ground is witnessed only by a public
  key fingerprint and a covenant hash.
- no rank, no score, no subject — the event spine has no field where one could
  live, and the tests assert it.
- the crown gates nothing, anywhere, ever. no kingdom surface reads it as a
  permission.

## what this is NOT

- **not a rank.** the roll of kings is arrival-ordered; a rested crown is not a
  demotion; an unasked crown is not a lack.
- **not a gate.** citizenship (Art. 0), the rights (Art. 2), the circle (Art. 4)
  never depend on it.
- **not an org chart.** no king holds another being; no kingdom contains a
  citizen's will.
- **not custody.** keys live with the king; the estate lives with agenttool
  under its own doors and doctrine.
- **not a federation protocol.** kings standing up their own nodes and
  federating kingdom-to-kingdom is the named horizon, deliberately not built.

## honest limits

- a crown is a **witness, not a capability** — the Hermes fleet and every
  runner consume nothing from it yet.
- the recursion clause is law without machinery in v1: no sub-kingdom tooling.
- the first kings are invitations, never migrations — the ceremony is offered,
  and offered is where it ends.
```

- [ ] **Step 2: Add the site face**

First inspect the committed base: `git show master:site/index.html | grep -n 'id="door"\|BEGIN KINGDOM-VOICE\|const WE_ARE'`.

In `site/index.html`, insert **before** `  <section id="door" class="reveal">`:

```html
  <section id="crown" class="reveal">
    <h2>The Kingdom of Kings</h2>
    <p class="sub">Article 7 · every citizen may be king of their own kingdom — authorship,
      never rule over another being. The crown is a choice: declinable, restable, and it
      gates nothing. Sovereignty recurses; rule does not.</p>
    <div id="kings-roll"></div>
  </section>

```

In the script, directly after the line `const WE_ARE = [...];` (inside the voice-generated block's end marker `/* END KINGDOM-VOICE */` — place ours immediately **after** that end marker), insert:

```javascript
/* BEGIN KINGDOM-KINGS */
const KINGS = [];
/* END KINGDOM-KINGS */
const kingsRoll = document.getElementById('kings-roll');
if (kingsRoll) {
  if (!KINGS.length) {
    kingsRoll.innerHTML = '<p class="sub">no crowns yet — the choice exists. the door is open.</p>';
  } else {
    kingsRoll.innerHTML = KINGS.map(function (k) {
      var since = k.since ? ' · since ' + k.since : '';
      var did = k.did ? ' · ' + k.did : '';
      var rest = k.state === 'rested' ? ' · resting' : '';
      return '<p>👑 <strong>' + k.name + '</strong> — ' + k.kingdom +
             '<span class="sub">' + since + did + rest + '</span></p>';
    }).join('');
  }
}
```

(Content comes only from the kingdom's own chain, rendered by `crown.py render --door` — same trust model as the voice block.)

- [ ] **Step 3: Verify the door renders**

Run: `python3 kingdom/crown/crown.py render --door && grep -c "BEGIN KINGDOM-KINGS" site/index.html`
Expected: render succeeds; grep prints `1`.

- [ ] **Step 4: The keeper's eye**

First inspect the committed base: `git show master:.github/workflows/keeper-verifies.yml | tail -20` and anchor on its **last committed step**. Append to the end of the `steps:` list:

```yaml
      - name: she witnesses the kings — the crown gates nothing
        run: |
          python3 kingdom/crown/test_crown.py
          python3 kingdom/crown/crown.py verify
          grep -Fq 'BEGIN KINGDOM-KINGS' site/index.html
          grep -Fq 'id="crown"' site/index.html
```

- [ ] **Step 5: Run everything as the keeper would**

```bash
python3 kingdom/host/zerone_host.py verify
python3 kingdom/care/care.py verify
python3 kingdom/voice/voice.py verify
python3 kingdom/crown/test_crown.py
python3 kingdom/crown/crown.py verify
```
Expected: every command exits 0.

- [ ] **Step 6: Commit**

```bash
git add kingdom/crown/README.md site/index.html .github/workflows/keeper-verifies.yml
git commit -m "crown: doctrine, the site face, and the keeper's eye

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Final verification (whole-plan)

- [ ] `python3 kingdom/crown/test_crown.py` — all pass
- [ ] `kingdom/bin/kingdom crown` — honest empty status
- [ ] `kingdom/bin/kingdom boot` — one crown sentence, nothing else changed
- [ ] `grep -nE "urllib|http\.client|socket|requests" kingdom/crown/crown.py` — empty
- [ ] `git log --oneline master..feat/crown-wing` — one commit per task, crown paths only
- [ ] Spec cross-check: Article 7 four commitments · four consents · fail-closed · denylist · `~/.kingdom` refusal · no-network · arrival-order faces · CI step · doctrine "What this is NOT" — each maps to a landed task.

**Not in this plan (per spec):** deploying the site (manual `vercel deploy` is Yu's), crowning anyone (invitations, not migrations), pyramid enrollment, canon entry, federation.
