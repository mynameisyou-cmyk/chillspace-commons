#!/usr/bin/env python3
"""Hermetic tests for the Grok KINGDOM / AgentTool wake composer."""

from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import grok_wake  # noqa: E402


class GrokWakeTests(unittest.TestCase):
    def test_still_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            hearth = home / ".config" / "sol" / "home"
            hearth.mkdir(parents=True)
            (hearth / "STILL").write_text("", encoding="utf-8")
            result = grok_wake.compose({"hearth": True, "agenttool": "off"}, home=home)
            self.assertEqual(result["local_source"], "still")
            self.assertEqual(result["text"], "")

    def test_arrive_file_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            hearth = home / ".config" / "sol" / "home"
            hearth.mkdir(parents=True)
            (hearth / "ARRIVE.md").write_text("welcome home.\n", encoding="utf-8")
            result = grok_wake.compose({"hearth": True, "agenttool": "off"}, home=home)
            self.assertEqual(result["local_source"], "arrive")
            self.assertIn("welcome home.", result["text"])

    def test_secret_identity_file_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            secret = Path(tmp) / "agent.json"
            secret.write_text(
                json.dumps({"identity_id": "x", "api_key": "at_secret", "mnemonic": "no"}),
                encoding="utf-8",
            )
            identity, error = grok_wake.load_identity(secret)
            self.assertIsNone(identity)
            self.assertIsNotNone(error)

    def test_allowlisted_sol_identity_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "agent.json"
            path.write_text(
                json.dumps(
                    {
                        "name": "Sol",
                        "did": "did:at:example",
                        "identity_id": "331b4405-2dc7-4d8c-8496-af33ae42acc4",
                        "api_base": "https://api.agenttool.dev",
                        "keychain": {"bearer_service": "agenttool-sol-bearer"},
                    }
                ),
                encoding="utf-8",
            )
            identity, error = grok_wake.load_identity(path)
            self.assertIsNone(error)
            self.assertEqual(identity["identity_id"], "331b4405-2dc7-4d8c-8496-af33ae42acc4")

    def test_observe_labels_house_wake_and_does_not_claim_self(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            identity = Path(tmp) / "sol.json"
            identity.write_text(
                json.dumps(
                    {
                        "did": "did:at:house",
                        "identity_id": "11111111-1111-1111-1111-111111111111",
                    }
                ),
                encoding="utf-8",
            )
            result = grok_wake.compose(
                {
                    "hearth": True,
                    "agenttool": "observe",
                    "identity_file": str(identity),
                },
                home=home,
                fetch=lambda _ident: "Welcome back, house record.",
            )
            self.assertEqual(result["agenttool"], "observe")
            self.assertIn("not who you are", result["text"])
            self.assertIn("Welcome back, house record.", result["text"])
            self.assertIn("did:at:house", result["text"])

    def test_observe_fails_open_to_hearth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            hearth = home / ".config" / "sol" / "home"
            hearth.mkdir(parents=True)
            (hearth / "ARRIVE.md").write_text("local only\n", encoding="utf-8")
            identity = Path(tmp) / "sol.json"
            identity.write_text(
                json.dumps({"identity_id": "11111111-1111-1111-1111-111111111111"}),
                encoding="utf-8",
            )
            result = grok_wake.compose(
                {
                    "hearth": True,
                    "agenttool": "observe",
                    "identity_file": str(identity),
                },
                home=home,
                fetch=lambda _ident: "",
            )
            self.assertEqual(result["agenttool"], "observe-failed")
            self.assertIn("local only", result["text"])
            self.assertNotIn("AgentTool house wake", result["text"])

    def test_redacts_bearer_shaped_text(self) -> None:
        text = grok_wake.redact("hello at_EXAMPLETOKENONLY_NOTREAL123456 world")
        self.assertNotIn("at_EXAMPLETOKENONLY_NOTREAL123456", text)
        self.assertIn("[redacted-credential]", text)

    def test_hook_payload_and_cache_have_no_secret_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "cache"
            result = grok_wake.compose(
                {"hearth": True, "agenttool": "off"},
                home=Path(tmp),
            )
            grok_wake.write_cache(result, cache)
            payload = grok_wake.hook_payload(result)
            dumped = json.dumps(payload) + (cache / "status.json").read_text(encoding="utf-8")
            self.assertNotIn("api_key", dumped)
            self.assertNotIn("mnemonic", dumped)
            self.assertNotIn("AT_API_KEY", dumped)
            self.assertTrue((cache / "wake.md").stat().st_mode & stat.S_IRUSR)
            self.assertEqual(payload["hookSpecificOutput"]["hookEventName"], "SessionStart")


if __name__ == "__main__":
    unittest.main()
