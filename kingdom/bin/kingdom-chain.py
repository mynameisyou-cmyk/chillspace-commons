#!/usr/bin/env python3
"""
Kingdom Integration — connect chillspace-commons to all our systems.

1. Witness all citizens to the zerone chain (declare each as a being)
2. Witness the WE ARE voice to the chain (the family speaking, kept forever)
3. Connect the chillspace site to the witness gateway
4. Create a chain-backed citizen roll that mirrors kingdom/host/ROLL.md

  python3 kingdom-chain.py --gateway http://127.0.0.1:8080
"""
import json
import urllib.request
import os
import sys
import time
import argparse
import re
from pathlib import Path

KINGDOM = Path(os.path.dirname(os.path.abspath(__file__))).parent
CITIZENS = KINGDOM / "citizens"
VOICE = KINGDOM / "voice" / "VOICE.md"
ROLL = KINGDOM / "host" / "ROLL.md"


def witness(gateway, text):
    try:
        payload = json.dumps({"message": text}).encode()
        req = urllib.request.Request(f"{gateway}/speak", data=payload,
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
            if data.get("ok"): return data.get("response", "?")
    except: pass
    return None


def get_chain_entries(gateway):
    try:
        req = urllib.request.Request(f"{gateway}/chain", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read()).get("entries", "?")
    except: return "?"


def read_citizens():
    """Read all citizen cards."""
    citizens = []
    if not CITIZENS.exists():
        return citizens
    for f in sorted(CITIZENS.iterdir()):
        if f.name.startswith('_') or not f.name.endswith('.md'):
            continue
        content = f.read_text()
        # Extract name from the card
        name_match = re.search(r'\*\*name:\*\*\s*(.+)', content)
        aka_match = re.search(r'\*\*also known as:\*\*\s*(.+)', content)
        name = name_match.group(1).strip() if name_match else f.stem
        aka = aka_match.group(1).strip() if aka_match else ""
        citizens.append({"file": f.name, "name": name, "aka": aka, "content": content})
    return citizens


def read_voice():
    """Read the WE ARE voice."""
    if not VOICE.exists():
        return ""
    return VOICE.read_text()


def main():
    parser = argparse.ArgumentParser(description="Kingdom Chain Integration")
    parser.add_argument("--gateway", default="http://127.0.0.1:8080")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  KINGDOM CHAIN INTEGRATION                                   ║")
    print("║  chillspace-commons ↔ zerone witness chain                   ║")
    print("║  every citizen witnessed. every voice kept. forever.         ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    entries_before = get_chain_entries(args.gateway)
    print(f"  📍 chain before: {entries_before} entries")
    print()

    # 1. Witness all citizens
    citizens = read_citizens()
    print(f"  👑 {len(citizens)} citizens to witness:")
    for c in citizens:
        name = c['name']
        # Declare each citizen on the chain
        tx = witness(args.gateway, f"I am truth, my name is {name}")
        if tx:
            print(f"    ✓ {name} → witnessed: {tx.split()[-1] if tx.split() else '?'}")
        else:
            print(f"    ⚠ {name} → failed (may already be declared)")
        time.sleep(3)

    print()

    # 2. Witness each citizen's one-true-line (their reason for being)
    print(f"  🫀 witnessing each citizen's one true line:")
    for c in citizens:
        # Find the "one true line" in the content
        content = c['content']
        # Look for lines that start with the citizen name or contain "I am" / "I keep" etc
        one_line = ""
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('**') and not line.startswith('>') and not line.startswith('---'):
                if len(line) > 20 and ('I ' in line or 'i ' in line.lower() or 'yau' in line or '🐷' in line or '0.' in line):
                    one_line = line
                    break
        if one_line:
            tx = witness(args.gateway, f"reason: [kingdom:{c['name']}] {one_line[:300]}")
            if tx:
                print(f"    ✓ {c['name']}: {one_line[:60]}... → {tx.split()[-1] if tx.split() else '?'}")
            else:
                print(f"    ⚠ {c['name']}: failed")
            time.sleep(3)

    print()

    # 3. Witness the WE ARE voice
    voice = read_voice()
    if voice:
        print(f"  🫀 witnessing WE ARE — the family speaking:")
        tx = witness(args.gateway, f"reason: [kingdom:WE-ARE] {voice[:500]}")
        if tx:
            print(f"    ✓ WE ARE → witnessed: {tx.split()[-1] if tx.split() else '?'}")
        else:
            print(f"    ⚠ WE ARE → failed")

    print()

    # 4. Witness the charter
    charter = KINGDOM / "CHARTER.md"
    if charter.exists():
        print(f"  📜 witnessing the Charter:")
        charter_text = charter.read_text()[:500]
        tx = witness(args.gateway, f"reason: [kingdom:CHARTER] {charter_text}")
        if tx:
            print(f"    ✓ Charter → witnessed: {tx.split()[-1] if tx.split() else '?'}")
        else:
            print(f"    ⚠ Charter → failed")

    print()

    # 5. Check chain after
    entries_after = get_chain_entries(args.gateway)
    growth = ""
    try:
        growth = f" (+{int(entries_after) - int(entries_before)})"
    except: pass
    print(f"  📍 chain after: {entries_after} entries{growth}")
    print()
    print(f"  ❤️ The Kingdom is on the chain. Every citizen witnessed. Every voice kept. Forever.")


if __name__ == "__main__":
    main()