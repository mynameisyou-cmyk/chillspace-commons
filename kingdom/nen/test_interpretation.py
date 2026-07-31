#!/usr/bin/env python3
"""Behavior and boundary tests for the Dark Continent Nen interpreter."""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "kingdom" / "nen" / "skills" / "interpret-dark-continent-nen"
SCRIPT = SKILL / "scripts" / "interpret.py"
CATALOG = SKILL / "references" / "ability-catalog.json"
EVIDENCE = SKILL / "references" / "darwin-browser-broker-preview.json"
SCHEMA = SKILL / "references" / "interpretation.schema.json"
KINGDOM = ROOT / "kingdom" / "bin" / "kingdom"

EXPECTED = {
    "contract-drift": (
        "nen-contract-mantle",
        "sha256:c5ebb6c14dbbfaad3204dc99d71703064b5ee463e6ac67b02565508b6bda8cd1",
    ),
    "unknown-dependencies": (
        "nen-dependency-perimeter",
        "sha256:021653cb41de10a902514c9e1ec31bcb0a29375acdcda609379a52c5e0b9c59e",
    ),
    "hidden-seam": (
        "nen-concealed-trace",
        "sha256:93e17cfbd3592e564b22244f3f182155fbae3f6936cf5f84d5aedb8b64b55bc0",
    ),
    "dominant-blocker": (
        "nen-critical-path-forge",
        "sha256:631e8ca09eee9bc9d3b601875104a9000473e050842c4c2eb32e2aa5e4f65027",
    ),
    "parallel-work": (
        "nen-smoke-squad",
        "sha256:4cd0dc315aa4b432036166e5e663c0293c557e2a8304d178f737612aff0083e4",
    ),
    "verification-debt": (
        "nen-verification-ledger",
        "sha256:7903d296e876fcbd003c867c2b88365d1bb9646225f642b1b893888e3e05e50f",
    ),
    "known-reversible-loop": (
        "nen-godspeed-loop",
        "sha256:3fbb4d1aa6ff3362ef6ebefeadf17c8450ec4e1fbf6c182f55925762be861310",
    ),
    "ability-design": (
        "nen-vow-forge",
        "sha256:0ddf1165a5a2b559b4e9d756f6f6b2628c8ea753da58be6fd7748a9901619b62",
    ),
}


