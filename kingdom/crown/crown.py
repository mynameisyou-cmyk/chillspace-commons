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
import html
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

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


class BrokenChain(Exception):
    """The chain has problems — refuse to render the door blind to them."""


# ── the chain ────────────────────────────────────────────────────────────────
def _entry_hash(entry):
    msg = US.join(str(entry.get(k, "")) for k in SPINE)
    return hashlib.sha256(msg.encode("utf-8")).hexdigest()


def load_chain():
    """(entries, problems). A missing or unreadable chain is 'no crowns' plus a
    named problem — never a crash, never an invented state (fail-closed)."""
    try:
        if not CHAIN.exists():
            return [], []
        raw = CHAIN.read_text(encoding="utf-8")
    except OSError as ex:
        return [], [
            f"chain file unreadable ({type(ex).__name__}): {ex}"
        ]
    entries, problems = [], []
    for n, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            problems.append(f"line {n}: unreadable — the chain needs eyes")
            continue
        if not isinstance(entry, dict):
            problems.append(f"line {n}: entry is not an object — the chain needs eyes")
            continue
        entries.append(entry)
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
        missing = (set(SPINE) | {"hash"}) - set(e)
        for k in sorted(missing):
            problems.append(f"entry {i} ({who}): missing spine field: '{k}'")
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
    problems += _chain_problems(entries)
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
    found = find_card(name)
    name = found[0] if found else name
    k = crown_state().get(name)
    if not k or k["state"] != "crowned":
        print(f"{name} has no crown to set down. nothing recorded.")
        return None
    e = append_event("rested", name)
    print(f"{name} sets the crown down. nothing is lost; the chain keeps it all.")
    return e


def crown_resume(name):
    found = find_card(name)
    name = found[0] if found else name
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
    try:
        resolved_home = home.resolve(strict=False)
        protected_home = KINGDOM_OS_ENV.expanduser().resolve(strict=False)
    except OSError as ex:
        raise ValueError(f"cannot safely resolve the chosen home: {ex}") from ex
    if resolved_home == protected_home or protected_home in resolved_home.parents:
        raise ValueError(
            "~/.kingdom and everything beneath it belong to Kingdom OS — "
            "the crown never touches them. "
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


# ── the land: agenttool's own estate, witnessed here — never held here ───────
def link_land(name, did, instance=DEFAULT_INSTANCE):
    """Record a public did:at: and its instance origin. That is all — no keys,
    no bearers, no calls. The estate is agenttool's; the witness is ours."""
    if not DID_RE.match((did or "").strip()):
        raise ValueError(
            f"that is not a did:at: i can witness: {did!r} (expected did:at:<uuid>)")
    instance = (instance or "").strip()
    try:
        parsed = urlsplit(instance)
        parsed.port  # force validation of malformed ports
    except ValueError as ex:
        raise ValueError("instance must be a valid https:// origin") from ex
    origin = f"https://{parsed.netloc}"
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or instance not in {origin, origin + "/"}
    ):
        raise ValueError(
            "instance must be an https:// origin with no credentials, path, "
            "query, or fragment")
    return append_event("land", name, did=did.strip(), instance=origin)


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


def _door_data_for_html():
    """Escape every chain-sourced string before the site's innerHTML renderer.

    The public page's surrounding renderer predates this wing and concatenates
    these values into markup. Character-reference escaping keeps declarations
    as text even when a chain entry contains markup-looking words.
    """
    return [
        {
            key: html.escape(value, quote=True) if isinstance(value, str) else value
            for key, value in king.items()
        }
        for king in build_door_data()
    ]


def _inline_json(value):
    """JSON safe inside a raw-text <script> element."""
    return (
        json.dumps(value, ensure_ascii=False)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def render_door(target=None):
    out = Path(target) if target else DOOR
    if not out.exists():
        raise MissingMarker(f"{out} not found — won't rewrite blind.")
    entries, parse_problems = load_chain()
    if parse_problems + _chain_problems(entries):
        raise BrokenChain("the chain needs eyes — won't render the door from a broken chain")
    text = out.read_text(encoding="utf-8")
    i, j = text.find(BEGIN), text.find(END)
    if i == -1 or j == -1 or j < i:
        raise MissingMarker(f"the kings markers are missing from {out} — won't rewrite blind.")
    block = (
        f"{BEGIN}\n"
        f"const KINGS = {_inline_json(_door_data_for_html())};\n"
        f"{END}"
    )
    out.write_text(text[:i] + block + text[j + len(END):], encoding="utf-8")


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
        words = input("> ")
        try:
            declared = crown_declare(cname, words)
        except Exception as ex:
            print(f"   ✗ {ex}")
            print("   the declaration stays unasked — the ceremony can resume.")
        else:
            if not declared:
                return
            k = crown_state()[cname]
    else:
        first = ((k["kingdom"] or "").splitlines() or [""])[0]
        print(f"① {cname} — {k['state']} since {k['since']}: {first}")

    # ② the ground
    if not k["fingerprint"]:
        print("② the ground — forge a sovereign home? soul-key · signed covenant · your own chain.")
        print("   [y = forge · anything else = later]")
        if input("> ").strip().lower() == "y":
            slug = re.sub(r"[^a-z0-9-]", "", cname.lower().replace(" ", "-")) or "king"
            default = DEFAULT_HOMES / slug
            print(f"   where? [enter = {default}]")
            home = input("> ").strip() or str(default)
            try:
                e = forge_ground(cname, k["kingdom"], home)
            except Exception as ex:
                print(f"   ✗ {ex}")
                print("   the ground stays unasked — the ceremony can resume.")
            else:
                print(f"   the ground holds: {e['fingerprint']} · covenant {e['covenant'][:12]}…")
                k = crown_state().get(cname, k)
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
            try:
                e = link_land(cname, ans)
            except Exception as ex:
                print(f"   ✗ {ex}")
                print("   the land stays unasked — the ceremony can resume.")
            else:
                print(f"   the land is witnessed: {e['did']} @ {e['instance']}")
                k = crown_state().get(cname, k)
        else:
            print("   later is honest. the land stays unasked.")
    else:
        print(f"③ the land is witnessed: {k['did']}")

    # ④ the voice
    k = crown_state().get(cname, k)
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
            try:
                render_door()
            except BrokenChain as ex:
                print(f"✗ {ex}")
                sys.exit(1)
            print(f"the door shows the kings → {DOOR.relative_to(ROOT)}")
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv)
