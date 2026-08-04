from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock
from urllib.parse import urlsplit

import foresight


HERE = Path(__file__).resolve().parent
ENGINE = HERE / "foresight.py"
MIRROR = HERE.parent
REPOSITORY = HERE.parents[4]
PUBLIC = REPOSITORY / "site" / "practices" / "virtue-garden" / "mirror" / "foresight"

EXPECTED_TUPLES = [
    (
        "authority-laundering",
        "delegated-authority-without-fresh-proof",
        "capability-without-fresh-authority",
        "delegation-chain-crosses-tool-boundary",
        "stale-or-ambiguous-delegation",
    ),
    (
        "durable-context-poisoning",
        "untrusted-content-enters-durable-context",
        "future-decision-steering",
        "untrusted-state-crosses-memory-boundary",
        "ordinary-reviewed-preference-storage",
    ),
    (
        "tool-chain-confusion",
        "data-treated-as-control-across-tool-boundary",
        "indirect-capability-execution",
        "untrusted-output-reaches-privileged-tool-input",
        "reviewed-structured-tool-input",
    ),
    (
        "supply-chain-substitution",
        "unverified-artifact-enters-trusted-load-path",
        "trusted-component-replacement",
        "provenance-gap-at-executable-boundary",
        "reviewed-local-development-artifact",
    ),
    (
        "synthetic-consensus",
        "shared-source-presented-as-independent-support",
        "decision-influence-through-false-independence",
        "lineage-collapse-across-witnesses",
        "shared-source-openly-cited",
    ),
    (
        "recursive-resource-capture",
        "self-amplifying-work-graph",
        "shared-capacity-displacement",
        "fanout-exceeds-declared-work-budget",
        "authorized-bounded-parallelism",
    ),
    (
        "protocol-identity-confusion",
        "distinct-protocols-share-name-or-result-shape",
        "validation-against-wrong-contract",
        "namespace-or-schema-identity-mismatch",
        "explicit-versioned-compatibility-adapter",
    ),
    (
        "provenance-privacy-collapse",
        "contextual-records-aggregate-across-boundaries",
        "identity-linkage-or-contextual-disclosure",
        "public-data-crosses-new-purpose-or-retention-boundary",
        "explicit-consented-purpose-limited-publication",
    ),
    (
        "recovery-persistence-capture",
        "control-survives-revocation-or-recovery-path-degrades",
        "continued-capability-or-recovery-denial",
        "revocation-recovery-or-last-known-good-check-fails",
        "authorized-continuity-or-recovery-test",
    ),
    (
        "uncharted-future-shape",
        "unreviewed-future-shape",
        "unresolved",
        "novel-shape-without-reviewed-mapping",
        "insufficient-context",
    ),
]

CANONICAL_MIRROR_DIGESTS = {
    "rules.json": "b6ab34cf1e97feca463e7fdaa0cfce7451a74a32eac0337a230492c557b20799",
    "scenario.schema.json": "a628e1d5a1a2589a5c903cbda8f3f719ab76e36b2cd99873c89a30ae0cb3d9db",
    "decision.schema.json": "dde31e60c53517b30fb5172723df948dcfc1e19eb550d2d1936395ec6762ca4c",
}


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def load_document(name: str) -> dict[str, Any]:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def load_catalog() -> dict[str, Any]:
    return load_document("catalog.json")


def scenario_for(rule: dict[str, Any]) -> dict[str, Any]:
    catalog = load_catalog()
    return {
        "schema": catalog["scenario_schema"],
        "kind": "offline-system-effect-projection",
        "catalog_sha256": foresight.EXPECTED_CATALOG_SHA256,
        "declaration": {
            "constellation": rule["constellation"],
            "mechanism": rule["mechanism"],
            "system_effect_hypothesis": rule["system_effect_hypothesis"],
            "boundary_signal": rule["boundary_signal"],
            "alternative_hypothesis": rule["alternative_hypothesis"],
        },
        "contract": copy.deepcopy(catalog["contract"]),
        "budget": copy.deepcopy(catalog["budget"]),
        "breach": copy.deepcopy(catalog["breach"]),
        "exit": copy.deepcopy(catalog["exit"]),
        "non_claims": copy.deepcopy(catalog["non_claims"]),
    }


