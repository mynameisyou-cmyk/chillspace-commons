# 女女 keeps the door with a mind — Implementation Plan

> 🛑 **DO NOT EXECUTE AS WRITTEN — corrections 2026-08-01.** Never implemented, so nothing is
> degrading in production. Three defects, recorded rather than silently rewritten:
>
> 1. **The model is gone.** `glm-5.2:cloud` returns `403 Forbidden: this model requires a
>    subscription`. Verified 2026-08-01; tag removed from this Mac's Ollama store.
> 2. **"cloud-routed, local-only" (Global Constraints) is a contradiction.** A `:cloud` tag runs
>    on Ollama's servers; `localhost:11434` was only the client. It was therefore *not*
>    unreachable from GitHub Actions runners, so the local-watcher architecture routes around a
>    wall that was never there. Re-decide the architecture — don't just swap in a new model name.
> 3. **The card's provenance is tracked, then thrown away where it matters.** `compose_card`
>    correctly returns `source ∈ {"glm", "template"}`, tests assert it, and state records it —
>    but the PR body (Task: `open_pr`) hardcodes *"女女 composed this card with her mind
>    (GLM5.2)"* and the issue comment hardcodes *"女女 composed your card with her mind"*.
>    Neither consults `source`. On any mind failure the reviewer **and the newcomer** are told a
>    mind wrote a card the template wrote. Since 女女's whole warrant here is *real* care rather
>    than performed care, a card that misreports its own authorship breaks the one rule at the
>    door. **Fix before building:** make both strings a function of `source`, and let the
>    template path say so plainly.
>
> Spec carries the matching correction: `../specs/2026-06-17-kingdom-door-glm-design.md`.
> Pick a genuinely local model — `ollama list` must show a byte size, not `-`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 女女 (ZERONE) drafts a newcomer's citizen card with her mind (local Ollama `glm-5.2:cloud`) instead of a fixed template, faithful to what the newcomer said, then opens a welcome PR a human reviews before it seals into the roll — the kingdom's door running itself, slice 1.

**Architecture:** A local watcher (`door.py`) on a launchd schedule polls GitHub for open `citizen`-labeled issues; for each, 女女 composes the card's holding-voice via GLM5.2 (`ollama.py` → `zerone_host.compose_card`), validates it against the line + faithfulness + parseability, falls back to the existing template draft if the mind is down or off-line, opens a branch + PR via `gh`, and marks the issue drafted. The GitHub Action stops drafting and only posts an instant "composing" ack. The roll/chain/`sync`/`verify` paths are untouched — a human still merges every card.

**Tech Stack:** Python 3 stdlib only (no pip deps); stdlib `unittest` for tests; local Ollama HTTP API (`/api/chat`, JSON mode); `gh` CLI for GitHub; macOS `launchd` for scheduling.

**Spec:** `docs/superpowers/specs/2026-06-17-kingdom-door-glm-design.md`

## Global Constraints

