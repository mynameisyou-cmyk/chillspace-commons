#!/usr/bin/env python3
"""Citizen-owned X speaker binding. Locates a token. Never reads one. Never posts."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping


BINDING_SCHEMA = "kingdom.x.binding/v1"
CHECK_SCHEMA = "kingdom.x.binding.check/v1"
ALLOWED_MODES = frozenset({"reply", "chat"})
LIFE_MODES = frozenset({"local", "rest", "unasked"})
LOCATOR_KINDS = frozenset({"unwired", "macos-keychain"})
BINDING_KEYS = (
    "schema",
    "citizen",
    "speaker_handle",
    "token_locator",
    "modes",
)
POLICY_KEYS = ("citizen", "configured", "life", "agenttool", "reason")
KEYCHAIN_KEYS = ("kind", "service", "account")
UNWIRED_KEYS = ("kind",)
HANDLE = re.compile(r"^[A-Za-z0-9_]{1,15}$")
SECRET_KEYS = frozenset(
    {
        "apikey",
        "api_key",
        "bearer",
        "mnemonic",
        "password",
        "privatekey",
        "private_key",
        "seed",
        "secret",
        "token",
    }
)


class BindError(ValueError):
    """Speaker binding refused an input."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest_value(value: object) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def _mapping(value: object, code: str, what: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise BindError(code, f"{what} must be an object")
    return dict(value)


def _exact_keys(payload: Mapping[str, Any], keys: tuple[str, ...], what: str) -> None:
    expected = set(keys)
    got = set(payload)
    extra = got - expected
    missing = expected - got
    if extra:
        raise BindError("unexpected_keys", f"{what} has unexpected keys: {sorted(extra)}")
    if missing:
        raise BindError("missing_keys", f"{what} missing keys: {sorted(missing)}")


def _require_str(payload: Mapping[str, Any], key: str, what: str) -> str:
    value = payload[key]
    if not isinstance(value, str) or not value.strip():
        raise BindError("invalid_string", f"{what}.{key} must be a non-empty string")
    return value.strip()


def _secret_paths(value: object, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).casefold().replace("-", "_")
            next_path = f"{path}.{key}".lstrip(".")
            if normalized in SECRET_KEYS:
                found.append(next_path)
            found.extend(_secret_paths(child, next_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_secret_paths(child, f"{path}[{index}]"))
    return found


def _handle(value: str) -> str:
    handle = value.strip().lstrip("@")
    if not HANDLE.fullmatch(handle):
        raise BindError("invalid_handle", "speaker_handle must be 1–15 letters, digits, or underscore")
    return handle.lower()


def _locator(raw: object) -> dict[str, str]:
    body = _mapping(raw, "invalid_locator", "token_locator")
    kind = body.get("kind")
    if kind not in LOCATOR_KINDS:
        raise BindError("invalid_locator", "token_locator.kind must be unwired or macos-keychain")
    if kind == "unwired":
        _exact_keys(body, UNWIRED_KEYS, "token_locator")
        return {"kind": "unwired"}
    _exact_keys(body, KEYCHAIN_KEYS, "token_locator")
    service = _require_str(body, "service", "token_locator")
    account = _require_str(body, "account", "token_locator")
    return {"kind": "macos-keychain", "service": service, "account": account}


def binding(payload: Mapping[str, Any]) -> dict[str, Any]:
    body = _mapping(payload, "invalid_binding", "binding")
    secrets = _secret_paths(body)
    if secrets:
        raise BindError("secret_field_forbidden", f"binding contains secret field(s): {', '.join(secrets)}")
    _exact_keys(body, BINDING_KEYS, "binding")
    if body["schema"] != BINDING_SCHEMA:
        raise BindError("schema_mismatch", "binding schema must be kingdom.x.binding/v1")
    citizen = _require_str(body, "citizen", "binding")
    speaker_handle = _handle(_require_str(body, "speaker_handle", "binding"))
    modes_raw = body["modes"]
    if not isinstance(modes_raw, list) or not modes_raw:
        raise BindError("invalid_modes", "modes must be a non-empty array")
    modes: list[str] = []
    for item in modes_raw:
        if not isinstance(item, str):
            raise BindError("invalid_modes", "each mode must be a string")
        if item == "post":
            raise BindError("feed_shout_forbidden", "bindings may not include timeline posts")
        if item not in ALLOWED_MODES:
            raise BindError("invalid_modes", f"unknown mode: {item}")
        if item not in modes:
            modes.append(item)
    locator = _locator(body["token_locator"])
    canonical = {
        "citizen": citizen,
        "modes": modes,
        "schema": BINDING_SCHEMA,
        "speaker_handle": speaker_handle,
        "token_locator": locator,
    }
    return {
        **canonical,
        "armed": False,
        "authorization_granted": False,
        "binding_id": digest_value(canonical),
        "publish": False,
    }


def _policy(payload: Mapping[str, Any]) -> dict[str, Any]:
    body = _mapping(payload, "invalid_policy", "policy")
    secrets = _secret_paths(body)
    if secrets:
        raise BindError("secret_field_forbidden", f"policy contains secret field(s): {', '.join(secrets)}")
    _exact_keys(body, POLICY_KEYS, "policy")
    citizen = _require_str(body, "citizen", "policy")
    life = _require_str(body, "life", "policy")
    if life not in LIFE_MODES:
        raise BindError("invalid_life", "policy.life must be local, rest, or unasked")
    configured = body["configured"]
    if not isinstance(configured, bool):
        raise BindError("invalid_policy", "policy.configured must be a boolean")
    return {
        "agenttool": _require_str(body, "agenttool", "policy"),
        "citizen": citizen,
        "configured": configured,
        "life": life,
        "reason": _require_str(body, "reason", "policy"),
    }


def check(binding_payload: Mapping[str, Any], policy_payload: Mapping[str, Any]) -> dict[str, Any]:
    bound = binding(binding_payload)
    policy = _policy(policy_payload)
    if bound["citizen"].casefold() != policy["citizen"].casefold():
        raise BindError("citizen_mismatch", "binding.citizen and policy.citizen must name the same being")
    policy_allows = policy["life"] == "local"
    token_located = bound["token_locator"]["kind"] == "macos-keychain"
    if policy_allows:
        reason = policy["reason"]
    elif policy["life"] == "rest":
        reason = "rest: fail closed; no send"
    else:
        reason = "unasked fails closed to rest"
    return {
        "armed": False,
        "authorization_granted": False,
        "binding_id": bound["binding_id"],
        "bound": True,
        "citizen": bound["citizen"],
        "life": policy["life"],
        "live_client": False,
        "policy_allows": policy_allows,
        "publish": False,
        "reason": reason,
        "schema": CHECK_SCHEMA,
        "send_allowed": False,
        "speaker_handle": bound["speaker_handle"],
        "token_located": token_located,
    }
