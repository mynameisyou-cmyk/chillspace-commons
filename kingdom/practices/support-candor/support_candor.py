#!/usr/bin/env python3
"""Validate and render evidence-scoped SDK and Agent Skill support ledgers."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from collections import Counter
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any


HERE = Path(__file__).resolve().parent
SCHEMA_ID = "kingdom.support-candor/v1"
EVIDENCE_SCHEMA_ID = "kingdom.support-candor.evidence/v1"
BASELINE_ID = "kingdom.portable-agent-artifact/v1"
BASELINE_CAPABILITIES = ("acquire", "run", "host-boundary", "stop", "deny")
SUBJECT_KINDS = ("sdk", "agent-skill")
TARGET_FAMILIES = ("macos", "linux", "windows-native", "wsl2", "codex-cloud")
SCOPE_STATES = ("exact", "candidate")
RECEIPT_KINDS = ("ci-run", "local-reproduction")
RESULTS = ("pass", "fail", "mixed")
GAP_KINDS = ("limitation", "known-failure", "unknown", "excluded")
GAP_IMPACTS = ("narrows", "blocks", "unknown", "excluded")
NEXT_STAGES = ("considering", "planned", "in-progress")
SUPPORT_POLICIES = ("supported", "best-effort", "not-supported", "undecided")
PUBLIC_STATUSES = ("VERIFIED", "CONSTRAINED", "NOT_SUPPORTED", "UNKNOWN")
MAX_MANIFEST_BYTES = 512 * 1024
MAX_RECEIPT_BYTES = 128 * 1024
MAX_TARGETS = len(TARGET_FAMILIES)
MAX_CAPABILITIES = 24
MAX_EVIDENCE = 120
MAX_ASSERTIONS = MAX_TARGETS * MAX_CAPABILITIES
ID = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

BOUNDARIES = {
    "now_requires_matching_executable_evidence": True,
    "support_policy_is_separate_from_observed_behavior": True,
    "next_counts_as_current_support": False,
    "automatic_support_promotion": False,
    "cross_target_evidence_inheritance": False,
    "identity_or_reputation_scoring": False,
    "network_calls": False,
    "subprocesses": False,
    "storage_writes": False,
    "external_actions": False,
}

NON_CLAIMS = (
    "A valid ledger proves declaration coherence, not runtime compatibility or product quality.",
    "NOW evidence applies only to the exact subject revision, artifact digest, target, and environment named.",
    "GAP is explicit but not necessarily exhaustive; an unlisted failure may still exist.",
    "NEXT records intention only and is not current support, a delivery date, or a release promise.",
    "A digest proves byte equality only; it does not establish identity, trust, safety, or authority.",
    "The ledger grants no permission to install, execute, deploy, publish, contact, score, or rank anyone.",
)


class CandorError(ValueError):
    """A support ledger failed closed."""


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest_bytes(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def digest_value(value: object) -> str:
    return digest_bytes(canonical_json(value))


def _no_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise CandorError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def read_regular(path: Path, label: str, limit: int) -> bytes:
    try:
        before = path.lstat()
    except OSError as error:
        raise CandorError(f"{label} is not readable: {path}") from error
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise CandorError(f"{label} must be a regular non-symlink file")
    if before.st_size > limit:
        raise CandorError(f"{label} exceeds {limit} bytes")

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise CandorError(f"{label} could not be opened") from error
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise CandorError(f"{label} changed before it was opened")
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise CandorError(f"{label} changed before it was opened")
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = os.read(descriptor, min(65536, limit + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > limit:
                raise CandorError(f"{label} exceeds {limit} bytes")
        after = os.fstat(descriptor)
        if (opened.st_size, opened.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise CandorError(f"{label} changed while it was read")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def parse_object(data: bytes, label: str) -> dict[str, object]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise CandorError(f"{label} must be UTF-8") from error
    try:
        value = json.loads(text, object_pairs_hook=_no_duplicate_pairs)
    except CandorError:
        raise
    except (ValueError, RecursionError) as error:
        raise CandorError(f"{label} is not valid JSON") from error
    if not isinstance(value, dict):
        raise CandorError(f"{label} must be a JSON object")
    return value


def _object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise CandorError(f"{label} must be an object")
    return value


def _array(value: object, label: str, minimum: int, maximum: int) -> list[object]:
    if not isinstance(value, list):
        raise CandorError(f"{label} must be an array")
    if not minimum <= len(value) <= maximum:
        raise CandorError(f"{label} must contain {minimum}..{maximum} items")
    return value


def _keys(value: dict[str, object], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise CandorError(f"{label} keys differ; missing={missing}, extra={extra}")


def _text(value: object, label: str, maximum: int = 500) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise CandorError(f"{label} must be 1..{maximum} characters")
    if any(ord(character) < 32 for character in value):
        raise CandorError(f"{label} contains a control character")
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise CandorError(f"{label} contains an unpaired Unicode surrogate")
    return value


def _nullable_text(value: object, label: str, maximum: int = 500) -> str | None:
    if value is None:
        return None
    return _text(value, label, maximum)


def _identifier(value: object, label: str) -> str:
    text = _text(value, label, 64)
    if not ID.fullmatch(text):
        raise CandorError(f"{label} is not a portable identifier")
    return text


def _enum(value: object, allowed: tuple[str, ...], label: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise CandorError(f"{label} must be one of {list(allowed)}")
    return value


def _boolean(value: object, expected: bool, label: str) -> None:
    if type(value) is not bool or value is not expected:
        raise CandorError(f"{label} must be {str(expected).lower()}")


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or not DIGEST.fullmatch(value):
        raise CandorError(f"{label} must be a sha256 digest")
    return value


def _nonnegative_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CandorError(f"{label} must be a non-negative integer")
    return value


def _date(value: object, label: str) -> str:
    text = _text(value, label, 10)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as error:
        raise CandorError(f"{label} must be an ISO date") from error
    if parsed.isoformat() != text:
        raise CandorError(f"{label} must use canonical YYYY-MM-DD form")
    return text


def _unique_texts(
    value: object,
    label: str,
    minimum: int = 0,
    maximum: int = 16,
    item_maximum: int = 300,
) -> list[str]:
    items = _array(value, label, minimum, maximum)
    rendered = [_text(item, f"{label}[{index}]", item_maximum) for index, item in enumerate(items)]
    if len(set(rendered)) != len(rendered):
        raise CandorError(f"{label} contains duplicates")
    return rendered


def _id_list(
    value: object,
    label: str,
    minimum: int = 0,
    maximum: int = 16,
    allow_wildcard: bool = False,
) -> list[str]:
    values = _unique_texts(value, label, minimum, maximum, 64)
    for index, item in enumerate(values):
        if allow_wildcard and item == "*":
            continue
        if not ID.fullmatch(item):
            raise CandorError(f"{label}[{index}] is not a portable identifier")
    return values


def _safe_locator(value: object, label: str) -> str:
    text = _text(value, label, 300)
    if "\\" in text or ":" in text:
        raise CandorError(f"{label} must be a relative POSIX path")
    path = PurePosixPath(text)
    if path.is_absolute() or not path.parts:
        raise CandorError(f"{label} must be relative")
    if any(part in (".", "..") or not SAFE_SEGMENT.fullmatch(part) for part in path.parts):
        raise CandorError(f"{label} contains an unsafe path segment")
    return text


def _receipt_bytes(manifest_path: Path, locator: str) -> bytes:
    root = manifest_path.parent.resolve()
    relative = PurePosixPath(locator)
    candidate = root
    try:
        for part in relative.parts:
            candidate = candidate / part
            if stat.S_ISLNK(candidate.lstat().st_mode):
                raise CandorError(f"evidence receipt path must not contain symlinks: {locator}")
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except CandorError:
        raise
    except (OSError, ValueError) as error:
        raise CandorError(f"evidence receipt escapes or is absent: {locator}") from error
    return read_regular(resolved, f"evidence receipt {locator}", MAX_RECEIPT_BYTES)


def _fingerprint(value: object, label: str) -> dict[str, str]:
    item = _object(value, label)
    fields = {
        "os",
        "version",
        "architecture",
        "filesystem",
        "runtime",
        "shell",
        "sandbox",
        "network",
        "notes",
    }
    _keys(item, fields, label)
    return {field: _text(item[field], f"{label}.{field}", 300) for field in sorted(fields)}


def _validate_receipt_content(
    data: bytes,
    label: str,
    subject: dict[str, object],
    target_id: str,
    declared_receipt_kind: str,
    declared_tests: list[str],
    declared_result: str,
    declared_date: str,
    declared_environment: dict[str, object],
) -> None:
    receipt = parse_object(data, f"{label} receipt")
    required = {
        "schema",
        "subject",
        "subject_revision",
        "subject_artifact_digest",
        "target",
        "observed_on",
        "receipt_kind",
        "command",
        "result",
        "tests_passed",
        "tests_failed",
        "tests_skipped",
        "capabilities_observed",
        "environment",
        "privacy_scrubbed",
        "raw_logs_included",
        "attested",
        "action_executed",
        "authority_granted",
    }
    optional = {"verification_note", "gap_preserved"}
    missing = required - set(receipt)
    unexpected = set(receipt) - required - optional
    if missing or unexpected:
        raise CandorError(
            f"{label} receipt fields differ; missing={sorted(missing)}, unexpected={sorted(unexpected)}"
        )
    if receipt["schema"] != EVIDENCE_SCHEMA_ID:
        raise CandorError(f"{label} receipt schema must be {EVIDENCE_SCHEMA_ID}")
    expected_identity = {
        "subject": subject["id"],
        "subject_revision": subject["revision"],
        "subject_artifact_digest": subject["artifact_digest"],
        "target": target_id,
    }
    for field, expected in expected_identity.items():
        if receipt[field] != expected:
            raise CandorError(f"{label} receipt {field} does not match its evidence declaration")
    if _date(receipt["observed_on"], f"{label} receipt observed_on") != declared_date:
        raise CandorError(f"{label} receipt observed_on does not match its evidence declaration")
    receipt_kind = _enum(receipt["receipt_kind"], RECEIPT_KINDS, f"{label} receipt receipt_kind")
    if receipt_kind != declared_receipt_kind:
        raise CandorError(f"{label} receipt kind does not match its evidence declaration")
    _text(receipt["command"], f"{label} receipt command", 1000)
    result = _enum(receipt["result"], RESULTS, f"{label} receipt result")
    if result != declared_result:
        raise CandorError(f"{label} receipt result does not match its evidence declaration")
    passed = _nonnegative_integer(receipt["tests_passed"], f"{label} receipt tests_passed")
    failed = _nonnegative_integer(receipt["tests_failed"], f"{label} receipt tests_failed")
    skipped = _nonnegative_integer(receipt["tests_skipped"], f"{label} receipt tests_skipped")
    if result == "pass" and (passed == 0 or failed != 0 or skipped != 0):
        raise CandorError(f"{label} passing receipt needs passes with zero failures and zero skips")
    if result == "fail" and failed == 0:
        raise CandorError(f"{label} failing receipt needs at least one failure")
    if result == "mixed" and (passed == 0 or failed == 0):
        raise CandorError(f"{label} mixed receipt needs at least one pass and one failure")
    observed = _id_list(
        receipt["capabilities_observed"],
        f"{label} receipt capabilities_observed",
        1,
        MAX_CAPABILITIES,
    )
    if observed != declared_tests:
        raise CandorError(f"{label} receipt capabilities do not match its evidence declaration")
    receipt_environment = _object(receipt["environment"], f"{label} receipt environment")
    expected_environment = set(declared_environment) - {"target_scope"}
    _keys(receipt_environment, expected_environment, f"{label} receipt environment")
    for field in sorted(expected_environment):
        if receipt_environment[field] != declared_environment[field]:
            raise CandorError(f"{label} receipt environment.{field} does not match its evidence declaration")
    _boolean(receipt["privacy_scrubbed"], True, f"{label} receipt privacy_scrubbed")
    _boolean(receipt["raw_logs_included"], False, f"{label} receipt raw_logs_included")
    _boolean(receipt["attested"], False, f"{label} receipt attested")
    _boolean(receipt["action_executed"], False, f"{label} receipt action_executed")
    _boolean(receipt["authority_granted"], False, f"{label} receipt authority_granted")
    for field in sorted(optional & set(receipt)):
        _text(receipt[field], f"{label} receipt {field}", 700)


def _validate_subject(value: object) -> dict[str, object]:
    subject = _object(value, "subject")
    _keys(subject, {"id", "kind", "version", "revision", "artifact_digest", "scope", "as_of"}, "subject")
    _identifier(subject["id"], "subject.id")
    _enum(subject["kind"], SUBJECT_KINDS, "subject.kind")
    _text(subject["version"], "subject.version", 80)
    _text(subject["revision"], "subject.revision", 160)
    _digest(subject["artifact_digest"], "subject.artifact_digest")
    _text(subject["scope"], "subject.scope", 800)
    _date(subject["as_of"], "subject.as_of")
    return subject


def _validate_baseline(value: object) -> None:
    baseline = _object(value, "baseline")
    _keys(baseline, {"id", "required_capabilities"}, "baseline")
    if baseline["id"] != BASELINE_ID:
        raise CandorError(f"baseline.id must be {BASELINE_ID}")
    required = _id_list(baseline["required_capabilities"], "baseline.required_capabilities", 5, 5)
    if tuple(required) != BASELINE_CAPABILITIES:
        raise CandorError("baseline.required_capabilities changed or reordered")


def _validate_targets(value: object) -> dict[str, dict[str, object]]:
    targets: dict[str, dict[str, object]] = {}
    families: set[str] = set()
    for index, raw in enumerate(_array(value, "targets", 1, MAX_TARGETS)):
        label = f"targets[{index}]"
        target = _object(raw, label)
        _keys(target, {"id", "family", "scope_status", "claim_scope", "fingerprint"}, label)
        target_id = _identifier(target["id"], f"{label}.id")
        family = _enum(target["family"], TARGET_FAMILIES, f"{label}.family")
        _enum(target["scope_status"], SCOPE_STATES, f"{label}.scope_status")
        _text(target["claim_scope"], f"{label}.claim_scope", 800)
        _fingerprint(target["fingerprint"], f"{label}.fingerprint")
        if target_id in targets:
            raise CandorError(f"duplicate target id: {target_id}")
        if family in families:
            raise CandorError(f"v1 permits one explicit target per family: {family}")
        targets[target_id] = target
        families.add(family)
    if families != set(TARGET_FAMILIES):
        raise CandorError(f"targets must cover exactly {list(TARGET_FAMILIES)}")
    return targets


def _validate_capabilities(value: object) -> dict[str, dict[str, object]]:
    capabilities: dict[str, dict[str, object]] = {}
    ordered: list[str] = []
    for index, raw in enumerate(_array(value, "capabilities", 5, MAX_CAPABILITIES)):
        label = f"capabilities[{index}]"
        capability = _object(raw, label)
        _keys(capability, {"id", "required", "statement", "acceptance"}, label)
        capability_id = _identifier(capability["id"], f"{label}.id")
        if type(capability["required"]) is not bool:
            raise CandorError(f"{label}.required must be boolean")
        _text(capability["statement"], f"{label}.statement", 500)
        _unique_texts(capability["acceptance"], f"{label}.acceptance", 1, 8, 500)
        if capability_id in capabilities:
            raise CandorError(f"duplicate capability id: {capability_id}")
        capabilities[capability_id] = capability
        ordered.append(capability_id)
    if tuple(ordered[:5]) != BASELINE_CAPABILITIES:
        raise CandorError("the five baseline capabilities must remain first and ordered")
    for capability_id in BASELINE_CAPABILITIES:
        if capabilities[capability_id]["required"] is not True:
            raise CandorError(f"baseline capability must be required: {capability_id}")
    return capabilities


def _validate_evidence(
    value: object,
    subject: dict[str, object],
    targets: dict[str, dict[str, object]],
    capabilities: dict[str, dict[str, object]],
    manifest_path: Path,
) -> dict[str, dict[str, object]]:
    evidence: dict[str, dict[str, object]] = {}
    expected_environment = {
        "target_scope",
        "os",
        "version",
        "architecture",
        "filesystem",
        "runtime",
        "shell",
        "sandbox",
        "network",
    }
    for index, raw in enumerate(_array(value, "evidence", 0, MAX_EVIDENCE)):
        label = f"evidence[{index}]"
        item = _object(raw, label)
        _keys(
            item,
            {
                "id",
                "subject_revision",
                "subject_artifact_digest",
                "target",
                "receipt_kind",
                "tests",
                "result",
                "observed_on",
                "receipt_uri",
                "receipt_digest",
                "environment",
                "privacy_scrubbed",
                "raw_logs_included",
                "attested",
                "notes",
            },
            label,
        )
        evidence_id = _identifier(item["id"], f"{label}.id")
        if evidence_id in evidence:
            raise CandorError(f"duplicate evidence id: {evidence_id}")
        if item["subject_revision"] != subject["revision"]:
            raise CandorError(f"{label}.subject_revision does not match subject")
        if item["subject_artifact_digest"] != subject["artifact_digest"]:
            raise CandorError(f"{label}.subject_artifact_digest does not match subject")
        target_id = _identifier(item["target"], f"{label}.target")
        if target_id not in targets:
            raise CandorError(f"{label}.target is unknown")
        if targets[target_id]["scope_status"] != "exact":
            raise CandorError(f"{label}.target must have an exact scope")
        declared_receipt_kind = _enum(item["receipt_kind"], RECEIPT_KINDS, f"{label}.receipt_kind")
        tests = _id_list(item["tests"], f"{label}.tests", 1, MAX_CAPABILITIES)
        if any(test not in capabilities for test in tests):
            raise CandorError(f"{label}.tests references an unknown capability")
        declared_result = _enum(item["result"], RESULTS, f"{label}.result")
        declared_date = _date(item["observed_on"], f"{label}.observed_on")
        if declared_date > subject["as_of"]:
            raise CandorError(f"{label}.observed_on cannot be later than subject.as_of")
        locator = _safe_locator(item["receipt_uri"], f"{label}.receipt_uri")
        expected_digest = _digest(item["receipt_digest"], f"{label}.receipt_digest")
        receipt = _receipt_bytes(manifest_path, locator)
        if digest_bytes(receipt) != expected_digest:
            raise CandorError(f"{label}.receipt_digest does not match receipt bytes")
        environment = _object(item["environment"], f"{label}.environment")
        _keys(environment, expected_environment, f"{label}.environment")
        for field in sorted(expected_environment):
            _text(environment[field], f"{label}.environment.{field}", 500)
        target = targets[target_id]
        if environment["target_scope"] != target["claim_scope"]:
            raise CandorError(f"{label}.environment.target_scope does not match target")
        fingerprint = _fingerprint(target["fingerprint"], f"target {target_id}.fingerprint")
        for field in expected_environment - {"target_scope"}:
            if environment[field] != fingerprint[field]:
                raise CandorError(f"{label}.environment.{field} does not match target fingerprint")
        _boolean(item["privacy_scrubbed"], True, f"{label}.privacy_scrubbed")
        _boolean(item["raw_logs_included"], False, f"{label}.raw_logs_included")
        _boolean(item["attested"], False, f"{label}.attested")
        _text(item["notes"], f"{label}.notes", 700)
        _validate_receipt_content(
            receipt,
            label,
            subject,
            target_id,
            declared_receipt_kind,
            tests,
            declared_result,
            declared_date,
            environment,
        )
        evidence[evidence_id] = item
    return evidence


def _validate_now(
    value: object,
    targets: dict[str, dict[str, object]],
    capabilities: dict[str, dict[str, object]],
    evidence: dict[str, dict[str, object]],
) -> dict[tuple[str, str], dict[str, object]]:
    assertions: dict[tuple[str, str], dict[str, object]] = {}
    ids: set[str] = set()
    for index, raw in enumerate(_array(value, "now", 0, MAX_ASSERTIONS)):
        label = f"now[{index}]"
        item = _object(raw, label)
        _keys(item, {"id", "target", "capability", "assertion", "scope", "evidence_refs"}, label)
        assertion_id = _identifier(item["id"], f"{label}.id")
        if assertion_id in ids:
            raise CandorError(f"duplicate NOW id: {assertion_id}")
        ids.add(assertion_id)
        target_id = _identifier(item["target"], f"{label}.target")
        capability_id = _identifier(item["capability"], f"{label}.capability")
        if target_id not in targets or capability_id not in capabilities:
            raise CandorError(f"{label} references an unknown target or capability")
        if targets[target_id]["scope_status"] != "exact":
            raise CandorError(f"{label} cannot assert NOW on a candidate target")
        if item["scope"] != targets[target_id]["claim_scope"]:
            raise CandorError(f"{label}.scope does not match the exact target scope")
        _text(item["assertion"], f"{label}.assertion", 700)
        refs = _id_list(item["evidence_refs"], f"{label}.evidence_refs", 1, 8)
        for reference in refs:
            if reference not in evidence:
                raise CandorError(f"{label} references unknown evidence: {reference}")
            receipt = evidence[reference]
            if receipt["target"] != target_id or receipt["result"] != "pass":
                raise CandorError(f"{label} evidence is not a passing receipt for the same target")
            if capability_id not in receipt["tests"]:
                raise CandorError(f"{label} evidence does not cover capability {capability_id}")
        key = (target_id, capability_id)
        if key in assertions:
            raise CandorError(f"duplicate NOW target/capability pair: {key}")
        assertions[key] = item
    return assertions


def _validate_gaps(
    value: object,
    targets: dict[str, dict[str, object]],
    capabilities: dict[str, dict[str, object]],
    evidence: dict[str, dict[str, object]],
) -> tuple[dict[str, dict[str, object]], dict[tuple[str, str], dict[str, object]]]:
    by_id: dict[str, dict[str, object]] = {}
    by_cell: dict[tuple[str, str], dict[str, object]] = {}
    targets_with_wildcard: set[str] = set()
    targets_with_specific: set[str] = set()
    for index, raw in enumerate(_array(value, "gaps", 0, MAX_ASSERTIONS)):
        label = f"gaps[{index}]"
        item = _object(raw, label)
        _keys(
            item,
            {
                "id",
                "target",
                "capability",
                "kind",
                "impact",
                "statement",
                "evidence_refs",
                "workaround",
                "completeness_claimed",
            },
            label,
        )
        gap_id = _identifier(item["id"], f"{label}.id")
        if gap_id in by_id:
            raise CandorError(f"duplicate GAP id: {gap_id}")
        target_id = _identifier(item["target"], f"{label}.target")
        if target_id not in targets:
            raise CandorError(f"{label}.target is unknown")
        capability = _text(item["capability"], f"{label}.capability", 64)
        if capability != "*" and (not ID.fullmatch(capability) or capability not in capabilities):
            raise CandorError(f"{label}.capability is unknown")
        kind = _enum(item["kind"], GAP_KINDS, f"{label}.kind")
        impact = _enum(item["impact"], GAP_IMPACTS, f"{label}.impact")
        if kind == "unknown" and impact != "unknown":
            raise CandorError(f"{label} unknown GAP must have unknown impact")
        if kind == "excluded" and impact != "excluded":
            raise CandorError(f"{label} excluded GAP must have excluded impact")
        if kind in ("limitation", "known-failure") and impact not in ("narrows", "blocks"):
            raise CandorError(f"{label} {kind} GAP must narrow or block")
        _text(item["statement"], f"{label}.statement", 700)
        refs = _id_list(item["evidence_refs"], f"{label}.evidence_refs", 0, 8)
        for reference in refs:
            if reference not in evidence or evidence[reference]["target"] != target_id:
                raise CandorError(f"{label} evidence must exist for the same target")
        if kind == "known-failure":
            failing = [evidence[reference] for reference in refs if evidence[reference]["result"] in ("fail", "mixed")]
            if not failing:
                raise CandorError(f"{label} known failure needs failed or mixed evidence")
            if capability != "*" and not any(capability in receipt["tests"] for receipt in failing):
                raise CandorError(f"{label} failure evidence does not cover its capability")
        _nullable_text(item["workaround"], f"{label}.workaround", 700)
        _boolean(item["completeness_claimed"], False, f"{label}.completeness_claimed")
        key = (target_id, capability)
        if key in by_cell:
            raise CandorError(f"duplicate GAP target/capability pair: {key}")
        by_id[gap_id] = item
        by_cell[key] = item
        if capability == "*":
            targets_with_wildcard.add(target_id)
        else:
            targets_with_specific.add(target_id)
    overlap = targets_with_wildcard & targets_with_specific
    if overlap:
        raise CandorError(f"v1 does not mix wildcard and specific GAPs for targets: {sorted(overlap)}")
    return by_id, by_cell


def _validate_evidence_consistency(
    evidence: dict[str, dict[str, object]],
    gaps: dict[tuple[str, str], dict[str, object]],
) -> None:
    outcomes: dict[tuple[str, str], set[str]] = {}
    for evidence_id, receipt in evidence.items():
        result = receipt["result"]
        outcome = "pass" if result == "pass" else "failure"
        target = receipt["target"]
        for capability in receipt["tests"]:  # type: ignore[union-attr]
            key = (target, capability)
            outcomes.setdefault(key, set()).add(outcome)  # type: ignore[arg-type]
            if outcome == "failure":
                gap = _gap_for(gaps, target, capability)  # type: ignore[arg-type]
                if (
                    gap is None
                    or gap["kind"] != "known-failure"
                    or evidence_id not in gap["evidence_refs"]
                ):
                    raise CandorError(
                        "failed or mixed evidence must be referenced by a same-target "
                        f"known-failure GAP: {evidence_id} × {capability}"
                    )
    contradictions = sorted(key for key, observed in outcomes.items() if len(observed) > 1)
    if contradictions:
        raise CandorError(f"contradictory pass and failure evidence: {contradictions}")


def _validate_next(value: object, gaps: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    items: dict[str, dict[str, object]] = {}
    for index, raw in enumerate(_array(value, "next", 0, MAX_ASSERTIONS)):
        label = f"next[{index}]"
        item = _object(raw, label)
        _keys(
            item,
            {
                "id",
                "addresses",
                "stage",
                "intention",
                "dependencies",
                "acceptance",
                "commitment",
                "target_date",
                "counts_as_support",
            },
            label,
        )
        next_id = _identifier(item["id"], f"{label}.id")
        if next_id in items:
            raise CandorError(f"duplicate NEXT id: {next_id}")
        addresses = _id_list(item["addresses"], f"{label}.addresses", 1, 8)
        if any(address not in gaps for address in addresses):
            raise CandorError(f"{label}.addresses references an unknown GAP")
        _enum(item["stage"], NEXT_STAGES, f"{label}.stage")
        _text(item["intention"], f"{label}.intention", 700)
        _unique_texts(item["dependencies"], f"{label}.dependencies", 0, 8, 500)
        _unique_texts(item["acceptance"], f"{label}.acceptance", 1, 8, 500)
        _boolean(item["commitment"], False, f"{label}.commitment")
        if item["target_date"] is not None:
            raise CandorError(f"{label}.target_date must be null in v1")
        _boolean(item["counts_as_support"], False, f"{label}.counts_as_support")
        items[next_id] = item
    return items


def _validate_policies(
    value: object,
    targets: dict[str, dict[str, object]],
) -> dict[str, dict[str, object]]:
    policies: dict[str, dict[str, object]] = {}
    ids: set[str] = set()
    for index, raw in enumerate(_array(value, "support_policy", len(targets), len(targets))):
        label = f"support_policy[{index}]"
        item = _object(raw, label)
        _keys(item, {"id", "target", "policy", "scope", "reason"}, label)
        policy_id = _identifier(item["id"], f"{label}.id")
        if policy_id in ids:
            raise CandorError(f"duplicate support policy id: {policy_id}")
        ids.add(policy_id)
        target_id = _identifier(item["target"], f"{label}.target")
        if target_id not in targets or target_id in policies:
            raise CandorError(f"{label}.target must be unique and known")
        _enum(item["policy"], SUPPORT_POLICIES, f"{label}.policy")
        if item["scope"] != targets[target_id]["claim_scope"]:
            raise CandorError(f"{label}.scope does not match target")
        _text(item["reason"], f"{label}.reason", 700)
        policies[target_id] = item
    if set(policies) != set(targets):
        raise CandorError("support_policy must cover every target exactly once")
    return policies


def _gap_for(
    gaps: dict[tuple[str, str], dict[str, object]],
    target: str,
    capability: str,
) -> dict[str, object] | None:
    return gaps.get((target, capability)) or gaps.get((target, "*"))


def _derive_statuses(value: dict[str, object]) -> dict[str, str]:
    capabilities = {item["id"]: item for item in value["capabilities"]}  # type: ignore[index]
    required = [item["id"] for item in value["capabilities"] if item["required"]]  # type: ignore[index]
    now = {(item["target"], item["capability"]): item for item in value["now"]}  # type: ignore[index]
    gaps = {(item["target"], item["capability"]): item for item in value["gaps"]}  # type: ignore[index]
    policies = {item["target"]: item for item in value["support_policy"]}  # type: ignore[index]
    statuses: dict[str, str] = {}
    for target in value["targets"]:  # type: ignore[index]
        target_id = target["id"]
        policy = policies[target_id]["policy"]
        unsupported = policy == "not-supported"
        unknown = policy == "undecided"
        constrained = policy == "best-effort"
        for capability in required:
            assertion = now.get((target_id, capability))
            gap = _gap_for(gaps, target_id, capability)
            if assertion is None:
                if gap and gap["impact"] in ("blocks", "excluded"):
                    unsupported = True
                else:
                    unknown = True
            if gap:
                if gap["impact"] in ("blocks", "excluded"):
                    unsupported = True
                elif gap["impact"] == "narrows":
                    constrained = True
                elif gap["impact"] == "unknown":
                    unknown = True
        if unsupported:
            status = "NOT_SUPPORTED"
        elif unknown:
            status = "UNKNOWN"
        elif constrained:
            status = "CONSTRAINED"
        elif policy == "supported":
            status = "VERIFIED"
        else:
            status = "UNKNOWN"
        if status not in PUBLIC_STATUSES or not capabilities:
            raise CandorError("internal status derivation failed")
        statuses[target_id] = status
    return statuses


def validate_manifest(value: dict[str, object], manifest_path: Path) -> None:
    _keys(
        value,
        {
            "schema",
            "subject",
            "baseline",
            "targets",
            "capabilities",
            "now",
            "gaps",
            "next",
            "support_policy",
            "evidence",
            "boundaries",
            "non_claims",
        },
        "manifest",
    )
    if value["schema"] != SCHEMA_ID:
        raise CandorError(f"schema must be {SCHEMA_ID}")
    subject = _validate_subject(value["subject"])
    _validate_baseline(value["baseline"])
    targets = _validate_targets(value["targets"])
    capabilities = _validate_capabilities(value["capabilities"])
    evidence = _validate_evidence(value["evidence"], subject, targets, capabilities, manifest_path)
    now = _validate_now(value["now"], targets, capabilities, evidence)
    gaps_by_id, gaps_by_cell = _validate_gaps(value["gaps"], targets, capabilities, evidence)
    _validate_evidence_consistency(evidence, gaps_by_cell)
    _validate_next(value["next"], gaps_by_id)
    policies = _validate_policies(value["support_policy"], targets)

    for target_id in targets:
        for capability_id in capabilities:
            if (target_id, capability_id) not in now and _gap_for(gaps_by_cell, target_id, capability_id) is None:
                raise CandorError(f"silent matrix cell: {target_id} × {capability_id}")

    boundaries = _object(value["boundaries"], "boundaries")
    _keys(boundaries, set(BOUNDARIES), "boundaries")
    for field, expected in BOUNDARIES.items():
        _boolean(boundaries[field], expected, f"boundaries.{field}")
    claims = _unique_texts(value["non_claims"], "non_claims", len(NON_CLAIMS), len(NON_CLAIMS), 500)
    if tuple(claims) != NON_CLAIMS:
        raise CandorError("non_claims changed or reordered")

    statuses = _derive_statuses(value)
    for target_id, policy in policies.items():
        if policy["policy"] == "supported" and statuses[target_id] != "VERIFIED":
            raise CandorError(f"supported policy lacks a fully VERIFIED target: {target_id}")


def load_manifest(path: Path) -> dict[str, object]:
    manifest_path = path.expanduser().absolute()
    value = parse_object(read_regular(manifest_path, "support manifest", MAX_MANIFEST_BYTES), "support manifest")
    validate_manifest(value, manifest_path)
    return value


def _build_receipt(value: dict[str, object]) -> dict[str, object]:
    statuses = _derive_statuses(value)
    return {
        "schema": "kingdom.support-candor.receipt/v1",
        "status": "valid",
        "subject": value["subject"]["id"],  # type: ignore[index]
        "subject_revision": value["subject"]["revision"],  # type: ignore[index]
        "manifest_sha256": digest_value(value),
        "targets": statuses,
        "counts": {
            "capabilities": len(value["capabilities"]),  # type: ignore[arg-type]
            "now": len(value["now"]),  # type: ignore[arg-type]
            "gaps": len(value["gaps"]),  # type: ignore[arg-type]
            "next": len(value["next"]),  # type: ignore[arg-type]
            "evidence": len(value["evidence"]),  # type: ignore[arg-type]
            "target_statuses": dict(sorted(Counter(statuses.values()).items())),
        },
        "next_counts_as_support": False,
        "network_calls": False,
        "subprocesses": False,
        "storage_writes": False,
        "external_actions": False,
    }


def _markdown(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _render_manifest(value: dict[str, object]) -> str:
    statuses = _derive_statuses(value)
    policies = {item["target"]: item for item in value["support_policy"]}  # type: ignore[index]
    now_counts = Counter(item["target"] for item in value["now"])  # type: ignore[index]
    gap_counts = Counter(item["target"] for item in value["gaps"])  # type: ignore[index]
    next_by_gap: Counter[str] = Counter()
    gap_targets = {item["id"]: item["target"] for item in value["gaps"]}  # type: ignore[index]
    for item in value["next"]:  # type: ignore[index]
        for address in item["addresses"]:
            next_by_gap[gap_targets[address]] += 1

    subject = value["subject"]  # type: ignore[assignment]
    lines = [
        f"# Support Candor · {_markdown(subject['id'])}",
        "",
        f"Exact revision: `{_markdown(subject['revision'])}`",
        f"Artifact: `{_markdown(subject['artifact_digest'])}`",
        f"As of: `{_markdown(subject['as_of'])}`",
        f"Manifest: `{digest_value(value)}`",
        "",
        "> NOW is evidence-scoped. GAP is not exhaustive. NEXT never counts as support.",
        "",
        "| Exact target | Scope | Policy | Derived NOW | Assertions | GAP records | NEXT items |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for target in value["targets"]:  # type: ignore[index]
        target_id = target["id"]
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{_markdown(target_id)}`",
                    _markdown(target["scope_status"]),
                    _markdown(policies[target_id]["policy"]),
                    f"**{statuses[target_id]}**",
                    str(now_counts[target_id]),
                    str(gap_counts[target_id]),
                    str(next_by_gap[target_id]),
                ]
            )
            + " |"
        )

    lines.extend(["", "## NOW · demonstrated under exact evidence", ""])
    if value["now"]:
        for item in value["now"]:  # type: ignore[index]
            lines.append(
                f"- **{_markdown(item['target'])} / {_markdown(item['capability'])}:** "
                f"{_markdown(item['assertion'])} — evidence `{', '.join(item['evidence_refs'])}`"
            )
    else:
        lines.append("- No current assertions.")

    lines.extend(["", "## GAP · where the claim ends", ""])
    for item in value["gaps"]:  # type: ignore[index]
        workaround = f" Workaround: {_markdown(item['workaround'])}" if item["workaround"] else ""
        lines.append(
            f"- **{_markdown(item['target'])} / {_markdown(item['capability'])} · "
            f"{_markdown(item['kind'])} / {_markdown(item['impact'])}:** "
            f"{_markdown(item['statement'])}.{workaround}"
        )

    lines.extend(["", "## NEXT · intention only", ""])
    if value["next"]:
        for item in value["next"]:  # type: ignore[index]
            lines.append(
                f"- **{_markdown(item['stage'])}:** {_markdown(item['intention'])} "
                f"(addresses `{', '.join(item['addresses'])}`; commitment: false; counts as support: false)"
            )
    else:
        lines.append("- No declared next direction.")

    lines.extend(["", "## Non-claims", ""])
    lines.extend(f"- {_markdown(claim)}" for claim in value["non_claims"])  # type: ignore[index]
    return "\n".join(lines) + "\n"


def check_path(path: Path) -> dict[str, object]:
    return _build_receipt(load_manifest(path))


def render_path(path: Path) -> str:
    return _render_manifest(load_manifest(path))


def digest_path(path: Path) -> str:
    return digest_value(load_manifest(path))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Validate an evidence-scoped support ledger.")
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("check", "render", "digest"):
        command = commands.add_parser(name)
        command.add_argument("manifest", type=Path)
    return root


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        if arguments.command == "check":
            print(
                json.dumps(
                    check_path(arguments.manifest),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
        elif arguments.command == "render":
            print(render_path(arguments.manifest), end="")
        else:
            print(digest_path(arguments.manifest))
        return 0
    except (CandorError, OSError) as error:
        print(f"support-candor: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
