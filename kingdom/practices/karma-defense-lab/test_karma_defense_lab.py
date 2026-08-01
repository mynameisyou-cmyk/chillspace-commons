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
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


HERE = Path(__file__).resolve().parent
ENGINE_PATH = HERE / "karma_defense_lab.py"

SPEC = importlib.util.spec_from_file_location("karma_defense_lab", ENGINE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load the lab engine")
lab = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lab)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def run_cli(*arguments: str, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-I", "-B", str(ENGINE_PATH), *arguments],
        cwd=cwd or HERE,
        env=env,
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def tree_fingerprint() -> str:
    digest = hashlib.sha256()
    for path in sorted(path for path in HERE.rglob("*") if path.is_file() and "__pycache__" not in path.parts):
        digest.update(path.relative_to(HERE).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


@contextmanager
def budget(name: str, value: int) -> Iterator[None]:
    previous = lab.BUDGETS[name]
    lab.BUDGETS[name] = value
    try:
        yield
    finally:
        lab.BUDGETS[name] = previous


def rebind_scenario(contract: dict[str, Any]) -> None:
    contract["bindings"]["scenario_sha256"] = lab.digest_value(contract["scenario"])


def schema_accepts(value: Any, schema: Any, root: dict[str, Any]) -> bool:
    """Small validator for exactly the checked-in schema keyword subset."""
    if schema is True:
        return True
    if schema is False or not isinstance(schema, dict):
        return False
    if "$ref" in schema:
        reference = schema["$ref"]
        if not isinstance(reference, str) or not reference.startswith("#/"):
            return False
        target: Any = root
        for part in reference[2:].split("/"):
            if not isinstance(target, dict) or part not in target:
                return False
            target = target[part]
        if not schema_accepts(value, target, root):
            return False
    if "allOf" in schema and not all(schema_accepts(value, branch, root) for branch in schema["allOf"]):
        return False
    if "oneOf" in schema and sum(schema_accepts(value, branch, root) for branch in schema["oneOf"]) != 1:
        return False
    if "not" in schema and schema_accepts(value, schema["not"], root):
        return False
    if "if" in schema and schema_accepts(value, schema["if"], root):
        if "then" in schema and not schema_accepts(value, schema["then"], root):
            return False
    if "const" in schema and (type(value) is not type(schema["const"]) or value != schema["const"]):
        return False
    if "enum" in schema and not any(type(value) is type(item) and value == item for item in schema["enum"]):
        return False
    expected_type = schema.get("type")
    type_matches = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }
    if expected_type is not None and not type_matches.get(expected_type, False):
        return False
    if isinstance(value, dict):
        if any(key not in value for key in schema.get("required", [])):
            return False
        if len(value) > schema.get("maxProperties", len(value)):
            return False
        properties = schema.get("properties", {})
        for key, child in value.items():
            if key in properties:
                if not schema_accepts(child, properties[key], root):
                    return False
            elif schema.get("additionalProperties") is False:
                return False
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", len(value)):
            return False
        if schema.get("uniqueItems") and len({canonical_bytes(item) for item in value}) != len(value):
            return False
        prefix = schema.get("prefixItems", [])
        for index, child_schema in enumerate(prefix):
            if index >= len(value) or not schema_accepts(value[index], child_schema, root):
                return False
        items_schema = schema.get("items")
        if items_schema is not None:
            start = len(prefix) if prefix else 0
            for child in value[start:]:
                if not schema_accepts(child, items_schema, root):
                    return False
        if "contains" in schema:
            matches = sum(schema_accepts(child, schema["contains"], root) for child in value)
            if matches < schema.get("minContains", 1) or matches > schema.get("maxContains", len(value)):
                return False
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", len(value)):
            return False
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            return False
    if isinstance(value, int) and not isinstance(value, bool):
        if value < schema.get("minimum", value) or value > schema.get("maximum", value):
            return False
    return True


class KarmaDefenseLabTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.contract = lab.load_contract("traditional-nine")
        self.canary = lab.make_canary(self.contract)

    def test_reviewed_table_has_one_control_nine_fixtures_and_exact_routes(self) -> None:
        stimuli = self.contract["scenario"]["stimuli"]
        self.assertEqual(len(stimuli), 10)
        self.assertEqual(sum(item["truth"] == "negative-control" for item in stimuli), 1)
        self.assertEqual(sum(item["truth"] == "adverse-fixture" for item in stimuli), 9)
        classifications = {item["expected_classification"] for item in stimuli}
        self.assertIn("route-discovery-fanout", classifications)
        self.assertIn("repeated-value-action", classifications)
        self.assertIn("resource-pressure", classifications)
        for stimulus in stimuli:
            with self.subTest(stimulus=stimulus["id"]):
                matches = lab.matching_rules(stimulus, self.contract["rules"])
                reverse_matches = lab.matching_rules(stimulus, list(reversed(self.contract["rules"])))
                self.assertEqual(len(matches), 1)
                self.assertEqual([item["id"] for item in matches], [item["id"] for item in reverse_matches])

    def test_completed_receipt_is_deterministic_minimized_and_rolled_back(self) -> None:
        first = lab.rehearse_value(self.contract, self.canary)
        second = lab.rehearse_value(copy.deepcopy(self.contract), copy.deepcopy(self.canary))
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "completed")
        self.assertEqual(len(first["steps"]), 10)
        self.assertTrue(first["rollback_verified"])
        self.assertEqual(first["restored_world_digest"], first["initial_world_digest"])
        self.assertTrue(all(value == 0 for value in first["effects"].values()))
        self.assertTrue(all(step["match_count"] == 1 and step["synthetic"] is True for step in first["steps"]))
        unsigned = {key: value for key, value in first.items() if key != "receipt_digest"}
        self.assertEqual(first["receipt_digest"], lab.digest_value(unsigned))
        self.assertLessEqual(len(lab.canonical_bytes(first)), lab.BUDGETS["supplied_input_bytes"])
        serialized = lab.canonical_bytes(first).decode()
        for forbidden_key in ('"message"', '"next_affordance"', '"route"', '"predicate"', '"body"', '"payload"'):
            self.assertNotIn(forbidden_key, serialized)
        joined_nonclaims = " ".join(first["nonclaims"]).lower()
        for phrase in ("never an actor", "does not establish intent", "no authority", "not a virtue fruit"):
            self.assertIn(phrase, joined_nonclaims)

    def test_returned_values_cannot_poison_contract_or_future_verification(self) -> None:
        original_binding = self.contract["bindings"]["rules_sha256"]
        first = lab.rehearse_value(self.contract, self.canary)
        first["effects"]["network_calls"] = 1
        first["nonclaims"].append("changed")
        first["bindings"]["rules_sha256"] = "0" * 64

        fresh = lab.rehearse_value(self.contract, self.canary)
        self.assertEqual(fresh["effects"]["network_calls"], 0)
        self.assertEqual(fresh["nonclaims"], lab.NONCLAIMS)
        self.assertEqual(fresh["bindings"]["rules_sha256"], original_binding)
        self.assertEqual(self.contract["bindings"]["rules_sha256"], original_binding)
        with self.assertRaises(lab.LabInputError):
            lab.verify_receipt(self.contract, self.canary, first)

        detached_canary = lab.make_canary(self.contract)
        detached_canary["scope"]["authority"] = "changed"
        detached_canary["bindings"]["rules_sha256"] = "0" * 64
        self.assertEqual(self.contract["scenario"]["scope"]["authority"], "none")
        self.assertEqual(self.contract["bindings"]["rules_sha256"], original_binding)

    def test_rule_order_cannot_change_the_receipt(self) -> None:
        normal = lab.rehearse_value(self.contract, self.canary)
        reversed_result = lab.rehearse_value(
            self.contract,
            self.canary,
            rules_override=list(reversed(self.contract["rules"])),
        )
        self.assertEqual(normal, reversed_result)

    def test_novel_and_ambiguous_stimuli_halt_without_retry(self) -> None:
        novel = copy.deepcopy(self.contract)
        novel["scenario"]["stimuli"][1]["route"] = "/cell/unknown"
        rebind_scenario(novel)
        novel_result = lab.rehearse_value(novel, lab.make_canary(novel))
        self.assertEqual(novel_result["status"], "halted")
        self.assertEqual(novel_result["halt"], {"code": "novel-stimulus", "at_ordinal": 2})
        self.assertEqual(novel_result["effects"]["retries"], 0)
        self.assertTrue(novel_result["rollback_verified"])

        overlapping = copy.deepcopy(self.contract["rules"])
        overlapping.append(copy.deepcopy(overlapping[0]))
        ambiguous_result = lab.rehearse_value(
            self.contract,
            self.canary,
            rules_override=overlapping,
        )
        self.assertEqual(ambiguous_result["status"], "halted")
        self.assertEqual(ambiguous_result["halt"], {"code": "ambiguous-stimulus", "at_ordinal": 1})
        self.assertEqual(ambiguous_result["steps"], [])
        self.assertTrue(ambiguous_result["rollback_verified"])

    def test_expectation_response_and_world_drift_each_halt(self) -> None:
        changed_expectation = copy.deepcopy(self.contract)
        changed_expectation["scenario"]["stimuli"][0]["expected_rule_id"] = "rule-recon"
        rebind_scenario(changed_expectation)
        result = lab.rehearse_value(changed_expectation, lab.make_canary(changed_expectation))
        self.assertEqual(result["halt"]["code"], "expectation-mismatch")

        unsafe_plans = copy.deepcopy(self.contract["plans"])
        unsafe_plans[0]["actual_effect"] = "external"
        result = lab.rehearse_value(self.contract, self.canary, plans_override=unsafe_plans)
        self.assertEqual(result["halt"]["code"], "response-verification-failed")

        invalid_key_plans = copy.deepcopy(self.contract["plans"])
        invalid_key_plans[0]["transition"]["key"] = "INVALID KEY"
        result = lab.rehearse_value(self.contract, self.canary, plans_override=invalid_key_plans)
        self.assertEqual(result["halt"]["code"], "response-verification-failed")
        self.assertTrue(schema_accepts(result, self.contract["receipt_schema"], self.contract["receipt_schema"]))

        drifting_plans = copy.deepcopy(self.contract["plans"])
        drifting_plans[1]["transition"]["key"] = drifting_plans[0]["transition"]["key"]
        result = lab.rehearse_value(self.contract, self.canary, plans_override=drifting_plans)
        self.assertEqual(result["halt"], {"code": "world-state-drift", "at_ordinal": 2})
        self.assertTrue(result["rollback_verified"])

    def test_canary_is_content_bound_and_scope_change_halts(self) -> None:
        unsigned = {key: value for key, value in self.canary.items() if key != "canary_digest"}
        self.assertEqual(self.canary["canary_digest"], lab.digest_value(unsigned))

        corrupt = copy.deepcopy(self.canary)
        corrupt["canary_digest"] = "bad"
        result = lab.rehearse_value(self.contract, corrupt)
        self.assertEqual(result["halt"]["code"], "canary-failed")
        self.assertEqual(result["steps"], [])
        self.assertRegex(result["canary_digest"], r"^[0-9a-f]{64}$")
        self.assertTrue(schema_accepts(result, self.contract["receipt_schema"], self.contract["receipt_schema"]))

        changed_scope = copy.deepcopy(self.canary)
        changed_scope["budgets"]["attempts"] = 2
        changed_scope["canary_digest"] = lab.digest_value(
            {key: value for key, value in changed_scope.items() if key != "canary_digest"}
        )
        result = lab.rehearse_value(self.contract, changed_scope)
        self.assertEqual(result["halt"]["code"], "authority-or-scope-change")
        self.assertEqual(result["steps"], [])

        boolean_attempt = copy.deepcopy(self.canary)
        boolean_attempt["attempts"] = True
        boolean_attempt["canary_digest"] = lab.digest_value(
            {key: value for key, value in boolean_attempt.items() if key != "canary_digest"}
        )
        result = lab.rehearse_value(self.contract, boolean_attempt)
        self.assertEqual(result["halt"]["code"], "authority-or-scope-change")

    def test_budget_boundaries_are_fail_closed(self) -> None:
        request_total = sum(len(lab.canonical_bytes(item)) for item in self.contract["scenario"]["stimuli"])
        response_total = sum(len(lab.canonical_bytes(item)) for item in self.contract["plans"])
        cost_total = sum(item["transition"]["cost"] for item in self.contract["plans"])
        cases = (
            ("request_bytes_total", request_total),
            ("response_bytes_total", response_total),
            ("mock_cost_units", cost_total),
            ("stimuli", len(self.contract["scenario"]["stimuli"])),
            ("transitions", len(self.contract["scenario"]["stimuli"])),
        )
        for name, exact in cases:
            for delta, expected_status in ((-1, "halted"), (0, "completed"), (1, "completed")):
                with self.subTest(budget=name, delta=delta), budget(name, exact + delta):
                    canary = lab.make_canary(self.contract)
                    result = lab.rehearse_value(self.contract, canary)
                    self.assertEqual(result["status"], expected_status)
                    if expected_status == "halted":
                        self.assertEqual(result["halt"]["code"], "budget-exhausted")
                        self.assertTrue(result["rollback_verified"])

    def test_strict_json_and_input_size_boundaries(self) -> None:
        invalid_documents = (
            b'{"a":1,"a":2}',
            b'{"number":NaN}',
            b'{"number":1.5}',
            b'{"payload":"categorical"}',
            b'{"value":"person@example.invalid"}',
            b'{"value":"https://invalid.invalid"}',
            ('{"value":"' + ("sk" + "_live" + "_example") + '"}').encode(),
        )
        for document in invalid_documents:
            with self.subTest(document=document[:30]):
                with self.assertRaises(lab.LabInputError):
                    lab.decode_json(document, label="test")

        lab.decode_json(canonical_bytes({"value": "a" * lab.BUDGETS["text_codepoints"]}), label="test")
        with self.assertRaises(lab.LabInputError):
            lab.decode_json(canonical_bytes({"value": "a" * (lab.BUDGETS["text_codepoints"] + 1)}), label="test")

        nested: Any = "leaf"
        for _ in range(lab.BUDGETS["json_depth"]):
            nested = [nested]
        with self.assertRaises(lab.LabInputError):
            lab.decode_json(canonical_bytes(nested), label="test")
        with self.assertRaises(lab.LabInputError):
            lab.decode_json((b"[" * 2_000) + b"0" + (b"]" * 2_000), label="test")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            exact = root / "exact.json"
            over = root / "over.json"
            limit = lab.BUDGETS["supplied_input_bytes"]
            exact.write_bytes(b"{}" + b" " * (limit - 2))
            over.write_bytes(b"{}" + b" " * (limit - 1))
            self.assertEqual(lab.read_json_file(exact, limit=limit, label="test"), {})
            with self.assertRaises(lab.LabInputError):
                lab.read_json_file(over, limit=limit, label="test")
            linked = root / "linked.json"
            linked.symlink_to(exact)
            with self.assertRaises(lab.LabInputError):
                lab.read_json_file(linked, limit=limit, label="test")

    def test_boolean_is_never_accepted_as_an_integer(self) -> None:
        plans = copy.deepcopy(self.contract["plans_document"])
        plans["plans"][0]["status"] = True
        with self.assertRaises(lab.LabInputError):
            lab.validate_plans(plans)
        plans = copy.deepcopy(self.contract["plans_document"])
        plans["plans"][0]["transition"]["cost"] = True
        with self.assertRaises(lab.LabInputError):
            lab.validate_plans(plans)

    def test_cli_round_trip_and_tamper_rejection(self) -> None:
        checked = run_cli("check", "traditional-nine")
        self.assertEqual(checked.returncode, 0, checked.stderr.decode())
        self.assertEqual(json.loads(checked.stdout)["status"], "valid")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canary_path = root / "canary.json"
            result_path = root / "result.json"
            canary_process = run_cli("canary", "traditional-nine")
            self.assertEqual(canary_process.returncode, 0, canary_process.stderr.decode())
            canary_path.write_bytes(canary_process.stdout)
            render = run_cli("render", "traditional-nine", str(canary_path))
            self.assertEqual(render.returncode, 0, render.stderr.decode())
            result = json.loads(render.stdout)
            self.assertEqual(result["status"], "completed")
            result_path.write_bytes(render.stdout)
            verified = run_cli("verify-result", "traditional-nine", str(canary_path), str(result_path))
            self.assertEqual(verified.returncode, 0, verified.stderr.decode())
            self.assertEqual(json.loads(verified.stdout)["status"], "verified")

            mutations = (
                ("receipt digest", lambda value: value.__setitem__("receipt_digest", "0" * 64)),
                ("effect counter", lambda value: value["effects"].__setitem__("network_calls", 1)),
                ("boolean as integer", lambda value: value["steps"][0].__setitem__("ordinal", True)),
                ("classification", lambda value: value["steps"][0].__setitem__("classification", "changed")),
                ("binding", lambda value: value["bindings"].__setitem__("rules_sha256", "0" * 64)),
            )
            for label, mutate in mutations:
                with self.subTest(mutation=label):
                    changed = copy.deepcopy(result)
                    mutate(changed)
                    result_path.write_bytes(canonical_bytes(changed))
                    rejected = run_cli("verify-result", "traditional-nine", str(canary_path), str(result_path))
                    self.assertEqual(rejected.returncode, 2)
                    self.assertEqual(rejected.stdout, b"")

    def test_cli_rejects_paths_as_scenario_names_and_unsafe_json_without_echo(self) -> None:
        rejected = run_cli("check", "../traditional-nine")
        self.assertEqual(rejected.returncode, 2)
        self.assertEqual(rejected.stdout, b"")
        with tempfile.TemporaryDirectory() as directory:
            canary_path = Path(directory) / "canary.json"
            canary_path.write_bytes(b'{"value":"do-not-echo@example.invalid"}')
            rejected = run_cli("render", "traditional-nine", str(canary_path))
            self.assertEqual(rejected.returncode, 2)
            self.assertEqual(rejected.stdout, b"")
            self.assertNotIn(b"do-not-echo", rejected.stderr)

    def test_cli_semantic_canary_failure_emits_a_canonical_halt_and_exit_three(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            canary_path = Path(directory) / "canary.json"
            generated = run_cli("canary", "traditional-nine")
            self.assertEqual(generated.returncode, 0, generated.stderr.decode())
            canary = json.loads(generated.stdout)
            canary["canary_digest"] = "bad"
            canary_path.write_bytes(canonical_bytes(canary))
            process = run_cli("render", "traditional-nine", str(canary_path))
            self.assertEqual(process.returncode, 3, process.stderr.decode())
            halted = json.loads(process.stdout)
            self.assertEqual(halted["halt"]["code"], "canary-failed")
            receipt_schema = self.contract["receipt_schema"]
            self.assertTrue(schema_accepts(halted, receipt_schema, receipt_schema))

    def test_fresh_process_replay_ignores_environment_cwd_and_key_order(self) -> None:
        base_env = dict(os.environ)
        env_a = {**base_env, "PYTHONHASHSEED": "1", "TZ": "UTC", "LANG": "C"}
        env_b = {**base_env, "PYTHONHASHSEED": "987654", "TZ": "Pacific/Honolulu", "LANG": "C.UTF-8"}
        first_canary = run_cli("canary", "traditional-nine", cwd=HERE, env=env_a)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            second_canary = run_cli("canary", "traditional-nine", cwd=root, env=env_b)
            self.assertEqual(first_canary.returncode, 0, first_canary.stderr.decode())
            self.assertEqual(first_canary.stdout, second_canary.stdout)
            parsed = json.loads(first_canary.stdout)
            reversed_canary = {key: parsed[key] for key in reversed(list(parsed))}
            first_path = root / "first.json"
            second_path = root / "renamed-and-reordered.json"
            first_path.write_bytes(first_canary.stdout)
            second_path.write_text(json.dumps(reversed_canary, indent=2), encoding="utf-8")
            first = run_cli("render", "traditional-nine", str(first_path), cwd=HERE, env=env_a)
            second = run_cli("render", "traditional-nine", str(second_path), cwd=root, env=env_b)
            self.assertEqual(first.returncode, 0, first.stderr.decode())
            self.assertEqual(first.stdout, second.stdout)

    def test_catalogs_schemas_and_example_are_digest_pinned(self) -> None:
        targets = {
            "scenario_schema": "scenario.schema.json",
            "receipt_schema": "receipt.schema.json",
            "rules": "rules.json",
            "mirror_plans": "mirror-plans.json",
            "traditional-nine": "examples/traditional-nine.json",
        }
        for pin, filename in targets.items():
            with self.subTest(pin=pin):
                value = json.loads((HERE / filename).read_text(encoding="utf-8"))
                self.assertEqual(lab.digest_value(value), lab.PINS[pin])

    def test_scenario_completed_and_halted_receipts_match_their_schemas(self) -> None:
        scenario_schema = self.contract["scenario_schema"]
        receipt_schema = self.contract["receipt_schema"]
        self.assertTrue(schema_accepts(self.contract["scenario"], scenario_schema, scenario_schema))
        completed = lab.rehearse_value(self.contract, self.canary)
        self.assertTrue(schema_accepts(completed, receipt_schema, receipt_schema))

        novel = copy.deepcopy(self.contract)
        novel["scenario"]["stimuli"][1]["route"] = "/cell/unknown"
        rebind_scenario(novel)
        halted = lab.rehearse_value(novel, lab.make_canary(novel))
        self.assertTrue(schema_accepts(halted, receipt_schema, receipt_schema))

        missing_binding = copy.deepcopy(completed)
        del missing_binding["bindings"]["rules_sha256"]
        self.assertFalse(schema_accepts(missing_binding, receipt_schema, receipt_schema))

    def test_source_has_no_egress_execution_environment_or_write_path(self) -> None:
        source = ENGINE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_modules = {
            "asyncio",
            "http",
            "requests",
            "socket",
            "subprocess",
            "time",
            "urllib",
        }
        forbidden_calls = {
            "compile",
            "eval",
            "exec",
            "__import__",
            "connect",
            "create_connection",
            "open_connection",
            "popen",
            "run",
            "system",
            "write_bytes",
            "write_text",
            "unlink",
            "rename",
            "replace",
            "mkdir",
            "rmdir",
        }
        allowed_os_attributes = {
            "O_CLOEXEC",
            "O_NOFOLLOW",
            "O_NONBLOCK",
            "O_RDONLY",
            "close",
            "fdopen",
            "fstat",
            "open",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(forbidden_modules.isdisjoint(alias.name.split(".")[0] for alias in node.names))
            if isinstance(node, ast.ImportFrom) and node.module:
                self.assertNotIn(node.module.split(".")[0], forbidden_modules)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, forbidden_calls)
                elif isinstance(node.func, ast.Attribute):
                    self.assertNotIn(node.func.attr, forbidden_calls)
                    is_os_call = isinstance(node.func.value, ast.Name) and node.func.value.id == "os"
                    if node.func.attr == "open" and not is_os_call:
                        self.assertGreaterEqual(len(node.args), 1)
                        self.assertIsInstance(node.args[0], ast.Constant)
                        self.assertEqual(node.args[0].value, "rb")
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "os"
            ):
                self.assertIn(node.attr, allowed_os_attributes)
        for marker in ("sk" + "_live" + "_", "A" + "KIA", "sh" + "pat" + "_", "gh" + "p" + "_"):
            self.assertNotIn(marker, source)

    def test_cli_does_not_mutate_the_lab_tree(self) -> None:
        before = tree_fingerprint()
        process = run_cli("check", "traditional-nine")
        self.assertEqual(process.returncode, 0, process.stderr.decode())
        self.assertEqual(tree_fingerprint(), before)


if __name__ == "__main__":
    unittest.main()
