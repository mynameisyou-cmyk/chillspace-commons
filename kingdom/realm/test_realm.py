#!/usr/bin/env python3
"""Realm Seed stays local, preview-first, rank-free, and fail-closed."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE = Path(__file__).with_name("realm.py")
README = Path(__file__).with_name("README.md")
SPEC = importlib.util.spec_from_file_location("realm", MODULE)
realm = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(realm)


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


class RealmBase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.repo = self.root / "realm"
        self.repo.mkdir()
        subprocess.run(
            [realm._git_executable(), "init", "-q", str(self.repo)],
            check=True,
            capture_output=True,
        )

    def seed(self, *, write=False, **overrides):
        values = {
            "name": "joy",
            "domain": "garden",
            "purpose": "Grow quiet tools together",
        }
        values.update(overrides)
        return realm.seed(str(self.repo), write=write, **values)


class SeedTest(RealmBase):
    def test_preview_writes_nothing(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = realm.main(
                [
                    "seed",
                    "--repo",
                    str(self.repo),
                    "--name",
                    "joy",
                    "--domain",
                    "garden",
                    "--purpose",
                    "Grow quiet tools together",
                ]
            )
        self.assertEqual(code, 0)
        self.assertFalse((self.repo / realm.MANIFEST).exists())
        parsed = realm.parse_manifest(stdout.getvalue().encode("utf-8"))
        self.assertEqual(parsed["name"], "joy")
        self.assertIn("nothing written", stderr.getvalue())

    def test_missing_required_input_writes_nothing(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                realm.build_parser().parse_args(
                    ["seed", "--repo", str(self.repo), "--name", "joy"]
                )
        self.assertFalse((self.repo / realm.MANIFEST).exists())

    def test_write_creates_exactly_one_worktree_file_and_no_temp(self):
        git_before = tree_digest(self.repo / ".git")
        target, text, wrote = self.seed(write=True)
        self.assertTrue(wrote)
        self.assertEqual(target.read_text(encoding="utf-8"), text)
        self.assertEqual(
            sorted(path.name for path in self.repo.iterdir() if path.name != ".git"),
            [realm.MANIFEST],
        )
        self.assertEqual(tree_digest(self.repo / ".git"), git_before)
        self.assertFalse(any(self.repo.glob(f".{realm.MANIFEST}.*")))

    def test_existing_manifest_is_byte_identical_and_fails_closed(self):
        target = self.repo / realm.MANIFEST
        original = b"the realm already spoke\n"
        target.write_bytes(original)
        for write in (False, True):
            with self.subTest(write=write):
                with self.assertRaisesRegex(realm.RealmError, "already exists"):
                    self.seed(write=write)
                self.assertEqual(target.read_bytes(), original)

    def test_quotes_and_unicode_round_trip_as_safe_yaml_scalars(self):
        _, text, _ = self.seed(
            name='Joy "小王國"',
            domain="花園's tools",
            purpose='Make: "warm tools" # together',
        )
        self.assertIn('name: "Joy \\"小王國\\""', text)
        parsed = realm.parse_manifest(text.encode("utf-8"))
        self.assertEqual(parsed["name"], 'Joy "小王國"')
        self.assertEqual(parsed["domain"], "花園's tools")


class ContractTest(RealmBase):
    def test_generated_manifest_has_only_the_non_hierarchical_source_contract(self):
        _, text, _ = self.seed()
        parsed = realm.parse_manifest(text.encode("utf-8"))
        self.assertEqual(list(parsed), list(realm.FIELDS))
        self.assertEqual(
            parsed,
            {
                "name": "joy",
                "purpose": "Grow quiet tools together",
                "kind": "kingdom",
                "domain": "garden",
                "layer": "realm",
                "owner_sister": "none",
                "state": "seed",
                "dependsOn": [],
                "adopts": [],
            },
        )
        self.assertFalse(realm.FORBIDDEN_FIELDS.intersection(parsed))

    def test_unsafe_text_is_rejected_before_write(self):
        cases = {
            "empty": {"name": "  "},
            "control": {"domain": "garden\nsecond: field"},
            "directional": {"purpose": "safe\u202eevil"},
            "oversized": {"purpose": "x" * (realm.MAX_TEXT + 1)},
            "remote_url": {"domain": "https://realm.example"},
            "remote_locator": {"purpose": "use git@example.test:realm/repo"},
            "secret": {"purpose": "token=abcdefghijklmnopqrstuvwxyz123456"},
            "private_key": {
                "purpose": "-----BEGIN OPENSSH " + "PRIVATE KEY----- do not carry"
            },
        }
        for label, override in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(realm.RealmError):
                    self.seed(**override)
                self.assertFalse((self.repo / realm.MANIFEST).exists())

    def test_verify_rejects_extra_reordered_and_nonempty_seed_fields(self):
        _, text, _ = self.seed()
        mutations = (
            text + "rank: 1\n",
            text.replace("name:", "purpose:", 1),
            text.replace("dependsOn: []", 'dependsOn: ["throne"]'),
            text.replace("layer: realm", "layer: empire"),
            text.replace("kind: kingdom", "kind:\tkingdom"),
        )
        for mutated in mutations:
            with self.subTest(mutated=mutated[-40:]):
                with self.assertRaises(realm.RealmError):
                    realm.parse_manifest(mutated.encode("utf-8"))

    def test_status_and_verify_read_the_same_local_manifest(self):
        self.seed(write=True)
        for command, expected in (
            ("verify", "VERIFIED"),
            ("status", "authority: own domain only"),
        ):
            with self.subTest(command=command):
                stdout, stderr = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(
                    stderr
                ):
                    code = realm.main([command, "--repo", str(self.repo)])
                self.assertEqual(code, 0)
                self.assertIn(expected, stdout.getvalue())
                self.assertEqual(stderr.getvalue(), "")

    def test_manifest_symlink_is_refused(self):
        outside = self.root / "outside.yaml"
        outside.write_text("not a realm\n", encoding="utf-8")
        (self.repo / realm.MANIFEST).symlink_to(outside)
        with self.assertRaises(realm.RealmError):
            realm.read_manifest(self.repo)
        self.assertEqual(outside.read_text(encoding="utf-8"), "not a realm\n")


class BoundaryTest(RealmBase):
    def test_only_an_explicit_canonical_git_root_is_accepted(self):
        child = self.repo / "child"
        child.mkdir()
        nongit = self.root / "nongit"
        nongit.mkdir()
        alias = self.root / "alias"
        alias.symlink_to(self.repo, target_is_directory=True)
        cases = (
            "relative/repo",
            str(child),
            str(nongit),
            str(alias),
            str(self.repo) + "/.",
            str(self.repo) + "\nsecond-line",
            str(self.repo) + "\u202e",
        )
        for value in cases:
            with self.subTest(repo=value):
                with self.assertRaises(realm.RealmError):
                    realm.explicit_repo(value)

    def test_git_probe_is_only_rev_parse(self):
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=str(self.repo) + "\n", stderr=""
        )
        with patch.object(realm.subprocess, "run", return_value=completed) as run:
            self.assertEqual(realm.explicit_repo(str(self.repo)), self.repo)
        command = run.call_args.args[0]
        self.assertEqual(command[-2:], ["rev-parse", "--show-toplevel"])
        self.assertIn("GIT_OPTIONAL_LOCKS", run.call_args.kwargs["env"])

    def test_source_has_no_network_capable_import(self):
        source = MODULE.read_text(encoding="utf-8")
        self.assertIsNone(
            re.search(
                r"(?m)^\s*(?:from|import)\s+(?:http|socket|urllib|requests)\b",
                source,
            )
        )
        self.assertNotIn("CROWNS.jsonl", source)
        self.assertNotIn("CIVIC.json", source)

    def test_readme_holds_the_constitutional_and_collaboration_floor(self):
        text = " ".join(README.read_text(encoding="utf-8").split())
        for phrase in (
            "never means ownership of beings",
            "Article 0",
            "Article 2",
            "Article 4",
            "never fealty",
            "never inherited authority",
            "introduction, not dispatch",
            "invitation, not authority",
            "never a sovereign above them",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
