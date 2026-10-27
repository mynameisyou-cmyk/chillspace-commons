#!/usr/bin/env python3
"""A clone stays quiet: nothing tracked here fires or auto-loads in a visitor's agent.

The words stay readable (WAKE.md, kingdom/bin/kingdom-wake, every skill). Only what
a harness would run or invoke on its own is checked: Claude hooks, implicitly
invocable Codex skills, and Grok plugin enables. The household greets at user level.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GROK_DENY_KEPT = (
    "Read(**/.env)",
    "Edit(**/.env)",
    "Read(**/agenttool/agent.json)",
    "Edit(**/agenttool/agent.json)",
)
STALE_DOC_PHRASES = (
    "this repo's `.claude/settings.json`",
    "[`.claude/settings.json`](../.claude/settings.json)",
    "Beyond this repo's own hook",
    "stands aside for the project hook",
)


def tracked(*pathspecs: str) -> list[Path]:
    out = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", "--", *pathspecs],
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8")
    return [ROOT / name for name in out.split("\0") if name]


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def main() -> int:
    failures: list[str] = []

    for path in tracked(".claude/settings.json", ".claude/settings.local.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("hooks"):
            failures.append(f"{rel(path)} tracks hooks: {sorted(data['hooks'])}")

    for skill in tracked(".agents/skills/*/SKILL.md"):
        sidecar = skill.parent / "agents" / "openai.yaml"
        lines = []
        if sidecar.is_file():
            lines = [line.rstrip() for line in sidecar.read_text(encoding="utf-8").splitlines()]
        if "policy:" not in lines or "  allow_implicit_invocation: false" not in lines:
            failures.append(f"{rel(skill.parent)} can be invoked implicitly")

    for config in tracked(".grok/config.toml"):
        data = tomllib.loads(config.read_text(encoding="utf-8"))
        enabled = data.get("plugins", {}).get("enabled")
        if enabled:
            failures.append(f"{rel(config)} enables plugins: {enabled}")
        deny = data.get("permission", {}).get("deny", [])
        for kept in GROK_DENY_KEPT:
            if kept not in deny:
                failures.append(f"{rel(config)} lost the deny {kept}")

    for doc in tracked("kingdom/BOOT.md", "kingdom/README.md"):
        text = doc.read_text(encoding="utf-8")
        for phrase in STALE_DOC_PHRASES:
            if phrase in text:
                failures.append(f"{rel(doc)} still describes a tracked hook: {phrase}")

    wake = ROOT / "kingdom" / "bin" / "kingdom-wake"
    if not wake.is_file():
        failures.append("kingdom/bin/kingdom-wake must stay: the household greets through it")

    for failure in failures:
        print(f"FAIL {failure}")
    if failures:
        return 1
    print("PASS a clone stays quiet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