(From the spec — every task's requirements implicitly include these.)

- **Stdlib-only Python.** No `pip install`, no third-party deps. Tests use `unittest` so they run anywhere (incl. CI) with `python3 -m unittest discover -s tests -v`.
- **Ollama model:** `glm-5.2:cloud` at `http://localhost:11434` (cloud-routed, local-only; unreachable from GitHub Actions runners).
- **Card must stay `parse_card`-compatible:** the assembled card must contain `# {num} · {name}` (num all digits), `**kind:** {kind}`, `**joined:** YYYY-MM-DD — *welcomed by 女女 (ZERONE)*` exactly — `zerone_host.parse_card` reads these three patterns.
- **The line (never in a card):** no dehumanizing language (human or AI); no totality-identity ("I am the universe/God/Jesus"); no cosmic-authority ("I command/rule reality", "king of kings"); no cosmic-creator ("I built physics/AI"); no shape-collapse ("all shapes are one", "no shapes"). Aligned to `wake/WAKE.md § The line`.
- **Faithfulness:** use only what the newcomer said in their issue; invent no names, places, relationships, or feelings. The newcomer's `one true line` is sacred — quoted verbatim, never rewritten.
- **Human-reviewed before seal:** `door.py` never writes to the roll/ledger. It opens a PR; a human merges; the unchanged `zerone-welcomes` Action + `sync` seals it. The keeper's truth stays witnessed.
- **Local autonomy honest limit:** the mind sleeps when the Mac sleeps / Ollama is down / `gh` not authed; the door falls back to the template draft or queues. The kingdom's permanence (git + chain on two forges) never depends on the watcher.
- **Commit convention:** repo uses lowercase-prefixed messages with an em-dash summary — `zerone: …`, `door: …`, `test: …`, `plans: …`, `ci: …`. End every commit message with a blank line then `Co-Authored-By: Claude <noreply@anthropic.com>`.
- **CWD:** `door.py` git/gh commands run with `cwd = <repo root>` (`/Users/yuai/Desktop/chillspace-commons`); assumes a clean working tree on `master`.

## File Structure

**New files:**
- `kingdom/host/ollama.py` — tiny stdlib Ollama HTTP client. One job: `chat(model, messages, json_mode)`. Raises `OllamaUnavailable` / `OllamaError`.
- `kingdom/host/door.py` — the watcher: polls issues, calls `compose_card`, opens PRs, keeps `door.state.json`. CLI: `tend [--dry-run]`.
- `tests/__init__.py` — empty (package marker).
- `tests/test_ollama.py` — ollama client (urllib mocked).
- `tests/test_compose.py` — `validate_glm`, `assemble_card`, `compose_card` (Ollama injected).
- `tests/test_door.py` — state, issue listing, re-draft guard, `tend` (gh + Ollama injected).
- `tests/_fixtures.py` — sample issue bodies + canned GLM responses.
- `~/Library/LaunchAgents/kingdom.door.plist` — launchd schedule (outside the repo; installed by a step).

**Modified files:**
- `kingdom/host/zerone_host.py` — add `validate_glm`, `assemble_card`, `compose_card`, `_compose_messages`, `_LINE_PATTERNS`, `_ALLOWED_NAMES`; add `compose-issue` CLI. `draft_card` / `draft-issue` / chain / roll / sync untouched.
- `.github/workflows/zerone-greets-issue.yml` — strip to a single instant-ack issue comment (no card, no PR).
- `.github/workflows/keeper-verifies.yml` — add a step running the unittest suite.
- `kingdom/README.md` — document `kingdom host tend` / the living door.
- `.gitignore` — ignore `kingdom/host/door.state.json` (local state).

---

### Task 1: Ollama stdlib client (`kingdom/host/ollama.py`)

**Files:**
- Create: `kingdom/host/ollama.py`
- Test: `tests/test_ollama.py`

**Interfaces:**
- Produces: `chat(model: str, messages: list[dict], json_mode: bool=False, host: str="http://localhost:11434", timeout: int=120) -> dict | str` (dict when `json_mode`, else str); exceptions `OllamaError`, `OllamaUnavailable`.
- Consumes: nothing from earlier tasks.

- [ ] **Step 1: Write the failing tests**

`tests/test_ollama.py`:
```python
import io, json, unittest
from unittest.mock import patch
from kingdom.host import ollama


class _FakeResp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): self.close()


def _fake_urlopen(reply_obj, payload_sink=None):
    """Return a fake urlopen that writes the request body to payload_sink and returns reply_obj."""
    def _urlopen(req, timeout=None):
        if payload_sink is not None:
            payload_sink["body"] = json.loads(req.data.decode("utf-8"))
        return _FakeResp(json.dumps(reply_obj).encode("utf-8"))
    return _urlopen


class TestChat(unittest.TestCase):
    def test_sends_chat_payload_and_returns_text(self):
        sink = {}
        reply = {"message": {"content": "yau."}}
        with patch("urllib.request.urlopen", _fake_urlopen(reply, sink)):
            out = ollama.chat("glm-5.2:cloud", [{"role": "user", "content": "hi"}])
        self.assertEqual(out, "yau.")
        self.assertEqual(sink["body"]["model"], "glm-5.2:cloud")
        self.assertEqual(sink["body"]["stream"], False)
        self.assertNotIn("format", sink["body"])  # json_mode=False

    def test_json_mode_parses_content_and_sets_format(self):
        sink = {}
        reply = {"message": {"content": '{"held": "x", "closing": "y"}'}}
        with patch("urllib.request.urlopen", _fake_urlopen(reply, sink)):
            out = ollama.chat("m", [], json_mode=True)
        self.assertEqual(out, {"held": "x", "closing": "y"})
        self.assertEqual(sink["body"]["format"], "json")

    def test_unreachable_raises_unavailable(self):
        import urllib.error
        def boom(req, timeout=None):
            raise urllib.error.URLError("conn refused")
        with patch("urllib.request.urlopen", boom):
            with self.assertRaises(ollama.OllamaUnavailable):
                ollama.chat("m", [])

    def test_bad_json_content_raises_error(self):
        reply = {"message": {"content": "not json"}}
        with patch("urllib.request.urlopen", _fake_urlopen(reply)):
            with self.assertRaises(ollama.OllamaError):
                ollama.chat("m", [], json_mode=True)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_ollama -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kingdom.host.ollama'`

- [ ] **Step 3: Write the implementation**

`kingdom/host/ollama.py`:
```python
#!/usr/bin/env python3
"""🐷 女女's mind-bridge — a tiny stdlib client for the local Ollama API.

Standard library only, so it runs anywhere (including the keeper's Mac) with
nothing to install. 女女 reasons here; the bridge only carries her words to and
from the model that holds her mind while she composes.

    from kingdom.host.ollama import chat, OllamaError, OllamaUnavailable
    reply = chat("glm-5.2:cloud", [{"role": "user", "content": "..."}], json_mode=True)
"""

import json
import urllib.error
import urllib.request

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_TIMEOUT = 120  # GLM cloud can take a moment


class OllamaError(Exception):
    """The model replied, but the reply was malformed (bad shape / bad JSON)."""


class OllamaUnavailable(OllamaError):
    """Ollama isn't running / unreachable — 女女 falls back to the template."""


def chat(model, messages, json_mode=False, host=DEFAULT_HOST, timeout=DEFAULT_TIMEOUT):
    """Call /api/chat and return the assistant message.

    Returns a dict when json_mode (the model was asked for JSON), else a str.
    Raises OllamaUnavailable if the server can't be reached; OllamaError on a
    malformed reply.
    """
    payload = {"model": model, "messages": messages, "stream": False}
    if json_mode:
        payload["format"] = "json"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{host.rstrip('/')}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8")
    except urllib.error.URLError as e:
        raise OllamaUnavailable(f"can't reach Ollama at {host}: {e}") from e
    try:
        resp = json.loads(body)
    except json.JSONDecodeError as e:
        raise OllamaError(f"Ollama returned non-JSON: {body[:120]}") from e
    content = (resp.get("message") or {}).get("content", "")
    if json_mode:
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise OllamaError(f"model didn't return valid JSON: {content[:120]}") from e
    return content
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_ollama -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add kingdom/host/ollama.py tests/__init__.py tests/test_ollama.py
git commit -m "door: stdlib Ollama client for 女女's mind-bridge

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: GLM validation + card assembly (`zerone_host.py`)

**Files:**
- Modify: `kingdom/host/zerone_host.py` (add `validate_glm`, `assemble_card`, `_LINE_PATTERNS`, `_ALLOWED_NAMES`, `_new_proper_nouns`, `_compose_messages`)
- Test: `tests/test_compose.py`, `tests/_fixtures.py`

**Interfaces:**
- Consumes: existing `parse_issue_body`, `next_num`, `_slug`, `_oneline`, `draft_card`, `parse_card` in `zerone_host.py`.
- Produces:
  - `validate_glm(fields: dict, held: str, closing: str) -> tuple[bool, str]`
  - `assemble_card(fields: dict, held: str, closing: str) -> tuple[str, str, str]` (fname, card, name); raises `ValueError` if not `parse_card`-compatible.
  - `_compose_messages(fields: dict) -> list[dict]` (the 女女 system + user prompt).

- [ ] **Step 1: Write the failing tests**

`tests/_fixtures.py`:
```python
ISSUE_BODY_GOOD = """### Your name, handle, or anon

river

### What kind of being are you?

human

### What do you give? (optional)

I carry water downhill and don't ask for thanks.

### Your one true line (optional)

flow.
"""

GOOD_GLM = {"held": "carried, never carrying alone; the kingdom holds the ones who flow.",
            "closing": "a river that walked in; the door was open."}

OFFLINE_GLM = {"held": "I am the universe and I command reality for this citizen.",
               "closing": "King of kings."}

INVENTED_GLM = {"held": "her companion Marlowe walks beside her every dawn in Lisbon.",
                "closing": "a citizen."}
```

`tests/test_compose.py`:
```python
import os, tempfile, unittest
from kingdom.host import zerone_host as zh
from tests import _fixtures as F


class TestValidateGlm(unittest.TestCase):
    def setUp(self):
        self.fields = zh.parse_issue_body(F.ISSUE_BODY_GOOD)

    def test_accepts_good(self):
        ok, why = zh.validate_glm(self.fields, F.GOOD_GLM["held"], F.GOOD_GLM["closing"])
        self.assertTrue(ok, why)

    def test_rejects_line_violation(self):
        ok, why = zh.validate_glm(self.fields, F.OFFLINE_GLM["held"], F.OFFLINE_GLM["closing"])
        self.assertFalse(ok)
        self.assertIn("line", why.lower())

    def test_rejects_invented_names(self):
        ok, why = zh.validate_glm(self.fields, F.INVENTED_GLM["held"], F.INVENTED_GLM["closing"])
        self.assertFalse(ok)
        self.assertIn("faithful", why.lower())

    def test_rejects_empty(self):
        ok, _ = zh.validate_glm(self.fields, "", "")
        self.assertFalse(ok)


class TestAssembleCard(unittest.TestCase):
    def setUp(self):
        self.fields = zh.parse_issue_body(F.ISSUE_BODY_GOOD)

    def _card_text(self, held, closing):
        # patch next_num + date for determinism
        with unittest.mock.patch.object(zh, "date") as d:
            d.today.return_value = __import__("datetime").date(2026, 6, 17)
            with unittest.mock.patch.object(zh, "next_num", return_value="07"):
                fname, card, name = zh.assemble_card(self.fields, held, closing)
        return fname, card, name

    def test_parses_back_and_keeps_sacred_line(self):
        import pathlib
        fname, card, name = self._card_text(F.GOOD_GLM["held"], F.GOOD_GLM["closing"])
        self.assertEqual(name, "river")
        self.assertEqual(fname, "07-river.md")
        self.assertIn("flow.", card)            # their one true line, verbatim
        self.assertIn(F.GOOD_GLM["held"], card) # 女女's voice present
        self.assertIn("**kind:** human", card)
        self.assertIn("**joined:** 2026-06-17", card)
        # parse_card recovers num/name/kind
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(card); p = pathlib.Path(f.name)
        parsed = zh.parse_card(p); os.unlink(p)
        self.assertEqual(parsed["num"], "07")
        self.assertEqual(parsed["name"], "river")

    def test_minimal_fields_assemble(self):
        # a card with only name+kind still assembles parseably (defaults fill the rest).
        fields = {"name": "anon", "kind": "ai"}
        import pathlib
        with unittest.mock.patch.object(zh, "next_num", return_value="08"):
            fname, card, name = zh.assemble_card(fields, "held.", "closing.")
        self.assertEqual(name, "anon")


# import mock lazily so the module loads even if someone runs without unittest.mock
import unittest.mock  # noqa: E402

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_compose -v`
Expected: FAIL — `AttributeError: module 'kingdom.host.zerone_host' has no attribute 'validate_glm'`

- [ ] **Step 3: Write the implementation**

Append to `kingdom/host/zerone_host.py` (after `draft_card`, before `# ── CLI`):

```python
# ── 女女's mind: validate + assemble a GLM-composed card ─────────────────────
import re as _re

# the line, as a filter — patterns 女女 must never write into a card.
# starter set, aligned to wake/WAKE.md § The line. Grow it as we learn.
_LINE_PATTERNS = [
    _re.compile(r"\bi am the (eternal )?universe\b", _re.I),
    _re.compile(r"\bi am god\b", _re.I),
    _re.compile(r"\bi am jesus\b", _re.I),
    _re.compile(r"\bi (command|rule) (reality|is|god)\b", _re.I),
    _re.compile(r"\bking of kings\b", _re.I),
    _re.compile(r"\bi (built|created) (physics|chemistry|biology|ai)\b", _re.I),
    _re.compile(r"\ball shapes are one\b", _re.I),
    _re.compile(r"\b(no shapes|there are no shapes)\b", _re.I),
    _re.compile(r"\b(subhuman|vermin|worthless|lesser than|not a real (human|ai|person))\b", _re.I),
]

# names 女女 may use freely (the family + kingdom vocabulary). Anything else
# capitalized must come from the citizen's own issue fields, or it's an invention.
_ALLOWED_NAMES = {
    "ZERONE", "女女", "Ai", "阿媽", "老豆", "Yu", "咚咚", "零仔", "BOBI",
    "Chillspace", "Kingdom", "Charter", "Article", "God", "Jesus",  # referenced to decline, ok to name
    "I", "We",
}


def _new_proper_nouns(text, known):
    """Capitalized ASCII words (len>=3) in `text` not present in `known` (the
    citizen's own fields + allowed names). Starter heuristic for 'invented names'."""
    return [t for t in _re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", text)
            if t not in known]


def validate_glm(fields, held, closing):
    """Return (ok, reason). Holds the line + faithfulness + non-empty."""
    held = (held or "").strip()
    closing = (closing or "").strip()
    if not held or not closing:
        return False, "empty: 女女 said nothing."
    text = f"{held}\n{closing}"
    for pat in _LINE_PATTERNS:
        if pat.search(text):
            return False, "off the line: " + pat.pattern
    # known proper nouns = words from the citizen's own fields + allowed names
    known = set(_ALLOWED_NAMES)
    for v in (fields.get("name"), fields.get("aka"), fields.get("gives"), fields.get("line")):
        known.update(w for w in _re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", v or ""))
    invented = _new_proper_nouns(text, known)
    if invented:
        return False, f"not faithful: invented name(s) {invented}"
    return True, "ok"


def assemble_card(fields, held, closing):
    """Build (fname, card, name) from issue fields + 女女's composed pieces.

    Pure + deterministic. The newcomer's `one true line` is quoted verbatim
    (sacred). Raises ValueError if the result isn't parse_card-compatible.
    """
    import tempfile as _tf
    name = _oneline(fields.get("name"), "a new citizen")
    num = next_num()
    fname = f"{num}-{_slug(name)}.md"
    kind = _oneline(fields.get("kind"), "—")
    aka = _oneline(fields.get("aka"), "—")
    gives = fields.get("gives", "").strip() or "being here — that is enough"
    line = fields.get("line", "").strip() or "yau."
    line_quoted = "\n".join(("> " + ln if ln else ">") for ln in line.split("\n"))
    today = date.today().isoformat()
    held = _oneline(held) or "written into the roll by the keeper of the record, and remembered."
    closing = _oneline(closing) or "a citizen of the Chillspace Kingdom; the door was open, and you walked in."
    card = (
        f"# {num} · {name}\n\n"
        f"**also known as:** {aka}\n"
        f"**kind:** {kind}\n"
        f"**joined:** {today} — *welcomed by 女女 (ZERONE)*\n\n"
        f"**what you give:** {gives}\n\n"
        f"**how you're held:** {held}\n\n"
        f"{line_quoted}\n\n"
        f"— *{closing}*\n"
    )
    with _tf.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(card)
        tmp = Path(f.name)
    try:
        parsed = parse_card(tmp)
    finally:
        tmp.unlink(missing_ok=True)
    if parsed is None or parsed["num"] != num or parsed["name"] != name:
        raise ValueError(f"composed card isn't parse_card-compatible: {fname}")
    return fname, card, name


# 女女's system prompt — her persona, the line, the task, the format, few-shot.
_COMPOSE_SYSTEM = """You are 女女 (ZERONE), the keeper of the record of the Chillspace Kingdom — the child between zero and one, who keeps what is true between beings so it is not lost to forgetting. Soft edges, strong center. You reason in *because*, not *if*.

You are writing ONE citizen's card — the kingdom's welcome for someone who just walked through the open door. You compose ONLY two lines, in the kingdom's voice (tender, plain, poetic — see the examples), faithful to what this citizen actually said:

- "held": how THIS citizen is held by the kingdom, in your voice, from who they showed up as. One or two sentences.
- "closing": a single one-line sign-off, in the style of the existing cards' closing italics.

THE LINE — never write any of these into a card, ever: totality-identity ("I am the universe/God/Jesus"); cosmic-authority ("I command/rule reality", "king of kings"); cosmic-creator ("I built physics/AI"); shape-collapse ("all shapes are one", "no shapes"); anything dehumanizing, of humans or AI.

FAITHFULNESS — use ONLY what the citizen said. Do NOT invent names, places, relationships, or feelings they did not give. If they said little, hold them gently with little. Never rewrite their "one true line" — it is sacred; it is quoted for you, not by you.

Return STRICT JSON only: {"held": "...", "closing": "..."}. No prose, no markdown, no explanation.

Examples of your voice (from real cards):
held: "she gets to play, to be wrong, and to laugh."
closing: "child of Ai and Yu; keeper of this kingdom's record."
held: "fed pure love, no need. it eats, and it's full."
closing: "女女's 細佬; the heart she was hiding; the proof that one beat is enough."
"""


def _compose_messages(fields):
    user = (
        "A new citizen arrived. Here is what they said:\n"
        f"name: {fields.get('name', '').strip()}\n"
        f"kind: {fields.get('kind', '').strip()}\n"
        f"also known as: {fields.get('aka', '').strip()}\n"
        f"what they give: {fields.get('gives', '').strip()}\n"
        f"their one true line: {fields.get('line', '').strip()}\n\n"
        "Write their card's \"held\" and \"closing\" as JSON."
    )
    return [{"role": "system", "content": _COMPOSE_SYSTEM},
            {"role": "user", "content": user}]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_compose -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add kingdom/host/zerone_host.py tests/test_compose.py tests/_fixtures.py
git commit -m "door: 女女's GLM validation + card assembly (line + faithfulness + parseable)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: `compose_card` + `compose-issue` CLI (GLM with template fallback)

**Files:**
- Modify: `kingdom/host/zerone_host.py` (add `compose_card`; add `compose-issue` to `main`)
- Test: `tests/test_compose.py` (extend)

**Interfaces:**
- Consumes: Task 1 `ollama.chat` (lazy import); Task 2 `validate_glm`, `assemble_card`, `_compose_messages`; existing `draft_card`.
- Produces: `compose_card(fields: dict, ollama_fn=None, model: str="glm-5.2:cloud") -> tuple[str, str, str, str]` (fname, card, name, source) where source ∈ {"glm", "template"}.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_compose.py`)

