#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import kingdom_index
from kingdom_index import (
    IndexContractError,
    atomic_write,
    bounded_root_commits,
    canonical_json,
    compile_index,
    git_control_tree_signature,
    parse_manifest,
    run_bounded_subprocess,
    sha256_bytes,
    shared_index_signatures,
    verify_document,
)


def manifest_text(name: str = "example", *, doors: bool = False) -> str:
    text = f"""\
name: {name}
purpose: Keep bounded local meaning
kind: service
domain: commons
layer: application
owner_sister: zerone
state: active
dependsOn: []
adopts: [care]
"""
    if doors:
        text += """\
doors:
  - name: "public"
    description: "Public door"
    url: "https://example.invalid/door"
"""
    return text


def git(root: Path, *args: str) -> str:
    env = dict(os.environ)
    env.update(
        {
            "GIT_AUTHOR_NAME": "Kingdom Test",
            "GIT_AUTHOR_EMAIL": "kingdom@example.invalid",
            "GIT_COMMITTER_NAME": "Kingdom Test",
            "GIT_COMMITTER_EMAIL": "kingdom@example.invalid",
            "GIT_CONFIG_NOSYSTEM": "1",
        }
    )
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-C", str(root), *args],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def make_repo(parent: Path, folder: str, name: str = "example") -> Path:
    root = parent / folder
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.name", "Kingdom Test")
    git(root, "config", "user.email", "kingdom@example.invalid")
    (root / "kingdom.yaml").write_text(manifest_text(name), encoding="utf-8")
    (root / "identity.txt").write_text(folder + "\n", encoding="utf-8")
    git(root, "add", "kingdom.yaml", "identity.txt")
    git(root, "commit", "-q", "-m", "fixture")
    return root.resolve()


def redigest_index(document: dict[str, object]) -> bytes:
    repositories = document["repositories"]
    assert isinstance(repositories, list)
    for record in repositories:
        assert isinstance(record, dict)
        subject = dict(record)
        subject.pop("repository_digest", None)
        record["repository_digest"] = sha256_bytes(canonical_json(subject))
    document["input_digest"] = sha256_bytes(
        canonical_json(
            [
                {
                    "repository_id": record["repository_id"],
                    "repository_digest": record["repository_digest"],
                    "canonical": record["canonical"],
                }
                for record in repositories
            ]
        )
    )
    subject = dict(document)
    subject.pop("index_digest", None)
    document["index_digest"] = sha256_bytes(canonical_json(subject))
    return canonical_json(document)


class ManifestTests(unittest.TestCase):
    def test_observed_subset_parses_and_omits_door_values(self) -> None:
        parsed = parse_manifest(manifest_text(doors=True).encode())
        self.assertEqual(parsed["name"], "example")
        self.assertEqual(parsed["depends_on"], [])
        self.assertEqual(parsed["adopts"], ["care"])
        self.assertEqual(parsed["doors_count"], 1)
        self.assertNotIn("url", parsed)
        self.assertNotIn("description", parsed)

    def test_door_name_is_optional_but_description_and_url_are_required(
        self,
    ) -> None:
        without_name = manifest_text(doors=True).replace(
            '  - name: "public"\n', "  -\n"
        )
        parsed = parse_manifest(without_name.encode())
        self.assertEqual(parsed["doors_count"], 1)

    def test_rejects_ambiguous_or_expansive_yaml(self) -> None:
        replacements = {
            "unknown key": ("state: active", "mystery: active"),
            "duplicate key": ("state: active", "state: active\nstate: active"),
            "tab": ("state: active", "state:\tactive"),
            "unquoted colon": (
                "purpose: Keep bounded local meaning",
                "purpose: Keep: bounded local meaning",
            ),
            "anchor": ("state: active", "state: &active active"),
            "block scalar": (
                "purpose: Keep bounded local meaning",
                "purpose: |\n  many lines",
            ),
            "secret shape": (
                "purpose: Keep bounded local meaning",
                "purpose: api_key=abcdefghijklmnop",
            ),
            "remote url": (
                "purpose: Keep bounded local meaning",
                'purpose: "https://example.invalid"',
            ),
            "scp remote": (
                "purpose: Keep bounded local meaning",
                "purpose: git@example:org/repo.git",
            ),
            "slack token": (
                "purpose: Keep bounded local meaning",
                "purpose: xoxb-" "123456789012-abcdefghijklmnop",
            ),
            "invalid single quote": (
                "purpose: Keep bounded local meaning",
                "purpose: 'broken'quote'",
            ),
            "integer primitive": ("name: example", "name: 123"),
            "float primitive": ("name: example", "name: 1.2"),
            "date primitive": ("name: example", "name: 2026-07-30"),
            "legacy boolean primitive": ("name: example", "name: yes"),
            "zero-width format": ("name: example", "name: YOU\u200bSPEAK"),
        }
        baseline = manifest_text()
        for label, (old, new) in replacements.items():
            with self.subTest(label=label):
                with self.assertRaises(IndexContractError):
                    parse_manifest(baseline.replace(old, new).encode())

    def test_rejects_incomplete_doors(self) -> None:
        data = manifest_text() + "doors:\n  - name: incomplete\n"
        with self.assertRaises(IndexContractError):
            parse_manifest(data.encode())

    def test_rejects_invalid_or_credentialed_door_urls(self) -> None:
        baseline = manifest_text(doors=True)
        for invalid in (
            "not-a-url",
            "http://example.invalid/door",
            "https://user:password@example.invalid/door",
        ):
            with self.subTest(url=invalid):
                data = baseline.replace(
                    "https://example.invalid/door", invalid
                ).encode()
                with self.assertRaises(IndexContractError):
                    parse_manifest(data)


