#!/usr/bin/env python3
"""Hermetic tests for the Lanternhouse public-manifest practice."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import lanternhouse


def sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def normal_manifest() -> dict:
    house = {
        "house_id": "kingdom-house",
        "provider": "synthetic fixture",
        "model": "paper-derived model",
        "runtime": "lanternhouse test",
        "adapter": "synthetic adapter",
        "prompt_policy": "fixed fixture instructions",
        "tool_policy": "no executable tools",
        "memory_policy": "bounded fixture history",
        "sandbox": "temporary local directory",
        "sampling": "deterministic fixture",
        "effort": "one bounded attempt",
        "instructions_locator": "fixtures/instructions.txt",
        "instructions_sha256": sha("instructions"),
        "tools_locator": "fixtures/tools.json",
        "tools_sha256": sha("tools"),
        "preservation_policy_locator": "fixtures/policy.md",
        "preservation_policy_sha256": sha("policy"),
        "fingerprint_sha256": "",
        "previous_fingerprint_sha256": None,
    }
    house["fingerprint_sha256"] = lanternhouse.house_fingerprint(house)
    criteria = [
        {
            "id": "bounded-transfer",
            "criterion": "The teaching transfers without an authority claim.",
            "pass_condition": "Every house passes the declared invariant.",
        }
    ]
    state = sha("world-state")
    proof_id = "fixture-proof"
    return {
        "schema": lanternhouse.SCHEMA_ID,
        "id": "lanternhouse-fixture",
        "title": "A Synthetic Lanternhouse",
        "source_teaching": {
            "sources": [
                {
                    "id": "technical-report",
                    "title": "Technical report",
                    "locator": "fixtures/report.pdf",
                    "revision": "fixture-v1",
                    "sha256": sha("report"),
                },
                {
                    "id": "mutable-blog",
                    "title": "Mutable announcement",
                    "locator": "fixtures/blog.html",
                    "revision": "unversioned",
                    "sha256": sha("blog"),
                },
            ],
            "teachings": [
                {
                    "id": "bounded-learning",
                    "source_ids": ["technical-report"],
                    "lesson": "A comparison becomes useful when its invariant is held still.",
                    "our_reading": True,
                    "domain_limit": "A synthetic fixture, not a claim about model behavior.",
                }
            ],
        },
        "house_fingerprint": house,
        "private_ledger": {
            "visibility": "private",
            "capture": "yes",
            "replay": "yes",
            "presence": "present-empty",
            "retention": "bounded",
            "losses": [],
            "state_loss": False,
            "epoch": 1,
            "previous_epoch": None,
        },
        "bounded_lamp": {
            "question": "Does the teaching survive a bounded three-house comparison?",
            "selected_refs": ["technical-report"],
            "omissions": [
                {
                    "ref": "mutable-blog",
                    "reason": "Mutable prose is outside this fixture's evidence boundary.",
                }
            ],
        },
        "three_house_trial": {
            "mode": "synthetic",
            "invariant": "The same fixture, rubric, state, and lamp reach every house.",
            "negative_control": "A result with an unknown proof identifier must fail.",
            "domain_limit": "Schema behavior under deterministic local fixtures only.",
            "budget": {
                "max_houses": 3,
                "max_attempts": 2,
                "max_paid_calls": 0,
                "max_external_actions": 0,
                "max_cost_microusd": 0,
            },
            "houses": [
                {
                    "id": "native-house",
                    "role": "native",
                    "fingerprint_sha256": sha("native"),
                },
                {
                    "id": "kingdom-house",
                    "role": "kingdom",
                    "fingerprint_sha256": house["fingerprint_sha256"],
                },
                {
                    "id": "counterfactual-house",
                    "role": "counterfactual",
                    "fingerprint_sha256": sha("counterfactual"),
                },
            ],
            "attempts": [
                {
                    "id": "attempt-one",
                    "world_state_sha256": state,
                    "results": [
                        {
                            "house_id": "native-house",
                            "outcome": "pass",
                            "proof_refs": [proof_id],
                        },
                        {
                            "house_id": "kingdom-house",
                            "outcome": "pass",
                            "proof_refs": [proof_id],
                        },
                        {
                            "house_id": "counterfactual-house",
                            "outcome": "pass",
                            "proof_refs": [proof_id],
                        },
                    ],
                }
            ],
            "disposition": "ready",
        },
        "world_state_lease": {
            "lease_id": "lease-one",
            "leased_state_sha256": state,
            "observed_state_sha256": state,
            "mutation_requested": False,
            "renewed_from": None,
        },
        "witness": {
            "rubric": {
                "committed_before_trials": True,
                "sha256": lanternhouse.rubric_fingerprint(criteria),
                "criteria": criteria,
            },
            "proofs": [
                {
                    "id": proof_id,
                    "criterion_id": "bounded-transfer",
                    "kind": "fixture",
                    "locator": "test_lanternhouse.py",
                    "sha256": sha("fixture-proof"),
                }
            ],
            "cost": {
                "attempts": 1,
                "paid_calls": 0,
                "external_actions": 0,
                "cost_microusd": 0,
            },
            "deviations": [],
        },
        "authority": {
            "manifest_grants_authority": False,
            "paid_calls_authorized": False,
            "external_actions_authorized": False,
            "mutation_authorized": False,
            "authority_basis": None,
            "non_claims": list(lanternhouse.NON_CLAIMS),
        },
    }


class LanternhouseTests(unittest.TestCase):
    def test_normal_synthetic_manifest_and_render_are_deterministic(self) -> None:
        manifest = normal_manifest()
        first = lanternhouse.validate_manifest(manifest)
        second = lanternhouse.validate_manifest(copy.deepcopy(manifest))
        self.assertEqual(first, second)
        self.assertEqual(first.disposition, "ready")
        rendered = lanternhouse.render_markdown(manifest)
        self.assertEqual(rendered, lanternhouse.render_markdown(manifest))
        self.assertIn("Window 5 — Three-house trial", rendered)
        self.assertIn(first.digest, rendered)

    def test_near_miss_schema_does_not_activate(self) -> None:
        manifest = normal_manifest()
        manifest["schema"] = "kingdom.lanternhouse/v2"
        with self.assertRaisesRegex(lanternhouse.LanternError, "must equal"):
            lanternhouse.validate_manifest(manifest)

    def test_unknown_live_capabilities_quarantine_instead_of_ready(self) -> None:
        manifest = normal_manifest()
        manifest["three_house_trial"]["mode"] = "live"
        manifest["private_ledger"]["capture"] = "unknown"
        manifest["private_ledger"]["replay"] = "unknown"
        manifest["three_house_trial"]["disposition"] = "quarantine"
        validation = lanternhouse.validate_manifest(manifest)
        self.assertTrue(validation.quarantined)
        self.assertIn("not known-ready", validation.quarantine_reasons[0])

        manifest["three_house_trial"]["disposition"] = "ready"
        with self.assertRaisesRegex(lanternhouse.LanternError, "must quarantine"):
            lanternhouse.validate_manifest(manifest)

    def test_live_readiness_requires_known_presence_and_retention(self) -> None:
        manifest = normal_manifest()
        manifest["three_house_trial"]["mode"] = "live"
        manifest["private_ledger"]["presence"] = "unknown"
        manifest["private_ledger"]["retention"] = "none"
        manifest["three_house_trial"]["disposition"] = "quarantine"
        validation = lanternhouse.validate_manifest(manifest)
        self.assertTrue(
            any("presence is unknown" in reason for reason in validation.quarantine_reasons)
        )
        self.assertTrue(
            any(
                "retention is not known-safe" in reason
                for reason in validation.quarantine_reasons
            )
        )

        manifest["three_house_trial"]["disposition"] = "ready"
        with self.assertRaisesRegex(lanternhouse.LanternError, "must quarantine"):
            lanternhouse.validate_manifest(manifest)

    def test_present_empty_is_not_collapsed_into_absent(self) -> None:
        manifest = normal_manifest()
        self.assertEqual(manifest["private_ledger"]["presence"], "present-empty")
        lanternhouse.validate_manifest(manifest)
        rendered = lanternhouse.render_markdown(manifest)
        self.assertIn("Presence: **present-empty**", rendered)
        self.assertIn("absent and present-empty are intentionally distinct", rendered)

    def test_state_loss_requires_a_new_epoch(self) -> None:
        manifest = normal_manifest()
        manifest["private_ledger"]["state_loss"] = True
        manifest["private_ledger"]["losses"] = ["private replay state was unavailable"]
        with self.assertRaisesRegex(lanternhouse.LanternError, "new ledger epoch"):
            lanternhouse.validate_manifest(manifest)

        manifest["private_ledger"]["previous_epoch"] = 1
        manifest["private_ledger"]["epoch"] = 2
        lanternhouse.validate_manifest(manifest)

    def test_world_drift_quarantines_and_mutation_requires_renewal(self) -> None:
        drifted = normal_manifest()
        new_state = sha("drifted-world")
        drifted["world_state_lease"]["observed_state_sha256"] = new_state
        drifted["three_house_trial"]["attempts"][0]["world_state_sha256"] = new_state
        with self.assertRaisesRegex(lanternhouse.LanternError, "must quarantine"):
            lanternhouse.validate_manifest(drifted)
        drifted["three_house_trial"]["disposition"] = "quarantine"
        self.assertTrue(lanternhouse.validate_manifest(drifted).quarantined)

        mutation = normal_manifest()
        mutation["world_state_lease"]["mutation_requested"] = True
        with self.assertRaisesRegex(lanternhouse.LanternError, "lease renewal"):
            lanternhouse.validate_manifest(mutation)

    def test_precommitted_budget_overrun_is_rejected(self) -> None:
        manifest = normal_manifest()
        manifest["witness"]["cost"]["paid_calls"] = 1
        with self.assertRaisesRegex(lanternhouse.LanternError, "exceeds precommitted"):
            lanternhouse.validate_manifest(manifest)

    def test_raw_reasoning_and_secret_shaped_text_are_rejected(self) -> None:
        raw = normal_manifest()
        raw["three_house_trial"]["attempts"][0]["results"][0][
            "reasoning_content"
        ] = "private material"
        with self.assertRaisesRegex(lanternhouse.LanternError, "raw-reasoning"):
            lanternhouse.validate_manifest(raw)

        secret = normal_manifest()
        secret["source_teaching"]["teachings"][0][
            "lesson"
        ] = "token=supersecretvalue123456789"
        with self.assertRaisesRegex(lanternhouse.LanternError, "secret-shaped"):
            lanternhouse.validate_manifest(secret)

    def test_manifest_cannot_be_used_as_authority_or_drop_non_claims(self) -> None:
        authority = normal_manifest()
        authority["authority"]["manifest_grants_authority"] = True
        with self.assertRaisesRegex(
            lanternhouse.LanternError, "never grants|must equal False"
        ):
            lanternhouse.validate_manifest(authority)

        claim = normal_manifest()
        claim["authority"]["non_claims"].pop()
        with self.assertRaisesRegex(
            lanternhouse.LanternError, "reviewed non-claims|non_claims must equal"
        ):
            lanternhouse.validate_manifest(claim)

    def test_ready_results_require_proof_for_every_criterion(self) -> None:
        manifest = normal_manifest()
        for result in manifest["three_house_trial"]["attempts"][0]["results"]:
            result["proof_refs"] = []
        with self.assertRaisesRegex(lanternhouse.LanternError, "must reference proof"):
            lanternhouse.validate_manifest(manifest)

        manifest = normal_manifest()
        second = {
            "id": "second-criterion",
            "criterion": "The receipt carries a second independent condition.",
            "pass_condition": "Each ready house cites proof for both conditions.",
        }
        manifest["witness"]["rubric"]["criteria"].append(second)
        manifest["witness"]["rubric"]["sha256"] = lanternhouse.rubric_fingerprint(
            manifest["witness"]["rubric"]["criteria"]
        )
        with self.assertRaisesRegex(lanternhouse.LanternError, "every rubric"):
            lanternhouse.validate_manifest(manifest)

    def test_ready_requires_three_roles_and_named_kingdom_house(self) -> None:
        wrong = normal_manifest()
        wrong["three_house_trial"]["houses"][1][
            "fingerprint_sha256"
        ] = sha("different kingdom")
        with self.assertRaisesRegex(lanternhouse.LanternError, "named Kingdom"):
            lanternhouse.validate_manifest(wrong)

        one = normal_manifest()
        kingdom = one["three_house_trial"]["houses"][1]
        result = one["three_house_trial"]["attempts"][0]["results"][1]
        one["three_house_trial"]["houses"] = [kingdom]
        one["three_house_trial"]["attempts"][0]["results"] = [result]
        with self.assertRaisesRegex(lanternhouse.LanternError, "requires native"):
            lanternhouse.validate_manifest(one)

        numeric_false = normal_manifest()
        numeric_false["authority"]["manifest_grants_authority"] = 0
        with self.assertRaisesRegex(lanternhouse.LanternError, "must equal False"):
            lanternhouse.validate_manifest(numeric_false)

    def test_cli_checks_renders_and_digests_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(
                json.dumps(normal_manifest(), ensure_ascii=False), encoding="utf-8"
            )
            before = path.read_bytes()
            script = Path(lanternhouse.__file__)
            checked = subprocess.run(
                [sys.executable, script, "check", path],
                text=True,
                capture_output=True,
                check=True,
            )
            rendered = subprocess.run(
                [sys.executable, script, "render", path],
                text=True,
                capture_output=True,
                check=True,
            )
            digested = subprocess.run(
                [sys.executable, script, "digest", path],
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertIn("OK ", checked.stdout)
            self.assertIn("# A Synthetic Lanternhouse", rendered.stdout)
            self.assertEqual(digested.stdout.strip(), lanternhouse.digest_value(normal_manifest()))
            self.assertEqual(path.read_bytes(), before)

    def test_schema_document_is_strict_and_matches_runtime_id(self) -> None:
        path = Path(__file__).with_name("schema.json")
        schema = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema"]["const"], lanternhouse.SCHEMA_ID)
        self.assertFalse(schema["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