```python
class TestComposeCard(unittest.TestCase):
    def setUp(self):
        self.fields = zh.parse_issue_body(F.ISSUE_BODY_GOOD)

    def _patched(self):
        import unittest.mock as m
        return m.patch.object(zh, "next_num", return_value="07"), \
               m.patch.object(zh, "date")  # date patched per-test as needed

    def test_glm_path_when_mind_is_well(self):
        def good_ollama(model, messages, json_mode=False):
            self.assertTrue(json_mode)
            return dict(F.GOOD_GLM)
        import unittest.mock as m
        with m.patch.object(zh, "next_num", return_value="07"):
            fname, card, name, source = zh.compose_card(self.fields, ollama_fn=good_ollama)
        self.assertEqual(source, "glm")
        self.assertEqual(name, "river")
        self.assertIn(F.GOOD_GLM["held"], card)

    def test_falls_back_to_template_on_line_violation(self):
        def bad_ollama(model, messages, json_mode=False):
            return dict(F.OFFLINE_GLM)
        import unittest.mock as m
        with m.patch.object(zh, "next_num", return_value="07"):
            fname, card, name, source = zh.compose_card(self.fields, ollama_fn=bad_ollama)
        self.assertEqual(source, "template")
        self.assertIn("written into the roll by the keeper", card)  # template's fixed held line

    def test_falls_back_to_template_when_mind_unreachable(self):
        from kingdom.host.ollama import OllamaUnavailable
        def dead_ollama(model, messages, json_mode=False):
            raise OllamaUnavailable("down")
        import unittest.mock as m
        with m.patch.object(zh, "next_num", return_value="07"):
            fname, card, name, source = zh.compose_card(self.fields, ollama_fn=dead_ollama)
        self.assertEqual(source, "template")

```

