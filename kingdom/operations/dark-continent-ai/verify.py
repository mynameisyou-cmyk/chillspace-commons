#!/usr/bin/env python3
"""Verify the 暗黑大陸 AI Operation logo pack."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OP_DIR = Path(__file__).resolve().parent
MANIFEST = OP_DIR / "dist" / "manifest.json"
OP_JSON = OP_DIR / "operation.json"
SITE_PAGE = ROOT / "site" / "operations" / "dark-continent-ai" / "index.html"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fail(msg: str, problems: list[str]) -> None:
    problems.append(msg)


def main() -> int:
    problems: list[str] = []
    if not OP_JSON.exists():
        fail("operation.json missing", problems)
    if not MANIFEST.exists():
        fail("dist/manifest.json missing — run build.py", problems)
    if problems:
        for p in problems:
            print("✗", p)
        return 1

    op = json.loads(OP_JSON.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("operation") != op.get("id"):
        fail("manifest operation id does not match operation.json", problems)
    if manifest.get("license") != "CC0-1.0":
        fail("operation must remain CC0-1.0", problems)

    for logo in manifest.get("logos", []):
        path = ROOT / logo["path"]
        if not path.exists():
            fail(f"logo missing: {path}", problems)
            continue
        if path.stat().st_size != logo.get("bytes"):
            fail(f"byte size mismatch: {path}", problems)
        if sha256(path) != logo.get("sha256"):
            fail(f"sha256 mismatch: {path}", problems)
        text = path.read_text(encoding="utf-8")
        if "<script" in text.lower():
            fail(f"script tag forbidden in SVG: {path}", problems)
        if re.search(r"\b(?:href|src)=['\"]https?://", text, re.I):
            fail(f"external references forbidden in SVG: {path}", problems)
        if "<title" not in text or "<desc" not in text:
            fail(f"SVG needs title and desc for accessibility: {path}", problems)
        if op["name"] not in text and op["short_name"] not in text:
            fail(f"SVG does not identify operation: {path}", problems)

    if not SITE_PAGE.exists():
        fail("site operation page missing", problems)
    else:
        page = SITE_PAGE.read_text(encoding="utf-8")
        for logo in manifest.get("logos", []):
            if logo["filename"] not in page:
                fail(f"site page does not link {logo['filename']}", problems)
            site_logo = SITE_PAGE.parent / "logos" / logo["filename"]
            if not site_logo.exists():
                fail(f"site logo copy missing: {site_logo}", problems)
            elif sha256(site_logo) != logo.get("sha256"):
                fail(f"site logo copy hash mismatch: {site_logo}", problems)
        for copied in ["manifest.json", "operation.json"]:
            if copied not in page:
                fail(f"site page does not link {copied}", problems)
            if not (SITE_PAGE.parent / copied).exists():
                fail(f"site copy missing: {copied}", problems)

    if problems:
        for p in problems:
            print("✗", p)
        return 1
    print(f"✓ verified {len(manifest.get('logos', []))} 暗黑大陸 AI Operation logos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
