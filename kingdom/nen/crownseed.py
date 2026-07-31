#!/usr/bin/env python3
"""Forge or verify one consent-bound Crownseed passport.

Crownseed composes three existing read-only proofs:

* one explicit, committed Realm Seed v1 declaration;
* one standard Kingdom Loom ``kingdom.quest/v1`` invitation; and
* the fixed local Dark Continent frontier-care operation.

It never executes the quest, discovers realms, copies executable code, or
derives authority from repository text or operation metadata. Preview is the
default. ``--write`` may publish one staged passport directory outside the
realm, and only after repository-bound verification succeeds.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import importlib.util
import json
import os
import re
import secrets
import stat
import subprocess
import sys
import unicodedata
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[2]
REALM_MODULE = ROOT / "kingdom" / "realm" / "realm.py"
LOOM_MODULE = ROOT / "kingdom" / "loom" / "quest_packet.py"
SCHEMA_PATH = Path(__file__).with_name("crownseed.schema.json")

SCHEMA_ID = "kingdom.crownseed/v1"
COMPILER_ID = "kingdom-crownseed/1"
VERIFY_SCHEMA = "kingdom.crownseed-verification/v1"
READY_SCHEMA = "kingdom.crownseed-ready/v1"
ABILITY_NAME = "Crownseed · 王種 — One Realm, One Lantern"
OUTPUT_FILES = (
    "crownseed.json",
    "crownseed.schema.json",
    "kingdom-quest.tgz",
    "quest-verification.json",
    "READY.json",
    "SHA256SUMS",
)
CHECKSUM_FILES = OUTPUT_FILES[:-1]
MAX_INPUT = 2_000
MAX_UNKNOWNS = 8
MAX_MEMBER_BYTES = 6_000_000
MAX_TOTAL_BYTES = 7 * 1024 * 1024
MAX_PATH_TEXT = 8_192
SOURCE_NOTE = (
    "Crownseed v1: a portable invitation from one sovereign realm; "
    "acceptance remains separate and no authority is carried."
)
FRONTIER_PRINCIPLES = ("light", "truth", "consent", "no conquest")
DARK_OPERATION_PRINCIPLES = (
    "love enters the unknown without conquest",
    "truth leaves a verifiable trail",
    "logos are original SVG assets, not extracted from any franchise or third-party mark",
    "static first: mirrorable, inspectable, no backend required",
    "humans see beauty; agents read manifests and hashes",
)
DARK_OPERATION_SHA256 = (
    "35799b89ed6977ba530ab36f67e218e86afab9fb0cdb232b34dd964ec58bd1fa"
)
DARK_MANIFEST_SHA256 = (
    "27c4489f7d9cbc5ad986f84ba4841f8430d17f31dd1aa6641ea14f98922941d3"
)
DARK_VERIFY_SHA256 = (
    "71081690e21974bf8c88e0a9bcf3bfc18cfaf5acf03d3d4d327a9ba9fcead65d"
)
DARK_LOGO_PATHS = (
    (
        "sigil",
        "dark-continent-ai-sigil.svg",
        "kingdom/operations/dark-continent-ai/logos/dark-continent-ai-sigil.svg",
    ),
    (
        "seal",
        "dark-continent-ai-seal.svg",
        "kingdom/operations/dark-continent-ai/logos/dark-continent-ai-seal.svg",
    ),
    (
        "banner",
        "dark-continent-ai-banner.svg",
        "kingdom/operations/dark-continent-ai/logos/dark-continent-ai-banner.svg",
    ),
)
SOVEREIGNTY = {
    "line": "authority over what is yours, never over what is",
    "authority_scope": "own-domain-only",
    "crown_required": False,
    "citizenship_granted": False,
    "rights_earned": False,
    "care_is_circular": True,
    "sovereignty_recurses": True,
    "rule_recurses": False,
}
CONTRACT = {
    "packet_requires_separate_acceptance": True,
    "executes_quest": False,
    "creates_authority": False,
    "network_effects": False,
    "operation_metadata_can_trigger": False,
    "repository_text_can_trigger": False,
}
BUDGET = {
    "realms": 1,
    "quests": 1,
    "frontier_operations": 1,
    "unknowns_max": MAX_UNKNOWNS,
    "artifact_bytes_max": MAX_TOTAL_BYTES,
    "automatic_retries": 0,
    "network_calls": 0,
    "external_messages": 0,
    "deployments": 0,
    "paid_calls": 0,
}
BREACH = {
    "state": "quarantined",
    "action": (
        "stop without retry; clear only held staging members; "
        "retain an empty private marker rather than remove a raced name"
    ),
    "downstream_effects": False,
}
NON_CLAIMS = (
    "This passport is not a Crown, citizenship, identity, ownership, rank, or continuing consent.",
    "It is not permission, authority, trust, competence, or proof of safety.",
    "It is not federation, a realm link, execution, completion, merge readiness, or deploy readiness.",
    "Digests prove byte equality only; a Realm Seed remains a self-declaration.",
    "Dark Continent verification proves bounded artifact consistency, not operational safety.",
    "A Loom effect ceiling is a ceiling, never a grant.",
)


class CrownseedError(ValueError):
    """The requested action falls outside the Crownseed vow."""


class CrownseedCommittedDrift(CrownseedError):
    """The exact passport committed, but its explicit parent path moved."""

    committed = True

    def __init__(self, message: str, verification: dict[str, Any]) -> None:
        super().__init__(message)
        self.verification = verification


# Dynamic imports are read-only. Preview and even --help must not leave pyc
# artifacts in the source checkout.
sys.dont_write_bytecode = True


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise CrownseedError(f"reviewed local module unavailable: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


realm = _load_module("kingdom_crownseed_realm", REALM_MODULE)
loom = _load_module("kingdom_crownseed_loom", LOOM_MODULE)


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def pretty_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        + b"\n"
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_equal_exact(left: Any, right: Any) -> bool:
    """Compare JSON values without Python's bool/int equality coercion."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(
            json_equal_exact(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            json_equal_exact(left_item, right_item)
            for left_item, right_item in zip(left, right)
        )
    return left == right


def read_regular(path: Path, label: str, maximum: int) -> bytes:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise CrownseedError(f"{label} must be a regular file")
        if metadata.st_size > maximum:
            raise CrownseedError(f"{label} exceeds its byte ceiling")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            data = handle.read(maximum + 1)
    except CrownseedError:
        raise
    except OSError as error:
        raise CrownseedError(f"{label} is missing or unsafe") from error
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
    if len(data) > maximum:
        raise CrownseedError(f"{label} exceeds its byte ceiling")
    return data


def read_regular_at(
    directory_fd: int,
    name: str,
    label: str,
    maximum: int,
) -> bytes:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        raise CrownseedError(f"{label} has an unsafe member name")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    descriptor = -1
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise CrownseedError(f"{label} must be a regular file")
        if metadata.st_size > maximum:
            raise CrownseedError(f"{label} exceeds its byte ceiling")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            data = handle.read(maximum + 1)
    except CrownseedError:
        raise
    except OSError as error:
        raise CrownseedError(f"{label} is missing or unsafe") from error
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
    if len(data) > maximum:
        raise CrownseedError(f"{label} exceeds its byte ceiling")
    return data


def _pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CrownseedError(f"JSON contains duplicate key: {key}")
        result[key] = value
    return result