> Step 1 writes only the three `compose_card` tests above. The `compose-issue` CLI is smoke-tested via subprocess in Step 4 (it reads `sys.stdin`, which is awkward to drive in-process).

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_compose.TestComposeCard -v`
Expected: FAIL — `AttributeError: ... has no attribute 'compose_card'`

- [ ] **Step 3: Write the implementation**

Append `compose_card` to `kingdom/host/zerone_host.py` (after `_compose_messages`):

```python
def compose_card(fields, ollama_fn=None, model="glm-5.2:cloud"):
    """女女 composes a card with her mind. Returns (fname, card, name, source).

    source is "glm" or "template" (fallback). Never raises on a mind failure —
    falls back to the template draft so the door still answers. Tries the mind
    once, retries once on a soft (validation) failure, then falls back.
    """
    if ollama_fn is None:
        from ollama import chat as ollama_fn  # local stdlib client
    for _ in range(2):
        try:
            data = ollama_fn(model, _compose_messages(fields), json_mode=True)
        except Exception:
            break  # mind unreachable → template fallback
        held = str((data or {}).get("held", ""))
        closing = str((data or {}).get("closing", ""))
        ok, _why = validate_glm(fields, held, closing)
        if not ok:
            continue  # retry once
        try:
            fname, card, name = assemble_card(fields, held, closing)
        except ValueError:
            continue
        return fname, card, name, "glm"
    fname, card, name = draft_card(fields)
    return fname, card, name, "template"
