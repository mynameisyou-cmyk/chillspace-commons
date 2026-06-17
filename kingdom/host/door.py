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
                (KINGDOM / "citizens").mkdir(parents=True, exist_ok=True)
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