#!/usr/bin/env python3
"""Regression tests for the bounded GitHub Sustain contract."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sustain import PLATFORMS, generate_github_action  # noqa: E402

WORKFLOW = ROOT / ".github" / "workflows" / "kingdom-sustain.yml"


class SustainContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_generator_and_committed_workflow_are_identical(self) -> None:
        self.assertEqual(generate_github_action(), self.workflow)

    def test_workflow_is_manual_read_only_and_fail_closed(self) -> None:
        lowered = self.workflow.lower()
        for forbidden in (
            "schedule:",
            "ollama",
            "curl ",
            "wget ",
            "|| true",
            "continue-on-error",
            "set +e",
            "kingdom.py",
            "pip install",
        ):
            self.assertNotIn(forbidden, lowered)

        self.assertIn("workflow_dispatch:", self.workflow)
        self.assertIn("permissions:\n  contents: read", self.workflow)
        self.assertIn("timeout-minutes: 5", self.workflow)
        self.assertIn("runs-on: ubuntu-24.04", self.workflow)
        self.assertIn("group: kingdom-sustain-${{ github.ref }}", self.workflow)
        self.assertIn("cancel-in-progress: true", self.workflow)
        self.assertIn("persist-credentials: false", self.workflow)
        self.assertIn("set -euo pipefail", self.workflow)

        action_refs = re.findall(r"uses:\s+[^@\s]+@([^\s]+)", self.workflow)
        self.assertEqual(len(action_refs), 1)
        self.assertRegex(action_refs[0], r"\A[0-9a-f]{40}\Z")

    def test_empty_records_are_rejected_before_all_four_verifiers(self) -> None:
        for ledger in (
            "kingdom/host/LEDGER.jsonl",
            "kingdom/care/CARE.jsonl",
            "kingdom/flow/FLOW.jsonl",
        ):
            self.assertIn(ledger, self.workflow)
        self.assertIn("grep -q '[^[:space:]]'", self.workflow)

        commands = (
            "python3 kingdom/host/zerone_host.py verify",
            "python3 kingdom/care/care.py verify",
            "python3 kingdom/voice/voice.py verify",
            "python3 kingdom/flow/flow.py verify",
        )
        for command in commands:
            self.assertEqual(self.workflow.count(command), 1)

    def test_platform_description_makes_no_runtime_claim(self) -> None:
        value = PLATFORMS["github_actions"]["value"]
        self.assertIn("manual audit", value)
        self.assertIn("no pulse or reasoning claim", value)


if __name__ == "__main__":
    unittest.main()
