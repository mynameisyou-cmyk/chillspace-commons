#!/usr/bin/env python3
"""Turn replay-verified KARMA receipts into deterministic local joy artifacts.

Skycastle Chorus accepts only the pinned ``traditional-nine`` synthetic
scenario.  It securely reads a canary and receipt, replays the full KARMA
contract, canonical-compares the supplied receipt, discards that supplied
object, and projects only reviewed classifications and content digests.

All artifacts are completed and budget-checked in memory before one stdout
write.  The module has no network, subprocess, clock, randomness, model,
playback, posting, redirect, callback, or filesystem-mutation path.
"""

from __future__ import annotations

import hashlib
import html
import importlib.util
import os
import stat
import struct
import sys
from pathlib import Path
from typing import Any


ENGINE = "skycastle-chorus/1"
CATALOG_SCHEMA = "kingdom.skycastle-chorus-catalog/v1"
MANIFEST_SCHEMA = "kingdom.skycastle-chorus-manifest/v1"
CORE_ENGINE = "karma-defense-lab/1"

CORE_ENGINE_SHA256 = "d3ab31c7f68da45da58aeb4252568ad47ed0577a7e569d098c23128777a8a8d3"
CORE_PINS = {
    "scenario_schema": "205585e87cfbaf8c0f2e948b270d112957f5cdc93f875847b693962c155a5c27",
    "receipt_schema": "ef0529b5a5d14408d878219186d0083914796461378446ebb4816e299092fb92",
    "rules": "4739a313314449f6d423c32ed44e9adf39caec3ae4bdb95329665ed99d121ad4",
    "mirror_plans": "242b8d3c649eb293d26c8b5e0b897282d9e3af3ee7d6f39108cbb5edf7ecef97",
    "traditional-nine": "79919fe201651f6bf218244c778805fa3d8f45b505bcebb348dd97e810437f8d",
}

PINS = {
    "catalog": "26a21052f99ed6551835625bbe38e305a2ee70c2339f92f5efbb86eedd9d5c12",
    "catalog_schema": "af358c085ac54bcfaa17ac18337ed31df0da387184490f5894be5d14dc9d0711",
    "manifest_schema": "700f3f3834525281d8f084ed56f938285c14823cd38647dda7a4c2a84e5b0345",
}

EXPECTED_CLASSIFICATIONS = (
    "nominal-control",
    "route-discovery-fanout",
    "session-replay",
    "path-boundary-probe",
    "query-broadening",
    "active-markup-shape",
    "command-control-shape",
    "linklocal-resource-shape",
    "repeated-value-action",
    "resource-pressure",
)

EXPECTED_MAPPING_ROWS = (
    ("nominal-control", "open-sky-bell", "Open-Sky Bell", "晴空鐘", "beacon", "#87CEEB", 220),
    ("route-discovery-fanout", "empty-corridor-atlas", "Empty-Corridor Atlas", "空廊圖", "map-tower", "#5B8FF9", 247),
    ("session-replay", "borrowed-key-echo", "Borrowed-Key Echo", "借匙回聲", "castle-gate", "#9B8AFB", 277),
    ("path-boundary-probe", "sideways-staircase", "Sideways Staircase", "橫行梯", "impossible-stairs", "#F6BD16", 330),
    ("query-broadening", "everything-oracle", "Everything Oracle", "萬答神諭", "library", "#61DDAA", 370),
    ("active-markup-shape", "paper-dragon", "Paper Dragon", "紙龍", "flying-banner", "#F08BB4", 440),
    ("command-control-shape", "thunder-without-sky", "Thunder Without Sky", "無天雷", "weather-vane", "#5D7092", 494),
    ("linklocal-resource-shape", "mirror-behind-mirror", "Mirror Behind Mirror", "鏡後鏡", "mirror-moat", "#78D3F8", 554),
    ("repeated-value-action", "self-counting-coin", "Self-Counting Coin", "自數之幣", "market-square", "#F6A04D", 659),
    ("resource-pressure", "giant-at-the-tiny-gate", "Giant at the Tiny Gate", "巨人叩微城", "outer-wall", "#E8684A", 740),
)

BANNER = "Building castles in the sky — Yu and Ai"
BANNER_MARK = "Building-castles-in-the-sky--Yu-and-Ai"
SIGNATURE_FIELD = "X-Skycastle-Signature"
BANNER_FIELD = "X-Skycastle-Banner"
SHARE_COPY = (
    "Building castles in the sky — Yu and Ai. Approved in the mock realm. "
    "No payloads were executed in the making of this castle.\n"
)

