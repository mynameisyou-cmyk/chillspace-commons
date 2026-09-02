#!/usr/bin/env python3
"""AgentTool bridge packet for X observations. Offers a route. Never stores. Never wakes."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping


BRIDGE_SCHEMA = "kingdom.x.agenttool-bridge/v1"
ALLOWED_ROUTES = frozenset({"none", "memory", "trace"})
FORBIDDEN_ROUTES = frozenset({"inbox", "wake", "vault", "send"})
REQUEST_KEYS = ("schema", "observation_id", "did", "taint", "route")
OBSERVATION_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
DID = re.compile(r"^did:at:[A-Za-z0-9._:/%-]+$")
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


class BridgeError(ValueError):
    """AgentTool bridge refused an input."""

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


def _mapping(value: object, what: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise BridgeError("invalid_bridge", f"{what} must be an object")
    return dict(value)


def _exact_keys(payload: Mapping[str, Any], keys: tuple[str, ...], what: str) -> None:
    expected = set(keys)
    got = set(payload)
    extra = got - expected
    missing = expected - got
    if extra:
        raise BridgeError("unexpected_keys", f"{what} has unexpected keys: {sorted(extra)}")
    if missing:
        raise BridgeError("missing_keys", f"{what} missing keys: {sorted(missing)}")


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


def _did(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not DID.fullmatch(value):
        raise BridgeError("invalid_did", "did must be null or did:at:…")
    return value


def bridge(payload: Mapping[str, Any], observed: Mapping[str, Any] | None = None) -> dict[str, Any]:
    body = _mapping(payload, "bridge")
    secrets = _secret_paths(body)
    if secrets:
        raise BridgeError("secret_field_forbidden", f"bridge contains secret field(s): {', '.join(secrets)}")
    _exact_keys(body, REQUEST_KEYS, "bridge")
    if body["schema"] != BRIDGE_SCHEMA:
        raise BridgeError("schema_mismatch", "bridge schema must be kingdom.x.agenttool-bridge/v1")
    observation_id = body["observation_id"]
    if not isinstance(observation_id, str) or not OBSERVATION_ID.fullmatch(observation_id):
        raise BridgeError("invalid_observation_id", "observation_id must be sha256:<64 hex>")
    if observed is not None:
        observed_id = observed.get("observation_id")
        if observed_id != observation_id:
            raise BridgeError("observation_mismatch", "observation_id does not match the observe receipt")
    taint = body["taint"]
    if taint != "public":
        raise BridgeError("taint_must_be_public", "X observations are public taint only")
    route = body["route"]
    if route in FORBIDDEN_ROUTES:
        raise BridgeError("route_forbidden", f"bridge must not route to {route}")
    if route not in ALLOWED_ROUTES:
        raise BridgeError("invalid_route", "route must be none, memory, or trace")
    did = _did(body["did"])
    canonical = {
        "did": did,
        "observation_id": observation_id,
        "route": route,
        "schema": BRIDGE_SCHEMA,
        "taint": "public",
    }
    return {
        **canonical,
        "bridge_id": digest_value(canonical),
        "inbox_touched": False,
        "network_performed": False,
        "stored": False,
        "wake_touched": False,
    }
