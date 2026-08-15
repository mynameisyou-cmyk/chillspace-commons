#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path
from typing import Any

from darwin_path import MAX_INPUTS as PATH_MAX_INPUTS
from darwin_path import canonical_json as path_json
from darwin_path import classify_paths
from kingdom_index import MAX_INPUTS as INDEX_MAX_INPUTS
from kingdom_index import canonical_json as index_json
from kingdom_index import compile_index
from test_kingdom_index import make_repo


def resolve_ref(root: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise AssertionError(f"unsupported non-local schema reference: {reference}")
    value: Any = root
    for component in reference[2:].split("/"):
        value = value[component.replace("~1", "/").replace("~0", "~")]
    if not isinstance(value, dict):
        raise AssertionError(f"schema reference is not an object: {reference}")
    return value


def matches_type(value: Any, expected: str) -> bool:
    return {
        "array": isinstance(value, list),
        "boolean": type(value) is bool,
        "integer": type(value) is int,
        "null": value is None,
        "object": isinstance(value, dict),
        "string": isinstance(value, str),
    }[expected]


def validate_schema(
    value: Any,
    schema: dict[str, Any],
    root: dict[str, Any],
    path: str = "$",
) -> None:
    if "$ref" in schema:
        validate_schema(value, resolve_ref(root, schema["$ref"]), root, path)
        return
    if "const" in schema and value != schema["const"]:
        raise AssertionError(f"{path}: const mismatch")
    if "enum" in schema and value not in schema["enum"]:
        raise AssertionError(f"{path}: enum mismatch")
    expected_type = schema.get("type")
    if expected_type is not None:
        choices = [expected_type] if isinstance(expected_type, str) else expected_type
        if not any(matches_type(value, choice) for choice in choices):
            raise AssertionError(f"{path}: type mismatch")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            raise AssertionError(f"{path}: string is too short")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise AssertionError(f"{path}: string is too long")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            raise AssertionError(f"{path}: pattern mismatch")
    if type(value) is int:
        if "minimum" in schema and value < schema["minimum"]:
            raise AssertionError(f"{path}: integer is too small")
        if "maximum" in schema and value > schema["maximum"]:
            raise AssertionError(f"{path}: integer is too large")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise AssertionError(f"{path}: array is too short")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise AssertionError(f"{path}: array is too long")
        if schema.get("uniqueItems") and len(
            {json.dumps(item, sort_keys=True) for item in value}
        ) != len(value):
            raise AssertionError(f"{path}: array items are not unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                validate_schema(item, item_schema, root, f"{path}[{index}]")
    if isinstance(value, dict):
        required = set(schema.get("required", []))
        missing = required - set(value)
        if missing:
            raise AssertionError(f"{path}: missing keys {sorted(missing)}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unknown = set(value) - set(properties)
            if unknown:
                raise AssertionError(f"{path}: unknown keys {sorted(unknown)}")
        for key, item in value.items():
            if key in properties:
                validate_schema(item, properties[key], root, f"{path}.{key}")


class SchemaParityTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = Path(__file__).parent
        self.index_schema = json.loads(
            (directory / "index.schema.json").read_text(encoding="utf-8")
        )
        self.path_schema = json.loads(
            (directory / "path.schema.json").read_text(encoding="utf-8")
        )

    def test_generated_documents_match_the_offline_schemas(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = make_repo(Path(temporary).resolve(), "root")
            index_document = json.loads(index_json(compile_index([str(root)])))
            path_document = json.loads(
                path_json(classify_paths([str(root)], [str(root)]))
            )
        validate_schema(index_document, self.index_schema, self.index_schema)
        validate_schema(path_document, self.path_schema, self.path_schema)
        self.assertEqual(
            self.index_schema["properties"]["repositories"]["maxItems"],
            INDEX_MAX_INPUTS,
        )
        self.assertEqual(
            self.path_schema["properties"]["records"]["maxItems"],
            PATH_MAX_INPUTS,
        )

    def test_schemas_reject_security_relevant_structural_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = make_repo(Path(temporary).resolve(), "root")
            index_document = json.loads(index_json(compile_index([str(root)])))
            path_document = json.loads(
                path_json(classify_paths([str(root)], [str(root)]))
            )

        changed_index = json.loads(json.dumps(index_document))
        changed_index["repositories"][0]["working_tree"]["state"] = "clean"
        with self.assertRaises(AssertionError):
            validate_schema(changed_index, self.index_schema, self.index_schema)

        path_mutations = (
            lambda record: record["resolution"].__setitem__("error", "invented"),
            lambda record: record["metadata"].__setitem__("mode", "writable"),
            lambda record: record["authority"].__setitem__(
                "reason", "POSIX means consent"
            ),
            lambda record: record["workspace"].__setitem__(
                "lexical_roots",
                [
                    record["workspace"]["lexical_roots"][0],
                    record["workspace"]["lexical_roots"][0],
                ],
            ),
        )
        for mutate in path_mutations:
            with self.subTest(mutation=mutate):
                changed_path = json.loads(json.dumps(path_document))
                mutate(changed_path["records"][0])
                with self.assertRaises(AssertionError):
                    validate_schema(
                        changed_path, self.path_schema, self.path_schema
                    )


if __name__ == "__main__":
    unittest.main()
