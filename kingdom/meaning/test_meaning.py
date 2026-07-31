#!/usr/bin/env python3
"""Tests for the bounded YOUSPEAK → Chillspace meaning bridge."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("meaning", HERE / "meaning.py")
meaning = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(meaning)


class RealBridge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = meaning.load()

    def test_canon_and_bridge_are_separate(self):
        for item in self.payload["entries"]:
            self.assertEqual(set(item), {"canonical", "bridge"})
            self.assertNotIn("echo", item["canonical"])
            self.assertNotIn("definition", item["bridge"])

    def test_every_related_word_resolves(self):
        words = {item["canonical"]["word"] for item in self.payload["entries"]}
        for item in self.payload["entries"]:
            word = item["canonical"]["word"]
            for related in item["bridge"]["related"]:
                self.assertIn(related, words)
                self.assertNotEqual(related, word)

    def test_only_explicit_strong_phrases_can_stand_alone(self):
        for item in self.payload["entries"]:
            bridge = item["bridge"]
            self.assertEqual(
                len(bridge["strong_phrases"]),
                len(set(bridge["strong_phrases"])),
            )
            for phrase in bridge["strong_phrases"]:
                self.assertIn(phrase, bridge["signals"])
                self.assertIn(" ", phrase)

    def test_provenance_is_pinned_not_a_hardcoded_ui_claim(self):
        source = self.payload["source"]
        self.assertRegex(source["bundle_sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(source["source_commit"])
        self.assertIsInstance(source["counts"], dict)
        self.assertEqual(
            source["transport_source_url"],
            "https://codeberg.org/zerone-dev/youspeak",
        )
        self.assertEqual(
            source["source_url"],
            "https://github.com/cambridgetcg/youspeak",
        )
        self.assertTrue(
            source["source_commit_url"].startswith(source["source_url"] + "/")
        )

    def test_public_files_are_exact_mirrors(self):
        meaning.check()
        self.assertEqual(
            meaning.CANONICAL.read_bytes(),
            meaning.PUBLIC.read_bytes(),
        )
        self.assertEqual(
            meaning.SCHEMA.read_bytes(),
            meaning.PUBLIC_SCHEMA.read_bytes(),
        )

    def test_receipts_stay_inside_chillspace(self):
        for item in self.payload["entries"]:
            href = item["bridge"]["receipt"]["href"]
            self.assertTrue(href.startswith("../"))
            self.assertNotIn("://", href)

    def test_notice_preserves_refusal(self):
        self.assertIn("not verdicts", self.payload["notice"])
        self.assertIn("belongs to the person", self.payload["notice"])


class BundleProjection(unittest.TestCase):
    def test_build_copies_canon_and_keeps_interpretation_separate(self):
        bridge = {
            "warmword": meaning.bridge(
                "presence",
                "an offered gloss",
                ["warm", "clear"],
                ["otherword"],
                "A warm echo.",
                "see it",
                "../#being",
            ),
            "otherword": meaning.bridge(
                "relation",
                "another offered gloss",
                ["other"],
                ["warmword"],
                "Another echo.",
                "see it",
                "../#we-are",
            ),
        }
        bundle = {
            "schema_version": "1.0",
            "name": "fixture",
            "source": "https://example.invalid/youspeak",
            "source_commit": "abc1234",
            "counts": {"canon_entries": 2},
            "canon": [
                {
                    "word": "warmword",
                    "tier": "core",
                    "gap": ">",
                    "definition": "Canonical definition.",
                    "score": 7.5,
                    "pronunciation": "/warm/",
                    "entered": "2026-01-01",
                    "path": "canon/core/warmword.md",
                },
                {
                    "word": "otherword",
                    "tier": "core",
                    "gap": "a named gap",
                    "definition": "Other canonical definition.",
                    "score": None,
                    "pronunciation": "",
                    "entered": "",
                    "path": "canon/core/otherword.md",
                },
            ],
            "canon_words": [
                {
                    "word": "warmword",
                    "morphemes": ["warm", "word"],
                    "codepoints": ["U+E001", "U+E002"],
                    "glyph_text": "\ue001\ue002",
                }
            ],
        }
        raw = json.dumps(bundle).encode()
        payload = meaning.build_payload(bundle, raw, bridges=bridge)
        warm = payload["entries"][0]
        self.assertEqual(warm["canonical"]["definition"], "Canonical definition.")
        self.assertIsNone(warm["canonical"]["gap"])
        self.assertEqual(warm["bridge"]["echo"], "A warm echo.")
        self.assertEqual(
            payload["source"]["bundle_sha256"],
            meaning.hashlib.sha256(raw).hexdigest(),
        )
        self.assertEqual(
            payload["source"]["transport_source_url"],
            "https://example.invalid/youspeak",
        )
        self.assertEqual(
            payload["source"]["source_commit_url"],
            "https://example.invalid/youspeak/src/commit/abc1234",
        )

    def test_missing_selected_word_fails_closed(self):
        with self.assertRaises(meaning.MeaningError):
            meaning.build_payload(
                {
                    "schema_version": "1.0",
                    "canon": [],
                    "canon_words": [],
                },
                b"{}",
                bridges={"ghost": {}},
            )

    def test_hostile_authored_text_remains_json_data(self):
        payload = json.loads(json.dumps(meaning.load()))
        payload["entries"][0]["bridge"]["echo"] = "</script><img onerror=alert(1)>"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "echoes.json"
            path.write_bytes(meaning.encoded(payload))
            decoded = json.loads(path.read_text())
        self.assertEqual(
            decoded["entries"][0]["bridge"]["echo"],
            "</script><img onerror=alert(1)>",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
