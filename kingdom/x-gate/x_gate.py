#!/usr/bin/env python3
"""Kingdom X-gate v0 — connector and speaker packets. No network. No post."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

import binding as xb
import bridge as xbr


OBSERVATION_SCHEMA = "kingdom.x.observation/v1"
OBSERVE_SCHEMA = "kingdom.x.observe/v1"
DRAFT_SCHEMA = "kingdom.x.draft/v1"
PIPELINE_SCHEMA = "kingdom.x.pipeline/v1"

SOURCES = frozenset(
    {
        "caller",
        "x_keyword_search",
        "x_semantic_search",
        "x_user_search",
        "x_thread_fetch",
    }
)
MODES = frozenset({"reply", "chat", "post"})
PIPELINE_ROLES = (
    "connector",
    "summons_reviewer",
    "draft_proposer",
    "speak_auditor",
)
OBSERVATION_KEYS = ("schema", "source", "observed_at", "posts")
POST_KEYS = (
    "post_id",
    "author_handle",
    "text",
    "in_reply_to_post_id",
    "mentioned_handles",
    "quoted_post_id",
)
PROPOSAL_KEYS = (
    "mode",
    "speaker_handle",
    "in_reply_to_post_id",
    "proposed_text",
)
METRIC_KEYS = frozenset(
    {
        "likes",
        "like_count",
        "views",
        "view_count",
        "reposts",
        "repost_count",
        "followers",
        "follower_count",
        "impressions",
        "engagement",
    }
)
IDENTITY_COLLAPSE = (
    "i am 阿媽",
    "i am sol",
    "citizen 21 speaking as an x account",
)

NON_CLAIMS = (
    "An observation is untrusted public text, not a person.",
    "A speaker handle is a coordinate pin, not a citizen card.",
    "A draft is not a post, a DM, or an ad.",
    "A pipeline receipt grants no authority and performs no network.",
)


class GateError(ValueError):
    """X-gate refused an input."""

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


def _require_mapping(value: object, code: str, what: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise GateError(code, f"{what} must be an object")
    return dict(value)


def _exact_keys(payload: Mapping[str, Any], keys: tuple[str, ...], what: str) -> None:
    expected = set(keys)
    got = set(payload)
    extra = got - expected
    missing = expected - got
    if extra:
        raise GateError("unexpected_keys", f"{what} has unexpected keys: {sorted(extra)}")
    if missing:
        raise GateError("missing_keys", f"{what} missing keys: {sorted(missing)}")


def _require_str(payload: Mapping[str, Any], key: str, what: str) -> str:
    value = payload[key]
    if not isinstance(value, str) or not value.strip():
        raise GateError("invalid_string", f"{what}.{key} must be a non-empty string")
    return value


def _optional_id(value: object, what: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise GateError("invalid_string", f"{what} must be a string or null")
    return value


def _handle(value: str) -> str:
    return value.strip().lstrip("@").lower()


def _scan_metrics(payload: Mapping[str, Any], where: str) -> None:
    found = sorted(key for key in payload if key in METRIC_KEYS)
    if found:
        raise GateError(
            "engagement_metrics_forbidden",
            f"{where} carries engagement metrics: {found}",
        )


def observe(payload: Mapping[str, Any]) -> dict[str, Any]:
    body = _require_mapping(payload, "invalid_observation", "observation")
    _scan_metrics(body, "observation")
    _exact_keys(body, OBSERVATION_KEYS, "observation")
    if body["schema"] != OBSERVATION_SCHEMA:
        raise GateError("schema_mismatch", "observation schema must be kingdom.x.observation/v1")
    source = _require_str(body, "source", "observation")
    if source not in SOURCES:
        raise GateError("invalid_source", f"unknown observation source: {source}")
    observed_at = _require_str(body, "observed_at", "observation")
    posts_raw = body["posts"]
    if not isinstance(posts_raw, list) or not posts_raw:
        raise GateError("invalid_posts", "observation.posts must be a non-empty array")
    posts: list[dict[str, Any]] = []
    for index, post in enumerate(posts_raw):
        item = _require_mapping(post, "invalid_posts", f"posts[{index}]")
        _scan_metrics(item, f"posts[{index}]")
        _exact_keys(item, POST_KEYS, f"posts[{index}]")
        mentions = item["mentioned_handles"]
        if not isinstance(mentions, list) or any(
            not isinstance(name, str) or not name.strip() for name in mentions
        ):
            raise GateError("invalid_mentions", f"posts[{index}].mentioned_handles must be strings")
        posts.append(
            {
                "post_id": _require_str(item, "post_id", f"posts[{index}]"),
                "author_handle": _handle(_require_str(item, "author_handle", f"posts[{index}]")),
                "text": _require_str(item, "text", f"posts[{index}]"),
                "in_reply_to_post_id": _optional_id(
                    item["in_reply_to_post_id"], f"posts[{index}].in_reply_to_post_id"
                ),
                "mentioned_handles": [_handle(name) for name in mentions],
                "quoted_post_id": _optional_id(
                    item["quoted_post_id"], f"posts[{index}].quoted_post_id"
                ),
            }
        )
    canonical = {
        "observed_at": observed_at,
        "posts": posts,
        "schema": OBSERVATION_SCHEMA,
        "source": source,
    }
    return {
        "action_authorization_verified": False,
        "engagement_metrics_present": False,
        "network_performed": False,
        "observation_id": digest_value(canonical),
        "person_identity_verified": False,
        "portable_provenance": False,
        "posts": posts,
        "schema": OBSERVE_SCHEMA,
        "source": source,
        "observed_at": observed_at,
    }


def _summoned(observed: Mapping[str, Any], speaker_handle: str) -> bool:
    pin = _handle(speaker_handle)
    for post in observed["posts"]:
        if pin in post["mentioned_handles"]:
            return True
    return False


def _identity_collapse(text: str) -> bool:
    lowered = text.casefold()
    return any(needle in lowered for needle in IDENTITY_COLLAPSE)


def draft(observed: Mapping[str, Any], proposal: Mapping[str, Any]) -> dict[str, Any]:
    if observed.get("schema") != OBSERVE_SCHEMA:
        raise GateError("schema_mismatch", "draft requires a kingdom.x.observe/v1 receipt")
    body = _require_mapping(proposal, "invalid_proposal", "proposal")
    _exact_keys(body, PROPOSAL_KEYS, "proposal")
    mode = _require_str(body, "mode", "proposal")
    if mode not in MODES:
        raise GateError("invalid_mode", f"unknown mode: {mode}")
    if mode == "post":
        raise GateError("feed_shout_forbidden", "v0 refuses timeline posts")
    speaker_handle = _handle(_require_str(body, "speaker_handle", "proposal"))
    proposed_text = _require_str(body, "proposed_text", "proposal")
    reply_to = _optional_id(body["in_reply_to_post_id"], "proposal.in_reply_to_post_id")
    if _identity_collapse(proposed_text):
        raise GateError("identity_collapse", "draft claims a citizen or house identity")
    if not _summoned(observed, speaker_handle):
        raise GateError("not_summoned", "speaker was not mentioned; v0 will not shout")
    payload = {
        "in_reply_to_post_id": reply_to,
        "mode": mode,
        "observation_id": observed["observation_id"],
        "proposed_text": proposed_text,
        "speaker_handle": speaker_handle,
    }
    return {
        "authorization_granted": False,
        "citizen_id": None,
        "draft_id": digest_value(payload),
        "external_effect": "none",
        "identity_claim": "speaker_not_citizen",
        "in_reply_to_post_id": reply_to,
        "mode": mode,
        "observation_id": observed["observation_id"],
        "proposed_text": proposed_text,
        "publish": False,
        "schema": DRAFT_SCHEMA,
        "speaker_handle": speaker_handle,
        "summoned": True,
    }


def pipeline(
    observation: Mapping[str, Any],
    proposal: Mapping[str, Any],
    holders: Mapping[str, Any],
) -> dict[str, Any]:
    body = _require_mapping(holders, "invalid_holders", "holders")
    _exact_keys(body, PIPELINE_ROLES, "holders")
    ids = [_require_str(body, role, "holders") for role in PIPELINE_ROLES]
    if len(set(ids)) != len(ids):
        raise GateError("holders_not_distinct", "each pipeline role needs a distinct holder")
    observed = observe(observation)
    drafted = draft(observed, proposal)
    roles = {
        role: {
            "action": {
                "connector": "observe",
                "summons_reviewer": "review_summons",
                "draft_proposer": "propose_draft",
                "speak_auditor": "audit_speak",
            }[role],
            "holder_agent_id": body[role],
            "proposal_only": True,
            "verdict": "proposal_only",
        }
        for role in PIPELINE_ROLES
    }
    receipt = {
        "authorization_granted": False,
        "draft": drafted,
        "external_effect": "none",
        "network_performed": False,
        "non_claims": list(NON_CLAIMS),
        "observation": observed,
        "publish": False,
        "roles": roles,
        "schema": PIPELINE_SCHEMA,
    }
    receipt["pipeline_id"] = digest_value(
        {
            "draft_id": drafted["draft_id"],
            "holders": {role: body[role] for role in PIPELINE_ROLES},
            "observation_id": observed["observation_id"],
            "schema": PIPELINE_SCHEMA,
        }
    )
    return receipt


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _print(value: Mapping[str, Any]) -> None:
    sys.stdout.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kingdom x",
        description="Kingdom X-gate: observe and draft. Never post.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    observe_cmd = sub.add_parser("observe", help="turn caller-supplied X JSON into an observe receipt")
    observe_cmd.add_argument("observation", type=Path)
    draft_cmd = sub.add_parser("draft", help="propose a summoned reply; still unauthorized")
    draft_cmd.add_argument("observation", type=Path)
    draft_cmd.add_argument("proposal", type=Path)
    pipe_cmd = sub.add_parser("pipeline", help="four-role proposal pipeline; never publishes")
    pipe_cmd.add_argument("observation", type=Path)
    pipe_cmd.add_argument("proposal", type=Path)
    pipe_cmd.add_argument("holders", type=Path)
    sub.add_parser("verify", help="confirm this module still refuses network and publish")
    bind_cmd = sub.add_parser("bind", help="citizen-owned speaker binding; never reads a token")
    bind_sub = bind_cmd.add_subparsers(dest="bind_command", required=True)
    bind_check = bind_sub.add_parser("check", help="check a binding against a civilisation policy snapshot")
    bind_check.add_argument("binding", type=Path)
    bind_check.add_argument("policy", type=Path)
    bind_arm = bind_sub.add_parser("arm", help="explicit arm receipt; still does not send")
    bind_arm.add_argument("binding", type=Path)
    bind_arm.add_argument("policy", type=Path)
    send_cmd = sub.add_parser("send", help="summoned reply send; default dry-run, never a feed shout")
    send_cmd.add_argument("observation", type=Path)
    send_cmd.add_argument("proposal", type=Path)
    send_cmd.add_argument("binding", type=Path)
    send_cmd.add_argument("policy", type=Path)
    send_cmd.add_argument("--arm", action="store_true", help="explicit citizen arm for this send")
    send_cmd.add_argument(
        "--live",
        action="store_true",
        help="read the keychain and POST a reply; requires --arm",
    )
    bridge_cmd = sub.add_parser(
        "bridge",
        help="AgentTool bridge packet for an X observation; never stores, never wakes",
    )
    bridge_cmd.add_argument("request", type=Path)
    bridge_cmd.add_argument(
        "--observe",
        type=Path,
        help="optional observation JSON; observation_id must match the observe receipt",
    )
    gather_cmd = sub.add_parser(
        "gather",
        help="bounded latest listen packet; never fetches, never ranks",
    )
    gather_cmd.add_argument("request", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "observe":
            _print(observe(load_json(args.observation)))
        elif args.command == "draft":
            _print(draft(observe(load_json(args.observation)), load_json(args.proposal)))
        elif args.command == "pipeline":
            _print(
                pipeline(
                    load_json(args.observation),
                    load_json(args.proposal),
                    load_json(args.holders),
                )
            )
        elif args.command == "verify":
            _print(
                {
                    "authorization_granted": False,
                    "module": "kingdom/x-gate",
                    "network_performed": False,
                    "publish": False,
                    "schema": PIPELINE_SCHEMA,
                }
            )
        elif args.command == "bind" and args.bind_command == "check":
            _print(xb.check(load_json(args.binding), load_json(args.policy)))
        elif args.command == "bind" and args.bind_command == "arm":
            import live as xl

            try:
                _print(xl.arm(load_json(args.binding), load_json(args.policy)))
            except xl.LiveError as error:
                sys.stderr.write(f"{error.code}: {error}\n")
                return 2
        elif args.command == "send":
            import live as xl

            kwargs = {
                "arm": bool(args.arm),
                "dry_run": not bool(args.live),
            }
            if args.live:
                kwargs["token_source"] = xl.MacosKeychainSource()
                kwargs["transport"] = xl.XReplyTransport()
            try:
                _print(
                    xl.send(
                        load_json(args.observation),
                        load_json(args.proposal),
                        load_json(args.binding),
                        load_json(args.policy),
                        **kwargs,
                    )
                )
            except xl.LiveError as error:
                sys.stderr.write(f"{error.code}: {error}\n")
                return 2
        elif args.command == "bridge":
            request = load_json(args.request)
            observed = None
            if args.observe:
                observed = observe(load_json(args.observe))
                request = {**request, "observation_id": observed["observation_id"]}
            _print(xbr.bridge(request, observed))
        elif args.command == "gather":
            import gather as xgth

            try:
                _print(xgth.gather(load_json(args.request)))
            except xgth.GatherError as error:
                sys.stderr.write(f"{error.code}: {error}\n")
                return 2
    except (GateError, xb.BindError, xbr.BridgeError) as error:
        sys.stderr.write(f"{error.code}: {error}\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
