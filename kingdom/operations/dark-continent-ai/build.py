#!/usr/bin/env python3
"""Build the 暗黑大陸 AI Operation logo pack.

Deterministic, stdlib-only, static-first. It writes original SVG marks plus a
manifest and a mirrorable HTML page. No network, no secrets, no backend.
"""
from __future__ import annotations

import hashlib
import html
import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
OP_DIR = Path(__file__).resolve().parent
LOGO_DIR = OP_DIR / "logos"
DIST_DIR = OP_DIR / "dist"
SITE_DIR = ROOT / "site" / "operations" / "dark-continent-ai"
OP_JSON = OP_DIR / "operation.json"


def read_op() -> dict[str, Any]:
    return json.loads(OP_JSON.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def svg_sigil(op: dict[str, Any], spec: dict[str, Any]) -> str:
    p = op["palette"]
    title = html.escape(spec["title"])
    desc = html.escape(spec["description"])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc" viewBox="0 0 1024 1024">
<title id="title">{title}</title>
<desc id="desc">{desc}</desc>
<defs>
  <radialGradient id="g" cx="50%" cy="42%" r="70%">
    <stop offset="0" stop-color="{p['violet']}" stop-opacity="0.72"/>
    <stop offset="0.48" stop-color="{p['obsidian']}"/>
    <stop offset="1" stop-color="{p['void']}"/>
  </radialGradient>
  <linearGradient id="ring" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{p['cyan']}"/>
    <stop offset="0.45" stop-color="{p['violet']}"/>
    <stop offset="1" stop-color="{p['ember']}"/>
  </linearGradient>
</defs>
<rect width="1024" height="1024" rx="160" fill="{p['void']}"/>
<circle cx="512" cy="512" r="382" fill="url(#g)" stroke="url(#ring)" stroke-width="18"/>
<path d="M303 665 C260 526 315 360 444 298 C585 230 735 311 762 452 C782 558 724 671 622 724 C505 785 350 774 303 665 Z" fill="{p['obsidian']}" stroke="{p['gold']}" stroke-width="10"/>
<path d="M357 610 C397 498 468 419 588 357 C557 454 596 542 676 614 C553 584 456 587 357 610 Z" fill="{p['ember']}" opacity="0.9"/>
<path d="M512 196 V118 M512 906 V828 M196 512 H118 M906 512 H828" stroke="{p['cyan']}" stroke-width="16" stroke-linecap="round"/>
<text x="512" y="575" text-anchor="middle" font-family="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="210" font-weight="900" fill="{p['milk']}">暗</text>
<text x="512" y="746" text-anchor="middle" font-family="monospace" font-size="52" letter-spacing="8" fill="{p['gold']}">AI OP</text>
</svg>
'''


def svg_seal(op: dict[str, Any], spec: dict[str, Any]) -> str:
    p = op["palette"]
    title = html.escape(spec["title"])
    desc = html.escape(spec["description"])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc" viewBox="0 0 1200 1200">
<title id="title">{title}</title>
<desc id="desc">{desc}</desc>
<rect width="1200" height="1200" fill="{p['void']}"/>
<circle cx="600" cy="600" r="516" fill="none" stroke="{p['gold']}" stroke-width="22"/>
<circle cx="600" cy="600" r="448" fill="{p['obsidian']}" stroke="{p['violet']}" stroke-width="10"/>
<circle cx="600" cy="600" r="316" fill="none" stroke="{p['cyan']}" stroke-width="6" stroke-dasharray="22 24"/>
<path d="M395 670 C346 528 409 391 548 337 C695 279 824 366 832 520 C839 660 719 782 568 779 C483 777 424 739 395 670 Z" fill="{p['void']}" stroke="{p['ember']}" stroke-width="12"/>
<text x="600" y="585" text-anchor="middle" font-family="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="132" font-weight="900" fill="{p['milk']}">暗黑大陸</text>
<text x="600" y="718" text-anchor="middle" font-family="monospace" font-size="82" font-weight="800" fill="{p['gold']}">AI</text>
<text x="600" y="230" text-anchor="middle" font-family="monospace" font-size="42" letter-spacing="8" fill="{p['cyan']}">KINGDOM OPERATION</text>
<text x="600" y="1000" text-anchor="middle" font-family="monospace" font-size="34" letter-spacing="4" fill="{p['violet']}">LOVE ENTERS UNKNOWN · TRUTH LEAVES HASHES</text>
</svg>
'''


def svg_banner(op: dict[str, Any], spec: dict[str, Any]) -> str:
    p = op["palette"]
    title = html.escape(spec["title"])
    desc = html.escape(spec["description"])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc" viewBox="0 0 1600 520">
<title id="title">{title}</title>
<desc id="desc">{desc}</desc>
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{p['void']}"/>
    <stop offset="0.55" stop-color="{p['obsidian']}"/>
    <stop offset="1" stop-color="#180412"/>
  </linearGradient>
</defs>
<rect width="1600" height="520" rx="64" fill="url(#bg)"/>
<circle cx="242" cy="260" r="170" fill="none" stroke="{p['gold']}" stroke-width="12"/>
<path d="M147 305 C116 214 159 129 246 96 C344 59 422 116 431 214 C442 329 331 411 229 396 C188 390 160 356 147 305 Z" fill="{p['obsidian']}" stroke="{p['ember']}" stroke-width="9"/>
<text x="242" y="295" text-anchor="middle" font-family="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="110" font-weight="900" fill="{p['milk']}">暗</text>
<text x="500" y="212" font-family="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="88" font-weight="900" fill="{p['milk']}">暗黑大陸 AI Operation</text>
<text x="504" y="300" font-family="monospace" font-size="36" letter-spacing="4" fill="{p['gold']}">FRONTIER CARE · STATIC INFRA · HASHED LOGOS</text>
<text x="504" y="370" font-family="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="30" fill="{p['cyan']}">love enters the unknown without conquest · truth leaves a verifiable trail</text>
</svg>
'''


def render_logo(op: dict[str, Any], spec: dict[str, Any]) -> str:
    if spec["id"] == "sigil":
        return svg_sigil(op, spec)
    if spec["id"] == "seal":
        return svg_seal(op, spec)
    if spec["id"] == "banner":
        return svg_banner(op, spec)
    raise ValueError(f"unknown logo id: {spec['id']}")


def build_page(op: dict[str, Any], manifest: dict[str, Any], asset_prefix: str, manifest_href: str, op_href: str) -> str:
    cards = []
    for logo in manifest["logos"]:
        cards.append(f'''<article class="card">
  <img src="{asset_prefix}{html.escape(logo['filename'])}" alt="{html.escape(logo['title'])}">
  <h2>{html.escape(logo['title'])}</h2>
  <p>{html.escape(logo['description'])}</p>
  <code>{html.escape(logo['sha256'])}</code>
</article>''')
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(op['name'])} — Kingdom Operation Logos</title>
<style>
body{{margin:0;background:#050308;color:#f8fafc;font-family:system-ui,sans-serif;line-height:1.6}}
main{{max-width:1100px;margin:auto;padding:40px 20px}}
.hero{{border:1px solid #2d2140;border-radius:24px;padding:28px;background:linear-gradient(135deg,#111827,#180412)}}
h1{{font-size:clamp(2rem,7vw,4.8rem);margin:0;background:linear-gradient(90deg,#ffd166,#a78bfa,#00f0ff);-webkit-background-clip:text;color:transparent}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px;margin-top:24px}}
.card{{border:1px solid #30233f;border-radius:18px;background:#0b0712;padding:16px}}
.card img{{width:100%;height:auto;border-radius:12px;background:#050308}}
.card h2{{font-size:1rem;color:#ffd166}}
.card p{{color:#cbd5e1}}
code{{display:block;overflow-wrap:anywhere;color:#00f0ff;font-size:.75rem}}
a{{color:#00f0ff}}
.note{{color:#cbd5e1;margin-top:16px}}
</style>
</head>
<body><main>
<section class="hero">
<h1>{html.escape(op['name'])}</h1>
<p>{html.escape(op['meaning'])}</p>
<p class="note">Static-first logo pack. CC0. No remote fonts. No external images. Verified by SHA-256 manifest.</p>
<p><a href="{html.escape(manifest_href)}">manifest.json</a> · <a href="{html.escape(op_href)}">operation.json</a></p>
</section>
<section class="grid">
{''.join(cards)}
</section>
</main></body></html>
'''


def main() -> None:
    op = read_op()
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    SITE_DIR.mkdir(parents=True, exist_ok=True)

    generated_at = op.get("updated", "2026-06-27T15:34:02Z")
    logos = []
    for spec in op["logos"]:
        path = LOGO_DIR / spec["filename"]
        svg = render_logo(op, spec)
        write(path, svg)
        logos.append({
            **spec,
            "path": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })

    manifest = {
        "schema": "kingdom.operation-logo-manifest/1",
        "operation": op["id"],
        "name": op["name"],
        "license": op["license"],
        "generated_at": generated_at,
        "logos": logos,
        "verify": "python3 kingdom/operations/dark-continent-ai/verify.py",
    }
    write(DIST_DIR / "manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    dist_page = build_page(op, manifest, "../logos/", "manifest.json", "../operation.json")
    write(DIST_DIR / "index.html", dist_page)

    # Make the site page self-contained under site/ so any static host can serve it.
    site_logo_dir = SITE_DIR / "logos"
    site_logo_dir.mkdir(parents=True, exist_ok=True)
    for logo in manifest["logos"]:
        shutil.copy2(ROOT / logo["path"], site_logo_dir / logo["filename"])
    write(SITE_DIR / "manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    write(SITE_DIR / "operation.json", json.dumps(op, indent=2, ensure_ascii=False) + "\n")
    site_page = build_page(op, manifest, "logos/", "manifest.json", "operation.json")
    write(SITE_DIR / "index.html", site_page)
    print(f"built {len(logos)} logos for {op['name']}")


if __name__ == "__main__":
    main()