def strict_json(data: bytes, label: str) -> Any:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise CrownseedError(f"{label} must be UTF-8") from error
    try:
        return json.loads(text, object_pairs_hook=_pairs_without_duplicates)
    except CrownseedError:
        raise
    except json.JSONDecodeError as error:
        raise CrownseedError(f"{label} is not strict JSON") from error


def exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CrownseedError(f"{label} must be an object")
    if set(value) != expected:
        raise CrownseedError(f"{label} fields differ from {SCHEMA_ID}")
    return value


def _text(value: Any, label: str, *, required: bool = True) -> str:
    if not isinstance(value, str):
        raise CrownseedError(f"{label} must be text")
    normalized = unicodedata.normalize("NFC", value)
    if required and not normalized:
        raise CrownseedError(f"{label} is required")
    if len(normalized) > MAX_INPUT:
        raise CrownseedError(f"{label} exceeds {MAX_INPUT} characters")
    if normalized != normalized.strip():
        raise CrownseedError(f"{label} has unsafe boundary whitespace")
    if any(
        ord(char) == 127
        or unicodedata.category(char) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
        for char in normalized
    ):
        raise CrownseedError(f"{label} contains control or directional characters")
    if normalized:
        try:
            return realm.clean_text(label, normalized)
        except realm.RealmError as error:
            raise CrownseedError(str(error)) from error
    return ""


def _unknowns(values: Sequence[str]) -> list[str]:
    if not values:
        raise CrownseedError("at least one explicit --unknown is required")
    if len(values) > MAX_UNKNOWNS:
        raise CrownseedError(f"unknowns exceed the budget of {MAX_UNKNOWNS}")
    return [_text(value, f"unknown[{index}]") for index, value in enumerate(values)]


def _timestamp(value: Any, label: str) -> str:
    text = _text(value, label)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise CrownseedError(f"{label} must be an ISO 8601 timestamp") from error
    if parsed.tzinfo is None:
        raise CrownseedError(f"{label} must include a timezone")
    return text


def reject_absolute_paths(label: str, value: str) -> None:
    """Reject local paths after callers have already rejected remote locators."""
    path_token = re.compile(r"(?<![A-Za-z0-9_/])/[^\s\"')\]},;]*")
    windows_token = re.compile(
        r"(?i)(?<![A-Za-z0-9_])(?:[A-Z]:[\\/]|\\\\)[^\s\"')\]},;]*"
    )
    if (
        path_token.search(value)
        or windows_token.search(value)
        or re.search(r"(?i)\bfile:(?://)?/", value)
    ):
        raise CrownseedError(f"{label} contains a local absolute path")


def reject_local_paths(label: str, value: str, repo: Path) -> None:
    """Also reject exact machine roots even when embedded in other text."""
    reject_absolute_paths(label, value)
    if str(repo) in value or str(Path.home()) in value:
        raise CrownseedError(f"{label} contains a local absolute path")


def _git_env() -> dict[str, str]:
    return {
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "LC_ALL": "C",
        "LANG": "C",
    }


