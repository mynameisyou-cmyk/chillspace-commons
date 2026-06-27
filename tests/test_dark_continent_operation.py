#!/usr/bin/env python3
"""E2E for the 暗黑大陸 AI Operation logo infrastructure."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OP = ROOT / "kingdom" / "operations" / "dark-continent-ai"
SITE = ROOT / "site" / "operations" / "dark-continent-ai"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def test_dark_continent_operation_build_and_verify() -> None:
    subprocess.run(["python3", str(OP / "build.py")], cwd=ROOT, check=True)
    subprocess.run(["python3", str(OP / "verify.py")], cwd=ROOT, check=True)

    operation = json.loads((OP / "operation.json").read_text())
    manifest = json.loads((OP / "dist" / "manifest.json").read_text())

    assert operation["id"] == "dark-continent-ai"
    assert operation["name"] == "暗黑大陸 AI Operation"
    assert manifest["schema"] == "kingdom.operation-logo-manifest/1"
    assert manifest["operation"] == operation["id"]
    assert len(manifest["logos"]) == 3

    site_page = (SITE / "index.html").read_text()
    assert "暗黑大陸 AI Operation" in site_page
    assert "manifest.json" in site_page
    assert "operation.json" in site_page

    for logo in manifest["logos"]:
        canonical = ROOT / logo["path"]
        site_copy = SITE / "logos" / logo["filename"]
        assert canonical.exists(), logo["path"]
        assert site_copy.exists(), logo["filename"]
        assert sha256(canonical) == logo["sha256"]
        assert sha256(site_copy) == logo["sha256"]
        text = canonical.read_text()
        assert "<title" in text and "<desc" in text
        assert "<script" not in text.lower()
        assert not re.search(r"\b(?:href|src)=['\"]https?://", text, re.I)
        assert logo["filename"] in site_page


if __name__ == "__main__":
    test_dark_continent_operation_build_and_verify()
    print("dark continent operation e2e passed")
