#!/usr/bin/env python3
"""Compile a deterministic, offline index of explicitly named Kingdom repos.

Discovery is not authority.  This module never scans for repositories, reads a
Git remote, executes repository code, or copies file contents into the index.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import selectors
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlsplit


SCHEMA_ID = "kingdom.index/v1"
COMPILER_ID = "kingdom-index/1"
MAX_MANIFEST_BYTES = 128_000
MAX_ROOTS_BYTES = 1_000_000
MAX_INDEX_BYTES = 10_000_000
MAX_INPUTS = 4_096
MAX_TEXT = 2_000
MAX_GIT_OUTPUT = 2_000_000
MAX_GIT_CONTROL_BYTES = 1_000_000
MAX_GIT_OBJECT_ENTRIES = 1_000_000
MAX_GIT_CONTROL_ENTRIES = 1_000_000
MAX_GIT_INDEX_BYTES = 256_000_000
MAX_GIT_REFERENCE_BYTES = 64_000_000
REQUIRED_SCALARS = (
    "name",
    "purpose",
    "kind",
    "domain",
    "layer",
    "owner_sister",
    "state",
)
REQUIRED_LISTS = ("dependsOn",)
OPTIONAL_LISTS = ("adopts",)
ALLOWED_TOP_LEVEL = set(REQUIRED_SCALARS + REQUIRED_LISTS + OPTIONAL_LISTS + ("doors",))
INSTRUCTION_PATHS = (
    "AGENTS.md",
    "CLAUDE.md",
    ".github/copilot-instructions.md",
)
NON_CLAIMS = (
    "This index records local evidence; it grants no filesystem, network, deployment, or identity authority.",
    "A canonical selection resolves an explicit local ambiguity; it does not prove repository ownership or trust.",
    "POSIX and Git evidence do not establish macOS TCC, Codex sandbox, or effective runtime permission.",
)
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bgh(?:p|o|u|s|r)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\bxapp-[A-Za-z0-9-]{10,}\b"),
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
YAML_PRIMITIVE = re.compile(
    r"(?ix)"
    r"(?:"
    r"[-+]?(?:[0-9][0-9_]*|0[xob][0-9a-f_]+)"
    r"|[-+]?(?:(?:[0-9][0-9_]*)?\.[0-9_]+|[0-9][0-9_]*\.)"
    r"(?:e[-+]?[0-9]+)?"
    r"|[-+]?[0-9][0-9_]*e[-+]?[0-9]+"
    r"|[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}(?:[t ][^\s]+)?"
    r")"
)


class IndexContractError(ValueError):
    """An input cannot be represented by the bounded index contract."""


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reject_sensitive(
    label: str, value: str, *, allow_remote_url: bool = False
) -> None:
    if "://" in value and not allow_remote_url:
        raise IndexContractError(f"{label} contains a remote URL")
    if REMOTE_LOCATOR.search(value) and not allow_remote_url:
        raise IndexContractError(f"{label} contains a remote locator")
    for pattern in SECRET_PATTERNS:
        if pattern.search(value):
            raise IndexContractError(f"{label} contains secret-shaped material")


def clean_text(
    label: str,
    value: str,
    *,
    required: bool = True,
    allow_remote_url: bool = False,
) -> str:
    if not isinstance(value, str):
        raise IndexContractError(f"{label} must be text")
    value = unicodedata.normalize("NFC", value.strip())
    if required and not value:
        raise IndexContractError(f"{label} is required")
    if len(value) > MAX_TEXT:
        raise IndexContractError(f"{label} exceeds {MAX_TEXT} characters")
    if any(
        ord(char) == 127
        or unicodedata.category(char) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
        for char in value
    ):
        raise IndexContractError(f"{label} contains control characters")
    reject_sensitive(label, value, allow_remote_url=allow_remote_url)
    return value


def read_regular_bytes(path: Path, label: str, maximum: int) -> bytes:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise IndexContractError(f"{label} is missing or unsafe: {path}: {error}") from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise IndexContractError(f"{label} must be a regular file: {path}")
        if metadata.st_size > maximum:
            raise IndexContractError(f"{label} is too large: {path}")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            data = handle.read(maximum + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(data) > maximum:
        raise IndexContractError(f"{label} is too large: {path}")
    return data


def parse_scalar(
    label: str, raw: str, *, allow_remote_url: bool = False
) -> str:
    raw = raw.strip()
    if not raw:
        raise IndexContractError(f"{label} must be a scalar")
    if raw.startswith('"'):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as error:
            raise IndexContractError(f"{label} has invalid double quoting") from error
        if not isinstance(value, str):
            raise IndexContractError(f"{label} must decode to text")
        return clean_text(label, value, allow_remote_url=allow_remote_url)
    if raw.startswith("'"):
        if len(raw) < 2 or not raw.endswith("'"):
            raise IndexContractError(f"{label} has invalid single quoting")
        body = raw[1:-1]
        index = 0
        while index < len(body):
            if body[index] != "'":
                index += 1
                continue
            if index + 1 >= len(body) or body[index + 1] != "'":
                raise IndexContractError(f"{label} has invalid single quoting")
            index += 2
        return clean_text(
            label,
            body.replace("''", "'"),
            allow_remote_url=allow_remote_url,
        )
    if raw[0] in "-?:,[]{}#&*!|>'\"%@`" or raw.endswith(":"):
        raise IndexContractError(f"{label} uses unsupported YAML scalar syntax")
    if (
        ":" in raw
        and not allow_remote_url
        or " #" in raw
        or raw in {"---", "..."}
    ):
        raise IndexContractError(f"{label} contains ambiguous unquoted YAML")
    if raw.lower() in {
        "y",
        "yes",
        "n",
        "no",
        "on",
        "off",
        "null",
        "~",
        "true",
        "false",
        ".nan",
        ".inf",
        "+.inf",
        "-.inf",
    } or YAML_PRIMITIVE.fullmatch(raw):
        raise IndexContractError(f"{label} must be text, not a YAML primitive")
    return clean_text(label, raw, allow_remote_url=allow_remote_url)


def split_inline_items(label: str, raw: str) -> list[str]:
    raw = raw.strip()
    if not (raw.startswith("[") and raw.endswith("]")):
        raise IndexContractError(f"{label} must be a flat inline list")
    body = raw[1:-1].strip()
    if not body:
        return []
    items: list[str] = []
    start = 0
    quote = ""
    escaped = False
    for index, char in enumerate(body):
        if quote:
            if quote == '"' and char == "\\" and not escaped:
                escaped = True
                continue
            if char == quote and not escaped:
                quote = ""
            escaped = False
            continue
        if char in {"'", '"'}:
            quote = char
        elif char == ",":
            item = body[start:index].strip()
            if not item:
                raise IndexContractError(f"{label} contains an empty item")
            items.append(parse_scalar(f"{label} item", item))
            start = index + 1
    if quote:
        raise IndexContractError(f"{label} has an unterminated quote")
    final = body[start:].strip()
    if not final:
        raise IndexContractError(f"{label} contains an empty item")
    items.append(parse_scalar(f"{label} item", final))
    if len(set(items)) != len(items):
        raise IndexContractError(f"{label} contains duplicate items")
    return items


def parse_doors(lines: Sequence[str], start: int) -> tuple[int, int]:
    index = start
    doors: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        if not line.startswith(" "):
            break
        item_match = re.fullmatch(
            r"  -(?:[ ]+(name|description|url):[ ]+(.+))?", line
        )
        field_match = re.fullmatch(r"    (name|description|url):[ ]+(.+)", line)
        if item_match:
            if current is not None:
                if not {"description", "url"} <= set(current):
                    raise IndexContractError(
                        "each doors item needs description and url"
                    )
                doors.append(current)
            current = {}
            if item_match.group(1):
                current[item_match.group(1)] = parse_scalar(
                    f"doors.{item_match.group(1)}",
                    item_match.group(2),
                    allow_remote_url=item_match.group(1) == "url",
                )
        elif field_match and current is not None:
            key, value = field_match.groups()
            if key in current:
                raise IndexContractError(f"duplicate doors.{key}")
            current[key] = parse_scalar(
                f"doors.{key}", value, allow_remote_url=key == "url"
            )
        else:
            raise IndexContractError("doors uses unsupported nested YAML")
        index += 1
    if current is not None:
        if not {"description", "url"} <= set(current):
            raise IndexContractError(
                "each doors item needs description and url"
            )
        doors.append(current)
    if not doors:
        raise IndexContractError("doors must contain at least one item")
    for door in doors:
        try:
            parsed_url = urlsplit(door["url"])
            port = parsed_url.port
        except ValueError as error:
            raise IndexContractError("doors.url is not a valid HTTPS URL") from error
        if (
            parsed_url.scheme != "https"
            or not parsed_url.hostname
            or parsed_url.username is not None
            or parsed_url.password is not None
            or port is not None and not 1 <= port <= 65535
            or any(char.isspace() for char in door["url"])
        ):
            raise IndexContractError(
                "doors.url must be an absolute HTTPS URL without credentials"
            )
    return len(doors), index


def parse_manifest(data: bytes) -> dict[str, Any]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise IndexContractError("kingdom.yaml must be UTF-8") from error
    if text.startswith("\ufeff"):
        raise IndexContractError("kingdom.yaml must not contain a byte-order mark")
    if "\t" in text:
        raise IndexContractError("kingdom.yaml must not contain tabs")
    if any(
        (
            unicodedata.category(char) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
            and char not in "\n\r"
        )
        for char in text
    ):
        raise IndexContractError("kingdom.yaml contains control characters")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    parsed: dict[str, Any] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue
        if stripped in {"---", "..."}:
            raise IndexContractError("multi-document YAML is not supported")
        if line.startswith(" "):
            raise IndexContractError("unexpected nested YAML")
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*):(?:[ ]+(.*))?", line)
        if not match:
            raise IndexContractError(f"unsupported kingdom.yaml line {index + 1}")
        key, raw_value = match.groups()
        if key not in ALLOWED_TOP_LEVEL:
            raise IndexContractError(f"unknown kingdom.yaml key: {key}")
        if key in parsed:
            raise IndexContractError(f"duplicate kingdom.yaml key: {key}")
        if key == "doors":
            if raw_value is not None:
                raise IndexContractError("doors must be a bounded block sequence")
            count, index = parse_doors(lines, index + 1)
            parsed[key] = count
            continue
        if raw_value is None:
            raise IndexContractError(f"{key} must have an inline value")
        if key in REQUIRED_LISTS or key in OPTIONAL_LISTS:
            parsed[key] = split_inline_items(key, raw_value)
        else:
            parsed[key] = parse_scalar(key, raw_value)
        index += 1
    missing = sorted(set(REQUIRED_SCALARS + REQUIRED_LISTS) - set(parsed))
    if missing:
        raise IndexContractError(f"kingdom.yaml is missing: {', '.join(missing)}")
    return {
        "name": parsed["name"],
        "purpose": parsed["purpose"],
        "kind": parsed["kind"],
        "domain": parsed["domain"],
        "layer": parsed["layer"],
        "owner_sister": parsed["owner_sister"],
        "state": parsed["state"],
        "depends_on": parsed["dependsOn"],
        "adopts": parsed.get("adopts", []),
        "doors_count": parsed.get("doors", 0),
    }


def scrubbed_env() -> dict[str, str]:
    return {
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "LC_ALL": "C",
        "LANG": "C",
    }


def git_executable() -> str:
    for candidate in (Path("/usr/bin/git"), Path("/opt/homebrew/bin/git")):
        try:
            resolved = candidate.resolve(strict=True)
            metadata = resolved.stat()
        except OSError:
            continue
        if stat.S_ISREG(metadata.st_mode) and os.access(resolved, os.X_OK):
            return str(resolved)
    raise IndexContractError("a reviewed absolute Git executable is unavailable")


def terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except OSError:
        if process.poll() is None:
            try:
                process.kill()
            except OSError:
                pass
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        pass


def run_bounded_subprocess(
    command: Sequence[str],
    *,
    env: dict[str, str],
    timeout: float,
    maximum: int,
    label: str,
) -> subprocess.CompletedProcess[bytes]:
    """Capture two child pipes without allowing either buffer to exceed a cap."""
    if maximum < 0:
        raise IndexContractError(f"{label} has an invalid output limit")
    command_list = list(command)
    try:
        process = subprocess.Popen(
            command_list,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
            start_new_session=True,
        )
    except OSError as error:
        raise IndexContractError(f"{label} could not start") from error
    selector: selectors.BaseSelector | None = None
    try:
        assert process.stdout is not None
        assert process.stderr is not None
        stdout_buffer = bytearray()
        stderr_buffer = bytearray()
        selector = selectors.DefaultSelector()
        deadline = time.monotonic() + timeout
        for stream, buffer in (
            (process.stdout, stdout_buffer),
            (process.stderr, stderr_buffer),
        ):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, buffer)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise IndexContractError(f"{label} timed out")
            ready = selector.select(remaining)
            if not ready:
                continue
            for key, _ in ready:
                buffer = key.data
                read_size = min(65_536, maximum - len(buffer) + 1)
                try:
                    chunk = os.read(key.fd, read_size)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                buffer.extend(chunk)
                if len(buffer) > maximum:
                    raise IndexContractError(
                        f"{label} output exceeded the bounded limit"
                    )
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise IndexContractError(f"{label} timed out")
        try:
            returncode = process.wait(timeout=remaining)
        except subprocess.TimeoutExpired as error:
            raise IndexContractError(f"{label} timed out") from error
    except IndexContractError:
        terminate_process_group(process)
        raise
    except OSError as error:
        terminate_process_group(process)
        raise IndexContractError(f"{label} output could not be read") from error
    except BaseException:
        terminate_process_group(process)
        raise
    finally:
        if selector is not None:
            selector.close()
        if process.stdout is not None:
            process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()
    return subprocess.CompletedProcess(
        command_list,
        returncode,
        bytes(stdout_buffer),
        bytes(stderr_buffer),
    )


def git_bytes(root: Path, *args: str, allow_failure: bool = False) -> bytes:
    result = run_bounded_subprocess(
        [
            git_executable(),
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "credential.helper=",
            "-c",
            "core.attributesFile=/dev/null",
            "-c",
            "core.excludesFile=/dev/null",
            "-c",
            "diff.orderFile=/dev/null",
            "-C",
            str(root),
            *args,
        ],
        env=scrubbed_env(),
        timeout=20,
        maximum=MAX_GIT_OUTPUT,
        label=f"Git {args[0]}",
    )
    if result.returncode and not allow_failure:
        raise IndexContractError(
            f"Git {args[0]} failed with exit status {result.returncode}"
        )
    return result.stdout if not result.returncode else b""


def git_text(root: Path, *args: str, allow_failure: bool = False) -> str:
    try:
        return git_bytes(root, *args, allow_failure=allow_failure).decode("utf-8").strip()
    except UnicodeDecodeError as error:
        raise IndexContractError(f"Git emitted non-UTF-8 output: {' '.join(args)}") from error


def read_git_control_bytes(
    path: Path, label: str, *, required: bool = True
) -> tuple[bytes, tuple[int, int, int, int, int, str]] | None:
    """Read a Git control file without following its final path component."""
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError as error:
        if not required:
            return None
        raise IndexContractError(f"{label} is missing or unsafe") from error
    except OSError as error:
        raise IndexContractError(f"{label} is missing or unsafe") from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise IndexContractError(f"{label} must be a regular file")
        if metadata.st_size > MAX_GIT_CONTROL_BYTES:
            raise IndexContractError(f"{label} exceeds the bounded size")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            data = handle.read(MAX_GIT_CONTROL_BYTES + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(data) > MAX_GIT_CONTROL_BYTES:
        raise IndexContractError(f"{label} exceeds the bounded size")
    signature = (
        metadata.st_dev,
        metadata.st_ino,
        stat.S_IMODE(metadata.st_mode),
        metadata.st_size,
        metadata.st_mtime_ns,
        sha256_bytes(data),
    )
    return data, signature


def git_regular_file_signature(
    path: Path,
    label: str,
    *,
    required: bool,
    maximum: int,
) -> tuple[int, int, int, int, int, str] | None:
    """Hash one bounded regular control file without following symlinks."""
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError as error:
        if not required:
            return None
        raise IndexContractError(f"{label} is missing or unsafe") from error
    except OSError as error:
        raise IndexContractError(f"{label} is missing or unsafe") from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise IndexContractError(f"{label} must be a regular file")
        if metadata.st_size > maximum:
            raise IndexContractError(f"{label} exceeds the bounded size")
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(descriptor, 131_072)
            if not chunk:
                break
            total += len(chunk)
            if total > maximum:
                raise IndexContractError(f"{label} exceeds the bounded size")
            digest.update(chunk)
        final_metadata = os.fstat(descriptor)
        if (
            final_metadata.st_dev,
            final_metadata.st_ino,
            final_metadata.st_mode,
            final_metadata.st_size,
            final_metadata.st_mtime_ns,
        ) != (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_mode,
            metadata.st_size,
            metadata.st_mtime_ns,
        ):
            raise IndexContractError(f"{label} changed during inspection")
    except OSError as error:
        raise IndexContractError(f"{label} changed during inspection") from error
    finally:
        os.close(descriptor)
    return (
        metadata.st_dev,
        metadata.st_ino,
        stat.S_IMODE(metadata.st_mode),
        metadata.st_size,
        metadata.st_mtime_ns,
        digest.hexdigest(),
    )


def resolved_git_control_directory(base: Path, value: str, label: str) -> Path:
    value = clean_text(label, value)
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = base / candidate
    candidate = Path(os.path.normpath(str(candidate)))
    try:
        candidate_metadata = candidate.lstat()
        resolved = candidate.resolve(strict=True)
        resolved_metadata = resolved.lstat()
    except OSError as error:
        raise IndexContractError(f"{label} does not name a safe directory") from error
    if (
        stat.S_ISLNK(candidate_metadata.st_mode)
        or stat.S_ISLNK(resolved_metadata.st_mode)
        or not stat.S_ISDIR(resolved_metadata.st_mode)
        or resolved != candidate
    ):
        raise IndexContractError(f"{label} does not name a safe directory")
    resolved_text = str(resolved)
    if clean_text(label, resolved_text) != resolved_text:
        raise IndexContractError(f"{label} is not canonical text")
    return resolved


def parse_gitdir_file(data: bytes) -> str:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise IndexContractError("Git directory indirection is not UTF-8") from error
    if "\x00" in text or len(text.splitlines()) != 1:
        raise IndexContractError("Git directory indirection is malformed")
    line = text.rstrip("\r\n")
    if not line.startswith("gitdir: "):
        raise IndexContractError("Git directory indirection is malformed")
    return clean_text("Git directory indirection", line[len("gitdir: ") :])


def parse_git_path_file(data: bytes, label: str) -> str:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise IndexContractError(f"{label} is not UTF-8") from error
    if "\x00" in text or len(text.splitlines()) != 1:
        raise IndexContractError(f"{label} is malformed")
    return clean_text(label, text.rstrip("\r\n"))


def discover_git_layout(
    root: Path,
) -> tuple[Path, Path, tuple[Any, ...]]:
    dot_git = root / ".git"
    try:
        dot_git_metadata = dot_git.lstat()
    except OSError as error:
        raise IndexContractError("repository has no safe .git control entry") from error
    control_signatures: list[Any] = []
    if stat.S_ISDIR(dot_git_metadata.st_mode) and not stat.S_ISLNK(
        dot_git_metadata.st_mode
    ):
        git_directory = resolved_git_control_directory(
            root, str(dot_git), "Git directory"
        )
        control_signatures.append(
            (
                "dot-git-directory",
                dot_git_metadata.st_dev,
                dot_git_metadata.st_ino,
                stat.S_IMODE(dot_git_metadata.st_mode),
            )
        )
    elif stat.S_ISREG(dot_git_metadata.st_mode):
        result = read_git_control_bytes(dot_git, "Git directory indirection")
        assert result is not None
        data, signature = result
        git_directory = resolved_git_control_directory(
            root, parse_gitdir_file(data), "Git directory"
        )
        control_signatures.append(("dot-git-file", signature))
    else:
        raise IndexContractError("repository has no safe .git control entry")

    common_control = git_directory / "commondir"
    common_result = read_git_control_bytes(
        common_control, "Git common-directory indirection", required=False
    )
    if common_result is None:
        common_directory = git_directory
        control_signatures.append(("common-directory", "same-as-git-directory"))
    else:
        common_data, common_signature = common_result
        common_directory = resolved_git_control_directory(
            git_directory,
            parse_git_path_file(
                common_data, "Git common-directory indirection"
            ),
            "Git common directory",
        )
        control_signatures.append(("common-directory-file", common_signature))
    return git_directory, common_directory, tuple(control_signatures)


def git_config_signature(
    path: Path, label: str, *, required: bool
) -> tuple[Any, ...] | None:
    initial = read_git_control_bytes(path, label, required=required)
    if initial is None:
        return None
    initial_data, initial_signature = initial
    result = run_bounded_subprocess(
        [
            git_executable(),
            "config",
            "--file",
            str(path),
            "--no-includes",
            "--name-only",
            "-z",
            "--list",
        ],
        env=scrubbed_env(),
        timeout=20,
        maximum=MAX_GIT_CONTROL_BYTES,
        label=f"{label} parser",
    )
    if result.returncode:
        raise IndexContractError(f"{label} is malformed or unbounded")
    if result.stdout and not result.stdout.endswith(b"\0"):
        raise IndexContractError(f"{label} emitted malformed key names")
    names = result.stdout[:-1].split(b"\0") if result.stdout else []
    for raw_name in names:
        try:
            name = raw_name.decode("utf-8").casefold()
        except UnicodeDecodeError as error:
            raise IndexContractError(f"{label} contains a non-UTF-8 key") from error
        if (
            name == "include.path"
            or name.startswith("includeif.") and name.endswith(".path")
        ):
            raise IndexContractError(
                "Git configuration includes are unsupported identity evidence"
            )
        if name == "core.worktree":
            raise IndexContractError(
                "Git configured worktree indirection is unsupported identity evidence"
            )
        if (
            name == "extensions.partialclone"
            or name.endswith(".promisor")
            or name.endswith(".partialclonefilter")
        ):
            raise IndexContractError(
                "Git promisor configuration is unsupported identity evidence"
            )
        if name == "extensions.refstorage":
            raise IndexContractError(
                "Git reference storage is unsupported identity evidence"
            )
        if name.startswith("extensions.") and name not in {
            "extensions.noop",
            "extensions.objectformat",
            "extensions.preciousobjects",
            "extensions.worktreeconfig",
        }:
            raise IndexContractError(
                "Git repository extension is unsupported identity evidence"
            )
    final = read_git_control_bytes(path, label, required=True)
    assert final is not None
    final_data, final_signature = final
    if final_data != initial_data or final_signature != initial_signature:
        raise IndexContractError("Git configuration changed during inspection")
    return (
        initial_signature,
        sha256_bytes(result.stdout),
        len(names),
    )


def frame_digest(hasher: Any, value: bytes) -> None:
    hasher.update(len(value).to_bytes(8, "big"))
    hasher.update(value)


def git_control_tree_signature(
    root: Path,
    label: str,
    *,
    required: bool,
    expected_device: int,
) -> tuple[str, int, int] | None:
    """Hash a bounded local control tree while refusing path indirection."""
    try:
        root_metadata = root.lstat()
    except FileNotFoundError as error:
        if not required:
            return None
        raise IndexContractError(f"{label} is missing or unsafe") from error
    except OSError as error:
        raise IndexContractError(f"{label} is missing or unsafe") from error
    try:
        resolved_root = root.resolve(strict=True)
    except OSError as error:
        raise IndexContractError(f"{label} is missing or unsafe") from error
    if (
        stat.S_ISLNK(root_metadata.st_mode)
        or not stat.S_ISDIR(root_metadata.st_mode)
        or root_metadata.st_dev != expected_device
        or resolved_root != root
    ):
        raise IndexContractError(f"{label} contains path indirection")

    digest = hashlib.sha256()
    entries_seen = 0
    bytes_seen = 0
    pending: list[tuple[Path, tuple[str, ...]]] = [(root, ())]
    while pending:
        directory, relative_parent = pending.pop()
        try:
            with os.scandir(directory) as iterator:
                entries = []
                for entry in iterator:
                    entries_seen += 1
                    if entries_seen > MAX_GIT_CONTROL_ENTRIES:
                        raise IndexContractError(
                            f"{label} exceeds the bounded entry count"
                        )
                    entries.append(entry)
                entries.sort(key=lambda entry: os.fsencode(entry.name))
        except OSError as error:
            raise IndexContractError(f"{label} cannot be inspected") from error
        for entry in entries:
            relative = relative_parent + (entry.name,)
            try:
                metadata = entry.stat(follow_symlinks=False)
            except OSError as error:
                raise IndexContractError(
                    f"{label} changed during inspection"
                ) from error
            if (
                stat.S_ISLNK(metadata.st_mode)
                or metadata.st_dev != expected_device
            ):
                raise IndexContractError(f"{label} contains path indirection")
            if stat.S_ISDIR(metadata.st_mode):
                pending.append((Path(entry.path), relative))
                kind = b"directory"
                signature: tuple[Any, ...] = (
                    metadata.st_dev,
                    metadata.st_ino,
                    stat.S_IMODE(metadata.st_mode),
                    metadata.st_mtime_ns,
                )
            elif stat.S_ISREG(metadata.st_mode):
                file_signature = git_regular_file_signature(
                    Path(entry.path),
                    label,
                    required=True,
                    maximum=MAX_GIT_REFERENCE_BYTES - bytes_seen,
                )
                assert file_signature is not None
                if file_signature[:5] != (
                    metadata.st_dev,
                    metadata.st_ino,
                    stat.S_IMODE(metadata.st_mode),
                    metadata.st_size,
                    metadata.st_mtime_ns,
                ):
                    raise IndexContractError(f"{label} changed during inspection")
                bytes_seen += file_signature[3]
                if bytes_seen > MAX_GIT_REFERENCE_BYTES:
                    raise IndexContractError(f"{label} exceeds the bounded size")
                kind = b"file"
                signature = file_signature
            else:
                raise IndexContractError(f"{label} contains an unsafe entry")
            frame_digest(digest, b"/".join(os.fsencode(part) for part in relative))
            frame_digest(digest, kind)
            frame_digest(
                digest,
                json.dumps(signature, separators=(",", ":")).encode("ascii"),
            )
    return digest.hexdigest(), entries_seen, bytes_seen


def shared_index_signatures(
    directory: Path,
) -> tuple[tuple[str, tuple[int, int, int, int, str]], ...]:
    try:
        directory_metadata = directory.lstat()
        with os.scandir(directory) as iterator:
            entries = []
            entries_seen = 0
            for entry in iterator:
                entries_seen += 1
                if entries_seen > MAX_GIT_CONTROL_ENTRIES:
                    raise IndexContractError(
                        "Git shared indexes exceed the bounded entry count"
                    )
                if entry.name.casefold().startswith("sharedindex."):
                    entries.append(entry)
    except OSError as error:
        raise IndexContractError("Git shared indexes cannot be inspected") from error
    signatures: list[tuple[str, tuple[int, int, int, int, str]]] = []
    total = 0
    for entry in sorted(entries, key=lambda item: os.fsencode(item.name)):
        signature = git_regular_file_signature(
            Path(entry.path),
            "Git shared index",
            required=True,
            maximum=MAX_GIT_INDEX_BYTES - total,
        )
        assert signature is not None
        if signature[0] != directory_metadata.st_dev:
            raise IndexContractError("Git shared index contains path indirection")
        total += signature[3]
        if total > MAX_GIT_INDEX_BYTES:
            raise IndexContractError("Git shared indexes exceed the bounded size")
        # Git refreshes a live shared index's mtime while reading the split
        # index, even with optional locks disabled. Keep the per-read mtime
        # stability check above, but compare preflights by file identity,
        # mode, size, and content so that timestamp-only liveness touches do
        # not make every genuine split-index repository unverifiable.
        stable_signature = (
            signature[0],
            signature[1],
            signature[2],
            signature[3],
            signature[5],
        )
        signatures.append((entry.name, stable_signature))
    return tuple(signatures)


def expected_git_control_paths(
    git_directory: Path, common_directory: Path
) -> dict[str, str]:
    return {
        "HEAD": str(git_directory / "HEAD"),
        "index": str(git_directory / "index"),
        "shallow": str(common_directory / "shallow"),
        "info/exclude": str(common_directory / "info" / "exclude"),
        "info/attributes": str(common_directory / "info" / "attributes"),
        "info/sparse-checkout": str(
            git_directory / "info" / "sparse-checkout"
        ),
        "packed-refs": str(common_directory / "packed-refs"),
        "refs": str(common_directory / "refs"),
        "refs/worktree": str(git_directory / "refs" / "worktree"),
        "refs/bisect": str(git_directory / "refs" / "bisect"),
        "refs/rewritten": str(git_directory / "refs" / "rewritten"),
    }


def reported_git_control_paths(
    root: Path, relative_paths: Sequence[str]
) -> dict[str, str]:
    arguments: list[str] = ["rev-parse", "--path-format=absolute"]
    for relative in relative_paths:
        arguments.extend(("--git-path", relative))
    raw = git_text(root, *arguments)
    values = raw.splitlines()
    if len(values) != len(relative_paths):
        raise IndexContractError("Git control-path reporting is incomplete")
    reported: dict[str, str] = {}
    for relative, value in zip(relative_paths, values, strict=True):
        cleaned = clean_text(f"Git {relative} path", value)
        path = Path(cleaned)
        if not path.is_absolute():
            path = root / path
        lexical = Path(os.path.normpath(str(path)))
        try:
            resolved = lexical.resolve(strict=False)
        except OSError as error:
            raise IndexContractError(
                "Git control path cannot be resolved safely"
            ) from error
        if resolved != lexical:
            raise IndexContractError("Git control path contains indirection")
        reported[relative] = str(lexical)
    return reported


def object_storage_signature(
    common_directory: Path,
) -> tuple[Path, str, int]:
    expected = common_directory / "objects"
    try:
        common_metadata = common_directory.lstat()
        objects_metadata = expected.lstat()
        objects_directory = expected.resolve(strict=True)
    except OSError as error:
        raise IndexContractError("Git object storage is missing or unsafe") from error
    if (
        stat.S_ISLNK(objects_metadata.st_mode)
        or not stat.S_ISDIR(objects_metadata.st_mode)
        or objects_directory != expected
        or objects_metadata.st_dev != common_metadata.st_dev
    ):
        raise IndexContractError("Git object storage is indirect or unsafe")

    hasher = hashlib.sha256()
    entries_seen = 0
    pending: list[tuple[Path, tuple[str, ...]]] = [(objects_directory, ())]
    while pending:
        directory, relative_parent = pending.pop()
        try:
            with os.scandir(directory) as iterator:
                entries = []
                for entry in iterator:
                    entries_seen += 1
                    if entries_seen > MAX_GIT_OBJECT_ENTRIES:
                        raise IndexContractError(
                            "Git object storage exceeds the bounded entry count"
                        )
                    entries.append(entry)
                entries.sort(key=lambda entry: os.fsencode(entry.name))
        except OSError as error:
            raise IndexContractError("Git object storage cannot be inspected") from error
        for entry in entries:
            relative = relative_parent + (entry.name,)
            folded_relative = tuple(part.casefold() for part in relative)
            try:
                metadata = entry.stat(follow_symlinks=False)
            except OSError as error:
                raise IndexContractError(
                    "Git object storage changed during inspection"
                ) from error
            if (
                stat.S_ISLNK(metadata.st_mode)
                or metadata.st_dev != objects_metadata.st_dev
            ):
                raise IndexContractError("Git object storage contains indirection")
            if stat.S_ISDIR(metadata.st_mode):
                pending.append((Path(entry.path), relative))
                kind = b"directory"
            elif stat.S_ISREG(metadata.st_mode):
                kind = b"file"
            else:
                raise IndexContractError("Git object storage contains an unsafe entry")

            if folded_relative in {
                ("info", "alternates"),
                ("info", "http-alternates"),
            } and (relative != folded_relative or metadata.st_size):
                raise IndexContractError(
                    "Git alternate object storage is unsupported identity evidence"
                )
            if entry.name.casefold().endswith(".promisor"):
                raise IndexContractError(
                    "Git promisor object storage is unsupported identity evidence"
                )

            frame_digest(hasher, b"/".join(os.fsencode(part) for part in relative))
            frame_digest(hasher, kind)
            frame_digest(
                hasher,
                (
                    f"{metadata.st_dev}:{metadata.st_ino}:"
                    f"{stat.S_IMODE(metadata.st_mode)}:{metadata.st_size}:"
                    f"{metadata.st_mtime_ns}"
                ).encode("ascii"),
            )
    return objects_directory, hasher.hexdigest(), entries_seen


def git_layout_preflight(root: Path) -> dict[str, Any]:
    git_directory, common_directory, control_signatures = discover_git_layout(root)
    git_metadata = git_directory.lstat()
    common_metadata = common_directory.lstat()
    config_paths = [
        common_directory / "config",
        git_directory / "config.worktree",
    ]
    if git_directory != common_directory:
        config_paths.append(git_directory / "config")
    config_signatures: list[tuple[str, tuple[Any, ...] | None]] = []
    seen: set[Path] = set()
    for index, path in enumerate(config_paths):
        if path in seen:
            continue
        seen.add(path)
        signature = git_config_signature(
            path,
            "Git repository configuration",
            required=index == 0,
        )
        config_signatures.append((str(path), signature))
    control_paths = expected_git_control_paths(git_directory, common_directory)
    grafts_path = common_directory / "info" / "grafts"
    if os.path.lexists(grafts_path):
        raise IndexContractError(
            "Git graft overlays are unsupported identity evidence"
        )
    repository_control_signatures = {
        "head": git_regular_file_signature(
            Path(control_paths["HEAD"]),
            "Git HEAD",
            required=True,
            maximum=MAX_GIT_CONTROL_BYTES,
        ),
        "index": git_regular_file_signature(
            Path(control_paths["index"]),
            "Git index",
            required=False,
            maximum=MAX_GIT_INDEX_BYTES,
        ),
        "shallow": git_regular_file_signature(
            Path(control_paths["shallow"]),
            "Git shallow boundary",
            required=False,
            maximum=MAX_GIT_REFERENCE_BYTES,
        ),
        "packed_refs": git_regular_file_signature(
            Path(control_paths["packed-refs"]),
            "Git packed refs",
            required=False,
            maximum=MAX_GIT_REFERENCE_BYTES,
        ),
        "info": git_control_tree_signature(
            common_directory / "info",
            "Git info controls",
            required=False,
            expected_device=common_metadata.st_dev,
        ),
        "worktree_info": (
            git_control_tree_signature(
                git_directory / "info",
                "Git worktree info controls",
                required=False,
                expected_device=git_metadata.st_dev,
            )
            if git_directory != common_directory
            else None
        ),
        "refs": git_control_tree_signature(
            Path(control_paths["refs"]),
            "Git refs",
            required=False,
            expected_device=common_metadata.st_dev,
        ),
        "worktree_refs": (
            git_control_tree_signature(
                git_directory / "refs",
                "Git worktree refs",
                required=False,
                expected_device=git_metadata.st_dev,
            )
            if git_directory != common_directory
            else None
        ),
    }
    for label, signature, device in (
        ("Git HEAD", repository_control_signatures["head"], git_metadata.st_dev),
        ("Git index", repository_control_signatures["index"], git_metadata.st_dev),
        (
            "Git shallow boundary",
            repository_control_signatures["shallow"],
            common_metadata.st_dev,
        ),
        (
            "Git packed refs",
            repository_control_signatures["packed_refs"],
            common_metadata.st_dev,
        ),
    ):
        if signature is not None and signature[0] != device:
            raise IndexContractError(f"{label} contains path indirection")
    shared_signatures = [
        (str(git_directory), shared_index_signatures(git_directory))
    ]
    if common_directory != git_directory:
        shared_signatures.append(
            (str(common_directory), shared_index_signatures(common_directory))
        )
    return {
        "git_directory": str(git_directory),
        "common_directory": str(common_directory),
        "control_signatures": control_signatures,
        "config_signatures": tuple(config_signatures),
        "control_paths": control_paths,
        "repository_control_signatures": repository_control_signatures,
        "shared_index_signatures": tuple(shared_signatures),
    }


def git_preflight(root: Path) -> dict[str, Any]:
    evidence = git_layout_preflight(root)
    objects_directory, object_signature, object_entries = object_storage_signature(
        Path(evidence["common_directory"])
    )
    return {
        **evidence,
        "objects_directory": str(objects_directory),
        "object_signature": object_signature,
        "object_entries": object_entries,
    }


def strict_absolute_path(value: str, label: str) -> Path:
    value = clean_text(label, value)
    path = Path(value)
    if not path.is_absolute():
        raise IndexContractError(f"{label} must be absolute")
    lexical = Path(os.path.normpath(value))
    if path != lexical:
        raise IndexContractError(f"{label} must be lexical-canonical: {lexical}")
    try:
        metadata = lexical.lstat()
    except OSError as error:
        raise IndexContractError(f"{label} does not exist: {lexical}: {error}") from error
    if stat.S_ISLNK(metadata.st_mode):
        raise IndexContractError(f"{label} must not be a symlink: {lexical}")
    try:
        resolved = lexical.resolve(strict=True)
    except OSError as error:
        raise IndexContractError(f"{label} cannot be resolved: {lexical}: {error}") from error
    if lexical != resolved:
        raise IndexContractError(f"{label} must use its canonical real path: {resolved}")
    return resolved


def absolute_git_path(root: Path, value: str, label: str) -> str:
    if not value:
        raise IndexContractError(f"Git did not report {label}")
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    try:
        resolved = str(path.resolve(strict=True))
    except OSError as error:
        raise IndexContractError(f"Git {label} is not resolvable") from error
    cleaned = clean_text(f"Git {label}", resolved)
    if cleaned != resolved:
        raise IndexContractError(f"Git {label} is not canonical text")
    return resolved


def instruction_records(root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for relative in INSTRUCTION_PATHS:
        path = root / relative
        cursor = root
        missing = False
        for part in Path(relative).parts:
            cursor /= part
            try:
                metadata = cursor.lstat()
            except FileNotFoundError:
                missing = True
                break
            except OSError as error:
                raise IndexContractError(
                    f"instruction path is inaccessible: {cursor}: {error}"
                ) from error
            if stat.S_ISLNK(metadata.st_mode):
                raise IndexContractError(
                    f"instruction path must not traverse a symlink: {cursor}"
                )
        if missing:
            continue
        data = read_regular_bytes(path, "instruction file", MAX_MANIFEST_BYTES)
        records.append(
            {"path": relative, "sha256": sha256_bytes(data), "bytes": len(data)}
        )
    return records


def working_tree_evidence(root: Path, head: str) -> dict[str, Any]:
    staged = git_bytes(
        root,
        "diff-index",
        "--cached",
        "--name-only",
        "-z",
        "--no-renames",
        "--no-ext-diff",
        "--no-textconv",
        head,
        "--",
    )
    staged_records = len([item for item in staged.split(b"\0") if item])
    positive_dirty_evidence = bool(staged)
    return {
        "state": "dirty" if positive_dirty_evidence else "unknown",
        "tracked_content": "not-inspected",
        "untracked_content": "not-inspected",
        "staged_records": staged_records,
        "staged_digest": sha256_bytes(staged),
    }


def bounded_root_commits(
    root: Path, head: str, expected_hex: int
) -> list[str]:
    commits: list[str] = []
    output = git_bytes(root, "rev-list", "--max-parents=0", head)
    for raw_line in io.BytesIO(output):
        raw_commit = raw_line.rstrip(b"\r\n")
        if not raw_commit:
            continue
        if len(commits) >= 256:
            raise IndexContractError(
                "Git root-commit lineage is missing or unbounded"
            )
        try:
            commit = raw_commit.decode("ascii")
        except UnicodeDecodeError as error:
            raise IndexContractError("Git root-commit lineage is invalid") from error
        if not re.fullmatch(rf"[0-9a-f]{{{expected_hex}}}", commit):
            raise IndexContractError("Git root-commit lineage is invalid")
        commits.append(commit)
    if not commits:
        raise IndexContractError("Git root-commit lineage is missing or unbounded")
    commits.sort()
    if len(set(commits)) != len(commits):
        raise IndexContractError("Git root-commit lineage is invalid")
    return commits


def compile_repository(root_value: str) -> dict[str, Any]:
    root = strict_absolute_path(root_value, "repository root")
    if not root.is_dir():
        raise IndexContractError(f"repository root must be a directory: {root}")
    layout_preflight = git_layout_preflight(root)
    reported_top = git_text(root, "rev-parse", "--show-toplevel")
    if not reported_top:
        raise IndexContractError(f"not a Git worktree: {root}")
    cleaned_top = clean_text("Git worktree root", reported_top)
    if (
        cleaned_top != reported_top
        or Path(os.path.normpath(reported_top)) != Path(reported_top)
        or reported_top != str(root)
    ):
        raise IndexContractError(
            "Git-reported worktree root is not the explicit canonical root"
        )
    try:
        top = Path(reported_top).resolve(strict=True)
    except OSError as error:
        raise IndexContractError("Git worktree root cannot be resolved") from error
    if top != root:
        raise IndexContractError("repository root must be the worktree root")

    manifest_path = root / "kingdom.yaml"
    manifest_bytes = read_regular_bytes(
        manifest_path, "kingdom manifest", MAX_MANIFEST_BYTES
    )
    manifest = parse_manifest(manifest_bytes)
    git_directory = absolute_git_path(
        root, git_text(root, "rev-parse", "--absolute-git-dir"), "directory"
    )
    common_directory = absolute_git_path(
        root, git_text(root, "rev-parse", "--git-common-dir"), "common directory"
    )
    objects_directory = absolute_git_path(
        root,
        git_text(
            root,
            "rev-parse",
            "--path-format=absolute",
            "--git-path",
            "objects",
        ),
        "objects directory",
    )
    if (
        git_directory != layout_preflight["git_directory"]
        or common_directory != layout_preflight["common_directory"]
        or objects_directory != str(Path(common_directory) / "objects")
    ):
        raise IndexContractError(
            "Git-reported control or object directories do not match bounded preflight"
        )
    reported_controls = reported_git_control_paths(
        root, tuple(layout_preflight["control_paths"])
    )
    if reported_controls != layout_preflight["control_paths"]:
        raise IndexContractError(
            "Git-reported control paths do not match bounded preflight"
        )
    preflight = git_preflight(root)
    if (
        any(preflight[key] != value for key, value in layout_preflight.items())
        or preflight["objects_directory"] != objects_directory
    ):
        raise IndexContractError(
            "Git layout or object storage changed during bounded preflight"
        )
    object_format = git_text(root, "rev-parse", "--show-object-format")
    if object_format not in {"sha1", "sha256"}:
        raise IndexContractError(f"unsupported Git object format: {object_format}")
    expected_hex = 40 if object_format == "sha1" else 64
    head = git_text(root, "rev-parse", "--verify", "HEAD")
    head_tree = git_text(root, "rev-parse", "--verify", f"{head}^{{tree}}")
    for label, value in (("HEAD", head), ("HEAD tree", head_tree)):
        if not re.fullmatch(rf"[0-9a-f]{{{expected_hex}}}", value):
            raise IndexContractError(f"Git {label} is invalid")
    grafts_path = Path(common_directory) / "info" / "grafts"
    if os.path.lexists(grafts_path):
        raise IndexContractError(
            "Git graft overlays are unsupported identity evidence"
        )
    shallow_text = git_text(root, "rev-parse", "--is-shallow-repository")
    if shallow_text not in {"true", "false"}:
        raise IndexContractError("Git shallow state is unknown")
    root_commits = bounded_root_commits(root, head, expected_hex)
    ref = git_text(
        root, "symbolic-ref", "--quiet", "--short", "HEAD", allow_failure=True
    ) or "DETACHED"
    ref = clean_text("Git ref", ref)
    worktree_evidence = working_tree_evidence(root, head)
    root_metadata = root.stat()
    instructions = instruction_records(root)
    lineage_complete = shallow_text == "false"
    lineage_digest = sha256_bytes(
        canonical_json(
            {
                "complete": lineage_complete,
                "object_format": object_format,
                "root_commits": root_commits,
            }
        )
    )
    manifest_record = {
        "path": "kingdom.yaml",
        "sha256": sha256_bytes(manifest_bytes),
        "bytes": len(manifest_bytes),
        "fields": manifest,
    }
    record: dict[str, Any] = {
        "repository_id": "",
        "canonical": False,
        "worktree_path": str(root),
        "path_identity": {
            "device": root_metadata.st_dev,
            "inode": root_metadata.st_ino,
        },
        "git": {
            "directory": git_directory,
            "common_directory": common_directory,
            "objects_directory": objects_directory,
            "object_format": object_format,
            "head": head,
            "head_tree": head_tree,
            "ref": ref,
            "shallow": shallow_text == "true",
            "root_commits": root_commits,
            "lineage_complete": lineage_complete,
            "lineage_digest": lineage_digest,
        },
        "working_tree": worktree_evidence,
        "manifest": manifest_record,
        "instructions": instructions,
    }
    identity = {
        "worktree_path": record["worktree_path"],
        "common_directory": common_directory,
        "objects_directory": objects_directory,
        "head": head,
        "manifest_name": unicodedata.normalize("NFC", manifest["name"]).casefold(),
    }
    record["repository_id"] = "repo-" + sha256_bytes(canonical_json(identity))[:32]

    end_metadata = root.stat()
    end_manifest = read_regular_bytes(
        manifest_path, "kingdom manifest", MAX_MANIFEST_BYTES
    )
    end_top = Path(
        git_text(root, "rev-parse", "--show-toplevel")
    ).resolve(strict=True)
    end_git_directory = absolute_git_path(
        root, git_text(root, "rev-parse", "--absolute-git-dir"), "directory"
    )
    end_common_directory = absolute_git_path(
        root,
        git_text(root, "rev-parse", "--git-common-dir"),
        "common directory",
    )
    end_objects_directory = absolute_git_path(
        root,
        git_text(
            root,
            "rev-parse",
            "--path-format=absolute",
            "--git-path",
            "objects",
        ),
        "objects directory",
    )
    end_reported_controls = reported_git_control_paths(
        root, tuple(layout_preflight["control_paths"])
    )
    end_shallow = git_text(root, "rev-parse", "--is-shallow-repository")
    end_root_commits = bounded_root_commits(root, head, expected_hex)
    end_ref = git_text(
        root, "symbolic-ref", "--quiet", "--short", "HEAD", allow_failure=True
    ) or "DETACHED"
    end_preflight = git_preflight(root)
    stable = (
        end_top == root
        and end_git_directory == git_directory
        and end_common_directory == common_directory
        and end_objects_directory == objects_directory
        and end_reported_controls == reported_controls
        and git_text(root, "rev-parse", "--verify", "HEAD") == head
        and end_shallow == shallow_text
        and end_root_commits == root_commits
        and end_ref == ref
        and end_preflight == preflight
        and (end_metadata.st_dev, end_metadata.st_ino)
        == (root_metadata.st_dev, root_metadata.st_ino)
        and end_manifest == manifest_bytes
        and not os.path.lexists(grafts_path)
        and instruction_records(root) == instructions
        and working_tree_evidence(root, head) == worktree_evidence
    )
    if not stable:
        raise IndexContractError(
            "repository evidence changed during compilation; retry a stable source"
        )
    return record


class DisjointSet:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def ambiguity_components(
    records: Sequence[dict[str, Any]],
) -> tuple[list[list[int]], dict[tuple[int, int], list[str]]]:
    sets = DisjointSet(len(records))
    pair_reasons: dict[tuple[int, int], list[str]] = {}
    for left in range(len(records)):
        for right in range(left + 1, len(records)):
            reasons: list[str] = []
            if (
                records[left]["git"]["common_directory"]
                == records[right]["git"]["common_directory"]
            ):
                reasons.append("git-common-directory")
            if (
                records[left]["git"]["lineage_complete"]
                and records[right]["git"]["lineage_complete"]
                and records[left]["git"]["lineage_digest"]
                == records[right]["git"]["lineage_digest"]
            ):
                reasons.append("complete-lineage")
            left_name = unicodedata.normalize(
                "NFC", records[left]["manifest"]["fields"]["name"]
            ).casefold()
            right_name = unicodedata.normalize(
                "NFC", records[right]["manifest"]["fields"]["name"]
            ).casefold()
            if left_name == right_name:
                reasons.append("manifest-name")
            if reasons:
                sets.union(left, right)
                pair_reasons[(left, right)] = reasons

    by_component: dict[int, list[int]] = {}
    for index in range(len(records)):
        by_component.setdefault(sets.find(index), []).append(index)
    components = sorted(
        by_component.values(),
        key=lambda members: records[members[0]]["worktree_path"],
    )
    return components, pair_reasons


def build_ambiguity_groups(
    records: Sequence[dict[str, Any]],
    components: Sequence[Sequence[int]],
    pair_reasons: dict[tuple[int, int], list[str]],
) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for members in components:
        selected = [index for index in members if records[index]["canonical"]]
        if len(selected) != 1:
            raise IndexContractError(
                "each repository identity component must have one canonical member"
            )
        if len(members) == 1:
            continue
        reasons = sorted(
            {
                reason
                for pair, pair_values in pair_reasons.items()
                if pair[0] in members and pair[1] in members
                for reason in pair_values
            }
        )
        repository_ids = sorted(records[index]["repository_id"] for index in members)
        group_subject = {"reasons": reasons, "repository_ids": repository_ids}
        groups.append(
            {
                "group_id": "ambiguity-"
                + sha256_bytes(canonical_json(group_subject))[:24],
                "reasons": reasons,
                "repository_ids": repository_ids,
                "canonical_repository_id": records[selected[0]]["repository_id"],
            }
        )
    groups.sort(key=lambda item: item["group_id"])
    return groups


def compile_index(
    repository_roots: Sequence[str], canonical_roots: Sequence[str] = ()
) -> dict[str, Any]:
    if not repository_roots:
        raise IndexContractError("at least one explicit repository root is required")
    if len(repository_roots) > MAX_INPUTS:
        raise IndexContractError(f"repository roots exceed {MAX_INPUTS}")
    if len(canonical_roots) > MAX_INPUTS:
        raise IndexContractError(f"canonical roots exceed {MAX_INPUTS}")
    if len(set(canonical_roots)) != len(canonical_roots):
        raise IndexContractError("canonical roots contain duplicate declarations")
    records = [compile_repository(value) for value in repository_roots]
    records.sort(key=lambda item: item["worktree_path"])
    paths = [item["worktree_path"] for item in records]
    if len(set(paths)) != len(paths):
        raise IndexContractError("repository roots contain duplicates or aliases")

    resolved_canonical = [
        str(strict_absolute_path(value, "canonical root"))
        for value in canonical_roots
    ]
    if len(set(resolved_canonical)) != len(resolved_canonical):
        raise IndexContractError("canonical roots contain duplicate aliases")
    explicit_canonical = set(resolved_canonical)
    unknown_canonical = sorted(explicit_canonical - set(paths))
    if unknown_canonical:
        raise IndexContractError(
            f"canonical root is not an indexed repository: {unknown_canonical[0]}"
        )

    components, pair_reasons = ambiguity_components(records)
    for members in components:
        selected = [
            index
            for index in members
            if records[index]["worktree_path"] in explicit_canonical
        ]
        if len(members) > 1 and len(selected) != 1:
            member_paths = ", ".join(records[index]["worktree_path"] for index in members)
            raise IndexContractError(
                "ambiguous repositories require exactly one --canonical-root: "
                + member_paths
            )
        canonical_index = selected[0] if selected else members[0]
        records[canonical_index]["canonical"] = True
    ambiguity_groups = build_ambiguity_groups(records, components, pair_reasons)

    for record in records:
        record["repository_digest"] = sha256_bytes(canonical_json(record))

    input_subject = [
        {
            "repository_id": record["repository_id"],
            "repository_digest": record["repository_digest"],
            "canonical": record["canonical"],
        }
        for record in records
    ]
    document: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "compiler": COMPILER_ID,
        "input_digest": sha256_bytes(canonical_json(input_subject)),
        "repositories": records,
        "ambiguity_groups": ambiguity_groups,
        "non_claims": list(NON_CLAIMS),
    }
    document["index_digest"] = sha256_bytes(canonical_json(document))
    if len(canonical_json(document)) > MAX_INDEX_BYTES:
        raise IndexContractError("compiled index exceeds the bounded size")
    return document


def read_roots_file(value: str) -> list[str]:
    if value == "-":
        data = sys.stdin.buffer.read(MAX_ROOTS_BYTES + 1)
    else:
        data = read_regular_bytes(Path(value), "roots file", MAX_ROOTS_BYTES)
    if len(data) > MAX_ROOTS_BYTES:
        raise IndexContractError("roots file is too large")
    if not data or not data.endswith(b"\0"):
        raise IndexContractError("roots file must be non-empty and NUL-terminated")
    raw_parts = data.split(b"\0")
    if raw_parts[-1] != b"" or any(not part for part in raw_parts[:-1]):
        raise IndexContractError("roots file contains an empty record")
    try:
        return [part.decode("utf-8") for part in raw_parts[:-1]]
    except UnicodeDecodeError as error:
        raise IndexContractError("roots file must contain UTF-8 paths") from error


def atomic_write(path: Path, data: bytes) -> None:
    if not path.is_absolute():
        raise IndexContractError("output path must be absolute")
    normalized = Path(os.path.normpath(str(path)))
    if normalized != path:
        raise IndexContractError(f"output path must be lexical-canonical: {normalized}")
    parent = path.parent
    try:
        resolved_parent = parent.resolve(strict=True)
        parent_metadata = parent.lstat()
    except OSError as error:
        raise IndexContractError(
            f"output parent is missing or unsafe: {parent}: {error}"
        ) from error
    if (
        resolved_parent != parent
        or not stat.S_ISDIR(parent_metadata.st_mode)
        or stat.S_ISLNK(parent_metadata.st_mode)
    ):
        raise IndexContractError(f"output parent is missing or unsafe: {parent}")
    if path.is_symlink():
        raise IndexContractError(f"refusing symlink output: {path}")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def require_exact_object(
    value: Any, keys: set[str], label: str
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise IndexContractError(f"{label} has missing or unknown keys")
    return value


def require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise IndexContractError(f"{label} is not a SHA-256 digest")
    return value


def require_nonnegative_integer(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise IndexContractError(f"{label} must be a non-negative integer")
    return value


def require_absolute_text(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise IndexContractError(f"{label} must be an absolute path")
    cleaned = clean_text(label, value)
    path = Path(value)
    if (
        cleaned != value
        or not path.is_absolute()
        or Path(os.path.normpath(value)) != path
    ):
        raise IndexContractError(f"{label} must be a canonical lexical absolute path")
    return value


def require_text_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise IndexContractError(f"{label} must be an array")
    cleaned: list[str] = []
    for index, item in enumerate(value):
        text = clean_text(f"{label}[{index}]", item)
        if text != item:
            raise IndexContractError(f"{label}[{index}] is not canonical text")
        cleaned.append(text)
    if len(set(cleaned)) != len(cleaned):
        raise IndexContractError(f"{label} contains duplicates")
    return cleaned


def validate_repository_record(record: dict[str, Any]) -> None:
    expected_repository_keys = {
        "repository_id",
        "canonical",
        "worktree_path",
        "path_identity",
        "git",
        "working_tree",
        "manifest",
        "instructions",
        "repository_digest",
    }
    require_exact_object(record, expected_repository_keys, "repository")
    repository_id = record["repository_id"]
    if not isinstance(repository_id, str) or not re.fullmatch(
        r"repo-[0-9a-f]{32}", repository_id
    ):
        raise IndexContractError("repository id is invalid")
    if type(record["canonical"]) is not bool:
        raise IndexContractError("repository canonical flag is invalid")
    worktree_path = require_absolute_text(
        record["worktree_path"], "repository worktree path"
    )

    identity = require_exact_object(
        record["path_identity"], {"device", "inode"}, "repository path identity"
    )
    require_nonnegative_integer(identity["device"], "repository path device")
    require_nonnegative_integer(identity["inode"], "repository path inode")

    git_record = require_exact_object(
        record["git"],
        {
            "directory",
            "common_directory",
            "objects_directory",
            "object_format",
            "head",
            "head_tree",
            "ref",
            "shallow",
            "root_commits",
            "lineage_complete",
            "lineage_digest",
        },
        "repository Git evidence",
    )
    git_directory = require_absolute_text(
        git_record["directory"], "repository Git directory"
    )
    common_directory = require_absolute_text(
        git_record["common_directory"], "repository Git common directory"
    )
    objects_directory = require_absolute_text(
        git_record["objects_directory"], "repository Git objects directory"
    )
    if objects_directory != str(Path(common_directory) / "objects"):
        raise IndexContractError(
            "repository Git objects directory is inconsistent"
        )
    object_format = git_record["object_format"]
    if object_format not in {"sha1", "sha256"}:
        raise IndexContractError("repository Git object format is invalid")
    expected_hex = 40 if object_format == "sha1" else 64
    for label in ("head", "head_tree"):
        if not isinstance(git_record[label], str) or not re.fullmatch(
            rf"[0-9a-f]{{{expected_hex}}}", git_record[label]
        ):
            raise IndexContractError(f"repository Git {label} is invalid")
    ref = clean_text("repository Git ref", git_record["ref"])
    if ref != git_record["ref"]:
        raise IndexContractError("repository Git ref is not canonical text")
    if type(git_record["shallow"]) is not bool or type(
        git_record["lineage_complete"]
    ) is not bool:
        raise IndexContractError("repository Git lineage flags are invalid")
    if git_record["lineage_complete"] != (not git_record["shallow"]):
        raise IndexContractError("repository Git lineage completeness is inconsistent")
    root_commits = git_record["root_commits"]
    if (
        not isinstance(root_commits, list)
        or not 1 <= len(root_commits) <= 256
        or root_commits != sorted(set(root_commits))
        or any(
            not isinstance(item, str)
            or not re.fullmatch(rf"[0-9a-f]{{{expected_hex}}}", item)
            for item in root_commits
        )
    ):
        raise IndexContractError("repository Git root commits are invalid")
    lineage_subject = {
        "complete": git_record["lineage_complete"],
        "object_format": object_format,
        "root_commits": root_commits,
    }
    if require_sha256(
        git_record["lineage_digest"], "repository Git lineage digest"
    ) != sha256_bytes(canonical_json(lineage_subject)):
        raise IndexContractError("repository Git lineage digest does not match")

    working_tree = require_exact_object(
        record["working_tree"],
        {
            "state",
            "tracked_content",
            "untracked_content",
            "staged_records",
            "staged_digest",
        },
        "repository working-tree evidence",
    )
    evidence_count = 0
    for kind in ("staged",):
        count = require_nonnegative_integer(
            working_tree[f"{kind}_records"],
            f"repository {kind} record count",
        )
        digest = require_sha256(
            working_tree[f"{kind}_digest"], f"repository {kind} digest"
        )
        if (count == 0) != (digest == sha256_bytes(b"")):
            raise IndexContractError(
                f"repository {kind} count and digest are inconsistent"
            )
        evidence_count += count
    expected_state = "dirty" if evidence_count else "unknown"
    if (
        working_tree["tracked_content"] != "not-inspected"
        or working_tree["untracked_content"] != "not-inspected"
        or working_tree["state"] != expected_state
    ):
        raise IndexContractError("repository dirty evidence is inconsistent")

    manifest = require_exact_object(
        record["manifest"],
        {"path", "sha256", "bytes", "fields"},
        "repository manifest evidence",
    )
    if manifest["path"] != "kingdom.yaml":
        raise IndexContractError("repository manifest path is invalid")
    require_sha256(manifest["sha256"], "repository manifest digest")
    manifest_bytes = require_nonnegative_integer(
        manifest["bytes"], "repository manifest byte count"
    )
    if not 0 < manifest_bytes <= MAX_MANIFEST_BYTES:
        raise IndexContractError("repository manifest byte count is out of bounds")
    fields = require_exact_object(
        manifest["fields"],
        {
            "name",
            "purpose",
            "kind",
            "domain",
            "layer",
            "owner_sister",
            "state",
            "depends_on",
            "adopts",
            "doors_count",
        },
        "repository manifest fields",
    )
    for key in REQUIRED_SCALARS:
        text = clean_text(f"manifest.{key}", fields[key])
        if text != fields[key]:
            raise IndexContractError(f"manifest.{key} is not canonical text")
    require_text_list(fields["depends_on"], "manifest.depends_on")
    require_text_list(fields["adopts"], "manifest.adopts")
    require_nonnegative_integer(fields["doors_count"], "manifest doors count")

    instructions = record["instructions"]
    if not isinstance(instructions, list):
        raise IndexContractError("repository instructions must be an array")
    instruction_paths: list[str] = []
    for instruction in instructions:
        instruction = require_exact_object(
            instruction,
            {"path", "sha256", "bytes"},
            "repository instruction evidence",
        )
        path = instruction["path"]
        if path not in INSTRUCTION_PATHS or path in instruction_paths:
            raise IndexContractError("repository instruction path is invalid")
        instruction_paths.append(path)
        require_sha256(instruction["sha256"], "repository instruction digest")
        byte_count = require_nonnegative_integer(
            instruction["bytes"], "repository instruction byte count"
        )
        if byte_count > MAX_MANIFEST_BYTES:
            raise IndexContractError("repository instruction is too large")
    expected_instruction_order = [
        path for path in INSTRUCTION_PATHS if path in instruction_paths
    ]
    if instruction_paths != expected_instruction_order:
        raise IndexContractError("repository instruction order is not canonical")

    expected_repository_id = "repo-" + sha256_bytes(
        canonical_json(
            {
                "worktree_path": worktree_path,
                "common_directory": common_directory,
                "objects_directory": objects_directory,
                "head": git_record["head"],
                "manifest_name": unicodedata.normalize(
                    "NFC", fields["name"]
                ).casefold(),
            }
        )
    )[:32]
    if repository_id != expected_repository_id:
        raise IndexContractError("repository id does not match its identity evidence")
    require_absolute_text(git_directory, "repository Git directory")
    supplied_repository_digest = require_sha256(
        record["repository_digest"], "repository digest"
    )
    repository_subject = dict(record)
    repository_subject.pop("repository_digest")
    if supplied_repository_digest != sha256_bytes(canonical_json(repository_subject)):
        raise IndexContractError("repository digest does not match")


def verify_document(data: bytes) -> dict[str, Any]:
    if len(data) > MAX_INDEX_BYTES:
        raise IndexContractError("index is too large")
    try:
        document = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise IndexContractError("index is not valid UTF-8 JSON") from error
    if not isinstance(document, dict):
        raise IndexContractError("index root must be an object")
    expected_top = {
        "schema",
        "compiler",
        "input_digest",
        "repositories",
        "ambiguity_groups",
        "non_claims",
        "index_digest",
    }
    if set(document) != expected_top:
        raise IndexContractError("index has missing or unknown top-level keys")
    if document.get("schema") != SCHEMA_ID or document.get("compiler") != COMPILER_ID:
        raise IndexContractError("index schema or compiler is unsupported")
    supplied = require_sha256(document.get("index_digest"), "index digest")
    subject = dict(document)
    subject.pop("index_digest", None)
    expected = sha256_bytes(canonical_json(subject))
    if supplied != expected:
        raise IndexContractError("index digest does not match")
    if data != canonical_json(document):
        raise IndexContractError("index is not in canonical JSON form")
    serialized = data.decode("utf-8")
    if "://" in serialized:
        raise IndexContractError("index contains a remote URL")
    if document.get("non_claims") != list(NON_CLAIMS):
        raise IndexContractError("index non-claims changed")
    repositories = document.get("repositories")
    if (
        not isinstance(repositories, list)
        or not repositories
        or len(repositories) > MAX_INPUTS
    ):
        raise IndexContractError("index repositories must be a non-empty array")
    repository_ids: set[str] = set()
    for record in repositories:
        if not isinstance(record, dict):
            raise IndexContractError("repository must be an object")
        validate_repository_record(record)
        repository_id = record["repository_id"]
        if repository_id in repository_ids:
            raise IndexContractError("repository ids are not unique")
        repository_ids.add(repository_id)
    worktree_paths = [record["worktree_path"] for record in repositories]
    if worktree_paths != sorted(worktree_paths) or len(set(worktree_paths)) != len(
        worktree_paths
    ):
        raise IndexContractError("repository order or paths are not canonical")
    expected_input = [
        {
            "repository_id": record["repository_id"],
            "repository_digest": record["repository_digest"],
            "canonical": record["canonical"],
        }
        for record in repositories
    ]
    if document.get("input_digest") != sha256_bytes(canonical_json(expected_input)):
        raise IndexContractError("input digest does not match repositories")
    groups = document.get("ambiguity_groups")
    if not isinstance(groups, list):
        raise IndexContractError("ambiguity groups must be an array")
    components, pair_reasons = ambiguity_components(repositories)
    expected_groups = build_ambiguity_groups(
        repositories, components, pair_reasons
    )
    if groups != expected_groups:
        raise IndexContractError(
            "ambiguity groups do not match repository identity evidence"
        )
    return document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    compile_parser = subparsers.add_parser("compile", help="compile an offline index")
    compile_parser.add_argument("--repo-root", action="append", default=[])
    compile_parser.add_argument("--roots-file")
    compile_parser.add_argument("--canonical-root", action="append", default=[])
    compile_parser.add_argument("--output", required=True)
    verify_parser = subparsers.add_parser("verify", help="verify canonical form and digest")
    verify_parser.add_argument("index")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "compile":
            roots = list(args.repo_root)
            if args.roots_file:
                roots.extend(read_roots_file(args.roots_file))
            document = compile_index(roots, args.canonical_root)
            data = canonical_json(document)
            if len(data) > MAX_INDEX_BYTES:
                raise IndexContractError("compiled index exceeds the bounded size")
            atomic_write(Path(args.output), data)
            print(args.output)
        else:
            path = Path(args.index)
            verify_document(read_regular_bytes(path, "index", MAX_INDEX_BYTES))
            print(f"verified {path}")
    except (IndexContractError, OSError, subprocess.SubprocessError) as error:
        print(f"kingdom-index: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