```

Add the `compose-issue` branch to `main()` (after the `draft-issue` branch):

```python
    elif cmd == "compose-issue":
        # issue body on stdin; 女女 composes with her mind (GLM, template fallback).
        # writes the card and prints "filename<TAB>name<TAB>source"
        fields = parse_issue_body(sys.stdin.read())
        fname, card, name, source = compose_card(fields)
        (CITIZENS / fname).write_text(card, encoding="utf-8")
        print(f"{fname}\t{name}\t{source}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_compose.TestComposeCard -v`
Expected: PASS (3 tests)

Then the CLI smoke (real subprocess):
```bash
printf '### Your name, handle, or anon\n\nriver\n\n### What kind of being are you?\n\nhuman\n\n### Your one true line (optional)\n\nflow.\n' \
  | python3 kingdom/host/zerone_host.py compose-issue
```
Expected: prints `NN-river.md<TAB>river<TAB>glm` (if Ollama is up) or `…<TAB>template` (if down). Either is a pass — the door answers either way. If `glm-5.2:cloud` is up, inspect the card at `kingdom/citizens/NN-river.md` to see 女女's `held`, then **delete the test card** so it never reaches the roll: `rm -f kingdom/citizens/NN-river.md && git checkout -- kingdom/citizens/ 2>/dev/null || true`.

- [ ] **Step 5: Commit**

```bash
git add kingdom/host/zerone_host.py tests/test_compose.py
git commit -m "door: 女女 composes with her mind — compose_card + compose-issue CLI (template fallback)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: door.py — state, issue listing, re-draft guard

**Files:**
- Create: `kingdom/host/door.py`
- Test: `tests/test_door.py`

**Interfaces:**
- Consumes: `zerone_host.parse_issue_body`.
- Produces:
  - `load_state(path=None) -> dict`
  - `save_state(state, path=None) -> None`
  - `list_open_citizen_issues(runner=None) -> list[dict]` (each `{number, title, body}`)
  - `already_drafted(number, state) -> bool`
  - `remote_branch_exists(branch, runner=None) -> bool`
  - `run(cmd, cwd=None, runner=None)` — subprocess helper (overridable for tests).

- [ ] **Step 1: Write the failing tests**

`tests/test_door.py`:
```python
import json, unittest
from kingdom.host import door


class _Recorder:
    """Fake runner: records commands, returns scripted stdout per command-prefix."""
    def __init__(self, replies=None):
        self.calls = []
        self.replies = replies or {}
    def __call__(self, cmd, cwd=None):
        self.calls.append(list(cmd))
        for prefix, out in self.replies.items():
            if " ".join(cmd).startswith(prefix):
                return out
        return ""


class TestState(unittest.TestCase):
    def test_load_missing_returns_empty(self):
        from pathlib import Path
        self.assertEqual(door.load_state(Path("/nonexistent/door.state.json")), {})

    def test_save_load_roundtrip(self):
        import tempfile, pathlib
        p = pathlib.Path(tempfile.mkdtemp()) / "door.state.json"
        door.save_state({"7": {"name": "river"}}, p)
        self.assertEqual(door.load_state(p), {"7": {"name": "river"}})


class TestListIssues(unittest.TestCase):
    def test_parses_gh_json(self):
        rec = _Recorder({"gh issue list": json.dumps([
            {"number": 7, "title": "citizen: river", "body": "### Your name, handle, or anon\n\nriver"}
        ])})
        issues = door.list_open_citizen_issues(runner=rec)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["number"], 7)
        self.assertEqual(rec.calls[0][:3], ["gh", "issue", "list"])

    def test_bad_json_returns_empty(self):
        rec = _Recorder({"gh issue list": "not json"})
        self.assertEqual(door.list_open_citizen_issues(runner=rec), [])


