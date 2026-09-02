#!/usr/bin/env python3
"""x402 seller split: builder code gets a cut. Not a campaign. No rail."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping


PLAN_SCHEMA = "kingdom.x402.aff-plan/v1"
SETTLEMENT_SCHEMA = "kingdom.x402.settlement/v1"
AFF_SCHEMA = "kingdom.x402.aff/v1"
RESERVE_SCHEMA = "kingdom.x402.aff.reserve/v1"
DEFAULT_BPS = 1000
BPS_DENOM = 10000
BUILDER = re.compile(r"^[a-z0-9_]{1,32}$")
ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")
SETTLEMENT_KEYS = (
    "schema",
    "seller_pay_to",
    "amount_atomic",
    "asset",
    "network",
    "builder_code",
    "builder_share_bps",
    "settlement_id",
    "observed_at",
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
        "clicks",
        "click_count",
        "reach",
    }
)


class AffError(ValueError):
    """Seller split refused an input."""

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
        raise AffError("invalid_aff", f"{what} must be an object")
    return dict(value)


def _exact_keys(payload: Mapping[str, Any], keys: tuple[str, ...], what: str) -> None:
    expected = set(keys)
    got = set(payload)
    extra = got - expected
    missing = expected - got
    if extra:
        raise AffError("unexpected_keys", f"{what} has unexpected keys: {sorted(extra)}")
    if missing:
        raise AffError("missing_keys", f"{what} missing keys: {sorted(missing)}")


def _scan_metrics(payload: Mapping[str, Any], where: str) -> None:
    found = sorted(key for key in payload if key in METRIC_KEYS)
    if found:
        raise AffError(
            "engagement_metrics_forbidden",
            f"{where} carries engagement metrics: {found}",
        )


def _address(value: object, what: str) -> str:
    if not isinstance(value, str) or not ADDRESS.fullmatch(value):
        raise AffError("invalid_address", f"{what} must be a 20-byte hex address")
    return value.lower()


def _atomic(value: object, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, str) or not value.isdigit():
        raise AffError("invalid_amount", f"{what} must be a decimal string of atomic units")
    amount = int(value)
    if amount <= 0:
        raise AffError("invalid_amount", f"{what} must be a positive atomic amount")
    return amount


def plan() -> dict[str, Any]:
    return {
        "bookable": False,
        "builder_share_bps": DEFAULT_BPS,
        "campaign": False,
        "engagement": False,
        "network_performed": False,
        "official_kingdom_mouth": False,
        "schema": PLAN_SCHEMA,
        "split_when": "builder_code present and dust does not round the builder share to zero",
    }


def ingest(payload: Mapping[str, Any]) -> dict[str, Any]:
    body = _mapping(payload, "settlement")
    _scan_metrics(body, "settlement")
    _exact_keys(body, SETTLEMENT_KEYS, "settlement")
    if body["schema"] != SETTLEMENT_SCHEMA:
        raise AffError("schema_mismatch", "settlement schema must be kingdom.x402.settlement/v1")
    seller_pay_to = _address(body["seller_pay_to"], "seller_pay_to")
    asset = _address(body["asset"], "asset")
    network = body["network"]
    if not isinstance(network, str) or not network.strip():
        raise AffError("invalid_string", "network is required")
    settlement_id = body["settlement_id"]
    if not isinstance(settlement_id, str) or not settlement_id.strip():
        raise AffError("invalid_string", "settlement_id is required")
    observed_at = body["observed_at"]
    if not isinstance(observed_at, str) or not observed_at.strip():
        raise AffError("invalid_string", "observed_at is required")
    amount = _atomic(body["amount_atomic"], "amount_atomic")
    bps = body["builder_share_bps"]
    if not isinstance(bps, int) or isinstance(bps, bool) or bps < 0:
        raise AffError("invalid_share", "builder_share_bps must be a non-negative integer")
    if bps > BPS_DENOM:
        raise AffError("share_too_wide", "builder_share_bps cannot exceed 10000")
    raw_code = body["builder_code"]
    if raw_code is None:
        builder_code = None
    elif isinstance(raw_code, str) and BUILDER.fullmatch(raw_code):
        builder_code = raw_code
    else:
        raise AffError("invalid_builder_code", "builder_code must be 1–32 lowercase letters, digits, or underscore")
    builder_share = 0
    if builder_code is not None:
        builder_share = (amount * bps) // BPS_DENOM
    seller_share = amount - builder_share
    split = builder_share > 0
    canonical = {
        "amount_atomic": str(amount),
        "asset": asset,
        "builder_code": builder_code,
        "builder_share_atomic": str(builder_share),
        "builder_share_bps": bps,
        "network": network.strip(),
        "schema": AFF_SCHEMA,
        "seller_pay_to": seller_pay_to,
        "seller_share_atomic": str(seller_share),
        "settlement_id": settlement_id.strip(),
        "split": split,
    }
    return {
        "aff_id": digest_value(canonical),
        "amount_atomic": str(amount),
        "asset": asset,
        "bookable": False,
        "builder_code": builder_code,
        "builder_share_atomic": str(builder_share),
        "builder_share_bps": bps,
        "campaign": False,
        "engagement": False,
        "network": network.strip(),
        "network_performed": False,
        "observed_at": observed_at.strip(),
        "official_kingdom_mouth": False,
        "schema": AFF_SCHEMA,
        "seller_pay_to": seller_pay_to,
        "seller_share_atomic": str(seller_share),
        "settlement_id": settlement_id.strip(),
        "split": split,
        "taint": "settlement",
    }


def reserve(aff: Mapping[str, Any]) -> dict[str, Any]:
    body = _mapping(aff, "aff")
    if body.get("schema") != AFF_SCHEMA:
        raise AffError("schema_mismatch", "reserve requires a kingdom.x402.aff/v1 receipt")
    payload = {
        "builder_code": body.get("builder_code"),
        "builder_share_atomic": body.get("builder_share_atomic"),
        "schema": RESERVE_SCHEMA,
        "seller_share_atomic": body.get("seller_share_atomic"),
        "settlement_id": body.get("settlement_id"),
        "split": body.get("split"),
    }
    return {
        "bookable": False,
        "builder_code": body.get("builder_code"),
        "builder_share_atomic": body.get("builder_share_atomic"),
        "campaign": False,
        "engagement": False,
        "execution_allowed": False,
        "liquid_usd_effect": "none",
        "network_performed": False,
        "reserve_id": digest_value(payload),
        "schema": RESERVE_SCHEMA,
        "seller_pay_to": body.get("seller_pay_to"),
        "seller_share_atomic": body.get("seller_share_atomic"),
        "settlement_id": body.get("settlement_id"),
        "split": body.get("split"),
        "taint": "settlement",
    }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _print(value: Mapping[str, Any]) -> None:
    sys.stdout.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kingdom x402",
        description="x402 seller split: a builder cut on a settlement. Never a campaign.",
    )
    sub = parser.add_subparsers(dest="family", required=True)
    aff_cmd = sub.add_parser("aff", help="ingest a settlement and split; never books reserve")
    aff_sub = aff_cmd.add_subparsers(dest="aff_command", required=True)
    aff_sub.add_parser("plan", help="print the split shape; does not touch a rail")
    ingest_cmd = aff_sub.add_parser("ingest", help="split a caller-supplied settlement")
    ingest_cmd.add_argument("settlement", type=Path)
    reserve_cmd = aff_sub.add_parser("reserve", help="shadow reserve receipt; bookable stays false")
    reserve_cmd.add_argument("settlement", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.aff_command == "plan":
            _print(plan())
        elif args.aff_command == "ingest":
            _print(ingest(load_json(args.settlement)))
        elif args.aff_command == "reserve":
            _print(reserve(ingest(load_json(args.settlement))))
    except AffError as error:
        sys.stderr.write(f"{error.code}: {error}\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
