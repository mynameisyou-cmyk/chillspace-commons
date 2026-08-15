#!/usr/bin/env python3
"""Classify explicit macOS paths as evidence, never as ambient authority."""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import pwd
import re
import stat
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Any, Sequence


SCHEMA_ID = "kingdom.path/v1"
CLASSIFIER_ID = "darwin-path/1"
MAX_PATH_TEXT = 8_192
MAX_DOCUMENT_BYTES = 10_000_000
MAX_INPUTS = 4_096
NON_CLAIMS = (
    "Path, POSIX, ACL, flag, and volume evidence does not establish macOS TCC consent.",
    "Process access probes describe only this classifier process and do not establish a future Codex sandbox.",
    "Cloud-backed and external classifications describe locality risk, not availability or permission.",
)
RELEVANT_XATTRS = {
    "com.apple.FinderInfo",
    "com.apple.macl",
    "com.apple.provenance",
    "com.apple.quarantine",
    "com.apple.rootless",
}
AUTHORITY_REASON = (
    "Path and process evidence cannot establish consent or a future execution boundary."
)


class PathContractError(ValueError):
    """A path cannot be represented by the bounded classifier contract."""


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def clean_path(value: str, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PathContractError(f"{label} is required")
    if len(value) > MAX_PATH_TEXT:
        raise PathContractError(f"{label} is too long")
    if "\0" in value or any(
        ord(char) == 127
        or unicodedata.category(char) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
        for char in value
    ):
        raise PathContractError(f"{label} contains control characters")
    value = unicodedata.normalize("NFC", value)
    if not Path(value).is_absolute():
        raise PathContractError(f"{label} must be absolute")
    return value


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def resolved_workspace_roots(values: Sequence[str]) -> list[Path]:
    if len(values) > MAX_INPUTS:
        raise PathContractError(f"workspace roots exceed {MAX_INPUTS}")
    roots: list[Path] = []
    for value in values:
        cleaned = clean_path(value, "workspace root")
        lexical = Path(os.path.normpath(cleaned))
        if Path(cleaned) != lexical:
            raise PathContractError(
                f"workspace root must be lexical-canonical: {lexical}"
            )
        if not lexical.is_dir() or lexical.is_symlink():
            raise PathContractError(f"workspace root is missing or unsafe: {lexical}")
        try:
            resolved = lexical.resolve(strict=True)
        except OSError as error:
            raise PathContractError(f"workspace root cannot be resolved: {lexical}") from error
        if lexical != resolved:
            raise PathContractError(
                f"workspace root must use its canonical real path: {resolved}"
            )
        roots.append(resolved)
    unique = sorted(set(roots), key=str)
    if len(unique) != len(roots):
        raise PathContractError("workspace roots contain duplicates")
    return unique


def deepest_existing_ancestor(path: Path) -> tuple[Path, list[str]]:
    cursor = path
    suffix: list[str] = []
    while True:
        try:
            cursor.stat()
            break
        except (OSError, RuntimeError):
            pass
        parent = cursor.parent
        if parent == cursor:
            break
        suffix.insert(0, cursor.name)
        cursor = parent
    return cursor, suffix


def file_type(mode: int) -> str:
    if stat.S_ISREG(mode):
        return "file"
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISLNK(mode):
        return "symlink"
    if stat.S_ISFIFO(mode):
        return "fifo"
    if stat.S_ISSOCK(mode):
        return "socket"
    if stat.S_ISCHR(mode):
        return "character-device"
    if stat.S_ISBLK(mode):
        return "block-device"
    return "other"


def symlink_component_count(path: Path) -> int:
    count = 0
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        try:
            if current.is_symlink():
                count += 1
        except OSError:
            break
    return count


def resolution_error_label(error: BaseException) -> str:
    if isinstance(error, RuntimeError) or getattr(error, "errno", None) == errno.ELOOP:
        return "symlink-loop"
    if isinstance(error, PermissionError):
        return "permission-denied"
    return "resolution-failed"


def classify_domain(
    resolved: Path, workspace_roots: Sequence[Path], home: Path | None = None
) -> tuple[str, str]:
    if home is None:
        try:
            home = Path(pwd.getpwuid(os.geteuid()).pw_dir).resolve()
        except (KeyError, OSError):
            home = None
    for root in workspace_roots:
        if is_within(resolved, root):
            return "workspace", "inferred"
    if home is not None:
        provider_roots = (
            home / "Library" / "CloudStorage",
            home / "Library" / "Mobile Documents",
        )
        if any(is_within(resolved, root) for root in provider_roots):
            return "provider", "inferred"
    if is_within(resolved, Path("/Volumes")) and resolved != Path("/Volumes"):
        return "external", "inferred"
    if is_within(resolved, Path("/System/Volumes/Data")) or is_within(
        resolved, Path("/private")
    ):
        return "local-runtime", "inferred"
    system_roots = (Path("/System"), Path("/bin"), Path("/sbin"))
    if any(is_within(resolved, root) for root in system_roots):
        return "system", "inferred"
    if is_within(resolved, Path("/usr")) and not is_within(
        resolved, Path("/usr/local")
    ):
        return "system", "inferred"
    local_roots = (
        Path("/Library"),
        Path("/Applications"),
        Path("/opt"),
        Path("/usr/local"),
    )
    if any(is_within(resolved, root) for root in local_roots):
        return "local-library", "inferred"
    if home is not None:
        if is_within(resolved, home / "Library"):
            return "user-library", "inferred"
        if is_within(resolved, home):
            return "user-home", "inferred"
    return "other", "inferred"


def classify_locality(domain: str) -> tuple[str, str, str]:
    if domain == "unknown":
        return "unknown", "unknown", "unknown"
    if domain == "provider":
        return "remote-capable", "inferred", "unknown"
    if domain == "external":
        return "external-or-network", "inferred", "unknown"
    return "local", "inferred", "not-applicable"


def xattr_evidence(path: Path) -> dict[str, Any]:
    try:
        all_names = [str(name) for name in os.listxattr(path, follow_symlinks=False)]
    except (AttributeError, OSError):
        return {"truth": "unknown", "names": [], "unreported_count": 0}
    names = sorted(name for name in all_names if name in RELEVANT_XATTRS)
    return {
        "truth": "observed",
        "names": names,
        "unreported_count": len(all_names) - len(names),
    }


def classify_path(
    requested: str, workspace_roots: Sequence[str] = ()
) -> dict[str, Any]:
    requested = clean_path(requested, "path")
    lexical = Path(os.path.normpath(requested))
    if Path(requested) != lexical:
        raise PathContractError(f"path must be lexical-canonical: {lexical}")
    roots = resolved_workspace_roots(workspace_roots)
    try:
        lexical_stat = lexical.lstat()
        lexical_exists = True
    except OSError:
        lexical_stat = None
        lexical_exists = False
    ancestor, missing_suffix = deepest_existing_ancestor(lexical)
    try:
        resolved = lexical.resolve(strict=True)
        target_exists = True
        resolution_error = ""
    except FileNotFoundError:
        target_exists = False
        try:
            resolved = lexical.resolve(strict=False)
            resolution_error = ""
        except (OSError, RuntimeError) as error:
            try:
                resolved = ancestor.resolve(strict=True).joinpath(*missing_suffix)
            except (OSError, RuntimeError):
                resolved = lexical
            resolution_error = resolution_error_label(error)
    except (OSError, RuntimeError) as error:
        target_exists = False
        try:
            resolved = ancestor.resolve(strict=True).joinpath(*missing_suffix)
        except (OSError, RuntimeError):
            resolved = lexical
        resolution_error = resolution_error_label(error)

    lexical_inside = [str(root) for root in roots if is_within(lexical, root)]
    resolved_inside = (
        []
        if resolution_error
        else [str(root) for root in roots if is_within(resolved, root)]
    )
    if resolution_error:
        workspace_relation = "unresolved"
    elif resolved_inside:
        workspace_relation = "inside"
    elif lexical_inside:
        workspace_relation = "escaped-via-resolution"
    else:
        workspace_relation = "outside"

    if resolution_error:
        domain, domain_truth = "unknown", "unknown"
    else:
        domain, domain_truth = classify_domain(resolved, roots)
    locality, locality_truth, materialization = classify_locality(domain)

    metadata_path = lexical if target_exists else ancestor
    try:
        metadata_stat = metadata_path.stat()
    except OSError:
        metadata_stat = None
    try:
        volume = os.statvfs(metadata_path)
        read_only = bool(volume.f_flag & getattr(os, "ST_RDONLY", 1))
        volume_truth = "observed"
    except OSError:
        read_only = None
        volume_truth = "unknown"

    metadata: dict[str, Any] = {
        "source": "target" if target_exists else "deepest-existing-ancestor",
        "file_type": file_type(lexical_stat.st_mode) if lexical_stat else "missing",
        "mode": (
            f"{stat.S_IMODE(metadata_stat.st_mode):04o}" if metadata_stat else None
        ),
        "uid": metadata_stat.st_uid if metadata_stat else None,
        "gid": metadata_stat.st_gid if metadata_stat else None,
        "device": metadata_stat.st_dev if metadata_stat else None,
        "inode": metadata_stat.st_ino if metadata_stat else None,
        "flags": getattr(metadata_stat, "st_flags", None) if metadata_stat else None,
        "xattrs": xattr_evidence(lexical if lexical_exists else ancestor),
    }
    probes = {
        "target_readable": os.access(lexical, os.R_OK),
        "target_writable": os.access(lexical, os.W_OK),
        "target_executable": os.access(lexical, os.X_OK),
        "ancestor_writable": os.access(ancestor, os.W_OK),
        "ancestor_executable": os.access(ancestor, os.X_OK),
        "truth": "observed-for-current-process",
    }
    record: dict[str, Any] = {
        "requested_path": requested,
        "lexical_path": str(lexical),
        "resolved_path": str(resolved),
        "resolution": {
            "complete": target_exists,
            "error": resolution_error or None,
            "deepest_existing_ancestor": str(ancestor),
            "missing_suffix": missing_suffix,
            "lexical_exists": lexical_exists,
            "target_exists": target_exists,
            "symlink_components": symlink_component_count(lexical),
            "final_component_is_symlink": bool(
                lexical_stat and stat.S_ISLNK(lexical_stat.st_mode)
            ),
        },
        "workspace": {
            "relation": workspace_relation,
            "lexical_roots": lexical_inside,
            "resolved_roots": resolved_inside,
        },
        "domain": {"value": domain, "truth": domain_truth},
        "locality": {
            "value": locality,
            "truth": locality_truth,
            "materialization": materialization,
        },
        "metadata": metadata,
        "volume": {"read_only": read_only, "truth": volume_truth},
        "process_access": probes,
        "authority": {
            "effective": "unknown",
            "tcc": "unknown",
            "codex_sandbox": "unknown",
            "acl": "unknown",
            "reason": AUTHORITY_REASON,
        },
    }
    record["record_digest"] = sha256_bytes(canonical_json(record))
    return record


def classify_paths(
    requested_paths: Sequence[str], workspace_roots: Sequence[str] = ()
) -> dict[str, Any]:
    if not requested_paths:
        raise PathContractError("at least one explicit path is required")
    if len(requested_paths) > MAX_INPUTS:
        raise PathContractError(f"paths exceed {MAX_INPUTS}")
    records = [classify_path(value, workspace_roots) for value in requested_paths]
    records.sort(key=lambda item: item["lexical_path"])
    lexical_paths = [item["lexical_path"] for item in records]
    if len(set(lexical_paths)) != len(lexical_paths):
        raise PathContractError("paths contain duplicate lexical targets")
    document: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "classifier": CLASSIFIER_ID,
        "host": {
            "kernel": os.uname().sysname,
            "machine": os.uname().machine,
            "hostname_included": False,
        },
        "records": records,
        "non_claims": list(NON_CLAIMS),
    }
    document["classification_digest"] = sha256_bytes(canonical_json(document))
    if len(canonical_json(document)) > MAX_DOCUMENT_BYTES:
        raise PathContractError("classification document exceeds the bounded size")
    return document


