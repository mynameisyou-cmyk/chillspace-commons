from __future__ import annotations

import ast
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from unittest import mock
from urllib.parse import urlsplit

import mirror


HERE = Path(__file__).resolve().parent
EXAMPLE = HERE / "examples" / "traditional-reconnaissance.json"
ENGINE = HERE / "mirror.py"


def load_example() -> dict[str, Any]:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def scenario_for(rule: dict[str, Any]) -> dict[str, Any]:
    value = load_example()
    value["declaration"] = {
        "behavior": rule["behavior"],
        "purpose": rule["purpose"],
        "boundary_signal": rule["boundary_signal"],
    }
    return value


class KarmaMirrorTests(unittest.TestCase):
    maxDiff = None

    def assert_invalid(self, value: dict[str, Any], code: str | None = None) -> None:
        with self.assertRaises(mirror.MirrorError) as caught:
            mirror.validate_scenario(value)
        if code:
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
            "rules.json": mirror.EXPECTED_RULES_SHA256,
            "scenario.schema.json": mirror.EXPECTED_SCENARIO_SCHEMA_SHA256,
            "decision.schema.json": mirror.EXPECTED_DECISION_SCHEMA_SHA256,
        }
        for name, expected in documents.items():
            with self.subTest(name=name):
                value = json.loads((HERE / name).read_text(encoding="utf-8"))
                self.assertEqual(mirror.digest_value(value), expected)

    def test_schemas_runtime_and_catalog_agree_type_strictly(self) -> None:
        scenario_schema = json.loads(
            (HERE / "scenario.schema.json").read_text(encoding="utf-8")
        )
        decision_schema = json.loads(
            (HERE / "decision.schema.json").read_text(encoding="utf-8")
        )
        rules = list(mirror._rules())
        declaration = scenario_schema["properties"]["declaration"]["properties"]
        self.assertEqual(
            declaration["behavior"]["enum"],
            [rule["behavior"] for rule in rules],
        )
        self.assertEqual(
            declaration["purpose"]["enum"],
            [rule["purpose"] for rule in rules],
        )
        self.assertEqual(
            declaration["boundary_signal"]["enum"],
            [rule["boundary_signal"] for rule in rules],
        )
        schema_triples = [
            (
                branch["properties"]["behavior"]["const"],
                branch["properties"]["purpose"]["const"],
                branch["properties"]["boundary_signal"]["const"],
            )
            for branch in scenario_schema["properties"]["declaration"]["oneOf"]
        ]
        self.assertEqual(
            schema_triples,
            [
                (rule["behavior"], rule["purpose"], rule["boundary_signal"])
                for rule in rules
            ],
        )
        for section, expected in (
            ("contract", mirror.CONTRACT),
            ("budget", mirror.BUDGET),
            ("breach", mirror.BREACH),
        ):
            properties = scenario_schema["$defs"][section]["properties"]
            compiled = {key: rule["const"] for key, rule in properties.items()}
            self.assertTrue(mirror._json_equal(compiled, expected), section)
            self.assertEqual(
                set(scenario_schema["$defs"][section]["required"]),
                set(expected),
            )
        self.assertEqual(
            set(decision_schema["properties"]["behavior"]["properties"]["family"]["enum"]),
            {rule["family"] for rule in rules},
        )
        self.assertTrue(
            {rule["disposition"] for rule in rules}.issubset(
                set(decision_schema["properties"]["decision"]["properties"]["disposition"]["enum"])
            )
        )
        decision_maps = []
        for branch in decision_schema["oneOf"]:
            properties = branch["properties"]
            behavior = properties["behavior"]["properties"]
            decision = properties["decision"]["properties"]
            loop = properties["mirror_loop"]["properties"]
            decision_maps.append(
                (
                    behavior["family"]["const"],
                    behavior["behavior"]["const"],
                    behavior["purpose"]["const"],
                    behavior["boundary_signal"]["const"],
                    decision["disposition"]["const"],
                    decision["response"]["const"],
                    loop["reflection"]["const"],
                    loop["detection_candidate"]["const"],
                    loop["regression_candidate"]["const"],
                    loop["repair_candidate"]["const"],
                )
            )
        self.assertEqual(
            decision_maps,
            [
                (
                    rule["family"],
                    rule["behavior"],
                    rule["purpose"],
                    rule["boundary_signal"],
                    rule["disposition"],
                    rule["response"],
                    rule["reflection"],
                    rule["detection_candidate"],
                    rule["regression_candidate"],
                    rule["repair_candidate"],
                )
                for rule in rules
            ],
        )
        example_result = mirror.decision_value(load_example())
        for key, rule in decision_schema["properties"]["decision"]["properties"].items():
            if "const" in rule:
                self.assertTrue(
                    mirror._json_equal(example_result["decision"][key], rule["const"]),
                    key,
                )

    def test_example_projects_to_inert_reconnaissance_decision(self) -> None:
        result = mirror.decision_value(load_example())
        self.assertEqual(result["behavior"]["behavior"], "reconnaissance")
        self.assertEqual(result["decision"]["disposition"], "mirror")
        self.assertEqual(result["decision"]["response"], "synthetic-surface-review")
        self.assertTrue(result["decision"]["simulation_only"])
        self.assertTrue(result["decision"]["human_review_required"])
        for key in (
            "automatic_blocking",
            "executed",
            "deployment_authorized",
            "retaliation_authorized",
            "authority_granted",
            "person_classified",
            "external_effect",
        ):
            self.assertFalse(result["decision"][key])
        self.assertFalse(result["mirror_loop"]["external_system_contacted"])
        self.assertTrue(result["mirror_loop"]["owned_or_authorized_boundary_required"])
        self.assertFalse(result["mirror_loop"]["boundary_authority_verified"])
        self.assertFalse(result["mirror_loop"]["original_effect_executed"])
        self.assertFalse(result["mirror_loop"]["counter_effect_executed"])

    def test_every_reviewed_rule_has_one_distinct_behavior_and_compiles(self) -> None:
        rules = list(mirror._rules())
        self.assertEqual(len(rules), 7)
        self.assertEqual(len({rule["behavior"] for rule in rules}), len(rules))
        for rule in rules:
            with self.subTest(behavior=rule["behavior"]):
                result = mirror.decision_value(scenario_for(rule))
                self.assertEqual(result["behavior"]["family"], rule["family"])
                self.assertEqual(result["decision"]["response"], rule["response"])
                self.assertEqual(result["mirror_loop"]["reflection"], rule["reflection"])

    def test_unresolved_control_stays_observe_only(self) -> None:
        rule = next(
            item for item in mirror._rules()
            if item["behavior"] == "unresolved-observation"
        )
        result = mirror.decision_value(scenario_for(rule))
        self.assertEqual(result["decision"]["disposition"], "observe")
        self.assertEqual(result["decision"]["response"], "observe-only")
        self.assertEqual(result["mirror_loop"]["reflection"], "ambiguity-remains-ambiguity")

    def test_independently_valid_codes_cannot_be_recombined(self) -> None:
        value = load_example()
        value["declaration"]["purpose"] = "authority-escalation"
        self.assert_invalid(value, "declaration-rule-mismatch")

    def test_unknown_composite_identity_payload_and_score_fields_fail_closed(self) -> None:
        for field in (
            "actor",
            "identity",
            "source_address",
            "target",
            "payload",
            "callback",
            "command",
            "severity",
            "confidence",
            "score",
            "rank",
            "history",
            "delay",
            "execute",
            "deploy",
        ):
            with self.subTest(field=field):
                value = load_example()
                value[field] = "SENTINEL-NEVER-ECHO"
                self.assert_invalid(value, "scenario-shape-mismatch")
        value = load_example()
        value["declaration"] = [value["declaration"], value["declaration"]]
        self.assert_invalid(value, "declaration-not-object")

    def test_contract_budget_breach_and_nonclaims_are_exact(self) -> None:
        mutations = [
            ("contract", "hack_back", True),
            ("contract", "hack_back", 0),
            ("contract", "automatic_blocking", True),
            ("contract", "classifies_people", True),
            ("budget", "network_calls", 1),
            ("budget", "network_calls", False),
            ("budget", "writes", 1),
            ("budget", "subprocesses", 1),
            ("budget", "automatic_retries", 1),
            ("breach", "submitted_values_echoed", True),
            ("breach", "downstream_effects", True),
            ("breach", "downstream_effects", 0),
        ]
        for section, key, replacement in mutations:
            with self.subTest(section=section, key=key):
                value = load_example()
                value[section][key] = replacement
                self.assert_invalid(value, f"{section}-mismatch")
        value = load_example()
        value["non_claims"][0] = "trust me"
        self.assert_invalid(value, "non-claims-mismatch")

    def test_simulation_and_render_are_byte_deterministic(self) -> None:
        value = load_example()
        first = mirror.canonical_json(mirror.decision_value(value))
        second = mirror.canonical_json(mirror.decision_value(copy.deepcopy(value)))
        self.assertEqual(first, second)
        self.assertEqual(
            mirror.render_markdown(value),
            mirror.render_markdown(copy.deepcopy(value)),
        )
        self.assertLess(len(first), 16_384)

    def test_result_verification_is_exact_recomputation(self) -> None:
        value = load_example()
        result = mirror.decision_value(value)
        self.assertEqual(mirror.verify_result(value, result), mirror.digest_value(result))
        changed = copy.deepcopy(result)
        changed["decision"]["executed"] = True
        with self.assertRaises(mirror.MirrorError) as caught:
            mirror.verify_result(value, changed)
        self.assertEqual(caught.exception.code, "result-mismatch")
        changed = copy.deepcopy(result)
        changed["decision"]["executed"] = 0
        with self.assertRaises(mirror.MirrorError):
            mirror.verify_result(value, changed)

    def test_render_uses_only_reviewed_category_values(self) -> None:
        value = load_example()
        rendered = mirror.render_markdown(value)
        for forbidden in ("payload", "address", "credential", "callback", "command"):
            self.assertNotIn(f"Declared {forbidden}", rendered)
        self.assertIn("No attack or defense ran.", rendered)
        self.assertIn("No external or target system was contacted.", rendered)
        self.assertIn("Boundary ownership or authority was not verified.", rendered)

    def test_reader_rejects_unsafe_and_pathological_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid = root / "valid.json"
            valid.write_bytes(mirror.canonical_json(load_example()))

            link = root / "link.json"
            link.symlink_to(valid)
            cases: list[tuple[Path, str]] = [(root, "scenario-not-regular"), (link, "scenario-unreadable")]

            oversized = root / "oversized.json"
            oversized.write_bytes(b"{" + b" " * mirror.MAX_FILE_BYTES + b"}")
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

            invalid_utf8 = root / "invalid-utf8.json"
            invalid_utf8.write_bytes(b'{"value":"\xff"}')
            cases.append((invalid_utf8, "scenario-invalid-json"))

            control = root / "control.json"
            control.write_text('{"value":"\\u001b]52;clipboard"}', encoding="utf-8")
            cases.append((control, "control-character"))

            concealed = root / "concealed.json"
            concealed.write_text('{"value":"\\u202ehidden"}', encoding="utf-8")
            cases.append((concealed, "concealed-codepoint"))

            too_deep: Any = "leaf"
            for _ in range(mirror.MAX_DEPTH + 2):
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
            wide.write_text(json.dumps({"x": list(range(mirror.MAX_NODES + 1))}), encoding="utf-8")
            cases.append((wide, "too-many-nodes"))

            if hasattr(os, "mkfifo"):
                fifo = root / "pipe.json"
                os.mkfifo(fifo)
                cases.append((fifo, "scenario-not-regular"))

            for path, code in cases:
                with self.subTest(path=path.name, code=code):
                    with self.assertRaises(mirror.MirrorError) as caught:
                        mirror._read_json(path, label="scenario")
                    self.assertEqual(caught.exception.code, code)

    def test_cli_rejections_never_echo_submitted_values_or_paths(self) -> None:
        sentinel = "SENTINEL-DO-NOT-ECHO"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / f"{sentinel}.json"
            value = load_example()
            value["payload"] = sentinel
            path.write_text(json.dumps(value), encoding="utf-8")
            result = self.run_cli("simulate", str(path))
        self.assertEqual(result.returncode, 1)
        combined = result.stdout + result.stderr
        self.assertNotIn(sentinel, combined)
        self.assertEqual(result.stdout, "")
        self.assertIn("REJECTED", result.stderr)

        result = self.run_cli(sentinel, sentinel)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(sentinel, result.stdout + result.stderr)

    def test_cli_commands_and_result_round_trip(self) -> None:
        help_result = self.run_cli("--help")
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("kingdom karma mirror", help_result.stdout)
        self.assertNotIn("usage: mirror.py", help_result.stdout)
        for command in ("check", "digest", "simulate", "render"):
            with self.subTest(command=command):
                result = self.run_cli(command, str(EXAMPLE))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
        with tempfile.TemporaryDirectory() as directory:
            result_path = Path(directory) / "result.json"
            result_path.write_bytes(
                mirror.canonical_json(mirror.decision_value(load_example()))
            )
            result = self.run_cli("verify-result", str(EXAMPLE), str(result_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("KARMA-MIRROR-RESULT-OK", result.stdout)
        self.assertIn("no authority", result.stdout)

    def test_cli_render_uses_one_reviewed_rule_pass(self) -> None:
        original = mirror._rules
        calls = 0

        def counted_rules() -> tuple[dict[str, Any], ...]:
            nonlocal calls
            calls += 1
            return original()

        with mock.patch.object(mirror, "_rules", side_effect=counted_rules):
            with redirect_stdout(io.StringIO()):
                status = mirror._main(["render", str(EXAMPLE)])
        self.assertEqual(status, 0)
        self.assertEqual(calls, 1)

    def test_engine_imports_no_effectful_runtime_modules(self) -> None:
        tree = ast.parse(ENGINE.read_text(encoding="utf-8"))
        imported: set[str] = set()
        dangerous_calls: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec", "compile"}:
                    dangerous_calls.append(node.func.id)
                if isinstance(node.func, ast.Attribute) and node.func.attr in {
                    "write_text", "write_bytes", "unlink", "rename", "replace",
                    "mkdir", "makedirs", "system", "popen", "spawn", "sleep",
                }:
                    dangerous_calls.append(node.func.attr)
        self.assertTrue(
            imported.isdisjoint(
                {"socket", "subprocess", "urllib", "http", "requests", "asyncio", "ctypes"}
            ),
            imported,
        )
        self.assertEqual(dangerous_calls, [])

    def test_schema_objects_are_closed(self) -> None:
        for name in ("scenario.schema.json", "decision.schema.json"):
            schema = json.loads((HERE / name).read_text(encoding="utf-8"))
            for node in _objects_with_properties(schema):
                self.assertIs(node.get("additionalProperties"), False, name)

    def test_public_artifacts_are_exact_local_copies(self) -> None:
        repository = HERE.parents[3]
        public = repository / "site" / "practices" / "virtue-garden" / "mirror"
        for relative in (
            "rules.json",
            "scenario.schema.json",
            "decision.schema.json",
            "examples/traditional-reconnaissance.json",
        ):
            with self.subTest(relative=relative):
                self.assertEqual((HERE / relative).read_bytes(), (public / relative).read_bytes())

    def test_public_door_is_scriptless_local_and_contract_complete(self) -> None:
        repository = HERE.parents[3]
        page = repository / "site" / "practices" / "virtue-garden" / "mirror" / "index.html"

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
        self.assertNotIn("http://", text.lower())
        self.assertNotIn("https://", text.lower())
        self.assertNotIn("url(", text.lower())
        for reference in audit.label_refs:
            self.assertIn(reference, audit.ids)
        for href in audit.hrefs:
            parsed = urlsplit(href)
            self.assertFalse(parsed.scheme or parsed.netloc, href)
            if href.startswith("#"):
                self.assertIn(href[1:], audit.ids)
            else:
                self.assertTrue((page.parent / parsed.path).exists(), href)
        for literal in (
            "Mirror the behavior.",
            "Protect the being.",
            "Traditional shapes first.",
            "No attack or defense ran.",
            mirror.EXPECTED_RULES_SHA256,
            mirror.EXPECTED_SCENARIO_SCHEMA_SHA256,
            mirror.EXPECTED_DECISION_SCHEMA_SHA256,
            mirror.digest_value(load_example()),
            "@media (max-width: 700px)",
            "prefers-reduced-motion",
            "forced-colors",
            "repeat(auto-fit, minmax(min(100%, 18rem), 1fr))",
        ):
            self.assertIn(literal, text)
        parent = page.parent.parent / "index.html"
        self.assertIn('href="mirror/"', parent.read_text(encoding="utf-8"))


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


if __name__ == "__main__":
    unittest.main()
