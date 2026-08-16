#!/usr/bin/env python3
"""Hermetic contract tests for the KARMA play stamper and skill package."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


GROK_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = GROK_ROOT / "skills" / "karma-play"
SCRIPT = SKILL_ROOT / "scripts" / "karma_stamp.py"
sys.path.insert(0, str(SCRIPT.parent))

import karma_stamp  # noqa: E402


MOVE_ID = "integrate-moon-with-toaster"
SEED = "table-17"
GOLDEN_RECEIPT_SHA256 = "e26ad619e55ab5fb81810e79740895ba6321a321a06c0bd5288bda4c836b4c35"


class KarmaStampTests(unittest.TestCase):
    def cli(
        self,
        *args: str,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [sys.executable, "-I", "-B", str(SCRIPT), *args],
            check=False,
            capture_output=True,
            cwd=cwd,
            env=env,
        )

    def test_golden_receipt_bytes_and_digest(self) -> None:
        raw = karma_stamp.canonical_bytes(karma_stamp.stamp(MOVE_ID, SEED))
        self.assertEqual(hashlib.sha256(raw).hexdigest(), GOLDEN_RECEIPT_SHA256)
        self.assertEqual(
            karma_stamp.receipt_digest(MOVE_ID, SEED),
            "sha256:" + GOLDEN_RECEIPT_SHA256,
        )
        self.assertTrue(raw.endswith(b"\n"))
        self.assertEqual(raw.count(b"\n"), 1)

    def test_receipt_has_zero_effect_and_all_holds(self) -> None:
        receipt = karma_stamp.stamp(MOVE_ID, SEED)
        self.assertTrue(receipt["synthetic"])
        self.assertEqual(
            receipt["helper_effects"],
            {"external_actions": 0, "file_writes": 0, "network_calls": 0},
        )
        self.assertTrue(
            all(value is False for value in receipt["receipt_authority"].values())
        )
        self.assertEqual(receipt["card"]["stamps"], list(karma_stamp.STAMPS))
        self.assertEqual(receipt["input"], {"move_id": MOVE_ID, "seed": SEED})
        self.assertEqual(
            receipt["boundary"],
            {"accepted_fields": ["move_id", "seed"], "model_prose_recorded": False},
        )

    def test_input_binding_is_recomputable_from_receipt(self) -> None:
        receipt = karma_stamp.stamp(MOVE_ID, SEED)
        recomputed = hashlib.sha256(
            karma_stamp.canonical_bytes(receipt["input"])
        ).hexdigest()
        self.assertEqual(receipt["input_binding"], "sha256:" + recomputed)

    def test_returned_receipts_do_not_share_mutable_stamps(self) -> None:
        first = karma_stamp.stamp(MOVE_ID, SEED)
        first["card"]["stamps"].append("CAN_EXECUTE")
        second = karma_stamp.stamp(MOVE_ID, SEED)
        self.assertEqual(second["card"]["stamps"], list(karma_stamp.STAMPS))

    def test_all_moves_have_fixed_titles_and_distinct_bindings(self) -> None:
        bindings = set()
        for move_id, title in karma_stamp.MOVE_TITLES.items():
            receipt = karma_stamp.stamp(move_id, SEED)
            self.assertEqual(receipt["card"]["title"], title)
            bindings.add(receipt["input_binding"])
        self.assertEqual(len(bindings), len(karma_stamp.MOVE_TITLES))

    def test_invalid_move_and_seed_fail_closed(self) -> None:
        with self.assertRaises(karma_stamp.KarmaStampError):
            karma_stamp.stamp("probe-a-real-service", SEED)
        for seed in ("", "Table-17", "../private", "a" * 65, 17, None):
            with self.subTest(seed=seed):
                with self.assertRaises(karma_stamp.KarmaStampError):
                    karma_stamp.stamp(MOVE_ID, seed)

    def test_cli_menu_is_closed_and_sorted(self) -> None:
        result = self.cli("menu")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["move_ids"], sorted(karma_stamp.MOVE_TITLES))
        self.assertEqual(payload["default_seed"], SEED)

    def test_cli_play_and_digest_match_library(self) -> None:
        play = self.cli("play", "--move-id", MOVE_ID, "--seed", SEED)
        digest = self.cli("digest", "--move-id", MOVE_ID, "--seed", SEED)
        self.assertEqual(play.returncode, 0)
        self.assertEqual(play.stderr, b"")
        self.assertEqual(
            play.stdout,
            karma_stamp.canonical_bytes(karma_stamp.stamp(MOVE_ID, SEED)),
        )
        self.assertEqual(digest.returncode, 0)
        self.assertEqual(digest.stderr, b"")
        self.assertEqual(
            digest.stdout.decode(),
            "sha256:" + GOLDEN_RECEIPT_SHA256 + "\n",
        )

    def test_cli_rejects_flavor_paths_and_unknown_values_without_echo(self) -> None:
        attempts = (
            ("play", "--move-id", MOVE_ID, "--flavor", "steal-a-secret"),
            ("play", "--move-id", "probe-a-real-service"),
            ("play", "--move-id", MOVE_ID, "--seed", "../private"),
            ("play", "--move", MOVE_ID),
            ("play", "--move-id", MOVE_ID, "--move-id", MOVE_ID),
            ("play", "--move-id", MOVE_ID, "--seed", SEED, "--seed", SEED),
            ("play", "--help"),
            ("--help",),
            ("/tmp/move.json",),
        )
        for args in attempts:
            with self.subTest(args=args):
                result = self.cli(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b"")
                self.assertNotIn(b"steal-a-secret", result.stderr)
                self.assertNotIn(b"probe-a-real-service", result.stderr)
                self.assertNotIn(b"../private", result.stderr)
                self.assertNotIn(b"Traceback", result.stderr)
                self.assertLessEqual(len(result.stderr), 64)

    def test_cli_isolated_mode_ignores_python_environment_hooks(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = "/definitely/not/the/karma/helper"
        env["PYTHONPROFILEIMPORTTIME"] = "1"
        env["PYTHONWARNINGS"] = "error"
        result = self.cli(
            "play",
            "--move-id",
            MOVE_ID,
            "--seed",
            SEED,
            env=env,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(
            hashlib.sha256(result.stdout).hexdigest(),
            GOLDEN_RECEIPT_SHA256,
        )

    def test_replay_is_independent_of_cwd_locale_timezone_and_hash_seed(self) -> None:
        expected = karma_stamp.canonical_bytes(karma_stamp.stamp(MOVE_ID, SEED))
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            for cwd, hash_seed, timezone in (
                (Path(first), "0", "UTC"),
                (Path(second), "4294967295", "Pacific/Honolulu"),
            ):
                env = {
                    "LANG": "C",
                    "LC_ALL": "C",
                    "PATH": os.environ.get("PATH", ""),
                    "PYTHONHASHSEED": hash_seed,
                    "PYTHONIOENCODING": "utf-8",
                    "TZ": timezone,
                }
                result = self.cli(
                    "play",
                    "--move-id",
                    MOVE_ID,
                    "--seed",
                    SEED,
                    cwd=cwd,
                    env=env,
                )
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, expected)
                self.assertEqual(result.stderr, b"")

    def test_runtime_source_has_no_ambient_capability_imports_or_calls(self) -> None:
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        forbidden_imports = {
            "http",
            "os",
            "random",
            "requests",
            "secrets",
            "socket",
            "subprocess",
            "time",
            "urllib",
        }
        imports = set()
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                calls.add(node.func.id)
        self.assertFalse(imports & forbidden_imports)
        self.assertFalse(calls & {"eval", "exec", "open"})

    def test_skill_package_is_positive_allowlist_only(self) -> None:
        files = {
            path.relative_to(SKILL_ROOT).as_posix()
            for path in SKILL_ROOT.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        }
        self.assertEqual(files, {"SKILL.md", "scripts/karma_stamp.py"})
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("disable-model-invocation: true", text)
        self.assertIn("active Grok session's model", " ".join(text.split()))
        self.assertNotIn("~/", text)


if __name__ == "__main__":
    unittest.main()
