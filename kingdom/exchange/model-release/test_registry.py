#!/usr/bin/env python3
"""Self-contained tests for the model-release capsule registry seam."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import model_release as release_v1  # noqa: E402
import validate_registry as registry_v1  # noqa: E402


def pretty(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def raw_descriptor(raw: bytes, media_type: str) -> dict[str, Any]:
    return {
        "media_type": media_type,
        "digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "size": len(raw),
    }


def file_descriptor(path: str, raw: bytes, media_type: str) -> dict[str, Any]:
    return {"path": path, **raw_descriptor(raw, media_type)}


def media_type(path: str) -> str:
    if path.endswith(".jsonl"):
        return "application/jsonl"
    if path.endswith(".json"):
        return "application/json"
    if path.endswith(".tar"):
        return "application/x-tar"
    if path.endswith(".pem") or path.endswith(".pub"):
        return "application/x-pem-file"
    if path.endswith(".txt") or path.endswith(".md"):
        return "text/plain"
    return "application/octet-stream"


class SignedFixture:
    """Build and reseal a complete capsule entirely inside one temp directory."""

    capsule_id = "signed-fixture-v1"
    release_path = "release.json"
    profile_path = "local-profile.json"
    evaluation_path = "evaluation-attestation.json"
    evaluation_receipt_path = "receipts/evaluation-attestation.receipt.json"
    evaluation_output_path = "evidence/evaluation/results.json"
    evaluation_benchmark_paths = {
        "dataset": "evidence/evaluation/dataset.json",
        "preprocessing": "evidence/evaluation/preprocessing.txt",
        "scoring": "evidence/evaluation/scoring.json",
    }
    attestation_path = "release-signature-attestation.json"
    launch_index_path = "launch-index.json"
    launch_signature_path = "launch-index.sig"
    payload_path = "signing/release-payload.txt"
    release_signature_path = "signing/release-signature.bin"
    public_key_path = "signing/public-key.pem"
    policy_path = "signing/verifier-policy.json"

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.source = directory / "source"
        self.public = directory / "public"
        self.capsule = self.source / "capsules" / self.capsule_id
        self.private_key = directory / "private-ed25519.pem"
        self.openssl = shutil.which("openssl")
        if self.openssl is None:
            raise unittest.SkipTest("OpenSSL is required for registry tests")
        self.openssl_version = registry_v1._openssl_version(self.openssl)
        self.records: list[tuple[str, str]] = [
            (self.profile_path, "receipts/local-profile.receipt.json"),
            (self.attestation_path, "receipts/release-signature-attestation.receipt.json"),
            (self.release_path, "receipts/release.receipt.json"),
        ]
        self.records.sort()
        self.release_attestations = [self.attestation_path]
        self.profile_attestations: list[str] = []
        self._build()

    def _write(self, relative: str, raw: bytes) -> None:
        target = self.capsule / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)

    def _json(self, relative: str) -> dict[str, Any]:
        return json.loads((self.capsule / relative).read_text(encoding="utf-8"))

    def _write_json(self, relative: str, value: dict[str, Any]) -> None:
        self._write(relative, pretty(value))

    def _sign(self, message: bytes, output: Path) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        message_path = self.directory / "message-to-sign.bin"
        message_path.write_bytes(message)
        result = subprocess.run(
            [
                self.openssl,
                "pkeyutl",
                "-sign",
                "-inkey",
                str(self.private_key),
                "-rawin",
                "-in",
                str(message_path),
                "-out",
                str(output),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        message_path.unlink()
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout)

    def _receipt(self, record_path: str, receipt_path: str) -> None:
        path = self.capsule / record_path
        loaded = release_v1.read_document(path, f"test record {record_path}")
        receipt = release_v1.make_receipt(loaded.value, loaded.raw)
        self._write_json(receipt_path, receipt)

    def _build(self) -> None:
        self.capsule.mkdir(parents=True)
        self.public.mkdir(parents=True)
        shutil.copyfile(HERE / "examples" / "synthetic-release.json", self.capsule / self.release_path)
        shutil.copyfile(HERE / "examples" / "synthetic-profile.json", self.capsule / self.profile_path)
        self._write("evidence/README.md", b"Synthetic bytes for registry tests only.\n")

        generated = subprocess.run(
            [self.openssl, "genpkey", "-algorithm", "ED25519", "-out", str(self.private_key)],
            check=False,
            capture_output=True,
            text=True,
        )
        if generated.returncode != 0:
            raise RuntimeError(generated.stderr or generated.stdout)
        public_key_target = self.capsule / self.public_key_path
        public_key_target.parent.mkdir(parents=True, exist_ok=True)
        exported = subprocess.run(
            [
                self.openssl,
                "pkey",
                "-in",
                str(self.private_key),
                "-pubout",
                "-out",
                str(public_key_target),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if exported.returncode != 0:
            raise RuntimeError(exported.stderr or exported.stdout)

        release_loaded = release_v1.read_document(self.capsule / self.release_path, "test release")
        release_digest = release_v1.validate_document(release_loaded.value)
        payload = registry_v1._domain_message(registry_v1.RELEASE_DOMAIN, release_digest)
        self._write(self.payload_path, payload)
        self._sign(payload, self.capsule / self.release_signature_path)

        public_raw = public_key_target.read_bytes()
        signer_identity = "urn:kingdom:ed25519:" + hashlib.sha256(public_raw).hexdigest()
        policy = {
            "schema": registry_v1.VERIFIER_POLICY_SCHEMA,
            "algorithm": "Ed25519",
            "public_key": raw_descriptor(public_raw, "application/x-pem-file"),
            "signer_identity": signer_identity,
            "release_domain": registry_v1.RELEASE_DOMAIN,
            "launch_index_domain": registry_v1.LAUNCH_INDEX_DOMAIN,
            "signed_value": registry_v1.SIGNED_VALUE,
            "identity_claim": registry_v1.IDENTITY_CLAIM,
            "authority_claim": registry_v1.AUTHORITY_CLAIM,
            "issuer": registry_v1.ISSUER,
        }
        self._write_json(self.policy_path, policy)
        self._write_signature_attestation(release_digest, signer_identity)

        for record_path, receipt_path in self.records:
            self._receipt(record_path, receipt_path)
        self.seal()

    def _write_signature_attestation(self, release_digest: str, signer_identity: str) -> None:
        signature_raw = (self.capsule / self.release_signature_path).read_bytes()
        policy_raw = (self.capsule / self.policy_path).read_bytes()
        signature_descriptor = raw_descriptor(signature_raw, "application/octet-stream")
        policy_descriptor = raw_descriptor(policy_raw, "application/json")
        attestation = {
            "schema": release_v1.ATTESTATION_SCHEMA,
            "kind": "attestation",
            "subject": {
                "name": "Lantern Fixture 1 release bytes",
                "kind": "model-release",
                "digest": release_digest,
            },
            "predicate_type": "signature",
            "evidence_class": "curator-observed",
            "assertor": {
                "name": "Kingdom registry synthetic test",
                "identity": signer_identity,
            },
            "issued_at": "2026-08-13T01:00:00Z",
            "signature": {
                "format": "detached-signature",
                "bundle": signature_descriptor,
                "signed_digest": release_digest,
                "signer_identity": signer_identity,
                "issuer": registry_v1.ISSUER,
                "verifier_policy": policy_descriptor,
                "verifier_tool": {
                    "name": "OpenSSL",
                    "version": self.openssl_version,
                    "source_revision": f"openssl-{self.openssl_version}",
                },
                "verified_at": "2026-08-13T01:00:00Z",
                "verified": True,
                "evidence_refs": ["detached-signature", "verifier-policy"],
            },
            "evidence": [
                {
                    "id": "detached-signature",
                    "title": "Synthetic detached release signature",
                    "kind": "signature-bundle",
                    "locator": "urn:kingdom:registry-test:release-signature",
                    "revision": "signed-fixture-v1",
                    "retrieved_at": "2026-08-13T01:00:00Z",
                    "mutability": "immutable",
                    "assertor": "Kingdom registry synthetic test",
                    "content": signature_descriptor,
                },
                {
                    "id": "verifier-policy",
                    "title": "Synthetic Ed25519 verifier policy",
                    "kind": "other",
                    "locator": "urn:kingdom:registry-test:verifier-policy",
                    "revision": "signed-fixture-v1",
                    "retrieved_at": "2026-08-13T01:00:00Z",
                    "mutability": "immutable",
                    "assertor": "Kingdom registry synthetic test",
                    "content": policy_descriptor,
                },
            ],
            "non_claims": list(release_v1.ATTESTATION_NON_CLAIMS),
        }
        self._write_json(self.attestation_path, attestation)

    def refresh_signature_attestation(self) -> None:
        release = release_v1.read_document(self.capsule / self.release_path, "test release")
        release_digest = release_v1.validate_document(release.value)
        signer_identity = self._json(self.policy_path)["signer_identity"]
        self._write_signature_attestation(release_digest, signer_identity)
        receipt = dict(self.records)[self.attestation_path]
        self._receipt(self.attestation_path, receipt)

    def replace_receipt(self, record_path: str) -> None:
        self._receipt(record_path, dict(self.records)[record_path])

    def add_evaluation(self) -> None:
        output_raw = b'{"fixture_cases_passed":2,"runs":1}\n'
        output_descriptor = raw_descriptor(output_raw, "application/json")
        evaluation = json.loads(
            (HERE / "examples" / "synthetic-evaluation.json").read_text(encoding="utf-8")
        )
        evaluation["evaluation"]["artifacts"][0]["descriptor"] = output_descriptor
        evaluation["evidence"][0]["content"] = output_descriptor
        self._write(self.evaluation_output_path, output_raw)
        benchmark_raw = {
            "dataset": b'{"cases":[{"expected":"2","input":"1 + 1"}]}\n',
            "preprocessing": b"Preserve the synthetic fixture input exactly.\n",
            "scoring": b'{"method":"exact-match"}\n',
        }
        for field, raw in benchmark_raw.items():
            path = self.evaluation_benchmark_paths[field]
            evaluation["evaluation"]["benchmark"][field] = raw_descriptor(
                raw, media_type(path)
            )
            self._write(path, raw)
        self._write_json(self.evaluation_path, evaluation)
        self.records.append((self.evaluation_path, self.evaluation_receipt_path))
        self.records.sort()
        self.profile_attestations.append(self.evaluation_path)
        self._receipt(self.evaluation_path, self.evaluation_receipt_path)
        self.seal()

    def _inventory(self) -> list[dict[str, Any]]:
        excluded = {self.launch_index_path, self.launch_signature_path}
        items: list[dict[str, Any]] = []
        for path in sorted(self.capsule.rglob("*")):
            if path.is_file():
                relative = path.relative_to(self.capsule).as_posix()
                if relative not in excluded:
                    items.append(file_descriptor(relative, path.read_bytes(), media_type(relative)))
        return items

    def _launch_index(self) -> dict[str, Any]:
        return {
            "schema": registry_v1.LAUNCH_INDEX_SCHEMA,
            "capsule_id": self.capsule_id,
            "files": self._inventory(),
            "records": [
                {"path": record_path, "receipt": receipt_path}
                for record_path, receipt_path in self.records
            ],
            "profile_sets": [
                {
                    "release": self.release_path,
                    "profile": self.profile_path,
                    "attestations": list(self.profile_attestations),
                }
            ],
            "release_attestations": list(self.release_attestations),
            "release_signature": {
                "release": self.release_path,
                "attestation": self.attestation_path,
                "payload": self.payload_path,
                "signature": self.release_signature_path,
                "public_key": self.public_key_path,
                "verifier_policy": self.policy_path,
            },
            "non_claims": list(registry_v1.LAUNCH_INDEX_NON_CLAIMS),
        }

    def write_registry(self) -> None:
        launch_raw = (self.capsule / self.launch_index_path).read_bytes()
        signature_raw = (self.capsule / self.launch_signature_path).read_bytes()
        registry = {
            "schema": registry_v1.REGISTRY_SCHEMA,
            "entries": [
                {
                    "id": self.capsule_id,
                    "title": "Signed synthetic registry fixture",
                    "capsule": f"capsules/{self.capsule_id}",
                    "launch_index": file_descriptor(
                        self.launch_index_path, launch_raw, "application/json"
                    ),
                    "launch_signature": file_descriptor(
                        self.launch_signature_path, signature_raw, "application/octet-stream"
                    ),
                }
            ],
            "non_claims": list(registry_v1.REGISTRY_NON_CLAIMS),
        }
        (self.source / "registry.json").write_bytes(pretty(registry))

    def mirror(self) -> None:
        public_capsules = self.public / "capsules"
        if public_capsules.exists():
            shutil.rmtree(public_capsules)
        shutil.copytree(self.source / "capsules", public_capsules)
        shutil.copyfile(self.source / "registry.json", self.public / "registry.json")

    def seal(self, *, sign_launch: bool = True, mirror: bool = True) -> None:
        launch_raw = pretty(self._launch_index())
        self._write(self.launch_index_path, launch_raw)
        if sign_launch:
            message = registry_v1._domain_message(
                registry_v1.LAUNCH_INDEX_DOMAIN,
                "sha256:" + hashlib.sha256(launch_raw).hexdigest(),
            )
            self._sign(message, self.capsule / self.launch_signature_path)
        self.write_registry()
        if mirror:
            self.mirror()

    def replace_indexed_media_type(self, path: str, replacement: str) -> None:
        index = self._json(self.launch_index_path)
        item = next(value for value in index["files"] if value["path"] == path)
        item["media_type"] = replacement
        launch_raw = pretty(index)
        self._write(self.launch_index_path, launch_raw)
        message = registry_v1._domain_message(
            registry_v1.LAUNCH_INDEX_DOMAIN,
            "sha256:" + hashlib.sha256(launch_raw).hexdigest(),
        )
        self._sign(message, self.capsule / self.launch_signature_path)
        self.write_registry()
        self.mirror()


class WitnessFixture:
    """Add one signed, archive-backed witness capsule to ``SignedFixture``."""

    capsule_id = "witness-fixture-v1"
    index_path = "witness-index.json"
    signature_path = "witness-index.sig"
    profile_path = "ubuntu-x64-profile.json"
    evaluation_path = "evaluation-attestation.json"
    profile_receipt_path = "receipts/ubuntu-x64-profile.receipt.json"
    evaluation_receipt_path = "receipts/evaluation-attestation.receipt.json"
    archive_path = "evidence/provenance/qwen3-ubuntu-witness.tar"
    bundle_path = "evidence/provenance/github-attestation-bundle.jsonl"
    root_path = "evidence/provenance/github-trusted-root.jsonl"
    public_key_path = "signing/public-key.pub"
    policy_path = "signing/verifier-policy.json"
    member_names = sorted(
        [
            "benchmark-dataset.json",
            "benchmark-preprocessing.txt",
            "benchmark-scoring.json",
            "evidence-manifest.json",
            "nonthinking-result.json",
            "public-probe.json",
            "run-summary.json",
            "run_qwen_probe.py",
            "runtime-manifest.json",
            "snapshot-byte-manifest.json",
            "wheel-lock.txt",
        ]
    )

    def __init__(self, base: SignedFixture) -> None:
        self.base = base
        self.source = base.source
        self.public = base.public
        self.directory = base.directory
        self.capsule = self.source / "capsules" / self.capsule_id
        self.private_key = self.directory / "witness-private-ed25519.pem"
        self.openssl = base.openssl
        self.member_raw = {
            name: (f"Synthetic witness bytes for {name}.\n").encode("utf-8")
            for name in self.member_names
        }
        self._build()

    def _write(self, relative: str, raw: bytes) -> None:
        target = self.capsule / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)

    def _write_json(self, relative: str, value: dict[str, Any]) -> None:
        self._write(relative, pretty(value))

    def _json(self, relative: str) -> dict[str, Any]:
        return json.loads((self.capsule / relative).read_text(encoding="utf-8"))

    def _sign(self, message: bytes, output: Path, key: Path | None = None) -> None:
        message_path = self.directory / "witness-message-to-sign.bin"
        message_path.write_bytes(message)
        result = subprocess.run(
            [
                self.openssl,
                "pkeyutl",
                "-sign",
                "-inkey",
                str(key or self.private_key),
                "-rawin",
                "-in",
                str(message_path),
                "-out",
                str(output),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        message_path.unlink()
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout)

    def _receipt(self, record_path: str, receipt_path: str) -> None:
        loaded = release_v1.read_document(self.capsule / record_path, f"test {record_path}")
        self._write_json(receipt_path, release_v1.make_receipt(loaded.value, loaded.raw))

    def _build_archive(self, *, omit: str | None = None, mismatch: str | None = None) -> None:
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w", format=tarfile.GNU_FORMAT) as handle:
            root = tarfile.TarInfo(".")
            root.type = tarfile.DIRTYPE
            root.mode = 0o755
            root.uid = root.gid = root.mtime = 0
            root.uname = root.gname = ""
            handle.addfile(root)
            for name in self.member_names:
                if name == omit:
                    continue
                raw = self.member_raw[name]
                if name == mismatch:
                    raw += b"mismatched archive-only byte\n"
                item = tarfile.TarInfo(f"./{name}")
                item.type = tarfile.REGTYPE
                item.mode = 0o644
                item.uid = item.gid = item.mtime = 0
                item.uname = item.gname = ""
                item.size = len(raw)
                handle.addfile(item, io.BytesIO(raw))
        self._write(self.archive_path, buffer.getvalue())

    def _build(self) -> None:
        self.capsule.mkdir(parents=True)
        generated = subprocess.run(
            [self.openssl, "genpkey", "-algorithm", "ED25519", "-out", str(self.private_key)],
            check=False,
            capture_output=True,
            text=True,
        )
        if generated.returncode != 0:
            raise RuntimeError(generated.stderr or generated.stdout)
        public_target = self.capsule / self.public_key_path
        public_target.parent.mkdir(parents=True)
        exported = subprocess.run(
            [
                self.openssl,
                "pkey",
                "-in",
                str(self.private_key),
                "-pubout",
                "-out",
                str(public_target),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if exported.returncode != 0:
            raise RuntimeError(exported.stderr or exported.stdout)

        release_loaded = release_v1.read_document(
            self.base.capsule / self.base.release_path, "witness fixture base release"
        )
        release_digest = release_v1.validate_document(release_loaded.value)
        profile = json.loads((HERE / "examples" / "synthetic-profile.json").read_text())
        profile["backend"]["provider"] = "KINGDOM workflow on a GitHub-hosted runner"
        profile["hardware"]["visibility"] = "observed"
        profile["subject"]["release_digest"] = release_digest
        self._write_json(self.profile_path, profile)
        profile_loaded = release_v1.read_document(self.capsule / self.profile_path, "witness profile")
        profile_digest = release_v1.validate_document(profile_loaded.value)

        for name, raw in self.member_raw.items():
            self._write(f"evidence/execution/{name}", raw)
        evaluation = json.loads((HERE / "examples" / "synthetic-evaluation.json").read_text())
        evaluation["subject"]["digest"] = profile_digest
        evaluation["evaluation"]["release_digest"] = release_digest
        evaluation["evaluation"]["execution_profile_digest"] = profile_digest
        result_raw = self.member_raw["nonthinking-result.json"]
        result_descriptor = raw_descriptor(result_raw, "application/json")
        evaluation["evaluation"]["artifacts"] = [
            {
                "name": "nonthinking-result.json",
                "role": "evaluation-results",
                "descriptor": result_descriptor,
                "evidence_ref": "fixture-evaluation-output",
            }
        ]
        evaluation["evidence"][0]["content"] = result_descriptor
        for field, name in {
            "dataset": "benchmark-dataset.json",
            "preprocessing": "benchmark-preprocessing.txt",
            "scoring": "benchmark-scoring.json",
        }.items():
            evaluation["evaluation"]["benchmark"][field] = raw_descriptor(
                self.member_raw[name], media_type(name)
            )
        self._write_json(self.evaluation_path, evaluation)
        self._receipt(self.profile_path, self.profile_receipt_path)
        self._receipt(self.evaluation_path, self.evaluation_receipt_path)
        self._write(self.bundle_path, b'{}\n')
        self._write(self.root_path, b'{"synthetic":"trusted-root"}\n')
        self._write(
            "evidence/provenance/offline-verification-receipt.json",
            b'{"fixture":"offline-verification"}\n',
        )
        self._write(
            "evidence/provenance/prior-attempt-failure-receipt.json",
            b'{"fixture":"prior-failure"}\n',
        )
        self._build_archive()
        self._write("README.md", b"Synthetic witness fixture.\n")

        public_raw = public_target.read_bytes()
        policy = {
            "schema": registry_v1.WITNESS_VERIFIER_POLICY_SCHEMA,
            "algorithm": "Ed25519",
            "public_key": raw_descriptor(public_raw, "application/x-pem-file"),
            "signer_identity": "urn:kingdom:ed25519:" + hashlib.sha256(public_raw).hexdigest(),
            "witness_index_domain": registry_v1.WITNESS_INDEX_DOMAIN,
            "signed_value": registry_v1.SIGNED_VALUE,
            "identity_claim": registry_v1.WITNESS_IDENTITY_CLAIM,
            "authority_claim": registry_v1.AUTHORITY_CLAIM,
            "issuer": registry_v1.ISSUER,
        }
        self._write_json(self.policy_path, policy)
        self.seal()

    def _inventory(self) -> list[dict[str, Any]]:
        excluded = {self.index_path, self.signature_path}
        return [
            file_descriptor(
                path.relative_to(self.capsule).as_posix(),
                path.read_bytes(),
                media_type(path.name),
            )
            for path in sorted(self.capsule.rglob("*"))
            if path.is_file() and path.relative_to(self.capsule).as_posix() not in excluded
        ]

    def _index(self) -> dict[str, Any]:
        base_launch_raw = (self.base.capsule / self.base.launch_index_path).read_bytes()
        base_release = release_v1.read_document(
            self.base.capsule / self.base.release_path, "witness fixture base release"
        )
        return {
            "schema": registry_v1.WITNESS_INDEX_SCHEMA,
            "capsule_id": self.capsule_id,
            "base_release": {
                "capsule_id": self.base.capsule_id,
                "launch_index_digest": "sha256:" + hashlib.sha256(base_launch_raw).hexdigest(),
                "release_path": self.base.release_path,
                "release_canonical_digest": release_v1.validate_document(base_release.value),
            },
            "files": self._inventory(),
            "records": [
                {"path": self.evaluation_path, "receipt": self.evaluation_receipt_path},
                {"path": self.profile_path, "receipt": self.profile_receipt_path},
            ],
            "profile_sets": [
                {"profile": self.profile_path, "attestations": [self.evaluation_path]}
            ],
            "archive_evidence": {
                "archive": self.archive_path,
                "members": [
                    {"member": name, "path": f"evidence/execution/{name}"}
                    for name in self.member_names
                ],
            },
            "github_attestation": {
                "artifact": self.archive_path,
                "bundle": self.bundle_path,
                "trusted_root": self.root_path,
                "repository": "fixture/example",
                "signer_workflow": "fixture/example/.github/workflows/qwen3-ubuntu-witness.yml",
                "source_digest": "b" * 40,
                "source_ref": "refs/heads/research/witness-fixture",
                "run_id": "123456789",
                "run_attempt": 1,
                "predicate_type": registry_v1.SLSA_PROVENANCE_V1,
                "runner_environment": "github-hosted",
                "verifier": {
                    "name": "gh",
                    "minimum_version": registry_v1.GH_ATTESTATION_MINIMUM_VERSION,
                    "source_revision": registry_v1.GH_ATTESTATION_SOURCE_REVISION,
                },
            },
            "witness_signature": {
                "public_key": self.public_key_path,
                "verifier_policy": self.policy_path,
            },
            "non_claims": list(registry_v1.WITNESS_INDEX_NON_CLAIMS),
        }

    def _write_registry(self) -> None:
        registry_path = self.source / "registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["entries"] = [
            entry for entry in registry["entries"] if entry["id"] != self.capsule_id
        ]
        index_raw = (self.capsule / self.index_path).read_bytes()
        signature_raw = (self.capsule / self.signature_path).read_bytes()
        registry["entries"].append(
            {
                "id": self.capsule_id,
                "title": "Synthetic GitHub-hosted witness fixture",
                "capsule": f"capsules/{self.capsule_id}",
                "launch_index": file_descriptor(self.index_path, index_raw, "application/json"),
                "launch_signature": file_descriptor(
                    self.signature_path, signature_raw, "application/octet-stream"
                ),
            }
        )
        registry["entries"].sort(key=lambda entry: entry["id"])
        registry_path.write_bytes(pretty(registry))

    def mirror(self) -> None:
        public_capsules = self.public / "capsules"
        if public_capsules.exists():
            shutil.rmtree(public_capsules)
        shutil.copytree(self.source / "capsules", public_capsules)
        shutil.copyfile(self.source / "registry.json", self.public / "registry.json")

    def seal(self, *, key: Path | None = None) -> None:
        index_raw = pretty(self._index())
        self._write(self.index_path, index_raw)
        self._sign(
            registry_v1._domain_message(
                registry_v1.WITNESS_INDEX_DOMAIN,
                "sha256:" + hashlib.sha256(index_raw).hexdigest(),
            ),
            self.capsule / self.signature_path,
            key,
        )
        self._write_registry()
        self.mirror()

    def mutate_index(self, transform: Any, *, key: Path | None = None) -> None:
        index = self._json(self.index_path)
        transform(index)
        index_raw = pretty(index)
        self._write(self.index_path, index_raw)
        self._sign(
            registry_v1._domain_message(
                registry_v1.WITNESS_INDEX_DOMAIN,
                "sha256:" + hashlib.sha256(index_raw).hexdigest(),
            ),
            self.capsule / self.signature_path,
            key,
        )
        self._write_registry()
        self.mirror()


class RegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="kingdom-registry-test-")
        self.root = Path(self.temporary.name)
        self.fixture = SignedFixture(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def assert_rejected(self, pattern: str, *, public: bool = False) -> None:
        with self.assertRaisesRegex(registry_v1.RegistryError, pattern):
            registry_v1.validate_registry(
                self.fixture.source,
                self.fixture.public if public else None,
            )

    def test_valid_source_and_public_mirror(self) -> None:
        result = registry_v1.validate_registry(self.fixture.source, self.fixture.public)
        self.assertEqual(result["capsules"], 1)
        self.assertEqual(result["records"], 3)
        self.assertEqual(result["crypto_checks"], 2)
        self.assertTrue(result["public"])

    def test_captured_json_evidence_may_contain_floats(self) -> None:
        self.fixture._write("evidence/publisher-config.json", b'{"epsilon": 0.00001}\n')
        self.fixture.seal()
        result = registry_v1.validate_registry(self.fixture.source, self.fixture.public)
        self.assertEqual(result["capsules"], 1)

    def test_captured_json_evidence_may_have_non_string_schema(self) -> None:
        self.fixture._write("evidence/publisher-schema.json", b'{"schema": []}\n')
        self.fixture.seal()
        result = registry_v1.validate_registry(self.fixture.source, self.fixture.public)
        self.assertEqual(result["capsules"], 1)

    def test_publisher_inventory_checks_source_descriptor_and_summary(self) -> None:
        source_raw = b'{"publisher":"fixture"}\n'
        inventory = {
            "schema": registry_v1.PUBLISHER_INVENTORY_SCHEMA,
            "publisher": "Fixture Publisher",
            "repository": "fixture/model",
            "revision": "a" * 40,
            "revision_timestamp": "2026-08-13T00:00:00Z",
            "retrieved_at": "2026-08-13T01:00:00Z",
            "source": "https://example.test/api/model/revision/" + "a" * 40,
            "source_descriptor": raw_descriptor(source_raw, "application/json"),
            "summary": {
                "file_count": 1,
                "total_bytes": 8,
                "weight_shards": 1,
                "weight_bytes": 8,
            },
            "files": [
                {
                    "path": "model-00001-of-000001.safetensors",
                    "size": 8,
                    "repository_object": "sha1:" + "b" * 40,
                    "published_content": {
                        "digest": "sha256:" + "c" * 64,
                        "size": 8,
                    },
                    "pointer_size": 128,
                }
            ],
        }
        registry_v1._validate_publisher_inventory(inventory, "test inventory")
        inventory["files"][0]["path"] = "model.safetensors"
        registry_v1._validate_publisher_inventory(inventory, "test single-file inventory")
        inventory["summary"]["weight_bytes"] = 9
        with self.assertRaisesRegex(registry_v1.RegistryError, "summary differs"):
            registry_v1._validate_publisher_inventory(inventory, "test inventory")
        inventory["summary"]["weight_bytes"] = True
        with self.assertRaisesRegex(registry_v1.RegistryError, "summary values must be integers"):
            registry_v1._validate_publisher_inventory(inventory, "test inventory")
        inventory["summary"] = {
            "file_count": 2,
            "total_bytes": 16,
            "weight_shards": 2,
            "weight_bytes": 16,
        }
        inventory["files"].append(
            {**inventory["files"][0], "path": "model-00001-of-000001.safetensors"}
        )
        inventory["files"].sort(key=lambda row: row["path"])
        with self.assertRaisesRegex(registry_v1.RegistryError, "must not mix"):
            registry_v1._validate_publisher_inventory(inventory, "test mixed inventory")

    def test_registry_rejects_traversal(self) -> None:
        registry = json.loads((self.fixture.source / "registry.json").read_text(encoding="utf-8"))
        registry["entries"][0]["capsule"] = "../outside"
        (self.fixture.source / "registry.json").write_bytes(pretty(registry))
        self.assert_rejected("traversal-free")

    @unittest.skipIf(os.name == "nt", "symlink semantics differ on Windows")
    def test_capsule_rejects_symlink(self) -> None:
        target = self.fixture.capsule / "evidence" / "README.md"
        target.unlink()
        target.symlink_to(self.fixture.private_key)
        self.assert_rejected("symlink")

    def test_capsule_rejects_missing_file(self) -> None:
        (self.fixture.capsule / "evidence" / "README.md").unlink()
        self.assert_rejected("cannot inspect")

    def test_capsule_rejects_extra_file(self) -> None:
        self.fixture._write("unregistered.txt", b"not in launch index\n")
        self.assert_rejected("file inventory differs")

    def test_capsule_rejects_case_fold_collision_with_launch_control(self) -> None:
        registry = json.loads((self.fixture.source / "registry.json").read_text(encoding="utf-8"))
        registry["entries"][0]["launch_signature"]["path"] = "LAUNCH-INDEX.JSON"
        (self.fixture.source / "registry.json").write_bytes(pretty(registry))
        self.assert_rejected("control paths collide when case-folded")

    def test_raw_descriptor_tamper_is_rejected(self) -> None:
        target = self.fixture.capsule / "evidence" / "README.md"
        target.write_bytes(b"Tampered bytes for registry tests only.\n")
        self.assert_rejected("raw descriptor differs")

    def test_exact_receipt_mismatch_is_rejected_after_reseal(self) -> None:
        profile = self.fixture._json(self.fixture.profile_path)
        profile["determinism"]["known_nondeterminism"] = ["A valid but changed declaration."]
        self.fixture._write_json(self.fixture.profile_path, profile)
        self.fixture.seal()
        self.assert_rejected("receipt does not match")

    def test_release_profile_binding_is_checked_after_valid_receipt(self) -> None:
        profile = self.fixture._json(self.fixture.profile_path)
        profile["subject"]["release_digest"] = "sha256:" + "f" * 64
        self.fixture._write_json(self.fixture.profile_path, profile)
        self.fixture.replace_receipt(self.fixture.profile_path)
        self.fixture.seal()
        self.assert_rejected("release/profile binding failed")

    def test_evaluation_descriptors_match_one_indexed_raw_file(self) -> None:
        self.fixture.add_evaluation()
        result = registry_v1.validate_registry(self.fixture.source, self.fixture.public)
        self.assertEqual(result["records"], 4)

    def test_evaluation_artifact_rejects_absent_raw_file(self) -> None:
        self.fixture.add_evaluation()
        (self.fixture.capsule / self.fixture.evaluation_output_path).unlink()
        self.fixture.seal()
        self.assert_rejected("evaluation artifact .* must match exactly one indexed raw file")

    def test_evaluation_artifact_rejects_wrong_indexed_media_type(self) -> None:
        self.fixture.add_evaluation()
        self.fixture.replace_indexed_media_type(
            self.fixture.evaluation_output_path, "application/octet-stream"
        )
        self.assert_rejected("evaluation artifact .* must match exactly one indexed raw file")

    def test_evaluation_artifact_rejects_duplicate_indexed_raw_files(self) -> None:
        self.fixture.add_evaluation()
        shutil.copyfile(
            self.fixture.capsule / self.fixture.evaluation_output_path,
            self.fixture.capsule / "evidence/evaluation/results-copy.json",
        )
        self.fixture.seal()
        self.assert_rejected("evaluation artifact .* must match exactly one indexed raw file")

    def test_evaluation_benchmark_rejects_absent_raw_file(self) -> None:
        self.fixture.add_evaluation()
        dataset = self.fixture.evaluation_benchmark_paths["dataset"]
        (self.fixture.capsule / dataset).unlink()
        self.fixture.seal()
        self.assert_rejected(
            "evaluation benchmark dataset must match exactly one indexed raw file"
        )

    def test_evaluation_benchmark_rejects_wrong_indexed_media_type(self) -> None:
        self.fixture.add_evaluation()
        preprocessing = self.fixture.evaluation_benchmark_paths["preprocessing"]
        self.fixture.replace_indexed_media_type(preprocessing, "application/octet-stream")
        self.assert_rejected(
            "evaluation benchmark preprocessing must match exactly one indexed raw file"
        )

    def test_evaluation_benchmark_rejects_duplicate_indexed_raw_files(self) -> None:
        self.fixture.add_evaluation()
        scoring = self.fixture.evaluation_benchmark_paths["scoring"]
        shutil.copyfile(
            self.fixture.capsule / scoring,
            self.fixture.capsule / "evidence/evaluation/scoring-copy.json",
        )
        self.fixture.seal()
        self.assert_rejected(
            "evaluation benchmark scoring must match exactly one indexed raw file"
        )

    def test_evaluation_artifacts_reject_path_aliasing(self) -> None:
        self.fixture.add_evaluation()
        evaluation = self.fixture._json(self.fixture.evaluation_path)
        artifact = dict(evaluation["evaluation"]["artifacts"][0])
        artifact["name"] = "aliased-results.json"
        evaluation["evaluation"]["artifacts"].append(artifact)
        self.fixture._write_json(self.fixture.evaluation_path, evaluation)
        self.fixture.replace_receipt(self.fixture.evaluation_path)
        self.fixture.seal()
        self.assert_rejected("evaluation artifacts must resolve to path-unique indexed files")

    def test_evaluation_benchmark_rejects_role_path_aliasing(self) -> None:
        self.fixture.add_evaluation()
        evaluation = self.fixture._json(self.fixture.evaluation_path)
        benchmark = evaluation["evaluation"]["benchmark"]
        benchmark["preprocessing"] = dict(benchmark["dataset"])
        self.fixture._write_json(self.fixture.evaluation_path, evaluation)
        self.fixture.replace_receipt(self.fixture.evaluation_path)
        self.fixture.seal()
        self.assert_rejected("benchmark dataset, preprocessing, and scoring must resolve to distinct")

    def test_evaluation_benchmark_rejects_artifact_path_aliasing(self) -> None:
        self.fixture.add_evaluation()
        evaluation = self.fixture._json(self.fixture.evaluation_path)
        artifact = evaluation["evaluation"]["artifacts"][0]
        evaluation["evaluation"]["benchmark"]["dataset"] = dict(artifact["descriptor"])
        self.fixture._write_json(self.fixture.evaluation_path, evaluation)
        self.fixture.replace_receipt(self.fixture.evaluation_path)
        self.fixture.seal()
        self.assert_rejected("benchmark paths must be disjoint from artifact paths")

    def test_resealed_invalid_release_signature_reaches_crypto_check(self) -> None:
        signature_path = self.fixture.capsule / self.fixture.release_signature_path
        signature = bytearray(signature_path.read_bytes())
        signature[0] ^= 1
        signature_path.write_bytes(bytes(signature))
        self.fixture.refresh_signature_attestation()
        self.fixture.seal()
        self.assert_rejected("release Ed25519 signature is invalid")

    def test_resealed_invalid_launch_signature_reaches_crypto_check(self) -> None:
        signature_path = self.fixture.capsule / self.fixture.launch_signature_path
        signature = bytearray(signature_path.read_bytes())
        signature[-1] ^= 1
        signature_path.write_bytes(bytes(signature))
        self.fixture.write_registry()
        self.assert_rejected("launch index Ed25519 signature is invalid")

    def test_release_signature_role_media_type_is_enforced(self) -> None:
        index = self.fixture._json(self.fixture.launch_index_path)
        for item in index["files"]:
            if item["path"] == self.fixture.public_key_path:
                item["media_type"] = "application/octet-stream"
                break
        launch_raw = pretty(index)
        self.fixture._write(self.fixture.launch_index_path, launch_raw)
        message = registry_v1._domain_message(
            registry_v1.LAUNCH_INDEX_DOMAIN,
            "sha256:" + hashlib.sha256(launch_raw).hexdigest(),
        )
        self.fixture._sign(message, self.fixture.capsule / self.fixture.launch_signature_path)
        self.fixture.write_registry()
        self.fixture.mirror()
        self.assert_rejected("release signature public_key must use application/x-pem-file")

    def test_unenumerated_v1_record_is_rejected_even_when_hashed(self) -> None:
        shutil.copyfile(
            self.fixture.capsule / self.fixture.profile_path,
            self.fixture.capsule / "unindexed-profile.json",
        )
        self.fixture.seal()
        self.assert_rejected("v1 record enumeration differs")

    def test_unenumerated_v1_record_cannot_hide_as_binary(self) -> None:
        shutil.copyfile(
            self.fixture.capsule / self.fixture.profile_path,
            self.fixture.capsule / "hidden-v1-record.bin",
        )
        self.fixture.seal()
        self.assert_rejected("v1 record enumeration differs")

    def test_public_mirror_byte_difference_is_rejected(self) -> None:
        target = self.fixture.public / "capsules" / self.fixture.capsule_id / "evidence" / "README.md"
        target.write_bytes(b"public bytes differ\n")
        self.assert_rejected("public mirror bytes differ", public=True)

    def test_public_mirror_extra_capsule_file_is_rejected(self) -> None:
        target = self.fixture.public / "capsules" / self.fixture.capsule_id / "extra.txt"
        target.write_bytes(b"extra\n")
        self.assert_rejected("public .* file set differs", public=True)


class WitnessRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="kingdom-witness-registry-test-")
        self.root = Path(self.temporary.name)
        self.base = SignedFixture(self.root)
        self.fixture = WitnessFixture(self.base)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def validate(self, *, public: bool = True) -> dict[str, int | bool]:
        with mock.patch.object(registry_v1, "_verify_github_attestation") as verifier:
            result = registry_v1.validate_registry(
                self.fixture.source, self.fixture.public if public else None
            )
        verifier.assert_called_once()
        return result

    def assert_rejected(self, pattern: str, *, patch_github: bool = True) -> None:
        context = (
            mock.patch.object(registry_v1, "_verify_github_attestation")
            if patch_github
            else mock.patch.object(registry_v1, "_gh_version", return_value="2.86.0")
        )
        with context:
            with self.assertRaisesRegex(registry_v1.RegistryError, pattern):
                registry_v1.validate_registry(self.fixture.source, self.fixture.public)

    def test_valid_legacy_and_witness_capsules_pass_without_mutating_legacy_bytes(self) -> None:
        base_index_before = (self.base.capsule / self.base.launch_index_path).read_bytes()
        base_signature_before = (self.base.capsule / self.base.launch_signature_path).read_bytes()
        result = self.validate()
        self.assertEqual(result["capsules"], 2)
        self.assertEqual(result["records"], 5)
        self.assertEqual(result["crypto_checks"], 4)
        self.assertEqual(
            (self.base.capsule / self.base.launch_index_path).read_bytes(), base_index_before
        )
        self.assertEqual(
            (self.base.capsule / self.base.launch_signature_path).read_bytes(),
            base_signature_before,
        )

    def test_wrong_base_anchor_and_launch_digest_are_rejected(self) -> None:
        self.fixture.mutate_index(
            lambda index: index["base_release"].__setitem__("capsule_id", "missing-base")
        )
        self.assert_rejected("base release must name another registered capsule")

    def test_wrong_base_launch_digest_is_rejected(self) -> None:
        self.fixture.mutate_index(
            lambda index: index["base_release"].__setitem__(
                "launch_index_digest", "sha256:" + "f" * 64
            )
        )
        self.assert_rejected("base launch-index digest differs from registry")

    def test_reused_task_key_is_rejected_after_valid_reseal(self) -> None:
        base_public = (self.base.capsule / self.base.public_key_path).read_bytes()
        self.fixture._write(self.fixture.public_key_path, base_public)
        policy = self.fixture._json(self.fixture.policy_path)
        policy["public_key"] = raw_descriptor(base_public, "application/x-pem-file")
        policy["signer_identity"] = (
            "urn:kingdom:ed25519:" + hashlib.sha256(base_public).hexdigest()
        )
        self.fixture._write_json(self.fixture.policy_path, policy)
        self.fixture.seal(key=self.base.private_key)
        self.assert_rejected("reuses a task signing key")

    def test_missing_tar_member_is_rejected_after_valid_reseal(self) -> None:
        self.fixture._build_archive(omit=self.fixture.member_names[0])
        self.fixture.seal()
        self.assert_rejected("members differ from the sorted witness mapping")

    def test_mismatched_tar_member_is_rejected_after_valid_reseal(self) -> None:
        self.fixture._build_archive(mismatch=self.fixture.member_names[0])
        self.fixture.seal()
        self.assert_rejected("member bytes differ from indexed extracted evidence")

    def test_stale_witness_receipt_is_rejected(self) -> None:
        profile = self.fixture._json(self.fixture.profile_path)
        profile["determinism"]["known_nondeterminism"].append("Resealed fixture mutation.")
        self.fixture._write_json(self.fixture.profile_path, profile)
        self.fixture.seal()
        self.assert_rejected("receipt does not match")

    def test_evaluation_binding_is_checked_after_receipt_refresh(self) -> None:
        evaluation = self.fixture._json(self.fixture.evaluation_path)
        evaluation["evaluation"]["release_digest"] = "sha256:" + "f" * 64
        self.fixture._write_json(self.fixture.evaluation_path, evaluation)
        self.fixture._receipt(self.fixture.evaluation_path, self.fixture.evaluation_receipt_path)
        self.fixture.seal()
        self.assert_rejected("base/profile/evaluation binding failed")

    def test_evaluation_artifact_and_benchmark_descriptors_require_unique_raw_files(self) -> None:
        result_raw = self.fixture.member_raw["nonthinking-result.json"]
        self.fixture._write("evidence/duplicate-result.json", result_raw)
        self.fixture.seal()
        self.assert_rejected("evaluation artifact nonthinking-result.json must match exactly one")

    def test_evaluation_benchmark_descriptor_requires_one_unique_raw_file(self) -> None:
        dataset_raw = self.fixture.member_raw["benchmark-dataset.json"]
        self.fixture._write("evidence/duplicate-dataset.json", dataset_raw)
        self.fixture.seal()
        self.assert_rejected("evaluation benchmark dataset must match exactly one")

    def test_github_policy_rejects_non_branch_source_ref_before_verification(self) -> None:
        self.fixture.mutate_index(
            lambda index: index["github_attestation"].__setitem__(
                "source_ref", "refs/tags/unreviewed"
            )
        )
        root_digest = (self.fixture.capsule / self.fixture.root_path).read_bytes()
        with mock.patch.object(
            registry_v1,
            "GH_TRUSTED_ROOT_DIGEST",
            "sha256:" + hashlib.sha256(root_digest).hexdigest(),
        ), mock.patch.object(registry_v1, "_gh_version", return_value="2.86.0"):
            with self.assertRaisesRegex(registry_v1.RegistryError, "full branch ref"):
                registry_v1.validate_registry(self.fixture.source, self.fixture.public)

    def test_github_policy_rejects_self_hosted_runner_declaration(self) -> None:
        self.fixture.mutate_index(
            lambda index: index["github_attestation"].__setitem__(
                "runner_environment", "self-hosted"
            )
        )
        root_raw = (self.fixture.capsule / self.fixture.root_path).read_bytes()
        with mock.patch.object(
            registry_v1,
            "GH_TRUSTED_ROOT_DIGEST",
            "sha256:" + hashlib.sha256(root_raw).hexdigest(),
        ), mock.patch.object(registry_v1, "_gh_version", return_value="2.86.0"):
            with self.assertRaisesRegex(registry_v1.RegistryError, "must be github-hosted"):
                registry_v1.validate_registry(self.fixture.source, self.fixture.public)

    def test_offline_github_verification_failure_is_rejected(self) -> None:
        with mock.patch.object(
            registry_v1,
            "_verify_github_attestation",
            side_effect=registry_v1.RegistryError(
                "synthetic offline gh verification failed"
            ),
        ):
            with self.assertRaisesRegex(registry_v1.RegistryError, "offline gh verification failed"):
                registry_v1.validate_registry(self.fixture.source, self.fixture.public)

    def test_witness_index_rejects_floats_and_path_traversal(self) -> None:
        self.fixture.mutate_index(
            lambda index: index["github_attestation"].__setitem__("run_attempt", 1.5)
        )
        self.assert_rejected("floating-point JSON")

    def test_witness_index_rejects_base_path_traversal(self) -> None:
        self.fixture.mutate_index(
            lambda index: index["base_release"].__setitem__(
                "release_path", "../signed-fixture-v1/release.json"
            )
        )
        self.assert_rejected("traversal-free")


class GitHubIdentityCompatibilityTests(unittest.TestCase):
    workflow = "fixture/example/.github/workflows/qwen3-ubuntu-witness.yml"

    @staticmethod
    def identity(regexp: str) -> dict[str, Any]:
        return {
            "subjectAlternativeName": {"subjectAlternativeName": "", "regexp": regexp},
            "issuer": {"issuer": "", "regexp": ".*"},
            "runnerEnvironment": "github-hosted",
        }

    def test_reviewed_gh_san_regex_spellings_are_accepted(self) -> None:
        legacy = f"^https://github.com/{self.workflow}"
        registry_v1._validate_gh_verified_identity(
            self.identity(legacy), self.workflow, "synthetic GitHub attestation"
        )
        registry_v1._validate_gh_verified_identity(
            self.identity(legacy.replace(".", r"\.")),
            self.workflow,
            "synthetic GitHub attestation",
        )

    def test_broader_or_different_gh_identity_is_rejected(self) -> None:
        for regexp in (
            "^https://github.com/.+",
            "^https://github\\.com/fixture/other/\\.github/workflows/qwen3-ubuntu-witness\\.yml",
        ):
            with self.subTest(regexp=regexp), self.assertRaisesRegex(
                registry_v1.RegistryError, "verified identity constraints differ"
            ):
                registry_v1._validate_gh_verified_identity(
                    self.identity(regexp), self.workflow, "synthetic GitHub attestation"
                )


class GitHubProcessIsolationTests(unittest.TestCase):
    def test_version_and_attestation_use_only_disposable_state_roots(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kingdom-fake-gh-isolation-") as directory:
            root = Path(directory)
            audit = root / "fake-gh-audit.jsonl"
            fake_gh = root / "gh"
            checkout = root / "checkout"
            checkout.mkdir()
            state_variables = (
                "HOME",
                "GH_CONFIG_DIR",
                "XDG_CONFIG_HOME",
                "XDG_STATE_HOME",
                "XDG_DATA_HOME",
                "XDG_CACHE_HOME",
            )
            ambient_paths = {
                name: root / "ambient" / name.lower().replace("_", "-")
                for name in state_variables
            }
            fake_gh.write_text(
                f"""#!{sys.executable}
