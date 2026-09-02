#!/usr/bin/env python3
"""Kingdom-shaped X gather: bounded, latest, public taint. No network."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

import x_gate as xg


GATHER_SCHEMA = "kingdom.x.gather/v1"
ALLOWED_MODES = frozenset({"topic", "summoned", "handle"})
FORBIDDEN_MODES = frozenset({"firehose", "followers", "ads", "top"})
REQUEST_KEYS = (
    "schema",
    "query",
    "mode",
    "sort",
    "source",
    "speaker_handle",
    "observed_at",
    "posts",
)
MAX_POSTS = 20
MAX_QUERY = 280


class GatherError(ValueError):
    """Gather refused an input."""

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
        raise GatherError("invalid_gather", f"{what} must be an object")
    return dict(value)


def _exact_keys(payload: Mapping[str, Any], keys: tuple[str, ...], what: str) -> None:
    expected = set(keys)
    got = set(payload)
    extra = got - expected
    missing = expected - got
    if extra:
        raise GatherError("unexpected_keys", f"{what} has unexpected keys: {sorted(extra)}")
    if missing:
        raise GatherError("missing_keys", f"{what} missing keys: {sorted(missing)}")


def _handle(value: str) -> str:
    return value.strip().lstrip("@").lower()


def gather(payload: Mapping[str, Any]) -> dict[str, Any]:
    body = _mapping(payload, "gather")
    xg._scan_metrics(body, "gather")
    _exact_keys(body, REQUEST_KEYS, "gather")
    if body["schema"] != GATHER_SCHEMA:
        raise GatherError("schema_mismatch", "gather schema must be kingdom.x.gather/v1")
    query = body["query"]
    if not isinstance(query, str) or not query.strip() or len(query) > MAX_QUERY:
        raise GatherError("invalid_query", "query must be 1–280 characters")
    query = query.strip()
    mode = body["mode"]
    if mode in FORBIDDEN_MODES:
        raise GatherError("mode_forbidden", f"gather must not use {mode}")
    if mode not in ALLOWED_MODES:
        raise GatherError("invalid_mode", "mode must be topic, summoned, or handle")
    if body["sort"] != "latest":
        raise GatherError("engagement_ranked", "gather sort must be latest, never top")
    source = body["source"]
    if source not in xg.SOURCES:
        raise GatherError("invalid_source", "unknown gather source")
    speaker_raw = body["speaker_handle"]
    if mode == "summoned":
        if not isinstance(speaker_raw, str) or not speaker_raw.strip():
            raise GatherError("speaker_required", "summoned gather needs speaker_handle")
        speaker_handle = _handle(speaker_raw)
    else:
        if speaker_raw is not None:
            raise GatherError("speaker_not_used", f"{mode} gather must set speaker_handle null")
        speaker_handle = None
    posts_raw = body["posts"]
    if not isinstance(posts_raw, list):
        raise GatherError("invalid_posts", "posts must be an array")
    if len(posts_raw) > MAX_POSTS:
        raise GatherError("listen_too_wide", f"gather listens at most {MAX_POSTS} posts")
    observed_at = body["observed_at"]
    if not isinstance(observed_at, str) or not observed_at.strip():
        raise GatherError("invalid_string", "observed_at must be a non-empty string")
    observation_id = None
    posts: list[dict[str, Any]] = []
    if posts_raw:
        try:
            observed = xg.observe(
                {
                    "schema": xg.OBSERVATION_SCHEMA,
                    "source": source,
                    "observed_at": observed_at,
                    "posts": posts_raw,
                }
            )
        except xg.GateError as exc:
            raise GatherError(exc.code, str(exc)) from exc
        posts = list(observed["posts"])
        observation_id = observed["observation_id"]
        if mode == "summoned":
            pin = speaker_handle or ""
            for post in posts:
                if pin not in post["mentioned_handles"]:
                    raise GatherError("not_summoned", "summoned gather requires the speaker in every post")
        if mode == "handle":
            pin = _handle(query)
            for post in posts:
                if post["author_handle"] != pin:
                    raise GatherError("handle_mismatch", "handle gather requires matching authors")
    canonical = {
        "mode": mode,
        "observed_at": observed_at,
        "posts": posts,
        "query": query,
        "schema": GATHER_SCHEMA,
        "sort": "latest",
        "source": source,
        "speaker_handle": speaker_handle,
    }
    return {
        "engagement_ranked": False,
        "gather_id": digest_value(canonical),
        "mode": mode,
        "network_performed": False,
        "observation_id": observation_id,
        "post_count": len(posts),
        "query": query,
        "schema": GATHER_SCHEMA,
        "sort": "latest",
        "source": source,
        "speaker_handle": speaker_handle,
        "surveillance": False,
        "taint": "public",
    }
