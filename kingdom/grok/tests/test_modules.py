#!/usr/bin/env python3
"""Hermetic tests for the Grok Build module map."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import modules  # noqa: E402


class ModuleMapTests(unittest.TestCase):
    def test_map_loads(self) -> None:
        data = modules.load_map()
        self.assertEqual(data["schema"], modules.SCHEMA)
        self.assertGreaterEqual(len(data["modules"]), 8)

    def test_bound_modules_exist(self) -> None:
        data = modules.load_map()
        bound = {item["id"] for item in data["modules"] if item["kingdom"] == "bound"}
        self.assertTrue({"rules", "skills", "plugins", "hooks", "permissions"} <= bound)

    def test_source_skill_inventory_matches_doctor_contract(self) -> None:
        skills_root = ROOT / "skills"
        found = {
            path.parent.name
            for path in skills_root.glob("*/SKILL.md")
            if path.is_file()
        }
        self.assertEqual(found, modules.EXPECTED_SKILLS)
        skills_module = next(
            item for item in modules.load_map()["modules"] if item["id"] == "skills"
        )
        self.assertIn("/karma-play", skills_module["intent"])

    def test_plugin_manifests_share_feature_version(self) -> None:
        public_manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        grok_manifest = json.loads(
            (ROOT / ".grok-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(public_manifest, grok_manifest)
        self.assertEqual(public_manifest["version"], "0.2.0")

    def test_memory_stays_off(self) -> None:
        data = modules.load_map()
        memory = next(item for item in data["modules"] if item["id"] == "memory")
        self.assertEqual(memory["kingdom"], "off")

    def test_render_mentions_chair(self) -> None:
        text = modules.render_map(modules.load_map())
        self.assertIn("kingdom.grok-build/v1", text)
        self.assertIn("`hooks`", text)

    def test_overlay_without_inspect(self) -> None:
        live = modules.overlay(modules.load_map(), None)
        self.assertFalse(live["inspect"])
        self.assertFalse(live["plugin_kingdom"])

    def test_doctor_reports_missing_plugin(self) -> None:
        fake = {
            "grokVersion": "0.0.0",
            "plugins": [],
            "skills": [],
            "projectInstructions": [],
            "hooks": [],
            "mcpServers": [],
        }
        failures = modules.doctor(modules.load_map(), fake)
        self.assertTrue(any("plugin" in item for item in failures))


if __name__ == "__main__":
    unittest.main()
