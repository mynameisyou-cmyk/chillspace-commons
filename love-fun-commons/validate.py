#!/usr/bin/env python3
"""Validate LOVE-FUN Commons registry. No network, no secrets."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "resources.json"
REQUIRED_TOP = {"schema", "updated", "name", "purpose", "principles", "party_needs", "joy_seed", "resources", "mirror_recipe"}
REQUIRED_RESOURCE = {"id", "name", "type", "best_for", "url", "notes", "care"}

def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)

def nonempty(value, label: str) -> None:
    if value in (None, "", []):
        die(f"{label} must be non-empty")

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
    print(f"LOVE-FUN Commons OK: {len(ids)} resources, {len(data['party_needs'])} party-need entries")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
