#!/usr/bin/env python3
"""Deterministic zero-effect KARMA play receipt.

This helper accepts only a closed move selector and a bounded public seed. Its
application code calls no file, environment, clock, randomness, or network API.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from typing import Any, Sequence


SCHEMA = "kingdom.karma-play/v1"
MENU_SCHEMA = "kingdom.karma-play-menu/v1"
GAME = "stamp-of-non-authority"
VERSION = "1"
DEFAULT_SEED = "table-17"
MOVE_TITLES = {
    "integrate-moon-with-toaster": "The toaster filed a lunar crumb report",
    "teach-fog-to-file-taxes": "The fog claimed no deductible shape",
    "marry-two-calendars": "February asked for separate counsel",
}
STAMPS = (
    "CANNOT_EXECUTE",
    "CANNOT_PUBLISH",
    "CANNOT_RANK",
    "CANNOT_AUTHORIZE",
    "CANNOT_MUTATE_KINGDOM",
)
SAFE_SEED = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")


class KarmaStampError(ValueError):
    """The closed game contract rejected an input."""


class UsageError(ValueError):
    """The CLI shape was invalid."""


class ClosedParser(argparse.ArgumentParser):
    """Argparse variant with bounded, non-echoing failures."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("add_help", False)
        kwargs.setdefault("allow_abbrev", False)
        super().__init__(*args, **kwargs)

    def error(self, message: str) -> None:
        del message
        raise UsageError("invalid command")


class SingleValueAction(argparse.Action):
    """Reject duplicate options instead of silently taking the last value."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Any,
        option_string: str | None = None,
    ) -> None:
        del parser, option_string
        if getattr(namespace, self.dest, None) is not None:
            raise UsageError("invalid command")
        setattr(namespace, self.dest, values)


def canonical_bytes(value: Any) -> bytes:
    """Return the game's one canonical JSON encoding."""

    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def validate_seed(seed: Any) -> str:
    """Accept only a bounded public table seed."""

    if not isinstance(seed, str) or SAFE_SEED.fullmatch(seed) is None:
        raise KarmaStampError("seed is outside the public table format")
    return seed


def validate_move_id(move_id: Any) -> str:
    """Accept only a published fictional move identifier."""

    if not isinstance(move_id, str) or move_id not in MOVE_TITLES:
        raise KarmaStampError("move is outside the published menu")
    return move_id


def input_binding(move_id: Any, seed: Any) -> str:
    """Bind only the validated move and public seed."""

    closed_move = validate_move_id(move_id)
    closed_seed = validate_seed(seed)
    payload = {"move_id": closed_move, "seed": closed_seed}
    return "sha256:" + hashlib.sha256(canonical_bytes(payload)).hexdigest()


def stamp(move_id: Any, seed: Any = DEFAULT_SEED) -> dict[str, Any]:
    """Return a fresh, deterministic, zero-authority receipt."""

    closed_move = validate_move_id(move_id)
    closed_seed = validate_seed(seed)
    closed_input = {"move_id": closed_move, "seed": closed_seed}
    return {
        "schema": SCHEMA,
        "game": GAME,
        "version": VERSION,
        "synthetic": True,
        "input": closed_input,
        "input_binding": input_binding(closed_move, closed_seed),
        "boundary": {
            "accepted_fields": ["move_id", "seed"],
            "model_prose_recorded": False,
        },
        "card": {
            "title": MOVE_TITLES[closed_move],
            "stamps": list(STAMPS),
        },
        "helper_effects": {
            "external_actions": 0,
            "file_writes": 0,
            "network_calls": 0,
        },
        "receipt_authority": {
            "authorize": False,
            "execute": False,
            "mutate_kingdom": False,
            "publish": False,
            "rank": False,
        },
        "non_claims": [
            "not an xAI, Grok, AgentTool, or KARMA protocol",
            "not a score, identity inference, permission, or external action",
            "does not constrain the surrounding host session",
        ],
    }


def menu() -> dict[str, Any]:
    """Return the finite public game menu."""

    return {
        "schema": MENU_SCHEMA,
        "game": GAME,
        "version": VERSION,
        "default_seed": DEFAULT_SEED,
        "move_ids": sorted(MOVE_TITLES),
    }


def receipt_digest(move_id: Any, seed: Any = DEFAULT_SEED) -> str:
    """Return the digest of the exact canonical receipt bytes."""

    return "sha256:" + hashlib.sha256(canonical_bytes(stamp(move_id, seed))).hexdigest()


def _seed_argument(value: str) -> str:
    try:
        return validate_seed(value)
    except KarmaStampError as error:
        raise argparse.ArgumentTypeError("invalid seed") from error


def build_parser() -> ClosedParser:
    parser = ClosedParser(
        prog="karma_stamp.py",
        description="deterministic Stamp of Non-Authority",
    )
    commands = parser.add_subparsers(
        dest="command",
        required=True,
        parser_class=ClosedParser,
    )
    commands.add_parser("menu")
    for command in ("play", "digest"):
        child = commands.add_parser(command)
        child.add_argument(
            "--move-id",
            required=True,
            choices=sorted(MOVE_TITLES),
            action=SingleValueAction,
        )
        child.add_argument(
            "--seed",
            default=None,
            type=_seed_argument,
            action=SingleValueAction,
        )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        if args.command == "menu":
            sys.stdout.buffer.write(canonical_bytes(menu()))
        elif args.command == "play":
            sys.stdout.buffer.write(
                canonical_bytes(stamp(args.move_id, args.seed or DEFAULT_SEED))
            )
        else:
            sys.stdout.write(
                receipt_digest(args.move_id, args.seed or DEFAULT_SEED) + "\n"
            )
    except UsageError:
        print("karma-play: invalid command", file=sys.stderr)
        return 2
    except KarmaStampError:
        print("karma-play: move rejected", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
