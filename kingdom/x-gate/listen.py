#!/usr/bin/env python3
"""Citizen-owned XAA live listen. Default dry-run. Mention and reply only."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Mapping, Protocol

import binding as xb
import live as xl
import xaa as xx


LISTEN_SCHEMA = "kingdom.x.xaa-listen/v1"
X_SUBSCRIPTIONS = "https://api.x.com/2/activity/subscriptions"
X_STREAM = "https://api.x.com/2/activity/stream"
SUBSCRIBE_KEYS = frozenset({"event_type", "filter", "tag"})
FILTER_KEYS = frozenset({"user_id"})


class ListenError(ValueError):
    """Live XAA listen refused an input or a stream."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class Stream(Protocol):
    def subscribe(self, *, body: Mapping[str, Any], token: str) -> str:
        ...

    def listen(self, *, token: str, max_events: int) -> list[Mapping[str, Any]]:
        ...

    def release(self, *, subscription_id: str, token: str) -> None:
        ...


class XActivityTransport:
    """Bounded XAA subscribe/listen/release. Caller supplies the token; this type never logs it."""

    def subscribe(self, *, body: Mapping[str, Any], token: str) -> str:
        _validate_subscription(body)
        payload = json.dumps(dict(body)).encode("utf-8")
        request = urllib.request.Request(
            X_SUBSCRIPTIONS,
            data=payload,
            method="POST",
            headers={
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                parsed = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            raise ListenError("transport_failed", "XAA subscribe transport failed closed") from exc
        sub_id = ""
        if isinstance(parsed, dict):
            data = parsed.get("data")
            if isinstance(data, dict):
                inner = data.get("subscription")
                if isinstance(inner, dict) and isinstance(inner.get("subscription_id"), str):
                    sub_id = inner["subscription_id"]
        if not sub_id:
            raise ListenError("transport_failed", "XAA subscribe returned no subscription id")
        return sub_id

    def listen(self, *, token: str, max_events: int) -> list[Mapping[str, Any]]:
        request = urllib.request.Request(
            X_STREAM,
            method="GET",
            headers={"Authorization": "Bearer " + token},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                events: list[Mapping[str, Any]] = []
                while len(events) < max_events:
                    line = response.readline()
                    if not line:
                        break
                    stripped = line.strip()
                    if not stripped:
                        continue
                    parsed = json.loads(stripped.decode("utf-8"))
                    if not isinstance(parsed, Mapping):
                        raise ListenError("transport_failed", "XAA stream returned a non-object")
                    events.append(dict(parsed))
                return events
        except ListenError:
            raise
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            raise ListenError("transport_failed", "XAA stream transport failed closed") from exc

    def release(self, *, subscription_id: str, token: str) -> None:
        request = urllib.request.Request(
            X_SUBSCRIPTIONS + "/" + subscription_id,
            method="DELETE",
            headers={"Authorization": "Bearer " + token},
        )
        try:
            with urllib.request.urlopen(request, timeout=20):
                return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ListenError("subscriptions_linger", "XAA subscriptions were not released") from exc


def _validate_subscription(body: Mapping[str, Any]) -> None:
    if not isinstance(body, Mapping):
        raise ListenError("firehose_forbidden", "subscription body must be an object")
    extra = set(body) - SUBSCRIBE_KEYS
    missing = {"event_type", "filter"} - set(body)
    if extra or missing or "webhook_id" in body:
        raise ListenError("firehose_forbidden", "XAA listen refuses webhooks, keywords, and extra filters")
    event_type = body.get("event_type")
    if event_type not in xx.ALLOWED_EVENT_TYPES:
        raise ListenError("not_summoned", f"{event_type} is not a summoned listen")
    filt = body.get("filter")
    if not isinstance(filt, Mapping) or set(filt) != FILTER_KEYS:
        raise ListenError("firehose_forbidden", "XAA listen filter is speaker user_id only")
    user_id = filt.get("user_id")
    if not isinstance(user_id, str) or not user_id.strip():
        raise ListenError("firehose_forbidden", "XAA listen needs filter.user_id")


def listen(
    binding_payload: Mapping[str, Any],
    policy_payload: Mapping[str, Any],
    *,
    speaker_user_id: str,
    arm: bool = False,
    dry_run: bool = True,
    token_source: xl.TokenSource | None = None,
    stream: Stream | None = None,
) -> dict[str, Any]:
    if not dry_run and not arm:
        raise ListenError("not_armed", "live listen requires an explicit arm")
    if arm:
        armed = xl.arm_binding(binding_payload, policy_payload)
    else:
        checked = xb.check(binding_payload, policy_payload)
        if not checked["policy_allows"] or not checked["token_located"]:
            raise ListenError("not_ready", "listen requires local policy and a keychain locator")
        armed = {
            "armed": False,
            "binding_id": checked["binding_id"],
            "citizen": checked["citizen"],
            "speaker_handle": checked["speaker_handle"],
        }
    bound = xb.binding(binding_payload)
    planned = xx.plan_subscriptions(speaker_user_id)
    receipt: dict[str, Any] = {
        "armed": bool(armed.get("armed")),
        "authorization_granted": False,
        "binding_id": bound["binding_id"],
        "citizen": bound["citizen"],
        "daemon": False,
        "dry_run": dry_run,
        "firehose": False,
        "live_client": True,
        "network_performed": False,
        "published": False,
        "schema": LISTEN_SCHEMA,
        "speaker_handle": bound["speaker_handle"],
        "speaker_user_id": planned["speaker_user_id"],
        "stream_open": False,
        "subscriptions": list(planned["subscriptions"]),
        "taint": "public",
        "webhook": False,
        "would_listen": True,
    }
    if dry_run:
        return receipt
    if token_source is None:
        raise ListenError("missing_token_source", "live listen needs a token source")
    if stream is None:
        raise ListenError("missing_stream", "live listen needs a stream")
    token = token_source.lookup(bound["token_locator"])
    if not token:
        raise ListenError("missing_token", "keychain locator did not yield a token")
    ids: list[str] = []
    ingest_error: ListenError | None = None
    try:
        for body in planned["subscriptions"]:
            ids.append(stream.subscribe(body=body, token=token))
        events = list(stream.listen(token=token, max_events=xx.MAX_EVENTS))[: xx.MAX_EVENTS]
        try:
            ingested = xx.ingest(
                {
                    "schema": xx.SUMMON_SCHEMA,
                    "speaker_user_id": planned["speaker_user_id"],
                    "speaker_handle": bound["speaker_handle"],
                    "events": events,
                }
            )
        except xx.XaaError as exc:
            ingest_error = ListenError(exc.code, str(exc))
        else:
            receipt["authorization_granted"] = True
            receipt["event_count"] = ingested["event_count"]
            receipt["kept_event_types"] = ingested["kept_event_types"]
            receipt["network_performed"] = True
            receipt["observation_id"] = ingested["observation_id"]
            receipt["posts"] = ingested["posts"]
            receipt["summon_id"] = ingested["summon_id"]
            receipt["would_listen"] = False
    finally:
        released: list[str] = []
        linger = False
        for sub_id in ids:
            try:
                stream.release(subscription_id=sub_id, token=token)
                released.append(sub_id)
            except Exception:
                linger = True
        receipt["subscriptions_released"] = (not linger) and len(released) == len(ids)
    if ingest_error is not None:
        raise ingest_error
    if not receipt["subscriptions_released"]:
        raise ListenError("subscriptions_linger", "XAA subscriptions were not released")
    return receipt
