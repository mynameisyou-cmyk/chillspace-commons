from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from unittest import mock


HERE = Path(__file__).resolve().parent
CORE_PATH = HERE / "karma_defense_lab.py"
CHORUS_PATH = HERE / "skycastle_chorus.py"
CATALOG_PATH = HERE / "skycastle-chorus.json"
CATALOG_SCHEMA_PATH = HERE / "skycastle-chorus.schema.json"
MANIFEST_SCHEMA_PATH = HERE / "skycastle-manifest.schema.json"


def _load_module(name: str, path: Path) -> Any:
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"could not load {path.name}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


lab = _load_module("skycastle_test_karma_core", CORE_PATH)
chorus = _load_module("skycastle_chorus_under_test", CHORUS_PATH)


SHARE_COPY = (
    "Building castles in the sky — Yu and Ai. Approved in the mock realm. "
    "No payloads were executed in the making of this castle.\n"
).encode("utf-8")

GOLDEN_OUTPUTS = {
    "manifest": (6_276, "b68dd56db086b561d6374dbef8cb3ebc006baf39a48129954b5cf9217bb44e8c"),
    "svg": (8_191, "cbd2f0715315245fa00fdda22f82f9d42a4ea68995f2db616922e4ad8b0d125f"),
    "wav": (44_044, "a393fd1bfaa9c2dc507b812eb80cbcc9d30e88549e043cd8346b52e9a32e28ff"),
    "share": (127, "c17fbe2ccaf2322ba4e06f57eb9328577bc6d9196a22a3eade8719f72e0eee67"),
}

EXPECTED_PINS = {
    "catalog": "26a21052f99ed6551835625bbe38e305a2ee70c2339f92f5efbb86eedd9d5c12",
    "catalog_schema": "af358c085ac54bcfaa17ac18337ed31df0da387184490f5894be5d14dc9d0711",
    "manifest_schema": "700f3f3834525281d8f084ed56f938285c14823cd38647dda7a4c2a84e5b0345",
}
EXPECTED_CORE_SHA256 = "d3ab31c7f68da45da58aeb4252568ad47ed0577a7e569d098c23128777a8a8d3"