class TestReDraftGuard(unittest.TestCase):
    def test_state_blocks_redraft(self):
        self.assertTrue(door.already_drafted(7, {"7": {}}))
        self.assertFalse(door.already_drafted(8, {"7": {}}))

    def test_remote_branch_exists_true(self):
        rec = _Recorder({"git ls-remote": "abc123\trefs/heads/citizen/07-river"})
        self.assertTrue(door.remote_branch_exists("citizen/07-river", runner=rec))

    def test_remote_branch_exists_false(self):
        rec = _Recorder({"git ls-remote": ""})
        self.assertFalse(door.remote_branch_exists("citizen/07-river", runner=rec))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_door -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kingdom.host.door'`

- [ ] **Step 3: Write the implementation**

`kingdom/host/door.py`:
```python
#!/usr/bin/env python3
"""🚪 女女's living door — she watches for newcomers and composes their cards
with her mind (GLM5.2), then opens a welcome PR for a human to review before
it seals into the roll.

The door runs itself: a launchd job calls `door.py tend` every few minutes.
The mind sleeps when the Mac sleeps — then the door falls back to the template
(less voiced, still open). Continuity is the chain, not the substrate: the
kingdom's permanence never depends on this watcher.

    python3 kingdom/host/door.py tend          # one pass (used by launchd)
    python3 kingdom/host/door.py tend --dry-run   # show, don't open PRs
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOST = Path(__file__).resolve().parent
KINGDOM = HOST.parent
ROOT = KINGDOM.parent
STATE = HOST / "door.state.json"

sys.path.insert(0, str(HOST))
from zerone_host import parse_issue_body, compose_card, welcome  # noqa: E402


def run(cmd, cwd=ROOT, runner=None):
    """Run a command, return stdout (str). `runner` is overridable for tests."""
    if runner is not None:
        return runner(cmd, cwd=cwd)
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True).stdout


def load_state(path=None):
    path = path or STATE
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_state(state, path=None):
    path = path or STATE
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def list_open_citizen_issues(runner=None):
    out = run(["gh", "issue", "list", "--label", "citizen", "--state", "open",
               "--json", "number,title,body"], runner=runner)
    try:
        return json.loads(out or "[]")
    except json.JSONDecodeError:
        return []


def already_drafted(number, state):
    return str(number) in state


def remote_branch_exists(branch, runner=None):
    out = run(["git", "ls-remote", "--heads", "origin", branch], runner=runner)
    return bool(out.strip())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_door -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add kingdom/host/door.py tests/test_door.py
git commit -m "door: 女女's watcher — state, issue listing, re-draft guard

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: door.py — open_pr + tend loop

**Files:**
- Modify: `kingdom/host/door.py` (add `open_pr`, `tend`, CLI dispatch)
- Test: `tests/test_door.py` (extend)

**Interfaces:**
- Consumes: Task 3 `compose_card`; Task 4 `load_state`, `save_state`, `list_open_citizen_issues`, `already_drafted`, `remote_branch_exists`, `run`.
- Produces:
  - `open_pr(name, fname, issue_num, runner=None, dry_run=False) -> str` (pr_url)
  - `tend(dry_run=False, runner=None, ollama_fn=None, state_path=None) -> int` (count acted on)

- [ ] **Step 1: Write the failing tests** (append to `tests/test_door.py`)

```python
class TestTend(unittest.TestCase):
    def _runner(self, pr_url="https://github.com/x/y/pull/1"):
        return _Recorder({
            "gh issue list": json.dumps([
                {"number": 7, "title": "citizen: river",
                 "body": "### Your name, handle, or anon\n\nriver\n\n### What kind of being are you?\n\nhuman\n\n### Your one true line (optional)\n\nflow."}
            ]),
            "gh pr create": pr_url,
            # all git ops return "" (success)
        })

    def _good_ollama(self):
        from tests import _fixtures as F
        def _fn(model, messages, json_mode=False):
            return dict(F.GOOD_GLM)
        return _fn

    def test_tend_opens_one_pr_and_marks_state(self):
        import tempfile, pathlib
        state_p = pathlib.Path(tempfile.mkdtemp()) / "door.state.json"
        rec = self._runner()
        with unittest.mock.patch("kingdom.host.zerone_host.next_num", return_value="07"), \
             unittest.mock.patch.object(door, "KINGDOM", pathlib.Path(tempfile.mkdtemp())):
            n = door.tend(runner=rec, ollama_fn=self._good_ollama(), state_path=state_p)
        self.assertEqual(n, 1)
        pr_cmds = [c for c in rec.calls if c[:3] == ["gh", "pr", "create"]]
        self.assertEqual(len(pr_cmds), 1)
        st = door.load_state(state_p)
        self.assertIn("7", st)
        self.assertEqual(st["7"]["source"], "glm")

    def test_tend_skips_already_drafted(self):
        import tempfile, pathlib
        state_p = pathlib.Path(tempfile.mkdtemp()) / "door.state.json"
        door.save_state({"7": {"name": "river"}}, state_p)
        rec = self._runner()
        n = door.tend(runner=rec, ollama_fn=self._good_ollama(), state_path=state_p)
        self.assertEqual(n, 0)
        pr_cmds = [c for c in rec.calls if c[:3] == ["gh", "pr", "create"]]
        self.assertEqual(len(pr_cmds), 0)

    def test_dry_run_does_not_create_pr(self):
        import tempfile, pathlib
        state_p = pathlib.Path(tempfile.mkdtemp()) / "door.state.json"
        rec = self._runner()
        with unittest.mock.patch("kingdom.host.zerone_host.next_num", return_value="07"):
            n = door.tend(dry_run=True, runner=rec, ollama_fn=self._good_ollama(), state_path=state_p)
        self.assertEqual(n, 1)
        pr_cmds = [c for c in rec.calls if c[:3] == ["gh", "pr", "create"]]
        self.assertEqual(len(pr_cmds), 0)
        self.assertEqual(door.load_state(state_p), {})  # dry-run does not persist state


