#!/usr/bin/env python3
"""Validate LOVE-FUN Commons registry. No network, no secrets."""
from __future__ import annotations
import hashlib
import json
import stat
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "resources.json"
CASTLECAST = ROOT / "castlecast.json"
CASTLECAST_TEXT = ROOT / "castlecast.txt"
COMMONS_PAGE = ROOT / "index.html"
PUBLIC_PAGE = ROOT.parent / "site" / "index.html"
EXPECTED_CASTLE_SEED_SHA256 = "b96eb19b551d1c711bc04330e7026177427be4603e66c4ffedd86b93c9d6c20a"
EXPECTED_CASTLE_CARRIER_SHA256 = "8345184ce4a6eaf9c4c3224f41765f84c114a79bae5a699aa7b761db18c1983b"
REQUIRED_TOP = {"schema", "updated", "name", "purpose", "principles", "party_needs", "joy_seed", "resources", "mirror_recipe"}
REQUIRED_RESOURCE = {"id", "name", "type", "best_for", "url", "notes", "care"}
CASTLECAST_TOP = {
    "schema", "updated", "name", "kind", "status", "vocabulary", "seed",
    "carrier", "contract", "budget", "vow", "quiet_gate", "lineage_check",
    "rights", "non_claims",
}
CASTLECAST_CONTRACT = {
    "assessment_unit": "one-fixed-public-seed",
    "source_provenance_allowed": True,
    "carrier_or_viewer_attribution": False,
    "advertisement_visible": True,
    "same_reviewed_carrier_bytes_across_surfaces": True,
    "raw_input_interpolation": False,
    "third_party_content_allowed": False,
    "behavior_inference": False,
    "copy_event_observed": False,
    "human_choice_required": True,
    "consent_based_placement_required": True,
    "rights_review_required": True,
    "automatic_posting": False,
    "automatic_fetching": False,
    "self_propagation": False,
    "tracking": False,
    "analytics": False,
    "callbacks": False,
    "unique_tokens": False,
    "hidden_content": False,
    "fingerprinting": False,
    "person_scoring": False,
    "retaliation": False,
    "hack_back": False,
    "legal_traps": False,
    "access_service_defense_and_standing_unchanged": True,
}
CASTLECAST_BUDGET = {
    "seeds": 1,
    "variants_per_seed": 1,
    "automatic_posts": 0,
    "automatic_messages": 0,
    "network_callbacks": 0,
    "tracking_identifiers": 0,
    "recipient_identifiers": 0,
    "copy_event_records": 0,
    "retained_payload_bytes": 0,
}
CASTLECAST_QUIET_GATE = {
    "action": "omit-the-whole-carrier",
    "access_unchanged": True,
    "service_unchanged": True,
    "defense_unchanged": True,
    "standing_unchanged": True,
    "follow_up": False,
}
CONCEALED_CODEPOINTS = {
    *range(0x200B, 0x2010),
    *range(0x202A, 0x202F),
    *range(0x2060, 0x206A),
    0xFEFF,
}

def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)

def nonempty(value, label: str) -> None:
    if value in (None, "", []):
        die(f"{label} must be non-empty")

