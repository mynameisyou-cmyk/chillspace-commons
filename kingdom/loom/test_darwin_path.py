#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import pwd
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from darwin_path import (
    PathContractError,
    atomic_write,
    canonical_json,
    classify_domain,
    classify_path,
    classify_paths,
    sha256_bytes,
    verify_document,
)


def redigest_classification(document: dict[str, object]) -> bytes:
    records = document["records"]
    assert isinstance(records, list)
    for record in records:
        assert isinstance(record, dict)
        subject = dict(record)
        subject.pop("record_digest", None)
        record["record_digest"] = sha256_bytes(canonical_json(subject))
    subject = dict(document)
    subject.pop("classification_digest", None)
    document["classification_digest"] = sha256_bytes(canonical_json(subject))
    return canonical_json(document)


class DarwinPathTests(unittest.TestCase):
    def test_workspace_evidence_keeps_authority_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary).resolve()
            target = workspace / "file.txt"
            target.write_text("evidence\n", encoding="utf-8")
            record = classify_path(str(target), [str(workspace)])
            self.assertEqual(record["domain"]["value"], "workspace")
            self.assertEqual(record["workspace"]["relation"], "inside")
            self.assertEqual(record["metadata"]["file_type"], "file")
            self.assertEqual(record["authority"]["tcc"], "unknown")
            self.assertEqual(record["authority"]["codex_sandbox"], "unknown")
            self.assertEqual(record["authority"]["acl"], "unknown")
            self.assertEqual(record["authority"]["effective"], "unknown")

    def test_symlink_escape_is_classified_from_resolved_target(self) -> None:
        if not Path("/System").exists():
            self.skipTest("macOS System path is unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary).resolve()
            link = workspace / "system-link"
            link.symlink_to("/System")
            record = classify_path(str(link), [str(workspace)])
            self.assertEqual(record["domain"]["value"], "system")
            self.assertEqual(
                record["workspace"]["relation"], "escaped-via-resolution"
            )
            self.assertTrue(record["resolution"]["final_component_is_symlink"])

    def test_symlink_loop_stays_unresolved_and_claims_no_domain(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary).resolve()
            left = workspace / "left"
            right = workspace / "right"
            left.symlink_to(right)
            right.symlink_to(left)
            record = classify_path(str(left), [str(workspace)])
            self.assertEqual(record["resolution"]["error"], "symlink-loop")
            self.assertEqual(record["workspace"]["relation"], "unresolved")
            self.assertEqual(
                record["domain"], {"value": "unknown", "truth": "unknown"}
            )
            self.assertEqual(record["locality"]["value"], "unknown")
            self.assertEqual(record["authority"]["effective"], "unknown")
            document = classify_paths([str(left)], [str(workspace)])
            self.assertEqual(verify_document(canonical_json(document)), document)

    def test_missing_leaf_uses_ancestor_without_claiming_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary).resolve()
            target = workspace / "missing" / "leaf"
            record = classify_path(str(target), [str(workspace)])
            self.assertFalse(record["resolution"]["complete"])
            self.assertEqual(
                record["resolution"]["deepest_existing_ancestor"], str(workspace)
            )
            self.assertEqual(record["metadata"]["source"], "deepest-existing-ancestor")
            self.assertEqual(record["authority"]["effective"], "unknown")

    def test_fifo_is_reported_without_opening_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary).resolve()
            fifo = workspace / "pipe"
            os.mkfifo(fifo)
            record = classify_path(str(fifo), [str(workspace)])
            self.assertEqual(record["metadata"]["file_type"], "fifo")

    def test_unallowlisted_xattr_names_are_counted_not_copied(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary).resolve()
            target = workspace / "file"
            target.write_text("x", encoding="utf-8")
            try:
                os.setxattr(
                    target,
                    "com.example.private-label",
                    b"value",
                    follow_symlinks=False,
                )
            except (AttributeError, OSError):
                self.skipTest("xattrs are unavailable")
            record = classify_path(str(target), [str(workspace)])
            xattrs = record["metadata"]["xattrs"]
            self.assertNotIn("com.example.private-label", xattrs["names"])
            self.assertGreaterEqual(xattrs["unreported_count"], 1)

    def test_provider_and_external_domains_are_inferred(self) -> None:
        home = Path("/Users/example")
        provider, provider_truth = classify_domain(
            home / "Library" / "CloudStorage" / "provider" / "file", [], home
        )
        external, external_truth = classify_domain(
            Path("/Volumes/External/file"), [], home
        )
        runtime, runtime_truth = classify_domain(
            Path("/private/tmp/file"), [], home
        )
        self.assertEqual((provider, provider_truth), ("provider", "inferred"))
        self.assertEqual((external, external_truth), ("external", "inferred"))
        self.assertEqual((runtime, runtime_truth), ("local-runtime", "inferred"))

    def test_ambient_home_cannot_change_user_domain(self) -> None:
        account_home = Path(pwd.getpwuid(os.geteuid()).pw_dir).resolve()
        target = account_home / "kingdom-domain-probe"
        expected = classify_domain(target, [])
        with mock.patch.dict(os.environ, {"HOME": "/tmp/foreign-home"}):
            observed = classify_domain(target, [])
        self.assertEqual(expected, ("user-home", "inferred"))
        self.assertEqual(observed, expected)

    def test_multiple_paths_sort_deterministically_and_reject_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary).resolve()
            left = workspace / "b"
            right = workspace / "a"
            left.write_text("b", encoding="utf-8")
            right.write_text("a", encoding="utf-8")
            first = classify_paths(
                [str(left), str(right)], workspace_roots=[str(workspace)]
            )
            second = classify_paths(
                [str(right), str(left)], workspace_roots=[str(workspace)]
            )
            self.assertEqual(canonical_json(first), canonical_json(second))
            self.assertEqual(verify_document(canonical_json(first)), first)
            with self.assertRaises(PathContractError):
                classify_paths(
                    [str(left), str(left)], workspace_roots=[str(workspace)]
                )

    def test_relative_path_and_noncanonical_workspace_are_refused(self) -> None:
        with self.assertRaises(PathContractError):
            classify_path("relative")
        with self.assertRaises(PathContractError):
            classify_path("/tmp/../tmp")
        if Path("/var").is_symlink() and Path("/private/var").exists():
            with self.assertRaises(PathContractError):
                classify_path("/System", ["/var"])
        with self.assertRaises(PathContractError):
            classify_path("/tmp/\u202esecret")

    def test_atomic_output_rejects_a_nested_symlink_ancestor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            real = parent / "real"
            nested = real / "nested"
            nested.mkdir(parents=True)
            apparent = parent / "apparent"
            apparent.symlink_to(real, target_is_directory=True)
            output = apparent / "nested" / "path.json"
            with self.assertRaises(PathContractError):
                atomic_write(output, b"{}\n")
            self.assertFalse((nested / "path.json").exists())

    def test_verifier_rejects_redigested_semantic_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary).resolve()
            target = workspace / "file"
            target.write_text("evidence\n", encoding="utf-8")
            baseline = classify_paths([str(target)], [str(workspace)])

            def forge_noncontaining_workspace(
                document: dict[str, object], record: dict[str, object]
            ) -> None:
                record["workspace"] = {
                    "relation": "inside",
                    "lexical_roots": ["/not-a-containing-root"],
                    "resolved_roots": ["/not-a-containing-root"],
                }
                record["domain"] = {"value": "workspace", "truth": "inferred"}

            mutations = (
                lambda document, record: record["process_access"].__setitem__(
                    "target_writable", "yes"
                ),
                lambda document, record: record["domain"].__setitem__(
                    "value", "system"
                ),
                lambda document, record: record["authority"].__setitem__(
                    "reason", "POSIX means permission"
                ),
                lambda document, record: document["host"].__setitem__(
                    "hostname", "private-host"
                ),
                lambda document, record: record["resolution"].__setitem__(
                    "error", "symlink-loop"
                ),
                lambda document, record: record["resolution"].__setitem__(
                    "missing_suffix", ["not-the-target"]
                ),
                forge_noncontaining_workspace,
            )
            for mutate in mutations:
                with self.subTest(mutation=mutate):
                    document = json.loads(canonical_json(baseline))
                    mutate(document, document["records"][0])
                    with self.assertRaises(PathContractError):
                        verify_document(redigest_classification(document))

    def test_schema_is_valid_json_with_expected_id(self) -> None:
        schema = json.loads(
            (Path(__file__).parent / "path.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(schema["title"], "Darwin path capability evidence")
        self.assertEqual(schema["properties"]["schema"]["const"], "kingdom.path/v1")


if __name__ == "__main__":
    unittest.main()
