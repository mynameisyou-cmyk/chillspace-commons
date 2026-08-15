#!/usr/bin/env python3
"""Acceptance tests for the deterministic, offline Incident Lantern engine."""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urljoin


sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ENGINE_PATH = HERE / "incident_lantern.py"
INCIDENT_SCHEMA_PATH = HERE / "incident.schema.json"
CANDIDATE_SCHEMA_PATH = HERE / "regression-candidate.schema.json"
GOLDEN_SOURCE_PATH = HERE / "examples" / "resource-pressure.source.json"
GOLDEN_INCIDENT_PATH = HERE / "examples" / "resource-pressure.incident.json"
PYTHON311 = Path("/Users/yuai/.local/bin/python3.11")

SPEC = importlib.util.spec_from_file_location("incident_lantern_under_test", ENGINE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load Incident Lantern engine")
LANTERN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LANTERN)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: thaw(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [thaw(child) for child in value]
    return value


def reverse_objects(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: reverse_objects(value[key])
            for key in reversed(list(value))
        }
    if isinstance(value, list):
        return [reverse_objects(child) for child in value]
    return value


def run_engine(
    arguments: tuple[str, ...] | list[str],
    payload: bytes = b"",
    *,
    cwd: Path | None = None,
    environment: dict[str, str] | None = None,
    interpreter: Path | str | None = None,
) -> subprocess.CompletedProcess[bytes]:
    env = dict(os.environ) if environment is None else dict(environment)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [str(interpreter or sys.executable), "-I", "-B", str(ENGINE_PATH), *arguments],
        input=payload,
        cwd=str(cwd or REPO),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
        check=False,
    )


def tree_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or not path.is_file():
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _json_equal(left: Any, right: Any) -> bool:
    try:
        return canonical_bytes(left) == canonical_bytes(right)
    except (TypeError, ValueError):
        return False


def schema_accepts(
    value: Any,
    schema: dict[str, Any],
    root: dict[str, Any],
    documents: dict[str, dict[str, Any]],
) -> bool:
    """Validate the closed schema subset used by this leaf without dependencies."""

    reference = schema.get("$ref")
    if reference is not None:
        if not isinstance(reference, str):
            return False
        if reference.startswith("#/"):
            target: Any = root
            for encoded in reference[2:].split("/"):
                key = encoded.replace("~1", "/").replace("~0", "~")
                if not isinstance(target, dict) or key not in target:
                    return False
                target = target[key]
            if not isinstance(target, dict):
                return False
            if not schema_accepts(value, target, root, documents):
                return False
        else:
            target_root = documents.get(reference)
            if target_root is None or not schema_accepts(
                value, target_root, target_root, documents
            ):
                return False

    if "allOf" in schema:
        branches = schema["allOf"]
        if not isinstance(branches, list) or not all(
            isinstance(branch, dict)
            and schema_accepts(value, branch, root, documents)
            for branch in branches
        ):
            return False

    if "const" in schema and not _json_equal(value, schema["const"]):
        return False
    if "enum" in schema:
        choices = schema["enum"]
        if not isinstance(choices, list) or not any(
            _json_equal(value, choice) for choice in choices
        ):
            return False

    expected_type = schema.get("type")
    if expected_type == "object" and not isinstance(value, dict):
        return False
    if expected_type == "array" and not isinstance(value, list):
        return False
    if expected_type == "string" and not isinstance(value, str):
        return False
    if expected_type == "integer" and type(value) is not int:
        return False
    if expected_type == "boolean" and type(value) is not bool:
        return False
    if expected_type == "null" and value is not None:
        return False

    if isinstance(value, dict) and any(
        key in schema for key in ("required", "properties", "additionalProperties")
    ):
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        if not isinstance(required, list) or not isinstance(properties, dict):
            return False
        if not set(required) <= set(value):
            return False
        if schema.get("additionalProperties") is False and not set(value) <= set(properties):
            return False
        for key, child in value.items():
            child_schema = properties.get(key)
            if child_schema is not None and (
                not isinstance(child_schema, dict)
                or not schema_accepts(child, child_schema, root, documents)
            ):
                return False

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            return False
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            return False
        prefix = schema.get("prefixItems", [])
        if not isinstance(prefix, list):
            return False
        for index, child_schema in enumerate(prefix):
            if index >= len(value):
                break
            if not isinstance(child_schema, dict) or not schema_accepts(
                value[index], child_schema, root, documents
            ):
                return False
        items = schema.get("items")
        remainder = value[len(prefix):] if prefix else value
        if items is False and remainder:
            return False
        if isinstance(items, dict) and not all(
            schema_accepts(child, items, root, documents) for child in remainder
        ):
            return False
        if schema.get("uniqueItems") is True:
            encoded = [canonical_bytes(child) for child in value]
            if len(encoded) != len(set(encoded)):
                return False

    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            return False
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            return False
        pattern = schema.get("pattern")
        if pattern is not None and (
            not isinstance(pattern, str) or re.search(pattern, value) is None
        ):
            return False

    if type(value) is int:
        if "minimum" in schema and value < schema["minimum"]:
            return False
        if "maximum" in schema and value > schema["maximum"]:
            return False
    return True