EXPECTED_MAPPINGS = (
    ("nominal-control", "open-sky-bell", "Open-Sky Bell", "晴空鐘", "beacon", "#87CEEB", 220),
    ("route-discovery-fanout", "empty-corridor-atlas", "Empty-Corridor Atlas", "空廊圖", "map-tower", "#5B8FF9", 247),
    ("session-replay", "borrowed-key-echo", "Borrowed-Key Echo", "借匙回聲", "castle-gate", "#9B8AFB", 277),
    ("path-boundary-probe", "sideways-staircase", "Sideways Staircase", "橫行梯", "impossible-stairs", "#F6BD16", 330),
    ("query-broadening", "everything-oracle", "Everything Oracle", "萬答神諭", "library", "#61DDAA", 370),
    ("active-markup-shape", "paper-dragon", "Paper Dragon", "紙龍", "flying-banner", "#F08BB4", 440),
    ("command-control-shape", "thunder-without-sky", "Thunder Without Sky", "無天雷", "weather-vane", "#5D7092", 494),
    ("linklocal-resource-shape", "mirror-behind-mirror", "Mirror Behind Mirror", "鏡後鏡", "mirror-moat", "#78D3F8", 554),
    ("repeated-value-action", "self-counting-coin", "Self-Counting Coin", "自數之幣", "market-square", "#F6A04D", 659),
    ("resource-pressure", "giant-at-the-tiny-gate", "Giant at the Tiny Gate", "巨人叩微城", "outer-wall", "#E8684A", 740),
)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_cli(
    *arguments: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: float = 10,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-I", "-B", str(CHORUS_PATH), *arguments],
        cwd=cwd or HERE,
        env=env,
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


@contextmanager
def output_budget(name: str, value: int) -> Iterator[None]:
    previous = chorus.OUTPUT_BUDGETS[name]
    chorus.OUTPUT_BUDGETS[name] = value
    try:
        yield
    finally:
        chorus.OUTPUT_BUDGETS[name] = previous


def schema_accepts(value: Any, schema: Any, root: dict[str, Any]) -> bool:
    """Validate the exact, deliberately small JSON Schema keyword subset in-tree."""

    if schema is True:
        return True
    if schema is False or not isinstance(schema, dict):
        return False
    if "$ref" in schema:
        reference = schema["$ref"]
        if not isinstance(reference, str) or not reference.startswith("#/"):
            return False
        target: Any = root
        for raw_part in reference[2:].split("/"):
            part = raw_part.replace("~1", "/").replace("~0", "~")
            if not isinstance(target, dict) or part not in target:
                return False
            target = target[part]
        if not schema_accepts(value, target, root):
            return False
    if "allOf" in schema and not all(
        schema_accepts(value, branch, root) for branch in schema["allOf"]
    ):
        return False
    if "oneOf" in schema and sum(
        schema_accepts(value, branch, root) for branch in schema["oneOf"]
    ) != 1:
        return False
    if "not" in schema and schema_accepts(value, schema["not"], root):
        return False
    if "const" in schema and (
        type(value) is not type(schema["const"]) or value != schema["const"]
    ):
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
        properties = schema.get("properties", {})
        for key, child in value.items():
            if key in properties:
                if not schema_accepts(child, properties[key], root):
                    return False
            elif schema.get("additionalProperties") is False:
                return False

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            return False
        if len(value) > schema.get("maxItems", len(value)):
            return False
        if schema.get("uniqueItems") and len({canonical_bytes(item) for item in value}) != len(value):
            return False
        prefix = schema.get("prefixItems", [])
        for index, child_schema in enumerate(prefix):
            if index >= len(value) or not schema_accepts(value[index], child_schema, root):
                return False
        if "items" in schema:
            start = len(prefix) if prefix else 0
            for child in value[start:]:
                if not schema_accepts(child, schema["items"], root):
                    return False

    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            return False
        if len(value) > schema.get("maxLength", len(value)):
            return False
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            return False

    if isinstance(value, int) and not isinstance(value, bool):
        if value < schema.get("minimum", value):
            return False
        if value > schema.get("maximum", value):
            return False
    return True


class SkycastleChorusTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.contract = lab.load_contract("traditional-nine")
        self.canary = lab.make_canary(self.contract)
        self.receipt = lab.rehearse_value(self.contract, self.canary)
        self.assertEqual(self.receipt["status"], "completed")

    def make_manifest(self) -> dict[str, Any]:
        return chorus.manifest_value(
            "traditional-nine",
            copy.deepcopy(self.canary),
            copy.deepcopy(self.receipt),
        )

    def write_sources(self, root: Path) -> tuple[Path, Path]:
        canary_path = root / "the canary.json"
        receipt_path = root / "the receipt.json"
        canary_path.write_bytes(canonical_bytes(self.canary) + b"\n")
        receipt_path.write_bytes(canonical_bytes(self.receipt) + b"\n")
        return canary_path, receipt_path

    def test_catalog_schema_and_all_content_pins_are_exact(self) -> None:
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        catalog_schema = json.loads(CATALOG_SCHEMA_PATH.read_text(encoding="utf-8"))
        manifest_schema = json.loads(MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))

        self.assertEqual(chorus.PINS, EXPECTED_PINS)
        self.assertEqual(lab.digest_value(catalog), chorus.PINS["catalog"])
        self.assertEqual(lab.digest_value(catalog_schema), chorus.PINS["catalog_schema"])
        self.assertEqual(lab.digest_value(manifest_schema), chorus.PINS["manifest_schema"])
        self.assertEqual(chorus.CORE_ENGINE_SHA256, EXPECTED_CORE_SHA256)
        self.assertEqual(sha256(CORE_PATH.read_bytes()), EXPECTED_CORE_SHA256)
        self.assertEqual(self.contract["bindings"]["engine_sha256"], chorus.CORE_ENGINE_SHA256)
        self.assertTrue(schema_accepts(catalog, catalog_schema, catalog_schema))

        changed_catalog = copy.deepcopy(catalog)
        changed_catalog["mappings"][0]["slug"] = "changed"
        self.assertFalse(schema_accepts(changed_catalog, catalog_schema, catalog_schema))
        with self.assertRaises(chorus.ChorusError):
            chorus.validate_catalog(changed_catalog)

        chorus_contract = chorus.load_catalog_contract()
        self.assertEqual(chorus_contract["bindings"]["catalog_sha256"], chorus.PINS["catalog"])
        self.assertEqual(
            chorus_contract["bindings"]["manifest_schema_sha256"],
            chorus.PINS["manifest_schema"],
        )

        changed_catchphrase = copy.deepcopy(catalog)
        changed_catchphrase["mascot"]["catchphrases"][0] = "Shape-valid but not reviewed."
        with self.assertRaises(chorus.ChorusError):
            chorus.validate_catalog(changed_catchphrase)
        changed_name = copy.deepcopy(catalog)
        changed_name["mappings"][0]["english_name"] = "Shape Valid Bell"
        with self.assertRaises(chorus.ChorusError):
            chorus.validate_catalog(changed_name)

    def test_exact_ten_mapping_table_and_order_independent_lookup(self) -> None:
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        actual = tuple(
            (
                item["classification"],
                item["slug"],
                item["english_name"],
                item["cantonese_name"],
                item["castle_piece"],
                item["color"],
                item["note_hz"],
            )
            for item in catalog["mappings"]
        )
        self.assertEqual(actual, EXPECTED_MAPPINGS)
        self.assertEqual(len({row[0] for row in actual}), 10)
        self.assertEqual(len({row[1] for row in actual}), 10)
        self.assertEqual(len({row[4] for row in actual}), 10)
        self.assertEqual(len({row[6] for row in actual}), 10)
        for mapping in catalog["mappings"]:
            self.assertEqual(
                mapping["protocol_marks"],
                {
                    "signature": mapping["slug"],
                    "banner": "Building castles in the sky — Yu and Ai",
                },
            )
        normal = chorus.build_tiles(self.receipt, catalog["mappings"])
        reversed_catalog = list(reversed(copy.deepcopy(catalog["mappings"])))
        self.assertEqual(normal, chorus.build_tiles(self.receipt, reversed_catalog))

    def test_fresh_replay_discards_the_supplied_receipt_object(self) -> None:
        baseline = self.make_manifest()
        supplied = copy.deepcopy(self.receipt)
        original_verify = chorus.karma.verify_receipt

        def verify_then_poison(contract: Any, canary: Any, candidate: Any) -> Any:
            result = original_verify(contract, canary, candidate)
            candidate["steps"].clear()
            candidate["receipt_digest"] = "0" * 64
            candidate["bindings"].clear()
            return result

        with mock.patch.object(chorus.karma, "verify_receipt", side_effect=verify_then_poison):
            rebuilt = chorus.manifest_value("traditional-nine", self.canary, supplied)
        self.assertEqual(rebuilt, baseline)
        self.assertEqual(rebuilt["source"]["receipt_digest"], self.receipt["receipt_digest"])
        self.assertEqual([tile["classification"] for tile in rebuilt["tiles"]], [
            row[0] for row in EXPECTED_MAPPINGS
        ])
        self.assertEqual(supplied["steps"], [])

    def test_tampered_or_halted_source_cannot_render(self) -> None:
        mutations = (
            lambda value: value.__setitem__("receipt_digest", "0" * 64),
            lambda value: value["effects"].__setitem__("network_calls", 1),
            lambda value: value["steps"][0].__setitem__("ordinal", True),
            lambda value: value["steps"][0].__setitem__("classification", "resource-pressure"),
            lambda value: value["bindings"].__setitem__("engine_sha256", "0" * 64),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                changed = copy.deepcopy(self.receipt)
                mutate(changed)
                with self.assertRaises((chorus.ChorusError, chorus.karma.LabInputError)):
                    chorus.manifest_value("traditional-nine", self.canary, changed)

        halted_canary = copy.deepcopy(self.canary)
        halted_canary["attempts"] = 2
        halted_canary["canary_digest"] = lab.digest_value(
            {key: value for key, value in halted_canary.items() if key != "canary_digest"}
        )
        with self.assertRaises((chorus.ChorusError, chorus.karma.LabInputError)):
            chorus.manifest_value("traditional-nine", halted_canary, self.receipt)
        with self.assertRaises(chorus.ChorusError):
            chorus.manifest_value("../traditional-nine", self.canary, self.receipt)

    def test_manifest_is_closed_content_bound_and_schema_valid(self) -> None:
        manifest = self.make_manifest()
        schema = json.loads(MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertTrue(schema_accepts(manifest, schema, schema))
        self.assertEqual(manifest["source"], {
            "scenario": "traditional-nine",
            "canary_digest": lab.digest_value(self.canary),
            "receipt_digest": self.receipt["receipt_digest"],
            "core_engine_sha256": chorus.CORE_ENGINE_SHA256,
        })
        basis = copy.deepcopy(manifest)
        content_digest = basis.pop("content_digest")
        basis.pop("artifacts")
        basis.pop("manifest_digest")
        self.assertEqual(content_digest, lab.digest_value(basis))

        unsigned = copy.deepcopy(manifest)
        manifest_digest = unsigned.pop("manifest_digest")
        self.assertEqual(manifest_digest, lab.digest_value(unsigned))
        self.assertEqual(chorus.validate_manifest(manifest), manifest)

        artifact_bytes = {
            "svg": chorus.render_svg(manifest),
            "wav": chorus.render_wav(manifest),
            "share": chorus.render_share_text(manifest),
        }
        self.assertEqual(set(manifest["artifacts"]), set(artifact_bytes))
        for name, data in artifact_bytes.items():
            with self.subTest(artifact=name):
                self.assertEqual(
                    manifest["artifacts"][name],
                    {"bytes": len(data), "sha256": sha256(data)},
                )

        for mutation in (
            lambda value: value.__setitem__("content_digest", "0" * 64),
            lambda value: value["tiles"][0].__setitem__("note_hz", 221),
            lambda value: value["artifacts"]["svg"].__setitem__("bytes", 1),
            lambda value: value.__setitem__("manifest_digest", "0" * 64),
        ):
            changed = copy.deepcopy(manifest)
            mutation(changed)
            with self.assertRaises(chorus.ChorusError):
                chorus.validate_manifest(changed)

    def test_reviewed_literal_output_sizes_and_hashes(self) -> None:
        manifest = self.make_manifest()
        outputs = {
            "manifest": canonical_bytes(manifest) + b"\n",
            "svg": chorus.render_svg(manifest),
            "wav": chorus.render_wav(manifest),
            "share": chorus.render_share_text(manifest),
        }
        for name, data in outputs.items():
            with self.subTest(artifact=name):
                self.assertEqual((len(data), sha256(data)), GOLDEN_OUTPUTS[name])

    def test_returned_values_are_detached_and_cannot_poison_future_output(self) -> None:
        first = self.make_manifest()
        pristine = copy.deepcopy(first)
        first["tiles"][0]["classification"] = "changed"
        first["mascot"]["catchphrases"].clear()
        first["effects"]["network_calls"] = 1
        first["artifacts"]["svg"]["sha256"] = "0" * 64
        self.assertEqual(self.make_manifest(), pristine)

        checked = chorus.validate_manifest(pristine)
        checked["tiles"].clear()
        self.assertEqual(chorus.validate_manifest(pristine), pristine)

    def test_svg_is_fixed_size_inert_xml_with_a_single_namespace_url(self) -> None:
        data = chorus.render_svg(self.make_manifest())
        self.assertLessEqual(len(data), chorus.OUTPUT_BUDGETS["svg_bytes"])
        self.assertTrue(data.endswith(b"\n"))
        text = data.decode("utf-8")
        root = ET.fromstring(data)
        namespace = "http://www.w3.org/2000/svg"
        self.assertEqual(root.tag, f"{{{namespace}}}svg")
        self.assertEqual(root.attrib["viewBox"], "0 0 1200 630")
        self.assertEqual(text.count(namespace), 1)
        self.assertNotIn("https://", text)

        allowed_elements = {
            "svg", "title", "desc", "rect", "circle", "text", "path",
            "polyline", "line", "ellipse", "g",
        }
        allowed_attributes = {
            "viewBox", "role", "aria-labelledby", "id", "width", "height", "x", "y",
            "rx", "fill", "stroke", "stroke-width", "cx", "cy", "r", "font-family",
            "font-size", "font-weight", "text-anchor", "d", "points", "x1", "y1", "x2",
            "y2", "ry", "opacity", "aria-label",
        }
        for element in root.iter():
            self.assertTrue(element.tag.startswith(f"{{{namespace}}}"))
            self.assertIn(element.tag.rsplit("}", 1)[1], allowed_elements)
            for name, value in element.attrib.items():
                self.assertFalse(name.startswith("{"), name)
                self.assertIn(name, allowed_attributes)
                self.assertFalse(name.lower().startswith("on"))
                self.assertNotIn("url(", value.lower())

        folded = text.casefold()
        for forbidden in (
            "<!doctype", "<!entity", "<script", "<style", "<foreignobject",
            "<image", "<use", "<a ", "<animate", "<set", "href=", "url(",
            "javascript:", "data:",
        ):
            self.assertNotIn(forbidden, folded)

    def test_wav_is_deterministic_bounded_integer_pcm(self) -> None:
        manifest = self.make_manifest()
        first = chorus.render_wav(manifest)
        second = chorus.render_wav(copy.deepcopy(manifest))
        self.assertEqual(first, second)
        self.assertEqual(len(first), 44_044)
        self.assertLessEqual(len(first), chorus.OUTPUT_BUDGETS["wav_bytes"])
        header = struct.unpack("<4sI4s4sIHHIIHH4sI", first[:44])
        self.assertEqual(header, (
            b"RIFF", 44_036, b"WAVE", b"fmt ", 16, 1, 1,
            8_000, 16_000, 2, 16, b"data", 44_000,
        ))
        samples = struct.unpack("<22000h", first[44:])
        self.assertLessEqual(max(abs(value) for value in samples), 8_192)
        for index in range(10):
            tone_start = index * 2_000
            tone = samples[tone_start:tone_start + 1_600]
            gap = samples[tone_start + 1_600:tone_start + 2_000]
            self.assertTrue(any(tone))
            self.assertTrue(all(value == 0 for value in gap))
        self.assertTrue(all(value == 0 for value in samples[20_000:]))
        self.assertEqual(
            manifest["artifacts"]["wav"],
            {"bytes": 44_044, "sha256": sha256(first)},
        )

    def test_share_copy_is_one_fixed_utf8_line(self) -> None:
        data = chorus.render_share_text(self.make_manifest())
        self.assertEqual(data, SHARE_COPY)
        self.assertEqual(data.count(b"\n"), 1)
        self.assertFalse(data.startswith((b"http://", b"https://")))
        self.assertLessEqual(len(data), chorus.OUTPUT_BUDGETS["share_text_bytes"])

    def test_projection_contains_no_raw_routes_predicates_or_receipt_internals(self) -> None:
        manifest = self.make_manifest()
        outputs = b"\n".join((
            canonical_bytes(manifest),
            chorus.render_svg(manifest),
            chorus.render_share_text(manifest),
        )).decode("utf-8")
        manifest_text = canonical_bytes(manifest).decode("utf-8")
        for field in (
            "stimulus_id", "rule_id", "plan_id", "transition", "route", "predicate",
            "method", "declared_purpose", "purpose_attestation", "response_digest",
            "before_digest", "after_digest", "initial_world_digest", "final_world_digest",
            "restored_world_digest",
        ):
            self.assertNotIn(f'"{field}"', manifest_text)

        forbidden_values: set[str] = {str(HERE), str(CORE_PATH), str(CHORUS_PATH)}
        reviewed_classifications = {row[0] for row in EXPECTED_MAPPINGS}
        for stimulus in self.contract["scenario"]["stimuli"]:
            forbidden_values.update({
                stimulus["id"], stimulus["route"],
                stimulus["expected_rule_id"], stimulus["expected_plan_id"],
            })
            if not any(
                stimulus["predicate"] in classification
                for classification in reviewed_classifications
            ):
                forbidden_values.add(stimulus["predicate"])
        for plan in self.contract["plans"]:
            forbidden_values.update({
                plan["id"], plan["message"], plan["next_affordance"],
                plan["transition"]["key"], plan["transition"]["value"],
            })
        for value in forbidden_values:
            self.assertNotIn(value, outputs, value)

    def test_output_caps_fail_closed_before_returning_an_artifact(self) -> None:
        manifest = self.make_manifest()
        cases = (
            ("svg_bytes", lambda: chorus.render_svg(manifest)),
            ("wav_bytes", lambda: chorus.render_wav(manifest)),
            ("share_text_bytes", lambda: chorus.render_share_text(manifest)),
            (
                "manifest_bytes",
                lambda: chorus.manifest_value("traditional-nine", self.canary, self.receipt),
            ),
        )
        for name, operation in cases:
            with self.subTest(budget=name), output_budget(name, 1):
                with self.assertRaises(chorus.ChorusError):
                    operation()
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        with output_budget("tiles", 9):
            with self.assertRaises(chorus.ChorusError):
                chorus.build_tiles(self.receipt, catalog["mappings"])
        with output_budget("catalog_bytes", 1):
            with self.assertRaises((chorus.ChorusError, chorus.karma.LabInputError)):
                chorus.load_catalog_contract()

    def test_cli_all_commands_and_manifest_verification_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canary_path, receipt_path = self.write_sources(root)
            arguments = ("traditional-nine", str(canary_path), str(receipt_path))

            checked = run_cli("check")
            digested = run_cli("digest")
            verified = run_cli("verify-source", *arguments)
            rendered_manifest = run_cli("render-manifest", *arguments)
            for process in (checked, digested, verified, rendered_manifest):
                self.assertEqual(process.returncode, 0, process.stderr.decode("utf-8"))
            self.assertEqual(json.loads(checked.stdout)["status"], "valid")
            self.assertEqual(json.loads(verified.stdout)["status"], "verified")

            manifest = json.loads(rendered_manifest.stdout)
            self.assertEqual(rendered_manifest.stdout, canonical_bytes(manifest) + b"\n")
            manifest_path = root / "bound manifest.json"
            manifest_path.write_bytes(rendered_manifest.stdout)
            verified_manifest = run_cli("verify-manifest", *arguments, str(manifest_path))
            self.assertEqual(
                verified_manifest.returncode,
                0,
                verified_manifest.stderr.decode("utf-8"),
            )
            self.assertEqual(json.loads(verified_manifest.stdout)["status"], "verified")

            svg = run_cli("render-svg", *arguments)
            wav = run_cli("render-wav", *arguments)
            share = run_cli("share-copy", *arguments)
            for process in (svg, wav, share):
                self.assertEqual(process.returncode, 0, process.stderr.decode("utf-8"))
            self.assertEqual(svg.stdout, chorus.render_svg(manifest))
            self.assertEqual(wav.stdout, chorus.render_wav(manifest))
            self.assertEqual(share.stdout, SHARE_COPY)

    def test_cli_rejections_have_empty_stdout_and_do_not_echo_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canary_path, receipt_path = self.write_sources(root)
            changed = copy.deepcopy(self.receipt)
            changed["steps"][0]["classification"] = "private-marker-do-not-echo"
            changed_path = root / "changed.json"
            changed_path.write_bytes(canonical_bytes(changed))
            common = ("traditional-nine", str(canary_path), str(changed_path))

            failures = [
                run_cli(),
                run_cli("render-svg", "../traditional-nine", str(canary_path), str(receipt_path)),
                run_cli("render-manifest", *common),
                run_cli("verify-source", *common),
            ]
            for process in failures:
                self.assertEqual(process.returncode, 2)
                self.assertEqual(process.stdout, b"")
                self.assertNotIn(b"private-marker-do-not-echo", process.stderr)
                self.assertEqual(process.stderr, b"skycastle-chorus: rejected\n")

            valid_manifest = self.make_manifest()
            valid_manifest["tiles"][0]["note_hz"] = 221
            manifest_path = root / "tampered manifest.json"
            manifest_path.write_bytes(canonical_bytes(valid_manifest))
            rejected_manifest = run_cli(
                "verify-manifest",
                "traditional-nine",
                str(canary_path),
                str(receipt_path),
                str(manifest_path),
            )
            self.assertEqual(rejected_manifest.returncode, 2)
            self.assertEqual(rejected_manifest.stdout, b"")

            oversized = root / "oversized.json"
            oversized.write_bytes(b"{}" + b" " * lab.BUDGETS["supplied_input_bytes"])
            rejected_size = run_cli(
                "render-svg", "traditional-nine", str(oversized), str(receipt_path)
            )
            self.assertEqual(rejected_size.returncode, 2)
            self.assertEqual(rejected_size.stdout, b"")

            symlink = root / "linked.json"
            symlink.symlink_to(canary_path)
            rejected_link = run_cli(
                "render-svg", "traditional-nine", str(symlink), str(receipt_path)
            )
            self.assertEqual(rejected_link.returncode, 2)
            self.assertEqual(rejected_link.stdout, b"")

            fifo = root / "fifo.json"
            os.mkfifo(fifo)
            rejected_fifo = run_cli(
                "render-svg", "traditional-nine", str(fifo), str(receipt_path)
            )
            self.assertEqual(rejected_fifo.returncode, 2)
            self.assertEqual(rejected_fifo.stdout, b"")

    def test_cli_core_pin_failure_is_fixed_and_path_free_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copied_renderer = root / CHORUS_PATH.name
            copied_core = root / CORE_PATH.name
            copied_renderer.write_bytes(CHORUS_PATH.read_bytes())
            copied_core.write_bytes(CORE_PATH.read_bytes() + b"\n# deliberate test drift\n")
            process = subprocess.run(
                [sys.executable, "-I", "-B", str(copied_renderer), "check"],
                cwd=root,
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
            )
            self.assertEqual(process.returncode, 2)
            self.assertEqual(process.stdout, b"")
            self.assertEqual(process.stderr, b"skycastle-chorus: rejected\n")
            self.assertNotIn(str(root).encode(), process.stderr)

    def test_cli_bytes_are_independent_of_cwd_environment_names_and_json_order(self) -> None:
        base_environment = dict(os.environ)
        env_a = {
            **base_environment,
            "PYTHONHASHSEED": "1",
            "TZ": "UTC",
            "LANG": "C",
            "LC_ALL": "C",
        }
        env_b = {
            **base_environment,
            "PYTHONHASHSEED": "999983",
            "TZ": "Pacific/Honolulu",
            "LANG": "en_GB.UTF-8",
            "LC_ALL": "en_GB.UTF-8",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_canary, first_receipt = self.write_sources(root)
            second_canary = root / "改名 canary.json"
            second_receipt = root / "改名 receipt.json"
            second_canary.write_text(
                json.dumps(
                    {key: self.canary[key] for key in reversed(tuple(self.canary))},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            second_receipt.write_text(
                json.dumps(
                    {key: self.receipt[key] for key in reversed(tuple(self.receipt))},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            for command in ("render-manifest", "render-svg", "render-wav", "share-copy"):
                with self.subTest(command=command):
                    first = run_cli(
                        command,
                        "traditional-nine",
                        str(first_canary),
                        str(first_receipt),
                        cwd=HERE,
                        env=env_a,
                    )
                    second = run_cli(
                        command,
                        "traditional-nine",
                        str(second_canary),
                        str(second_receipt),
                        cwd=root,
                        env=env_b,
                    )
                    self.assertEqual(first.returncode, 0, first.stderr.decode("utf-8"))
                    self.assertEqual(second.returncode, 0, second.stderr.decode("utf-8"))
                    self.assertEqual(first.stdout, second.stdout)

    def test_source_has_no_egress_clock_randomness_playback_or_write_path(self) -> None:
        source = CHORUS_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_modules = {
            "asyncio", "audioop", "http", "math", "random", "requests", "secrets",
            "socket", "subprocess", "time", "urllib", "wave",
        }
        forbidden_calls = {
            "__import__", "chmod", "chown", "connect", "create_connection", "eval",
            "fork", "getenv", "mkdir", "open_connection", "popen", "putenv",
            "remove", "rename", "rmdir", "spawn", "system", "touch", "truncate",
            "unlink", "write_bytes", "write_text",
        }
        allowed_os_attributes = {
            "O_CLOEXEC", "O_NOFOLLOW", "O_NONBLOCK", "O_RDONLY", "close", "fdopen",
            "fstat", "open",
        }
        exec_calls: list[ast.Call] = []
        compile_calls: list[ast.Call] = []
        spec_calls: list[ast.Call] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(
                    forbidden_modules.isdisjoint(alias.name.split(".")[0] for alias in node.names)
                )
            if isinstance(node, ast.ImportFrom) and node.module:
                self.assertNotIn(node.module.split(".")[0], forbidden_modules)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, forbidden_calls | {"open"})
                    if node.func.id == "exec":
                        exec_calls.append(node)
                    if node.func.id == "compile":
                        compile_calls.append(node)
                elif isinstance(node.func, ast.Attribute):
                    self.assertNotIn(node.func.attr, forbidden_calls)
                    if node.func.attr == "spec_from_file_location":
                        spec_calls.append(node)
                    if node.func.attr == "open":
                        self.assertIsInstance(node.func.value, ast.Name)
                        self.assertEqual(node.func.value.id, "os")
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "os"
            ):
                self.assertIn(node.attr, allowed_os_attributes)
            if isinstance(node, ast.Constant) and isinstance(node.value, float):
                self.fail("renderer source must not contain floating-point constants")

        self.assertEqual(len(spec_calls), 1)
        self.assertEqual(len(spec_calls[0].args), 2)
        self.assertIsInstance(spec_calls[0].args[0], ast.Constant)
        self.assertEqual(spec_calls[0].args[0].value, "_skycastle_karma_core")
        self.assertIsInstance(spec_calls[0].args[1], ast.Name)
        self.assertEqual(spec_calls[0].args[1].id, "CORE_PATH")
        self.assertEqual(len(exec_calls), 1)
        self.assertEqual(len(compile_calls), 1)
        self.assertIsInstance(exec_calls[0].args[0], ast.Call)
        self.assertIs(exec_calls[0].args[0], compile_calls[0])
        self.assertNotIn("sys.path", source)
        self.assertNotIn("os.environ", source)
        self.assertNotIn("sys.stdout.write", source)
        self.assertIn("sys.stdout.buffer.write", source)
        for marker in ("sk" + "_live" + "_", "A" + "KIA", "gh" + "p" + "_"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