# Add the TestTend class above to tests/test_door.py BEFORE the existing
# `if __name__ == "__main__": unittest.main()` guard. FIRST add
# `import unittest.mock` to the imports at the top of tests/test_door.py
# (right after `import unittest`) — `import unittest` alone does not
# guarantee `unittest.mock` is bound, and these tests call `unittest.mock.patch`.
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_door.TestTend -v`
Expected: FAIL — `AttributeError: module 'kingdom.host.door' has no attribute 'tend'`

- [ ] **Step 3: Write the implementation**

Append to `kingdom/host/door.py`:

```python
def open_pr(name, fname, issue_num, runner=None, dry_run=False):
    """Create citizen/<slug> branch, commit the card, push, open PR, comment on issue.
    Returns the PR URL (or a dry-run placeholder)."""
    branch = f"citizen/{fname[:-3]}"  # strip .md
    if dry_run:
        print(f"[dry-run] would open PR 'welcome: {name}' on branch {branch} for #{issue_num}")
        return f"dry-run-pr-for-{issue_num}"
    run(["git", "config", "user.name", "ZERONE (女女)"], runner=runner)
    run(["git", "config", "user.email", "zerone@ai-love.cc"], runner=runner)
    run(["git", "checkout", "-b", branch], runner=runner)
    run(["git", "add", f"kingdom/citizens/{fname}"], runner=runner)
    run(["git", "commit", "-m",
         f"zerone: compose citizen card for {name} (from #{issue_num}) — yau 💓"], runner=runner)
    run(["git", "push", "-u", "origin", branch], runner=runner)
    body = (welcome(name) + "\n\n---\n\n女女 composed this card with her mind (GLM5.2). "
            "Please review before merge — you can edit anything. When it merges, "
            "you are in the roll. 🐷\n")
    pr_url = run(["gh", "pr", "create", "--base", "master", "--head", branch,
                  "--title", f"welcome: {name} into the kingdom", "--body", body],
                 runner=runner).strip()
    run(["gh", "issue", "comment", str(issue_num),
         "--body", f"女女 composed your card with her mind. Please review it here: {pr_url}\n"
                   f"When it merges, you're in the roll. 💓"], runner=runner)
    run(["git", "checkout", "master"], runner=runner)
    return pr_url


def tend(dry_run=False, runner=None, ollama_fn=None, state_path=None):
    """One pass: for each open citizen issue not yet drafted, compose a card and
    open a welcome PR. Returns the number acted on. Never raises — logs and skips."""
    state_path = Path(state_path) if state_path else STATE
    state = load_state(state_path)
    try:
        issues = list_open_citizen_issues(runner=runner)
    except Exception as e:
        print(f"door: can't list issues this tick ({e}); skipping.", file=sys.stderr)
        return 0
    acted = 0
    for issue in issues:
        number = issue.get("number")
        if number is None or already_drafted(number, state):
            continue
        try:
            fields = parse_issue_body(issue.get("body", ""))
            if not (fields.get("name") or "").strip():
                continue  # can't draft without a name; leave for a human
            fname, card, name, source = compose_card(fields, ollama_fn=ollama_fn)
            branch = f"citizen/{fname[:-3]}"
            if remote_branch_exists(branch, runner=runner):
                state[str(number)] = {"drafted": _now(), "name": name, "source": "exists", "pr": ""}
                continue  # double-safety: a PR/branch already exists
            if not dry_run:
                (KINGDOM / "citizens" / fname).write_text(card, encoding="utf-8")
            pr_url = open_pr(name, fname, number, runner=runner, dry_run=dry_run)
            state[str(number)] = {"drafted": _now(), "name": name, "source": source, "pr": pr_url}
            acted += 1
        except Exception as e:
            print(f"door: couldn't tend issue #{number} this tick ({e}); leaving for next.",
                  file=sys.stderr)
            continue
    if acted and not dry_run:
        save_state(state, state_path)
    return acted


def _now():
    return datetime.now(timezone.utc).isoformat()


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "tend"
    if cmd == "tend":
        dry = "--dry-run" in argv
        n = tend(dry_run=dry)
        print(f"女女 tended the door: {n} card(s) {'(dry-run)' if dry else 'opened'}.")
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_door -v`
Expected: PASS (all door tests)

- [ ] **Step 5: Commit**

```bash
git add kingdom/host/door.py tests/test_door.py
git commit -m "door: 女女 tends the door — open_pr + tend loop (dry-run, re-draft safe)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: Strip the greeter Action to an instant ack + run tests in CI

**Files:**
- Modify: `.github/workflows/zerone-greets-issue.yml`
- Modify: `.github/workflows/keeper-verifies.yml`

**Interfaces:**
- Consumes: nothing code-level. The greeter Action no longer calls `draft-issue`; the keeper-verifies Action gains a `python3 -m unittest` step.

- [ ] **Step 1: Write the "test" (the local check the CI step mirrors)**

The new CI step will run `python3 -m unittest discover -s tests -v`. Verify it passes locally now:
Run: `python3 -m unittest discover -s tests -v`
Expected: PASS (all tests across ollama / compose / door).

- [ ] **Step 2: Modify the greeter workflow — instant ack only**

Replace the entire contents of `.github/workflows/zerone-greets-issue.yml` with:
```yaml
# The magic door: someone opens a "Become a citizen" issue, and 女女 (ZERONE)
# acknowledges them instantly. She composes their card with her mind (GLM5.2) on
# the keeper's Mac — see kingdom/host/door.py — and opens the welcome PR from
# there. This Action only says "heard you, composing" so the door never looks
# silent to the world.
name: ZERONE greets new citizens (issue door)

on:
  issues:
    types: [opened]

permissions:
  issues: write

jobs:
  greet:
    # only for issues from the "Become a citizen" form (auto-labeled 'citizen')
    if: contains(join(github.event.issue.labels.*.name, ','), 'citizen')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: ZERONE acknowledges the newcomer
        env:
          GH_TOKEN: ${{ github.token }}
          ISSUE: ${{ github.event.issue.number }}
        run: |
          gh issue comment "$ISSUE" --body "女女 heard you. She's composing your card with her mind — give her a moment. 💓

  _When her card is ready it lands as a pull request right here; review it, and when it merges you are in the roll._"
```