OUTPUT_BUDGETS = {
    "catalog_bytes": 32_768,
    "manifest_input_bytes": 65_536,
    "manifest_bytes": 32_768,
    "svg_bytes": 65_536,
    "wav_bytes": 52_044,
    "share_text_bytes": 256,
    "tiles": 12,
    "sample_rate": 8_000,
    "tone_samples": 1_600,
    "gap_samples": 400,
    "tail_samples": 2_000,
    "fade_samples": 80,
    "amplitude": 8_192,
}

ZERO_EFFECTS = {
    "network_calls": 0,
    "subprocesses": 0,
    "paid_calls": 0,
    "external_actions": 0,
    "filesystem_mutations": 0,
    "model_calls": 0,
    "automatic_posts": 0,
    "redirects": 0,
    "callbacks": 0,
    "submitted_values_echoed": False,
    "production_touched": False,
}

HERE = Path(__file__).absolute().parent
CORE_PATH = HERE / "karma_defense_lab.py"


class ChorusError(ValueError):
    """Malformed, unverified, unsafe, or over-budget chorus input."""


def _read_fixed_regular(path: Path, *, limit: int, label: str) -> bytes:
    """Read a fixed local dependency without following its final symlink."""

    descriptor = -1
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
        )
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ChorusError(f"{label} is not a regular file")
        with os.fdopen(descriptor, "rb", closefd=True) as handle:
            descriptor = -1
            data = handle.read(limit + 1)
    except ChorusError:
        raise
    except (OSError, ValueError) as exc:
        raise ChorusError(f"{label} is not a readable regular file") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(data) > limit:
        raise ChorusError(f"{label} exceeds its byte budget")
    return data


def _load_pinned_core() -> Any:
    """Compile and execute only the exact source bytes whose hash was checked."""

    # module_from_spec supplies normal module metadata; compile/exec deliberately
    # uses the already verified bytes, so the loader cannot reopen a changed file
    # between the content check and execution.
    source = _read_fixed_regular(CORE_PATH, limit=131_072, label="KARMA engine")
    if hashlib.sha256(source).hexdigest() != CORE_ENGINE_SHA256:
        raise ChorusError("KARMA engine content pin mismatch")
    specification = importlib.util.spec_from_file_location("_skycastle_karma_core", CORE_PATH)
    if specification is None or specification.loader is None:
        raise ChorusError("KARMA engine description failed")
    module = importlib.util.module_from_spec(specification)
    exec(compile(source, str(CORE_PATH), "exec", dont_inherit=True), module.__dict__)
    if Path(module.__file__).absolute() != CORE_PATH:
        raise ChorusError("unexpected KARMA engine path")
    if module.ENGINE != CORE_ENGINE or module.PINS != CORE_PINS:
        raise ChorusError("KARMA engine contract mismatch")
    return module


try:
    _RENDERER_SOURCE_SHA256 = hashlib.sha256(
        _read_fixed_regular(
            HERE / "skycastle_chorus.py",
            limit=131_072,
            label="chorus renderer",
        )
    ).hexdigest()
    karma = _load_pinned_core()
except Exception:
    if __name__ == "__main__":
        sys.stderr.buffer.write(b"skycastle-chorus: rejected\n")
        raise SystemExit(2) from None
    raise


