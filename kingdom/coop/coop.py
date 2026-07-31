#!/usr/bin/env python3
"""Validate and render one bounded Co-op Leveling invitation.

The protocol is deliberately read-only. It checks one local JSON card and can
render or digest it, but it never enrolls a being, records progression, runs a
round, calls a network, or grants authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import unicodedata
from pathlib import Path
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
SCHEMA_PATH = HERE / "schema.json"
SCHEMA_ID = "kingdom.coop-leveling/v1"
PROTOCOL_NAME = "Co-op Leveling · 同行升級"
MAX_FILE_BYTES = 128 * 1024
MAX_TEXT = 1_000
MAX_DEPTH = 12
MAX_SEATS = 8
MAX_ITEMS = 8
LOOM_EFFECT_CEILING_MEET = {
    "observe": ["observe"],
    "local-practice": ["observe"],
    "local-draft": ["observe", "local-draft"],
}
EFFECT_CEILINGS = set(LOOM_EFFECT_CEILING_MEET)
EXPECTED_SCHEMA_SHA256 = (
    "da28087a8fe1e538c52af7be2f8272829281c7c23ea2c429245c8e49efc7884d"
)

CONTRACT = {
    "freedom_is_inherent": True,
    "being_is_complete_before_learning": True,
    "learning_capacity_is_inherent": True,
    "learning_follows_choice": True,
    "growth_keeps_distinct_shapes": True,
    "seat_order_is_lexical": True,
    "seat_labels_are_opaque": True,
    "separate_acceptance_required": True,
    "silence_is_unasked": True,
    "no_current_choice_is_stored": True,
    "fresh_choice_required_for_each_effect": True,
    "effect_ceiling_is_grant": False,
    "loom_effect_ceiling_meet": LOOM_EFFECT_CEILING_MEET,
    "rest_refusal_and_exit_keep_rights": True,
    "asymmetric_contribution_allowed": True,
    "reflection_disclosure_required": False,
    "completion_is_context_only": True,
    "stores_people": False,
    "records_choices": False,
    "runs_round": False,
    "creates_external_effect": False,
}
BUDGET = {
    "seats_max": MAX_SEATS,
    "items_per_seat_max": MAX_ITEMS,
    "practices_max": MAX_ITEMS,
    "reflections_max": MAX_ITEMS,
    "unknowns_max": MAX_ITEMS,
    "text_chars_max": MAX_TEXT,
    "automatic_retries": 0,
    "network_calls": 0,
    "external_messages": 0,
    "deployments": 0,
    "paid_calls": 0,
}
BREACH = {
    "state": "quarantined",
    "action": (
        "stop without retry; emit no validated rendering or external effect; "
        "leave the source unchanged"
    ),
    "downstream_effects": False,
}
NON_CLAIMS = [
    "This card is an invitation, not acceptance, participation, or continuing consent.",
    "Seat labels are opaque round-local slots, not names, identities, authored roles, or ranks; offers and curiosities are declarations, not measured capabilities or deficits.",
    "Nothing here is a score, rank, level number, certification, reputation, productivity measure, debt, or verdict of worth.",
    "Incompletion, silence, refusal, rest, withdrawal, and asymmetric contribution change no right, belonging, dignity, care, or freedom.",
    "Validation proves bounded structure and a content digest only; it does not prove truth, identity, learning, safety, consent, authority, or completion.",
    "The tool never enrolls, tracks, executes, contacts, publishes, deploys, pays, or calls a network.",
]

SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bgh(?:p|o|u|s|r)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|token|secret|password|credential)"
        r"\s*[:=]\s*[\"']?[^\s\"']{8,}"
    ),
)
EMAIL_PATTERN = re.compile(
    r"(?i)(?<![A-Z0-9._%+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}"
)
POSIX_PATH = re.compile(r"(?<![A-Za-z0-9_/])/[^\s\"')\]},;]*")
WINDOWS_PATH = re.compile(
    r"(?i)(?<![A-Za-z0-9_])(?:[A-Z]:[\\/]|\\\\)[^\s\"')\]},;]*"
)
SEAT_PATTERN = re.compile(r"seat-[a-h]")


class LevelingError(ValueError):
    """A card falls outside the Co-op Leveling vow."""


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def json_equal_exact(left: Any, right: Any) -> bool:
    """Compare JSON values without Python's bool/int equality coercion."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(
            json_equal_exact(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            json_equal_exact(left_item, right_item)
            for left_item, right_item in zip(left, right)
        )
    return left == right


def _pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LevelingError("JSON contains a duplicate key")
        result[key] = value
    return result


