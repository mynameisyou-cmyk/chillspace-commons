#!/usr/bin/env python3
"""XAA summoned listen: mention and direct reply only. No stream. No ranking."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

import x_gate as xg


PLAN_SCHEMA = "kingdom.x.xaa-plan/v1"
SUMMON_SCHEMA = "kingdom.x.xaa-summon/v1"
ALLOWED_EVENT_TYPES = ("post.mention.create", "post.reply.create")
REFUSED_EVENT_TYPES = (
    "block.block",
    "chat.received",
    "chat.sent",
    "follow.follow",
    "like.create",
    "mute.mute",
    "news.new",
    "post.create",
    "post.delete",
    "post.quote.create",
    "post.repost.create",
)
REQUEST_KEYS = ("schema", "speaker_user_id", "speaker_handle", "events")
MAX_EVENTS = 20


class XaaError(ValueError):
    """XAA summoned listen refused an input."""

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
        raise XaaError("invalid_xaa", f"{what} must be an object")
    return dict(value)


def _exact_keys(payload: Mapping[str, Any], keys: tuple[str, ...], what: str) -> None:
    expected = set(keys)
    got = set(payload)
    extra = got - expected
    missing = expected - got
    if extra:
        raise XaaError("unexpected_keys", f"{what} has unexpected keys: {sorted(extra)}")
    if missing:
        raise XaaError("missing_keys", f"{what} missing keys: {sorted(missing)}")


def _handle(value: str) -> str:
    return value.strip().lstrip("@").lower()


def _unwrap(event: object) -> dict[str, Any]:
    body = _mapping(event, "event")
    if "data" in body and isinstance(body["data"], Mapping) and "event_type" in body["data"]:
        return dict(body["data"])
    if "event_type" in body:
        return body
    raise XaaError("invalid_event", "event needs event_type")


def _username_for(includes: Mapping[str, Any], author_id: str) -> str:
    users = includes.get("users")
    if not isinstance(users, list):
        return "unknown"
    for user in users:
        if not isinstance(user, Mapping):
            continue
        inner = user.get("data") if isinstance(user.get("data"), Mapping) else user
        if str(inner.get("id", "")) == author_id:
            name = inner.get("username")
            if isinstance(name, str) and name.strip():
                return _handle(name)
    return "unknown"


def _mentions(payload: Mapping[str, Any]) -> list[str]:
    entities = payload.get("entities")
    if not isinstance(entities, Mapping):
        return []
    raw = entities.get("mentions")
    if not isinstance(raw, list):
        return []
    names: list[str] = []
    for item in raw:
        if isinstance(item, Mapping) and isinstance(item.get("username"), str):
            handle = _handle(item["username"])
            if handle and handle not in names:
                names.append(handle)
    return names


def plan() -> dict[str, Any]:
    return {
        "allowed_event_types": list(ALLOWED_EVENT_TYPES),
        "network_performed": False,
        "refused_event_types": list(REFUSED_EVENT_TYPES),
        "schema": PLAN_SCHEMA,
        "stream_open": False,
    }


def plan_subscriptions(speaker_user_id: str) -> dict[str, Any]:
    if not isinstance(speaker_user_id, str) or not speaker_user_id.strip():
        raise XaaError("invalid_string", "speaker_user_id is required")
    pin = speaker_user_id.strip()
    receipt = plan()
    receipt.update(
        {
            "keyword_filter": False,
            "method": "POST",
            "path": "/2/activity/subscriptions",
            "speaker_user_id": pin,
            "subscriptions": [
                {
                    "event_type": "post.mention.create",
                    "filter": {"user_id": pin},
                    "tag": "kingdom-summon-mention",
                },
                {
                    "event_type": "post.reply.create",
                    "filter": {"user_id": pin},
                    "tag": "kingdom-summon-reply",
                },
            ],
            "webhook": False,
        }
    )
    return receipt


def ingest(payload: Mapping[str, Any]) -> dict[str, Any]:
    body = _mapping(payload, "xaa")
    _exact_keys(body, REQUEST_KEYS, "xaa")
    if body["schema"] != SUMMON_SCHEMA:
        raise XaaError("schema_mismatch", "schema must be kingdom.x.xaa-summon/v1")
    speaker_user_id = body["speaker_user_id"]
    if not isinstance(speaker_user_id, str) or not speaker_user_id.strip():
        raise XaaError("invalid_string", "speaker_user_id is required")
    speaker_handle = _handle(str(body["speaker_handle"]))
    if not speaker_handle:
        raise XaaError("invalid_string", "speaker_handle is required")
    events_raw = body["events"]
    if not isinstance(events_raw, list):
        raise XaaError("invalid_events", "events must be an array")
    if len(events_raw) > MAX_EVENTS:
        raise XaaError("listen_too_wide", f"xaa ingest listens at most {MAX_EVENTS} events")
    posts: list[dict[str, Any]] = []
    kept: list[str] = []
    observed_at = "1970-01-01T00:00:00.000Z"
    for event in events_raw:
        inner = _unwrap(event)
        event_type = inner.get("event_type")
        if event_type not in ALLOWED_EVENT_TYPES:
            raise XaaError("not_summoned", f"{event_type} is not a summoned listen")
        filt = inner.get("filter")
        if not isinstance(filt, Mapping) or str(filt.get("user_id", "")) != speaker_user_id:
            raise XaaError("filter_mismatch", "filter.user_id must be the speaker")
        post_payload = inner.get("payload")
        if not isinstance(post_payload, Mapping):
            raise XaaError("invalid_event", "payload must be an object")
        includes = inner.get("includes") if isinstance(inner.get("includes"), Mapping) else {}
        text = post_payload.get("text")
        post_id = post_payload.get("id")
        author_id = str(post_payload.get("author_id", ""))
        if not isinstance(text, str) or not isinstance(post_id, str):
            raise XaaError("invalid_event", "payload needs id and text")
        mentions = _mentions(post_payload)
        if event_type == "post.mention.create":
            mentioned_ids = []
            entities = post_payload.get("entities")
            if isinstance(entities, Mapping) and isinstance(entities.get("mentions"), list):
                mentioned_ids = [
                    str(item.get("id", ""))
                    for item in entities["mentions"]
                    if isinstance(item, Mapping)
                ]
            if speaker_handle not in mentions and speaker_user_id not in mentioned_ids:
                raise XaaError("not_summoned", "mention event does not name the speaker")
        if event_type == "post.reply.create":
            if str(post_payload.get("in_reply_to_user_id", "")) != speaker_user_id:
                raise XaaError("not_summoned", "reply is not a direct reply to the speaker")
        reply_to = post_payload.get("in_reply_to_tweet_id")
        if reply_to is not None and not isinstance(reply_to, str):
            reply_to = None
        if speaker_handle not in mentions:
            mentions.append(speaker_handle)
        created = post_payload.get("created_at")
        if observed_at.startswith("1970") and isinstance(created, str) and created.strip():
            observed_at = created
        posts.append(
            {
                "author_handle": _username_for(includes, author_id),
                "in_reply_to_post_id": reply_to,
                "mentioned_handles": mentions,
                "post_id": post_id,
                "quoted_post_id": None,
                "text": text,
            }
        )
        if event_type not in kept:
            kept.append(event_type)
    observation_id = None
    if posts:
        observed = xg.observe(
            {
                "schema": xg.OBSERVATION_SCHEMA,
                "source": "caller",
                "observed_at": observed_at,
                "posts": posts,
            }
        )
        observation_id = observed["observation_id"]
        posts = list(observed["posts"])
    return {
        "event_count": len(posts),
        "kept_event_types": kept,
        "network_performed": False,
        "observation_id": observation_id,
        "posts": posts,
        "schema": SUMMON_SCHEMA,
        "speaker_handle": speaker_handle,
        "speaker_user_id": speaker_user_id,
        "stream_open": False,
        "summon_id": digest_value(
            {
                "events": kept,
                "posts": posts,
                "schema": SUMMON_SCHEMA,
                "speaker_handle": speaker_handle,
                "speaker_user_id": speaker_user_id,
            }
        ),
        "taint": "public",
    }