import json
import os
import pathlib
import sys

audit = pathlib.Path({str(audit)!r})
command = sys.argv[1] if len(sys.argv) > 1 else "missing"
state_names = {state_variables!r}
paths = {{name: os.environ[name] for name in state_names}}
for name, value in paths.items():
    target = pathlib.Path(value)
    target.mkdir(parents=True, exist_ok=True)
    (target / ("fake-gh-" + command + ".marker")).write_text("isolated\\n")
record = {{
    "command": command,
    "paths": paths,
    "controls": {{name: os.environ.get(name) for name in (
        "GH_PROMPT_DISABLED", "GIT_TERMINAL_PROMPT", "GH_TELEMETRY",
        "DO_NOT_TRACK", "GH_NO_UPDATE_NOTIFIER", "HTTP_PROXY", "HTTPS_PROXY",
        "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy", "no_proxy",
    )}},
}}
with audit.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(record, sort_keys=True) + "\\n")
if command == "version":
    print("gh version 2.96.0 (synthetic)")
else:
    print("[]")
""",
                encoding="utf-8",
            )
            fake_gh.chmod(0o755)

            artifact_path = root / "artifact.tar"
            bundle_path = root / "bundle.jsonl"
            trusted_root_path = root / "trusted-root.jsonl"
            artifact_path.write_bytes(b"synthetic artifact")
            bundle_path.write_bytes(b"{}\n")
            trusted_root_path.write_bytes(b'{"synthetic":"trusted-root"}\n')
            artifact = registry_v1.RawFile(artifact_path, artifact_path.read_bytes())
            bundle = registry_v1.RawFile(bundle_path, bundle_path.read_bytes())
            trusted_root = registry_v1.RawFile(
                trusted_root_path, trusted_root_path.read_bytes()
            )
            policy = {
                "repository": "fixture/example",
                "signer_workflow": (
                    "fixture/example/.github/workflows/qwen3-ubuntu-witness.yml"
                ),
                "source_digest": "b" * 40,
                "source_ref": "refs/heads/research/witness-fixture",
                "run_id": "123456789",
                "run_attempt": 1,
                "predicate_type": registry_v1.SLSA_PROVENANCE_V1,
                "runner_environment": "github-hosted",
                "verifier": {
                    "name": "gh",
                    "minimum_version": registry_v1.GH_ATTESTATION_MINIMUM_VERSION,
                    "source_revision": registry_v1.GH_ATTESTATION_SOURCE_REVISION,
                },
            }
            ambient_environment = {name: str(path) for name, path in ambient_paths.items()}
            previous_directory = Path.cwd()
            try:
                os.chdir(checkout)
                with mock.patch.dict(os.environ, ambient_environment, clear=False), mock.patch.object(
                    registry_v1, "GH_TRUSTED_ROOT_DIGEST", trusted_root.digest
                ):
                    with self.assertRaisesRegex(
                        registry_v1.RegistryError,
                        "must verify exactly one bundled attestation",
                    ):
                        registry_v1._verify_github_attestation(
                            str(fake_gh),
                            artifact,
                            bundle,
                            trusted_root,
                            policy,
                            "synthetic GitHub attestation",
                        )
            finally:
                os.chdir(previous_directory)

            records = [json.loads(line) for line in audit.read_text().splitlines()]
            self.assertEqual([record["command"] for record in records], ["version", "attestation"])
            self.assertEqual(records[0]["paths"], records[1]["paths"])
            isolated_paths = {name: Path(value) for name, value in records[0]["paths"].items()}
            for name, path in isolated_paths.items():
                self.assertNotEqual(path, ambient_paths[name])
                self.assertFalse(path.exists())
            controls = records[0]["controls"]
            self.assertEqual(controls["GH_PROMPT_DISABLED"], "1")
            self.assertEqual(controls["GIT_TERMINAL_PROMPT"], "0")
            self.assertEqual(controls["GH_TELEMETRY"], "false")
            self.assertEqual(controls["DO_NOT_TRACK"], "true")
            self.assertEqual(controls["GH_NO_UPDATE_NOTIFIER"], "1")
            for name in (
                "HTTP_PROXY",
                "HTTPS_PROXY",
                "ALL_PROXY",
                "http_proxy",
                "https_proxy",
                "all_proxy",
            ):
                self.assertEqual(controls[name], "http://127.0.0.1:9")
            self.assertEqual(controls["NO_PROXY"], "")
            self.assertEqual(controls["no_proxy"], "")
            for path in ambient_paths.values():
                self.assertFalse(path.exists())
            self.assertEqual(list(checkout.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
