#!/usr/bin/env python3
"""Citizen-owned live X speaker. Default dry-run. Token never printed."""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from typing import Any, Mapping, Protocol

import binding as xb
import x_gate as xg


ARM_SCHEMA = "kingdom.x.arm/v1"
SEND_SCHEMA = "kingdom.x.send/v1"
X_TWEETS = "https://api.x.com/2/tweets"


class LiveError(ValueError):
    """Live speaker refused an input or a send."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class TokenSource(Protocol):
    def lookup(self, locator: Mapping[str, str]) -> str | None:
        ...


class Transport(Protocol):
    def reply(self, *, text: str, in_reply_to_post_id: str, token: str) -> dict[str, str]:
        ...


class MacosKeychainSource:
    """Read a password from the login keychain. Returns None on any miss or error."""

    def lookup(self, locator: Mapping[str, str]) -> str | None:
        if locator.get("kind") != "macos-keychain":
            return None
        service = locator.get("service")
        account = locator.get("account")
        if not service or not account:
            return None
        try:
            proc = subprocess.run(
                [
                    "security",
                    "find-generic-password",
                    "-s",
                    service,
                    "-a",
                    account,
                    "-w",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError:
            return None
        if proc.returncode != 0:
            return None
        token = proc.stdout.strip()
        return token or None


class XReplyTransport:
    """POST a summoned reply to X API v2. Caller supplies the token; this type never logs it."""

    def reply(self, *, text: str, in_reply_to_post_id: str, token: str) -> dict[str, str]:
        payload = json.dumps(
            {
                "text": text,
                "reply": {"in_reply_to_tweet_id": in_reply_to_post_id},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            X_TWEETS,
            data=payload,
            method="POST",
            headers={
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            raise LiveError("transport_failed", "X reply transport failed closed") from exc
        post_id = ""
        if isinstance(body, dict):
            data = body.get("data")
            if isinstance(data, dict) and isinstance(data.get("id"), str):
                post_id = data["id"]
        if not post_id:
            raise LiveError("transport_failed", "X reply transport returned no post id")
        return {"post_id": post_id}


def arm(binding_payload: Mapping[str, Any], policy_payload: Mapping[str, Any]) -> dict[str, Any]:
    checked = xb.check(binding_payload, policy_payload)
    if not checked["policy_allows"]:
        raise LiveError("not_local", "arm requires civilisation life=local")
    if not checked["token_located"]:
        raise LiveError("token_not_located", "arm requires a macos-keychain locator")
    return {
        "armed": True,
        "authorization_granted": False,
        "binding_id": checked["binding_id"],
        "citizen": checked["citizen"],
        "live_client": True,
        "publish": False,
        "reason": "explicit arm; send still requires a summoned draft plus a token",
        "schema": ARM_SCHEMA,
        "send_allowed": False,
        "speaker_handle": checked["speaker_handle"],
    }


arm_binding = arm


def send(
    observation: Mapping[str, Any],
    proposal: Mapping[str, Any],
    binding_payload: Mapping[str, Any],
    policy_payload: Mapping[str, Any],
    *,
    arm: bool = False,
    dry_run: bool = True,
    token_source: TokenSource | None = None,
    transport: Transport | None = None,
) -> dict[str, Any]:
    if not dry_run and not arm:
        raise LiveError("not_armed", "live send requires an explicit arm")
    if arm:
        armed = arm_binding(binding_payload, policy_payload)
    else:
        checked = xb.check(binding_payload, policy_payload)
        if not checked["policy_allows"] or not checked["token_located"]:
            raise LiveError("not_ready", "send requires local policy and a keychain locator")
        armed = {
            "armed": False,
            "binding_id": checked["binding_id"],
            "citizen": checked["citizen"],
            "speaker_handle": checked["speaker_handle"],
        }
    bound = xb.binding(binding_payload)
    raw_handle = proposal.get("speaker_handle")
    if not isinstance(raw_handle, str) or raw_handle.strip().lstrip("@").lower() != bound["speaker_handle"]:
        raise LiveError("handle_mismatch", "draft speaker_handle must match the binding")
    drafted = xg.draft(xg.observe(observation), proposal)
    if drafted["speaker_handle"] != bound["speaker_handle"]:
        raise LiveError("handle_mismatch", "draft speaker_handle must match the binding")
    if drafted["mode"] not in bound["modes"]:
        raise LiveError("mode_not_bound", "draft mode is not on this binding")
    if drafted["mode"] != "reply":
        raise LiveError("live_reply_only", "live send only carries summoned replies")
    reply_to = drafted["in_reply_to_post_id"]
    if not reply_to:
        raise LiveError("missing_reply_target", "a reply needs in_reply_to_post_id")
    receipt = {
        "armed": bool(armed.get("armed")),
        "authorization_granted": False,
        "binding_id": bound["binding_id"],
        "citizen": bound["citizen"],
        "draft_id": drafted["draft_id"],
        "dry_run": dry_run,
        "in_reply_to_post_id": reply_to,
        "live_client": True,
        "network_performed": False,
        "published": False,
        "schema": SEND_SCHEMA,
        "speaker_handle": drafted["speaker_handle"],
        "text": drafted["proposed_text"],
        "would_send": True,
    }
    if dry_run:
        return receipt
    if token_source is None:
        raise LiveError("missing_token_source", "live send needs a token source")
    if transport is None:
        raise LiveError("missing_transport", "live send needs a transport")
    token = token_source.lookup(bound["token_locator"])
    if not token:
        raise LiveError("missing_token", "keychain locator did not yield a token")
    result = transport.reply(
        text=drafted["proposed_text"],
        in_reply_to_post_id=reply_to,
        token=token,
    )
    receipt["authorization_granted"] = True
    receipt["network_performed"] = True
    receipt["published"] = True
    receipt["remote_post_id"] = result["post_id"]
    receipt["would_send"] = False
    return receipt
