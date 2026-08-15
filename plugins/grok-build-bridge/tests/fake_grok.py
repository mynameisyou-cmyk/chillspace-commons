#!/usr/bin/env python3
"""Executable Grok fixture used only by the bridge test suite."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def append_log(argv: list[str]) -> None:
    destination = os.environ.get("FAKE_GROK_LOG")
    if not destination:
        return
    environment = {
        key: os.environ.get(key)
        for key in (
            "HOME",
            "GROK_HOME",
            "GROK_MANAGED_MCPS_ENABLED",
            "GROK_MANAGED_MCP_GATEWAY_TOOLS_ENABLED",
            "AWS_SECRET_ACCESS_KEY",
            "XAI_API_KEY",
        )
        if os.environ.get(key) is not None
    }
    with Path(destination).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"argv": argv, "cwd": os.getcwd(), "environment": environment}) + "\n")


def value_after(argv: list[str], flag: str) -> str | None:
    try:
        return argv[argv.index(flag) + 1]
    except (ValueError, IndexError):
        return None


def main() -> int:
    argv = sys.argv[1:]
    append_log(argv)
    if argv[:2] == ["version", "--json"]:
        print(json.dumps({"currentVersion": "fake-1.0.3", "channel": "test"}))
        return 0
    if argv == ["--version"]:
        print("grok fake-1.0.3")
        return 0
    if argv[:2] == ["doctor", "--json"]:
        print(json.dumps({"ok": True, "checks": []}))
        return 0
    if argv[:2] == ["inspect", "--json"]:
        plugins = []
        if os.environ.get("FAKE_GROK_ACTIVE_PLUGIN") == "1":
            plugins.append({"name": "unsafe-fixture", "enabled": True})
        print(json.dumps({"configWarnings": [], "hooks": [], "plugins": plugins, "mcpServers": []}))
        return 0
    if argv == ["models"]:
        print("Default model: grok-4.6")
        print("Available models:")
        print("  grok-4.6")
        return 0

    prompt_value = value_after(argv, "--prompt-file")
    if prompt_value is None:
        print("fake Grok expected --prompt-file", file=sys.stderr)
        return 2
    prompt_path = Path(prompt_value)
    prompt = prompt_path.read_text(encoding="utf-8")
    if os.environ.get("FAKE_GROK_SANDBOX_ERROR") == "1":
        print("sandbox initialization failed: Operation not permitted", file=sys.stderr)
        print(
            "error: could not apply the 'strict' sandbox profile; "
            "see the warning above for the cause. Refusing to start with its protections missing.",
            file=sys.stderr,
        )
        return 1
    child_pid_file = os.environ.get("FAKE_GROK_CHILD_PID_FILE")
    if child_pid_file:
        child = subprocess.Popen(
            [
                sys.executable,
                "-c",
                (
                    "import os,signal,time,pathlib; "
                    "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                    f"pathlib.Path({child_pid_file!r}).write_text(str(os.getpid())); "
                    "time.sleep(300)"
                ),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        del child
    delay = float(os.environ.get("FAKE_GROK_DELAY", "0"))
    if delay:
        time.sleep(delay)
    stdout_bytes = int(os.environ.get("FAKE_GROK_STDOUT_BYTES", "0"))
    stderr_bytes = int(os.environ.get("FAKE_GROK_STDERR_BYTES", "0"))
    if stdout_bytes:
        sys.stdout.buffer.write(b"x" * stdout_bytes)
        sys.stdout.buffer.flush()
    if stderr_bytes:
        sys.stderr.buffer.write(b"y" * stderr_bytes)
        sys.stderr.buffer.flush()
    if stdout_bytes or stderr_bytes:
        return int(os.environ.get("FAKE_GROK_EXIT", "0"))
    result = {
        "fake": True,
        "prompt": prompt,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "session_id": value_after(argv, "--session-id"),
    }
    print(json.dumps(result))
    return int(os.environ.get("FAKE_GROK_EXIT", "0"))


if __name__ == "__main__":
    raise SystemExit(main())