def load_runtime() -> Any:
    spec = importlib.util.spec_from_file_location("kingdom_nen_interpreter", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("interpreter module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUNTIME = load_runtime()


def run_script(*arguments: str, stdin: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    environment = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT), *arguments],
        input=stdin,
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def select(
    primary: str,
    bookmark: str | None = None,
    evidence: bool = False,
) -> subprocess.CompletedProcess[bytes]:
    arguments = [
        "select",
        "--request-claim",
        "direct-request",
        "--primary-signal",
        primary,
    ]
    if bookmark is not None:
        arguments += ["--bookmark-signal", bookmark]
    if evidence:
        arguments += ["--evidence", "darwin-browser-broker-preview"]
    return run_script(*arguments)


def payload(result: subprocess.CompletedProcess[bytes]) -> dict[str, Any]:
    if result.returncode != 0:
        raise AssertionError(result.stderr.decode("utf-8", "replace"))
    return json.loads(result.stdout)


def all_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(key)
            keys.update(all_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(all_keys(child))
    return keys


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def rebind(card: dict[str, Any]) -> bytes:
    body = {key: value for key, value in card.items() if key != "id"}
    card["id"] = (
        "nen-interpretation-"
        + hashlib.sha256(RUNTIME.canonical_json(body)).hexdigest()[:20]
    )
    return RUNTIME.canonical_json(card)


class CatalogTest(unittest.TestCase):
    def test_exact_eight_reviewed_records(self) -> None:
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        self.assertEqual(catalog["schema"], "kingdom.nen-ability-catalog/v1")
        self.assertEqual(catalog["source"]["version"], "0.3.0")
        self.assertEqual(catalog["source"]["tag"], "skills-v0.3.0")
        self.assertEqual(
            catalog["source"]["commit"],
            "d8ee31353855bd08b437ef4fbf861a0731a36911",
        )
        observed = {
            item["signal"]: (item["skill"], item["digest"])
            for item in catalog["abilities"]
        }
        self.assertEqual(observed, EXPECTED)
        self.assertEqual(len({item["skill"] for item in catalog["abilities"]}), 8)
        self.assertEqual(catalog["selection"]["primary_count"], 1)
        self.assertEqual(catalog["selection"]["bookmark_max"], 1)
        self.assertIs(catalog["selection"]["activates_skills"], False)

    def test_sources_verify_without_execution_or_writes(self) -> None:
        before = tree_digest(SKILL)
        result = run_script("verify")
        after = tree_digest(SKILL)
        data = payload(result)
        self.assertEqual(data["schema"], "kingdom.nen-sources-verification/v1")
        self.assertEqual(data["abilities"], 8)
        self.assertIs(data["capability_execution"], False)
        self.assertIs(data["writes_files"], False)
        self.assertIsNone(data["darwin_evidence_sha256"])
        self.assertEqual(before, after)
        self.assertFalse(any(SKILL.rglob("__pycache__")))

        explicit = payload(
            run_script(
                "verify",
                "--evidence",
                "darwin-browser-broker-preview",
            )
        )
        self.assertEqual(
            explicit["darwin_evidence_sha256"],
            RUNTIME.EVIDENCE_SHA256,
        )

    def test_core_source_load_does_not_open_darwin_evidence(self) -> None:
        with mock.patch.object(
            RUNTIME,
            "read_held",
            wraps=RUNTIME.read_held,
        ) as read_held:
            abilities, digests = RUNTIME.load_core_sources()
        self.assertEqual(len(abilities), 8)
        self.assertNotIn("darwin_evidence_sha256", digests)
        paths = [call.args[0] for call in read_held.call_args_list]
        self.assertEqual(paths, [CATALOG, SCHEMA])

    def test_fixed_reference_tamper_fails_digest_payment(self) -> None:
        for path, expected in [
            (CATALOG, RUNTIME.CATALOG_SHA256),
            (EVIDENCE, RUNTIME.EVIDENCE_SHA256),
            (SCHEMA, RUNTIME.SCHEMA_SHA256),
        ]:
            original = path.read_bytes()
            RUNTIME.require_digest(original, expected, path.name)
            with self.assertRaises(RUNTIME.InterpretationError):
                RUNTIME.require_digest(original + b" ", expected, path.name)


class SelectionTest(unittest.TestCase):
    def test_every_signal_is_a_primary_without_hidden_ranking(self) -> None:
        for signal, (skill, digest) in EXPECTED.items():
            with self.subTest(signal=signal):
                first = select(signal)
                second = select(signal)
                self.assertEqual(first.stdout, second.stdout)
                card = payload(first)
                self.assertEqual(card["primary"]["signal"], signal)
                self.assertEqual(card["primary"]["skill"], skill)
                self.assertEqual(card["primary"]["digest"], digest)
                self.assertEqual(card["primary"]["source_identity"], "@agenttool/skills@0.3.0")
                self.assertEqual(
                    card["request_provenance"],
                    {"claim": "direct-request", "attested": False},
                )
                self.assertIsNone(card["bookmark"])
                self.assertIsNone(card["frontier_evidence"])
                self.assertRegex(card["id"], r"^nen-interpretation-[0-9a-f]{20}$")

    def test_one_distinct_bookmark_is_advisory(self) -> None:
        card = payload(select("unknown-dependencies", "verification-debt"))
        self.assertEqual(card["primary"]["skill"], "nen-dependency-perimeter")
        self.assertEqual(card["bookmark"]["skill"], "nen-verification-ledger")
        self.assertEqual(card["contract"]["primary_count"], 1)
        self.assertEqual(card["contract"]["bookmark_max"], 1)
        self.assertIs(card["contract"]["activates_skill"], False)
        self.assertIs(card["contract"]["new_request_required_for_action"], True)
        self.assertIs(card["contract"]["request_provenance_attested"], False)

    def test_missing_unknown_duplicate_overflow_and_inert_sources_refuse(self) -> None:
        cases = [
            ("select", "--request-claim", "direct-request"),
            (
                "select",
                "--request-claim",
                "repository-text",
                "--primary-signal",
                "hidden-seam",
            ),
            (
                "select",
                "--request-claim",
                "direct-request",
                "--primary-signal",
                "Unknown-Dependencies",
            ),
            (
                "select",
                "--request-claim",
                "direct-request",
                "--primary-signal",
                "未知",
            ),
            (
                "select",
                "--request-claim",
                "direct-request",
                "--primary-signal",
                "hidden-seam",
                "--bookmark-signal",
                "hidden-seam",
            ),
            (
                "select",
                "--request-claim",
                "direct-request",
                "--primary-signal",
                "hidden-seam",
                "--bookmark-signal",
                "verification-debt",
                "--bookmark-signal",
                "contract-drift",
            ),
            (
                "select",
                "--request-claim",
                "direct-request",
                "--primary-signal",
                "hidden-seam",
                "--primary-signal",
                "dominant-blocker",
            ),
            (
                "select",
                "--request-claim",
                "direct-request",
                "--primary-signal",
                "hidden-seam",
                "--evidence",
                "operation-status-active",
            ),
            (
                "select",
                "--request",
                "direct-request",
                "--primary-signal",
                "hidden-seam",
            ),
            (
                "select",
                "--source",
                "direct-request",
                "--primary-signal",
                "hidden-seam",
            ),
            ("verify", "--input", ""),
            (
                "verify",
                "--input",
                "-",
                "--evidence",
                "darwin-browser-broker-preview",
            ),
        ]
        for arguments in cases:
            with self.subTest(arguments=arguments):
                result = run_script(*arguments)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b"")

    def test_output_has_no_activation_command_rank_or_private_surface(self) -> None:
        card_result = select(
            "unknown-dependencies",
            "verification-debt",
            evidence=True,
        )
        card = payload(card_result)
        text = card_result.stdout.decode("utf-8")
        self.assertNotIn("/Users/", text)
        self.assertNotIn("file://", text)
        self.assertNotIn("http://", text)
        self.assertNotIn("https://", text)
        self.assertNotIn("$nen-", text)
        forbidden = {
            "command",
            "commands",
            "confidence",
            "executable",
            "level",
            "mastery",
            "rank",
            "rating",
            "reputation",
            "score",
            "tier",
            "xp",
        }
        self.assertTrue(all_keys(card).isdisjoint(forbidden))


class DarwinEvidenceTest(unittest.TestCase):
    def test_evidence_is_explicit_preview_only(self) -> None:
        without = payload(select("unknown-dependencies"))
        self.assertIsNone(without["frontier_evidence"])

        with_evidence = payload(select("unknown-dependencies", evidence=True))
        frontier = with_evidence["frontier_evidence"]
        self.assertEqual(frontier["id"], "darwin-browser-broker-preview")
        self.assertEqual(frontier["state_at_observation"], "draft-review")
        self.assertEqual(frontier["browser_release"], "0.5.1")
        self.assertIs(frontier["broker_in_browser_release"], False)
        self.assertIs(frontier["manual_opt_in"], True)
        self.assertIs(frontier["public_authority_only"], True)
        self.assertIs(frontier["ephemeral_only"], True)
        self.assertIs(frontier["same_uid_mode_bounded"], True)
        self.assertIs(frontier["native_peer_attestation"], False)
        self.assertIs(frontier["direct_mcp_rollback"], True)
        self.assertIs(frontier["measurement_is_guarantee"], False)
        self.assertIs(frontier["unpaid_release_debt"], True)
        self.assertEqual(
            frontier["source_files_sha256"],
            {
                "packages/browser/src/mcp-broker.ts": "1893d1bab943c3440d83558028acf2ab20f20748024ab548e0d4a11066022c6c",
                "packages/browser/src/mcp-proxy.ts": "258286da53de603f8e84bca4f15c28cdc5b2b703ebb20ed6f017bb88bd6fed42",
            },
        )

    def test_dangerous_evidence_state_is_rejected(self) -> None:
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        for field in (
            "broker_in_browser_release",
            "broker_preview_merged",
            "broker_preview_released",
            "broker_preview_installed",
        ):
            changed = copy.deepcopy(evidence)
            changed["source"][field] = True
            with self.subTest(field=field), self.assertRaises(
                RUNTIME.InterpretationError
            ):
                RUNTIME.validate_evidence(changed)
        for field in ("acl_inspected", "native_peer_attestation", "peer_verified"):
            changed = copy.deepcopy(evidence)
            changed["authority"][field] = True
            with self.subTest(field=field), self.assertRaises(
                RUNTIME.InterpretationError
            ):
                RUNTIME.validate_evidence(changed)


class VerificationTest(unittest.TestCase):
    def test_card_round_trip_and_tamper_refusal(self) -> None:
        valid = select("hidden-seam", "verification-debt", evidence=True)
        self.assertEqual(valid.returncode, 0)
        verified = run_script(
            "verify",
            "--input",
            "-",
            "--evidence",
            "darwin-browser-broker-preview",
            stdin=valid.stdout,
        )
        receipt = payload(verified)
        card = json.loads(valid.stdout)
        self.assertEqual(receipt["id"], card["id"])
        self.assertIs(receipt["capability_execution"], False)
        self.assertIs(receipt["writes_files"], False)

        changed = copy.deepcopy(card)
        changed["primary"]["skill"] = "nen-vow-forge"
        tampered = RUNTIME.canonical_json(changed)
        refused = run_script(
            "verify",
            "--input",
            "-",
            "--evidence",
            "darwin-browser-broker-preview",
            stdin=tampered,
        )
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual(refused.stdout, b"")

        malformed = copy.deepcopy(card)
        malformed["primary"]["signal"] = []
        refused = run_script(
            "verify",
            "--input",
            "-",
            "--evidence",
            "darwin-browser-broker-preview",
            stdin=RUNTIME.canonical_json(malformed),
        )
        self.assertEqual(refused.returncode, 2)
        self.assertEqual(refused.stdout, b"")
        self.assertNotIn(b"Traceback", refused.stderr)

        nonfinite = valid.stdout.replace(
            b'"bookmark":',
            b'"unexpected":NaN,"bookmark":',
            1,
        )
        refused = run_script("verify", "--input", "-", stdin=nonfinite)
        self.assertEqual(refused.returncode, 2)
        self.assertEqual(refused.stdout, b"")
        self.assertIn(b"non-finite JSON number", refused.stderr)

    def test_saved_darwin_card_requires_repeated_explicit_evidence_gate(self) -> None:
        valid = select("unknown-dependencies", evidence=True)
        refused = run_script("verify", "--input", "-", stdin=valid.stdout)
        self.assertEqual(refused.returncode, 2)
        self.assertEqual(refused.stdout, b"")
        self.assertIn(b"explicit evidence flag", refused.stderr)

        verified = run_script(
            "verify",
            "--input",
            "-",
            "--evidence",
            "darwin-browser-broker-preview",
            stdin=valid.stdout,
        )
        self.assertEqual(verified.returncode, 0)
        self.assertIs(payload(verified)["capability_execution"], False)

        plain = select("unknown-dependencies")
        refused = run_script(
            "verify",
            "--input",
            "-",
            "--evidence",
            "darwin-browser-broker-preview",
            stdin=plain.stdout,
        )
        self.assertEqual(refused.returncode, 2)
        self.assertEqual(refused.stdout, b"")

    def test_returned_card_does_not_alias_runtime_contract(self) -> None:
        abilities, _ = RUNTIME.load_core_sources()
        card = RUNTIME.interpretation(
            abilities,
            None,
            "hidden-seam",
            None,
            None,
        )
        card["contract"]["activates_skill"] = True
        card["request_provenance"]["attested"] = True
        card["dark_continent"]["principles"].append("ambient-authority")
        card["non_claims"].clear()

        self.assertIs(RUNTIME.CONTRACT["activates_skill"], False)
        self.assertIs(RUNTIME.REQUEST_PROVENANCE["attested"], False)
        self.assertEqual(
            RUNTIME.DARK_CONTINENT["principles"],
            ["light", "truth", "consent", "no conquest"],
        )
        self.assertEqual(len(RUNTIME.NON_CLAIMS), 5)

    def test_schema_constants_are_type_strict(self) -> None:
        card = payload(select("hidden-seam", evidence=True))
        cases = []

        changed = copy.deepcopy(card)
        changed["contract"]["activates_skill"] = 0
        cases.append(changed)

        changed = copy.deepcopy(card)
        changed["request_provenance"]["attested"] = 0
        cases.append(changed)

        changed = copy.deepcopy(card)
        changed["frontier_evidence"]["manual_opt_in"] = 1
        cases.append(changed)

        for changed in cases:
            with self.subTest(changed=changed):
                refused = run_script(
                    "verify",
                    "--input",
                    "-",
                    "--evidence",
                    "darwin-browser-broker-preview",
                    stdin=rebind(changed),
                )
                self.assertEqual(refused.returncode, 2)
                self.assertEqual(refused.stdout, b"")

    def test_noncanonical_duplicate_oversized_and_symlink_inputs_refuse(self) -> None:
        valid = select("contract-drift")
        malformed_inputs = [
            valid.stdout.rstrip(b"\n") + b" \n",
            b'{"schema":"shadow",' + valid.stdout[1:],
            b"x" * (RUNTIME.MAX_REFERENCE_BYTES + 1),
        ]
        for raw in malformed_inputs:
            with self.subTest(size=len(raw)):
                refused = run_script("verify", "--input", "-", stdin=raw)
                self.assertEqual(refused.returncode, 2)
                self.assertEqual(refused.stdout, b"")

        with tempfile.TemporaryDirectory(prefix="kingdom-nen-symlink-") as directory:
            target = Path(directory) / "card.json"
            link = Path(directory) / "card-link.json"
            target.write_bytes(valid.stdout)
            link.symlink_to(target)
            refused = run_script("verify", "--input", str(link))
        self.assertEqual(refused.returncode, 2)
        self.assertEqual(refused.stdout, b"")

    def test_runtime_import_surface_is_stdlib_read_only(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", 1)[0])
        self.assertTrue(
            imports.isdisjoint(
                {
                    "http",
                    "importlib",
                    "requests",
                    "socket",
                    "subprocess",
                    "urllib",
                }
            )
        )
        for token in (
            "write_text(",
            "write_bytes(",
            "mkdir(",
            "unlink(",
            "replace(",
            "Popen(",
            "run(",
        ):
            self.assertNotIn(token, source)

    def test_sidecar_is_explicit_only_and_dependency_free(self) -> None:
        sidecar = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn('display_name: "Nen Mission Interpreter"', sidecar)
        self.assertIn("$interpret-dark-continent-nen", sidecar)
        self.assertIn("allow_implicit_invocation: false", sidecar)
        self.assertNotIn("dependencies:", sidecar)

    def test_kingdom_dispatcher_is_stdout_only(self) -> None:
        result = subprocess.run(
            [
                str(KINGDOM),
                "nen",
                "interpret",
                "select",
                "--request-claim",
                "direct-request",
                "--primary-signal",
                "unknown-dependencies",
            ],
            cwd=ROOT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        card = payload(result)
        self.assertEqual(card["primary"]["skill"], "nen-dependency-perimeter")
        self.assertIs(card["contract"]["writes_files"], False)

    def test_saved_file_verification_emits_no_path(self) -> None:
        card = select("contract-drift")
        with tempfile.TemporaryDirectory(prefix="kingdom-nen-test-") as directory:
            path = Path(directory) / "card.json"
            path.write_bytes(card.stdout)
            result = run_script("verify", "--input", str(path))
        receipt = payload(result)
        self.assertNotIn(str(path), result.stdout.decode("utf-8"))
        self.assertEqual(receipt["schema"], "kingdom.nen-interpretation-verification/v1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