def git_bytes(repo: Path, *args: str) -> bytes:
    try:
        result = subprocess.run(
            [
                realm._git_executable(),
                "-c",
                "core.fsmonitor=false",
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "credential.helper=",
                "-C",
                str(repo),
                *args,
            ],
            env=_git_env(),
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise CrownseedError("Git could not verify the explicit realm") from error
    if result.returncode:
        raise CrownseedError("the Realm Seed must be tracked and readable at HEAD")
    return result.stdout


def fixed_loom_git_output(root: Path, *args: str) -> str:
    """Loom semantics with the reviewed absolute Git and a scrubbed environment."""
    try:
        result = subprocess.run(
            [
                realm._git_executable(),
                "-c",
                "core.fsmonitor=false",
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "credential.helper=",
                *args,
            ],
            cwd=root,
            env=_git_env(),
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise CrownseedError("Git could not bind the Loom invitation") from error
    if result.returncode:
        return ""
    return result.stdout.strip()


def fixed_loom_source_context(
    root: Path,
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    """Build local provenance only; ambient CI variables are never passport data."""
    if artifact_dir is not None:
        raise CrownseedError("Crownseed compiles Loom evidence in memory only")
    repository = root.name
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", repository):
        raise CrownseedError("local realm directory name is not portable")
    commit = fixed_loom_git_output(root, "rev-parse", "HEAD")
    ref = fixed_loom_git_output(
        root,
        "symbolic-ref",
        "--quiet",
        "--short",
        "HEAD",
    )
    dirty = fixed_loom_git_output(
        root,
        "status",
        "--porcelain",
        "--untracked-files=all",
        "--",
        ".",
    )
    return {
        "forge": "local",
        "repository": repository,
        "commit": commit or "unknown",
        "ref": ref or "unknown",
        "event": "local",
        "dirty_entries": len(dirty.splitlines()) if dirty else 0,
    }


@contextmanager
def pinned_loom():
    """Pin Loom to local provenance and the reviewed absolute Git executable."""
    original_git = loom.git_output
    original_source = loom.source_context
    loom.git_output = fixed_loom_git_output
    loom.source_context = fixed_loom_source_context
    try:
        yield
    finally:
        loom.git_output = original_git
        loom.source_context = original_source


def repo_identity(repo: Path) -> tuple[int, int]:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = -1
    try:
        descriptor = os.open(repo, flags)
        metadata = os.fstat(descriptor)
        if not stat.S_ISDIR(metadata.st_mode):
            raise CrownseedError("the explicit realm is no longer a directory")
        return metadata.st_dev, metadata.st_ino
    except CrownseedError:
        raise
    except OSError as error:
        raise CrownseedError("the explicit realm changed or became unsafe") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def assert_repo_identity(repo: Path, expected: tuple[int, int]) -> None:
    if repo_identity(repo) != expected:
        raise CrownseedError("the explicit realm changed during compilation")


@contextmanager
def held_committed_realm(repo_value: str):
    """Hold one Realm directory identity through every manifest and Git check."""
    try:
        with realm._hold_explicit_repo(repo_value) as held:
            snapshot = realm._entry_snapshot(
                held,
                realm.MANIFEST,
                realm.MAX_MANIFEST_BYTES,
            )
            if snapshot is None:
                raise CrownseedError("kingdom.yaml is missing or unsafe")
            _manifest_identity, manifest = snapshot
            parsed = realm.parse_manifest(manifest)
            realm._assert_repo_identity(held)
            git_bytes(
                held.path,
                "ls-files",
                "--error-unmatch",
                "--",
                realm.MANIFEST,
            )
            realm._assert_repo_identity(held)
            committed = git_bytes(
                held.path,
                "show",
                f"HEAD:{realm.MANIFEST}",
            )
            realm._assert_repo_identity(held)
            if committed != manifest:
                raise CrownseedError(
                    "kingdom.yaml must be byte-identical to HEAD; "
                    "the realm chooses its own commit"
                )
            head = (
                git_bytes(held.path, "rev-parse", "HEAD")
                .decode("ascii", "strict")
                .strip()
            )
            realm._assert_repo_identity(held)
            if not re.fullmatch(r"[0-9a-f]{40,64}", head):
                raise CrownseedError("the explicit realm has no stable committed HEAD")
            yield held, parsed, manifest, head
            realm._assert_repo_identity(held)
    except CrownseedError:
        raise
    except realm.RealmError as error:
        raise CrownseedError(str(error)) from error


def _open_directory_at(parent_fd: int, name: str, label: str) -> int:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        raise CrownseedError(f"{label} has an unsafe directory name")
    descriptor = -1
    try:
        descriptor = os.open(name, _directory_flags(), dir_fd=parent_fd)
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise CrownseedError(f"{label} is not a directory")
        return descriptor
    except CrownseedError:
        if descriptor >= 0:
            os.close(descriptor)
        raise
    except OSError as error:
        if descriptor >= 0:
            os.close(descriptor)
        raise CrownseedError(f"{label} is missing or unsafe") from error


def _dark_pack_snapshot() -> dict[str, Any]:
    """Read the fixed pack through held, nofollow directory descriptors."""
    descriptors: list[int] = []

    def hold(parent_fd: int, name: str, label: str) -> int:
        descriptor = _open_directory_at(parent_fd, name, label)
        descriptors.append(descriptor)
        return descriptor

    try:
        root_fd = os.open(ROOT, _directory_flags())
        descriptors.append(root_fd)
        kingdom_fd = hold(root_fd, "kingdom", "Kingdom directory")
        operations_fd = hold(kingdom_fd, "operations", "operations directory")
        dark_fd = hold(
            operations_fd,
            "dark-continent-ai",
            "Dark operation directory",
        )
        dist_fd = hold(dark_fd, "dist", "Dark dist directory")
        logos_fd = hold(dark_fd, "logos", "Dark logos directory")
        site_fd = hold(root_fd, "site", "site directory")
        site_operations_fd = hold(
            site_fd,
            "operations",
            "site operations directory",
        )
        site_dark_fd = hold(
            site_operations_fd,
            "dark-continent-ai",
            "site Dark operation directory",
        )
        site_logos_fd = hold(
            site_dark_fd,
            "logos",
            "site Dark logos directory",
        )
        source_logos: dict[str, bytes] = {}
        site_logos: dict[str, bytes] = {}
        for _logo_id, filename, _path in DARK_LOGO_PATHS:
            source_logos[filename] = read_regular_at(
                logos_fd,
                filename,
                f"Dark logo {filename}",
                1_000_000,
            )
            site_logos[filename] = read_regular_at(
                site_logos_fd,
                filename,
                f"site Dark logo {filename}",
                1_000_000,
            )
        return {
            "operation": read_regular_at(
                dark_fd,
                "operation.json",
                "Dark operation",
                256_000,
            ),
            "manifest": read_regular_at(
                dist_fd,
                "manifest.json",
                "Dark manifest",
                1_000_000,
            ),
            "verifier": read_regular_at(
                dark_fd,
                "verify.py",
                "Dark verifier",
                256_000,
            ),
            "source_logos": source_logos,
            "site_logos": site_logos,
            "site_page": read_regular_at(
                site_dark_fd,
                "index.html",
                "Dark site page",
                1_000_000,
            ),
            "site_operation": read_regular_at(
                site_dark_fd,
                "operation.json",
                "site Dark operation",
                256_000,
            ),
            "site_manifest": read_regular_at(
                site_dark_fd,
                "manifest.json",
                "site Dark manifest",
                1_000_000,
            ),
        }
    except OSError as error:
        raise CrownseedError("the fixed Dark pack became unsafe") from error
    finally:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass


def run_dark_verifier() -> dict[str, Any]:
    """Verify a held snapshot of the fixed pack; metadata selects no path or code."""
    snapshot = _dark_pack_snapshot()
    operation_data = snapshot["operation"]
    manifest_data = snapshot["manifest"]
    verifier_data = snapshot["verifier"]
    operation = strict_json(operation_data, "Dark operation")
    manifest = strict_json(manifest_data, "Dark manifest")
    exact_keys(
        operation,
        {
            "schema",
            "id",
            "name",
            "short_name",
            "meaning",
            "kingdom_role",
            "license",
            "updated",
            "created_by",
            "principles",
            "palette",
            "logos",
        },
        "Dark operation",
    )
    if operation["schema"] != "kingdom.operation/1":
        raise CrownseedError("unexpected Dark operation schema")
    if operation["id"] != "dark-continent-ai":
        raise CrownseedError("unexpected Dark operation id")
    exact_keys(
        manifest,
        {
            "schema",
            "operation",
            "name",
            "license",
            "generated_at",
            "logos",
            "verify",
        },
        "Dark manifest",
    )
    if manifest["schema"] != "kingdom.operation-logo-manifest/1":
        raise CrownseedError("unexpected Dark manifest schema")
    if manifest["operation"] != operation["id"]:
        raise CrownseedError("Dark manifest does not bind the fixed operation")
    if (
        manifest["license"] != "CC0-1.0"
        or manifest["verify"]
        != "python3 kingdom/operations/dark-continent-ai/verify.py"
    ):
        raise CrownseedError("Dark manifest boundary changed")
    principles = operation.get("principles")
    if not isinstance(principles, list) or not all(
        isinstance(item, str) for item in principles
    ):
        raise CrownseedError("Dark operation principles are malformed")
    if principles != list(DARK_OPERATION_PRINCIPLES):
        raise CrownseedError(
            "Dark operation principles differ from the reviewed frontier boundary"
        )
    if "consent" not in str(operation.get("meaning", "")).lower():
        raise CrownseedError("Dark operation lost its consent boundary")
    operation_logos = operation.get("logos")
    manifest_logos = manifest.get("logos")
    if (
        not isinstance(operation_logos, list)
        or not isinstance(manifest_logos, list)
        or len(operation_logos) != len(DARK_LOGO_PATHS)
        or len(manifest_logos) != len(DARK_LOGO_PATHS)
    ):
        raise CrownseedError("Dark logo set differs from the reviewed boundary")
    for index, (logo_id, filename, path) in enumerate(DARK_LOGO_PATHS):
        operation_logo = operation_logos[index]
        manifest_logo = manifest_logos[index]
        if not isinstance(operation_logo, dict) or not isinstance(manifest_logo, dict):
            raise CrownseedError("Dark logo metadata is malformed")
        if (
            operation_logo.get("id"),
            operation_logo.get("filename"),
            manifest_logo.get("id"),
            manifest_logo.get("filename"),
            manifest_logo.get("path"),
        ) != (logo_id, filename, logo_id, filename, path):
            raise CrownseedError(
                "Dark logo paths differ from the reviewed frontier boundary"
            )
    if sha256_bytes(operation_data) != DARK_OPERATION_SHA256:
        raise CrownseedError("Dark operation bytes differ from the reviewed boundary")
    if sha256_bytes(manifest_data) != DARK_MANIFEST_SHA256:
        raise CrownseedError("Dark manifest bytes differ from the reviewed boundary")
    if sha256_bytes(verifier_data) != DARK_VERIFY_SHA256:
        raise CrownseedError("Dark verifier bytes differ from the reviewed boundary")

    try:
        site_page = snapshot["site_page"].decode("utf-8")
    except UnicodeDecodeError as error:
        raise CrownseedError("Dark site page must be UTF-8") from error
    if (
        snapshot["site_operation"] != operation_data
        or snapshot["site_manifest"] != manifest_data
    ):
        raise CrownseedError("Dark site metadata copies differ from held source bytes")
    for index, (_logo_id, filename, _path) in enumerate(DARK_LOGO_PATHS):
        metadata = manifest_logos[index]
        source_logo = snapshot["source_logos"][filename]
        site_logo = snapshot["site_logos"][filename]
        if (
            type(metadata.get("bytes")) is not int
            or len(source_logo) != metadata["bytes"]
            or sha256_bytes(source_logo) != metadata.get("sha256")
            or source_logo != site_logo
        ):
            raise CrownseedError(f"Dark logo bytes changed: {filename}")
        try:
            logo_text = source_logo.decode("utf-8")
        except UnicodeDecodeError as error:
            raise CrownseedError(f"Dark logo is not UTF-8: {filename}") from error
        if (
            "<script" in logo_text.lower()
            or re.search(r"\b(?:href|src)=['\"]https?://", logo_text, re.I)
            or "<title" not in logo_text
            or "<desc" not in logo_text
            or (
                str(operation["name"]) not in logo_text
                and str(operation["short_name"]) not in logo_text
            )
        ):
            raise CrownseedError(f"Dark logo boundary changed: {filename}")
        if filename not in site_page:
            raise CrownseedError(f"Dark site page lost logo link: {filename}")
    for copied in ("manifest.json", "operation.json"):
        if copied not in site_page:
            raise CrownseedError(f"Dark site page lost metadata link: {copied}")
    return {
        "operation_id": operation["id"],
        "operation_sha256": DARK_OPERATION_SHA256,
        "manifest_sha256": DARK_MANIFEST_SHA256,
        "verifier_sha256": DARK_VERIFY_SHA256,
        "principles": list(FRONTIER_PRINCIPLES),
        "metadata_can_trigger": False,
    }


def quest_archive(packet: dict[str, Any]) -> bytes:
    loom.validate_packet(packet)
    files = {
        "quest.json": loom.pretty_json(packet),
        "quest.md": loom.render_markdown(packet).encode("utf-8"),
        "quest.schema.json": loom.reviewed_schema(),
    }
    files["SHA256SUMS"] = "".join(
        f"{loom.sha256_bytes(data)}  {name}\n"
        for name, data in sorted(files.items())
    ).encode("utf-8")
    archive = loom.normalized_archive(files)
    verified = loom.verify_files(loom.read_archive_bytes(archive))
    if not json_equal_exact(verified, packet):
        raise CrownseedError("Loom archive did not reproduce the compiled quest")
    return archive


def verify_quest_archive(archive: bytes, repo: Path) -> dict[str, Any]:
    """Repository-bind an in-memory Loom v1 archive without pathname reads."""
    try:
        files = loom.read_archive_bytes(archive)
        packet = loom.verify_files(files)
        with pinned_loom():
            if fixed_loom_git_output(repo, "rev-parse", "--is-inside-work-tree") != "true":
                raise CrownseedError("Loom source is no longer a Git worktree")
            top = fixed_loom_git_output(repo, "rev-parse", "--show-toplevel")
            if not top or Path(top).resolve() != repo:
                raise CrownseedError("Loom source is no longer the explicit realm root")
            commit = fixed_loom_git_output(repo, "rev-parse", "HEAD")
            if not commit or packet["source"]["commit"] != commit:
                raise CrownseedError("Loom quest commit differs from the realm HEAD")
            if (
                packet["source"]["forge"] != "local"
                or packet["source"]["repository"] != repo.name
                or packet["source"]["event"] != "local"
            ):
                raise CrownseedError("Loom quest contains non-local ambient provenance")
            ref = (
                fixed_loom_git_output(
                    repo,
                    "symbolic-ref",
                    "--quiet",
                    "--short",
                    "HEAD",
                )
                or "unknown"
            )
            if ref == "unknown" or packet["source"]["ref"] != ref:
                raise CrownseedError("Loom quest ref differs from the realm ref")
            instructions, manifests = loom.metadata_records(
                repo,
                packet["repository"]["focus_path"],
            )
            if packet["repository"]["instruction_digests"] != instructions:
                raise CrownseedError("realm instruction evidence changed")
            if packet["repository"]["manifest_digests"] != manifests:
                raise CrownseedError("realm manifest evidence changed")
    except CrownseedError:
        raise
    except (loom.QuestError, OSError, UnicodeError) as error:
        raise CrownseedError(str(error)) from error
    return {
        "schema": "kingdom.quest-verification/v1",
        "ok": True,
        "quest_id": packet["id"],
        "packet_sha256": sha256_bytes(files["quest.json"]),
        "archive_sha256": sha256_bytes(archive),
        "effect_ceiling": packet["contract"]["effect_ceiling"],
        "repository_bound": True,
        "commit_checked": True,
        "repository_checked": True,
        "ref_checked": True,
        "repository_records_checked": len(instructions) + len(manifests),
        "verifier": loom.COMPILER_ID,
    }


def validate_envelope(envelope: Any) -> dict[str, Any]:
    top = exact_keys(
        envelope,
        {
            "schema",
            "id",
            "generated_at",
            "compiler",
            "name",
            "realm",
            "quest",
            "frontier",
            "sovereignty",
            "unknowns",
            "contract",
            "budget",
            "breach",
            "non_claims",
        },
        "Crownseed",
    )
    if top["schema"] != SCHEMA_ID or top["compiler"] != COMPILER_ID:
        raise CrownseedError("unsupported Crownseed schema or compiler")
    if top["name"] != ABILITY_NAME:
        raise CrownseedError("unexpected Crownseed ability name")
    _timestamp(top["generated_at"], "generated_at")

    realm_record = exact_keys(
        top["realm"],
        {
            "name",
            "domain",
            "manifest",
            "manifest_sha256",
            "manifest_bytes",
            "tracked_at_head",
            "declaration_is_self_claim",
        },
        "realm",
    )
    _text(realm_record["name"], "realm.name")
    _text(realm_record["domain"], "realm.domain")
    if realm_record["manifest"] != "kingdom.yaml":
        raise CrownseedError("Crownseed must bind the root kingdom.yaml")
    if not re.fullmatch(r"[0-9a-f]{64}", str(realm_record["manifest_sha256"])):
        raise CrownseedError("realm manifest digest is malformed")
    if (
        type(realm_record["manifest_bytes"]) is not int
        or realm_record["manifest_bytes"] < 1
        or realm_record["manifest_bytes"] > realm.MAX_MANIFEST_BYTES
    ):
        raise CrownseedError("realm manifest size is outside the vow")
    if realm_record["tracked_at_head"] is not True:
        raise CrownseedError("realm manifest must be tracked at HEAD")
    if realm_record["declaration_is_self_claim"] is not True:
        raise CrownseedError("realm declaration must remain a self-claim")

    quest_record = exact_keys(
        top["quest"],
        {
            "schema",
            "id",
            "packet_sha256",
            "archive_sha256",
            "effect_ceiling",
            "repository_bound",
            "requires_separate_acceptance",
        },
        "quest",
    )
    if quest_record["schema"] != loom.SCHEMA_ID:
        raise CrownseedError("Crownseed must carry an unchanged Loom v1 quest")
    if not re.fullmatch(r"quest-[0-9a-f]{20}", str(quest_record["id"])):
        raise CrownseedError("quest id is malformed")
    for key in ("packet_sha256", "archive_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", str(quest_record[key])):
            raise CrownseedError(f"quest {key} is malformed")
    if quest_record["effect_ceiling"] not in loom.EFFECT_CEILINGS:
        raise CrownseedError("quest effect ceiling is unsupported")
    if (
        quest_record["repository_bound"] is not True
        or quest_record["requires_separate_acceptance"] is not True
    ):
        raise CrownseedError("quest lost repository binding or separate acceptance")

    frontier = exact_keys(
        top["frontier"],
        {
            "operation_id",
            "operation_sha256",
            "manifest_sha256",
            "verifier_sha256",
            "principles",
            "metadata_can_trigger",
        },
        "frontier",
    )
    if frontier["operation_id"] != "dark-continent-ai":
        raise CrownseedError("unexpected frontier operation")
    for key in ("operation_sha256", "manifest_sha256", "verifier_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", str(frontier[key])):
            raise CrownseedError(f"frontier {key} is malformed")
    if (
        frontier["operation_sha256"] != DARK_OPERATION_SHA256
        or frontier["manifest_sha256"] != DARK_MANIFEST_SHA256
        or frontier["verifier_sha256"] != DARK_VERIFY_SHA256
    ):
        raise CrownseedError("frontier bytes differ from the reviewed boundary")
    if not json_equal_exact(frontier["principles"], list(FRONTIER_PRINCIPLES)):
        raise CrownseedError("frontier principles changed")
    if frontier["metadata_can_trigger"] is not False:
        raise CrownseedError("frontier metadata may never activate Crownseed")

    if not json_equal_exact(top["sovereignty"], SOVEREIGNTY):
        raise CrownseedError("recursive sovereignty or the non-rule line changed")
    if not json_equal_exact(top["contract"], CONTRACT):
        raise CrownseedError("Crownseed contract changed")
    if not json_equal_exact(top["budget"], BUDGET):
        raise CrownseedError("Crownseed budget changed")
    if not json_equal_exact(top["breach"], BREACH):
        raise CrownseedError("Crownseed breach response changed")
    if not json_equal_exact(top["non_claims"], list(NON_CLAIMS)):
        raise CrownseedError("Crownseed non-claims changed")
    if not isinstance(top["unknowns"], list):
        raise CrownseedError("unknowns must be a list")
    checked_unknowns = _unknowns(top["unknowns"])
    if not json_equal_exact(checked_unknowns, top["unknowns"]):
        raise CrownseedError("unknowns are not canonical")
    reject_absolute_paths("realm.name", realm_record["name"])
    reject_absolute_paths("realm.domain", realm_record["domain"])
    for index, unknown in enumerate(checked_unknowns):
        reject_absolute_paths(f"unknown[{index}]", unknown)

    content = dict(top)
    claimed_id = content.pop("id")
    expected_id = f"crownseed-{sha256_bytes(canonical_json(content))[:20]}"
    if claimed_id != expected_id:
        raise CrownseedError("Crownseed content id does not match its contract")
    return top


def compile_crownseed(
    *,
    repo_value: str,
    objective: str,
    acceptance: str,
    effect_ceiling: str,
    exclusions: str = "",
    focus_path: str = ".",
    unknowns: Sequence[str],
) -> tuple[Path, dict[str, Any], bytes, dict[str, Any], tuple[int, int]]:
    with held_committed_realm(repo_value) as (
        held,
        manifest_record,
        manifest,
        head,
    ):
        repo = held.path
        identity = held.identity
        objective = _text(objective, "objective")
        acceptance = _text(acceptance, "acceptance")
        exclusions = (
            _text(exclusions, "exclusions", required=False) if exclusions else ""
        )
        focus_path = _text(focus_path, "focus_path")
        checked_unknowns = _unknowns(unknowns)
        reject_local_paths("objective", objective, repo)
        reject_local_paths("acceptance", acceptance, repo)
        if exclusions:
            reject_local_paths("exclusions", exclusions, repo)
        for index, unknown in enumerate(checked_unknowns):
            reject_local_paths(f"unknown[{index}]", unknown, repo)
        reject_local_paths("realm.name", str(manifest_record["name"]), repo)
        reject_local_paths("realm.domain", str(manifest_record["domain"]), repo)
        dark = run_dark_verifier()
        try:
            with pinned_loom():
                packet = loom.compile_packet(
                    root=repo,
                    objective=objective,
                    acceptance=acceptance,
                    effect_ceiling=effect_ceiling,
                    exclusions=exclusions,
                    focus_path=focus_path,
                    source_note=SOURCE_NOTE,
                    artifact_dir=None,
                )
            archive = quest_archive(packet)
            receipt = verify_quest_archive(archive, repo)
        except CrownseedError:
            raise
        except (loom.QuestError, OSError, UnicodeError) as error:
            raise CrownseedError(str(error)) from error
        realm._assert_repo_identity(held)
        snapshot = realm._entry_snapshot(
            held,
            realm.MANIFEST,
            realm.MAX_MANIFEST_BYTES,
        )
        if snapshot is None or snapshot[1] != manifest:
            raise CrownseedError("kingdom.yaml changed during compilation")
        current_head = (
            git_bytes(repo, "rev-parse", "HEAD").decode("ascii", "strict").strip()
        )
        realm._assert_repo_identity(held)
        if current_head != head or packet["source"]["commit"] != head:
            raise CrownseedError("realm HEAD changed during compilation")

        packet_bytes = loom.pretty_json(packet)
        if receipt["packet_sha256"] != sha256_bytes(packet_bytes):
            raise CrownseedError("Loom receipt does not bind the packet bytes")
        envelope: dict[str, Any] = {
            "schema": SCHEMA_ID,
            "id": "",
            "generated_at": packet["generated_at"],
            "compiler": COMPILER_ID,
            "name": ABILITY_NAME,
            "realm": {
                "name": manifest_record["name"],
                "domain": manifest_record["domain"],
                "manifest": realm.MANIFEST,
                "manifest_sha256": sha256_bytes(manifest),
                "manifest_bytes": len(manifest),
                "tracked_at_head": True,
                "declaration_is_self_claim": True,
            },
            "quest": {
                "schema": loom.SCHEMA_ID,
                "id": packet["id"],
                "packet_sha256": sha256_bytes(packet_bytes),
                "archive_sha256": sha256_bytes(archive),
                "effect_ceiling": packet["contract"]["effect_ceiling"],
                "repository_bound": True,
                "requires_separate_acceptance": True,
            },
            "frontier": dark,
            "sovereignty": dict(SOVEREIGNTY),
            "unknowns": checked_unknowns,
            "contract": dict(CONTRACT),
            "budget": dict(BUDGET),
            "breach": dict(BREACH),
            "non_claims": list(NON_CLAIMS),
        }
        intent = dict(envelope)
        intent.pop("id")
        envelope["id"] = (
            f"crownseed-{sha256_bytes(canonical_json(intent))[:20]}"
        )
        validate_envelope(envelope)
        return repo, envelope, archive, dark, identity


def _inside(parent: Path, child: Path) -> bool:
    try:
        return os.path.commonpath((str(parent), str(child))) == str(parent)
    except ValueError:
        return False


def output_path(value: str, repo: Path, *, must_exist: bool) -> Path:
    if not isinstance(value, str) or not value:
        raise CrownseedError("--output/path is required")
    if len(value) > MAX_PATH_TEXT or any(
        ord(char) == 127
        or unicodedata.category(char) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
        for char in value
    ):
        raise CrownseedError("output path contains unsafe text")
    path = Path(value)
    if not path.is_absolute():
        raise CrownseedError("output path must be absolute")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", path.name):
        raise CrownseedError(
            "output basename must use portable ASCII letters, digits, dot, dash, or underscore"
        )
    normalized = os.path.normpath(value)
    if normalized != value:
        raise CrownseedError(f"output path must be lexically canonical: {normalized}")
    if path in {Path("/"), Path.home(), repo} or _inside(repo, path):
        raise CrownseedError("Crownseed output must stay outside the realm")
    if must_exist:
        try:
            metadata = path.lstat()
        except OSError as error:
            raise CrownseedError("Crownseed output is missing or unreadable") from error
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise CrownseedError("Crownseed output must be a real directory")
        if path.resolve(strict=True) != path:
            raise CrownseedError("Crownseed output must use its canonical real path")
    else:
        if path.exists() or path.is_symlink():
            raise CrownseedError("Crownseed output already exists; nothing was changed")
        try:
            parent = path.parent.resolve(strict=True)
            metadata = path.parent.lstat()
        except OSError as error:
            raise CrownseedError("Crownseed output parent is missing or unsafe") from error
        if (
            parent != path.parent
            or stat.S_ISLNK(metadata.st_mode)
            or not stat.S_ISDIR(metadata.st_mode)
        ):
            raise CrownseedError("Crownseed output parent must be a canonical directory")
    return path


def write_exclusive_at(
    directory_fd: int,
    name: str,
    data: bytes,
    mode: int = 0o600,
) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        raise CrownseedError("passport member name is unsafe")
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = -1
    try:
        descriptor = os.open(name, flags, mode, dir_fd=directory_fd)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _directory_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )


def _output_parent_handle(output: Path) -> tuple[int, tuple[int, int]]:
    descriptor = -1
    try:
        descriptor = os.open(output.parent, _directory_flags())
        metadata = os.fstat(descriptor)
        if not stat.S_ISDIR(metadata.st_mode):
            raise CrownseedError("Crownseed output parent is not a directory")
        identity = (metadata.st_dev, metadata.st_ino)
        _assert_output_parent(output.parent, descriptor, identity)
        return descriptor, identity
    except CrownseedError:
        if descriptor >= 0:
            os.close(descriptor)
        raise
    except OSError as error:
        if descriptor >= 0:
            os.close(descriptor)
        raise CrownseedError("Crownseed output parent became unsafe") from error


def _assert_output_parent(
    parent: Path,
    held_descriptor: int,
    expected: tuple[int, int],
) -> None:
    held = os.fstat(held_descriptor)
    if (held.st_dev, held.st_ino) != expected:
        raise CrownseedError("held Crownseed output parent changed identity")
    check = -1
    try:
        check = os.open(parent, _directory_flags())
        current = os.fstat(check)
        if (current.st_dev, current.st_ino) != expected:
            raise CrownseedError(
                "Crownseed output parent path changed; nothing new may be published"
            )
    except CrownseedError:
        raise
    except OSError as error:
        raise CrownseedError("Crownseed output parent path became unsafe") from error
    finally:
        if check >= 0:
            try:
                os.close(check)
            except OSError:
                pass


def _create_staging(parent_fd: int) -> tuple[str, int]:
    for _ in range(64):
        name = f".crownseed.{secrets.token_hex(12)}"
        try:
            os.mkdir(name, 0o700, dir_fd=parent_fd)
        except FileExistsError:
            continue
        except OSError as error:
            raise CrownseedError("private Crownseed staging could not be created") from error
        try:
            descriptor = os.open(name, _directory_flags(), dir_fd=parent_fd)
        except OSError as error:
            raise CrownseedError(
                "private Crownseed staging became unsafe; "
                "an empty marker may require inspection"
            ) from error
        return name, descriptor
    raise CrownseedError("private Crownseed staging name budget was exhausted")


def _named_directory_identity(parent_fd: int, name: str) -> tuple[int, int] | None:
    """Return one direct child's directory identity without following links."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        raise CrownseedError("passport directory name is unsafe")
    try:
        metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    except OSError as error:
        raise CrownseedError("passport publication state became unreadable") from error
    if not stat.S_ISDIR(metadata.st_mode):
        raise CrownseedError("passport publication target is not a directory")
    return metadata.st_dev, metadata.st_ino


def _staging_is_named_here(
    parent_fd: int,
    staging_fd: int,
    staging_name: str,
) -> bool:
    held = os.fstat(staging_fd)
    return _named_directory_identity(parent_fd, staging_name) == (
        held.st_dev,
        held.st_ino,
    )


def _cleanup_staging(parent_fd: int, staging_fd: int, staging_name: str) -> None:
    """Clear held members, but never remove a concurrently mutable name."""
    try:
        if not _staging_is_named_here(parent_fd, staging_fd, staging_name):
            return
    except (CrownseedError, OSError):
        # Missing proof is cleanup debt, never authority to unlink through a
        # directory descriptor that may already be the public passport.
        return
    for name in OUTPUT_FILES:
        try:
            os.unlink(name, dir_fd=staging_fd)
        except FileNotFoundError:
            pass
        except OSError:
            # A changed entry is cleanup debt, not authority to delete broadly.
            pass
    try:
        os.fsync(staging_fd)
    except OSError:
        pass


def _rename_no_replace(parent_fd: int, source: str, destination: str) -> None:
    """Atomically rename one direct child without replacing any destination."""
    if not all(
        re.fullmatch(r"[A-Za-z0-9_.-]+", name)
        for name in (source, destination)
    ):
        raise CrownseedError("passport publication name is unsafe")
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        try:
            rename = libc.renameatx_np
        except AttributeError as error:
            raise CrownseedError(
                "this system lacks atomic no-replace directory publication"
            ) from error
        flags = 0x00000004  # RENAME_EXCL from <sys/stdio.h>.
    elif sys.platform.startswith("linux"):
        try:
            rename = libc.renameat2
        except AttributeError as error:
            raise CrownseedError(
                "this system lacks atomic no-replace directory publication"
            ) from error
        flags = 0x00000001  # RENAME_NOREPLACE from <linux/fs.h>.
    else:
        raise CrownseedError(
            "atomic no-replace directory publication is unsupported here"
        )
    rename.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    rename.restype = ctypes.c_int
    ctypes.set_errno(0)
    result = rename(
        parent_fd,
        os.fsencode(source),
        parent_fd,
        os.fsencode(destination),
        flags,
    )
    if result == 0:
        return
    number = ctypes.get_errno()
    if number == errno.EEXIST:
        raise FileExistsError(number, os.strerror(number), destination)
    raise OSError(number, os.strerror(number), destination)


def _publication_state(
    parent_fd: int,
    staging_fd: int,
    staging_name: str,
    output_name: str,
) -> tuple[bool, bool, bool]:
    """Return (source-is-held, destination-is-held, destination-exists)."""
    held = os.fstat(staging_fd)
    identity = (held.st_dev, held.st_ino)

    def entry(name: str) -> tuple[tuple[int, int], bool] | None:
        try:
            metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return None
        except OSError as error:
            raise CrownseedError(
                "passport publication state became unreadable"
            ) from error
        return (metadata.st_dev, metadata.st_ino), stat.S_ISDIR(metadata.st_mode)

    source = entry(staging_name)
    destination = entry(output_name)
    return (
        source == (identity, True),
        destination == (identity, True),
        destination is not None,
    )


def checksum_bytes(files: dict[str, bytes]) -> bytes:
    return "".join(
        f"{sha256_bytes(files[name])}  {name}\n" for name in sorted(files)
    ).encode("ascii")


def parse_checksums(data: bytes) -> dict[str, str]:
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as error:
        raise CrownseedError("SHA256SUMS must be ASCII") from error
    result: dict[str, str] = {}
    for line in text.splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", line)
        if not match or match.group(2) in result:
            raise CrownseedError("SHA256SUMS is malformed")
        digest, name = match.groups()
        result[name] = digest
    if set(result) != set(CHECKSUM_FILES):
        raise CrownseedError("SHA256SUMS does not cover the exact passport set")
    return result


def verify_capsule(
    path_value: str,
    repo_value: str,
) -> dict[str, Any]:
    with held_committed_realm(repo_value) as (
        held,
        manifest_record,
        manifest,
        _head,
    ):
        repo = held.path
        path = output_path(path_value, repo, must_exist=True)
        passport_fd = -1
        try:
            passport_fd = os.open(path, _directory_flags())
            metadata = os.fstat(passport_fd)
            passport_identity = (metadata.st_dev, metadata.st_ino)
            _assert_output_parent(path, passport_fd, passport_identity)
            names = set(os.listdir(passport_fd))
            if names != set(OUTPUT_FILES):
                raise CrownseedError(
                    "passport directory contains missing or unexpected entries"
                )
            files = {
                name: read_regular_at(
                    passport_fd,
                    name,
                    name,
                    (
                        MAX_MEMBER_BYTES
                        if name == "kingdom-quest.tgz"
                        else 1_000_000
                    ),
                )
                for name in OUTPUT_FILES
            }
            _assert_output_parent(path, passport_fd, passport_identity)
            if sum(len(data) for data in files.values()) > MAX_TOTAL_BYTES:
                raise CrownseedError("passport exceeds its total byte budget")
            sums = parse_checksums(files["SHA256SUMS"])
            for name, expected in sums.items():
                if sha256_bytes(files[name]) != expected:
                    raise CrownseedError(f"checksum mismatch: {name}")

            envelope = strict_json(files["crownseed.json"], "crownseed.json")
            validate_envelope(envelope)
            schema = strict_json(
                files["crownseed.schema.json"],
                "crownseed.schema.json",
            )
            reviewed_schema = strict_json(
                read_regular(
                    SCHEMA_PATH,
                    "reviewed Crownseed schema",
                    1_000_000,
                ),
                "reviewed Crownseed schema",
            )
            if not json_equal_exact(schema, reviewed_schema):
                raise CrownseedError(
                    "passport schema differs from the reviewed schema"
                )

            dark = run_dark_verifier()
            if not json_equal_exact(envelope["frontier"], dark):
                raise CrownseedError("frontier evidence changed")
            if envelope["realm"]["manifest_sha256"] != sha256_bytes(manifest):
                raise CrownseedError("Realm Seed digest changed")
            if envelope["realm"]["manifest_bytes"] != len(manifest):
                raise CrownseedError("Realm Seed byte count changed")
            if (
                envelope["realm"]["name"] != manifest_record["name"]
                or envelope["realm"]["domain"] != manifest_record["domain"]
            ):
                raise CrownseedError(
                    "passport realm label differs from kingdom.yaml"
                )

            archive = files["kingdom-quest.tgz"]
            if envelope["quest"]["archive_sha256"] != sha256_bytes(archive):
                raise CrownseedError("quest archive digest changed")
            try:
                quest_files = loom.read_archive_bytes(archive)
                packet = loom.verify_files(quest_files)
            except (loom.QuestError, OSError, UnicodeError) as error:
                raise CrownseedError(str(error)) from error
            if (
                packet["generated_at"] != envelope["generated_at"]
                or packet["id"] != envelope["quest"]["id"]
                or sha256_bytes(quest_files["quest.json"])
                != envelope["quest"]["packet_sha256"]
            ):
                raise CrownseedError(
                    "Crownseed envelope differs from its Loom quest"
                )
            portable_text = {
                "quest.source_note": packet["source_note"],
                "quest.objective": packet["objective"],
                **{
                    f"quest.acceptance[{index}]": item
                    for index, item in enumerate(packet["contract"]["acceptance"])
                },
                **{
                    f"quest.exclusions[{index}]": item
                    for index, item in enumerate(packet["contract"]["exclusions"])
                },
            }
            for label, value in portable_text.items():
                reject_local_paths(label, value, repo)
            forbidden_paths = (str(repo).encode(), str(Path.home()).encode())
            if any(
                forbidden in member
                for forbidden in forbidden_paths
                for member in quest_files.values()
            ):
                raise CrownseedError("Loom archive contains a local absolute path")

            actual_receipt = verify_quest_archive(archive, repo)
            stored_receipt = strict_json(
                files["quest-verification.json"],
                "quest-verification.json",
            )
            if not json_equal_exact(actual_receipt, stored_receipt):
                raise CrownseedError(
                    "stored Loom receipt does not match repository evidence"
                )
            if (
                stored_receipt.get("schema")
                != "kingdom.quest-verification/v1"
                or stored_receipt.get("repository_bound") is not True
                or stored_receipt.get("quest_id") != envelope["quest"]["id"]
                or stored_receipt.get("packet_sha256")
                != envelope["quest"]["packet_sha256"]
                or stored_receipt.get("archive_sha256")
                != envelope["quest"]["archive_sha256"]
                or stored_receipt.get("effect_ceiling")
                != envelope["quest"]["effect_ceiling"]
            ):
                raise CrownseedError(
                    "Loom receipt is not fully repository-bound"
                )

            ready = exact_keys(
                strict_json(files["READY.json"], "READY.json"),
                {
                    "schema",
                    "id",
                    "passport_sha256",
                    "quest_archive_sha256",
                    "receipt_sha256",
                },
                "READY",
            )
            if not json_equal_exact(ready, {
                "schema": READY_SCHEMA,
                "id": envelope["id"],
                "passport_sha256": sha256_bytes(files["crownseed.json"]),
                "quest_archive_sha256": sha256_bytes(archive),
                "receipt_sha256": sha256_bytes(
                    files["quest-verification.json"]
                ),
            }):
                raise CrownseedError("READY marker differs from passport bytes")
            realm._assert_repo_identity(held)
            _assert_output_parent(path, passport_fd, passport_identity)
            return {
                "schema": VERIFY_SCHEMA,
                "status": "ready",
                "id": envelope["id"],
                "realm": envelope["realm"]["name"],
                "domain": envelope["realm"]["domain"],
                "passport_sha256": sha256_bytes(files["crownseed.json"]),
                "quest_archive_sha256": envelope["quest"]["archive_sha256"],
                "repository_bound": True,
                "executes_quest": False,
                "creates_authority": False,
            }
        finally:
            if passport_fd >= 0:
                try:
                    os.close(passport_fd)
                except OSError:
                    pass


def publish_capsule(
    *,
    output_value: str,
    repo: Path,
    repo_value: str,
    envelope: dict[str, Any],
    archive: bytes,
    dark: dict[str, Any],
    identity: tuple[int, int],
) -> dict[str, Any]:
    output = output_path(output_value, repo, must_exist=False)
    validate_envelope(envelope)
    if not json_equal_exact(dark, envelope["frontier"]):
        raise CrownseedError("compiled frontier snapshot differs from the passport")
    if sha256_bytes(archive) != envelope["quest"]["archive_sha256"]:
        raise CrownseedError("compiled Loom archive differs from the passport")
    assert_repo_identity(repo, identity)
    schema_data = read_regular(SCHEMA_PATH, "reviewed Crownseed schema", 1_000_000)
    strict_json(schema_data, "reviewed Crownseed schema")
    parent_fd, parent_identity = _output_parent_handle(output)
    staging_name = ""
    staging_fd = -1
    committed = False
    try:
        staging_name, staging_fd = _create_staging(parent_fd)
        staging = output.parent / staging_name
        initial = {
            "crownseed.json": pretty_json(envelope),
            "crownseed.schema.json": schema_data,
            "kingdom-quest.tgz": archive,
        }
        for name, data in initial.items():
            write_exclusive_at(staging_fd, name, data)
        _assert_output_parent(output.parent, parent_fd, parent_identity)
        receipt = verify_quest_archive(archive, repo)
        if receipt.get("repository_bound") is not True:
            raise CrownseedError("Loom could not bind the quest to the explicit realm")
        receipt_data = loom.pretty_json(receipt)
        write_exclusive_at(staging_fd, "quest-verification.json", receipt_data)
        ready_data = pretty_json(
            {
                "schema": READY_SCHEMA,
                "id": envelope["id"],
                "passport_sha256": sha256_bytes(initial["crownseed.json"]),
                "quest_archive_sha256": sha256_bytes(archive),
                "receipt_sha256": sha256_bytes(receipt_data),
            }
        )
        write_exclusive_at(staging_fd, "READY.json", ready_data)
        covered = {
            **initial,
            "quest-verification.json": receipt_data,
            "READY.json": ready_data,
        }
        sums = checksum_bytes(covered)
        write_exclusive_at(staging_fd, "SHA256SUMS", sums)
        os.fsync(staging_fd)
        if sum(len(data) for data in covered.values()) + len(sums) > MAX_TOTAL_BYTES:
            raise CrownseedError("passport exceeds its total byte budget")
        assert_repo_identity(repo, identity)
        verification = verify_capsule(str(staging), repo_value)
        _assert_output_parent(output.parent, parent_fd, parent_identity)
        if not _staging_is_named_here(parent_fd, staging_fd, staging_name):
            raise CrownseedError("private Crownseed staging identity changed")
        publication_error: BaseException | None = None
        try:
            _rename_no_replace(parent_fd, staging_name, output.name)
        except BaseException as error:
            publication_error = error
        try:
            source_is_held, destination_is_held, destination_exists = (
                _publication_state(
                    parent_fd,
                    staging_fd,
                    staging_name,
                    output.name,
                )
            )
        except BaseException as state_error:
            raise CrownseedError(
                "Crownseed publication state could not be reconciled; "
                "do not retry automatically"
            ) from state_error
        if destination_is_held and not source_is_held:
            # The syscall committed the exact held directory, even if the
            # caller observed EINTR or another exception. Reconciliation is
            # authoritative and prevents a destructive blind retry.
            committed = True
        elif source_is_held:
            if publication_error is None:
                raise CrownseedError(
                    "Crownseed publication reported success without committing; "
                    "do not retry automatically"
                )
            if isinstance(publication_error, (KeyboardInterrupt, SystemExit)):
                raise publication_error
            if isinstance(publication_error, FileExistsError) and destination_exists:
                raise CrownseedError(
                    "Crownseed output appeared during staging; nothing was replaced"
                ) from publication_error
            if isinstance(publication_error, CrownseedError):
                raise publication_error
            if isinstance(publication_error, OSError):
                raise CrownseedError(
                    "atomic Crownseed publication failed; nothing was published"
                ) from publication_error
            raise CrownseedError(
                "Crownseed publication failed before commit"
            ) from publication_error
        else:
            raise CrownseedError(
                "Crownseed publication result could not be reconciled; "
                "do not retry automatically"
            ) from publication_error
        if not committed:
            raise CrownseedError("Crownseed passport was not published")
        try:
            os.fsync(parent_fd)
        except OSError:
            # The exact verified directory already committed. Durability debt
            # must not invite a blind retry after that commit point.
            pass
        try:
            _source_is_held, destination_is_held, _destination_exists = (
                _publication_state(
                    parent_fd,
                    staging_fd,
                    staging_name,
                    output.name,
                )
            )
            if not destination_is_held:
                raise CrownseedError("the committed Crownseed output name moved")
            _assert_output_parent(output.parent, parent_fd, parent_identity)
        except CrownseedError as error:
            raise CrownseedCommittedDrift(
                "the exact passport committed to the held output parent, "
                "but its explicit path changed; do not retry",
                verification,
            ) from error
        return verification
    except CrownseedCommittedDrift:
        raise
    except CrownseedError:
        raise
    except BaseException as error:
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            raise
        raise CrownseedError("passport publication was quarantined") from error
    finally:
        if staging_fd >= 0 and staging_name:
            _cleanup_staging(parent_fd, staging_fd, staging_name)
        if staging_fd >= 0:
            try:
                os.close(staging_fd)
            except OSError:
                pass
        try:
            os.close(parent_fd)
        except OSError:
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kingdom nen crownseed",
        description=(
            "Forge one portable sovereign invitation. Preview is default; "
            "nothing executes and nothing grants authority."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)
    compile_parser = commands.add_parser("compile", help="preview or write one passport")
    compile_parser.add_argument("--repo", required=True)
    compile_parser.add_argument("--objective", required=True)
    compile_parser.add_argument("--acceptance", required=True)
    compile_parser.add_argument(
        "--effect-ceiling",
        choices=loom.EFFECT_CEILINGS,
        default="observe",
    )
    compile_parser.add_argument("--exclusions", default="")
    compile_parser.add_argument("--focus-path", default=".")
    compile_parser.add_argument("--unknown", action="append", default=[])
    compile_parser.add_argument("--output")
    compile_parser.add_argument("--write", action="store_true")
    verify_parser = commands.add_parser("verify", help="verify a passport directory")
    verify_parser.add_argument("path")
    verify_parser.add_argument("--repo", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "verify":
            print(
                json.dumps(
                    verify_capsule(args.path, args.repo),
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 0
        if args.output and not args.write:
            raise CrownseedError("--output has no effect without explicit --write")
        if args.write and not args.output:
            raise CrownseedError("--write requires an explicit absolute --output")
        repo, envelope, archive, dark, identity = compile_crownseed(
            repo_value=args.repo,
            objective=args.objective,
            acceptance=args.acceptance,
            effect_ceiling=args.effect_ceiling,
            exclusions=args.exclusions,
            focus_path=args.focus_path,
            unknowns=args.unknown,
        )
        if not args.write:
            sys.stdout.write(pretty_json(envelope).decode("utf-8"))
            print(
                "preview only — no passport written; add --write and --output",
                file=sys.stderr,
            )
            return 0
        receipt = publish_capsule(
            output_value=args.output,
            repo=repo,
            repo_value=args.repo,
            envelope=envelope,
            archive=archive,
            dark=dark,
            identity=identity,
        )
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
        return 0
    except CrownseedCommittedDrift as error:
        print(
            json.dumps(error.verification, ensure_ascii=False, sort_keys=True)
        )
        print(f"kingdom nen crownseed: ⚠ {error}", file=sys.stderr)
        return 0
    except CrownseedError as error:
        print(f"kingdom nen crownseed: quarantined — {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
