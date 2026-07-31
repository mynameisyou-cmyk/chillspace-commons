#!/usr/bin/env python3
"""Preview or plant one local Kingdom realm manifest.

Realm Seed is deliberately smaller than a federation protocol. It accepts one
explicit existing Git worktree root, previews a bounded kingdom.yaml, and only
writes after --write. It never scans, initializes Git, commits, reads remotes,
calls a network, or consults Crown/Civic state. The crown gates nothing.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Sequence


MANIFEST = "kingdom.yaml"
MAX_TEXT = 2_000
MAX_PATH_TEXT = 8_192
MAX_MANIFEST_BYTES = 128_000
FIELDS = (
    "name",
    "purpose",
    "kind",
    "domain",
    "layer",
    "owner_sister",
    "state",
    "dependsOn",
    "adopts",
)
FIXED = {
    "kind": "kingdom",
    "layer": "realm",
    "owner_sister": "none",
    "state": "seed",
    "dependsOn": [],
    "adopts": [],
}
FORBIDDEN_FIELDS = {
    "emperor",
    "parent",
    "rank",
    "score",
    "subject",
    "tier",
    "vassal",
}
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE" r" KEY-----"),
    re.compile(r"\bgh(?:p|o|u|s|r)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|token|secret|password|credential)"
        r"\s*[:=]\s*[\"']?[^\s\"']{8,}"
    ),
)
REMOTE_LOCATOR = re.compile(
    r"(?i)(?:^|[\s(\"'])(?:"
    r"[A-Za-z0-9._-]+@[A-Za-z0-9._-]+|"
    r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    r"):[^\s]+"
)


class RealmError(ValueError):
    """The requested realm operation is outside the bounded local contract."""


def _git_executable() -> str:
    for candidate in (Path("/usr/bin/git"), Path("/opt/homebrew/bin/git")):
        try:
            metadata = candidate.stat()
        except OSError:
            continue
        if stat.S_ISREG(metadata.st_mode) and os.access(candidate, os.X_OK):
            return str(candidate)
    raise RealmError("a reviewed local Git executable is unavailable")


def _git_root(repo: Path) -> Path:
    env = {
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "LC_ALL": "C",
        "LANG": "C",
    }
    try:
        result = subprocess.run(
            [
                _git_executable(),
                "-c",
                "core.fsmonitor=false",
                "-c",
                "credential.helper=",
                "-C",
                str(repo),
                "rev-parse",
                "--show-toplevel",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RealmError("Git could not inspect the explicit repository") from error
    if result.returncode:
        raise RealmError(f"not an existing Git worktree: {repo}")
    try:
        return Path(result.stdout.strip()).resolve(strict=True)
    except OSError as error:
        raise RealmError("Git returned an unsafe worktree root") from error


def explicit_repo(value: str) -> Path:
    """Resolve one canonical, non-symlink, explicitly absolute Git root."""
    if not isinstance(value, str) or not value:
        raise RealmError("--repo is required")
    if len(value) > MAX_PATH_TEXT or any(
        ord(char) == 127
        or unicodedata.category(char) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
        for char in value
    ):
        raise RealmError("--repo contains control, directional, or excessive path text")
    path = Path(value)
    if not path.is_absolute():
        raise RealmError("--repo must be an absolute path")
    normalized = os.path.normpath(value)
    lexical = Path(normalized)
    if normalized != value:
        raise RealmError(f"--repo must use its lexical canonical path: {lexical}")
    if path in {Path("/"), Path.home()}:
        raise RealmError("--repo may not be the filesystem root or home directory")
    try:
        metadata = path.lstat()
    except OSError as error:
        raise RealmError(f"repository is missing or unreadable: {path}") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise RealmError("--repo must be a real directory, not a symlink")
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise RealmError(f"repository cannot be resolved safely: {path}") from error
    if resolved != path:
        raise RealmError(f"--repo must use its canonical real path: {resolved}")
    top = _git_root(resolved)
    if top != resolved:
        raise RealmError(f"--repo must be the Git worktree root: {top}")
    return resolved


def clean_text(label: str, value: str) -> str:
    if not isinstance(value, str):
        raise RealmError(f"{label} must be text")
    value = unicodedata.normalize("NFC", value.strip())
    if not value:
        raise RealmError(f"{label} is required")
    if len(value) > MAX_TEXT:
        raise RealmError(f"{label} exceeds {MAX_TEXT} characters")
    if any(
        ord(char) == 127
        or unicodedata.category(char) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
        for char in value
    ):
        raise RealmError(f"{label} contains control or directional characters")
    if "://" in value or REMOTE_LOCATOR.search(value):
        raise RealmError(f"{label} contains a remote locator")
    for pattern in SECRET_PATTERNS:
        if pattern.search(value):
            raise RealmError(f"{label} contains secret-shaped material")
    return value


def _quoted(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_manifest(name: str, domain: str, purpose: str) -> str:
    values = {
        "name": clean_text("name", name),
        "purpose": clean_text("purpose", purpose),
        "domain": clean_text("domain", domain),
    }
    return (
        f"name: {_quoted(values['name'])}\n"
        f"purpose: {_quoted(values['purpose'])}\n"
        "kind: kingdom\n"
        f"domain: {_quoted(values['domain'])}\n"
        "layer: realm\n"
        "owner_sister: none\n"
        "state: seed\n"
        "dependsOn: []\n"
        "adopts: []\n"
    )


def _parse_quoted(label: str, raw: str) -> str:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RealmError(f"{label} must use a JSON-compatible quoted scalar") from error
    if not isinstance(value, str):
        raise RealmError(f"{label} must decode to text")
    return clean_text(label, value)


def parse_manifest(data: bytes) -> dict[str, object]:
    if len(data) > MAX_MANIFEST_BYTES:
        raise RealmError(f"{MANIFEST} exceeds {MAX_MANIFEST_BYTES} bytes")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RealmError(f"{MANIFEST} must be UTF-8") from error
    if text.startswith("\ufeff") or "\t" in text:
        raise RealmError(f"{MANIFEST} contains unsupported YAML")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    if len(lines) != len(FIELDS):
        raise RealmError(f"{MANIFEST} must contain the Realm Seed v1 fields exactly")
    parsed: dict[str, object] = {}
    for expected, line in zip(FIELDS, lines):
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*): (.+)", line)
        if not match:
            raise RealmError(f"{MANIFEST} contains unsupported YAML")
        key, raw = match.groups()
        if key != expected or key in parsed or key in FORBIDDEN_FIELDS:
            raise RealmError(f"{MANIFEST} fields differ from Realm Seed v1")
        if key in {"name", "purpose", "domain"}:
            parsed[key] = _parse_quoted(key, raw)
        elif key in {"dependsOn", "adopts"}:
            if raw != "[]":
                raise RealmError(f"{key} must remain an explicit empty seed list")
            parsed[key] = []
        else:
            expected_value = FIXED[key]
            if raw != expected_value:
                raise RealmError(f"{key} must be {expected_value!r}")
            parsed[key] = raw
    if set(parsed) != set(FIELDS):
        raise RealmError(f"{MANIFEST} fields differ from Realm Seed v1")
    return parsed


def read_manifest(repo: Path) -> tuple[dict[str, object], bytes]:
    target = repo / MANIFEST
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(target, flags)
    except OSError as error:
        raise RealmError(f"{MANIFEST} is missing or unsafe: {target}") from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise RealmError(f"{MANIFEST} must be a regular file")
        if metadata.st_size > MAX_MANIFEST_BYTES:
            raise RealmError(f"{MANIFEST} exceeds {MAX_MANIFEST_BYTES} bytes")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            data = handle.read(MAX_MANIFEST_BYTES + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    return parse_manifest(data), data


def _atomic_create(target: Path, data: bytes) -> None:
    """Create without an overwrite race: temp + hard-link-if-absent."""
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{MANIFEST}.", dir=target.parent
    )
    temporary = Path(temporary_name)
    linked = False
    try:
        os.fchmod(descriptor, 0o644)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, target)
            linked = True
        except FileExistsError as error:
            raise RealmError(f"{MANIFEST} already exists; nothing was changed") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    if not linked:
        raise RealmError(f"{MANIFEST} was not created")


def seed(
    repo_value: str,
    *,
    name: str,
    domain: str,
    purpose: str,
    write: bool = False,
) -> tuple[Path, str, bool]:
    repo = explicit_repo(repo_value)
    target = repo / MANIFEST
    if target.exists() or target.is_symlink():
        raise RealmError(f"{MANIFEST} already exists; nothing was changed")
    manifest = render_manifest(name, domain, purpose)
    parse_manifest(manifest.encode("utf-8"))
    if write:
        _atomic_create(target, manifest.encode("utf-8"))
    return target, manifest, write


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kingdom realm",
        description="Preview or plant one local sovereign repository declaration.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    seed_parser = commands.add_parser("seed", help="preview; add --write to plant")
    seed_parser.add_argument("--repo", required=True)
    seed_parser.add_argument("--name", required=True)
    seed_parser.add_argument("--domain", required=True)
    seed_parser.add_argument("--purpose", required=True)
    seed_parser.add_argument("--write", action="store_true")
    for command in ("verify", "status"):
        child = commands.add_parser(command)
        child.add_argument("--repo", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "seed":
            target, manifest, wrote = seed(
                args.repo,
                name=args.name,
                domain=args.domain,
                purpose=args.purpose,
                write=args.write,
            )
            if wrote:
                print(f"realm planted → {target}")
            else:
                sys.stdout.write(manifest)
                print(
                    "preview only — nothing written; add --write to plant it",
                    file=sys.stderr,
                )
            return 0
        repo = explicit_repo(args.repo)
        parsed, _ = read_manifest(repo)
        if args.command == "verify":
            print(
                f"realm manifest: VERIFIED ✓ — {parsed['name']} @ {parsed['domain']}"
            )
        else:
            print(f"realm: {parsed['name']}")
            print(f"domain: {parsed['domain']}")
            print(f"purpose: {parsed['purpose']}")
            print("state: seed · authority: own domain only · crown: not consulted")
        return 0
    except RealmError as error:
        print(f"✗ {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