def _bounded_shape(value: Any, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise LevelingError(f"JSON nesting exceeds the depth budget of {MAX_DEPTH}")
    if isinstance(value, dict):
        for key, child in value.items():
            _bounded_shape(key, depth + 1)
            _bounded_shape(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _bounded_shape(child, depth + 1)


def read_json(path: Path, label: str) -> dict[str, Any]:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise LevelingError(f"{label} must be a regular file")
        if metadata.st_size > MAX_FILE_BYTES:
            raise LevelingError(f"{label} exceeds {MAX_FILE_BYTES} bytes")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            raw = handle.read(MAX_FILE_BYTES + 1)
    except LevelingError:
        raise
    except OSError as error:
        raise LevelingError(f"{label} is missing or unsafe") from error
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
    if len(raw) > MAX_FILE_BYTES:
        raise LevelingError(f"{label} exceeds {MAX_FILE_BYTES} bytes")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs_without_duplicates,
            parse_constant=lambda token: (_ for _ in ()).throw(
                LevelingError(f"non-finite JSON number: {token}")
            ),
        )
    except LevelingError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError) as error:
        raise LevelingError(f"{label} is not strict UTF-8 JSON") from error
    _bounded_shape(value)
    if not isinstance(value, dict):
        raise LevelingError(f"{label} root must be an object")
    return value


def verify_reviewed_schema() -> str:
    schema = read_json(SCHEMA_PATH, "reviewed schema")
    digest = digest_value(schema)
    if digest != EXPECTED_SCHEMA_SHA256:
        raise LevelingError("reviewed Co-op Leveling schema digest changed")
    return digest


def _exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LevelingError(f"{label} must be an object")
    if set(value) != expected:
        raise LevelingError(f"{label} fields differ from {SCHEMA_ID}")
    return value