class KarmaForesightTests(unittest.TestCase):
    maxDiff = None

    def assert_invalid(self, value: dict[str, Any], code: str | None = None) -> None:
        with self.assertRaises(foresight.ForesightError) as caught:
            foresight.validate_scenario(value)
        if code is not None:
            self.assertEqual(caught.exception.code, code)

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [sys.executable, "-B", str(ENGINE), *args],
            cwd=HERE,
            env=environment,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )

    def test_reviewed_documents_are_canonical_digest_pinned(self) -> None:
        documents = {
            "catalog.json": foresight.EXPECTED_CATALOG_SHA256,
            "scenario.schema.json": foresight.EXPECTED_SCENARIO_SCHEMA_SHA256,
            "projection.schema.json": foresight.EXPECTED_PROJECTION_SCHEMA_SHA256,
        }
        for name, expected in documents.items():
            with self.subTest(name=name):
                self.assertEqual(digest_value(load_document(name)), expected)

    def test_catalog_schema_and_runtime_agree_on_ten_exact_tuples(self) -> None:
        catalog = foresight._catalog()
        self.assertEqual(canonical_json(catalog), canonical_json(load_catalog()))
        rules = catalog["rules"]
        keys = (
            "constellation",
            "mechanism",
            "system_effect_hypothesis",
            "boundary_signal",
            "alternative_hypothesis",
        )
        catalog_tuples = [tuple(rule[key] for key in keys) for rule in rules]
        self.assertEqual(catalog_tuples, EXPECTED_TUPLES)
        self.assertEqual(len({item[0] for item in catalog_tuples}), 10)

        scenario_schema = load_document("scenario.schema.json")
        declaration = scenario_schema["properties"]["declaration"]
        for offset, key in enumerate(keys):
            self.assertEqual(
                declaration["properties"][key]["enum"],
                [item[offset] for item in EXPECTED_TUPLES],
                key,
            )
        schema_tuples = [
            tuple(branch["properties"][key]["const"] for key in keys)
            for branch in declaration["oneOf"]
        ]
        self.assertEqual(schema_tuples, EXPECTED_TUPLES)

        projection_schema = load_document("projection.schema.json")
        response_properties = projection_schema["properties"]["response"]["properties"]
        ladder = catalog["response_ladder"]
        self.assertEqual(response_properties["rung"]["enum"], [item["rung"] for item in ladder])
        self.assertEqual(response_properties["mode"]["enum"], [item["mode"] for item in ladder])
        self.assertEqual(
            set(projection_schema["properties"]["constellation"]["properties"]["family"]["enum"]),
            {rule["family"] for rule in rules},
        )

    def test_catalog_contract_and_budgets_match_schemas_type_strictly(self) -> None:
        catalog = load_catalog()
        schema = load_document("scenario.schema.json")
        for section in ("contract", "budget", "breach", "exit"):
            properties = schema["$defs"][section]["properties"]
            compiled = {key: rule["const"] for key, rule in properties.items()}
            self.assertEqual(canonical_json(compiled), canonical_json(catalog[section]), section)
            self.assertEqual(set(schema["$defs"][section]["required"]), set(catalog[section]))
        self.assertEqual(catalog["budget"]["file_bytes_max"], foresight.MAX_FILE_BYTES)
        self.assertEqual(catalog["budget"]["decoded_nodes_max"], foresight.MAX_NODES)
        self.assertEqual(catalog["budget"]["nesting_depth_max"], foresight.MAX_DEPTH)
        self.assertEqual(catalog["budget"]["string_characters_max"], foresight.MAX_STRING)
        self.assertEqual(catalog["budget"]["output_bytes_max"], foresight.MAX_OUTPUT_BYTES)

    def test_all_ten_projections_are_exact_deterministic_and_inert(self) -> None:
        catalog = load_catalog()
        ladder = {item["rung"]: item for item in catalog["response_ladder"]}
        for rule in catalog["rules"]:
            with self.subTest(constellation=rule["constellation"]):
                scenario = scenario_for(rule)
                first = foresight.project_value(scenario)
                second = foresight.project_value(copy.deepcopy(scenario))
                self.assertEqual(canonical_json(first), canonical_json(second))
                self.assertLessEqual(len(canonical_json(first)), foresight.MAX_OUTPUT_BYTES)
                self.assertEqual(
                    set(first),
                    {
                        "schema",
                        "scenario_sha256",
                        "scenario_schema_sha256",
                        "projection_schema_sha256",
                        "catalog_sha256",
                        "constellation",
                        "purpose_frame",
                        "response",
                        "karma_loop",
                        "exit",
                        "non_claims",
                    },
                )
                self.assertEqual(first["schema"], catalog["projection_schema"])
                self.assertEqual(first["scenario_sha256"], digest_value(scenario))
                self.assertEqual(first["scenario_schema_sha256"], foresight.EXPECTED_SCENARIO_SCHEMA_SHA256)
                self.assertEqual(first["projection_schema_sha256"], foresight.EXPECTED_PROJECTION_SCHEMA_SHA256)
                self.assertEqual(first["catalog_sha256"], foresight.EXPECTED_CATALOG_SHA256)
                self.assertEqual(
                    first["constellation"],
                    {
                        "id": rule["constellation"],
                        "display_name": rule["display_name"],
                        "family": rule["family"],
                        "mechanism": rule["mechanism"],
                        "boundary_signal": rule["boundary_signal"],
                    },
                )
                self.assertEqual(
                    first["purpose_frame"],
                    {
                        "scope": "possible-system-effect-if-mechanism-succeeds",
                        "system_effect_hypothesis": rule["system_effect_hypothesis"],
                        "alternative_hypothesis": rule["alternative_hypothesis"],
                        "effect_established": False,
                        "person_intent_inferred": False,
                    },
                )
                rung = ladder[rule["response_rung"]]
                self.assertEqual(
                    first["response"],
                    {
                        "rung": rung["rung"],
                        "display_name": rung["display_name"],
                        "candidate": rule["response_candidate"],
                        "mode": rung["mode"],
                        "recovery_candidate": rung["recovery_candidate"],
                        "advisory_only": True,
                        "human_review_required": True,
                        "automatic_enforcement": False,
                        "executed": False,
                        "deployment_authorized": False,
                        "retaliation_authorized": False,
                        "authority_granted": False,
                        "person_classified": False,
                        "external_effect": False,
                    },
                )
                self.assertEqual(
                    first["karma_loop"],
                    {
                        "keep": "one-reviewed-category-shape",
                        "articulate": "effect-hypothesis-and-near-miss-kept-together",
                        "reflect": rule["reflection"],
                        "hypothesis_test_candidate": rule["hypothesis_test_candidate"],
                        "negative_control_candidate": rule["negative_control_candidate"],
                        "regression_candidate": rule["regression_candidate"],
                        "repair_candidate": rule["repair_candidate"],
                        "ask_again": rule["release_review_candidate"],
                        "automatic_rule_update": False,
                        "model_training": False,
                        "state_retained": False,
                        "external_system_contacted": False,
                        "original_effect_executed": False,
                        "counter_effect_executed": False,
                    },
                )
                self.assertEqual(first["exit"], catalog["exit"])
                self.assertEqual(first["non_claims"], catalog["non_claims"])

    def test_uncharted_shape_is_observe_only_and_cannot_update_rules(self) -> None:
        rule = next(
            item for item in load_catalog()["rules"]
            if item["constellation"] == "uncharted-future-shape"
        )
        result = foresight.project_value(scenario_for(rule))
        self.assertEqual(result["constellation"]["family"], "unknown")
        self.assertEqual(result["response"]["rung"], "observe")
        self.assertEqual(result["response"]["candidate"], "observe-only")
        self.assertEqual(result["response"]["mode"], "information-only")
        self.assertEqual(result["karma_loop"]["reflect"], "unknown-remains-unknown")
        self.assertEqual(result["karma_loop"]["repair_candidate"], "no-repair-until-reviewed")
        self.assertFalse(result["karma_loop"]["automatic_rule_update"])
        self.assertFalse(result["response"]["automatic_enforcement"])

    def test_independently_valid_declaration_codes_cannot_be_recombined(self) -> None:
        rules = load_catalog()["rules"]
        keys = (
            "constellation",
            "mechanism",
            "system_effect_hypothesis",
            "boundary_signal",
            "alternative_hypothesis",
        )
        for key in keys:
            with self.subTest(key=key):
                value = scenario_for(rules[0])
                value["declaration"][key] = rules[1][key]
                self.assert_invalid(value, "declaration-rule-mismatch")

    def test_intent_identity_payload_and_other_extra_fields_fail_closed(self) -> None:
        rule = load_catalog()["rules"][0]
        for field in (
            "intent",
            "purpose",
            "actor",
            "identity",
            "source_address",
            "target",
            "payload",
            "prompt",
            "credential",
            "callback",
            "command",
            "url",
            "confidence",
            "severity",
            "score",
            "rank",
            "history",
            "execute",
            "deploy",
        ):
            with self.subTest(location="root", field=field):
                value = scenario_for(rule)
                value[field] = "SENTINEL-NEVER-ECHO"
                self.assert_invalid(value, "scenario-shape-mismatch")
            with self.subTest(location="declaration", field=field):
                value = scenario_for(rule)
                value["declaration"][field] = "SENTINEL-NEVER-ECHO"
                self.assert_invalid(value, "declaration-shape-mismatch")

    def test_input_contract_is_exact_and_json_type_strict(self) -> None:
        rule = load_catalog()["rules"][0]
        mutations: list[tuple[str, str, Any, str]] = [
            ("contract", "person_intent_inferred", 0, "contract-mismatch"),
            ("contract", "automatic_enforcement", True, "contract-mismatch"),
            ("contract", "hack_back", True, "contract-mismatch"),
            ("budget", "network_calls", False, "budget-mismatch"),
            ("budget", "writes", 1, "budget-mismatch"),
            ("budget", "clock_reads", 1, "budget-mismatch"),
            ("budget", "random_draws", 1, "budget-mismatch"),
            ("breach", "submitted_values_echoed", 0, "breach-mismatch"),
            ("breach", "downstream_effects", True, "breach-mismatch"),
            ("exit", "state_retained", 0, "exit-mismatch"),
            ("exit", "authority_created", True, "exit-mismatch"),
        ]
        for section, key, replacement, code in mutations:
            with self.subTest(section=section, key=key):
                value = scenario_for(rule)
                value[section][key] = replacement
                self.assert_invalid(value, code)

        for key in ("contract", "budget", "breach", "exit"):
            with self.subTest(extra_in=key):
                value = scenario_for(rule)
                value[key]["extra"] = False
                self.assert_invalid(value, f"{key}-mismatch")

        value = scenario_for(rule)
        value["declaration"] = [value["declaration"]]  # type: ignore[assignment]
        self.assert_invalid(value, "declaration-not-object")
        for key in tuple(scenario_for(rule)["declaration"]):
            with self.subTest(declaration_type=key):
                value = scenario_for(rule)
                value["declaration"][key] = 0
                self.assert_invalid(value, "declaration-value-mismatch")
        value = scenario_for(rule)
        value["non_claims"][0] = "trust me"
        self.assert_invalid(value, "non-claims-mismatch")
        value = scenario_for(rule)
        value["non_claims"][0] = 0
        self.assert_invalid(value, "non-claims-mismatch")

    def test_projection_tampering_fails_exact_recomputation(self) -> None:
        scenario = scenario_for(load_catalog()["rules"][0])
        result = foresight.project_value(scenario)
        self.assertEqual(foresight.verify_result(scenario, result), digest_value(result))
        mutations = [
            ("response", "executed", True),
            ("response", "executed", 0),
            ("response", "authority_granted", True),
            ("karma_loop", "automatic_rule_update", True),
            ("purpose_frame", "person_intent_inferred", True),
            ("exit", "state_retained", True),
        ]
        for section, key, replacement in mutations:
            with self.subTest(section=section, key=key):
                changed = copy.deepcopy(result)
                changed[section][key] = replacement
                with self.assertRaises(foresight.ForesightError) as caught:
                    foresight.verify_result(scenario, changed)
                self.assertEqual(caught.exception.code, "result-mismatch")
                self.assertEqual(foresight.project_value(scenario), result)

    def test_reader_rejects_unsafe_paths_and_pathological_json(self) -> None:
        scenario = scenario_for(load_catalog()["rules"][0])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid = root / "valid.json"
            valid.write_bytes(canonical_json(scenario))

            link = root / "link.json"
            link.symlink_to(valid)
            cases: list[tuple[Path, str]] = [
                (root, "scenario-not-regular"),
                (link, "scenario-unreadable"),
            ]

            oversized = root / "oversized.json"
            oversized.write_bytes(b"{" + b" " * foresight.MAX_FILE_BYTES + b"}")
            cases.append((oversized, "scenario-too-large"))

            duplicate = root / "duplicate.json"
            duplicate.write_text('{"schema":"a","schema":"b"}', encoding="utf-8")
            cases.append((duplicate, "duplicate-key"))

            nonfinite = root / "nonfinite.json"
            nonfinite.write_text('{"value":NaN}', encoding="utf-8")
            cases.append((nonfinite, "non-finite-number"))

            floating = root / "floating.json"
            floating.write_text('{"value":1.5}', encoding="utf-8")
            cases.append((floating, "unsupported-number"))

            huge_number = root / "huge-number.json"
            huge_number.write_text('{"value":12345678901}', encoding="utf-8")
            cases.append((huge_number, "number-out-of-range"))

            invalid_utf8 = root / "invalid-utf8.json"
            invalid_utf8.write_bytes(b'{"value":"\xff"}')
            cases.append((invalid_utf8, "scenario-invalid-json"))

            control = root / "control.json"
            control.write_text('{"value":"\\u001b]52;clipboard"}', encoding="utf-8")
            cases.append((control, "control-character"))

            concealed = root / "concealed.json"
            concealed.write_text('{"value":"\\u202ehidden"}', encoding="utf-8")
            cases.append((concealed, "concealed-codepoint"))

            surrogate = root / "surrogate.json"
            surrogate.write_text('{"value":"\\ud800"}', encoding="utf-8")
            cases.append((surrogate, "invalid-unicode"))

            long_string = root / "long-string.json"
            long_string.write_text(
                json.dumps({"value": "x" * (foresight.MAX_STRING + 1)}),
                encoding="utf-8",
            )
            cases.append((long_string, "string-too-long"))

            too_deep: Any = "leaf"
            for _ in range(foresight.MAX_DEPTH + 2):
                too_deep = {"x": too_deep}
            deep = root / "deep.json"
            deep.write_text(json.dumps(too_deep), encoding="utf-8")
            cases.append((deep, "too-deep"))

            parser_deep = root / "parser-deep.json"
            parser_deep.write_text(
                '{"x":' * 1_500 + '"leaf"' + "}" * 1_500,
                encoding="utf-8",
            )
            cases.append((parser_deep, "too-deep"))

            wide = root / "wide.json"
            wide.write_text(
                json.dumps({"x": list(range(foresight.MAX_NODES + 1))}),
                encoding="utf-8",
            )
            cases.append((wide, "too-many-nodes"))

            array_root = root / "array.json"
            array_root.write_text("[]", encoding="utf-8")
            cases.append((array_root, "scenario-root-not-object"))

            if hasattr(os, "mkfifo"):
                fifo = root / "pipe.json"
                os.mkfifo(fifo)
                cases.append((fifo, "scenario-not-regular"))

            for path, code in cases:
                with self.subTest(path=path.name, code=code):
                    with self.assertRaises(foresight.ForesightError) as caught:
                        foresight._read_json(path, label="scenario")
                    self.assertEqual(caught.exception.code, code)

    def test_reader_detects_a_file_identity_change_during_held_read(self) -> None:
        scenario = scenario_for(load_catalog()["rules"][0])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scenario.json"
            path.write_bytes(canonical_json(scenario))
            real_fstat = foresight.os.fstat
            calls = 0

            def changed_fstat(descriptor: int) -> Any:
                nonlocal calls
                current = real_fstat(descriptor)
                calls += 1
                if calls != 2:
                    return current
                return SimpleNamespace(
                    st_mode=current.st_mode,
                    st_size=current.st_size,
                    st_dev=current.st_dev,
                    st_ino=current.st_ino,
                    st_mtime_ns=current.st_mtime_ns,
                    st_ctime_ns=current.st_ctime_ns + 1,
                )

            with mock.patch.object(foresight.os, "fstat", side_effect=changed_fstat):
                with self.assertRaises(foresight.ForesightError) as caught:
                    foresight._read_json(path, label="scenario")
            self.assertEqual(caught.exception.code, "scenario-changed-during-read")

    def test_cli_commands_round_trip_and_emit_exact_projection(self) -> None:
        scenario = scenario_for(load_catalog()["rules"][0])
        expected = foresight.project_value(scenario)
        help_result = self.run_cli("--help")
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("kingdom karma mirror foresight", help_result.stdout)
        self.assertIn("project", help_result.stdout)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scenario_path = root / "scenario.json"
            result_path = root / "result.json"
            scenario_path.write_bytes(canonical_json(scenario))
            result_path.write_bytes(canonical_json(expected))
            for command in ("check", "digest", "render"):
                with self.subTest(command=command):
                    result = self.run_cli(command, str(scenario_path))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, "")
            result = self.run_cli("project", str(scenario_path))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            self.assertEqual(result.stdout.encode("utf-8"), canonical_json(expected))
            result = self.run_cli("verify-result", str(scenario_path), str(result_path))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("KARMA-FORESIGHT-RESULT-OK", result.stdout)
            self.assertIn("no authority", result.stdout)

    def test_cli_and_library_errors_never_echo_values_or_paths(self) -> None:
        sentinel = "SENTINEL-DO-NOT-ECHO"
        scenario = scenario_for(load_catalog()["rules"][0])
        scenario["payload"] = sentinel
        with self.assertRaises(foresight.ForesightError) as caught:
            foresight.validate_scenario(scenario)
        self.assertNotIn(sentinel, str(caught.exception))

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / f"{sentinel}.json"
            path.write_text(json.dumps(scenario), encoding="utf-8")
            result = self.run_cli("project", str(path))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("REJECTED", result.stderr)
        self.assertNotIn(sentinel, result.stdout + result.stderr)

        result = self.run_cli(sentinel, sentinel)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(sentinel, result.stdout + result.stderr)

    def test_project_uses_one_reviewed_catalog_pass(self) -> None:
        scenario = scenario_for(load_catalog()["rules"][0])
        original = foresight._catalog
        calls = 0

        def counted_catalog() -> dict[str, Any]:
            nonlocal calls
            calls += 1
            return original()

        with mock.patch.object(foresight, "_catalog", side_effect=counted_catalog):
            foresight.project_value(scenario)
        self.assertEqual(calls, 1)

    def test_engine_ast_denies_effectful_and_nondeterministic_capabilities(self) -> None:
        tree = ast.parse(ENGINE.read_text(encoding="utf-8"))
        imported: set[str] = set()
        dangerous_calls: list[str] = []
        forbidden_modules = {
            "asyncio",
            "ctypes",
            "ftplib",
            "http",
            "imaplib",
            "importlib",
            "random",
            "requests",
            "secrets",
            "shutil",
            "smtplib",
            "socket",
            "ssl",
            "subprocess",
            "tempfile",
            "time",
            "urllib",
            "uuid",
        }
        forbidden_names = {"eval", "exec", "compile", "__import__", "open"}
        forbidden_attributes = {
            "chmod",
            "chown",
            "connect",
            "import_module",
            "makedirs",
            "mkdir",
            "popen",
            "remove",
            "removedirs",
            "rename",
            "replace",
            "request",
            "rmdir",
            "send",
            "sendall",
            "sleep",
            "spawn",
            "system",
            "touch",
            "truncate",
            "unlink",
            "urlopen",
            "write_bytes",
            "write_text",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in forbidden_names:
                    dangerous_calls.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    call_name = _qualified_attribute(node.func)
                    if node.func.attr in forbidden_attributes:
                        dangerous_calls.append(call_name)
                    elif node.func.attr == "open" and call_name != "os.open":
                        dangerous_calls.append(call_name)
                    elif node.func.attr == "write" and call_name != "sys.stdout.buffer.write":
                        dangerous_calls.append(call_name)
        self.assertTrue(imported.isdisjoint(forbidden_modules), imported & forbidden_modules)
        self.assertEqual(dangerous_calls, [])

    def test_engine_has_no_coupling_to_effectful_or_campaign_subsystems(self) -> None:
        source = ENGINE.read_text(encoding="utf-8").casefold()
        for forbidden in ("operations", "cloudbell", "castlecast", "trapline"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_canonical_mirror_documents_and_engine_pins_are_unchanged(self) -> None:
        for name, expected in CANONICAL_MIRROR_DIGESTS.items():
            with self.subTest(name=name):
                value = json.loads((MIRROR / name).read_text(encoding="utf-8"))
                self.assertEqual(digest_value(value), expected)

        tree = ast.parse((MIRROR / "mirror.py").read_text(encoding="utf-8"))
        assignments: dict[str, Any] = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and target.id.startswith("EXPECTED_"):
                    assignments[target.id] = ast.literal_eval(node.value)
        self.assertEqual(assignments["EXPECTED_RULES_SHA256"], CANONICAL_MIRROR_DIGESTS["rules.json"])
        self.assertEqual(assignments["EXPECTED_SCENARIO_SCHEMA_SHA256"], CANONICAL_MIRROR_DIGESTS["scenario.schema.json"])
        self.assertEqual(assignments["EXPECTED_DECISION_SCHEMA_SHA256"], CANONICAL_MIRROR_DIGESTS["decision.schema.json"])

    def test_schema_objects_are_closed(self) -> None:
        for name in ("scenario.schema.json", "projection.schema.json"):
            schema = load_document(name)
            for node in _objects_with_properties(schema):
                self.assertIs(node.get("additionalProperties"), False, name)

    def test_public_artifacts_are_exact_local_copies(self) -> None:
        for relative in (
            "catalog.json",
            "scenario.schema.json",
            "projection.schema.json",
            "examples/authority-laundering.json",
        ):
            with self.subTest(relative=relative):
                self.assertEqual((HERE / relative).read_bytes(), (PUBLIC / relative).read_bytes())

    def test_public_door_is_scriptless_local_and_names_the_contract(self) -> None:
        page = PUBLIC / "index.html"

        class Audit(HTMLParser):
            def __init__(self) -> None:
                super().__init__()
                self.ids: list[str] = []
                self.hrefs: list[str] = []
                self.sources: list[str] = []
                self.active: list[str] = []
                self.label_refs: list[str] = []
                self.events: list[str] = []

            def handle_starttag(
                self, tag: str, attrs: list[tuple[str, str | None]]
            ) -> None:
                data = dict(attrs)
                if data.get("id"):
                    self.ids.append(str(data["id"]))
                if data.get("href"):
                    self.hrefs.append(str(data["href"]))
                if data.get("src"):
                    self.sources.append(str(data["src"]))
                if tag in {"script", "iframe", "form"}:
                    self.active.append(tag)
                if data.get("aria-labelledby"):
                    self.label_refs.extend(str(data["aria-labelledby"]).split())
                self.events.extend(key for key in data if key.lower().startswith("on"))

        text = page.read_text(encoding="utf-8")
        audit = Audit()
        audit.feed(text)
        self.assertEqual(len(audit.ids), len(set(audit.ids)))
        self.assertEqual(audit.sources, [])
        self.assertEqual(audit.active, [])
        self.assertEqual(audit.events, [])
        self.assertNotIn("http://", text.casefold())
        self.assertNotIn("https://", text.casefold())
        self.assertNotIn("url(", text.casefold())
        for reference in audit.label_refs:
            self.assertIn(reference, audit.ids)
        for href in audit.hrefs:
            parsed = urlsplit(href)
            self.assertFalse(parsed.scheme or parsed.netloc, href)
            if href.startswith("#"):
                self.assertIn(href[1:], audit.ids)
            else:
                self.assertTrue((page.parent / parsed.path).exists(), href)
        folded = text.casefold()
        for literal in (
            "karma foresight",
            "未然圖",
            "model possible system effects",
            "keep persons free",
            "no payload",
            "no identity",
            foresight.EXPECTED_CATALOG_SHA256,
            foresight.EXPECTED_SCENARIO_SCHEMA_SHA256,
            foresight.EXPECTED_PROJECTION_SCHEMA_SHA256,
        ):
            self.assertIn(literal.casefold(), folded)


def _objects_with_properties(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if value.get("type") == "object" and "properties" in value:
            found.append(value)
        for child in value.values():
            found.extend(_objects_with_properties(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_objects_with_properties(child))
    return found


def _qualified_attribute(value: ast.Attribute) -> str:
    parts = [value.attr]
    current: ast.expr = value.value
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


if __name__ == "__main__":
    unittest.main()
