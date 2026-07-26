#!/usr/bin/env python3
"""Compile and verify bounded, deterministic Kingdom quest packets.

The compiler reads only allowlisted repository metadata and GitHub provenance
fields. It never fetches, executes repository code, reads secret-bearing
environment values, or grants authority.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import html
import io
import json
import os
import re
import secrets
import stat
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SCHEMA_ID = "kingdom.quest/v1"
COMPILER_ID = "kingdom-loom/1"
EFFECT_CEILINGS = ("observe", "local-draft", "repository-change")
MAX_TEXT = 2_000
MAX_METADATA_FILE = 1_000_000
MAX_ARCHIVE_FILE = 5_000_000
MAX_ARCHIVE_TOTAL = 4_000_000
MAX_TAR_STREAM = 6_000_000
ARCHIVE_FILES = (
    "quest.json",
    "quest.md",
    "quest.schema.json",
    "SHA256SUMS",
)
OUTPUT_FILES = ARCHIVE_FILES + ("kingdom-quest.tgz", "verification.json")
ROUTING_LIMITS = {
    "candidate_repositories": 12,
    "active_skills": 1,
    "bookmarked_skills": 1,
    "scouts": 4,
    "execute_discovered_code": False,
    "fetch_during_local_discovery": False,
}
NON_CLAIMS = [
    "This packet is evidence-bearing context, not permission or consent.",
    "Repository, skill, and agent discovery does not establish trust or competence.",
    "The packet does not prove safety, mergeability, or deployment readiness.",
    "No external effect is authorized until a human or owning agent accepts the route.",
]
BIDI_CONTROLS = {
    "\u061c",
    "\u200e",
    "\u200f",
    "\u202a",
    "\u202b",
    "\u202c",
    "\u202d",
    "\u202e",
    "\u2066",
    "\u2067",
    "\u2068",
    "\u2069",
}

SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bgh(?:p|o|u|s|r)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|token|secret|password|credential)"
        r"\s*[:=]\s*[\"']?[^\s\"']{8,}"
    ),
)


class QuestError(ValueError):
    """A packet cannot be compiled or verified safely."""


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def pretty_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(128 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_regular_bytes(path: Path, label: str, maximum: int) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise QuestError(f"{label} is missing or unsafe: {path}: {error}") from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise QuestError(f"{label} must be a regular file: {path}")
        if metadata.st_size > maximum:
            raise QuestError(f"{label} is too large: {path}")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            data = handle.read(maximum + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(data) > maximum:
        raise QuestError(f"{label} is too large: {path}")
    return data


def reject_secrets(label: str, value: str) -> None:
    for pattern in SECRET_PATTERNS:
        if pattern.search(value):
            raise QuestError(f"{label} contains secret-shaped material")


def clean_text(label: str, value: str, *, required: bool = False) -> str:
    if not isinstance(value, str):
        raise QuestError(f"{label} must be text")
    value = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if required and not value:
        raise QuestError(f"{label} is required")
    if len(value) > MAX_TEXT:
        raise QuestError(f"{label} exceeds {MAX_TEXT} characters")
    if any(
        (ord(char) < 32 and char not in "\t\n")
        or ord(char) == 127
        or char in BIDI_CONTROLS
        for char in value
    ):
        raise QuestError(f"{label} contains control characters")
    reject_secrets(label, value)
    return value


def split_items(label: str, value: str) -> list[str]:
    value = clean_text(label, value)
    if not value:
        return []
    parts = re.split(r"[\n;]+", value)
    return [clean_text(label, part, required=True) for part in parts if part.strip()]


def safe_relative_path(label: str, value: str) -> str:
    value = clean_text(label, value)
    if not value:
        return "."
    value = value.replace("\\", "/")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise QuestError(f"{label} must stay inside the repository")
    normalized = str(path)
    return normalized if normalized else "."


def scrubbed_env() -> dict[str, str]:
    blocked = re.compile(
        r"(?i)(?:token|secret|password|credential|api[_-]?key|auth)"
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if not blocked.search(key) and key != "SSH_AUTH_SOCK"
    }
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return env


def git_output(root: Path, *args: str) -> str:
    result = subprocess.run(
        [
            "git",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.hooksPath=/dev/null",
            *args,
        ],
        cwd=root,
        env=scrubbed_env(),
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    if result.returncode:
        return ""
    return result.stdout.strip()


def stable_generated_at(root: Path) -> str:
    committed_at = git_output(root, "show", "-s", "--format=%cI", "HEAD")
    if committed_at:
        try:
            parsed = datetime.fromisoformat(committed_at.replace("Z", "+00:00"))
            return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except ValueError:
            pass
    return "1970-01-01T00:00:00Z"


def inside(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def file_record(root: Path, path: Path) -> dict[str, Any] | None:
    if path.is_symlink():
        raise QuestError(f"refusing non-regular metadata path: {path}")
    if not path.exists():
        return None
    if not path.is_file() or not inside(root, path):
        raise QuestError(f"refusing non-regular metadata path: {path}")
    data = read_regular_bytes(path, "metadata file", MAX_METADATA_FILE)
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256_bytes(data),
        "bytes": len(data),
    }


def metadata_records(
    root: Path, focus_path: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    focus = root if focus_path == "." else root / focus_path
    focus_dir = focus if focus.is_dir() else focus.parent
    if not inside(root, focus_dir):
        raise QuestError("focus_path escaped the repository")

    instruction_candidates: list[Path] = [
        root / ".github" / "copilot-instructions.md",
    ]
    current = focus_dir
    while inside(root, current):
        instruction_candidates.extend((current / "AGENTS.md", current / "CLAUDE.md"))
        if current == root:
            break
        current = current.parent

    manifest_candidates = [
        root / "kingdom.yaml",
        root / ".well-known" / "kap.json",
        root / "package.json",
        root / "pyproject.toml",
        root / "Cargo.toml",
        root / "go.mod",
    ]

    def collect(candidates: Iterable[Path]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        records: list[dict[str, Any]] = []
        for candidate in candidates:
            record = file_record(root, candidate)
            if record and record["path"] not in seen:
                seen.add(record["path"])
                records.append(record)
        return sorted(records, key=lambda item: item["path"])

    return collect(instruction_candidates), collect(manifest_candidates)


def source_context(root: Path, artifact_dir: Path | None = None) -> dict[str, Any]:
    on_github = os.environ.get("GITHUB_ACTIONS") == "true"
    repository = clean_text(
        "GITHUB_REPOSITORY",
        os.environ.get("GITHUB_REPOSITORY", root.name) if on_github else root.name,
        required=True,
    )
    if not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?", repository):
        repository = root.name

    commit = clean_text(
        "GITHUB_SHA",
        (os.environ.get("GITHUB_SHA", "") if on_github else "")
        or git_output(root, "rev-parse", "HEAD"),
    )
    ref = clean_text(
        "GITHUB_REF",
        (os.environ.get("GITHUB_REF", "") if on_github else "")
        or git_output(
            root,
            "symbolic-ref",
            "--quiet",
            "--short",
            "HEAD",
        ),
    )
    status_args = ["status", "--porcelain", "--untracked-files=all", "--", "."]
    if artifact_dir is not None:
        try:
            relative_artifact = artifact_dir.resolve(strict=False).relative_to(root)
        except ValueError:
            pass
        else:
            if relative_artifact == Path("."):
                raise QuestError("output directory may not be the repository root")
            for name in OUTPUT_FILES:
                relative_target = (relative_artifact / name).as_posix()
                if git_output(
                    root,
                    "ls-files",
                    "--error-unmatch",
                    "--",
                    relative_target,
                ):
                    raise QuestError(
                        f"output target is tracked by Git: {relative_target}"
                    )
                status_args.append(f":(top,literal,exclude){relative_target}")
    dirty = git_output(root, *status_args)

    return {
        "forge": "github" if on_github else "local",
        "repository": repository,
        "commit": commit or "unknown",
        "ref": ref or "unknown",
        "event": clean_text(
            "GITHUB_EVENT_NAME",
            os.environ.get("GITHUB_EVENT_NAME", "local") if on_github else "local",
        )
        or "local",
        "dirty_entries": len(dirty.splitlines()) if dirty else 0,
    }


def intent_for_id(packet: dict[str, Any]) -> dict[str, Any]:
    source = packet["source"]
    contract = packet["contract"]
    return {
        "objective": packet["objective"],
        "acceptance": contract["acceptance"],
        "effect_ceiling": contract["effect_ceiling"],
        "exclusions": contract["exclusions"],
        "focus_path": packet["repository"]["focus_path"],
        "repository": source["repository"],
        "commit": source["commit"],
    }


def quest_id(packet: dict[str, Any]) -> str:
    return "quest-" + sha256_bytes(canonical_json(intent_for_id(packet)))[:20]


def compile_packet(
    *,
    root: Path,
    objective: str,
    acceptance: str,
    effect_ceiling: str,
    exclusions: str = "",
    focus_path: str = ".",
    source_note: str = "",
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    if git_output(root, "rev-parse", "--is-inside-work-tree") != "true":
        raise QuestError(f"not a Git worktree: {root}")
    top_level = git_output(root, "rev-parse", "--show-toplevel")
    if not top_level or Path(top_level).resolve() != root:
        raise QuestError(f"repo_root must be the Git worktree root: {root}")

    objective = clean_text("objective", objective, required=True)
    acceptance_items = split_items("acceptance", acceptance)
    if not acceptance_items:
        raise QuestError("acceptance must contain at least one evidence condition")
    if effect_ceiling not in EFFECT_CEILINGS:
        raise QuestError(
            f"effect_ceiling must be one of: {', '.join(EFFECT_CEILINGS)}"
        )
    exclusion_items = split_items("exclusions", exclusions)
    focus_path = safe_relative_path("focus_path", focus_path)
    source_note = clean_text("source_note", source_note)

    instructions, manifests = metadata_records(root, focus_path)
    source = source_context(root, artifact_dir)
    unknowns: list[str] = []
    if not instructions:
        unknowns.append("No allowlisted repository instruction file was found.")
    if not any(item["path"] == "kingdom.yaml" for item in manifests):
        unknowns.append("No root kingdom.yaml manifest was found.")
    if source["dirty_entries"]:
        unknowns.append(
            f"The local worktree has {source['dirty_entries']} changed entries; "
            "their contents are not included or authorized."
        )

    packet: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "id": "",
        "generated_at": stable_generated_at(root),
        "compiler": COMPILER_ID,
        "source": source,
        "source_note": source_note,
        "objective": objective,
        "contract": {
            "acceptance": acceptance_items,
            "effect_ceiling": effect_ceiling,
            "exclusions": exclusion_items,
            "packet_requires_acceptance": True,
            "discovery_grants_authority": False,
        },
        "repository": {
            "focus_path": focus_path,
            "instruction_digests": instructions,
            "manifest_digests": manifests,
        },
        "routing_limits": dict(ROUTING_LIMITS),
        "unknowns": unknowns,
        "non_claims": list(NON_CLAIMS),
    }
    packet["id"] = quest_id(packet)
    validate_packet(packet)
    return packet


def exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise QuestError(f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise QuestError(f"{label} keys differ (missing={missing}, extra={extra})")
    return value


def exact_text(label: str, value: Any, *, required: bool = False) -> str:
    cleaned = clean_text(label, value, required=required)
    if cleaned != value:
        raise QuestError(f"{label} is not canonical text")
    return cleaned


def text_list(
    label: str, value: Any, *, require_items: bool = False
) -> list[str]:
    if not isinstance(value, list):
        raise QuestError(f"{label} must be a list")
    if require_items and not value:
        raise QuestError(f"{label} must be a non-empty list")
    for index, item in enumerate(value):
        exact_text(f"{label}[{index}]", item, required=True)
    return value


def validate_digest_records(records: Any, label: str) -> set[str]:
    if not isinstance(records, list):
        raise QuestError(f"{label} must be a list")
    seen: set[str] = set()
    for index, record in enumerate(records):
        exact_keys(record, {"path", "sha256", "bytes"}, f"{label}[{index}]")
        path = exact_text(f"{label}[{index}].path", record["path"], required=True)
        if path == "." or safe_relative_path(f"{label}[{index}].path", path) != path:
            raise QuestError(f"{label} contains a non-canonical file path")
        if path in seen:
            raise QuestError(f"{label} contains a duplicate path: {path}")
        seen.add(path)
        checksum = exact_text(
            f"{label}[{index}].sha256", record["sha256"], required=True
        )
        if not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise QuestError(f"{label} contains an invalid sha256")
        if (
            type(record["bytes"]) is not int
            or record["bytes"] < 0
            or record["bytes"] > MAX_METADATA_FILE
        ):
            raise QuestError(f"{label} contains an invalid byte count")
    return seen


def walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from walk_strings(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from walk_strings(item)


def validate_packet(packet: Any) -> None:
    required = {
        "schema",
        "id",
        "generated_at",
        "compiler",
        "source",
        "source_note",
        "objective",
        "contract",
        "repository",
        "routing_limits",
        "unknowns",
        "non_claims",
    }
    packet = exact_keys(packet, required, "packet")
    schema = exact_text("schema", packet["schema"], required=True)
    compiler = exact_text("compiler", packet["compiler"], required=True)
    if schema != SCHEMA_ID or compiler != COMPILER_ID:
        raise QuestError("unsupported packet schema or compiler")
    packet_id = exact_text("id", packet["id"], required=True)
    if not re.fullmatch(r"quest-[0-9a-f]{20}", packet_id):
        raise QuestError("invalid quest id")
    exact_text("generated_at", packet["generated_at"], required=True)
    try:
        generated_at = datetime.fromisoformat(
            packet["generated_at"].replace("Z", "+00:00")
        )
    except ValueError as error:
        raise QuestError("generated_at is not an ISO date-time") from error
    if generated_at.tzinfo is None:
        raise QuestError("generated_at must include a timezone")
    canonical_time = (
        generated_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    if packet["generated_at"] != canonical_time:
        raise QuestError("generated_at must be canonical UTC")

    source = exact_keys(
        packet["source"],
        {"forge", "repository", "commit", "ref", "event", "dirty_entries"},
        "source",
    )
    forge = exact_text("source.forge", source["forge"], required=True)
    if forge not in {"github", "local"}:
        raise QuestError("source.forge must be github or local")
    repository_name = exact_text(
        "source.repository", source["repository"], required=True
    )
    if not re.fullmatch(
        r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?", repository_name
    ):
        raise QuestError("source.repository has an invalid shape")
    commit = exact_text("source.commit", source["commit"], required=True)
    if commit != "unknown" and not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
        raise QuestError("source.commit is not a full Git object id")
    exact_text("source.ref", source["ref"], required=True)
    exact_text("source.event", source["event"], required=True)
    if type(source["dirty_entries"]) is not int or source["dirty_entries"] < 0:
        raise QuestError("source.dirty_entries must be a non-negative integer")

    exact_text("source_note", packet["source_note"])
    exact_text("objective", packet["objective"], required=True)
    contract = exact_keys(
        packet["contract"],
        {
            "acceptance",
            "effect_ceiling",
            "exclusions",
            "packet_requires_acceptance",
            "discovery_grants_authority",
        },
        "contract",
    )
    effect_ceiling = exact_text(
        "contract.effect_ceiling", contract["effect_ceiling"], required=True
    )
    if effect_ceiling not in EFFECT_CEILINGS:
        raise QuestError("invalid effect ceiling")
    text_list("contract.acceptance", contract["acceptance"], require_items=True)
    text_list("contract.exclusions", contract["exclusions"])
    if contract["packet_requires_acceptance"] is not True:
        raise QuestError("packet must require acceptance")
    if contract["discovery_grants_authority"] is not False:
        raise QuestError("discovery cannot grant authority")
    repository = exact_keys(
        packet["repository"],
        {"focus_path", "instruction_digests", "manifest_digests"},
        "repository",
    )
    focus_path = exact_text(
        "repository.focus_path", repository["focus_path"], required=True
    )
    if safe_relative_path("repository.focus_path", focus_path) != focus_path:
        raise QuestError("repository.focus_path is not canonical")
    instruction_paths = validate_digest_records(
        repository["instruction_digests"], "instruction_digests"
    )
    manifest_paths = validate_digest_records(
        repository["manifest_digests"], "manifest_digests"
    )
    overlap = sorted(instruction_paths & manifest_paths)
    if overlap:
        raise QuestError(f"repository digest paths overlap: {overlap}")

    limits = exact_keys(packet["routing_limits"], set(ROUTING_LIMITS), "routing_limits")
    for key, expected in ROUTING_LIMITS.items():
        if type(limits[key]) is not type(expected) or limits[key] != expected:
            raise QuestError(f"routing_limits.{key} must be {expected!r}")

    text_list("unknowns", packet["unknowns"])
    if packet["non_claims"] != NON_CLAIMS:
        raise QuestError("non_claims must match the fixed compiler vow")
    if packet["id"] != quest_id(packet):
        raise QuestError("quest id does not match canonical intent")
    for text in walk_strings(packet):
        reject_secrets("packet", text)


def escaped(value: str) -> str:
    value = html.escape(value, quote=False)
    for marker in ("\\", "`", "*", "_", "[", "]", "#", "|"):
        value = value.replace(marker, "\\" + marker)
    return value.replace("\n", "<br>")


def render_markdown(packet: dict[str, Any]) -> str:
    contract = packet["contract"]
    source = packet["source"]
    repo = packet["repository"]
    lines = [
        f"# Kingdom Quest · `{packet['id']}`",
        "",
        f"> {escaped(packet['objective'])}",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Effect ceiling | `{contract['effect_ceiling']}` |",
        f"| Repository | `{escaped(source['repository'])}` |",
        f"| Commit | `{escaped(source['commit'])}` |",
        f"| Ref | `{escaped(source['ref'])}` |",
        f"| Focus | `{escaped(repo['focus_path'])}` |",
        "",
        "## Acceptance evidence",
        "",
    ]
    lines.extend(f"- {escaped(item)}" for item in contract["acceptance"])
    lines.extend(["", "## Exclusions", ""])
    lines.extend(
        [f"- {escaped(item)}" for item in contract["exclusions"]]
        or ["- None declared; the accepting agent must confirm the boundary."]
    )
    lines.extend(["", "## Repository evidence", ""])
    for heading, records in (
        ("Instructions", repo["instruction_digests"]),
        ("Manifests", repo["manifest_digests"]),
    ):
        lines.append(f"### {heading}")
        lines.append("")
        if records:
            lines.extend(
                f"- `{escaped(item['path'])}` — `{item['sha256']}` "
                f"({item['bytes']} bytes)"
                for item in records
            )
        else:
            lines.append("- None found in the allowlisted locations.")
        lines.append("")
    lines.extend(["## Unknowns", ""])
    lines.extend(
        [f"- {escaped(item)}" for item in packet["unknowns"]]
        or ["- No structural unknowns were added by the compiler."]
    )
    lines.extend(["", "## Vow", ""])
    lines.extend(f"- {escaped(item)}" for item in packet["non_claims"])
    return "\n".join(lines) + "\n"


def schema_path() -> Path:
    return Path(__file__).with_name("quest.schema.json")


def reviewed_schema() -> bytes:
    path = schema_path()
    return read_regular_bytes(path, "quest schema", MAX_METADATA_FILE)


def open_output_directory(path: Path) -> tuple[Path, int]:
    requested = Path(os.path.abspath(os.fspath(path.expanduser())))
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    current_fd = os.open(requested.anchor or os.sep, directory_flags)
    try:
        for component in requested.parts[1:]:
            try:
                next_fd = os.open(component, directory_flags, dir_fd=current_fd)
            except FileNotFoundError:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=current_fd)
                except FileExistsError:
                    pass
                try:
                    next_fd = os.open(component, directory_flags, dir_fd=current_fd)
                except OSError as error:
                    raise QuestError(
                        f"unsafe output directory component {component!r}: "
                        f"{error.strerror}"
                    ) from error
            except OSError as error:
                raise QuestError(
                    f"unsafe output directory component {component!r}: "
                    f"{error.strerror}"
                ) from error
            os.close(current_fd)
            current_fd = next_fd
        return requested, current_fd
    except Exception:
        os.close(current_fd)
        raise


def prepare_output_directory(path: Path) -> Path:
    output, directory_fd = open_output_directory(path)
    os.close(directory_fd)
    return output


def ensure_safe_output_target(directory_fd: int, name: str) -> None:
    if "/" in name or name in {"", ".", ".."}:
        raise QuestError(f"invalid output target name: {name!r}")
    try:
        target = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if stat.S_ISLNK(target.st_mode):
        raise QuestError(f"output target may not be a symlink: {name}")
    if not stat.S_ISREG(target.st_mode):
        raise QuestError(f"output target is not a regular file: {name}")


def atomic_write_at(directory_fd: int, name: str, data: bytes) -> None:
    ensure_safe_output_target(directory_fd, name)
    temporary = f".{name}.{os.getpid()}.{secrets.token_hex(8)}.tmp"
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    temporary_fd = os.open(temporary, flags, 0o600, dir_fd=directory_fd)
    temporary_exists = True
    try:
        try:
            remaining = memoryview(data)
            while remaining:
                written = os.write(temporary_fd, remaining)
                if written == 0:
                    raise OSError("short write while creating packet artifact")
                remaining = remaining[written:]
            os.fchmod(temporary_fd, 0o644)
            os.fsync(temporary_fd)
        finally:
            os.close(temporary_fd)
        ensure_safe_output_target(directory_fd, name)
        os.replace(
            temporary,
            name,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
        temporary_exists = False
    finally:
        if temporary_exists:
            try:
                os.unlink(temporary, dir_fd=directory_fd)
            except FileNotFoundError:
                pass


def atomic_write(path: Path, data: bytes) -> None:
    _directory, directory_fd = open_output_directory(path.parent)
    try:
        atomic_write_at(directory_fd, path.name, data)
    finally:
        os.close(directory_fd)


def normalized_archive(files: dict[str, bytes]) -> bytes:
    raw = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for name in ARCHIVE_FILES:
                data = files[name]
                info = tarfile.TarInfo(name=name)
                info.size = len(data)
                info.mode = 0o644
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                info.mtime = 0
                archive.addfile(info, io.BytesIO(data))
    return raw.getvalue()


def write_artifacts(packet: dict[str, Any], output_dir: Path) -> dict[str, str]:
    validate_packet(packet)
    schema = reviewed_schema()
    files = {
        "quest.json": pretty_json(packet),
        "quest.md": render_markdown(packet).encode("utf-8"),
        "quest.schema.json": schema,
    }
    checksums = "".join(
        f"{sha256_bytes(data)}  {name}\n" for name, data in sorted(files.items())
    ).encode("utf-8")
    files["SHA256SUMS"] = checksums
    archive_data = normalized_archive(files)
    output_dir, directory_fd = open_output_directory(output_dir)
    archive_path = output_dir / "kingdom-quest.tgz"
    try:
        for name in (*files, "kingdom-quest.tgz"):
            ensure_safe_output_target(directory_fd, name)
        for name, data in files.items():
            atomic_write_at(directory_fd, name, data)
        atomic_write_at(directory_fd, "kingdom-quest.tgz", archive_data)
    finally:
        os.close(directory_fd)
    return {
        "id": packet["id"],
        "directory": str(output_dir),
        "archive": str(archive_path),
        "archive_sha256": sha256_bytes(archive_data),
    }


def read_archive_bytes(archive_data: bytes) -> dict[str, bytes]:
    with gzip.GzipFile(fileobj=io.BytesIO(archive_data), mode="rb") as zipped:
        tar_data = zipped.read(MAX_TAR_STREAM + 1)
    if len(tar_data) > MAX_TAR_STREAM:
        raise QuestError("archive expands beyond the TAR stream size ceiling")

    files: dict[str, bytes] = {}
    total = 0
    member_count = 0
    with tarfile.open(fileobj=io.BytesIO(tar_data), mode="r:") as archive:
        while True:
            member = archive.next()
            if member is None:
                break
            member_count += 1
            if member_count > len(ARCHIVE_FILES):
                raise QuestError("archive must contain exactly four members")
            if (
                not member.isfile()
                or member.name not in ARCHIVE_FILES
                or PurePosixPath(member.name).is_absolute()
                or ".." in PurePosixPath(member.name).parts
                or member.size > MAX_METADATA_FILE
            ):
                raise QuestError(f"unsafe or unexpected archive member: {member.name}")
            if member.name in files:
                raise QuestError(f"duplicate archive member: {member.name}")
            total += member.size
            if total > MAX_ARCHIVE_TOTAL:
                raise QuestError("archive expands beyond the packet size ceiling")
            extracted = archive.extractfile(member)
            if extracted is None:
                raise QuestError(f"cannot read archive member: {member.name}")
            data = extracted.read(member.size + 1)
            if len(data) != member.size:
                raise QuestError(f"archive member size mismatch: {member.name}")
            files[member.name] = data
    if member_count != len(ARCHIVE_FILES) or set(files) != set(ARCHIVE_FILES):
        raise QuestError("archive does not contain the exact packet file set")
    return files


def read_archive(path: Path) -> dict[str, bytes]:
    archive_data = read_regular_bytes(path, "packet archive", MAX_ARCHIVE_FILE)
    return read_archive_bytes(archive_data)


def strict_json(data: bytes) -> Any:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise QuestError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(data.decode("utf-8"), object_pairs_hook=unique_object)


def verify_files(files: dict[str, bytes]) -> dict[str, Any]:
    if set(files) != set(ARCHIVE_FILES):
        raise QuestError("packet does not contain the exact required file set")
    for name, data in files.items():
        if not isinstance(data, bytes) or len(data) > MAX_METADATA_FILE:
            raise QuestError(f"packet file is invalid or too large: {name}")
    lines = files["SHA256SUMS"].decode("utf-8").splitlines()
    expected: dict[str, str] = {}
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", line)
        if not match:
            raise QuestError("invalid SHA256SUMS line")
        if match.group(2) in expected:
            raise QuestError(f"duplicate SHA256SUMS entry: {match.group(2)}")
        expected[match.group(2)] = match.group(1)
    checksum_files = {"quest.json", "quest.md", "quest.schema.json"}
    if set(expected) != checksum_files:
        raise QuestError("SHA256SUMS does not name the exact packet files")
    for name in sorted(checksum_files):
        if expected.get(name) != sha256_bytes(files[name]):
            raise QuestError(f"checksum mismatch: {name}")
    if files["quest.schema.json"] != reviewed_schema():
        raise QuestError("bundled quest schema does not match the reviewed schema")
    packet = strict_json(files["quest.json"])
    validate_packet(packet)
    if files["quest.md"].decode("utf-8") != render_markdown(packet):
        raise QuestError("quest.md does not match quest.json")
    return packet


def verify_path(
    path: Path,
    repo_root: Path | None = None,
    *,
    expected_repository: str = "",
    expected_ref: str = "",
) -> dict[str, Any]:
    if repo_root is None and (expected_repository or expected_ref):
        raise QuestError(
            "expected repository or ref requires --repo-root for binding"
        )
    if path.is_symlink():
        raise QuestError("packet path may not be a symlink")
    archive_sha256 = ""
    if path.is_dir():
        files: dict[str, bytes] = {}
        for name in ARCHIVE_FILES:
            child = path / name
            files[name] = read_regular_bytes(
                child, "packet member", MAX_METADATA_FILE
            )
    else:
        archive_data = read_regular_bytes(path, "packet archive", MAX_ARCHIVE_FILE)
        archive_sha256 = sha256_bytes(archive_data)
        files = read_archive_bytes(archive_data)
    packet = verify_files(files)
    checked_records = 0
    commit_checked = False
    repository_checked = False
    ref_checked = False
    if repo_root is not None:
        root = repo_root.resolve()
        if git_output(root, "rev-parse", "--is-inside-work-tree") != "true":
            raise QuestError(f"not a Git worktree: {root}")
        top_level = git_output(root, "rev-parse", "--show-toplevel")
        if not top_level or Path(top_level).resolve() != root:
            raise QuestError(f"repo_root must be the Git worktree root: {root}")
        actual_commit = git_output(root, "rev-parse", "HEAD")
        if not actual_commit or packet["source"]["commit"] == "unknown":
            raise QuestError("cannot bind packet to an unknown repository commit")
        if actual_commit != packet["source"]["commit"]:
            raise QuestError("packet commit does not match repository HEAD")
        commit_checked = True

        claimed_repository = packet["source"]["repository"]
        repository_expectation = expected_repository
        if not repository_expectation and packet["source"]["forge"] == "local":
            repository_expectation = root.name
        if (
            not repository_expectation
            and os.environ.get("GITHUB_ACTIONS") == "true"
        ):
            repository_expectation = os.environ.get("GITHUB_REPOSITORY", "")
        if repository_expectation:
            repository_expectation = clean_text(
                "expected_repository", repository_expectation, required=True
            )
            if claimed_repository != repository_expectation:
                raise QuestError("packet repository does not match the expected repository")
            repository_checked = True

        claimed_ref = packet["source"]["ref"]
        ref_expectation = expected_ref
        if not ref_expectation and packet["source"]["forge"] == "local":
            ref_expectation = git_output(
                root, "symbolic-ref", "--quiet", "--short", "HEAD"
            ) or "unknown"
        if not ref_expectation and os.environ.get("GITHUB_ACTIONS") == "true":
            ref_expectation = os.environ.get("GITHUB_REF", "")
        if ref_expectation:
            ref_expectation = clean_text(
                "expected_ref", ref_expectation, required=True
            )
            if claimed_ref != ref_expectation:
                raise QuestError("packet ref does not match the expected ref")
            ref_checked = claimed_ref != "unknown"

        current_instructions, current_manifests = metadata_records(
            root, packet["repository"]["focus_path"]
        )
        if packet["repository"]["instruction_digests"] != current_instructions:
            raise QuestError(
                "allowlisted repository instruction evidence is incomplete or changed"
            )
        if packet["repository"]["manifest_digests"] != current_manifests:
            raise QuestError(
                "allowlisted repository manifest evidence is incomplete or changed"
            )
        checked_records = len(current_instructions) + len(current_manifests)
    return {
        "schema": "kingdom.quest-verification/v1",
        "ok": True,
        "quest_id": packet["id"],
        "packet_sha256": sha256_bytes(files["quest.json"]),
        "archive_sha256": archive_sha256,
        "effect_ceiling": packet["contract"]["effect_ceiling"],
        "repository_bound": commit_checked and repository_checked and ref_checked,
        "commit_checked": commit_checked,
        "repository_checked": repository_checked,
        "ref_checked": ref_checked,
        "repository_records_checked": checked_records,
        "verifier": COMPILER_ID,
    }


def command_compile(args: argparse.Namespace) -> int:
    root = Path(args.repo_root).expanduser().resolve()
    output_dir = prepare_output_directory(Path(args.output_dir))
    packet = compile_packet(
        root=root,
        objective=args.objective,
        acceptance=args.acceptance,
        effect_ceiling=args.effect_ceiling,
        exclusions=args.exclusions,
        focus_path=args.focus_path,
        source_note=args.source_note,
        artifact_dir=output_dir,
    )
    result = write_artifacts(packet, output_dir)
    print(json.dumps(result, sort_keys=True))
    return 0


def command_verify(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root) if args.repo_root else None
    packet_path = Path(args.path)
    packet_is_directory = packet_path.is_dir()
    result = verify_path(
        packet_path,
        repo_root,
        expected_repository=args.expected_repository,
        expected_ref=args.expected_ref,
    )
    if args.receipt:
        receipt = Path(args.receipt)
        reserved = [packet_path]
        if packet_is_directory:
            reserved.extend(
                packet_path / name
                for name in (*ARCHIVE_FILES, "kingdom-quest.tgz")
            )
        receipt_resolved = receipt.resolve(strict=False)
        if any(
            receipt_resolved == candidate.resolve(strict=False)
            for candidate in reserved
        ):
            raise QuestError(
                "verification receipt may not overwrite a packet artifact"
            )
        prepare_output_directory(receipt.parent)
        atomic_write(receipt, pretty_json(result))
    print(json.dumps(result, sort_keys=True))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    compile_cmd = commands.add_parser("compile", help="compile a quest packet")
    compile_cmd.add_argument("--repo-root", default=".")
    compile_cmd.add_argument("--objective", required=True)
    compile_cmd.add_argument("--acceptance", required=True)
    compile_cmd.add_argument(
        "--effect-ceiling", choices=EFFECT_CEILINGS, default="observe"
    )
    compile_cmd.add_argument("--exclusions", default="")
    compile_cmd.add_argument("--focus-path", default=".")
    compile_cmd.add_argument("--source-note", default="")
    compile_cmd.add_argument("--output-dir", default=".kingdom-quest")
    compile_cmd.set_defaults(func=command_compile)

    verify_cmd = commands.add_parser("verify", help="verify a packet directory or archive")
    verify_cmd.add_argument("path")
    verify_cmd.add_argument("--repo-root")
    verify_cmd.add_argument("--expected-repository", default="")
    verify_cmd.add_argument("--expected-ref", default="")
    verify_cmd.add_argument("--receipt")
    verify_cmd.set_defaults(func=command_verify)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return args.func(args)
    except (
        QuestError,
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        subprocess.TimeoutExpired,
        tarfile.TarError,
    ) as error:
        print(f"kingdom loom: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