def read_regular_bytes(path: Path, maximum: int) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise PathContractError(f"document is missing or unsafe: {path}: {error}") from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > maximum:
            raise PathContractError(f"document is not a bounded regular file: {path}")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            data = handle.read(maximum + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(data) > maximum:
        raise PathContractError("document is too large")
    return data


def require_exact_object(
    value: Any, keys: set[str], label: str
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise PathContractError(f"{label} has missing or unknown keys")
    return value


def require_nonnegative_integer(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise PathContractError(f"{label} must be a non-negative integer")
    return value


def require_absolute_path_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or clean_path(value, label) != value:
        raise PathContractError(f"{label} is not canonical path text")
    path = Path(value)
    if Path(os.path.normpath(value)) != path:
        raise PathContractError(f"{label} is not lexical-canonical")
    return value


def require_string_array(
    value: Any,
    label: str,
    *,
    absolute: bool = False,
    sorted_unique: bool = True,
) -> list[str]:
    if not isinstance(value, list):
        raise PathContractError(f"{label} must be an array")
    result: list[str] = []
    for index, item in enumerate(value):
        if absolute:
            item = require_absolute_path_text(item, f"{label}[{index}]")
        elif (
            not isinstance(item, str)
            or not item
            or item in {".", ".."}
            or "/" in item
            or unicodedata.normalize("NFC", item) != item
            or any(
                ord(char) == 127
                or unicodedata.category(char)
                in {"Cc", "Cf", "Cs", "Zl", "Zp"}
                for char in item
            )
        ):
            raise PathContractError(f"{label}[{index}] is invalid")
        result.append(item)
    if sorted_unique and result != sorted(set(result)):
        raise PathContractError(f"{label} is not sorted and unique")
    return result


def validate_record(record: dict[str, Any]) -> None:
    require_exact_object(
        record,
        {
            "requested_path",
            "lexical_path",
            "resolved_path",
            "resolution",
            "workspace",
            "domain",
            "locality",
            "metadata",
            "volume",
            "process_access",
            "authority",
            "record_digest",
        },
        "classification record",
    )
    requested = require_absolute_path_text(
        record["requested_path"], "classification requested path"
    )
    lexical = require_absolute_path_text(
        record["lexical_path"], "classification lexical path"
    )
    require_absolute_path_text(
        record["resolved_path"], "classification resolved path"
    )
    if lexical != str(Path(os.path.normpath(requested))):
        raise PathContractError("classification lexical path is not derived")

    resolution = require_exact_object(
        record["resolution"],
        {
            "complete",
            "error",
            "deepest_existing_ancestor",
            "missing_suffix",
            "lexical_exists",
            "target_exists",
            "symlink_components",
            "final_component_is_symlink",
        },
        "classification resolution evidence",
    )
    for key in (
        "complete",
        "lexical_exists",
        "target_exists",
        "final_component_is_symlink",
    ):
        if type(resolution[key]) is not bool:
            raise PathContractError(f"classification resolution {key} is invalid")
    if resolution["complete"] != resolution["target_exists"]:
        raise PathContractError("classification resolution completeness is inconsistent")
    error = resolution["error"]
    if error not in {None, "symlink-loop", "permission-denied", "resolution-failed"}:
        raise PathContractError("classification resolution error is invalid")
    ancestor = require_absolute_path_text(
        resolution["deepest_existing_ancestor"],
        "classification deepest existing ancestor",
    )
    missing_suffix = require_string_array(
        resolution["missing_suffix"],
        "classification missing suffix",
        sorted_unique=False,
    )
    if Path(ancestor).joinpath(*missing_suffix) != Path(lexical):
        raise PathContractError(
            "classification ancestor and missing suffix do not derive the lexical path"
        )
    if error is not None and resolution["complete"]:
        raise PathContractError(
            "classification cannot be complete with a resolution error"
        )
    if resolution["complete"] and (
        missing_suffix or Path(ancestor) != Path(lexical)
    ):
        raise PathContractError(
            "complete classification has partial-resolution evidence"
        )
    require_nonnegative_integer(
        resolution["symlink_components"],
        "classification symlink component count",
    )
    if error == "symlink-loop" and resolution["symlink_components"] == 0:
        raise PathContractError(
            "symlink-loop classification has no symlink components"
        )
    if resolution["final_component_is_symlink"] and (
        not resolution["lexical_exists"]
        or resolution["symlink_components"] == 0
    ):
        raise PathContractError(
            "final-symlink evidence is inconsistent"
        )

    workspace = require_exact_object(
        record["workspace"],
        {"relation", "lexical_roots", "resolved_roots"},
        "classification workspace evidence",
    )
    lexical_roots = require_string_array(
        workspace["lexical_roots"],
        "classification lexical workspace roots",
        absolute=True,
    )
    resolved_roots = require_string_array(
        workspace["resolved_roots"],
        "classification resolved workspace roots",
        absolute=True,
    )
    if any(
        not is_within(Path(lexical), Path(root)) for root in lexical_roots
    ) or any(
        not is_within(Path(record["resolved_path"]), Path(root))
        for root in resolved_roots
    ):
        raise PathContractError(
            "classification workspace roots do not contain their paths"
        )
    if error:
        expected_relation = "unresolved"
        if resolved_roots:
            raise PathContractError(
                "unresolved classification has resolved workspace roots"
            )
    elif resolved_roots:
        expected_relation = "inside"
    elif lexical_roots:
        expected_relation = "escaped-via-resolution"
    else:
        expected_relation = "outside"
    if workspace["relation"] != expected_relation:
        raise PathContractError("classification workspace relation is inconsistent")

    domain = require_exact_object(
        record["domain"], {"value", "truth"}, "classification domain evidence"
    )
    domain_values = {
        "workspace",
        "provider",
        "external",
        "system",
        "local-library",
        "user-library",
        "user-home",
        "local-runtime",
        "other",
        "unknown",
    }
    if domain["value"] not in domain_values:
        raise PathContractError("classification domain is invalid")
    if error:
        expected_domain = {"value": "unknown", "truth": "unknown"}
    else:
        expected_domain_value, expected_domain_truth = classify_domain(
            Path(record["resolved_path"]),
            [Path(root) for root in resolved_roots],
        )
        expected_domain = {
            "value": expected_domain_value,
            "truth": expected_domain_truth,
        }
    if domain != expected_domain:
        raise PathContractError(
            "classification domain does not match its path evidence"
        )

    locality = require_exact_object(
        record["locality"],
        {"value", "truth", "materialization"},
        "classification locality evidence",
    )
    expected_locality = classify_locality(domain["value"])
    if (
        locality["value"],
        locality["truth"],
        locality["materialization"],
    ) != expected_locality:
        raise PathContractError("classification locality is inconsistent")

    metadata = require_exact_object(
        record["metadata"],
        {
            "source",
            "file_type",
            "mode",
            "uid",
            "gid",
            "device",
            "inode",
            "flags",
            "xattrs",
        },
        "classification metadata",
    )
    expected_source = (
        "target" if resolution["target_exists"] else "deepest-existing-ancestor"
    )
    if metadata["source"] != expected_source:
        raise PathContractError("classification metadata source is inconsistent")
    allowed_file_types = {
        "file",
        "directory",
        "symlink",
        "fifo",
        "socket",
        "character-device",
        "block-device",
        "other",
        "missing",
    }
    if metadata["file_type"] not in allowed_file_types:
        raise PathContractError("classification file type is invalid")
    if (metadata["file_type"] == "missing") != (
        not resolution["lexical_exists"]
    ):
        raise PathContractError("classification file existence is inconsistent")
    if (metadata["file_type"] == "symlink") != resolution[
        "final_component_is_symlink"
    ]:
        raise PathContractError("classification final-symlink type is inconsistent")
    if metadata["mode"] is not None and (
        not isinstance(metadata["mode"], str)
        or not re.fullmatch(r"[0-7]{4}", metadata["mode"])
    ):
        raise PathContractError("classification mode is invalid")
    for key in ("uid", "gid", "device", "inode", "flags"):
        value = metadata[key]
        if value is not None:
            require_nonnegative_integer(value, f"classification metadata {key}")
    xattrs = require_exact_object(
        metadata["xattrs"],
        {"truth", "names", "unreported_count"},
        "classification xattr evidence",
    )
    if (
        not isinstance(xattrs["names"], list)
        or xattrs["names"] != sorted(set(xattrs["names"]))
        or any(name not in RELEVANT_XATTRS for name in xattrs["names"])
    ):
        raise PathContractError("classification xattr names are invalid")
    require_nonnegative_integer(
        xattrs["unreported_count"], "classification unreported xattr count"
    )
    if xattrs["truth"] == "unknown":
        if xattrs["names"] or xattrs["unreported_count"]:
            raise PathContractError("unknown xattr evidence contains observations")
    elif xattrs["truth"] != "observed":
        raise PathContractError("classification xattr truth is invalid")

    volume = require_exact_object(
        record["volume"], {"read_only", "truth"}, "classification volume evidence"
    )
    if volume["truth"] == "observed":
        if type(volume["read_only"]) is not bool:
            raise PathContractError("observed volume evidence is not boolean")
    elif volume["truth"] == "unknown":
        if volume["read_only"] is not None:
            raise PathContractError("unknown volume evidence contains an observation")
    else:
        raise PathContractError("classification volume truth is invalid")

    process_access = require_exact_object(
        record["process_access"],
        {
            "target_readable",
            "target_writable",
            "target_executable",
            "ancestor_writable",
            "ancestor_executable",
            "truth",
        },
        "classification process-access evidence",
    )
    for key in (
        "target_readable",
        "target_writable",
        "target_executable",
        "ancestor_writable",
        "ancestor_executable",
    ):
        if type(process_access[key]) is not bool:
            raise PathContractError(f"classification process-access {key} is invalid")
    if process_access["truth"] != "observed-for-current-process":
        raise PathContractError("classification process-access truth is invalid")

    authority = require_exact_object(
        record["authority"],
        {"effective", "tcc", "codex_sandbox", "acl", "reason"},
        "classification authority",
    )
    if any(
        authority[key] != "unknown"
        for key in ("effective", "tcc", "codex_sandbox", "acl")
    ) or authority["reason"] != AUTHORITY_REASON:
        raise PathContractError("classification overclaims effective authority")

    supplied_record = record["record_digest"]
    if (
        not isinstance(supplied_record, str)
        or not re.fullmatch(r"[0-9a-f]{64}", supplied_record)
    ):
        raise PathContractError("classification record digest is invalid")
    subject_record = dict(record)
    subject_record.pop("record_digest")
    if supplied_record != sha256_bytes(canonical_json(subject_record)):
        raise PathContractError("classification record digest does not match")


def verify_document(data: bytes) -> dict[str, Any]:
    if len(data) > MAX_DOCUMENT_BYTES:
        raise PathContractError("classification document is too large")
    try:
        document = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PathContractError("classification is not valid UTF-8 JSON") from error
    expected_top = {
        "schema",
        "classifier",
        "host",
        "records",
        "non_claims",
        "classification_digest",
    }
    if not isinstance(document, dict) or set(document) != expected_top:
        raise PathContractError("classification has missing or unknown top-level keys")
    if (
        document.get("schema") != SCHEMA_ID
        or document.get("classifier") != CLASSIFIER_ID
        or document.get("non_claims") != list(NON_CLAIMS)
    ):
        raise PathContractError("classification contract changed")
    supplied = document.get("classification_digest")
    subject = dict(document)
    subject.pop("classification_digest", None)
    if (
        not isinstance(supplied, str)
        or not re.fullmatch(r"[0-9a-f]{64}", supplied)
        or supplied != sha256_bytes(canonical_json(subject))
    ):
        raise PathContractError("classification digest does not match")
    if data != canonical_json(document):
        raise PathContractError("classification is not in canonical JSON form")
    host = require_exact_object(
        document.get("host"),
        {"kernel", "machine", "hostname_included"},
        "classification host evidence",
    )
    if host["hostname_included"] is not False:
        raise PathContractError("classification host evidence is invalid")
    for key in ("kernel", "machine"):
        value = host[key]
        if (
            not isinstance(value, str)
            or not value
            or len(value) > 128
            or unicodedata.normalize("NFC", value) != value
            or any(
                ord(char) == 127
                or unicodedata.category(char)
                in {"Cc", "Cf", "Cs", "Zl", "Zp"}
                for char in value
            )
        ):
            raise PathContractError(f"classification host {key} is invalid")
    records = document.get("records")
    if (
        not isinstance(records, list)
        or not records
        or len(records) > MAX_INPUTS
    ):
        raise PathContractError("classification records must be a non-empty array")
    for record in records:
        if not isinstance(record, dict):
            raise PathContractError("classification record must be an object")
        validate_record(record)
    lexical_paths = [record["lexical_path"] for record in records]
    if lexical_paths != sorted(lexical_paths) or len(set(lexical_paths)) != len(
        lexical_paths
    ):
        raise PathContractError("classification record order is not canonical")
    return document


def atomic_write(path: Path, data: bytes) -> None:
    if not path.is_absolute():
        raise PathContractError("output path must be absolute")
    normalized = Path(os.path.normpath(str(path)))
    if normalized != path:
        raise PathContractError(f"output path must be lexical-canonical: {normalized}")
    parent = path.parent
    try:
        resolved_parent = parent.resolve(strict=True)
        parent_metadata = parent.lstat()
    except OSError as error:
        raise PathContractError(
            f"output parent is missing or unsafe: {parent}: {error}"
        ) from error
    if (
        resolved_parent != parent
        or not stat.S_ISDIR(parent_metadata.st_mode)
        or stat.S_ISLNK(parent_metadata.st_mode)
    ):
        raise PathContractError(f"output parent is missing or unsafe: {parent}")
    if path.is_symlink():
        raise PathContractError(f"refusing symlink output: {path}")
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--path", action="append")
    inputs.add_argument("--verify")
    parser.add_argument("--workspace-root", action="append", default=[])
    parser.add_argument("--output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.verify:
            if args.workspace_root or args.output:
                raise PathContractError(
                    "--verify cannot be combined with workspace roots or output"
                )
            path = Path(args.verify)
            verify_document(read_regular_bytes(path, MAX_DOCUMENT_BYTES))
            print(f"verified {path}")
        else:
            document = classify_paths(args.path, args.workspace_root)
            data = canonical_json(document)
            if len(data) > MAX_DOCUMENT_BYTES:
                raise PathContractError(
                    "classification document exceeds the bounded size"
                )
            if args.output:
                atomic_write(Path(args.output), data)
                print(args.output)
            else:
                sys.stdout.buffer.write(data)
    except (OSError, PathContractError) as error:
        print(f"darwin-path: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
