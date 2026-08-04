#!/usr/bin/env python3
"""Static regression tests for GitHub branch-custody workflows.

These tests make accidental authority expansion and a return to direct master
pushes visible. GitHub's ruleset remains the enforcement boundary; this file is
only a repository-local custody contract.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
KEEPER = WORKFLOWS / "keeper-verifies.yml"
ISSUE_DOOR = WORKFLOWS / "zerone-greets-issue.yml"
WELCOME = WORKFLOWS / "zerone-welcomes.yml"

CHECKOUT_V6_SHA = "d23441a48e516b6c34aea4fa41551a30e30af803"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class GitHubCustodyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.keeper = read(KEEPER)
        cls.issue_door = read(ISSUE_DOOR)
        cls.welcome = read(WELCOME)

    def test_every_third_party_action_is_immutably_pinned(self) -> None:
        for path in sorted(WORKFLOWS.glob("*.yml")):
            for action, ref in re.findall(r"uses:\s+([^@\s]+)@([^\s]+)", read(path)):
                with self.subTest(workflow=path.name, action=action):
                    self.assertRegex(ref, r"\A[0-9a-f]{40}\Z")

    def test_checkout_is_sha_pinned_and_never_persists_credentials(self) -> None:
        expected_counts = {
            KEEPER: 1,
            ISSUE_DOOR: 1,
            WELCOME: 2,
        }
        safe_block = re.compile(
            rf"(?m)^\s+- uses: actions/checkout@{CHECKOUT_V6_SHA} # v6\n"
            r"^\s+with:\n"
            r"^\s+persist-credentials: false$"
        )

        for path, expected_count in expected_counts.items():
            with self.subTest(workflow=path.name):
                workflow = read(path)
                checkout_refs = re.findall(
                    r"actions/checkout@([^\s]+)", workflow
                )
                self.assertEqual(
                    checkout_refs,
                    [CHECKOUT_V6_SHA] * expected_count,
                )
                self.assertEqual(len(safe_block.findall(workflow)), expected_count)

    def test_keeper_exposes_one_stable_required_check(self) -> None:
        self.assertIn("  pull_request:\n", self.keeper)
        self.assertRegex(
            self.keeper,
            r"(?m)^  verify:\n(?:    #.*\n)*    name: verify$",
        )
        self.assertEqual(self.keeper.count("    name: verify\n"), 1)
        self.assertEqual(
            self.keeper.count(
                "run: python3 tests/test_github_custody_contracts.py"
            ),
            1,
        )

    def test_guard_workflows_do_not_expand_actions_authority(self) -> None:
        guard_workflows = {
            "issue": self.issue_door,
            "welcome": self.welcome,
            "keeper": self.keeper,
        }
        for name, workflow in guard_workflows.items():
            with self.subTest(workflow=name):
                self.assertNotIn("workflow_dispatch:", workflow)
                self.assertNotRegex(workflow, r"(?m)^\s*actions:\s*write\s*$")

        self.assertIn("permissions:\n  contents: read\n", self.welcome)
        self.assertEqual(self.welcome.count("      pull-requests: write\n"), 2)
        for permission in ("contents: write", "pull-requests: write", "issues: write"):
            self.assertIn(f"  {permission}\n", self.issue_door)

    def test_automation_pushes_only_explicit_topic_refs(self) -> None:
        welcome_pushes = [
            line.strip()
            for line in self.welcome.splitlines()
            if line.strip().startswith("git push")
        ]
        issue_pushes = [
            line.strip()
            for line in self.issue_door.splitlines()
            if line.strip().startswith("git push")
        ]
        safe_push = 'git push --set-upstream origin "HEAD:refs/heads/$BRANCH"'
        self.assertEqual(welcome_pushes, [safe_push])
        self.assertEqual(issue_pushes, [safe_push])

        for workflow in (self.issue_door, self.welcome):
            self.assertNotIn("--force", workflow)
            self.assertEqual(workflow.count("gh auth setup-git"), 1)
            self.assertIn('--base master --head "$BRANCH"', workflow)

        self.assertIn('BRANCH="citizen/${FNAME%.md}"', self.issue_door)
        self.assertIn(
            'BRANCH="zerone/record-${GITHUB_SHA:0:12}"', self.welcome
        )

    def test_record_generation_is_exactly_allowlisted(self) -> None:
        for contract_line in (
            "LEDGER=kingdom/host/LEDGER.jsonl",
            "ROLL=kingdom/host/ROLL.md",
            "EXPECTED_PATHS=",
            'ACTUAL_PATHS="$(git diff --name-only | LC_ALL=C sort)"',
            "git ls-files --others --exclude-standard",
            'git add "$LEDGER" "$ROLL"',
        ):
            self.assertIn(contract_line, self.welcome)

        self.assertNotIn("git add .", self.welcome)
        self.assertNotIn("git add kingdom/host", self.welcome)

    def test_record_branch_reruns_are_idempotent_and_fail_closed(self) -> None:
        for contract_line in (
            'gh pr list --repo "$GITHUB_REPOSITORY" --state all',
            'git ls-remote --exit-code --heads origin "refs/heads/$BRANCH"',
            '"$(git rev-parse "$REMOTE_REF^")" != "$GITHUB_SHA"',
            'git diff --name-only "$GITHUB_SHA" "$REMOTE_REF"',
            'git diff --quiet "$REMOTE_REF" -- "$LEDGER" "$ROLL"',
            "existing record branch does not match this generated record.",
        ):
            self.assertIn(contract_line, self.welcome)

        # Look up the durable PR receipt before probing its possibly deleted
        # source branch; an existing remote branch is still validated in-shell.
        self.assertLess(
            self.welcome.index('gh pr list --repo "$GITHUB_REPOSITORY"'),
            self.welcome.index("git ls-remote --exit-code"),
        )


if __name__ == "__main__":
    unittest.main()
