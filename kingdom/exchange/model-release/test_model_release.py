#!/usr/bin/env python3
"""Hermetic tests for the Kingdom Model Release Substrate."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import model_release


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EXAMPLES = HERE / "examples"
RELEASE_PATH = EXAMPLES / "synthetic-release.json"
PROFILE_PATH = EXAMPLES / "synthetic-profile.json"
ATTESTATION_PATH = EXAMPLES / "synthetic-evaluation.json"
CLI = HERE / "model_release.py"

RELEASE_DIGEST = "sha256:d7bba76c6c5edb7700b1ff16ca007716a4ef1247522e0248e4040a1408754bee"
PROFILE_DIGEST = "sha256:6dd631eaf578b80eaca14654b3baf2367d086c47e246ab09b9b9669ef18a7cf7"
ATTESTATION_DIGEST = "sha256:3afadc88398aec6e680825a48237b8aa3516dc21b2f26909dda14e5eaa9767b6"


def descriptor(byte: str, *, size: int = 32, media_type: str = "application/json") -> dict:
    return {
        "media_type": media_type,
        "digest": "sha256:" + byte * 64,
        "size": size,
    }


def evidence(identifier: str, content: dict) -> dict:
    return {
        "id": identifier,
        "title": f"Synthetic {identifier}",
        "kind": "fixture",
        "locator": f"urn:kingdom:fixture:{identifier}",
        "revision": f"fixture-{identifier}-1",
        "retrieved_at": "2026-08-13T00:00:00Z",
        "mutability": "immutable",
        "assertor": "Kingdom synthetic fixture",
        "content": content,
    }


def attestation_base(predicate_type: str, subject_kind: str, subject_digest: str) -> dict:
    return {
        "schema": model_release.ATTESTATION_SCHEMA,
        "kind": "attestation",
        "subject": {
            "name": "Synthetic bounded subject",
            "kind": subject_kind,
            "digest": subject_digest,
        },
        "predicate_type": predicate_type,
        "evidence_class": "curator-observed",
        "assertor": {
            "name": "Kingdom synthetic fixture",
            "identity": "urn:kingdom:fixture:curator",
        },
        "issued_at": "2026-08-13T00:00:00Z",
        "evidence": [],
        "non_claims": list(model_release.ATTESTATION_NON_CLAIMS),
    }


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def reverse_keys(value):
    if isinstance(value, dict):
        return {key: reverse_keys(child) for key, child in reversed(list(value.items()))}
    if isinstance(value, list):
        return [reverse_keys(child) for child in value]
    return value


class ModelReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.release = load(RELEASE_PATH)
        self.profile = load(PROFILE_PATH)
        self.attestation = load(ATTESTATION_PATH)

    def assert_invalid(self, value: dict, phrase: str) -> None:
        with self.assertRaisesRegex(model_release.ReleaseError, phrase):
            model_release.validate_document(value)

    def test_reviewed_schema_digest_is_pinned(self) -> None:
        self.assertEqual(
            model_release.verify_reviewed_schema(),
            model_release.EXPECTED_SCHEMA_SHA256,
        )

    def test_synthetic_examples_are_valid_and_digest_stable(self) -> None:
        self.assertEqual(model_release.validate_document(self.release), RELEASE_DIGEST)
        self.assertEqual(model_release.validate_document(self.profile), PROFILE_DIGEST)
        self.assertEqual(
            model_release.validate_document(self.attestation),
            ATTESTATION_DIGEST,
        )

    def test_release_profile_and_attestation_bind_as_one_set(self) -> None:
        self.assertEqual(
            model_release.verify_set(
                self.release,
                self.profile,
                [self.attestation],
            ),
            (RELEASE_DIGEST, PROFILE_DIGEST, [ATTESTATION_DIGEST]),
        )

        with self.assertRaisesRegex(model_release.ReleaseError, "duplicates an earlier"):
            model_release.verify_set(
                self.release,
                self.profile,
                [self.attestation, copy.deepcopy(self.attestation)],
            )

    def test_canonical_digest_ignores_object_key_order(self) -> None:
        reordered = reverse_keys(self.release)
        self.assertEqual(
            model_release.validate_document(reordered),
            RELEASE_DIGEST,
        )
        self.assertEqual(
            model_release.canonical_json(reordered),
            model_release.canonical_json(self.release),
        )

    def test_a_hashed_field_change_changes_the_release_digest(self) -> None:
        changed = copy.deepcopy(self.release)
        changed["artifacts"][0]["descriptor"]["digest"] = (
            "sha256:0101010101010101010101010101010101010101010101010101010101010101"
        )
        digest = model_release.validate_document(changed)
        self.assertNotEqual(digest, RELEASE_DIGEST)

    def test_receipt_binds_canonical_content_and_exact_source_bytes(self) -> None:
        loaded = model_release.read_document(RELEASE_PATH)
        receipt = model_release.make_receipt(loaded.value, loaded.raw)
        self.assertEqual(receipt["content_digest"], RELEASE_DIGEST)
        self.assertEqual(receipt["canonical"]["sha256"], RELEASE_DIGEST)
        self.assertEqual(
            receipt["reviewed_schema"]["canonical_sha256"],
            "sha256:" + model_release.EXPECTED_SCHEMA_SHA256,
        )
        validator_raw = model_release.VALIDATOR_PATH.read_bytes()
        self.assertEqual(receipt["validator"]["name"], model_release.VALIDATOR_NAME)
        self.assertEqual(receipt["validator"]["version"], model_release.VALIDATOR_VERSION)
        self.assertEqual(
            receipt["validator"]["source"]["digest"],
            model_release.sha256_bytes(validator_raw),
        )
        self.assertEqual(receipt["validation_profile"], model_release.VALIDATION_PROFILE)
        self.assertEqual(model_release.verify_receipt(loaded, receipt), RELEASE_DIGEST)

        with tempfile.TemporaryDirectory() as directory:
            changed_path = Path(directory) / "release.json"
            changed_path.write_bytes(loaded.raw + b"\n")
            changed = model_release.read_document(changed_path)
            self.assertEqual(model_release.validate_document(changed.value), RELEASE_DIGEST)
            with self.assertRaisesRegex(model_release.ReleaseError, "exact source"):
                model_release.verify_receipt(changed, receipt)

    def test_receipt_generation_is_deterministic(self) -> None:
        loaded = model_release.read_document(PROFILE_PATH)
        first = model_release.make_receipt(loaded.value, loaded.raw)
        second = model_release.make_receipt(copy.deepcopy(loaded.value), loaded.raw)
        self.assertEqual(first, second)
        self.assertEqual(
            model_release.canonical_json(first),
            model_release.canonical_json(second),
        )

    def test_receipt_cannot_change_object_kind(self) -> None:
        loaded = model_release.read_document(RELEASE_PATH)
        receipt = model_release.make_receipt(loaded.value, loaded.raw)
        receipt["object_kind"] = "execution-profile"
        self.assert_invalid(receipt, "schema and kind differ")

        receipt = model_release.make_receipt(loaded.value, loaded.raw)
        receipt["reviewed_schema"]["canonical_sha256"] = "sha256:" + "0" * 64
        self.assert_invalid(receipt, "reviewed schema identity changed")

        receipt = model_release.make_receipt(loaded.value, loaded.raw)
        receipt["validator"]["source"]["digest"] = "sha256:" + "0" * 64
        self.assert_invalid(receipt, "validator identity changed")

    def test_unknown_and_unavailable_artifacts_cannot_invent_descriptors(self) -> None:
        changed = copy.deepcopy(self.release)
        changed["artifacts"][0]["identity_status"] = "unknown"
        self.assert_invalid(changed, "cannot carry a byte descriptor")

        changed = copy.deepcopy(self.release)
        del changed["artifacts"][0]["descriptor"]
        self.assert_invalid(changed, "requires a descriptor")

    def test_mutable_revisions_do_not_pass_as_exact_runtime_identity(self) -> None:
        changed = copy.deepcopy(self.profile)
        changed["engine"]["source_revision"] = "main"
        self.assert_invalid(changed, "mutable or unresolved revision")

        changed = copy.deepcopy(self.profile)
        changed["resolved"]["attention_backend"] = "auto"
        self.assert_invalid(changed, "unresolved default")

        changed = copy.deepcopy(self.profile)
        changed["engine"]["source_revision"] = "refs/heads/main"
        self.assert_invalid(changed, "mutable or unresolved revision")

        changed = copy.deepcopy(self.release)
        changed["release"]["version"] = "latest"
        self.assert_invalid(changed, "mutable or unresolved revision")

    def test_backend_observation_is_not_promoted_to_digest(self) -> None:
        changed = copy.deepcopy(self.profile)
        changed["backend"]["observations"][0]["name"] = "model_digest"
        self.assert_invalid(changed, "cannot be labeled as cryptographic")

    def test_raw_reasoning_fields_are_refused(self) -> None:
        changed = copy.deepcopy(self.release)
        changed["interface"]["reasoning"]["raw_reasoning"] = "fixture trace"
        self.assert_invalid(changed, "forbidden raw-reasoning field")

        changed = copy.deepcopy(self.release)
        changed["disclosures"][0]["field"] = "raw_reasoning"
        self.assert_invalid(changed, "raw-reasoning content channel")

    def test_reasoning_continuation_must_use_declared_item_types(self) -> None:
        changed = copy.deepcopy(self.release)
        changed["interface"]["reasoning"]["continuation"]["resend"] = [
            "undeclared-item"
        ]
        self.assert_invalid(changed, "resends undeclared")

    def test_release_requires_baseline_disclosures_and_terms_states(self) -> None:
        changed = copy.deepcopy(self.release)
        changed["disclosures"] = [changed["disclosures"][-1]]
        self.assert_invalid(changed, "missing baseline disclosure fields")

        changed = copy.deepcopy(self.release)
        changed["terms"] = []
        self.assert_invalid(changed, "reviewed schema branch")

        changed = copy.deepcopy(self.release)
        changed["release"]["access"] = "api"
        self.assert_invalid(changed, "missing terms states")

        changed = copy.deepcopy(self.release)
        changed["terms"][0]["status"] = "not-applicable"
        self.assert_invalid(changed, "cannot mark license not-applicable")

    def test_reasoning_disclosure_and_continuation_state_are_distinct(self) -> None:
        changed = copy.deepcopy(self.release)
        changed["interface"]["reasoning"]["disclosure"] = "summary"
        changed["interface"]["reasoning"]["continuation_state"] = "encrypted"
        model_release.validate_document(changed)

        changed = copy.deepcopy(self.release)
        changed["interface"]["reasoning"]["continuation_state"] = "none"
        self.assert_invalid(changed, "state none cannot resend")

    def test_execution_profile_must_bind_the_supplied_release(self) -> None:
        changed = copy.deepcopy(self.profile)
        changed["subject"]["release_digest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(model_release.ReleaseError, "does not bind"):
            model_release.verify_set(self.release, changed, [])

    def test_attestation_must_bind_a_known_set_subject(self) -> None:
        changed = copy.deepcopy(self.attestation)
        changed["subject"]["digest"] = "sha256:" + "0" * 64
        changed["evaluation"]["execution_profile_digest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(model_release.ReleaseError, "unknown release-set subject"):
            model_release.verify_set(self.release, self.profile, [changed])

    def test_attestation_predicate_type_has_exactly_one_matching_body(self) -> None:
        changed = copy.deepcopy(self.attestation)
        changed["predicate_type"] = "signature"
        self.assert_invalid(changed, "exactly the signature predicate")

    def test_duplicate_json_keys_are_rejected(self) -> None:
        raw = b'{"schema":"kingdom.model-release/v1","schema":"other"}'
        with self.assertRaisesRegex(model_release.ReleaseError, "duplicate JSON key"):
            model_release._parse_json(raw, "fixture")

    def test_floats_are_outside_the_canonical_profile(self) -> None:
        with self.assertRaisesRegex(model_release.ReleaseError, "floating-point"):
            model_release._parse_json(b'{"value":0.5}', "fixture")

    def test_integers_are_bounded_without_a_traceback(self) -> None:
        raw = ('{"value":' + "9" * 5000 + "}").encode()
        with self.assertRaisesRegex(model_release.ReleaseError, "signed 64-bit"):
            model_release._parse_json(raw, "fixture")

    def test_timestamps_are_real_and_ordered(self) -> None:
        changed = copy.deepcopy(self.release)
        changed["release"]["released_at"] = "2026-99-99T99:99:99Z"
        self.assert_invalid(changed, "real UTC timestamp")

        changed = copy.deepcopy(self.attestation)
        changed["evaluation"]["finished_at"] = "2026-08-13T00:00:01Z"
        self.assert_invalid(changed, "issued before the run finished")

        changed = copy.deepcopy(self.attestation)
        changed["evaluation"]["judge"]["revision"] = "latest"
        self.assert_invalid(changed, "mutable or unresolved revision")

        changed = copy.deepcopy(self.attestation)
        changed["evidence"][0]["retrieved_at"] = "2099-01-01T00:00:00Z"
        self.assert_invalid(changed, "retrieved after issuance")

    def test_hosted_api_profiles_bind_the_observable_identity_seam(self) -> None:
        hosted = copy.deepcopy(self.profile)
        hosted["engine"].update(
            {
                "version": "provider-managed",
                "implementation": "provider-managed",
                "loader": "provider-managed",
                "source_revision": "provider-managed",
                "kernels": [],
            }
        )
        hosted["engine"].pop("custom_code_revision", None)
        hosted["engine"].pop("package", None)
        hosted["resolved"] = {
            "dtype": "provider-managed",
            "weight_quantization": "unknown",
            "kv_cache_dtype": "provider-managed",
            "load_format": "provider-managed",
            "context_tokens": "provider-managed",
            "parallelism": "provider-managed",
            "attention_backend": "unknown",
            "speculative_decoding": "provider-managed",
            "rope_overrides": "unknown",
        }
        hosted["hardware"] = {
            "visibility": "provider-managed",
            "accelerators": [],
            "driver": "provider-managed",
            "compute_stack": "provider-managed",
            "interconnect": "unknown",
            "topology": "unknown",
        }
        hosted["backend"]["kind"] = "hosted-api"
        with self.assertRaisesRegex(model_release.ReleaseError, "requires an API binding"):
            model_release.validate_document(hosted)

        hosted["backend"]["api_binding"] = {
            "requested_model": {
                "value": "fixture-model-latest",
                "alias_mutability": "mutable",
            },
            "returned_model": {"status": "present", "value": "fixture-model-2026-08-13"},
            "region": {"status": "unknown"},
            "request_configuration": copy.deepcopy(
                hosted["evidence"][0]["content"]
            ),
            "observed_at": "2026-08-13T00:00:00Z",
            "evidence_refs": ["fixture-runtime-docs"],
        }
        model_release.validate_document(hosted)

        broken = copy.deepcopy(hosted)
        del broken["backend"]["api_binding"]["returned_model"]["value"]
        self.assert_invalid(broken, "requires a value")

        broken = copy.deepcopy(hosted)
        broken["resolved"]["attention_backend"] = "auto"
        self.assert_invalid(broken, "unresolved default")

        broken = copy.deepcopy(hosted)
        broken["backend"]["api_binding"]["request_configuration"]["digest"] = (
            "sha256:" + "0" * 64
        )
        self.assert_invalid(broken, "no evidence content matching")

    def test_evaluation_artifacts_match_their_evidence_bytes(self) -> None:
        changed = copy.deepcopy(self.attestation)
        changed["evaluation"]["artifacts"][0]["descriptor"]["digest"] = (
            "sha256:" + "0" * 64
        )
        self.assert_invalid(changed, "no evidence content matching")

        changed = copy.deepcopy(self.attestation)
        changed["evaluation"]["evidence_refs"] = []
        self.assert_invalid(changed, "reviewed schema branch")

    def test_build_outputs_are_bound_to_release_artifacts(self) -> None:
        build_log = descriptor("1")
        attestation = attestation_base("build-provenance", "model-release", RELEASE_DIGEST)
        attestation["build"] = {
            "build_type": "urn:kingdom:fixture:model-build",
            "builder_id": "urn:kingdom:fixture:builder",
            "builder_version": "fixture-builder-1",
            "invocation_id": "fixture-invocation-1",
            "coverage": "partial",
            "started_at": "2026-08-13T00:00:00Z",
            "finished_at": "2026-08-13T00:00:00Z",
            "parameters": [],
            "resolved_dependencies": [],
            "outputs": [
                {
                    "artifact_ref": "weights-one",
                    "name": self.release["artifacts"][0]["name"],
                    "role": self.release["artifacts"][0]["role"],
                    "descriptor": copy.deepcopy(self.release["artifacts"][0]["descriptor"]),
                }
            ],
            "byproducts": [],
            "evidence_refs": ["fixture-build-log"],
        }
        attestation["evidence"] = [evidence("fixture-build-log", build_log)]
        model_release.verify_set(self.release, self.profile, [attestation])

        attestation["build"]["outputs"][0]["descriptor"]["digest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(model_release.ReleaseError, "differs from release artifact"):
            model_release.verify_set(self.release, self.profile, [attestation])

        complete = copy.deepcopy(attestation)
        complete["build"]["outputs"][0]["descriptor"] = copy.deepcopy(
            self.release["artifacts"][0]["descriptor"]
        )
        complete["build"]["coverage"] = "complete"
        with self.assertRaisesRegex(model_release.ReleaseError, "complete build coverage"):
            model_release.verify_set(self.release, self.profile, [complete])

    def test_signature_binds_subject_policy_tool_and_evidence(self) -> None:
        bundle = descriptor("2")
        policy = descriptor("3")
        attestation = attestation_base("signature", "execution-profile", PROFILE_DIGEST)
        attestation["signature"] = {
            "format": "sigstore-bundle",
            "bundle": bundle,
            "signed_digest": PROFILE_DIGEST,
            "signer_identity": "fixture signer",
            "issuer": "fixture issuer",
            "verifier_policy": policy,
            "verifier_tool": {
                "name": "fixture verifier",
                "version": "1.0.0",
                "source_revision": "fixture-verifier-commit-1",
            },
            "verified_at": "2026-08-13T00:00:00Z",
            "verified": True,
            "evidence_refs": ["fixture-signature", "fixture-policy"],
        }
        attestation["evidence"] = [
            evidence("fixture-signature", bundle),
            evidence("fixture-policy", policy),
        ]
        model_release.verify_set(self.release, self.profile, [attestation])

        attestation["signature"]["signed_digest"] = RELEASE_DIGEST
        self.assert_invalid(attestation, "differs from its attestation subject")

    def test_artifact_check_streams_and_compares_real_bytes(self) -> None:
        payload = b"synthetic artifact bytes\n"
        release = copy.deepcopy(self.release)
        release["artifacts"][0]["identity_status"] = "descriptor-asserted"
        release["artifacts"][0]["descriptor"] = {
            "media_type": "application/octet-stream",
            "digest": "sha256:" + hashlib.sha256(payload).hexdigest(),
            "size": len(payload),
        }
        with tempfile.TemporaryDirectory() as directory:
            artifact_path = Path(directory) / "artifact.bin"
            artifact_path.write_bytes(payload)
            self.assertEqual(
                model_release.verify_artifact_file(release, "weights-one", artifact_path),
                (release["artifacts"][0]["descriptor"]["digest"], len(payload)),
            )
            artifact_path.write_bytes(b"X" * len(payload))
            with self.assertRaisesRegex(model_release.ReleaseError, "digest differs"):
                model_release.verify_artifact_file(release, "weights-one", artifact_path)

    def test_correction_requires_a_superseding_replacement_release(self) -> None:
        replacement = copy.deepcopy(self.release)
        replacement["release"]["version"] = "1.0.1-fixture"
        replacement["relations"] = [
            {"kind": "supersedes", "target_digest": RELEASE_DIGEST}
        ]
        replacement_digest = model_release.validate_document(replacement)
        change_note = descriptor("4")
        correction = attestation_base("correction", "model-release", RELEASE_DIGEST)
        correction["change"] = {
            "kind": "correction",
            "reason": "Synthetic correction fixture.",
            "effective_at": "2026-08-13T00:00:00Z",
            "replacement_digest": replacement_digest,
            "evidence_refs": ["fixture-correction"],
        }
        correction["evidence"] = [evidence("fixture-correction", change_note)]
        old_digest, new_digest, _ = model_release.verify_supersession(
            self.release, replacement, correction
        )
        self.assertEqual((old_digest, new_digest), (RELEASE_DIGEST, replacement_digest))

        without_relation = copy.deepcopy(replacement)
        without_relation["relations"] = []
        without_relation_correction = copy.deepcopy(correction)
        without_relation_correction["change"]["replacement_digest"] = (
            model_release.validate_document(without_relation)
        )
        with self.assertRaisesRegex(model_release.ReleaseError, "does not supersede"):
            model_release.verify_supersession(
                self.release, without_relation, without_relation_correction
            )

        missing = copy.deepcopy(correction)
        del missing["change"]["replacement_digest"]
        self.assert_invalid(missing, "requires a replacement")

    def test_markdown_rendering_keeps_untrusted_text_inert(self) -> None:
        changed = copy.deepcopy(self.release)
        changed["release"]["publisher"] = "![pixel](https://attacker.invalid/pixel)"
        rendered = model_release.render_markdown(changed)
        self.assertNotIn("![pixel]", rendered)
        self.assertIn(r"\!\[pixel\]", rendered)

    def test_non_nfc_text_is_rejected(self) -> None:
        changed = copy.deepcopy(self.release)
        changed["release"]["name"] = "Cafe\u0301"
        self.assert_invalid(changed, "NFC Unicode")

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_final_symlink_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            link = Path(directory) / "release.json"
            link.symlink_to(RELEASE_PATH)
            with self.assertRaisesRegex(model_release.ReleaseError, "missing or unsafe"):
                model_release.read_document(link)

    def test_cli_receipt_and_verification_round_trip(self) -> None:
        receipt_result = subprocess.run(
            [sys.executable, "-B", str(CLI), "receipt", str(RELEASE_PATH)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(receipt_result.returncode, 0, receipt_result.stderr)
        receipt = json.loads(receipt_result.stdout)
        self.assertEqual(receipt["content_digest"], RELEASE_DIGEST)
        with tempfile.TemporaryDirectory() as directory:
            receipt_path = Path(directory) / "receipt.json"
            receipt_path.write_text(receipt_result.stdout, encoding="utf-8")
            verified = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(CLI),
                    "verify",
                    str(RELEASE_PATH),
                    str(receipt_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertIn("MODEL-RELEASE-RECEIPT-OK", verified.stdout)

    def test_cli_verify_set_and_render_are_bounded(self) -> None:
        verified = subprocess.run(
            [
                sys.executable,
                "-B",
                str(CLI),
                "verify-set",
                str(RELEASE_PATH),
                str(PROFILE_PATH),
                str(ATTESTATION_PATH),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertIn("attestations=1", verified.stdout)

        rendered = model_release.render_markdown(self.release)
        self.assertIn("Reasoning interface", rendered)
        self.assertIn(RELEASE_DIGEST, rendered)
        self.assertNotIn("fixture trace", rendered)


if __name__ == "__main__":
    unittest.main()