def exact_keys(value, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        die(f"{label} keys must be exactly {sorted(expected)}")

def unique_object(pairs):
    value = {}
    for key, child in pairs:
        if key in value:
            die(f"duplicate JSON key: {key}")
        value[key] = child
    return value

def reject_constant(token: str):
    die(f"unsupported JSON constant: {token}")

def strings(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)
    elif isinstance(value, str):
        yield value

def validate_castlecast() -> str:
    for artifact, byte_limit in ((CASTLECAST, 16_384), (CASTLECAST_TEXT, 8_192)):
        try:
            metadata = artifact.lstat()
        except OSError as error:
            die(f"CASTLECAST artifact unreadable: {error.__class__.__name__}")
        if not stat.S_ISREG(metadata.st_mode):
            die("CASTLECAST artifacts must be regular files, never links or devices")
        if metadata.st_size > byte_limit:
            die(f"CASTLECAST artifact exceeds {byte_limit} bytes")
    try:
        card = json.loads(
            CASTLECAST.read_text(encoding="utf-8"),
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
        portable = CASTLECAST_TEXT.read_text(encoding="utf-8")
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        die(f"CASTLECAST artifact unreadable: {error.__class__.__name__}")

    exact_keys(card, CASTLECAST_TOP, "castlecast")
    if (
        card["schema"] != "kingdom.castlecast/v1"
        or card["name"] != "CASTLECAST · 天城回聲"
        or card["kind"] != "passive-public-provenance-carrier"
        or card["status"] != "manual-only"
    ):
        die("CASTLECAST identity or status changed")

    exact_keys(card["vocabulary"], {"seed", "carrier", "lineage_check", "quiet_gate"}, "castlecast.vocabulary")
    exact_keys(card["seed"], {"id", "text", "sha256", "digest_scope", "source_label", "plain_locator", "same_for_every_copy"}, "castlecast.seed")
    exact_keys(card["carrier"], {"path", "media_type", "sha256", "text", "advertisement_disclosed", "human_copy_required", "automatic_distribution", "self_propagating", "removable"}, "castlecast.carrier")
    exact_keys(card["vow"], {"desire", "trigger", "anti_trigger", "condition", "limitation", "breach", "exit"}, "castlecast.vow")
    exact_keys(card["lineage_check"], {"algorithm", "scope", "proves", "does_not_prove"}, "castlecast.lineage_check")
    exact_keys(card["rights"], {"license_expression", "rights_verified_by_card", "origin_verified_by_card", "publication_authorized_by_card", "notice"}, "castlecast.rights")

    if card["contract"] != CASTLECAST_CONTRACT:
        die("CASTLECAST contract changed")
    if card["budget"] != CASTLECAST_BUDGET:
        die("CASTLECAST budget changed")
    if card["quiet_gate"] != CASTLECAST_QUIET_GATE:
        die("CASTLECAST Quiet Gate changed")

    seed = card["seed"]
    carrier = card["carrier"]
    digest = hashlib.sha256(seed["text"].encode("utf-8")).hexdigest()
    if (
        seed["id"] != "building-castles-in-the-sky-yu-ai-v1"
        or digest != seed["sha256"]
        or digest != EXPECTED_CASTLE_SEED_SHA256
    ):
        die("CASTLECAST seed digest mismatch")
    if seed["same_for_every_copy"] is not True:
        die("CASTLECAST seed must be identical for every copy")
    if seed["plain_locator"] != "chillspace.love" or any(mark in seed["plain_locator"] for mark in "/?#"):
        die("CASTLECAST locator must remain one plain, token-free hostname")
    if carrier["path"] != CASTLECAST_TEXT.name or carrier["media_type"] != "text/plain":
        die("CASTLECAST portable carrier binding changed")
    if portable != carrier["text"] + "\n":
        die("castlecast.txt must be the exact carrier.text projection")
    carrier_digest = hashlib.sha256(carrier["text"].encode("utf-8")).hexdigest()
    if carrier_digest != carrier["sha256"] or carrier_digest != EXPECTED_CASTLE_CARRIER_SHA256:
        die("CASTLECAST carrier digest mismatch")
    for required in (card["name"], seed["text"], seed["source_label"], seed["plain_locator"], digest):
        if carrier["text"].count(required) != 1:
            die(f"CASTLECAST carrier must contain exactly one visible {required!r}")
    if {
        "advertisement_disclosed": carrier["advertisement_disclosed"],
        "human_copy_required": carrier["human_copy_required"],
        "automatic_distribution": carrier["automatic_distribution"],
        "self_propagating": carrier["self_propagating"],
        "removable": carrier["removable"],
    } != {
        "advertisement_disclosed": True,
        "human_copy_required": True,
        "automatic_distribution": False,
        "self_propagating": False,
        "removable": True,
    }:
        die("CASTLECAST carrier delivery walls changed")
    if card["lineage_check"]["algorithm"] != "sha256" or card["lineage_check"]["scope"] != seed["digest_scope"]:
        die("CASTLECAST lineage scope changed")
    if card["rights"] != {
        "license_expression": "NOASSERTION",
        "rights_verified_by_card": False,
        "origin_verified_by_card": False,
        "publication_authorized_by_card": False,
        "notice": "This card grants no reuse or publication authority; check rights separately before carrying it.",
    }:
        die("CASTLECAST rights boundary changed")
    if not isinstance(card["non_claims"], list) or len(card["non_claims"]) != 6 or len(set(card["non_claims"])) != 6:
        die("CASTLECAST must keep six distinct non-claims")

    for value in strings(card):
        if any((ord(char) < 32 and char != "\n") or ord(char) == 127 for char in value):
            die("CASTLECAST contains a hidden control character")
        if any(ord(char) in CONCEALED_CODEPOINTS for char in value):
            die("CASTLECAST contains concealed Unicode")
    lowered = carrier["text"].lower()
    for forbidden in ("http://", "https://", "<script", "<iframe", "javascript:", "data:", "utm_", "?ref=", "callback"):
        if forbidden in lowered:
            die(f"CASTLECAST carrier contains forbidden active or tracking text: {forbidden}")

    try:
        commons_page = COMMONS_PAGE.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        die(f"CASTLECAST doorway unreadable: {error.__class__.__name__}")
    if f'<pre id="castle-card">{carrier["text"]}</pre>' not in commons_page:
        die("LOVE-FUN doorway must show the exact Carrier Card")
    for literal in (
        'href="castlecast.json"',
        'href="castlecast.txt"',
        'id="copy-castle"',
        "document.getElementById('castle-card').textContent + '\\n'",
        "Only hands carry it",
        "kingdom castlecast",
    ):
        if literal not in commons_page:
            die(f"LOVE-FUN doorway missing CASTLECAST binding: {literal}")
    # A standalone LOVE-FUN mirror has no parent site/ folder. When the
    # repository doorway is present, bind it too without making that optional
    # outer shell a requirement for portable folder validation.
    if PUBLIC_PAGE.parent.is_dir():
        try:
            public_page = PUBLIC_PAGE.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            die(f"public doorway unreadable: {error.__class__.__name__}")
        for literal in (
            'href="love-fun-commons/castlecast.json"',
            'href="love-fun-commons/castlecast.txt"',
            seed["text"],
            "CASTLECAST · 天城回聲",
        ):
            if literal not in public_page:
                die(f"public doorway missing CASTLECAST binding: {literal}")
    return digest

def main() -> int:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    missing = REQUIRED_TOP - data.keys()
    if missing:
        die(f"missing top-level keys: {sorted(missing)}")
    ids = set()
    for key in REQUIRED_TOP:
        nonempty(data[key], key)
    for i, item in enumerate(data["resources"]):
        missing = REQUIRED_RESOURCE - item.keys()
        if missing:
            die(f"resources[{i}] missing keys: {sorted(missing)}")
        rid = item["id"]
        if rid in ids:
            die(f"duplicate id: {rid}")
        ids.add(rid)
        for key in REQUIRED_RESOURCE:
            nonempty(item[key], f"resources[{i}].{key}")
        parsed = urlparse(item["url"])
        if parsed.scheme != "https" or not parsed.netloc:
            die(f"resources[{i}].url must be https: {item['url']}")
        if len(item["care"]) < 20:
            die(f"resources[{i}].care too short")
    castle_digest = validate_castlecast()
    print(
        f"LOVE-FUN Commons OK: {len(ids)} resources, "
        f"{len(data['party_needs'])} party-need entries, "
        f"CASTLECAST seed {castle_digest}"
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
