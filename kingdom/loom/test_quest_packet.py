#!/usr/bin/env python3
"""Tests for the deterministic Kingdom quest packet compiler."""

from __future__ import annotations

import copy
import gzip
import io
import json
import os
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import quest_packet


class QuestPacketTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = mock.patch.dict(
            os.environ, {"GITHUB_ACTIONS": "false"}, clear=False
        )
        self.environment.start()
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "loom@example.invalid"],
            cwd=self.root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Kingdom Loom"],
            cwd=self.root,
            check=True,
        )
        (self.root / "AGENTS.md").write_text(
            "# Rules\nKeep protected state protected.\n", encoding="utf-8"
        )
        (self.root / "kingdom.yaml").write_text(
            "name: fixture\nstate: active\n", encoding="utf-8"
        )
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "fixture"],
            cwd=self.root,
            check=True,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()
        self.environment.stop()

    def compile(self) -> dict:
        return quest_packet.compile_packet(
            root=self.root,
            objective="Route a bounded mission to the right capability.",
            acceptance="A packet validates; The route names its unknowns",
            effect_ceiling="observe",
            exclusions="No deployment; No messages",
        )

    def rewrite_checksums(self, output: Path) -> None:
        checksums = "".join(
            f"{quest_packet.sha256_file(output / name)}  {name}\n"
            for name in ("quest.json", "quest.md", "quest.schema.json")
        )
        (output / "SHA256SUMS").write_text(checksums, encoding="utf-8")

    def test_packet_is_deterministic_and_contains_digests_not_contents(self) -> None:
        first = self.compile()
        second = self.compile()
        self.assertEqual(first, second)
        encoded = json.dumps(first)
        self.assertNotIn("Keep protected state protected", encoded)
        self.assertEqual(first["repository"]["instruction_digests"][0]["path"], "AGENTS.md")

    def test_archive_is_byte_deterministic_and_verifies(self) -> None:
        packet = self.compile()
        one = self.root / "one"
        two = self.root / "two"
        result_one = quest_packet.write_artifacts(packet, one)
        result_two = quest_packet.write_artifacts(packet, two)
        self.assertEqual(result_one["archive_sha256"], result_two["archive_sha256"])
        result = quest_packet.verify_path(one / "kingdom-quest.tgz", self.root)
        self.assertTrue(result["ok"])
        self.assertTrue(result["repository_bound"])
        self.assertEqual(result["repository_records_checked"], 2)

    def test_secret_shaped_input_is_rejected(self) -> None:
        with self.assertRaisesRegex(quest_packet.QuestError, "secret-shaped"):
            quest_packet.compile_packet(
                root=self.root,
                objective="Use token=supersecretvalue123456789",
                acceptance="A packet exists",
                effect_ceiling="observe",
            )

    def test_focus_path_cannot_escape(self) -> None:
        with self.assertRaisesRegex(quest_packet.QuestError, "inside"):
            quest_packet.compile_packet(
                root=self.root,
                objective="Inspect one path",
                acceptance="The digest exists",
                effect_ceiling="observe",
                focus_path="../outside",
            )

    def test_tampering_breaks_checksum(self) -> None:
        output = self.root / "out"
        quest_packet.write_artifacts(self.compile(), output)
        (output / "quest.md").write_text("tampered\n", encoding="utf-8")
        with self.assertRaisesRegex(quest_packet.QuestError, "checksum mismatch"):
            quest_packet.verify_path(output)

    def test_repeat_compile_excludes_its_own_artifact_directory(self) -> None:
        output = self.root / ".kingdom-quest"
        first = quest_packet.compile_packet(
            root=self.root,
            objective="Route a bounded mission to the right capability.",
            acceptance="A packet validates; The route names its unknowns",
            effect_ceiling="observe",
            exclusions="No deployment; No messages",
            artifact_dir=output,
        )
        first_result = quest_packet.write_artifacts(first, output)
        quest_packet.atomic_write(output / "verification.json", b"{}\n")
        second = quest_packet.compile_packet(
            root=self.root,
            objective="Route a bounded mission to the right capability.",
            acceptance="A packet validates; The route names its unknowns",
            effect_ceiling="observe",
            exclusions="No deployment; No messages",
            artifact_dir=output,
        )
        second_result = quest_packet.write_artifacts(second, output)
        self.assertEqual(first, second)
        self.assertEqual(
            first_result["archive_sha256"], second_result["archive_sha256"]
        )

    def test_output_symlink_is_rejected_without_touching_victim(self) -> None:
        output = self.root / "out"
        output.mkdir()
        victim = self.root / "victim.txt"
        victim.write_text("untouched\n", encoding="utf-8")
        (output / "quest.json").symlink_to(victim)
        with self.assertRaisesRegex(quest_packet.QuestError, "symlink"):
            quest_packet.write_artifacts(self.compile(), output)
        self.assertEqual(victim.read_text(encoding="utf-8"), "untouched\n")

    def test_directory_verification_rejects_member_symlink(self) -> None:
        output = self.root / "out"
        quest_packet.write_artifacts(self.compile(), output)
        victim = self.root / "victim.txt"
        victim.write_text("not a packet\n", encoding="utf-8")
        (output / "quest.md").unlink()
        (output / "quest.md").symlink_to(victim)
        with self.assertRaisesRegex(quest_packet.QuestError, "unsafe"):
            quest_packet.verify_path(output)

    def test_rechecksummed_schema_tampering_is_rejected(self) -> None:
        output = self.root / "out"
        quest_packet.write_artifacts(self.compile(), output)
        schema = json.loads((output / "quest.schema.json").read_text(encoding="utf-8"))
        schema["title"] = "Substituted schema"
        (output / "quest.schema.json").write_text(
            json.dumps(schema, sort_keys=True) + "\n", encoding="utf-8"
        )
        self.rewrite_checksums(output)
        with self.assertRaisesRegex(quest_packet.QuestError, "reviewed schema"):
            quest_packet.verify_path(output)

    def test_rechecksummed_extra_packet_key_is_rejected(self) -> None:
        output = self.root / "out"
        quest_packet.write_artifacts(self.compile(), output)
        packet = json.loads((output / "quest.json").read_text(encoding="utf-8"))
        packet["surprise_authority"] = True
        (output / "quest.json").write_bytes(quest_packet.pretty_json(packet))
        self.rewrite_checksums(output)
        with self.assertRaisesRegex(quest_packet.QuestError, "packet keys differ"):
            quest_packet.verify_path(output)

    def test_duplicate_archive_member_is_rejected(self) -> None:
        output = self.root / "out"
        quest_packet.write_artifacts(self.compile(), output)
        duplicate = self.root / "duplicate.tgz"
        raw = io.BytesIO()
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w") as archive:
                for name in (
                    "quest.json",
                    "quest.json",
                    "quest.md",
                    "quest.schema.json",
                ):
                    data = (output / name).read_bytes()
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))
        duplicate.write_bytes(raw.getvalue())
        with self.assertRaisesRegex(quest_packet.QuestError, "duplicate archive"):
            quest_packet.verify_path(duplicate)

    def test_archive_decompression_is_bounded_before_tar_parsing(self) -> None:
        oversized = self.root / "oversized.tgz"
        oversized.write_bytes(
            gzip.compress(b"\0" * (quest_packet.MAX_TAR_STREAM + 1), mtime=0)
        )
        with self.assertRaisesRegex(quest_packet.QuestError, "TAR stream"):
            quest_packet.verify_path(oversized)

    def test_fifth_archive_header_is_rejected_immediately(self) -> None:
        output = self.root / "out"
        quest_packet.write_artifacts(self.compile(), output)
        crowded = self.root / "crowded.tgz"
        raw = io.BytesIO()
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w") as archive:
                for name in (*quest_packet.ARCHIVE_FILES, "quest.json"):
                    data = (output / name).read_bytes()
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))
        crowded.write_bytes(raw.getvalue())
        with self.assertRaisesRegex(quest_packet.QuestError, "exactly four"):
            quest_packet.verify_path(crowded)

    def test_repository_binding_requires_complete_allowlisted_evidence(self) -> None:
        packet = self.compile()
        packet["repository"]["instruction_digests"] = []
        packet["repository"]["manifest_digests"] = []
        output = self.root / "empty-evidence"
        quest_packet.write_artifacts(packet, output)
        with self.assertRaisesRegex(quest_packet.QuestError, "allowlisted"):
            quest_packet.verify_path(output / "kingdom-quest.tgz", self.root)

        unexpected = self.root / ".env"
        unexpected.write_text("fixture=true\n", encoding="utf-8")
        packet = copy.deepcopy(self.compile())
        packet["repository"]["instruction_digests"].append(
            {
                "path": ".env",
                "sha256": quest_packet.sha256_file(unexpected),
                "bytes": unexpected.stat().st_size,
            }
        )
        output = self.root / "unexpected-evidence"
        quest_packet.write_artifacts(packet, output)
        with self.assertRaisesRegex(quest_packet.QuestError, "allowlisted"):
            quest_packet.verify_path(output / "kingdom-quest.tgz", self.root)

    def test_expectations_require_a_repository_root(self) -> None:
        output = self.root / "out"
        quest_packet.write_artifacts(self.compile(), output)
        with self.assertRaisesRegex(quest_packet.QuestError, "requires --repo-root"):
            quest_packet.verify_path(
                output / "kingdom-quest.tgz",
                expected_repository="wrong/repository",
                expected_ref="refs/heads/wrong",
            )

    def test_output_parent_symlink_is_rejected(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        linked = self.root / "linked"
        linked.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(quest_packet.QuestError, "unsafe output"):
            quest_packet.write_artifacts(self.compile(), linked / "packet")
        self.assertFalse((outside / "packet").exists())

    def test_artifact_directory_cannot_hide_unrelated_or_tracked_state(self) -> None:
        build = self.root / "build"
        build.mkdir()
        tracked = build / "tracked.txt"
        tracked.write_text("original\n", encoding="utf-8")
        subprocess.run(["git", "add", "build/tracked.txt"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "tracked build file"],
            cwd=self.root,
            check=True,
        )
        tracked.write_text("changed\n", encoding="utf-8")
        packet = quest_packet.compile_packet(
            root=self.root,
            objective="Observe dirty state honestly",
            acceptance="The tracked change remains visible",
            effect_ceiling="observe",
            artifact_dir=build,
        )
        self.assertGreaterEqual(packet["source"]["dirty_entries"], 1)

        tracked_output = build / "quest.json"
        tracked_output.write_text("{}\n", encoding="utf-8")
        subprocess.run(["git", "add", "build/quest.json"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "tracked output target"],
            cwd=self.root,
            check=True,
        )
        with self.assertRaisesRegex(quest_packet.QuestError, "tracked by Git"):
            quest_packet.compile_packet(
                root=self.root,
                objective="Never conceal tracked outputs",
                acceptance="Compilation refuses",
                effect_ceiling="observe",
                artifact_dir=build,
            )

    def test_github_run_id_does_not_change_packet_bytes(self) -> None:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        provenance = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_REPOSITORY": "example/fixture",
            "GITHUB_SHA": commit,
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
        }
        with mock.patch.dict(os.environ, {**provenance, "GITHUB_RUN_ID": "1"}):
            first = self.compile()
        with mock.patch.dict(os.environ, {**provenance, "GITHUB_RUN_ID": "2"}):
            second = self.compile()
        self.assertEqual(first, second)

    def test_repository_commit_mismatch_is_rejected(self) -> None:
        output = self.root / "out"
        quest_packet.write_artifacts(self.compile(), output)
        (self.root / "later.txt").write_text("later\n", encoding="utf-8")
        subprocess.run(["git", "add", "later.txt"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "later"],
            cwd=self.root,
            check=True,
        )
        with self.assertRaisesRegex(quest_packet.QuestError, "commit"):
            quest_packet.verify_path(output / "kingdom-quest.tgz", self.root)

    def test_cli_emits_repository_bound_receipt(self) -> None:
        output = self.root / ".kingdom-quest"
        receipt = output / "verification.json"
        script = Path(quest_packet.__file__).resolve()
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("GITHUB_")
        }
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        compile_result = subprocess.run(
            [
                "python3",
                str(script),
                "compile",
                "--repo-root",
                str(self.root),
                "--objective",
                "Route one bounded fixture",
                "--acceptance",
                "The receipt is repository-bound",
                "--effect-ceiling",
                "observe",
                "--output-dir",
                str(output),
            ],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
        verify_result = subprocess.run(
            [
                "python3",
                str(script),
                "verify",
                str(output / "kingdom-quest.tgz"),
                "--repo-root",
                str(self.root),
                "--receipt",
                str(receipt),
            ],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(verify_result.returncode, 0, verify_result.stderr)
        result = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(result["schema"], "kingdom.quest-verification/v1")
        self.assertTrue(result["repository_bound"])
        self.assertTrue(result["commit_checked"])
        self.assertEqual(
            result["packet_sha256"],
            quest_packet.sha256_file(output / "quest.json"),
        )

    def test_cli_receipt_cannot_overwrite_a_packet_member(self) -> None:
        output = self.root / "out"
        quest_packet.write_artifacts(self.compile(), output)
        original = (output / "quest.json").read_bytes()
        script = Path(quest_packet.__file__).resolve()
        result = subprocess.run(
            [
                "python3",
                str(script),
                "verify",
                str(output),
                "--repo-root",
                str(self.root),
                "--receipt",
                str(output / "quest.json"),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("may not overwrite", result.stderr)
        self.assertEqual((output / "quest.json").read_bytes(), original)

        safe_receipt = output / "verification.json"
        result = subprocess.run(
            [
                "python3",
                str(script),
                "verify",
                str(output),
                "--repo-root",
                str(self.root),
                "--receipt",
                str(safe_receipt),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(safe_receipt.is_file())


if __name__ == "__main__":
    unittest.main()