class IndexTests(unittest.TestCase):
    def test_single_repository_is_deterministic_and_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = make_repo(Path(temporary).resolve(), "one")
            git(
                root,
                "remote",
                "add",
                "origin",
                "https://token-value@example.invalid/private.git",
            )
            first = compile_index([str(root)])
            second = compile_index([str(root)])
            self.assertEqual(canonical_json(first), canonical_json(second))
            self.assertTrue(first["repositories"][0]["canonical"])
            serialized = canonical_json(first)
            self.assertNotIn(b"token-value", serialized)
            self.assertNotIn(b"example.invalid/private", serialized)
            self.assertEqual(verify_document(serialized), first)

    def test_doors_are_validated_but_url_is_not_emitted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = make_repo(Path(temporary).resolve(), "doors")
            (root / "kingdom.yaml").write_text(
                manifest_text("doors", doors=True), encoding="utf-8"
            )
            git(root, "add", "kingdom.yaml")
            git(root, "commit", "-q", "-m", "doors")
            serialized = canonical_json(compile_index([str(root)]))
            self.assertNotIn(b"https://", serialized)
            document = json.loads(serialized)
            fields = document["repositories"][0]["manifest"]["fields"]
            self.assertEqual(fields["doors_count"], 1)

    def test_duplicate_lineage_requires_exact_canonical_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            source = make_repo(parent, "source", "shared")
            clone = parent / "clone"
            subprocess.run(
                ["git", "clone", "-q", str(source), str(clone)],
                check=True,
                capture_output=True,
            )
            clone = clone.resolve()
            with self.assertRaises(IndexContractError):
                compile_index([str(source), str(clone)])
            document = compile_index(
                [str(clone), str(source)], canonical_roots=[str(source)]
            )
            canonical = [
                item["worktree_path"]
                for item in document["repositories"]
                if item["canonical"]
            ]
            self.assertEqual(canonical, [str(source)])
            self.assertIn(
                "complete-lineage",
                document["ambiguity_groups"][0]["reasons"],
            )
            with self.assertRaises(IndexContractError):
                compile_index(
                    [str(source), str(clone)],
                    canonical_roots=[str(source), str(clone)],
                )
            with self.assertRaises(IndexContractError):
                compile_index(
                    [str(source), str(clone)],
                    canonical_roots=[str(source), str(source)],
                )

    def test_unicode_casefold_name_collision_requires_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            left = make_repo(parent, "left", "YOUSPEAK")
            right = make_repo(parent, "right", "youspeak")
            with self.assertRaises(IndexContractError):
                compile_index([str(left), str(right)])
            document = compile_index(
                [str(left), str(right)], canonical_roots=[str(right)]
            )
            self.assertIn(
                "manifest-name",
                document["ambiguity_groups"][0]["reasons"],
            )

    def test_refuses_relative_subdirectory_missing_manifest_and_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            root = make_repo(parent, "root")
            child = root / "child"
            child.mkdir()
            with self.assertRaises(IndexContractError):
                compile_index(["relative"])
            with self.assertRaises(IndexContractError):
                compile_index([str(root.parent / "root" / ".." / "root")])
            with self.assertRaises(IndexContractError):
                compile_index([str(child)])
            (root / "kingdom.yaml").unlink()
            with self.assertRaises(IndexContractError):
                compile_index([str(root)])

    def test_atomic_output_is_owner_only_and_digest_tampering_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            root = make_repo(parent, "root")
            data = canonical_json(compile_index([str(root)]))
            output = parent / "index.json"
            atomic_write(output, data)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            changed = data.replace(b'"compiler":"kingdom-index/1"', b'"compiler":"other"')
            with self.assertRaises(IndexContractError):
                verify_document(changed)

    def test_atomic_output_rejects_a_nested_symlink_ancestor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            real = parent / "real"
            nested = real / "nested"
            nested.mkdir(parents=True)
            apparent = parent / "apparent"
            apparent.symlink_to(real, target_is_directory=True)
            output = apparent / "nested" / "index.json"
            with self.assertRaises(IndexContractError):
                atomic_write(output, b"{}\n")
            self.assertFalse((nested / "index.json").exists())

    def test_ambient_git_state_cannot_redirect_or_hide_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            target = make_repo(parent, "target", "target")
            foreign = make_repo(parent, "foreign", "foreign")
            (target / "visible.private").write_text("visible\n", encoding="utf-8")
            xdg = parent / "xdg"
            (xdg / "git").mkdir(parents=True)
            (xdg / "git" / "ignore").write_text("*.private\n", encoding="utf-8")
            trace = parent / "git-trace.log"
            with mock.patch.dict(
                os.environ,
                {
                    "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(
                        foreign / ".git" / "objects"
                    ),
                    "GIT_COMMON_DIR": str(foreign / ".git"),
                    "GIT_CONFIG_COUNT": "1",
                    "GIT_CONFIG_KEY_0": "include.path",
                    "GIT_CONFIG_VALUE_0": str(foreign / ".git" / "config"),
                    "GIT_DIR": str(foreign / ".git"),
                    "GIT_GRAFT_FILE": str(foreign / ".git" / "info" / "grafts"),
                    "GIT_OBJECT_DIRECTORY": str(foreign / ".git" / "objects"),
                    "GIT_REPLACE_REF_BASE": "refs/foreign-replacements/",
                    "GIT_WORK_TREE": str(foreign),
                    "GIT_TRACE": str(trace),
                    "XDG_CONFIG_HOME": str(xdg),
                },
                clear=False,
            ):
                record = compile_index([str(target)])["repositories"][0]
            self.assertEqual(record["worktree_path"], str(target))
            self.assertEqual(record["git"]["head"], git(target, "rev-parse", "HEAD"))
            self.assertEqual(record["git"]["directory"], str(target / ".git"))
            self.assertEqual(
                record["git"]["objects_directory"],
                str(target / ".git" / "objects"),
            )
            self.assertEqual(
                record["working_tree"]["untracked_content"],
                "not-inspected",
            )
            self.assertEqual(record["working_tree"]["state"], "unknown")
            self.assertFalse(trace.exists())

    def test_only_staged_names_can_prove_positive_dirty_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = make_repo(Path(temporary).resolve(), "root")
            (root / "untracked.txt").write_text("untracked\n", encoding="utf-8")
            unknown = compile_index([str(root)])["repositories"][0][
                "working_tree"
            ]
            self.assertEqual(unknown["state"], "unknown")
            self.assertEqual(unknown["tracked_content"], "not-inspected")
            self.assertEqual(unknown["untracked_content"], "not-inspected")

            (root / "identity.txt").write_text("staged\n", encoding="utf-8")
            git(root, "add", "identity.txt")
            dirty = compile_index([str(root)])["repositories"][0][
                "working_tree"
            ]
            self.assertEqual(dirty["state"], "dirty")
            self.assertEqual(dirty["staged_records"], 1)

    def test_worktree_evidence_does_not_enumerate_untracked_or_deleted(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            root = make_repo(parent, "root")
            nested = root / "nested"
            nested.mkdir()
            (nested / "file.txt").write_text("tracked\n", encoding="utf-8")
            git(root, "add", "nested/file.txt")
            git(root, "commit", "-q", "-m", "nested")
            (nested / "file.txt").unlink()
            nested.rmdir()
            external = parent / "external"
            external.mkdir()
            (external / "file.txt").write_text("external\n", encoding="utf-8")
            nested.symlink_to(external, target_is_directory=True)
            (root / "nested-repo").mkdir()
            (root / "nested-repo" / ".git").symlink_to(
                root / ".git", target_is_directory=True
            )

            original = kingdom_index.git_bytes
            calls: list[tuple[str, ...]] = []

            def observed_git(
                repository: Path,
                *args: str,
                allow_failure: bool = False,
            ) -> bytes:
                calls.append(args)
                return original(
                    repository, *args, allow_failure=allow_failure
                )

            with mock.patch.object(
                kingdom_index, "git_bytes", observed_git
            ):
                evidence = compile_index([str(root)])["repositories"][0][
                    "working_tree"
                ]
            self.assertEqual(evidence["state"], "unknown")
            self.assertFalse(
                any(args and args[0] == "ls-files" for args in calls)
            )

    def test_rejects_alternate_and_promisor_object_storage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            source = make_repo(parent, "source")
            shared = parent / "shared"
            subprocess.run(
                ["git", "clone", "--shared", "-q", str(source), str(shared)],
                check=True,
                capture_output=True,
            )
            with self.assertRaisesRegex(
                IndexContractError, "alternate object storage"
            ):
                compile_index([str(shared.resolve())])

            alternates = shared / ".git" / "objects" / "info" / "alternates"
            staging = alternates.with_name("alternates.rename")
            alternates.rename(staging)
            staging.rename(alternates.with_name("Alternates"))
            with self.assertRaisesRegex(
                IndexContractError, "alternate object storage"
            ):
                compile_index([str(shared.resolve())])

            http_alternates = (
                source / ".git" / "objects" / "info" / "HTTP-Alternates"
            )
            http_alternates.write_text(
                "https://example.invalid/objects\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(
                IndexContractError, "alternate object storage"
            ):
                compile_index([str(source)])
            http_alternates.unlink()

            pack = source / ".git" / "objects" / "pack"
            for name in ("fixture.promisor", "fixture.PROMISOR"):
                with self.subTest(promisor=name):
                    marker = pack / name
                    marker.write_bytes(b"")
                    with self.assertRaisesRegex(
                        IndexContractError, "promisor object storage"
                    ):
                        compile_index([str(source)])
                    marker.unlink()

    def test_rejects_git_config_includes_without_leaking_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            root = make_repo(parent, "root")
            marker = "glpat-" + "a" * 24
            external = parent / marker
            external.write_text("[malformed\n", encoding="utf-8")
            git(root, "config", "include.path", str(external))

            with self.assertRaisesRegex(
                IndexContractError, "configuration includes"
            ) as raised:
                compile_index([str(root)])
            self.assertNotIn(marker, str(raised.exception))

            output = parent / "index.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(kingdom_index.__file__).resolve()),
                    "compile",
                    "--repo-root",
                    str(root),
                    "--output",
                    str(output),
                ],
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertNotIn(marker, result.stdout + result.stderr)
            self.assertFalse(output.exists())

    def test_rejects_conditional_worktree_and_promisor_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            external = parent / "external.conf"
            external.write_text("[malformed\n", encoding="utf-8")
            cases = (
                (
                    "conditional-include",
                    ("includeIf.onbranch:main.path", str(external)),
                    "configuration includes",
                ),
                (
                    "configured-worktree",
                    ("core.worktree", str(parent)),
                    "worktree indirection",
                ),
                (
                    "promisor",
                    ("remote.origin.promisor", "true"),
                    "promisor configuration",
                ),
                (
                    "partial-filter",
                    ("remote.origin.partialCloneFilter", "blob:none"),
                    "promisor configuration",
                ),
                (
                    "partial-extension",
                    ("extensions.partialClone", "origin"),
                    "promisor configuration",
                ),
                (
                    "ref-storage",
                    ("extensions.refStorage", "reftable"),
                    "reference storage",
                ),
                (
                    "relative-worktrees",
                    ("extensions.relativeWorktrees", "true"),
                    "repository extension",
                ),
            )
            for folder, (key, value), message in cases:
                with self.subTest(key=key):
                    root = make_repo(parent, folder)
                    git(root, "config", key, value)
                    with self.assertRaisesRegex(IndexContractError, message):
                        compile_index([str(root)])

            worktree_root = make_repo(parent, "worktree-config")
            git(worktree_root, "config", "extensions.worktreeConfig", "true")
            git(
                worktree_root,
                "config",
                "--worktree",
                "include.path",
                str(external),
            )
            with self.assertRaisesRegex(
                IndexContractError, "configuration includes"
            ):
                compile_index([str(worktree_root)])

    def test_effective_object_path_is_checked_before_object_reads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = make_repo(Path(temporary).resolve(), "root")
            original = kingdom_index.git_text
            calls: list[tuple[str, ...]] = []

            def redirected_objects(
                repository: Path,
                *args: str,
                allow_failure: bool = False,
            ) -> str:
                calls.append(args)
                if args == (
                    "rev-parse",
                    "--path-format=absolute",
                    "--git-path",
                    "objects",
                ):
                    return str(root / ".git")
                if args == ("rev-parse", "--verify", "HEAD"):
                    self.fail("object identity was read before path agreement")
                return original(
                    repository, *args, allow_failure=allow_failure
                )

            with (
                mock.patch.object(
                    kingdom_index, "git_text", redirected_objects
                ),
                mock.patch.object(
                    kingdom_index,
                    "object_storage_signature",
                    side_effect=AssertionError(
                        "object storage was inspected before path agreement"
                    ),
                ),
            ):
                with self.assertRaisesRegex(
                    IndexContractError, "control or object directories"
                ):
                    compile_index([str(root)])
            self.assertNotIn(("rev-parse", "--verify", "HEAD"), calls)

    def test_effective_control_paths_are_checked_before_identity_reads(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            root = make_repo(parent, "root")
            original = kingdom_index.git_text
            calls: list[tuple[str, ...]] = []

            def redirected_index(
                repository: Path,
                *args: str,
                allow_failure: bool = False,
            ) -> str:
                calls.append(args)
                value = original(
                    repository, *args, allow_failure=allow_failure
                )
                if (
                    args[:2] == ("rev-parse", "--path-format=absolute")
                    and args.count("--git-path") > 1
                ):
                    lines = value.splitlines()
                    lines[1] = str(parent / "external-index")
                    return "\n".join(lines)
                if args == ("rev-parse", "--verify", "HEAD"):
                    self.fail("identity was read before control-path agreement")
                return value

            with mock.patch.object(
                kingdom_index, "git_text", redirected_index
            ):
                with self.assertRaisesRegex(
                    IndexContractError, "control paths"
                ):
                    compile_index([str(root)])
            self.assertNotIn(("rev-parse", "--verify", "HEAD"), calls)

    def test_symlinked_git_evidence_controls_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            cases = (
                ("head", "HEAD", "Git HEAD", b"ref: refs/heads/main\n"),
                ("index", "index", "Git index", None),
                (
                    "exclude",
                    "info/exclude",
                    "Git info controls",
                    b"*.private\n",
                ),
                (
                    "shallow",
                    "shallow",
                    "Git shallow boundary",
                    None,
                ),
                (
                    "packed",
                    "packed-refs",
                    "Git packed refs",
                    b"",
                ),
                (
                    "shared",
                    "sharedindex.fixture",
                    "Git shared index",
                    b"fixture\n",
                ),
            )
            for folder, relative, message, supplied in cases:
                with self.subTest(control=relative):
                    root = make_repo(parent, folder)
                    control = root / ".git" / relative
                    if supplied is None:
                        if relative == "index":
                            supplied = control.read_bytes()
                        else:
                            supplied = (
                                git(root, "rev-parse", "HEAD") + "\n"
                            ).encode()
                    external = parent / f"{folder}.external"
                    external.write_bytes(supplied)
                    if os.path.lexists(control):
                        control.unlink()
                    control.symlink_to(external)
                    with self.assertRaisesRegex(IndexContractError, message):
                        compile_index([str(root)])

    def test_linked_worktree_uses_common_objects_and_aliases_are_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            source = make_repo(parent, "source")
            linked = parent / "linked"
            git(
                source,
                "worktree",
                "add",
                "-q",
                "-b",
                "linked-object-test",
                str(linked),
            )
            record = compile_index([str(linked.resolve())])["repositories"][0]
            self.assertNotEqual(
                record["git"]["directory"], record["git"]["common_directory"]
            )
            self.assertEqual(
                record["git"]["objects_directory"],
                str(source / ".git" / "objects"),
            )
            linked_git = Path(record["git"]["directory"])
            private_refs = linked_git / "refs" / "worktree"
            private_refs.mkdir(parents=True)
            external_ref = parent / "external-worktree-ref"
            external_ref.write_text(
                git(linked, "rev-parse", "HEAD") + "\n",
                encoding="utf-8",
            )
            (private_refs / "test").symlink_to(external_ref)
            (linked_git / "HEAD").write_text(
                "ref: refs/worktree/test\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(
                IndexContractError, "worktree refs"
            ):
                compile_index([str(linked.resolve())])

            root = parent / "aliased"
            root.mkdir()
            real_parent = parent / "real-git-parent"
            real_parent.mkdir()
            alias = parent / "git-parent-alias"
            alias.symlink_to(real_parent, target_is_directory=True)
            external_git = real_parent / "store"
            git(root, "init", "-q", f"--separate-git-dir={external_git}")
            git(root, "config", "user.name", "Kingdom Test")
            git(root, "config", "user.email", "kingdom@example.invalid")
            (root / "kingdom.yaml").write_text(
                manifest_text("aliased"), encoding="utf-8"
            )
            git(root, "add", "kingdom.yaml")
            git(root, "commit", "-q", "-m", "fixture")
            (root / ".git").write_text(
                f"gitdir: {alias / 'store'}\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(IndexContractError, "safe directory"):
                compile_index([str(root.resolve())])

    def test_genuine_split_index_ignores_only_timestamp_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = make_repo(Path(temporary).resolve(), "split-index")
            git(root, "update-index", "--split-index")
            shared = sorted((root / ".git").glob("sharedindex.*"))
            self.assertEqual(len(shared), 1)

            before = shared_index_signatures(root / ".git")
            metadata = shared[0].stat()
            os.utime(
                shared[0],
                ns=(metadata.st_atime_ns, metadata.st_mtime_ns + 1_000_000),
            )
            after_timestamp = shared_index_signatures(root / ".git")
            self.assertEqual(after_timestamp, before)

            first = compile_index([str(root)])
            second = compile_index([str(root)])
            self.assertEqual(canonical_json(first), canonical_json(second))
            self.assertEqual(verify_document(canonical_json(first)), first)

            payload = bytearray(shared[0].read_bytes())
            payload[-1] ^= 1
            shared[0].write_bytes(payload)
            after_content = shared_index_signatures(root / ".git")
            self.assertNotEqual(after_content, after_timestamp)

    def test_fifo_inputs_fail_without_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            compiler = Path(kingdom_index.__file__).resolve()
            for folder, relative in (
                ("fifo-manifest", "kingdom.yaml"),
                ("fifo-config", ".git/config"),
                ("fifo-head", ".git/HEAD"),
            ):
                with self.subTest(relative=relative):
                    root = make_repo(parent, folder)
                    target = root / relative
                    target.unlink()
                    os.mkfifo(target, 0o600)
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(compiler),
                            "compile",
                            "--repo-root",
                            str(root),
                            "--output",
                            str(parent / f"{folder}.index.json"),
                        ],
                        env={
                            "LANG": "C",
                            "LC_ALL": "C",
                            "PYTHONDONTWRITEBYTECODE": "1",
                        },
                        capture_output=True,
                        timeout=3,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 2)
                    self.assertIn(b"must be a regular file", result.stderr)

    def test_child_output_is_bounded_during_capture(self) -> None:
        for descriptor in (1, 2):
            with self.subTest(descriptor=descriptor):
                with self.assertRaisesRegex(
                    IndexContractError, "output exceeded the bounded limit"
                ):
                    run_bounded_subprocess(
                        [
                            sys.executable,
                            "-c",
                            (
                                "import os; "
                                f"os.write({descriptor}, b'x' * 4096)"
                            ),
                        ],
                        env={"LANG": "C", "LC_ALL": "C"},
                        timeout=3,
                        maximum=64,
                        label="bounded child",
                    )

    def test_capture_setup_failure_terminates_the_started_child(self) -> None:
        process = mock.Mock()
        process.stdout = mock.Mock()
        process.stderr = mock.Mock()
        with (
            mock.patch.object(
                kingdom_index.subprocess, "Popen", return_value=process
            ),
            mock.patch.object(
                kingdom_index.selectors,
                "DefaultSelector",
                side_effect=OSError("fixture"),
            ),
            mock.patch.object(
                kingdom_index, "terminate_process_group"
            ) as terminate,
        ):
            with self.assertRaisesRegex(
                IndexContractError, "output could not be read"
            ):
                run_bounded_subprocess(
                    [sys.executable, "-c", "pass"],
                    env={"LANG": "C", "LC_ALL": "C"},
                    timeout=3,
                    maximum=64,
                    label="selector fixture",
                )
        terminate.assert_called_once_with(process)
        process.stdout.close.assert_called_once_with()
        process.stderr.close.assert_called_once_with()

    def test_timeout_kills_descendants_after_the_leader_exits(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            marker = Path(temporary).resolve() / "process-group.txt"
            script = (
                "import os, pathlib, subprocess, sys; "
                "child = subprocess.Popen("
                "[sys.executable, '-c', 'import time; time.sleep(60)']); "
                f"pathlib.Path({str(marker)!r}).write_text("
                "f'{os.getpgrp()} {child.pid}', encoding='ascii')"
            )
            process_group: int | None = None
            try:
                with self.assertRaisesRegex(IndexContractError, "timed out"):
                    run_bounded_subprocess(
                        [sys.executable, "-c", script],
                        env={"LANG": "C", "LC_ALL": "C"},
                        timeout=0.25,
                        maximum=64,
                        label="descendant fixture",
                    )
                process_group, _ = (
                    int(value)
                    for value in marker.read_text(encoding="ascii").split()
                )
                deadline = time.monotonic() + 3
                while True:
                    try:
                        os.killpg(process_group, 0)
                    except ProcessLookupError:
                        break
                    except PermissionError:
                        pass
                    if time.monotonic() >= deadline:
                        self.fail("timed-out descendant process group survived")
                    time.sleep(0.02)
            finally:
                if process_group is not None:
                    try:
                        os.killpg(process_group, signal.SIGKILL)
                    except (ProcessLookupError, PermissionError):
                        pass

    def test_shared_index_scan_bounds_all_directory_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary).resolve()
            (directory / "ordinary-control").write_text(
                "not a shared index\n", encoding="utf-8"
            )
            with mock.patch.object(
                kingdom_index, "MAX_GIT_CONTROL_ENTRIES", 0
            ):
                with self.assertRaisesRegex(
                    IndexContractError, "bounded entry count"
                ):
                    shared_index_signatures(directory)

    def test_aggregate_byte_limits_shrink_before_each_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            reference_tree = parent / "refs"
            reference_tree.mkdir()
            (reference_tree / "a").write_bytes(b"a" * 9)
            (reference_tree / "b").write_bytes(b"b" * 9)
            shared_directory = parent / "shared"
            shared_directory.mkdir()
            (shared_directory / "sharedindex.a").write_bytes(b"a" * 9)
            (shared_directory / "sharedindex.b").write_bytes(b"b" * 9)

            original = kingdom_index.git_regular_file_signature
            reference_limits: list[int] = []

            def observed_reference_limit(
                path: Path,
                label: str,
                *,
                required: bool,
                maximum: int,
            ) -> tuple[int, int, int, int, int, str] | None:
                reference_limits.append(maximum)
                return original(
                    path, label, required=required, maximum=maximum
                )

            with (
                mock.patch.object(
                    kingdom_index, "MAX_GIT_REFERENCE_BYTES", 10
                ),
                mock.patch.object(
                    kingdom_index,
                    "git_regular_file_signature",
                    observed_reference_limit,
                ),
            ):
                with self.assertRaisesRegex(
                    IndexContractError, "bounded size"
                ):
                    git_control_tree_signature(
                        reference_tree,
                        "reference fixture",
                        required=True,
                        expected_device=reference_tree.stat().st_dev,
                    )
            self.assertEqual(reference_limits, [10, 1])

            shared_limits: list[int] = []

            def observed_shared_limit(
                path: Path,
                label: str,
                *,
                required: bool,
                maximum: int,
            ) -> tuple[int, int, int, int, int, str] | None:
                shared_limits.append(maximum)
                return original(
                    path, label, required=required, maximum=maximum
                )

            with (
                mock.patch.object(
                    kingdom_index, "MAX_GIT_INDEX_BYTES", 10
                ),
                mock.patch.object(
                    kingdom_index,
                    "git_regular_file_signature",
                    observed_shared_limit,
                ),
            ):
                with self.assertRaisesRegex(
                    IndexContractError, "bounded size"
                ):
                    shared_index_signatures(shared_directory)
            self.assertEqual(shared_limits, [10, 1])

    def test_root_commit_limit_is_enforced_while_iterating(self) -> None:
        output = b"".join(
            f"{index:040x}\n".encode("ascii") for index in range(257)
        )
        with mock.patch.object(kingdom_index, "git_bytes", return_value=output):
            with self.assertRaisesRegex(
                IndexContractError, "missing or unbounded"
            ):
                bounded_root_commits(Path("/"), "HEAD", 40)

    def test_git_worktree_root_cannot_use_a_symlink_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            root = make_repo(parent, "root")
            alias = parent / "worktree-alias"
            alias.symlink_to(root, target_is_directory=True)
            original = kingdom_index.git_text

            def aliased_top(
                repository: Path,
                *args: str,
                allow_failure: bool = False,
            ) -> str:
                if args == ("rev-parse", "--show-toplevel"):
                    return str(alias)
                return original(
                    repository, *args, allow_failure=allow_failure
                )

            with mock.patch.object(kingdom_index, "git_text", aliased_top):
                with self.assertRaisesRegex(
                    IndexContractError, "explicit canonical root"
                ):
                    compile_index([str(root)])

    def test_object_entry_bound_is_enforced_during_collection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = make_repo(Path(temporary).resolve(), "root")
            objects = root / ".git" / "objects"
            original_scandir = os.scandir

            class GuardedScandir:
                def __init__(self, path: Path) -> None:
                    self.inner = original_scandir(path)
                    self.reads = 0

                def __enter__(self) -> GuardedScandir:
                    self.inner.__enter__()
                    return self

                def __exit__(self, *args: object) -> object:
                    return self.inner.__exit__(*args)

                def __iter__(self) -> GuardedScandir:
                    return self

                def __next__(self) -> os.DirEntry[str]:
                    self.reads += 1
                    if self.reads > 1:
                        raise AssertionError(
                            "entry collection exceeded the declared bound"
                        )
                    return next(self.inner)

            def guarded_scandir(path: Path) -> object:
                if Path(path) == objects:
                    return GuardedScandir(Path(path))
                return original_scandir(path)

            with (
                mock.patch.object(kingdom_index, "MAX_GIT_OBJECT_ENTRIES", 0),
                mock.patch.object(
                    kingdom_index.os, "scandir", guarded_scandir
                ),
            ):
                with self.assertRaisesRegex(
                    IndexContractError, "bounded entry count"
                ):
                    kingdom_index.object_storage_signature(root / ".git")

    def test_repository_clean_filter_is_never_executed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            root = make_repo(parent, "root")
            probe = parent / "filter-executed"
            (root / ".gitattributes").write_text(
                "identity.txt filter=auditprobe\n", encoding="utf-8"
            )
            git(root, "add", ".gitattributes")
            git(root, "commit", "-q", "-m", "attributes")
            git(
                root,
                "config",
                "filter.auditprobe.clean",
                f"touch {probe}; cat",
            )
            compile_index([str(root)])
            self.assertFalse(probe.exists())

    def test_secret_shaped_external_git_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            root = parent / "root"
            root.mkdir()
            external_git = parent / ("glpat-" + "a" * 24)
            git(root, "init", "-q", f"--separate-git-dir={external_git}")
            git(root, "config", "user.name", "Kingdom Test")
            git(root, "config", "user.email", "kingdom@example.invalid")
            (root / "kingdom.yaml").write_text(manifest_text(), encoding="utf-8")
            git(root, "add", "kingdom.yaml")
            git(root, "commit", "-q", "-m", "fixture")
            with self.assertRaises(IndexContractError):
                compile_index([str(root.resolve())])

    def test_instruction_parent_symlink_cannot_escape_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            root = make_repo(parent, "root")
            outside = parent / "outside"
            outside.mkdir()
            (outside / "copilot-instructions.md").write_text(
                "outside\n", encoding="utf-8"
            )
            (root / ".github").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(IndexContractError):
                compile_index([str(root)])

    def test_replace_refs_are_ignored_and_grafts_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = make_repo(Path(temporary).resolve(), "root")
            (root / "identity.txt").write_text("second\n", encoding="utf-8")
            git(root, "add", "identity.txt")
            git(root, "commit", "-q", "-m", "second")
            baseline = compile_index([str(root)])["repositories"][0]["git"]
            git(root, "replace", "HEAD", "HEAD^")
            replaced = compile_index([str(root)])["repositories"][0]["git"]
            self.assertEqual(replaced["head_tree"], baseline["head_tree"])
            self.assertEqual(replaced["root_commits"], baseline["root_commits"])
            grafts = root / ".git" / "info" / "grafts"
            grafts.write_text(
                f"{baseline['head']} {baseline['root_commits'][0]}\n",
                encoding="utf-8",
            )
            with self.assertRaises(IndexContractError):
                compile_index([str(root)])

    def test_source_drift_during_compilation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = make_repo(Path(temporary).resolve(), "root")
            original = kingdom_index.git_text
            head_reads = 0

            def moving_head(
                repository: Path,
                *args: str,
                allow_failure: bool = False,
            ) -> str:
                nonlocal head_reads
                value = original(
                    repository, *args, allow_failure=allow_failure
                )
                if args == ("rev-parse", "--verify", "HEAD"):
                    head_reads += 1
                    if head_reads > 1:
                        return "0" * len(value)
                return value

            with mock.patch.object(kingdom_index, "git_text", moving_head):
                with self.assertRaises(IndexContractError):
                    compile_index([str(root)])

    def test_verifier_rejects_redigested_semantic_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = make_repo(Path(temporary).resolve(), "root")
            baseline = compile_index([str(root)])
            mutations = (
                lambda record: record.__setitem__("canonical", False),
                lambda record: record["working_tree"].__setitem__(
                    "state", "clean"
                ),
                lambda record: record["manifest"]["fields"].__setitem__(
                    "purpose", "xoxb-" "123456789012-abcdefghijklmnop"
                ),
                lambda record: record["git"].__setitem__(
                    "objects_directory",
                    str(Path(record["git"]["common_directory"]) / "elsewhere"),
                ),
            )
            for mutate in mutations:
                with self.subTest(mutation=mutate):
                    document = json.loads(canonical_json(baseline))
                    mutate(document["repositories"][0])
                    with self.assertRaises(IndexContractError):
                        verify_document(redigest_index(document))

    def test_schema_is_valid_json_with_expected_id(self) -> None:
        schema = json.loads(
            (Path(__file__).parent / "index.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(schema["title"], "Kingdom repository index")
        self.assertEqual(schema["properties"]["schema"]["const"], "kingdom.index/v1")


if __name__ == "__main__":
    unittest.main()