def assert_recursively_closed(test: unittest.TestCase, schema: Any, path: str = "$") -> None:
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            test.assertIs(schema.get("additionalProperties"), False, path)
            test.assertEqual(
                set(schema.get("required", [])),
                set(schema.get("properties", {})),
                path,
            )
        for key, child in schema.items():
            assert_recursively_closed(test, child, path + "." + key)
    elif isinstance(schema, list):
        for index, child in enumerate(schema):
            assert_recursively_closed(test, child, f"{path}[{index}]")


class IncidentLanternTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = LANTERN.load_contract()
        cls.incident_schema = json.loads(INCIDENT_SCHEMA_PATH.read_bytes())
        cls.candidate_schema = json.loads(CANDIDATE_SCHEMA_PATH.read_bytes())
        cls.schema_documents = {
            "incident.schema.json": cls.incident_schema,
            "regression-candidate.schema.json": cls.candidate_schema,
        }
        cases = {
            case["rule_id"]: case
            for case in (
                thaw(raw) for raw in cls.contract["bundle"]["corpus"]["cases"]
            )
        }
        cls.planned_event = copy.deepcopy(cases["authority-laundering"]["event"])
        cls.planned_receipt = LANTERN.future.plan_event(
            cls.planned_event, cls.contract["bundle"]
        )
        cls.planned_source = {
            "schema": LANTERN.SOURCE_SCHEMA,
            "event": copy.deepcopy(cls.planned_event),
            "receipt": copy.deepcopy(cls.planned_receipt),
        }
        cls.private_marker = "private-marker-do-not-echo"
        cls.halted_event = copy.deepcopy(cls.planned_event)
        cls.halted_event["mechanism"] = cls.private_marker
        cls.halted_receipt = LANTERN.future.plan_event(
            cls.halted_event, cls.contract["bundle"]
        )
        cls.halted_source = {
            "schema": LANTERN.SOURCE_SCHEMA,
            "event": copy.deepcopy(cls.halted_event),
            "receipt": copy.deepcopy(cls.halted_receipt),
        }
        cls.planned_candidate = LANTERN.candidate_value(
            copy.deepcopy(cls.planned_source), cls.contract
        )
        cls.halted_candidate = LANTERN.candidate_value(
            copy.deepcopy(cls.halted_source), cls.contract
        )
        cls.planned_incident = LANTERN.incident_value(
            copy.deepcopy(cls.planned_source), cls.contract
        )
        cls.halted_incident = LANTERN.incident_value(
            copy.deepcopy(cls.halted_source), cls.contract
        )

    def assert_schema_accepts(self, value: Any, schema: dict[str, Any]) -> None:
        self.assertTrue(
            schema_accepts(value, schema, schema, self.schema_documents),
            canonical_bytes(value)[:500],
        )

    def assert_fixed_rejection(self, result: subprocess.CompletedProcess[bytes]) -> None:
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(result.stderr, b"incident-lantern: rejected\n")

    def test_planned_and_valid_halted_receipts_freshly_replay(self) -> None:
        planned = copy.deepcopy(self.planned_incident)
        halted = copy.deepcopy(self.halted_incident)
        self.assertEqual(self.planned_receipt["status"], "planned")
        self.assertEqual(self.halted_receipt["status"], "halted")
        self.assertEqual(planned["status"], "ready-for-review")
        self.assertEqual(planned["source"]["source_status"], "planned")
        self.assertEqual(planned["headline"]["disposition"], "reviewed-plan")
        self.assertEqual(halted["status"], "halted-for-review")
        self.assertEqual(halted["source"]["source_status"], "halted")
        self.assertEqual(halted["headline"]["disposition"], "boundary-halt")
        self.assertEqual(halted["headline"]["planned_action"], "quarantine")
        self.assertEqual(
            halted["learning"]["regression_candidate"]["event"],
            LANTERN.WITHHELD_EVENT,
        )
        self.assertNotIn(self.private_marker.encode("ascii"), canonical_bytes(halted))
        self.assert_schema_accepts(planned, self.incident_schema)
        self.assert_schema_accepts(halted, self.incident_schema)
        self.assert_schema_accepts(self.planned_candidate, self.candidate_schema)
        self.assert_schema_accepts(self.halted_candidate, self.candidate_schema)
        self.assertEqual(
            LANTERN.validate_incident(planned, self.contract), planned
        )
        self.assertEqual(
            LANTERN.validate_incident(halted, self.contract), halted
        )

    def test_supplied_receipt_tamper_and_redigest_are_rejected(self) -> None:
        tampered_receipt = copy.deepcopy(self.planned_receipt)
        tampered_receipt["decision"]["action"] = "allow"
        tampered_receipt["receipt_digest"] = digest_value(
            {
                key: value
                for key, value in tampered_receipt.items()
                if key != "receipt_digest"
            }
        )
        tampered_source = copy.deepcopy(self.planned_source)
        tampered_source["receipt"] = tampered_receipt
        with self.assertRaises(LANTERN.LanternError):
            LANTERN.incident_value(tampered_source, self.contract)
        with self.assertRaises(LANTERN.LanternError):
            LANTERN.candidate_value(tampered_source, self.contract)
        for command in ("build", "candidate"):
            result = run_engine((command,), canonical_bytes(tampered_source))
            self.assert_fixed_rejection(result)

        changed_event = copy.deepcopy(self.planned_source)
        changed_event["event"]["signal"] = "changed-categorical-signal"
        with self.assertRaises(LANTERN.LanternError):
            LANTERN.incident_value(changed_event, self.contract)

        tampered_incident = copy.deepcopy(self.planned_incident)
        tampered_incident["headline"]["severity"] = 0
        tampered_incident["incident_digest"] = digest_value(
            {
                key: value
                for key, value in tampered_incident.items()
                if key != "incident_digest"
            }
        )
        verify_wrapper = {
            "schema": LANTERN.VERIFY_SCHEMA,
            "source": copy.deepcopy(self.planned_source),
            "incident": tampered_incident,
        }
        with self.assertRaises(LANTERN.LanternError):
            LANTERN.verify_value(verify_wrapper, self.contract)
        self.assert_fixed_rejection(
            run_engine(("verify",), canonical_bytes(verify_wrapper))
        )

    def test_privacy_nonreflection_and_input_free_diagnostics(self) -> None:
        marker_event = copy.deepcopy(self.planned_event)
        markers = (
            "private-surface-do-not-echo",
            "private-mechanism-do-not-echo",
            "private-signal-do-not-echo",
        )
        marker_event["surface"], marker_event["mechanism"], marker_event["signal"] = markers
        marker_receipt = LANTERN.future.plan_event(
            marker_event, self.contract["bundle"]
        )
        source = {
            "schema": LANTERN.SOURCE_SCHEMA,
            "event": marker_event,
            "receipt": marker_receipt,
        }
        incident = LANTERN.incident_value(source, self.contract)
        candidate = LANTERN.candidate_value(source, self.contract)
        rendered = canonical_bytes(incident) + canonical_bytes(candidate)
        for marker in markers:
            self.assertNotIn(marker.encode("ascii"), rendered)
        self.assertEqual(candidate["event"], LANTERN.WITHHELD_EVENT)

        environment = dict(os.environ)
        environment_marker = "LANTERN_ENVIRONMENT_MARKER_7f3d"
        environment["INCIDENT_LANTERN_PRIVATE_MARKER"] = environment_marker
        cli = run_engine(
            ("build",), canonical_bytes(source), environment=environment
        )
        self.assertEqual(cli.returncode, 0, cli.stderr)
        self.assertNotIn(environment_marker.encode("ascii"), cli.stdout + cli.stderr)
        for marker in markers:
            self.assertNotIn(marker.encode("ascii"), cli.stdout + cli.stderr)

        rejected_values = (
            "<script>private-marker</script>",
            "person@example.invalid",
            "https://private.invalid/path",
            "../private/path",
        )
        for submitted in rejected_values:
            bad = copy.deepcopy(self.planned_source)
            bad["event"]["signal"] = submitted
            result = run_engine(("build",), canonical_bytes(bad))
            self.assert_fixed_rejection(result)
            self.assertNotIn(submitted.encode("ascii"), result.stdout + result.stderr)

        raw_wrapper = copy.deepcopy(self.planned_source)
        raw_wrapper["payload"] = "raw-private-input-do-not-echo"
        result = run_engine(("candidate",), canonical_bytes(raw_wrapper))
        self.assert_fixed_rejection(result)
        self.assertNotIn(b"raw-private-input", result.stdout + result.stderr)

    def test_schemas_are_closed_pinned_and_enforced(self) -> None:
        self.assertEqual(self.incident_schema["$id"], LANTERN.INCIDENT_SCHEMA_ID)
        self.assertEqual(self.candidate_schema["$id"], LANTERN.CANDIDATE_SCHEMA_ID)
        self.assertNotIn("$schema", self.incident_schema)
        self.assertNotIn("$schema", self.candidate_schema)
        assert_recursively_closed(self, self.incident_schema)
        assert_recursively_closed(self, self.candidate_schema)
        for path in (INCIDENT_SCHEMA_PATH, CANDIDATE_SCHEMA_PATH):
            self.assertLessEqual(path.stat().st_size, LANTERN.LIMITS["schema_bytes"])
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                LANTERN.PINS[path.name],
            )
        self.assertEqual(
            self.contract["bindings"]["incident_schema_sha256"],
            LANTERN.PINS["incident.schema.json"],
        )
        self.assertEqual(
            self.contract["bindings"]["candidate_schema_sha256"],
            LANTERN.PINS["regression-candidate.schema.json"],
        )
        incident_base = urljoin(
            INCIDENT_SCHEMA_PATH.resolve().as_uri(), self.incident_schema["$id"]
        )
        candidate_base = urljoin(
            CANDIDATE_SCHEMA_PATH.resolve().as_uri(), self.candidate_schema["$id"]
        )
        candidate_ref = self.incident_schema["$defs"]["learning"]["properties"][
            "regression_candidate"
        ]["$ref"]
        self.assertEqual(urljoin(incident_base, candidate_ref), candidate_base)
        self.assert_schema_accepts(self.planned_incident, self.incident_schema)

        extra = copy.deepcopy(self.planned_candidate)
        extra["surprise"] = "not-closed"
        self.assertFalse(
            schema_accepts(
                extra,
                self.candidate_schema,
                self.candidate_schema,
                self.schema_documents,
            )
        )
        with self.assertRaises(LANTERN.LanternError):
            LANTERN.validate_candidate(extra, self.contract)

        boolean_integer = copy.deepcopy(self.planned_candidate)
        boolean_integer["expected"]["severity"] = True
        boolean_integer["candidate_digest"] = digest_value(
            {
                key: value
                for key, value in boolean_integer.items()
                if key != "candidate_digest"
            }
        )
        self.assertFalse(
            schema_accepts(
                boolean_integer,
                self.candidate_schema,
                self.candidate_schema,
                self.schema_documents,
            )
        )
        with self.assertRaises(LANTERN.LanternError):
            LANTERN.validate_candidate(boolean_integer, self.contract)

        missing = copy.deepcopy(self.planned_incident)
        del missing["actions"][0]["rollback"]
        self.assertFalse(
            schema_accepts(
                missing,
                self.incident_schema,
                self.incident_schema,
                self.schema_documents,
            )
        )
        with self.assertRaises(LANTERN.LanternError):
            LANTERN.validate_incident(missing, self.contract)

    def test_candidate_and_incident_digests_bind_semantics(self) -> None:
        candidate = copy.deepcopy(self.planned_candidate)
        incident = copy.deepcopy(self.planned_incident)
        candidate_unsigned = {
            key: value for key, value in candidate.items() if key != "candidate_digest"
        }
        incident_unsigned = {
            key: value for key, value in incident.items() if key != "incident_digest"
        }
        self.assertEqual(candidate["candidate_digest"], digest_value(candidate_unsigned))
        self.assertEqual(incident["incident_digest"], digest_value(incident_unsigned))
        self.assertEqual(candidate["source"]["event_digest"], digest_value(self.planned_event))
        self.assertEqual(
            candidate["source"]["receipt_digest"], self.planned_receipt["receipt_digest"]
        )
        receipt_unsigned = {
            key: value
            for key, value in self.planned_receipt.items()
            if key != "receipt_digest"
        }
        self.assertEqual(self.planned_receipt["receipt_digest"], digest_value(receipt_unsigned))
        identifier_basis = {
            "event_digest": candidate["source"]["event_digest"],
            "receipt_digest": candidate["source"]["receipt_digest"],
        }
        self.assertEqual(
            candidate["candidate_id"], "candidate-" + digest_value(identifier_basis)[:16]
        )
        self.assertEqual(
            incident["incident_id"], "incident-" + digest_value(identifier_basis)[:16]
        )
        self.assertEqual(
            incident["source"]["bindings"]["incident_engine_sha256"],
            hashlib.sha256(ENGINE_PATH.read_bytes()).hexdigest(),
        )

        poisoned = copy.deepcopy(candidate)
        poisoned["expected"]["action"] = "allow"
        poisoned["candidate_digest"] = digest_value(
            {key: value for key, value in poisoned.items() if key != "candidate_digest"}
        )
        with self.assertRaises(LANTERN.LanternError):
            LANTERN.validate_candidate(poisoned, self.contract)

        for boolean_field in ("automatic_install", "classifier_mutated"):
            confused = copy.deepcopy(candidate)
            confused["promotion"][boolean_field] = 0
            confused["candidate_digest"] = digest_value(
                {
                    key: value
                    for key, value in confused.items()
                    if key != "candidate_digest"
                }
            )
            with self.assertRaises(LANTERN.LanternError):
                LANTERN.validate_candidate(confused, self.contract)

        mutable = LANTERN.candidate_value(copy.deepcopy(self.planned_source), self.contract)
        mutable["promotion"]["classifier_mutated"] = True
        mutable["source"]["bindings"]["policy_sha256"] = "0" * 64
        fresh = LANTERN.candidate_value(copy.deepcopy(self.planned_source), self.contract)
        self.assertEqual(fresh, self.planned_candidate)

    def test_actions_controls_and_epistemics_are_proposal_only(self) -> None:
        for incident in (self.planned_incident, self.halted_incident):
            self.assertEqual(incident["controls"], LANTERN.ZERO_CONTROLS)
            for key in (
                "network_calls", "process_spawns", "model_calls", "secret_reads",
                "filesystem_writes", "external_messages", "engine_retained_records",
            ):
                self.assertIs(type(incident["controls"][key]), int)
                self.assertEqual(incident["controls"][key], 0)
            for key in ("authority_granted", "action_executed", "classifier_mutated"):
                self.assertIs(incident["controls"][key], False)
            actions = incident["actions"]
            self.assertEqual(len(actions), 3)
            self.assertEqual(
                [(item["rank"], item["kind"]) for item in actions],
                [(1, "primary"), (2, "fallback"), (3, "verification")],
            )
            for action in actions:
                self.assertEqual(action["authority"], "human-required")
                self.assertIs(action["automatic"], False)
                self.assertEqual(action["actual_effect"], "none")
                self.assertEqual(action["state"], "not-executed")
                self.assertTrue(action["preconditions"])
                self.assertTrue(action["rollback"])
                self.assertTrue(action["verification"])
            epistemics = incident["epistemics"]
            self.assertEqual(len(epistemics["facts"]), 4)
            self.assertEqual(len(epistemics["inferences"]), 2)
            self.assertGreaterEqual(len(epistemics["unknowns"]), 4)
            self.assertLessEqual(len(epistemics["unknowns"]), 7)
            self.assertTrue(all(item["confidence"] == "confirmed" for item in epistemics["facts"]))
            self.assertTrue(all(item["confidence"] == "policy-derived" for item in epistemics["inferences"]))
            self.assertTrue(all(item["confidence"] == "unknown" for item in epistemics["unknowns"]))
            self.assertTrue(all(item["refs"] for group in epistemics.values() for item in group))
            candidate = incident["learning"]["regression_candidate"]
            self.assertEqual(candidate["promotion"]["state"], "human-review-required")
            self.assertIs(candidate["promotion"]["automatic_install"], False)
            self.assertIs(candidate["promotion"]["classifier_mutated"], False)
            self.assertEqual(candidate["promotion"]["authority"], "none")

        self.assertEqual(len(self.planned_incident["epistemics"]["unknowns"]), 6)
        self.assertEqual(len(self.halted_incident["epistemics"]["unknowns"]), 7)
        self.assertEqual(
            [item["phase"] for item in self.planned_incident["timeline"]],
            [
                "categorical-observation",
                "source-bindings-validated",
                "receipt-replayed",
                "policy-decision-produced",
                "human-review-pending",
            ],
        )
        self.assertEqual(self.halted_incident["timeline"][3]["state"], "halted")
        self.assertEqual(self.halted_incident["timeline"][4]["state"], "pending")

    def test_cli_round_trip_verification_and_failure_semantics(self) -> None:
        checked = run_engine(("check",))
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(checked.stdout, b"incident-lantern: ok\n")
        self.assertEqual(checked.stderr, b"")

        bindings = run_engine(("digest",))
        self.assertEqual(bindings.returncode, 0, bindings.stderr)
        digest_document = json.loads(bindings.stdout)
        self.assertEqual(digest_document["schema"], "kingdom.incident-bindings/v1")
        self.assertEqual(digest_document["bindings"], self.contract["bindings"])
        self.assertEqual(bindings.stdout, canonical_bytes(digest_document) + b"\n")

        source_payload = canonical_bytes(self.planned_source)
        built = run_engine(("build",), source_payload)
        candidate = run_engine(("candidate",), source_payload)
        self.assertEqual(built.returncode, 0, built.stderr)
        self.assertEqual(candidate.returncode, 0, candidate.stderr)
        self.assertEqual(built.stdout, canonical_bytes(self.planned_incident) + b"\n")
        self.assertEqual(candidate.stdout, canonical_bytes(self.planned_candidate) + b"\n")

        verification = {
            "schema": LANTERN.VERIFY_SCHEMA,
            "source": copy.deepcopy(self.planned_source),
            "incident": copy.deepcopy(self.planned_incident),
        }
        verified = run_engine(("verify",), canonical_bytes(verification))
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertEqual(verified.stdout, b"true\n")
        self.assertEqual(verified.stderr, b"")

        halted = run_engine(("build",), canonical_bytes(self.halted_source))
        self.assertEqual(halted.returncode, 0, halted.stderr)
        self.assertEqual(json.loads(halted.stdout)["status"], "halted-for-review")

        for arguments, payload in (
            ((), b""),
            (("unknown",), b""),
            (("check", "extra"), b""),
            (("build",), b'{"schema":'),
        ):
            self.assert_fixed_rejection(run_engine(arguments, payload))

    def test_bounded_input_and_atomic_rejection(self) -> None:
        source = canonical_bytes(self.planned_source)
        self.assertLess(len(source), LANTERN.LIMITS["source_bytes"])
        exact = source + b" " * (LANTERN.LIMITS["source_bytes"] - len(source))
        accepted = run_engine(("build",), exact)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertEqual(accepted.stdout, canonical_bytes(self.planned_incident) + b"\n")
        self.assert_fixed_rejection(run_engine(("build",), exact + b" "))
        self.assert_fixed_rejection(run_engine(("build",), b""))

        duplicate = source.replace(
            b'{"event":',
            b'{"schema":"kingdom.incident-source/v1","event":',
            1,
        )
        self.assert_fixed_rejection(run_engine(("build",), duplicate))

        for invalid_count in (True, 1.5):
            malformed = copy.deepcopy(self.planned_source)
            malformed["event"]["evidence_count"] = invalid_count
            self.assert_fixed_rejection(
                run_engine(("candidate",), canonical_bytes(malformed))
            )

        node_bomb = canonical_bytes({"extra": [0] * (LANTERN.LIMITS["nodes"] + 1)})
        self.assertLess(len(node_bomb), LANTERN.LIMITS["source_bytes"])
        self.assert_fixed_rejection(run_engine(("build",), node_bomb))
        recursion_bomb = b"[" * 1_200 + b"]" * 1_200
        self.assertLess(len(recursion_bomb), LANTERN.LIMITS["source_bytes"])
        interpreters: list[Path | str] = [sys.executable]
        if PYTHON311.is_file():
            interpreters.append(PYTHON311)
        for interpreter in interpreters:
            self.assert_fixed_rejection(
                run_engine(("build",), recursion_bomb, interpreter=interpreter)
            )
        self.assertLessEqual(
            len(canonical_bytes(self.planned_candidate)) + 1,
            LANTERN.LIMITS["candidate_bytes"],
        )
        self.assertLessEqual(
            len(canonical_bytes(self.planned_incident)) + 1,
            LANTERN.LIMITS["incident_bytes"],
        )

    def test_checked_in_rehearsal_golden_is_current(self) -> None:
        source = GOLDEN_SOURCE_PATH.read_bytes()
        golden = GOLDEN_INCIDENT_PATH.read_bytes()
        self.assertEqual(source, canonical_bytes(json.loads(source)) + b"\n")
        self.assertEqual(golden, canonical_bytes(json.loads(golden)) + b"\n")
        built = run_engine(("build",), source)
        self.assertEqual(built.returncode, 0, built.stderr)
        self.assertEqual(built.stderr, b"")
        self.assertEqual(built.stdout, golden)

    def test_determinism_key_order_environment_cwd_and_interpreter(self) -> None:
        normal = canonical_bytes(self.planned_source)
        reordered = json.dumps(
            reverse_objects(self.planned_source),
            ensure_ascii=True,
            indent=2,
        ).encode("ascii")
        environments = []
        for seed, timezone, locale in (
            ("1", "UTC", "C"),
            ("77", "Pacific/Honolulu", "C.UTF-8"),
            ("999", "Europe/London", "en_GB.UTF-8"),
        ):
            environment = dict(os.environ)
            environment.update(
                {"PYTHONHASHSEED": seed, "TZ": timezone, "LANG": locale}
            )
            environments.append(environment)
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            outputs = [
                run_engine(
                    ("build",),
                    normal if index == 0 else reordered,
                    cwd=HERE if index == 0 else temp,
                    environment=environment,
                )
                for index, environment in enumerate(environments)
            ]
        for result in outputs:
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, b"")
        self.assertEqual(outputs[0].stdout, outputs[1].stdout)
        self.assertEqual(outputs[1].stdout, outputs[2].stdout)

        if PYTHON311.is_file():
            current = run_engine(("build",), normal, interpreter=sys.executable)
            older = run_engine(("build",), normal, interpreter=PYTHON311)
            self.assertEqual(current.returncode, 0, current.stderr)
            self.assertEqual(older.returncode, 0, older.stderr)
            self.assertEqual(current.stdout, older.stdout)
            self.assertEqual(current.stderr, older.stderr)

    def test_cli_does_not_mutate_the_source_tree(self) -> None:
        before = tree_fingerprint(HERE)
        built = run_engine(("build",), canonical_bytes(self.planned_source))
        self.assertEqual(built.returncode, 0, built.stderr)
        verify_wrapper = {
            "schema": LANTERN.VERIFY_SCHEMA,
            "source": copy.deepcopy(self.planned_source),
            "incident": copy.deepcopy(self.planned_incident),
        }
        verified = run_engine(("verify",), canonical_bytes(verify_wrapper))
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertEqual(tree_fingerprint(HERE), before)

    def test_ast_and_runtime_effect_boundary(self) -> None:
        source = ENGINE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in (
                node.names
                if isinstance(node, ast.Import)
                else [ast.alias(name=node.module or "")]
            )
        }
        self.assertTrue(
            imports.isdisjoint(
                {
                    "asyncio", "http", "random", "requests", "secrets", "socket",
                    "subprocess", "time", "urllib", "webbrowser",
                }
            )
        )
        for forbidden in (
            "os.environ", "os.getenv", "os.system", "O_WRONLY", "O_RDWR",
            "O_CREAT", "O_TRUNC", "O_APPEND", "write_bytes", "write_text",
            "unlink(", "rename(", "replace(", "mkdir(", "rmdir(",
        ):
            self.assertNotIn(forbidden, source)

        exec_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "exec"
        ]
        self.assertEqual(len(exec_calls), 1)
        compiled = exec_calls[0].args[0]
        self.assertIsInstance(compiled, ast.Call)
        self.assertIsInstance(compiled.func, ast.Name)
        self.assertEqual(compiled.func.id, "compile")
        self.assertIsInstance(compiled.args[0], ast.Name)
        self.assertEqual(compiled.args[0].id, "source")
        self.assertIsInstance(compiled.args[2], ast.Constant)
        self.assertEqual(compiled.args[2].value, "exec")
        self.assertTrue(
            any(
                keyword.arg == "dont_inherit"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
                for keyword in compiled.keywords
            )
        )
        spec_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "spec_from_file_location"
        ]
        self.assertEqual(len(spec_calls), 1)
        self.assertIsInstance(spec_calls[0].args[1], ast.Name)
        self.assertEqual(spec_calls[0].args[1].id, "FUTURE_PATH")
        schema_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_load_schema"
        ]
        self.assertEqual(
            [node.args[0].value for node in schema_calls],
            ["incident.schema.json", "regression-candidate.schema.json"],
        )

        forbidden_events: list[str] = []
        write_opens: list[tuple[object, ...]] = []
        active = {"value": True}
        write_mask = 0
        for name in ("O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC", "O_APPEND"):
            write_mask |= getattr(os, name, 0)

        def audit(event: str, arguments: tuple[object, ...]) -> None:
            if not active["value"]:
                return
            if event == "open":
                mode = arguments[1] if len(arguments) > 1 else None
                flags = arguments[2] if len(arguments) > 2 else 0
                if (
                    isinstance(mode, str) and bool(set(mode) & set("wax+"))
                ) or (
                    isinstance(flags, int) and bool(flags & write_mask)
                ):
                    write_opens.append(arguments)
            elif event.startswith(
                (
                    "socket.", "subprocess.", "os.system", "os.remove", "os.rename",
                    "os.rmdir", "os.mkdir", "os.symlink", "os.link",
                )
            ):
                forbidden_events.append(event)

        sys.addaudithook(audit)
        try:
            incident = LANTERN.incident_value(
                copy.deepcopy(self.planned_source), self.contract
            )
        finally:
            active["value"] = False
        self.assertEqual(forbidden_events, [])
        self.assertEqual(write_opens, [])
        self.assertEqual(incident["controls"], LANTERN.ZERO_CONTROLS)


if __name__ == "__main__":
    unittest.main()
