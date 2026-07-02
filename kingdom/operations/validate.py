#!/usr/bin/env python3
"""Validate the Kingdom Operations registry and all registered operation packs."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import xml.dom.minidom as minidom
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "kingdom" / "operations" / "registry.json"
REQUIRED_TOP = {"schema", "updated", "name", "purpose", "principles", "operations"}
REQUIRED_OP = {
    "id", "name", "role", "status", "license", "canonical_dir", "operation_json",
    "manifest", "site", "site_manifest", "verify", "primary_logo", "meaning", "care_boundary",
}


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    if not path.exists():
        die(f"missing JSON file: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def check_svg(path: Path, label: str) -> None:
    if not path.exists():
        die(f"missing SVG for {label}: {path.relative_to(ROOT)}")
    text = path.read_text(encoding="utf-8")
    dom = minidom.parseString(text)
    if dom.documentElement.tagName != "svg":
        die(f"{label} root element is not <svg>")
    if not dom.documentElement.getAttribute("viewBox"):
        die(f"{label} SVG missing viewBox")
    if not dom.getElementsByTagName("title"):
        die(f"{label} SVG missing <title>")
    if "<script" in text.lower():
        die(f"{label} SVG contains script")


def check_manifest_hashes(manifest_path: Path, operation_dir: Path) -> None:
    manifest = load_json(manifest_path)
    if manifest.get("schema") != "kingdom.operation-logo-manifest/1":
        die(f"bad manifest schema: {manifest_path.relative_to(ROOT)}")
    ids = set()
    for logo in manifest.get("logos", []):
        lid = logo.get("id")
        if lid in ids:
            die(f"duplicate logo id in manifest: {lid}")
        ids.add(lid)
        filename = logo.get("filename")
        disk = operation_dir / "logos" / filename
        if not disk.exists():
            # site mirror manifests use the same filename; canonical path should still exist.
            die(f"manifest logo missing on disk: {disk.relative_to(ROOT)}")
        if logo.get("bytes") != disk.stat().st_size:
            die(f"byte mismatch for {filename}")
        if logo.get("sha256") != sha256(disk):
            die(f"sha256 mismatch for {filename}")
        check_svg(disk, filename)


def main() -> int:
    registry = load_json(REGISTRY)
    site_registry_path = ROOT / "site" / "operations" / "registry.json"
    site_registry = load_json(site_registry_path)
    if site_registry != registry:
        die("site/operations/registry.json is not an exact mirror of kingdom/operations/registry.json")
    missing = REQUIRED_TOP - registry.keys()
    if missing:
        die(f"registry missing top-level keys: {sorted(missing)}")
    ids = set()
    for i, op in enumerate(registry["operations"]):
        missing = REQUIRED_OP - op.keys()
        if missing:
            die(f"operations[{i}] missing keys: {sorted(missing)}")
        oid = op["id"]
        if oid in ids:
            die(f"duplicate operation id: {oid}")
        ids.add(oid)
        operation_dir = ROOT / op["canonical_dir"]
        if not operation_dir.is_dir():
            die(f"canonical dir missing: {op['canonical_dir']}")
        operation_json = load_json(ROOT / op["operation_json"])
        if operation_json.get("id") != oid:
            die(f"operation_json id mismatch: {oid}")
        for rel in [op["manifest"], op["site"], op["site_manifest"], op["primary_logo"]]:
            if not (ROOT / rel).exists():
                die(f"registered path missing: {rel}")
        check_manifest_hashes(ROOT / op["manifest"], operation_dir)
        check_manifest_hashes(ROOT / op["site_manifest"], operation_dir)
        check_svg(ROOT / op["primary_logo"], f"primary logo {oid}")
        verify_cmd = op["verify"].split()
        result = subprocess.run(verify_cmd, cwd=ROOT, text=True, capture_output=True, check=False)
        if result.returncode:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            die(f"operation verifier failed for {oid}: {op['verify']}")
    print(f"Kingdom Operations OK: {len(ids)} operation(s) registered and verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