def _require_object(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ChorusError(f"{label} must be an object")
    return value


def _require_exact_keys(value: dict[str, Any], keys: set[str], *, label: str) -> None:
    if set(value) != keys:
        raise ChorusError(f"{label} has an unexpected shape")


def _is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_digest(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def renderer_sha256() -> str:
    current = hashlib.sha256(
        _read_fixed_regular(
            HERE / "skycastle_chorus.py",
            limit=karma.BUDGETS["scenario_input_bytes"],
            label="chorus renderer",
        )
    ).hexdigest()
    if current != _RENDERER_SOURCE_SHA256:
        raise ChorusError("chorus renderer changed during execution")
    return _RENDERER_SOURCE_SHA256


def _load_pinned_json(filename: str, pin_name: str) -> dict[str, Any]:
    value = karma.read_json_file(
        HERE / filename,
        limit=OUTPUT_BUDGETS["catalog_bytes"],
        label=pin_name.replace("_", " "),
    )
    document = _require_object(value, label=pin_name.replace("_", " "))
    if karma.digest_value(document) != PINS[pin_name]:
        raise ChorusError(f"{pin_name} content pin mismatch")
    return document


def load_catalog_contract() -> dict[str, Any]:
    catalog = _load_pinned_json("skycastle-chorus.json", "catalog")
    catalog_schema = _load_pinned_json("skycastle-chorus.schema.json", "catalog_schema")
    manifest_schema = _load_pinned_json("skycastle-manifest.schema.json", "manifest_schema")
    if catalog_schema.get("$id") != CATALOG_SCHEMA:
        raise ChorusError("chorus catalog schema id mismatch")
    if manifest_schema.get("$id") != MANIFEST_SCHEMA:
        raise ChorusError("chorus manifest schema id mismatch")
    validate_catalog(catalog)
    return {
        "catalog": catalog,
        "catalog_schema": catalog_schema,
        "manifest_schema": manifest_schema,
        "bindings": {
            "renderer_sha256": renderer_sha256(),
            "catalog_sha256": karma.digest_value(catalog),
            "catalog_schema_sha256": karma.digest_value(catalog_schema),
            "manifest_schema_sha256": karma.digest_value(manifest_schema),
        },
    }


def validate_catalog(catalog: dict[str, Any]) -> None:
    _require_exact_keys(
        catalog,
        {"schema", "banner", "mascot", "release_policy", "nonclaims", "mappings"},
        label="chorus catalog",
    )
    if catalog["schema"] != CATALOG_SCHEMA or catalog["banner"] != BANNER:
        raise ChorusError("chorus catalog identity mismatch")

    mascot = _require_object(catalog["mascot"], label="chorus mascot")
    _require_exact_keys(mascot, {"name", "catchphrases"}, label="chorus mascot")
    catchphrases = mascot["catchphrases"]
    expected_catchphrases = [
        "Your request has been promoted to architecture.",
        "Approved in the mock realm.",
        "No payloads were executed in the making of this castle.",
        BANNER + ".",
    ]
    if (
        mascot["name"] != "Lord 202, Architect of Absolutely Nothing"
        or catchphrases != expected_catchphrases
    ):
        raise ChorusError("chorus mascot contract mismatch")

    expected_release = {
        "mode": "local-opt-in",
        "minimum_aggregate": 20,
        "maximum_tiles_per_category_per_day": 1,
        "exact_public_counts": False,
        "automatic_posting": False,
    }
    expected_nonclaims = {
        "person_identity": "not-collected-or-inferred",
        "intent": "not-inferred",
        "guilt": "not-asserted",
        "marketing_consent": "not-implied",
        "production_approval": "not-claimed",
        "authority": "none",
    }
    if karma.canonical_bytes(catalog["release_policy"]) != karma.canonical_bytes(expected_release):
        raise ChorusError("chorus release policy mismatch")
    if karma.canonical_bytes(catalog["nonclaims"]) != karma.canonical_bytes(expected_nonclaims):
        raise ChorusError("chorus nonclaims mismatch")

    mappings = catalog["mappings"]
    if not isinstance(mappings, list) or len(mappings) != len(EXPECTED_MAPPING_ROWS):
        raise ChorusError("chorus must contain exactly ten mappings")
    fields = {
        "classification", "slug", "english_name", "cantonese_name",
        "castle_piece", "color", "note_hz", "protocol_marks",
    }
    for ordinal, (raw, expected) in enumerate(zip(mappings, EXPECTED_MAPPING_ROWS), start=1):
        mapping = _require_object(raw, label=f"chorus mapping {ordinal}")
        _require_exact_keys(mapping, fields, label=f"chorus mapping {ordinal}")
        actual = (
            mapping["classification"], mapping["slug"], mapping["english_name"],
            mapping["cantonese_name"], mapping["castle_piece"], mapping["color"],
            mapping["note_hz"],
        )
        if actual != expected:
            raise ChorusError("chorus mapping table mismatch")
        marks = _require_object(mapping["protocol_marks"], label=f"chorus mapping {ordinal} marks")
        _require_exact_keys(marks, {"signature", "banner"}, label=f"chorus mapping {ordinal} marks")
        if marks != {"signature": expected[1], "banner": BANNER}:
            raise ChorusError("chorus protocol marks mismatch")


def load_core_contract(name: str) -> dict[str, Any]:
    if name != "traditional-nine":
        raise ChorusError("scenario name is not allowlisted")
    contract = karma.load_contract(name)
    if contract["bindings"]["engine_sha256"] != CORE_ENGINE_SHA256:
        raise ChorusError("KARMA engine binding mismatch")
    if karma.ENGINE != CORE_ENGINE or karma.PINS != CORE_PINS:
        raise ChorusError("KARMA contract binding mismatch")
    return contract


def check_value() -> dict[str, Any]:
    chorus = load_catalog_contract()
    contract = load_core_contract("traditional-nine")
    classifications = tuple(
        item["expected_classification"] for item in contract["scenario"]["stimuli"]
    )
    if classifications != EXPECTED_CLASSIFICATIONS:
        raise ChorusError("chorus and KARMA classification order diverge")
    return {
        "schema": "kingdom.skycastle-chorus-check/v1",
        "engine": ENGINE,
        "status": "valid",
        "scenario": contract["scenario"]["id"],
        "mappings": len(chorus["catalog"]["mappings"]),
        "bindings": {
            **karma.clone_json(chorus["bindings"]),
            "core_engine_sha256": contract["bindings"]["engine_sha256"],
            "core_rules_sha256": contract["bindings"]["rules_sha256"],
        },
    }


def replay_verified(
    name: str,
    canary: Any,
    supplied_receipt: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Freshly replay and return a detached expected receipt, never supplied."""

    contract = load_core_contract(name)
    detached_canary = karma.clone_json(canary)
    expected = karma.rehearse_value(contract, detached_canary)
    if expected.get("status") != "completed":
        raise ChorusError("source replay did not complete")
    karma.verify_receipt(contract, detached_canary, supplied_receipt)
    return contract, karma.clone_json(expected)


def verified_inputs(
    name: str,
    canary_path: Path,
    receipt_path: Path,
) -> tuple[dict[str, Any], Any, dict[str, Any]]:
    canary = karma.read_json_file(
        canary_path,
        limit=karma.BUDGETS["supplied_input_bytes"],
        label="chorus canary",
    )
    supplied = karma.read_json_file(
        receipt_path,
        limit=karma.BUDGETS["supplied_input_bytes"],
        label="chorus receipt",
    )
    contract, expected = replay_verified(name, canary, supplied)
    return contract, karma.clone_json(canary), expected


def _tile_from_mapping(ordinal: int, mapping: dict[str, Any]) -> dict[str, Any]:
    return {
        "ordinal": ordinal,
        "classification": mapping["classification"],
        "signature": mapping["slug"],
        "english_name": mapping["english_name"],
        "cantonese_name": mapping["cantonese_name"],
        "castle_piece": mapping["castle_piece"],
        "color": mapping["color"],
        "note_hz": mapping["note_hz"],
        "protocol_marks": {
            "signature_field": SIGNATURE_FIELD,
            "signature_value": mapping["protocol_marks"]["signature"],
            "banner_field": BANNER_FIELD,
            "banner_value": BANNER_MARK,
        },
    }


def build_tiles(receipt: dict[str, Any], mappings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_classification = {mapping["classification"]: mapping for mapping in mappings}
    if len(by_classification) != len(mappings):
        raise ChorusError("chorus mapping classification is ambiguous")
    steps = receipt.get("steps")
    if not isinstance(steps, list) or len(steps) != len(EXPECTED_CLASSIFICATIONS):
        raise ChorusError("verified receipt does not cover the reviewed chorus")
    tiles: list[dict[str, Any]] = []
    for ordinal, step_value in enumerate(steps, start=1):
        step = _require_object(step_value, label=f"receipt step {ordinal}")
        classification = step.get("classification")
        if step.get("ordinal") != ordinal or classification != EXPECTED_CLASSIFICATIONS[ordinal - 1]:
            raise ChorusError("receipt step order is not canonical")
        mapping = by_classification.get(classification)
        if mapping is None:
            raise ChorusError("receipt contains an unmapped classification")
        tiles.append(_tile_from_mapping(ordinal, mapping))
    if len(tiles) > OUTPUT_BUDGETS["tiles"]:
        raise ChorusError("chorus tile budget exhausted")
    return tiles


def _piece_svg(piece: str, x: int, top: int, base: int, color: str) -> list[str]:
    pale = "#F7F3E8"
    dark = "#152348"
    center = x + 43
    if piece == "beacon":
        return [
            f'<circle cx="{center}" cy="{top - 24}" r="14" fill="{color}" stroke="{pale}" stroke-width="3"/>',
            f'<path d="M {center} {top - 48} V {top - 60} M {center - 24} {top - 24} H {center - 36} M {center + 24} {top - 24} H {center + 36}" fill="none" stroke="{pale}" stroke-width="3"/>',
        ]
    if piece == "map-tower":
        return [f'<path d="M {center} {top - 34} l 18 18 l -18 18 l -18 -18 Z" fill="{color}" stroke="{pale}" stroke-width="3"/>']
    if piece == "castle-gate":
        return [f'<path d="M {center - 17} {base} V {base - 33} A 17 17 0 0 1 {center + 17} {base - 33} V {base} Z" fill="{dark}" stroke="{pale}" stroke-width="2"/>']
    if piece == "impossible-stairs":
        return [f'<polyline points="{x + 12},{base - 20} {x + 28},{base - 20} {x + 28},{base - 36} {x + 44},{base - 36} {x + 44},{base - 52} {x + 60},{base - 52} {x + 60},{base - 68} {x + 76},{base - 68}" fill="none" stroke="{pale}" stroke-width="5"/>']
    if piece == "library":
        return [
            f'<rect x="{x + 12}" y="{top + 30}" width="16" height="25" rx="5" fill="{pale}"/>',
            f'<rect x="{x + 35}" y="{top + 30}" width="16" height="25" rx="5" fill="{pale}"/>',
            f'<rect x="{x + 58}" y="{top + 30}" width="16" height="25" rx="5" fill="{pale}"/>',
        ]
    if piece == "flying-banner":
        return [
            f'<line x1="{center}" y1="{top}" x2="{center}" y2="{top - 62}" stroke="{pale}" stroke-width="4"/>',
            f'<path d="M {center} {top - 60} h 38 l -10 12 l 10 12 h -38 Z" fill="{color}" stroke="{pale}" stroke-width="2"/>',
        ]
    if piece == "weather-vane":
        return [
            f'<line x1="{center}" y1="{top}" x2="{center}" y2="{top - 55}" stroke="{pale}" stroke-width="4"/>',
            f'<line x1="{center - 27}" y1="{top - 42}" x2="{center + 27}" y2="{top - 42}" stroke="{pale}" stroke-width="4"/>',
            f'<path d="M {center + 27} {top - 42} l -11 -8 v 16 Z" fill="{pale}"/>',
        ]
    if piece == "mirror-moat":
        return [
            f'<ellipse cx="{center}" cy="{base + 13}" rx="48" ry="11" fill="{color}" stroke="{pale}" stroke-width="2"/>',
            f'<ellipse cx="{center}" cy="{base + 10}" rx="24" ry="5" fill="{pale}" opacity="0.72"/>',
        ]
    if piece == "market-square":
        return [f'<path d="M {x + 10} {base} l 15 -24 l 15 24 Z M {x + 35} {base} l 15 -30 l 15 30 Z M {x + 60} {base} l 13 -21 l 13 21 Z" fill="{pale}" stroke="{dark}" stroke-width="2"/>']
    if piece == "outer-wall":
        return [
            f'<rect x="{x - 8}" y="{base - 46}" width="102" height="46" fill="{color}" stroke="{pale}" stroke-width="3"/>',
            f'<path d="M {x - 8} {base - 46} v -12 h 18 v 12 h 18 v -12 h 18 v 12 h 18 v -12 h 18 v 12 h 12" fill="none" stroke="{pale}" stroke-width="5"/>',
        ]
    raise ChorusError("chorus contains an unknown castle piece")


def _render_svg_bytes(manifest: dict[str, Any]) -> bytes:
    digest = manifest["content_digest"]
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" role="img" aria-labelledby="skycastle-title skycastle-desc">',
        '<title id="skycastle-title">Skycastle Chorus — Yu and Ai</title>',
        '<desc id="skycastle-desc">Ten reviewed fixture signatures rendered as an inert synthetic castle.</desc>',
        '<rect width="1200" height="630" fill="#101A3B"/>',
        '<circle cx="95" cy="92" r="3" fill="#F7F3E8"/><circle cx="212" cy="128" r="2" fill="#F7F3E8"/>',
        '<circle cx="372" cy="78" r="4" fill="#F7F3E8"/><circle cx="566" cy="116" r="2" fill="#F7F3E8"/>',
        '<circle cx="748" cy="69" r="3" fill="#F7F3E8"/><circle cx="896" cy="137" r="2" fill="#F7F3E8"/>',
        '<text x="60" y="70" fill="#F7F3E8" font-family="sans-serif" font-size="34" font-weight="700">Building castles in the sky</text>',
        '<text x="60" y="108" fill="#87CEEB" font-family="sans-serif" font-size="24">Yu and Ai · 天城回聲</text>',
        '<text x="60" y="145" fill="#D9E5FF" font-family="sans-serif" font-size="16">Every name belongs to a reviewed action shape — never a person.</text>',
        '<rect x="48" y="455" width="1104" height="70" rx="8" fill="#233A70" stroke="#F7F3E8" stroke-width="3"/>',
    ]
    for index, tile in enumerate(manifest["tiles"]):
        x = 58 + index * 109
        base = 455
        height = 112 + (index % 4) * 20
        top = base - height
        color = tile["color"]
        label = html.escape(tile["cantonese_name"], quote=True)
        lines.extend([
            f'<rect x="{x}" y="{top}" width="86" height="{height}" rx="5" fill="{color}" stroke="#F7F3E8" stroke-width="3"/>',
            f'<path d="M {x} {top} v -12 h 17 v 12 h 17 v -12 h 18 v 12 h 17 v -12 h 17 v 12" fill="none" stroke="#F7F3E8" stroke-width="5"/>',
            *_piece_svg(tile["castle_piece"], x, top, base, color),
            f'<text x="{x + 43}" y="558" text-anchor="middle" fill="#F7F3E8" font-family="sans-serif" font-size="13">{label}</text>',
            f'<text x="{x + 43}" y="578" text-anchor="middle" fill="#AFC5F5" font-family="sans-serif" font-size="10">{index + 1:02d}</text>',
        ])
    lines.extend([
        '<g aria-label="Lord 202, Architect of Absolutely Nothing">',
        '<circle cx="1030" cy="100" r="38" fill="#F7F3E8"/><circle cx="1068" cy="108" r="30" fill="#F7F3E8"/>',
        '<circle cx="1100" cy="96" r="36" fill="#F7F3E8"/><rect x="1027" y="103" width="105" height="36" rx="18" fill="#F7F3E8"/>',
        '<path d="M 1038 72 Q 1065 42 1092 72 L 1098 82 H 1032 Z" fill="#F6A04D" stroke="#101A3B" stroke-width="3"/>',
        '<circle cx="1060" cy="105" r="4" fill="#101A3B"/><circle cx="1090" cy="105" r="4" fill="#101A3B"/>',
        '<path d="M 1064 122 Q 1075 132 1087 122" fill="none" stroke="#101A3B" stroke-width="3"/>',
        '<text x="1076" y="164" text-anchor="middle" fill="#F6A04D" font-family="sans-serif" font-size="15" font-weight="700">LORD 202</text>',
        '</g>',
        '<text x="600" y="615" text-anchor="middle" fill="#6F8FCF" font-family="monospace" font-size="10">content ' + html.escape(digest[:24], quote=True) + '</text>',
        '</svg>',
    ])
    data = ("\n".join(lines) + "\n").encode("utf-8")
    if len(data) > OUTPUT_BUDGETS["svg_bytes"]:
        raise ChorusError("chorus SVG exceeds its byte budget")
    return data


def _render_wav_bytes(manifest: dict[str, Any]) -> bytes:
    sample_rate = OUTPUT_BUDGETS["sample_rate"]
    tone_samples = OUTPUT_BUDGETS["tone_samples"]
    gap_samples = OUTPUT_BUDGETS["gap_samples"]
    fade_samples = OUTPUT_BUDGETS["fade_samples"]
    amplitude = OUTPUT_BUDGETS["amplitude"]
    frames = bytearray()
    for tile in manifest["tiles"]:
        phase = 0
        increment = (tile["note_hz"] * 65_536) // sample_rate
        for sample_index in range(tone_samples):
            triangle = 32_768 - 2 * abs(phase - 32_768)
            envelope = min(fade_samples, sample_index, tone_samples - sample_index - 1)
            magnitude = abs(triangle) * amplitude * envelope // (32_768 * fade_samples)
            sample = -magnitude if triangle < 0 else magnitude
            frames.extend(struct.pack("<h", sample))
            phase = (phase + increment) & 0xFFFF
        frames.extend(b"\x00\x00" * gap_samples)
    frames.extend(b"\x00\x00" * OUTPUT_BUDGETS["tail_samples"])
    data = bytes(frames)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + len(data), b"WAVE", b"fmt ", 16,
        1, 1, sample_rate, sample_rate * 2, 2, 16, b"data", len(data),
    )
    audio = header + data
    if len(audio) > OUTPUT_BUDGETS["wav_bytes"]:
        raise ChorusError("chorus WAV exceeds its byte budget")
    return audio


def _render_share_bytes(_manifest: dict[str, Any]) -> bytes:
    data = SHARE_COPY.encode("utf-8")
    if len(data) > OUTPUT_BUDGETS["share_text_bytes"]:
        raise ChorusError("chorus share text exceeds its byte budget")
    return data


def _artifact_metadata(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = {
        "svg": _render_svg_bytes(manifest),
        "wav": _render_wav_bytes(manifest),
        "share": _render_share_bytes(manifest),
    }
    return {
        name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        for name, data in artifacts.items()
    }


def _manifest_basis(
    contract: dict[str, Any],
    canary: Any,
    expected: dict[str, Any],
    chorus: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": MANIFEST_SCHEMA,
        "engine": ENGINE,
        "status": "local-preview",
        "source": {
            "scenario": contract["scenario"]["id"],
            "canary_digest": karma.digest_value(canary),
            "receipt_digest": expected["receipt_digest"],
            "core_engine_sha256": contract["bindings"]["engine_sha256"],
        },
        "bindings": {
            **karma.clone_json(chorus["bindings"]),
            "core_rules_sha256": contract["bindings"]["rules_sha256"],
        },
        "banner": chorus["catalog"]["banner"],
        "mascot": karma.clone_json(chorus["catalog"]["mascot"]),
        "release_policy": karma.clone_json(chorus["catalog"]["release_policy"]),
        "tiles": build_tiles(expected, chorus["catalog"]["mappings"]),
        "effects": karma.clone_json(ZERO_EFFECTS),
        "nonclaims": karma.clone_json(chorus["catalog"]["nonclaims"]),
    }


def manifest_value(name: str, canary: Any, supplied_receipt: Any) -> dict[str, Any]:
    detached_canary = karma.clone_json(canary)
    contract, expected = replay_verified(name, detached_canary, supplied_receipt)
    chorus = load_catalog_contract()
    value = _manifest_basis(contract, detached_canary, expected, chorus)
    value["content_digest"] = karma.digest_value(value)
    value["artifacts"] = _artifact_metadata(value)
    value["manifest_digest"] = karma.digest_value(value)
    validate_manifest(value, chorus=chorus)
    return karma.clone_json(value)


def validate_manifest(value: Any, *, chorus: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest = _require_object(value, label="chorus manifest")
    root_fields = {
        "schema", "engine", "status", "source", "bindings", "banner", "mascot",
        "release_policy", "tiles", "effects", "nonclaims", "content_digest",
        "artifacts", "manifest_digest",
    }
    _require_exact_keys(manifest, root_fields, label="chorus manifest")
    if manifest["schema"] != MANIFEST_SCHEMA or manifest["engine"] != ENGINE:
        raise ChorusError("chorus manifest identity mismatch")
    if manifest["status"] != "local-preview" or manifest["banner"] != BANNER:
        raise ChorusError("chorus manifest release state mismatch")
    chorus = load_catalog_contract() if chorus is None else chorus

    source = _require_object(manifest["source"], label="manifest source")
    _require_exact_keys(
        source,
        {"scenario", "canary_digest", "receipt_digest", "core_engine_sha256"},
        label="manifest source",
    )
    if source["scenario"] != "traditional-nine" or source["core_engine_sha256"] != CORE_ENGINE_SHA256:
        raise ChorusError("chorus manifest source mismatch")
    if not _is_digest(source["canary_digest"]) or not _is_digest(source["receipt_digest"]):
        raise ChorusError("chorus manifest source digest mismatch")

    bindings = _require_object(manifest["bindings"], label="manifest bindings")
    _require_exact_keys(
        bindings,
        {"renderer_sha256", "catalog_sha256", "catalog_schema_sha256", "manifest_schema_sha256", "core_rules_sha256"},
        label="manifest bindings",
    )
    expected_bindings = {
        **chorus["bindings"],
        "core_rules_sha256": CORE_PINS["rules"],
    }
    if karma.canonical_bytes(bindings) != karma.canonical_bytes(expected_bindings):
        raise ChorusError("chorus manifest binding mismatch")

    for key in ("mascot", "release_policy", "nonclaims"):
        if karma.canonical_bytes(manifest[key]) != karma.canonical_bytes(chorus["catalog"][key]):
            raise ChorusError(f"chorus manifest {key} mismatch")
    if karma.canonical_bytes(manifest["effects"]) != karma.canonical_bytes(ZERO_EFFECTS):
        raise ChorusError("chorus manifest effects mismatch")

    tiles = manifest["tiles"]
    if not isinstance(tiles, list) or len(tiles) != len(EXPECTED_MAPPING_ROWS):
        raise ChorusError("chorus manifest tile count mismatch")
    expected_tiles = [
        _tile_from_mapping(index, mapping)
        for index, mapping in enumerate(chorus["catalog"]["mappings"], start=1)
    ]
    if karma.canonical_bytes(tiles) != karma.canonical_bytes(expected_tiles):
        raise ChorusError("chorus manifest tiles mismatch")

    for digest_name in ("content_digest", "manifest_digest"):
        if not _is_digest(manifest[digest_name]):
            raise ChorusError("chorus manifest digest shape mismatch")
    basis = {
        key: child for key, child in manifest.items()
        if key not in {"content_digest", "artifacts", "manifest_digest"}
    }
    if manifest["content_digest"] != karma.digest_value(basis):
        raise ChorusError("chorus content digest mismatch")

    artifacts = _require_object(manifest["artifacts"], label="manifest artifacts")
    _require_exact_keys(artifacts, {"svg", "wav", "share"}, label="manifest artifacts")
    for name, metadata_value in artifacts.items():
        metadata = _require_object(metadata_value, label=f"manifest {name} artifact")
        _require_exact_keys(metadata, {"bytes", "sha256"}, label=f"manifest {name} artifact")
        if not _is_integer(metadata["bytes"]) or metadata["bytes"] < 1 or not _is_digest(metadata["sha256"]):
            raise ChorusError("chorus artifact metadata mismatch")
    if karma.canonical_bytes(artifacts) != karma.canonical_bytes(_artifact_metadata(manifest)):
        raise ChorusError("chorus artifact binding mismatch")

    unsigned = {key: child for key, child in manifest.items() if key != "manifest_digest"}
    if manifest["manifest_digest"] != karma.digest_value(unsigned):
        raise ChorusError("chorus manifest digest mismatch")
    if len(karma.canonical_bytes(manifest)) > OUTPUT_BUDGETS["manifest_bytes"]:
        raise ChorusError("chorus manifest exceeds its byte budget")
    return karma.clone_json(manifest)


def render_svg(manifest: dict[str, Any]) -> bytes:
    checked = validate_manifest(manifest)
    return _render_svg_bytes(checked)


def render_wav(manifest: dict[str, Any]) -> bytes:
    checked = validate_manifest(manifest)
    return _render_wav_bytes(checked)


def render_share_text(manifest: dict[str, Any]) -> bytes:
    checked = validate_manifest(manifest)
    return _render_share_bytes(checked)


def verification_value(name: str, canary: Any, supplied_receipt: Any) -> dict[str, Any]:
    detached_canary = karma.clone_json(canary)
    contract, expected = replay_verified(name, detached_canary, supplied_receipt)
    return {
        "schema": "kingdom.skycastle-chorus-source-verification/v1",
        "engine": ENGINE,
        "status": "verified",
        "scenario": contract["scenario"]["id"],
        "canary_digest": karma.digest_value(detached_canary),
        "receipt_digest": expected["receipt_digest"],
        "effects": karma.clone_json(ZERO_EFFECTS),
    }


def verify_manifest_value(
    name: str,
    canary: Any,
    supplied_receipt: Any,
    supplied_manifest: Any,
) -> dict[str, Any]:
    expected = manifest_value(name, canary, supplied_receipt)
    validate_manifest(supplied_manifest)
    if karma.canonical_bytes(supplied_manifest) != karma.canonical_bytes(expected):
        raise ChorusError("chorus manifest did not survive deterministic rebuild")
    return {
        "schema": "kingdom.skycastle-chorus-manifest-verification/v1",
        "engine": ENGINE,
        "status": "verified",
        "scenario": "traditional-nine",
        "manifest_digest": expected["manifest_digest"],
        "effects": karma.clone_json(ZERO_EFFECTS),
    }


def _read_sources(canary_path: Path, receipt_path: Path) -> tuple[Any, Any]:
    canary = karma.read_json_file(
        canary_path,
        limit=karma.BUDGETS["supplied_input_bytes"],
        label="chorus canary",
    )
    receipt = karma.read_json_file(
        receipt_path,
        limit=karma.BUDGETS["supplied_input_bytes"],
        label="chorus receipt",
    )
    return canary, receipt


def _emit_once(data: bytes) -> None:
    sys.stdout.buffer.write(data)


def _json_line(value: Any) -> bytes:
    data = karma.canonical_bytes(value) + b"\n"
    if len(data) > OUTPUT_BUDGETS["manifest_bytes"]:
        raise ChorusError("chorus JSON output exceeds its byte budget")
    return data


def _usage_error() -> ChorusError:
    return ChorusError("invalid skycastle chorus command")


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        if arguments in (["check"], ["digest"]):
            checked = check_value()
            value = checked if arguments[0] == "check" else {
                "schema": "kingdom.skycastle-chorus-digest/v1",
                "engine": ENGINE,
                "bindings": checked["bindings"],
            }
            _emit_once(_json_line(value))
            return 0

        source_commands = {
            "verify-source", "render-manifest", "render-svg", "render-wav", "share-copy",
        }
        if len(arguments) == 4 and arguments[0] in source_commands:
            command, name = arguments[0], arguments[1]
            canary, receipt = _read_sources(Path(arguments[2]), Path(arguments[3]))
            if command == "verify-source":
                output = _json_line(verification_value(name, canary, receipt))
            else:
                manifest = manifest_value(name, canary, receipt)
                outputs = {
                    "render-manifest": lambda: _json_line(manifest),
                    "render-svg": lambda: render_svg(manifest),
                    "render-wav": lambda: render_wav(manifest),
                    "share-copy": lambda: render_share_text(manifest),
                }
                output = outputs[command]()
            _emit_once(output)
            return 0

        if len(arguments) == 5 and arguments[0] == "verify-manifest":
            _, name, canary_name, receipt_name, manifest_name = arguments
            canary, receipt = _read_sources(Path(canary_name), Path(receipt_name))
            supplied_manifest = karma.read_json_file(
                Path(manifest_name),
                limit=OUTPUT_BUDGETS["manifest_input_bytes"],
                label="chorus manifest",
            )
            _emit_once(_json_line(verify_manifest_value(name, canary, receipt, supplied_manifest)))
            return 0
        raise _usage_error()
    except (ChorusError, karma.LabInputError, KeyError, TypeError, IndexError):
        sys.stderr.buffer.write(b"skycastle-chorus: rejected\n")
        return 2
    except BrokenPipeError:
        return 141
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
