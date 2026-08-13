#!/usr/bin/env python3
"""Self-contained tests for the model-release capsule registry seam."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


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
    if path.endswith(".json"):
        return "application/json"
    if path.endswith(".pem"):
        return "application/x-pem-file"
    if path.endswith(".txt") or path.endswith(".md"):
        return "text/plain"
    return "application/octet-stream"


class SignedFixture:
    """Build and reseal a complete capsule entirely inside one temp directory."""

    capsule_id = "signed-fixture-v1"
    release_path = "release.json"
    profile_path = "local-profile.json"
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
        inventory["summary"]["weight_bytes"] = 9
        with self.assertRaisesRegex(registry_v1.RegistryError, "summary differs"):
            registry_v1._validate_publisher_inventory(inventory, "test inventory")
        inventory["summary"]["weight_bytes"] = True
        with self.assertRaisesRegex(registry_v1.RegistryError, "summary values must be integers"):
            registry_v1._validate_publisher_inventory(inventory, "test inventory")

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


if __name__ == "__main__":
    unittest.main()