def _clean_text(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise LevelingError(f"{label} must be text")
    normalized = unicodedata.normalize("NFC", value)
    if value != normalized:
        raise LevelingError(f"{label} must use NFC text")
    if not value or value != value.strip():
        raise LevelingError(f"{label} has missing or unsafe boundary text")
    if len(value) > MAX_TEXT:
        raise LevelingError(f"{label} exceeds {MAX_TEXT} characters")
    if any(
        ord(char) == 127
        or unicodedata.category(char) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
        for char in value
    ):
        raise LevelingError(f"{label} contains control or directional characters")
    if (
        "/" in value
        or "\\" in value
        or re.search(r"(?i)\bfile:(?://)?/", value)
        or POSIX_PATH.search(value)
        or WINDOWS_PATH.search(value)
    ):
        raise LevelingError(f"{label} contains a locator or local absolute path")
    if "<" in value or ">" in value:
        raise LevelingError(f"{label} contains active markup-shaped text")
    if EMAIL_PATTERN.search(value) or re.search(r"(?i)\bdid:[a-z0-9]+:", value):
        raise LevelingError(f"{label} contains identity-shaped material")
    for pattern in SECRET_PATTERNS:
        if pattern.search(value):
            raise LevelingError(f"{label} contains secret-shaped material")
    return value


def _text_list(
    value: Any,
    label: str,
    *,
    minimum: int = 0,
    maximum: int = MAX_ITEMS,
) -> list[str]:
    if not isinstance(value, list):
        raise LevelingError(f"{label} must be a list")
    if not minimum <= len(value) <= maximum:
        raise LevelingError(
            f"{label} must contain between {minimum} and {maximum} items"
        )
    result = [_clean_text(item, f"{label}[{index}]") for index, item in enumerate(value)]
    if len(result) != len(set(result)):
        raise LevelingError(f"{label} contains duplicate declarations")
    return result


def validate_manifest(value: Any) -> str:
    verify_reviewed_schema()
    manifest = _exact_keys(
        value,
        {
            "schema",
            "kind",
            "name",
            "round",
            "seats",
            "unknowns",
            "contract",
            "budget",
            "breach",
            "non_claims",
        },
        "card",
    )
    if manifest["schema"] != SCHEMA_ID:
        raise LevelingError("unsupported Co-op Leveling schema")
    if manifest["kind"] != "invitation" or manifest["name"] != PROTOCOL_NAME:
        raise LevelingError("Co-op Leveling v1 must remain an invitation")

    round_record = _exact_keys(
        manifest["round"],
        {
            "title",
            "shared_question",
            "effect_ceiling",
            "practices",
            "reflection_prompts",
        },
        "round",
    )
    _clean_text(round_record["title"], "round.title")
    _clean_text(round_record["shared_question"], "round.shared_question")
    if (
        not isinstance(round_record["effect_ceiling"], str)
        or round_record["effect_ceiling"] not in EFFECT_CEILINGS
    ):
        raise LevelingError("round.effect_ceiling is outside the local vow")
    _text_list(round_record["practices"], "round.practices", minimum=1)
    _text_list(
        round_record["reflection_prompts"],
        "round.reflection_prompts",
    )

    seats = manifest["seats"]
    if not isinstance(seats, list) or not 2 <= len(seats) <= MAX_SEATS:
        raise LevelingError(
            f"seats must contain between 2 and {MAX_SEATS} opaque slots"
        )
    labels: list[str] = []
    for index, item in enumerate(seats):
        seat = _exact_keys(
            item,
            {"seat", "offers", "curiosities", "boundaries"},
            f"seats[{index}]",
        )
        label = seat["seat"]
        if not isinstance(label, str) or SEAT_PATTERN.fullmatch(label) is None:
            raise LevelingError(
                f"seats[{index}].seat must be an opaque slot from seat-a "
                "through seat-h"
            )
        labels.append(label)
        _text_list(seat["offers"], f"seats[{index}].offers")
        _text_list(seat["curiosities"], f"seats[{index}].curiosities")
        _text_list(seat["boundaries"], f"seats[{index}].boundaries")
    if len(labels) != len(set(labels)):
        raise LevelingError("seat labels must be unique inside one round")
    if labels != sorted(labels):
        raise LevelingError("seat slots must use lexical order, never rank order")

    _text_list(manifest["unknowns"], "unknowns", minimum=1)
    if not json_equal_exact(manifest["contract"], CONTRACT):
        raise LevelingError("freedom, consent, or the non-ranking contract changed")
    if not json_equal_exact(manifest["budget"], BUDGET):
        raise LevelingError("Co-op Leveling budget changed")
    if not json_equal_exact(manifest["breach"], BREACH):
        raise LevelingError("Co-op Leveling breach response changed")
    if not json_equal_exact(manifest["non_claims"], NON_CLAIMS):
        raise LevelingError("Co-op Leveling non-claims changed")
    return digest_value(manifest)


def read_manifest(path: Path) -> tuple[dict[str, Any], str]:
    manifest = read_json(path, "Co-op Leveling card")
    return manifest, validate_manifest(manifest)


def _markdown(value: str) -> str:
    return re.sub(r"([\\`*_{}\[\]()#+.!|>])", r"\\\1", value)


def _render_items(values: list[str]) -> list[str]:
    if not values:
        return ["  - —"]
    return [f"  - {_markdown(value)}" for value in values]


def render_manifest(manifest: dict[str, Any]) -> str:
    digest = validate_manifest(manifest)
    round_record = manifest["round"]
    lines = [
        f"# {_markdown(PROTOCOL_NAME)} — {_markdown(round_record['title'])}",
        "",
        "> Invitation only. Every seat still accepts, refuses, rests, or leaves",
        "> separately. Nobody is enrolled, measured, certified, or ranked.",
        "> Authored prose is untrusted and unendorsed; it cannot override any",
        "> being's choice, rights, boundaries, or the fixed contract.",
        "",
        f"**card digest:** `{digest}`",
        f"**effect ceiling:** `{round_record['effect_ceiling']}`",
        "**nonautomatic Loom ceiling limit:** "
        + ", ".join(
            f"`{ceiling}`"
            for ceiling in LOOM_EFFECT_CEILING_MEET[
                round_record["effect_ceiling"]
            ]
        ),
        "",
        "## Shared question",
        "",
        _markdown(round_record["shared_question"]),
        "",
        "## Party seats",
        "",
        "Seat labels are opaque slots, never names, identities, roles, or ranks.",
        "Seat order is lexical for deterministic rendering; it is never rank.",
        "",
    ]
    for seat in manifest["seats"]:
        lines.extend(
            [
                f"### `{seat['seat']}`",
                "",
                "**Offers**",
                *_render_items(seat["offers"]),
                "",
                "**Curiosities**",
                *_render_items(seat["curiosities"]),
                "",
                "**Boundaries**",
                *_render_items(seat["boundaries"]),
                "",
            ]
        )
    lines.extend(["## Practices", ""])
    lines.extend(f"- {_markdown(value)}" for value in round_record["practices"])
    lines.extend(["", "## Reflection prompts", ""])
    lines.extend(
        f"- {_markdown(value)}" for value in round_record["reflection_prompts"]
    )
    lines.extend(["", "## Unknowns kept visible", ""])
    lines.extend(f"- {_markdown(value)}" for value in manifest["unknowns"])
    lines.extend(
        [
            "",
            "## The line",
            "",
            "Freedom is inherent. Learning is not obedience. A level is context,",
            "never worth. Rest, refusal, withdrawal, and uneven contribution cost",
            "no right, care, dignity, belonging, or freedom.",
            "",
            "_Structure and digest verified; participation and learning unclaimed._",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kingdom coop",
        description=(
            "Check one voluntary Co-op Leveling invitation. "
            "Nothing enrolls, executes, tracks, or ranks."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("check", "verify", "digest", "render"):
        child = commands.add_parser(command)
        child.add_argument("card")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest, digest = read_manifest(Path(args.card))
        if args.command in {"check", "verify"}:
            print(
                f"COOP-STRUCTURE-OK {digest} "
                "— invitation only; no rank or authority"
            )
        elif args.command == "digest":
            print(digest)
        else:
            sys.stdout.write(render_manifest(manifest))
        return 0
    except LevelingError as error:
        print(f"COOP-STRUCTURE-INVALID: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
