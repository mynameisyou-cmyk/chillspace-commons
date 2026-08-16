#!/usr/bin/env python3
"""Read-only map of Grok Build modules and their Kingdom bindings."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
MAP_PATH = HERE / "modules.json"
SCHEMA = "kingdom.grok-build/v1"
REQUIRED_MODULE_KEYS = {
    "id",
    "label",
    "entry",
    "mode",
    "network",
    "writes",
    "kingdom",
    "intent",
}
KINGDOM_VALUES = {"none", "bound", "observe", "off", "optional", "substrate-release"}
EXPECTED_SKILLS = {
    "yau",
    "kingdom-boot",
    "agenttool-wake",
    "grok-build",
    "karma-play",
}


class ModuleError(ValueError):
    """The module map is structurally invalid."""


def load_map(path: Path = MAP_PATH) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise ModuleError("schema must be kingdom.grok-build/v1")
    modules = data.get("modules")
    if not isinstance(modules, list) or not modules:
        raise ModuleError("modules must be a non-empty array")
    ids: set[str] = set()
    for item in modules:
        missing = REQUIRED_MODULE_KEYS - set(item)
        if missing:
            raise ModuleError(f"module missing keys: {sorted(missing)}")
        if item["id"] in ids:
            raise ModuleError(f"duplicate module id: {item['id']}")
        if item["kingdom"] not in KINGDOM_VALUES:
            raise ModuleError(f"unknown kingdom binding: {item['kingdom']}")
        ids.add(item["id"])
    return data


def render_map(data: dict[str, Any]) -> str:
    lines = [
        f"# {data['name']} — Kingdom module map",
        "",
        f"`{data['schema']}` · chair `{data['version']}`",
        "",
        data["intent"],
        "",
        "| id | label | kingdom | network | intent |",
        "|---|---|---|---|---|",
    ]
    for item in data["modules"]:
        net = item["network"] if isinstance(item["network"], str) else (
            "yes" if item["network"] else "no"
        )
        lines.append(
            f"| `{item['id']}` | {item['label']} | `{item['kingdom']}` | {net} "
            f"| {item['intent']} |"
        )
    lines += ["", "## Non-claims", ""]
    lines += [f"- {claim}" for claim in data["non_claims"]]
    lines.append("")
    return "\n".join(lines)


def inspect_json() -> dict[str, Any] | None:
    grok = shutil.which("grok") or str(Path.home() / ".grok" / "bin" / "grok")
    if not Path(grok).exists():
        return None
    try:
        completed = subprocess.run(
            [grok, "inspect", "--json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
            env={k: v for k, v in os.environ.items() if not k.upper().endswith("_KEY")},
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None


def overlay(data: dict[str, Any], inspect: dict[str, Any] | None) -> dict[str, Any]:
    live = {
        "inspect": inspect is not None,
        "grok_version": None,
        "plugin_kingdom": False,
        "skills": [],
        "rule": False,
        "hooks_file": False,
        "mcp": [],
        "memory_note": "experimental; not read from inspect",
    }
    if inspect is None:
        return live
    live["grok_version"] = inspect.get("grokVersion")
    for plugin in inspect.get("plugins") or []:
        if plugin.get("name") == "kingdom" and plugin.get("enabled"):
            live["plugin_kingdom"] = True
    live["skills"] = sorted(
        skill.get("name")
        for skill in inspect.get("skills") or []
        if (skill.get("source") or {}).get("plugin_name") == "kingdom"
    )
    live["rule"] = any(
        str(item.get("path", "")).endswith("rules/kingdom.md")
        for item in inspect.get("projectInstructions") or []
    )
    live["hooks_file"] = any(
        "kingdom/hooks/hooks.json" in str(hook.get("target", ""))
        or (hook.get("source") or {}).get("plugin_name") == "kingdom"
        for hook in inspect.get("hooks") or []
    )
    live["mcp"] = [
        server.get("name")
        for server in inspect.get("mcpServers") or []
        if server.get("name")
    ]
    return live


def doctor(data: dict[str, Any], inspect: dict[str, Any] | None) -> list[str]:
    live = overlay(data, inspect)
    failures: list[str] = []
    if inspect is None:
        failures.append("grok inspect unavailable")
        return failures
    if live["grok_version"] != data["version"]:
        failures.append(
            f"map pins {data['version']}; inspect reports {live['grok_version']}"
        )
    if not live["plugin_kingdom"]:
        failures.append("kingdom plugin not enabled in inspect")
    missing = sorted(EXPECTED_SKILLS - set(live["skills"]))
    if missing:
        failures.append(f"missing kingdom skills: {missing}")
    if not live["rule"]:
        failures.append("kingdom arrival rule not loaded")
    if not live["hooks_file"]:
        failures.append("kingdom SessionStart hook file not loaded")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Grok Build module map for the Kingdom")
    parser.add_argument(
        "command",
        nargs="?",
        default="map",
        choices=("map", "inspect", "doctor"),
    )
    args = parser.parse_args(argv)
    try:
        data = load_map()
    except (OSError, json.JSONDecodeError, ModuleError) as error:
        print(f"modules: {error}", file=sys.stderr)
        return 2
    if args.command == "map":
        sys.stdout.write(render_map(data))
        return 0
    inspect = inspect_json()
    live = overlay(data, inspect)
    if args.command == "inspect":
        print(json.dumps(live, indent=2))
        return 0
    failures = doctor(data, inspect)
    print(json.dumps({"ok": not failures, "failures": failures, "live": live}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
