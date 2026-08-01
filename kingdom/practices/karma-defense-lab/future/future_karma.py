#!/usr/bin/env python3
"""Deterministic, offline planner for bounded future-Kingdom KARMA rehearsals."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any

sys.dont_write_bytecode = True

ENGINE = "future-karma/1"
EVENT_SCHEMA = "kingdom.karma.event/v1"
RECEIPT_SCHEMA = "kingdom.karma.receipt/v1"
VERIFY_SCHEMA = "kingdom.karma.verify/v1"
TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$", re.ASCII)
TEST_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$", re.ASCII)
RESOURCE_PART_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$", re.ASCII)
BASE = Path(os.path.abspath(__file__)).parent
LAB_BASE = BASE.parent
ALLOWED_ACTIONS = (
    "allow",
    "observe",
    "throttle",
    "deny",
    "quarantine",
    "synthetic-mirror",
)
EXPECTED_LIMITS = MappingProxyType({
    "max_event_bytes": 2048,
    "max_verify_bytes": 16384,
    "max_nodes": 40,
    "max_depth": 5,
    "max_evidence_count": 4,
    "max_attempts": 1,
})
EXPECTED_DEFAULT = MappingProxyType({
    "action": "quarantine",
    "fallback": "deny",
    "severity": 5,
    "halt_code": "unmatched-selector",
})
EXPECTED_LOVE = MappingProxyType({
    "posture": "care-with-boundaries",
    "heartbrick_candidate": True,
    "love_letter_candidate": True,
    "publication_authorized": False,
    "public_counter_delta": 0,
    "source_text_reflected": False,
    "attribution": "none",
    "review": "human-required",
})
ZERO_EFFECTS = MappingProxyType({
    "network_calls": 0,
    "process_spawns": 0,
    "model_calls": 0,
    "secret_reads": 0,
    "filesystem_writes": 0,
    "external_messages": 0,
})
EVENT_KEYS = (
    "schema",
    "surface",
    "mechanism",
    "signal",
    "signal_quality",
    "provenance",
    "novelty",
    "purpose",
    "scope",
    "authority",
    "evidence_count",
)
RULE_KEYS = (
    "id",
    "threat_id",
    "selector",
    "min_evidence",
    "action",
    "fallback",
    "severity",
    "mirror_mode",
    "rationale",
)
THREAT_KEYS = (
    "id",
    "title",
    "entry_point",
    "assets",
    "prevention",
    "detection",
    "containment",
    "recovery",
    "privacy_output",
    "evidence_status",
    "test_ids",
)
PINS = MappingProxyType({
    "policy.json": "7c566a11f1330eaa1093e7ad093627c1f79e7cb032962a078f6b348896733004",
    "event.schema.json": "8299d74eafbf86e8a208a1687c442ed8f4e01fc2a5f1b91a9c7662731ab57247",
    "policy.schema.json": "9bb12132b4e16ea01582a5c04d1f88f8869381cbf20e022545f9fc6a57f3479c",
    "receipt.schema.json": "f6e27f93891a53ab23fc2ba78941b94954ec441a9df5e7f917cec0ace7526124",
    "threat-model.json": "c20e2fff39494f908f07339c6d2bfc2805af0d79071a946e6f1752b8391e1c7b",
    "threat-model.schema.json": "506e3db53c9e36cd54668b188511dedc280c6ca2fc1cfbe471abd1cba9db5c5d",
    "examples/adversarial-corpus.json": "6e1f019b5682c84cf7363b77bf9b093a88e3dc5f388a17223371e674d940d0ec",
})
STABLE_CORE_PIN = "d3ab31c7f68da45da58aeb4252568ad47ed0577a7e569d098c23128777a8a8d3"
POLICY_CANONICAL_PIN = "dd63d0d103038701870531f344576cf85d4d686c041b53e2c86f82e84afe511f"
NONCLAIMS = (
    "Offline synthetic planning is not live efficacy or deployment.",
    "A digest proves deterministic self-consistency, not authentic external provenance.",
    "The caller owns concurrency, deduplication, audience, expiry, retention, and deletion.",
    "No receipt attributes identity, intent, guilt, or authority.",
    "Synthetic mirror means a local sterile candidate with no egress or publication.",
)

_BUNDLE_TOKEN = object()


class KarmaError(Exception):
    """Base class for fixed-diagnostic failures."""


class InvalidInput(KarmaError):
    """Input was malformed or outside the closed event contract."""


class InvalidBundle(KarmaError):
    """A pinned local source or catalog failed validation."""


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(child) for child in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_thaw(child) for child in value]
    return value


class Bundle:
    """Recursively immutable carrier; content is revalidated at trust entries."""

    __slots__ = ("__data",)

    def __init__(self, data: dict[str, Any], token: object) -> None:
        if token is not _BUNDLE_TOKEN:
            raise InvalidBundle()
        object.__setattr__(self, "_Bundle__data", _freeze(data))

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise TypeError("Bundle is immutable")

    def __getitem__(self, key: str) -> Any:
        return self.__data[key]


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        .encode("ascii")
    )


def _digest(value: Any) -> str:
    payload = value if isinstance(value, bytes) else _canonical(value)
    return hashlib.sha256(payload).hexdigest()


def _exact_keys(value: Any, keys: list[str], error: type[KarmaError]) -> None:
    if not isinstance(value, dict) or set(value) != set(keys):
        raise error()


def _is_ascii_text(value: Any, *, minimum: int = 1, maximum: int = 256) -> bool:
    if not isinstance(value, str) or not minimum <= len(value) <= maximum:
        return False
    return all(0x20 <= ord(char) <= 0x7E for char in value)


def _is_token(value: Any) -> bool:
    return isinstance(value, str) and TOKEN_RE.fullmatch(value) is not None


def _walk(value: Any, *, max_nodes: int, max_depth: int) -> None:
    nodes = 0

    def visit(item: Any, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > max_nodes or depth > max_depth:
            raise InvalidInput()
        if isinstance(item, dict):
            for key, child in item.items():
                if not _is_ascii_text(key, maximum=80):
                    raise InvalidInput()
                visit(child, depth + 1)
        elif isinstance(item, list):
            for child in item:
                visit(child, depth + 1)
        elif isinstance(item, str):
            if not _is_ascii_text(item, minimum=0, maximum=4096):
                raise InvalidInput()
        elif item is None or isinstance(item, (bool, int)):
            return
        else:
            raise InvalidInput()

    visit(value, 0)


def _decode_json(
    payload: bytes, *, max_bytes: int, max_nodes: int, max_depth: int
) -> Any:
    if not isinstance(payload, bytes) or not 0 < len(payload) <= max_bytes:
        raise InvalidInput()
    try:
        text = payload.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise InvalidInput() from exc

    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise InvalidInput()
            result[key] = value
        return result

    def reject_number(_: str) -> Any:
        raise InvalidInput()

    try:
        value = json.loads(
            text,
            object_pairs_hook=pairs_hook,
            parse_float=reject_number,
            parse_constant=reject_number,
        )
    except (json.JSONDecodeError, UnicodeError, ValueError, InvalidInput) as exc:
        raise InvalidInput() from exc
    _walk(value, max_nodes=max_nodes, max_depth=max_depth)
    return value


def _assert_physical_directory(root: Path) -> Path:
    absolute = Path(os.path.abspath(root))
    try:
        resolved = Path(os.path.realpath(absolute, strict=True))
        info = os.lstat(absolute)
    except (OSError, ValueError) as exc:
        raise InvalidBundle() from exc
    if absolute != resolved or stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise InvalidBundle()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        try:
            part_info = os.lstat(current)
        except OSError as exc:
            raise InvalidBundle() from exc
        if stat.S_ISLNK(part_info.st_mode):
            raise InvalidBundle()
    return absolute


def _safe_read_regular(
    root: Path,
    relative_name: str,
    *,
    expected_digest: str | None,
    max_bytes: int = 262144,
) -> bytes:
    physical_root = _assert_physical_directory(root)
    relative = PurePosixPath(relative_name)
    if (
        relative.is_absolute()
        or not relative.parts
        or any(
            part in {"", ".", ".."} or RESOURCE_PART_RE.fullmatch(part) is None
            for part in relative.parts
        )
    ):
        raise InvalidBundle()
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_DIRECTORY", 0)
    )
    file_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    directory_descriptors: list[int] = []
    descriptor: int | None = None
    try:
        root_before = os.lstat(physical_root)
        root_descriptor = os.open(physical_root, directory_flags)
        directory_descriptors.append(root_descriptor)
        root_open = os.fstat(root_descriptor)
        if (
            not stat.S_ISDIR(root_open.st_mode)
            or (root_before.st_dev, root_before.st_ino)
            != (root_open.st_dev, root_open.st_ino)
        ):
            raise InvalidBundle()
        parent_descriptor = root_descriptor
        for part in relative.parts[:-1]:
            child_descriptor = os.open(
                part, directory_flags, dir_fd=parent_descriptor
            )
            directory_descriptors.append(child_descriptor)
            child_info = os.fstat(child_descriptor)
            if (
                not stat.S_ISDIR(child_info.st_mode)
                or child_info.st_dev != root_open.st_dev
            ):
                raise InvalidBundle()
            parent_descriptor = child_descriptor
        descriptor = os.open(
            relative.parts[-1], file_flags, dir_fd=parent_descriptor
        )
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_dev != root_open.st_dev
            or before.st_size < 1
            or before.st_size > max_bytes
        ):
            raise InvalidBundle()
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(65536, remaining))
            if not chunk:
                raise InvalidBundle()
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise InvalidBundle()
        after = os.fstat(descriptor)
        identity_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        identity_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        if identity_before != identity_after:
            raise InvalidBundle()
        payload = b"".join(chunks)
    except OSError as exc:
        raise InvalidBundle() from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        for directory_descriptor in reversed(directory_descriptors):
            os.close(directory_descriptor)
    if expected_digest is not None and _digest(payload) != expected_digest:
        raise InvalidBundle()
    return payload


def validate_event(event: Any) -> dict[str, Any]:
    _walk(event, max_nodes=EXPECTED_LIMITS["max_nodes"], max_depth=EXPECTED_LIMITS["max_depth"])
    _exact_keys(event, EVENT_KEYS, InvalidInput)
    if event["schema"] != EVENT_SCHEMA:
        raise InvalidInput()
    for key in ("surface", "mechanism", "signal"):
        if not _is_token(event[key]):
            raise InvalidInput()
    if event["signal_quality"] not in {"confirmed", "ambiguous", "unknown"}:
        raise InvalidInput()
    if event["provenance"] not in {"pinned", "unpinned", "unknown"}:
        raise InvalidInput()
    if event["novelty"] not in {"known", "novel", "ambiguous"}:
        raise InvalidInput()
    if (
        event["purpose"] != "defensive-regression"
        or event["scope"] != "offline-synthetic"
        or event["authority"] != "none"
    ):
        raise InvalidInput()
    count = event["evidence_count"]
    if type(count) is not int or not 0 <= count <= EXPECTED_LIMITS["max_evidence_count"]:
        raise InvalidInput()
    return event


def validate_policy(policy: Any) -> dict[str, Any]:
    _exact_keys(
        policy,
        ["schema", "policy_id", "actions", "limits", "default", "love", "effects", "rules"],
        InvalidBundle,
    )
    if (
        policy["schema"] != "kingdom.karma.policy/v1"
        or not _is_token(policy["policy_id"])
        or not isinstance(policy["actions"], list)
        or tuple(policy["actions"]) != ALLOWED_ACTIONS
        or policy["limits"] != EXPECTED_LIMITS
        or policy["default"] != EXPECTED_DEFAULT
        or policy["love"] != EXPECTED_LOVE
        or policy["effects"] != ZERO_EFFECTS
        or not isinstance(policy["rules"], list)
        or not 16 <= len(policy["rules"]) <= 64
    ):
        raise InvalidBundle()
    ids: set[str] = set()
    selectors: set[tuple[str, str, str]] = set()
    for rule in policy["rules"]:
        _exact_keys(rule, RULE_KEYS, InvalidBundle)
        _exact_keys(rule["selector"], ["surface", "mechanism", "signal"], InvalidBundle)
        if not _is_token(rule["id"]) or not _is_token(rule["threat_id"]):
            raise InvalidBundle()
        selector = tuple(rule["selector"][key] for key in ("surface", "mechanism", "signal"))
        if not all(_is_token(value) for value in selector):
            raise InvalidBundle()
        if rule["id"] in ids or selector in selectors:
            raise InvalidBundle()
        ids.add(rule["id"])
        selectors.add(selector)
        if (
            type(rule["min_evidence"]) is not int
            or not 0 <= rule["min_evidence"] <= EXPECTED_LIMITS["max_evidence_count"]
            or rule["action"] not in ALLOWED_ACTIONS
            or rule["fallback"] not in {"deny", "quarantine"}
            or type(rule["severity"]) is not int
            or not 0 <= rule["severity"] <= 5
            or not _is_ascii_text(rule["rationale"], maximum=160)
        ):
            raise InvalidBundle()
        expected_mirror = "isolated-no-egress" if rule["action"] == "synthetic-mirror" else "none"
        if rule["mirror_mode"] != expected_mirror:
            raise InvalidBundle()
        if rule["action"] == "allow" and (
            rule["id"] != "control-nominal" or rule["severity"] != 0
        ):
            raise InvalidBundle()
    return policy


def validate_threat_model(model: Any, policy: dict[str, Any]) -> dict[str, Any]:
    _exact_keys(model, ["schema", "model_id", "scope", "nonclaims", "classes"], InvalidBundle)
    if (
        model["schema"] != "kingdom.karma.threat-model/v1"
        or not _is_token(model["model_id"])
        or model["scope"] != "offline-synthetic-planning-only"
        or not isinstance(model["nonclaims"], list)
        or len(model["nonclaims"]) < 3
        or not all(_is_ascii_text(item, maximum=220) for item in model["nonclaims"])
        or not isinstance(model["classes"], list)
        or len(model["classes"]) < 12
    ):
        raise InvalidBundle()
    threat_ids: set[str] = set()
    test_ids: set[str] = set()
    for item in model["classes"]:
        _exact_keys(item, THREAT_KEYS, InvalidBundle)
        if not _is_token(item["id"]) or item["id"] in threat_ids:
            raise InvalidBundle()
        threat_ids.add(item["id"])
        if item["evidence_status"] not in {"observed", "inferred", "unknown"}:
            raise InvalidBundle()
        for key in (
            "title",
            "entry_point",
            "prevention",
            "detection",
            "containment",
            "recovery",
            "privacy_output",
        ):
            if not _is_ascii_text(item[key], maximum=240):
                raise InvalidBundle()
        if (
            not isinstance(item["assets"], list)
            or not item["assets"]
            or not all(_is_ascii_text(value, maximum=120) for value in item["assets"])
            or not isinstance(item["test_ids"], list)
            or not item["test_ids"]
            or not all(
                isinstance(value, str) and TEST_ID_RE.fullmatch(value) is not None
                for value in item["test_ids"]
            )
        ):
            raise InvalidBundle()
        test_ids.update(item["test_ids"])
    policy_threats = {rule["threat_id"] for rule in policy["rules"]}
    if policy_threats != threat_ids or not test_ids:
        raise InvalidBundle()
    return model


def _schema_contracts(schemas: dict[str, Any]) -> None:
    expected_ids = {
        "event.schema.json": EVENT_SCHEMA,
        "policy.schema.json": "kingdom.karma.policy/v1",
        "receipt.schema.json": RECEIPT_SCHEMA,
        "threat-model.schema.json": "kingdom.karma.threat-model/v1",
    }
    for name, expected_id in expected_ids.items():
        schema = schemas[name]
        if (
            not isinstance(schema, dict)
            or schema.get("$id") != expected_id
            or schema.get("type") != "object"
            or schema.get("additionalProperties") is not False
            or not isinstance(schema.get("required"), list)
            or not isinstance(schema.get("properties"), dict)
            or set(schema["required"]) != set(schema["properties"])
        ):
            raise InvalidBundle()
    event_schema = schemas["event.schema.json"]
    if set(event_schema["required"]) != set(EVENT_KEYS):
        raise InvalidBundle()


def validate_corpus(corpus: Any, policy: dict[str, Any]) -> dict[str, Any]:
    _exact_keys(corpus, ["schema", "corpus_id", "cases"], InvalidBundle)
    if (
        corpus["schema"] != "kingdom.karma.corpus/v1"
        or not _is_token(corpus["corpus_id"])
        or not isinstance(corpus["cases"], list)
    ):
        raise InvalidBundle()
    by_id = {rule["id"]: rule for rule in policy["rules"]}
    seen: set[str] = set()
    case_ids: set[str] = set()
    for case in corpus["cases"]:
        _exact_keys(
            case,
            ["id", "threat_id", "rule_id", "event", "expected_action", "expected_halted"],
            InvalidBundle,
        )
        if (
            not _is_token(case["id"])
            or case["id"] in case_ids
            or case["rule_id"] not in by_id
            or case["rule_id"] in seen
            or type(case["expected_halted"]) is not bool
        ):
            raise InvalidBundle()
        case_ids.add(case["id"])
        seen.add(case["rule_id"])
        try:
            event = validate_event(case["event"])
        except InvalidInput as exc:
            raise InvalidBundle() from exc
        rule = by_id[case["rule_id"]]
        selector = tuple(event[key] for key in ("surface", "mechanism", "signal"))
        rule_selector = tuple(rule["selector"][key] for key in ("surface", "mechanism", "signal"))
        if (
            selector != rule_selector
            or case["threat_id"] != rule["threat_id"]
            or case["expected_action"] != rule["action"]
            or case["expected_halted"] is not False
            or event["evidence_count"] < rule["min_evidence"]
        ):
            raise InvalidBundle()
    if seen != set(by_id):
        raise InvalidBundle()
    return corpus


def load_bundle() -> Bundle:
    raw: dict[str, bytes] = {}
    for name, expected in PINS.items():
        raw[name] = _safe_read_regular(BASE, name, expected_digest=expected)
    core = _safe_read_regular(
        LAB_BASE,
        "karma_defense_lab.py",
        expected_digest=STABLE_CORE_PIN,
        max_bytes=131072,
    )
    engine_source = _safe_read_regular(
        BASE, "future_karma.py", expected_digest=None, max_bytes=131072
    )
    decoded: dict[str, Any] = {}
    for name, payload in raw.items():
        try:
            decoded[name] = _decode_json(
                payload, max_bytes=262144, max_nodes=12000, max_depth=20
            )
        except InvalidInput as exc:
            raise InvalidBundle() from exc
    policy = validate_policy(decoded["policy.json"])
    schemas = {
        name: decoded[name]
        for name in (
            "event.schema.json",
            "policy.schema.json",
            "receipt.schema.json",
            "threat-model.schema.json",
        )
    }
    _schema_contracts(schemas)
    threat_model = validate_threat_model(decoded["threat-model.json"], policy)
    corpus = validate_corpus(decoded["examples/adversarial-corpus.json"], policy)
    bindings = {
        "engine_sha256": _digest(engine_source),
        "stable_core_sha256": _digest(core),
        "policy_sha256": _digest(raw["policy.json"]),
        "event_schema_sha256": _digest(raw["event.schema.json"]),
        "policy_schema_sha256": _digest(raw["policy.schema.json"]),
        "receipt_schema_sha256": _digest(raw["receipt.schema.json"]),
        "threat_model_sha256": _digest(raw["threat-model.json"]),
        "threat_model_schema_sha256": _digest(raw["threat-model.schema.json"]),
        "corpus_sha256": _digest(raw["examples/adversarial-corpus.json"]),
    }
    return Bundle(
        {
            "policy": policy,
            "threat_model": threat_model,
            "corpus": corpus,
            "schemas": schemas,
            "bindings": bindings,
        },
        _BUNDLE_TOKEN,
    )


def _validate_planning_bundle(
    bundle: Bundle,
) -> tuple[dict[str, Any], dict[str, str]]:
    if type(bundle) is not Bundle:
        raise InvalidBundle()
    try:
        policy = _thaw(bundle["policy"])
        bindings = _thaw(bundle["bindings"])
    except (KeyError, TypeError) as exc:
        raise InvalidBundle() from exc
    validate_policy(policy)
    if _digest(policy) != POLICY_CANONICAL_PIN:
        raise InvalidBundle()
    expected_static = {
        "stable_core_sha256": STABLE_CORE_PIN,
        "policy_sha256": PINS["policy.json"],
        "event_schema_sha256": PINS["event.schema.json"],
        "policy_schema_sha256": PINS["policy.schema.json"],
        "receipt_schema_sha256": PINS["receipt.schema.json"],
        "threat_model_sha256": PINS["threat-model.json"],
        "threat_model_schema_sha256": PINS["threat-model.schema.json"],
        "corpus_sha256": PINS["examples/adversarial-corpus.json"],
    }
    _exact_keys(
        bindings,
        ["engine_sha256", *expected_static],
        InvalidBundle,
    )
    if any(bindings[key] != value for key, value in expected_static.items()):
        raise InvalidBundle()
    current_engine = _safe_read_regular(
        BASE, "future_karma.py", expected_digest=None, max_bytes=131072
    )
    if bindings["engine_sha256"] != _digest(current_engine):
        raise InvalidBundle()
    return policy, bindings


def _halt_decision(code: str) -> dict[str, Any]:
    return {
        "rule_id": "none",
        "threat_id": "none",
        "action": "quarantine",
        "fallback": "deny",
        "severity": 5,
        "halt_code": code,
        "mirror": {"mode": "none", "max_attempts": 0, "egress": False},
    }


def plan_event(event: dict[str, Any], bundle: Bundle) -> dict[str, Any]:
    policy, bindings = _validate_planning_bundle(bundle)
    event = validate_event(event)
    selector = tuple(event[key] for key in ("surface", "mechanism", "signal"))
    matches = [
        rule
        for rule in policy["rules"]
        if tuple(rule["selector"][key] for key in ("surface", "mechanism", "signal"))
        == selector
    ]
    safe_boundary = (
        event["signal_quality"] == "confirmed"
        and event["provenance"] == "pinned"
        and event["novelty"] == "known"
    )
    if len(matches) != 1:
        decision = _halt_decision("unmatched-selector")
        status_value = "halted"
        classification = "unmatched-categorical"
    elif not safe_boundary:
        decision = _halt_decision("boundary-uncertain")
        status_value = "halted"
        classification = "uncertain-categorical"
    elif event["evidence_count"] < matches[0]["min_evidence"]:
        decision = _halt_decision("insufficient-evidence")
        status_value = "halted"
        classification = "insufficient-categorical"
    else:
        rule = matches[0]
        mirror_attempts = 1 if rule["action"] == "synthetic-mirror" else 0
        decision = {
            "rule_id": rule["id"],
            "threat_id": rule["threat_id"],
            "action": rule["action"],
            "fallback": rule["fallback"],
            "severity": rule["severity"],
            "halt_code": "none",
            "mirror": {
                "mode": rule["mirror_mode"],
                "max_attempts": mirror_attempts,
                "egress": False,
            },
        }
        status_value = "planned"
        classification = "reviewed-categorical"
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "engine": ENGINE,
        "status": status_value,
        "bindings": bindings,
        "event": {
            "digest": _digest(event),
            "classification": classification,
            "raw_retained": False,
        },
        "decision": decision,
        "controls": {
            "actual_effects": dict(ZERO_EFFECTS),
            "authority_granted": False,
            "public_output": False,
            "retention": {
                "event": "digest-only",
                "receipt": "caller-owned-review-only",
                "deletion_enforced": False,
            },
            "replay": {
                "mode": "stateless-exact",
                "dedupe_owner": "caller",
                "audience_owner": "caller",
                "expiry_owner": "caller",
            },
        },
        "love": dict(EXPECTED_LOVE),
        "nonclaims": list(NONCLAIMS),
    }
    receipt["receipt_digest"] = _digest(receipt)
    return receipt


def verify_receipt(
    event: dict[str, Any], receipt: Any, bundle: Bundle
) -> bool:
    if type(bundle) is not Bundle:
        return False
    if not isinstance(receipt, dict):
        return False
    try:
        expected = plan_event(event, bundle)
    except InvalidInput:
        return False
    return _canonical(receipt) == _canonical(expected)


def _check(bundle: Bundle) -> None:
    for case in bundle["corpus"]["cases"]:
        event = _thaw(case["event"])
        receipt = plan_event(event, bundle)
        if (
            receipt["decision"]["rule_id"] != case["rule_id"]
            or receipt["decision"]["threat_id"] != case["threat_id"]
            or receipt["decision"]["action"] != case["expected_action"]
            or (receipt["status"] == "halted") != case["expected_halted"]
            or not verify_receipt(event, receipt, bundle)
        ):
            raise InvalidBundle()


def _read_stdin(limit: int) -> bytes:
    payload = sys.stdin.buffer.read(limit + 1)
    if len(payload) > limit:
        raise InvalidInput()
    return payload


def _emit_json(value: Any) -> None:
    sys.stdout.buffer.write(_canonical(value) + b"\n")


def _usage() -> int:
    sys.stderr.write("usage: future_karma.py {check|digest|plan|verify}\n")
    return 2


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in {"check", "digest", "plan", "verify"}:
        return _usage()
    command = argv[1]
    try:
        bundle = load_bundle()
    except KarmaError:
        sys.stderr.write("future-karma: bundle-invalid\n")
        return 2
    if command == "check":
        try:
            _check(bundle)
        except KarmaError:
            sys.stderr.write("future-karma: check-failed\n")
            return 2
        sys.stdout.write("future-karma: ok\n")
        return 0
    if command == "digest":
        _emit_json(
            {
                "schema": "kingdom.karma.bindings/v1",
                "engine": ENGINE,
                "policy_id": bundle["policy"]["policy_id"],
                "bindings": dict(bundle["bindings"]),
            }
        )
        return 0
    if command == "plan":
        try:
            event = _decode_json(
                _read_stdin(EXPECTED_LIMITS["max_event_bytes"]),
                max_bytes=EXPECTED_LIMITS["max_event_bytes"],
                max_nodes=EXPECTED_LIMITS["max_nodes"],
                max_depth=EXPECTED_LIMITS["max_depth"],
            )
            receipt = plan_event(event, bundle)
        except InvalidInput:
            sys.stderr.write("future-karma: invalid-input\n")
            return 2
        _emit_json(receipt)
        return 0
    try:
        wrapper = _decode_json(
            _read_stdin(EXPECTED_LIMITS["max_verify_bytes"]),
            max_bytes=EXPECTED_LIMITS["max_verify_bytes"],
            max_nodes=500,
            max_depth=16,
        )
        _exact_keys(wrapper, ["schema", "event", "receipt"], InvalidInput)
        if wrapper["schema"] != VERIFY_SCHEMA:
            raise InvalidInput()
        valid = verify_receipt(wrapper["event"], wrapper["receipt"], bundle)
    except InvalidInput:
        valid = False
    sys.stdout.write("true\n" if valid else "false\n")
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
