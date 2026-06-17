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