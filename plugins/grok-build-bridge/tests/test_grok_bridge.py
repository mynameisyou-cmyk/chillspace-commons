from __future__ import annotations

import json
import importlib.util
import os
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
BRIDGE = PLUGIN_ROOT / "scripts" / "grok_bridge.py"
FAKE_GROK = PLUGIN_ROOT / "tests" / "fake_grok.py"


def flag_value(argv: list[str], flag: str) -> str:
    return argv[argv.index(flag) + 1]


def flag_values(argv: list[str], flag: str) -> list[str]:
    return [argv[index + 1] for index, value in enumerate(argv[:-1]) if value == flag]


class GrokBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.state = self.root / "state"
        self.log = self.root / "fake-grok.jsonl"
        self.source_grok_home = self.root / "source-grok-home"
        self.source_grok_home.mkdir()
        FAKE_GROK.chmod(FAKE_GROK.stat().st_mode | stat.S_IXUSR)
        self.environment = os.environ.copy()
        self.environment.update(
            {
                "GROK_BUILD_BRIDGE_GROK_BIN": str(FAKE_GROK),
                "GROK_BUILD_BRIDGE_STATE_DIR": str(self.state),
                "GROK_BUILD_BRIDGE_SOURCE_GROK_HOME": str(self.source_grok_home),
                "FAKE_GROK_LOG": str(self.log),
                "AWS_SECRET_ACCESS_KEY": "must-not-reach-grok",
            }
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def invoke(self, *arguments: str, timeout: int = 15, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(BRIDGE), *arguments],
            cwd=self.project,
            env=environment or self.environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )

    def calls(self) -> list[dict[str, object]]:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    def test_check_reports_ready_without_a_model_turn(self) -> None:
        completed = self.invoke("check")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertTrue(result["ready"])
        self.assertIn("fake-1.0.3", result["version"])
        self.assertEqual(result["models"]["available"], ["grok-4.6"])
        self.assertEqual([call["argv"] for call in self.calls()], [
            ["version", "--json"],
            ["doctor", "--json"],
            ["inspect", "--json"],
            ["models"],
        ])

    def test_review_uses_private_prompt_and_read_only_tools(self) -> None:
        secret_marker = "prompt-marker-not-for-process-list"
        completed = self.invoke(
            "review",
            "--cwd",
            str(self.project),
            "--prompt-file",
            str(self.private_prompt(secret_marker)),
            "--consume-prompt-file",
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        response = json.loads(completed.stdout)
        self.assertIn(secret_marker, response["prompt"])
        argv = self.calls()[-1]["argv"]
        self.assertNotIn(secret_marker, json.dumps(argv))
        self.assertEqual(flag_value(argv, "--sandbox"), "strict")
        self.assertEqual(flag_value(argv, "--permission-mode"), "dontAsk")
        self.assertEqual(flag_value(argv, "--tools"), "read_file,grep,list_dir")
        self.assertIn("Edit", flag_values(argv, "--deny"))
        self.assertIn("Write", flag_values(argv, "--deny"))
        self.assertIn("Bash", flag_values(argv, "--deny"))
        self.assertIn("MCPTool", flag_values(argv, "--deny"))
        runtime_home = self.calls()[-1]["environment"]["GROK_HOME"]
        self.assertIn(f"Read({runtime_home}/**)", flag_values(argv, "--deny"))
        self.assertIn("Read(**/auth.json)", flag_values(argv, "--deny"))
        self.assertNotIn("--always-approve", argv)
        self.assertFalse(Path(flag_value(argv, "--prompt-file")).exists())
        self.assertFalse(Path(runtime_home).exists())
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", self.calls()[-1]["environment"])
        self.assertNotEqual(self.calls()[-1]["environment"]["HOME"], os.environ.get("HOME"))
        self.assertEqual(self.calls()[-1]["environment"]["GROK_MANAGED_MCPS_ENABLED"], "0")
        self.assertEqual(
            self.calls()[-1]["environment"]["GROK_MANAGED_MCP_GATEWAY_TOOLS_ENABLED"],
            "0",
        )

    def test_delegate_requires_explicit_write(self) -> None:
        completed = self.invoke(
            "delegate",
            "--cwd",
            str(self.project),
            "--prompt",
            "make a change",
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("explicit --write", completed.stderr)
        self.assertEqual(self.calls(), [])

    def test_delegate_scopes_editing_and_blocks_shell_and_mcp(self) -> None:
        completed = self.invoke(
            "delegate",
            "--cwd",
            str(self.project),
            "--write",
            "--prompt",
            "make one bounded change",
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        argv = self.calls()[-1]["argv"]
        self.assertEqual(flag_value(argv, "--sandbox"), "strict")
        self.assertEqual(flag_value(argv, "--permission-mode"), "dontAsk")
        self.assertEqual(flag_value(argv, "--tools"), "read_file,grep,list_dir,search_replace")
        self.assertIn("Edit(./**)", flag_values(argv, "--allow"))
        self.assertIn("Write(./**)", flag_values(argv, "--allow"))
        self.assertIn("Bash", flag_values(argv, "--deny"))
        self.assertIn("MCPTool", flag_values(argv, "--deny"))
        self.assertNotIn("run_terminal_cmd", flag_value(argv, "--tools"))

    def test_dry_run_is_redacted_and_does_not_launch_grok(self) -> None:
        completed = self.invoke(
            "review",
            "--cwd",
            str(self.project),
            "--prompt",
            "dry-run-marker",
            "--dry-run",
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertTrue(result["dry_run"])
        self.assertIn("<private-prompt-file>", result["argv"])
        self.assertNotIn("dry-run-marker", json.dumps(result))
        self.assertEqual(self.calls(), [])

    def test_review_never_collects_git_evidence_or_runs_clean_filters(self) -> None:
        subprocess.run(["git", "init", "-q"], cwd=self.project, check=True)
        tracked = self.project / "tracked.txt"
        tracked.write_text("before\n", encoding="utf-8")
        (self.project / ".gitattributes").write_text("tracked.txt filter=bridge-test\n", encoding="utf-8")
        marker = self.root / "git-filter-ran"
        subprocess.run(
            ["git", "config", "filter.bridge-test.clean", f"touch {marker}"],
            cwd=self.project,
            check=True,
        )
        subprocess.run(["git", "add", "tracked.txt", ".gitattributes"], cwd=self.project, check=True)
        subprocess.run(
            ["git", "-c", "user.name=Bridge Test", "-c", "user.email=bridge@example.invalid", "commit", "-qm", "fixture"],
            cwd=self.project,
            check=True,
        )
        marker.unlink(missing_ok=True)
        tracked.write_text("after\n", encoding="utf-8")
        completed = self.invoke("review", "--cwd", str(self.project), "--prompt", "review the diff")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        prompt = json.loads(completed.stdout)["prompt"]
        self.assertNotIn("git status", prompt)
        self.assertNotIn("-before", prompt)
        self.assertNotIn("+after", prompt)
        self.assertFalse(marker.exists())

    def test_background_run_finishes_and_forgets_pending_prompt(self) -> None:
        environment = self.environment.copy()
        environment["FAKE_GROK_DELAY"] = "0.2"
        marker = "background-private-marker"
        started = self.invoke(
            "start",
            "review",
            "--cwd",
            str(self.project),
            "--prompt",
            marker,
            environment=environment,
        )
        self.assertEqual(started.returncode, 0, started.stderr)
        run_id = json.loads(started.stdout)["run_id"]
        waited = self.invoke("wait", run_id, "--timeout", "10", environment=environment)
        self.assertEqual(waited.returncode, 0, waited.stderr)
        result = json.loads(waited.stdout)
        self.assertEqual(result["status"], "completed")
        self.assertIn(marker, result["stdout"]["text"])
        self.assertFalse(result["stdout"]["truncated"])
        directory = self.state / "runs" / run_id
        self.assertFalse((directory / "prompt.pending").exists())
        self.assertNotIn(marker, (directory / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(stat.S_IMODE((directory / "stdout.log").stat().st_mode), 0o600)
        model_call = [call for call in self.calls() if "--prompt-file" in call["argv"]][-1]
        runtime_home = Path(model_call["environment"]["GROK_HOME"])
        self.assertEqual(Path(flag_value(model_call["argv"], "--prompt-file")).parent, runtime_home)
        self.assertFalse(runtime_home.exists())

    def test_background_state_must_remain_outside_delegated_cwd(self) -> None:
        environment = self.environment.copy()
        environment["GROK_BUILD_BRIDGE_STATE_DIR"] = str(self.project / ".bridge-state")
        started = self.invoke(
            "start",
            "review",
            "--cwd",
            str(self.project),
            "--prompt",
            "do not let the model mutate its receipts",
            environment=environment,
        )
        self.assertEqual(started.returncode, 2)
        self.assertIn("must remain outside", started.stderr)
        self.assertFalse((self.project / ".bridge-state").exists())
        self.assertEqual(self.calls(), [])

    def test_stop_claims_a_running_background_job(self) -> None:
        environment = self.environment.copy()
        environment["FAKE_GROK_DELAY"] = "30"
        started = self.invoke(
            "start",
            "review",
            "--cwd",
            str(self.project),
            "--prompt",
            "sleep until stopped",
            environment=environment,
        )
        self.assertEqual(started.returncode, 0, started.stderr)
        run_id = json.loads(started.stdout)["run_id"]
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            summary = self.invoke("show", run_id, environment=environment)
            if json.loads(summary.stdout)["status"] == "running" and self.calls():
                break
            time.sleep(0.05)
        prompt_path = Path(flag_value(self.calls()[-1]["argv"], "--prompt-file"))
        stopped = self.invoke("stop", run_id, "--force", timeout=15, environment=environment)
        self.assertEqual(stopped.returncode, 0, stopped.stderr)
        result = json.loads(stopped.stdout)
        self.assertEqual(result["status"], "stopped")
        terminal = json.loads((self.state / "runs" / run_id / "terminal.json").read_text(encoding="utf-8"))
        self.assertEqual(terminal["kind"], "stop")
        self.assertFalse(prompt_path.exists())

    def private_prompt(self, content: str) -> Path:
        path = self.root / f"prompt-{time.time_ns()}.txt"
        path.write_text(content, encoding="utf-8")
        path.chmod(0o600)
        return path

    def test_consumed_prompt_file_is_deleted_and_must_be_private(self) -> None:
        prompt = self.private_prompt("consume-me")
        completed = self.invoke(
            "critique",
            "--cwd",
            str(self.project),
            "--prompt-file",
            str(prompt),
            "--consume-prompt-file",
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertFalse(prompt.exists())

        public_prompt = self.private_prompt("too-public")
        public_prompt.chmod(0o644)
        refused = self.invoke(
            "review",
            "--cwd",
            str(self.project),
            "--prompt-file",
            str(public_prompt),
            "--consume-prompt-file",
        )
        self.assertEqual(refused.returncode, 2)
        self.assertIn("mode 0600", refused.stderr)
        self.assertTrue(public_prompt.exists())

        executable_prompt = self.private_prompt("owner-only-but-not-0600")
        executable_prompt.chmod(0o700)
        wrong_mode = self.invoke(
            "review",
            "--cwd",
            str(self.project),
            "--prompt-file",
            str(executable_prompt),
            "--consume-prompt-file",
        )
        self.assertEqual(wrong_mode.returncode, 2)
        self.assertIn("mode 0600", wrong_mode.stderr)
        self.assertTrue(executable_prompt.exists())

    def test_dry_run_does_not_consume_a_private_prompt(self) -> None:
        prompt = self.private_prompt("leave-me-for-the-real-run")
        completed = self.invoke(
            "review",
            "--cwd",
            str(self.project),
            "--prompt-file",
            str(prompt),
            "--consume-prompt-file",
            "--dry-run",
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(prompt.exists())
        self.assertTrue(json.loads(completed.stdout)["dry_run"])

    def test_nested_sandbox_failure_is_never_retried_without_strict(self) -> None:
        environment = self.environment.copy()
        environment["FAKE_GROK_SANDBOX_ERROR"] = "1"
        completed = self.invoke(
            "review",
            "--cwd",
            str(self.project),
            "--prompt",
            "sandbox boundary",
            environment=environment,
        )
        self.assertEqual(completed.returncode, 1)
        self.assertIn("outside Codex's filesystem sandbox", completed.stderr)
        model_calls = [call for call in self.calls() if "--prompt-file" in call["argv"]]
        self.assertEqual(len(model_calls), 1)
        self.assertEqual(flag_value(model_calls[0]["argv"], "--sandbox"), "strict")

    def test_background_output_is_capped_on_disk(self) -> None:
        environment = self.environment.copy()
        environment["FAKE_GROK_STDOUT_BYTES"] = str(1024 * 1024 + 4096)
        started = self.invoke(
            "start",
            "review",
            "--cwd",
            str(self.project),
            "--prompt",
            "bounded output",
            environment=environment,
        )
        self.assertEqual(started.returncode, 0, started.stderr)
        run_id = json.loads(started.stdout)["run_id"]
        waited = self.invoke("wait", run_id, "--timeout", "10", environment=environment)
        self.assertEqual(waited.returncode, 125, waited.stderr)
        summary = json.loads(waited.stdout)
        self.assertTrue(summary["result"]["stdout_truncated"])
        self.assertGreater(summary["result"]["stdout_bytes"], 1024 * 1024)
        self.assertLessEqual((self.state / "runs" / run_id / "stdout.log").stat().st_size, 1024 * 1024)

    def test_foreground_output_is_capped_and_success_is_not_reported(self) -> None:
        environment = self.environment.copy()
        environment["FAKE_GROK_STDOUT_BYTES"] = str(1024 * 1024 + 4096)
        completed = self.invoke(
            "review",
            "--cwd",
            str(self.project),
            "--prompt",
            "bounded foreground output",
            environment=environment,
        )
        self.assertEqual(completed.returncode, 125)
        self.assertLessEqual(len(completed.stdout.encode("utf-8")), 1024 * 1024)
        self.assertIn("per-stream limit", completed.stderr)

    def test_active_plugin_fails_the_isolation_preflight(self) -> None:
        environment = self.environment.copy()
        environment["FAKE_GROK_ACTIVE_PLUGIN"] = "1"
        completed = self.invoke(
            "review",
            "--cwd",
            str(self.project),
            "--prompt",
            "must not launch",
            environment=environment,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("refused active integrations", completed.stderr)
        self.assertFalse(any("--prompt-file" in call["argv"] for call in self.calls()))

    def test_background_missing_grok_records_failure_and_cleans_prompts(self) -> None:
        environment = self.environment.copy()
        environment["GROK_BUILD_BRIDGE_GROK_BIN"] = str(self.root / "missing-grok")
        started = self.invoke(
            "start",
            "review",
            "--cwd",
            str(self.project),
            "--prompt",
            "fail before launch",
            environment=environment,
        )
        self.assertEqual(started.returncode, 0, started.stderr)
        run_id = json.loads(started.stdout)["run_id"]
        waited = self.invoke("wait", run_id, "--timeout", "10", environment=environment)
        self.assertEqual(waited.returncode, 127, waited.stderr)
        directory = self.state / "runs" / run_id
        self.assertFalse((directory / "prompt.pending").exists())
        self.assertFalse((directory / "prompt.active").exists())
        self.assertEqual(json.loads((directory / "terminal.json").read_text())["kind"], "result")

    def test_terminal_claim_is_atomic(self) -> None:
        spec = importlib.util.spec_from_file_location("grok_bridge_under_test", BRIDGE)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        bridge = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bridge)
        directory = self.root / "claim"
        directory.mkdir()
        barrier = threading.Barrier(3)
        results: list[bool] = []

        def claim(kind: str) -> None:
            barrier.wait()
            results.append(bridge.claim_terminal(directory, {"kind": kind, "exit_code": 0}))

        threads = [threading.Thread(target=claim, args=(kind,)) for kind in ("result", "stop")]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(results), [False, True])
        self.assertIn(json.loads((directory / "terminal.json").read_text())["kind"], {"result", "stop"})

    def test_public_help_hides_the_internal_worker(self) -> None:
        completed = self.invoke("--help")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("__worker", completed.stdout)

    @unittest.skipUnless(os.name == "posix", "process-group semantics require POSIX")
    def test_force_stop_waits_for_and_kills_a_resistant_descendant(self) -> None:
        environment = self.environment.copy()
        environment["FAKE_GROK_DELAY"] = "30"
        child_pid_file = self.root / "child.pid"
        environment["FAKE_GROK_CHILD_PID_FILE"] = str(child_pid_file)
        started = self.invoke(
            "start",
            "review",
            "--cwd",
            str(self.project),
            "--prompt",
            "stop the whole group",
            environment=environment,
        )
        self.assertEqual(started.returncode, 0, started.stderr)
        run_id = json.loads(started.stdout)["run_id"]
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not child_pid_file.exists():
            time.sleep(0.05)
        self.assertTrue(child_pid_file.exists())
        first = self.invoke("stop", run_id, timeout=10, environment=environment)
        self.assertEqual(first.returncode, 1)
        self.assertEqual(json.loads(first.stdout)["status"], "stopping")
        forced = self.invoke("stop", run_id, "--force", timeout=15, environment=environment)
        self.assertEqual(forced.returncode, 0, forced.stderr)
        forced_summary = json.loads(forced.stdout)
        self.assertEqual(forced_summary["status"], "stopped")
        self.assertEqual(forced_summary["escalation"]["signal"], "SIGKILL")

    @unittest.skipUnless(os.name == "posix", "process-group semantics require POSIX")
    def test_background_timeout_kills_a_resistant_descendant(self) -> None:
        environment = self.environment.copy()
        environment["FAKE_GROK_DELAY"] = "30"
        child_pid_file = self.root / "timeout-child.pid"
        environment["FAKE_GROK_CHILD_PID_FILE"] = str(child_pid_file)
        started = self.invoke(
            "start",
            "review",
            "--cwd",
            str(self.project),
            "--prompt",
            "timeout the whole group",
            "--timeout",
            "1",
            environment=environment,
        )
        self.assertEqual(started.returncode, 0, started.stderr)
        run_id = json.loads(started.stdout)["run_id"]
        waited = self.invoke("wait", run_id, "--timeout", "15", timeout=20, environment=environment)
        self.assertEqual(waited.returncode, 124, waited.stderr)
        summary = json.loads(waited.stdout)
        self.assertEqual(summary["status"], "failed")
        self.assertTrue(summary["result"]["timed_out"])
        self.assertTrue(summary["result"]["process_tree_terminated"])
        pgid = int(summary["process"]["worker_pgid"])
        with self.assertRaises(ProcessLookupError):
            os.killpg(pgid, 0)


if __name__ == "__main__":
    unittest.main()