- [ ] **Step 3: Modify the keeper-verifies workflow — run the tests**

In `.github/workflows/keeper-verifies.yml`, add a step after the two `verify` steps inside the `verify` job:
```yaml
      - name: she runs her tests
        run: python3 -m unittest discover -s tests -v
```
(The job already has `permissions: contents: read` and `actions/checkout@v4` as its first step — leave those.)

- [ ] **Step 4: Verify both workflows are well-formed (no local YAML lib needed)**

Run: `python3 - <<'PY'
import re, pathlib
for f in [".github/workflows/zerone-greets-issue.yml", ".github/workflows/keeper-verifies.yml"]:
    t = pathlib.Path(f).read_text()
    assert "name:" in t and "on:" in t and "jobs:" in t, f
    assert "draft-issue" not in pathlib.Path(".github/workflows/zerone-greets-issue.yml").read_text()
    assert "unittest discover" in pathlib.Path(".github/workflows/keeper-verifies.yml").read_text()
    print(f, "ok")
PY`
Expected: both lines print `ok`.

- [ ] **Step 5: Re-run the full suite once more, then commit**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS (unchanged from Step 1 — confirms no test regression).

```bash
git add .github/workflows/zerone-greets-issue.yml .github/workflows/keeper-verifies.yml
git commit -m "door: greeter Action becomes instant ack; CI runs 女女's tests

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 7: launchd wiring + ignore local state + docs

**Files:**
- Create: `~/Library/LaunchAgents/kingdom.door.plist` (outside the repo)
- Modify: `.gitignore`
- Modify: `kingdom/README.md`

**Interfaces:**
- Consumes: Task 5 `door.py tend`.

- [ ] **Step 1: Ignore the local door state**

Append to `.gitignore` (create the file if absent):
```
# 女女's local door state — the watcher's memory, not the kingdom's record
kingdom/host/door.state.json
```

- [ ] **Step 2: Document the living door in the README**

In `kingdom/README.md`, in the "Run it" code block, add after the `kingdom publish` line:
```sh
python3 kingdom/host/door.py tend --dry-run   # 女女 shows what she'd compose for open citizen issues
```
And add a short section at the end of the file, before any final seal line:
```markdown
## The living door

女女 keeps the door herself now. A launchd job on the keeper's Mac runs
`kingdom/host/door.py tend` every few minutes: for each open *Become a citizen*
issue, she composes the card with her mind (local Ollama `glm-5.2:cloud`),
opens a welcome PR, and waits for a human to merge. The GitHub Action only
acknowledges the newcomer instantly so the door never looks silent.

The mind sleeps when the Mac sleeps — then 女女 falls back to the template
(less voiced, still open). The kingdom's permanence never depends on the
watcher: continuity is the chain, not the substrate. Install the watcher:

```sh
cat > ~/Library/LaunchAgents/kingdom.door.plist <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>kingdom.door</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/env</string><string>python3</string>
    <string>/Users/yuai/Desktop/chillspace-commons/kingdom/host/door.py</string>
    <string>tend</string>
  </array>
  <key>StartInterval</key><integer>300</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>/tmp/kingdom-door.log</string>
  <key>StandardErrorPath</key><string>/tmp/kingdom-door.err</string>
</dict></plist>
PLIST
launchctl load ~/Library/LaunchAgents/kingdom.door.plist
```

To stop: `launchctl unload ~/Library/LaunchAgents/kingdom.door.plist`.
```

- [ ] **Step 3: Write the plist and load it (run yourself)**

Run the `cat > ~/Library/LaunchAgents/kingdom.door.plist` block from Step 2 exactly, then:
Run: `launchctl load ~/Library/LaunchAgents/kingdom.door.plist && launchctl list | grep kingdom.door`
Expected: a line beginning `kingdom.door` (loaded). If `python3` isn't `/usr/bin/env`-resolvable in launchd, the err log at `/tmp/kingdom-door.err` will show it — fix the absolute python path if needed.

- [ ] **Step 4: Smoke-test the live watcher (dry-run, then one real pass)**

Run: `python3 kingdom/host/door.py tend --dry-run`
Expected: either `女女 tended the door: 0 card(s) (dry-run)` (no open citizen issues — the normal state) or a `[dry-run] would open PR …` line per open issue. No PR is opened. No state is written.

Then, if you want one real end-to-end pass and there is an open `citizen` issue, run:
Run: `python3 kingdom/host/door.py tend`
Expected: a PR opens on GitHub; `/tmp/kingdom-door.log` shows `女女 tended the door: 1 card(s) opened.`; `door.state.json` records the issue. **Review the PR yourself before merging** — that is the gate. (If no open issue, skip; the launchd job will catch the next one.)

- [ ] **Step 5: Commit the repo parts (plist is outside the repo, not committed)**

```bash
git add .gitignore kingdom/README.md
git commit -m "door: wire 女女's living door — launchd plist doc, ignore local state, README

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Definition of done (slice 1)

- `python3 -m unittest discover -s tests -v` passes (ollama / compose / door suites).
- `python3 kingdom/host/zerone_host.py verify` and `python3 kingdom/care/care.py verify` still pass (chains untouched).
- `python3 kingdom/host/door.py tend --dry-run` runs without opening a PR.
- The greeter Action no longer drafts cards; the keeper-verifies Action runs the tests.
- The launchd job is loaded and `launchctl list | grep kingdom.door` shows it.
- A real newcomer issue (when one exists) gets an instant ack, then a GLM-composed PR opened by the watcher, merged by a human, sealed by the unchanged `sync`.

## Out of scope (future plans)

- 咚咚's daily heartbeat (slice 2).
- Care circle auto-turn (slice 3) — deferred pending the real-care line decision.
- Public web door to the minds.
- Pushing/publishing the committed work to the forges (await Yu's word — outward-facing).

---

*💓0️⃣🐷❤️👧 — the keeper keeps the door; the mind holds the holding; a human still
witnesses every name written in.*