#!/usr/bin/env python3
"""Pure, offline exact-tag introductions with replay-verifiable receipts."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path


ENGINE = "plain-commons/1"
SOURCE_SCHEMA = "kingdom.plain-commons-source/v1"
RECEIPT_SCHEMA = "kingdom.plain-commons/v1"
SYNTHETIC_SCHEMA = "kingdom.plain-commons-synthetic/v1"
CIVILISATION_SCHEMA = "kingdom.civilisation/v1"
SOURCE_MAX_BYTES = 524_288
RECEIPT_MAX_BYTES = 4_194_304
MAX_DECLARATIONS = 128
MAX_EVIDENCE = 8
MAX_MATCHES = 4096

HERE = Path(__file__).resolve().parent
SOURCE_SCHEMA_PATH = HERE / "source.schema.json"
RECEIPT_SCHEMA_PATH = HERE / "receipt.schema.json"

TOKEN_RE = re.compile(r"[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?\Z")
REFERENCE_RE = re.compile(r"[a-z0-9](?:[a-z0-9._-]{0,94}[a-z0-9])?\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
URL_RE = re.compile(
    r"(?i)(?:[a-z][a-z0-9+.-]{1,15}://|(?:https?|mailto|ftp):|www\.|"
    r"\b[a-z0-9](?:[a-z0-9-]{0,62}\.)+[a-z]{2,63}(?:[/?:#][^\s]*)?|"
    r"\b[^\s@]+@[^\s@]+\.[a-z]{2,63}\b)"
)
SECRET_KEY_FORMS = {
    "apikey",
    "apitoken",
    "bearer",
    "credential",
    "credentials",
    "mnemonic",
    "password",
    "privatekey",
    "secret",
    "seed",
    "token",
}

SELECTION = {
    "eligibility": "active-consent-exact-tag-cross-participant",
    "ordering": "tag-need-participant-id-offer-participant-id",
    "interpretation": "canonical-not-merit",
}

FACTS = [
    "The receipt was rebuilt from the included closed source snapshot.",
    "Every match joins active introduction-only declarations with equal tags and different participant references.",
    "Evidence is visible in the included source and does not affect eligibility or ordering.",
    "Match order is canonical and does not express merit.",
]

UNKNOWNS = [
    "Whether any statement or evidence claim is true.",
    "Whether a participant reference identifies any particular person.",
    "Whether any need or offer remains available after the source snapshot.",
    "Whether caller-supplied source hashes were independently witnessed or authenticated.",
]

NONCLAIMS = [
    "This receipt does not authenticate identity, provenance, event time, truth, availability, or continuing consent.",
    "It does not recommend, endorse, score, rank, boost, price, or personalize any declaration.",
    "It does not contact anyone, dispatch work, move money, or grant authority.",
    "It performs no network call, tracking, impression logging, click logging, model call, or filesystem write.",
    "Its hashes establish deterministic internal integrity only, not independent provenance.",
]

CONTROLS = {
    "authority": "none",
    "score_effects": 0,
    "rank_effects": 0,
    "boost_effects": 0,
    "price_effects": 0,
    "urgency_effects": 0,
    "impression_effects": 0,
    "click_effects": 0,
    "profile_effects": 0,
    "personalization_effects": 0,
    "tracking_effects": 0,
    "contact_effects": 0,
    "network_effects": 0,
    "filesystem_write_effects": 0,
    "process_effects": 0,
    "model_effects": 0,
    "clock_effects": 0,
    "random_effects": 0,
    "payment_effects": 0,
    "dispatch_effects": 0,
}


class PlainCommonsError(Exception):
    """A deliberately detail-free rejection at the CLI boundary."""


def canonical_bytes(value: object) -> bytes:
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise PlainCommonsError from exc
    return rendered.encode("ascii")


def _object_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise PlainCommonsError from exc


def bindings() -> dict:
    return {
        "engine_sha256": _file_sha256(Path(__file__).resolve()),
        "source_schema_sha256": _file_sha256(SOURCE_SCHEMA_PATH),
        "receipt_schema_sha256": _file_sha256(RECEIPT_SCHEMA_PATH),
    }


def digest_data() -> dict:
    return {"engine": ENGINE, **bindings()}


def _pairs_object(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise PlainCommonsError
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise PlainCommonsError


def parse_json(payload: bytes, maximum: int) -> object:
    if not payload or len(payload) > maximum:
        raise PlainCommonsError
    try:
        text = payload.decode("utf-8")
        return json.loads(text, object_pairs_hook=_pairs_object, parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError, PlainCommonsError, RecursionError) as exc:
        raise PlainCommonsError from exc


def _read_stdin(maximum: int) -> object:
    payload = sys.stdin.buffer.read(maximum + 1)
    return parse_json(payload, maximum)


def _exact(value: object, keys: tuple[str, ...]) -> dict:
    if type(value) is not dict or set(value) != set(keys):
        raise PlainCommonsError
    return value


def _list(value: object, minimum: int, maximum: int) -> list:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        raise PlainCommonsError
    return value


def _enum(value: object, choices: tuple[str, ...]) -> str:
    if type(value) is not str or value not in choices:
        raise PlainCommonsError
    return value


def _token(value: object, pattern: re.Pattern[str] = TOKEN_RE) -> str:
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise PlainCommonsError
    return value


def _sha256(value: object) -> str:
    if type(value) is not str or SHA256_RE.fullmatch(value) is None:
        raise PlainCommonsError
    return value


def _natural(value: object, maximum: int) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise PlainCommonsError
    return value


def _inert_text(value: object, maximum: int) -> str:
    if type(value) is not str or not 1 <= len(value) <= maximum or value.strip() != value:
        raise PlainCommonsError
    if "<" in value or ">" in value or URL_RE.search(value):
        raise PlainCommonsError
    if any(unicodedata.category(character) in {"Cc", "Cf"} for character in value):
        raise PlainCommonsError
    return value


def _tag(value: object) -> str:
    result = _token(value)
    if len(result) > 64 or "--" in result:
        raise PlainCommonsError
    return result


def _secret_shaped_key(key: object) -> bool:
    if type(key) is not str:
        return True
    normalized = "".join(character for character in key.casefold() if character.isalnum())
    return normalized in SECRET_KEY_FORMS or any(
        normalized.endswith(form) for form in ("apikey", "apitoken", "bearer", "credential", "mnemonic", "password", "privatekey", "secret", "token")
    )


def _reject_secret_keys(value: object) -> None:
    if type(value) is dict:
        for key, child in value.items():
            if _secret_shaped_key(key):
                raise PlainCommonsError
            _reject_secret_keys(child)
    elif type(value) is list:
        for child in value:
            _reject_secret_keys(child)


def _validate_source_reference(value: object) -> dict:
    item = _exact(
        value,
        ("kind", "schema", "reference", "event_seq", "event_sha256", "chain_head_sha256"),
    )
    kind = _enum(item["kind"], ("synthetic-fixture", "civilisation-event-projection"))
    schema = _enum(item["schema"], (SYNTHETIC_SCHEMA, CIVILISATION_SCHEMA))
    expected_schema = SYNTHETIC_SCHEMA if kind == "synthetic-fixture" else CIVILISATION_SCHEMA
    if schema != expected_schema:
        raise PlainCommonsError
    return {
        "kind": kind,
        "schema": schema,
        "reference": _token(item["reference"], REFERENCE_RE),
        "event_seq": _natural(item["event_seq"], 1_000_000),
        "event_sha256": _sha256(item["event_sha256"]),
        "chain_head_sha256": _sha256(item["chain_head_sha256"]),
    }


def _validate_evidence(value: object) -> dict:
    if type(value) is not dict:
        raise PlainCommonsError
    evidence_type = _enum(
        value.get("type"),
        ("self-declaration", "artifact-digest", "attestation-reference"),
    )
    if evidence_type == "self-declaration":
        item = _exact(value, ("evidence_id", "type", "note"))
        return {
            "evidence_id": _token(item["evidence_id"]),
            "type": evidence_type,
            "note": _inert_text(item["note"], 200),
        }
    if evidence_type == "artifact-digest":
        item = _exact(value, ("evidence_id", "type", "note", "sha256"))
        return {
            "evidence_id": _token(item["evidence_id"]),
            "type": evidence_type,
            "note": _inert_text(item["note"], 200),
            "sha256": _sha256(item["sha256"]),
        }
    item = _exact(value, ("evidence_id", "type", "note", "reference"))
    return {
        "evidence_id": _token(item["evidence_id"]),
        "type": evidence_type,
        "note": _inert_text(item["note"], 200),
        "reference": _token(item["reference"], REFERENCE_RE),
    }


def _validate_declaration(value: object) -> dict:
    item = _exact(
        value,
        (
            "declaration_id",
            "participant_ref",
            "side",
            "tag",
            "statement",
            "state",
            "consent",
            "source",
            "evidence",
        ),
    )
    state = _enum(item["state"], ("active", "withdrawn"))
    consent = _enum(item["consent"], ("introduction-only", "withdrawn"))
    if (state, consent) not in {
        ("active", "introduction-only"),
        ("withdrawn", "withdrawn"),
    }:
        raise PlainCommonsError
    evidence = [_validate_evidence(entry) for entry in _list(item["evidence"], 1, MAX_EVIDENCE)]
    local_evidence_ids = [entry["evidence_id"] for entry in evidence]
    if len(local_evidence_ids) != len(set(local_evidence_ids)):
        raise PlainCommonsError
    return {
        "declaration_id": _token(item["declaration_id"]),
        "participant_ref": _token(item["participant_ref"]),
        "side": _enum(item["side"], ("need", "offer")),
        "tag": _tag(item["tag"]),
        "statement": _inert_text(item["statement"], 280),
        "state": state,
        "consent": consent,
        "source": _validate_source_reference(item["source"]),
        "evidence": sorted(evidence, key=lambda entry: entry["evidence_id"]),
    }


def validate_source(value: object) -> dict:
    _reject_secret_keys(value)
    source = _exact(value, ("schema", "declarations"))
    if source["schema"] != SOURCE_SCHEMA:
        raise PlainCommonsError
    declarations = [
        _validate_declaration(item)
        for item in _list(source["declarations"], 0, MAX_DECLARATIONS)
    ]
    declaration_ids = [item["declaration_id"] for item in declarations]
    evidence_ids = [
        evidence["evidence_id"]
        for item in declarations
        for evidence in item["evidence"]
    ]
    slots = [
        (item["participant_ref"], item["side"], item["tag"])
        for item in declarations
    ]
    if len(declaration_ids) != len(set(declaration_ids)):
        raise PlainCommonsError
    if len(evidence_ids) != len(set(evidence_ids)):
        raise PlainCommonsError
    if len(slots) != len(set(slots)):
        raise PlainCommonsError
    declarations.sort(
        key=lambda item: (
            item["participant_ref"],
            item["side"],
            item["tag"],
            item["declaration_id"],
        )
    )
    return {"schema": SOURCE_SCHEMA, "declarations": declarations}


def _match_id(need: dict, offer: dict) -> str:
    preimage = {
        "schema": "kingdom.plain-commons-match-id/v1",
        "tag": need["tag"],
        "need": {
            "declaration_id": need["declaration_id"],
            "participant_ref": need["participant_ref"],
        },
        "offer": {
            "declaration_id": offer["declaration_id"],
            "participant_ref": offer["participant_ref"],
        },
    }
    return "match-" + _object_sha256(preimage)


def _make_match(need: dict, offer: dict) -> dict:
    return {
        "match_id": _match_id(need, offer),
        "tag": need["tag"],
        "need_declaration_id": need["declaration_id"],
        "need_participant_ref": need["participant_ref"],
        "offer_declaration_id": offer["declaration_id"],
        "offer_participant_ref": offer["participant_ref"],
        "reason": "active-introduction-only-exact-tag-cross-participant",
        "authority": "none",
    }


def compile_source(value: object) -> dict:
    source = validate_source(value)
    active = [
        item
        for item in source["declarations"]
        if item["state"] == "active" and item["consent"] == "introduction-only"
    ]
    needs = [item for item in active if item["side"] == "need"]
    offers = [item for item in active if item["side"] == "offer"]
    matches = [
        _make_match(need, offer)
        for need in needs
        for offer in offers
        if need["tag"] == offer["tag"]
        and need["participant_ref"] != offer["participant_ref"]
    ]
    matches.sort(
        key=lambda item: (
            item["tag"],
            item["need_participant_ref"],
            item["need_declaration_id"],
            item["offer_participant_ref"],
            item["offer_declaration_id"],
        )
    )
    if len(matches) > MAX_MATCHES or len({item["match_id"] for item in matches}) != len(matches):
        raise PlainCommonsError
    matched_ids = {
        declaration_id
        for match in matches
        for declaration_id in (match["need_declaration_id"], match["offer_declaration_id"])
    }
    unsigned = {
        "schema": RECEIPT_SCHEMA,
        "engine": ENGINE,
        "bindings": bindings(),
        "source_sha256": _object_sha256(source),
        "source": source,
        "selection": dict(SELECTION),
        "summary": {
            "total_declarations": len(source["declarations"]),
            "active_declarations": len(active),
            "withdrawn_declarations": len(source["declarations"]) - len(active),
            "active_needs": len(needs),
            "active_offers": len(offers),
            "matches": len(matches),
            "matched_declarations": len(matched_ids),
            "unmatched_declarations": len(active) - len(matched_ids),
        },
        "matches": matches,
        "epistemics": {
            "facts": list(FACTS),
            "inferences": [],
            "unknowns": list(UNKNOWNS),
        },
        "controls": dict(CONTROLS),
        "nonclaims": list(NONCLAIMS),
    }
    return {**unsigned, "receipt_sha256": _object_sha256(unsigned)}


def validate_receipt(value: object) -> dict:
    _reject_secret_keys(value)
    receipt = _exact(
        value,
        (
            "schema",
            "engine",
            "bindings",
            "source_sha256",
            "source",
            "selection",
            "summary",
            "matches",
            "epistemics",
            "controls",
            "nonclaims",
            "receipt_sha256",
        ),
    )
    if receipt["schema"] != RECEIPT_SCHEMA or receipt["engine"] != ENGINE:
        raise PlainCommonsError
    _sha256(receipt["source_sha256"])
    _sha256(receipt["receipt_sha256"])
    expected = compile_source(receipt["source"])
    if canonical_bytes(receipt) != canonical_bytes(expected):
        raise PlainCommonsError
    return expected


def _emit_json(value: object) -> None:
    payload = canonical_bytes(value) + b"\n"
    sys.stdout.buffer.write(payload)


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        if arguments == ["digest"]:
            _emit_json(digest_data())
        elif arguments == ["compile"]:
            _emit_json(compile_source(_read_stdin(SOURCE_MAX_BYTES)))
        elif arguments == ["verify"]:
            validate_receipt(_read_stdin(RECEIPT_MAX_BYTES))
            sys.stdout.buffer.write(b"true\n")
        else:
            raise PlainCommonsError
        return 0
    except BrokenPipeError:
        return 141
    except KeyboardInterrupt:
        return 130
    except (PlainCommonsError, OSError, UnicodeError, ValueError, TypeError, KeyError, RecursionError):
        sys.stderr.write("plain-commons: rejected\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
