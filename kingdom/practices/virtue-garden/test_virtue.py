from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import virtue


HERE = Path(__file__).resolve().parent
EXAMPLES = HERE / "examples"


def load_example(name: str = "constructive-infrastructure.json") -> dict[str, Any]:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def drop_evidence(manifest: dict[str, Any], evidence_id: str) -> None:
    manifest["evidence"] = [
        item for item in manifest["evidence"] if item["id"] != evidence_id
    ]


def add_evidence(
    manifest: dict[str, Any],
    evidence_id: str,
    kind: str,
    *,
    depends_on: list[str] | None = None,
) -> None:
    manifest["evidence"].append(
        {
            "id": evidence_id,
            "kind": kind,
            "locator": f"fixture:{evidence_id}",
            "sha256": hashlib.sha256(evidence_id.encode()).hexdigest(),
            "depends_on": depends_on or [],
        }
    )


class VirtueGardenTests(unittest.TestCase):
    maxDiff = None

    def assert_invalid(self, manifest: dict[str, Any], phrase: str | None = None) -> None:
        with self.assertRaises(virtue.VirtueError) as caught:
            virtue.validate_manifest(manifest)
        if phrase:
            self.assertIn(phrase, str(caught.exception))

    def test_reviewed_examples_cover_three_dispositions(self) -> None:
        expected = {
            "constructive-infrastructure.json": "fruiting",
            "circular-praise.json": "compost",
            "unknown-impact.json": "observe",
        }
        for name, disposition in expected.items():
            with self.subTest(name=name):
                result = virtue.validate_manifest(load_example(name))
                self.assertEqual(result.actions[0].disposition, disposition)

    def test_both_schemas_use_only_runtime_supported_keywords(self) -> None:
        supported = {
            "$schema",
            "$id",
            "$defs",
            "$ref",
            "title",
            "description",
            "type",
            "required",
            "properties",
            "additionalProperties",
            "const",
            "enum",
            "anyOf",
            "minItems",
            "maxItems",
            "uniqueItems",
            "items",
            "minLength",
            "maxLength",
            "pattern",
            "minimum",
            "maximum",
        }

        def walk(rule: dict[str, Any], path: str) -> None:
            self.assertFalse(
                set(rule) - supported,
                f"{path} uses unsupported keywords: {set(rule) - supported}",
            )
            for name, child in rule.get("$defs", {}).items():
                walk(child, f"{path}.$defs.{name}")
            for name, child in rule.get("properties", {}).items():
                walk(child, f"{path}.properties.{name}")
            for index, child in enumerate(rule.get("anyOf", [])):
                walk(child, f"{path}.anyOf[{index}]")
            if isinstance(rule.get("items"), dict):
                walk(rule["items"], f"{path}.items")

        for name in ("schema.json", "evaluation.schema.json"):
            with self.subTest(name=name):
                walk(json.loads((HERE / name).read_text(encoding="utf-8")), "$")

    def test_full_contract_documents_are_digest_pinned(self) -> None:
        self.assertEqual(
            virtue.digest_value(json.loads((HERE / "schema.json").read_text())),
            virtue.EXPECTED_SCHEMA_SHA256,
        )
        self.assertEqual(
            virtue.digest_value(json.loads((HERE / "rules.json").read_text())),
            virtue.EXPECTED_RULES_SHA256,
        )
        self.assertEqual(
            virtue.digest_value(
                json.loads((HERE / "evaluation.schema.json").read_text())
            ),
            virtue.EXPECTED_RESULT_SCHEMA_SHA256,
        )

    def test_public_page_is_local_linked_and_contract_complete(self) -> None:
        repository = HERE.parents[2]
        page = repository / "site" / "practices" / "virtue-garden" / "index.html"

        class Audit(HTMLParser):
            def __init__(self) -> None:
                super().__init__()
                self.ids: list[str] = []
                self.hrefs: list[str] = []
                self.sources: list[str] = []
                self.active_elements: list[str] = []

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
                if tag in {"script", "iframe"}:
                    self.active_elements.append(tag)

        text = page.read_text(encoding="utf-8")
        audit = Audit()
        audit.feed(text)
        self.assertEqual(len(audit.ids), len(set(audit.ids)))
        self.assertEqual(audit.sources, [])
        self.assertEqual(audit.active_elements, [])
        self.assertNotRegex(text, r"(?i)https?://|url\s*\(")
        for href in audit.hrefs:
            parsed = urlsplit(href)
            self.assertFalse(parsed.scheme or parsed.netloc, href)
            if href.startswith("#"):
                self.assertIn(href[1:], audit.ids)
            else:
                self.assertTrue((page.parent / parsed.path).exists(), href)
        for literal in (
            "schema.json",
            "evaluation.schema.json",
            "rules.json",
            "examples/constructive-infrastructure.json",
            "examples/circular-praise.json",
            "examples/unknown-impact.json",
            "citable-candidate",
            "presentable-candidate",
            "handoff-candidate",
            "teaching-candidate",
            "reuse-candidate",
            "for human review",
            "verify-result",
        ):
            self.assertIn(literal, text)

        for document in (HERE / "README.md", HERE / "DOCTRINE.md"):
            markdown = document.read_text(encoding="utf-8")
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", markdown):
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc or target.startswith("#"):
                    continue
                self.assertTrue((document.parent / parsed.path).exists(), target)

    def test_evaluation_is_deterministic_strict_and_non_aggregating(self) -> None:
        manifest = load_example()
        first = virtue.receipt_value(manifest)
        second = virtue.receipt_value(copy.deepcopy(manifest))
        self.assertEqual(first, second)
        self.assertEqual(first["schema"], "kingdom.virtue-evaluation/v1")
        self.assertEqual(
            [item["kind"] for item in first["action"]["local_affordance_candidates"]],
            [
                "citable-candidate",
                "presentable-candidate",
                "handoff-candidate",
                "teaching-candidate",
                "reuse-candidate",
            ],
        )
        self.assertEqual(
            first["action"]["rails"]["rights_action_boundary"], "respected"
        )
        self.assertNotIn("rights", first["action"]["rails"])
        serialized = json.dumps(first, sort_keys=True)
        for forbidden in (
            '"id"',
            "fingerprint",
            "title",
            "note",
            "evidence_ref",
            "locator",
            "deviations",
        ):
            self.assertNotIn(forbidden, serialized)
        keys: set[str] = set()

        def collect_keys(value: Any) -> None:
            if isinstance(value, dict):
                keys.update(value)
                for child in value.values():
                    collect_keys(child)
            elif isinstance(value, list):
                for child in value:
                    collect_keys(child)

        collect_keys(first)
        self.assertTrue(
            {"score", "total", "rank", "leaderboard", "payment", "access"}.isdisjoint(
                keys
            )
        )
        self.assertEqual(
            virtue.render_markdown(manifest),
            virtue.render_markdown(copy.deepcopy(manifest)),
        )

    def test_render_uses_only_the_privacy_minimized_result(self) -> None:
        manifest = load_example()
        manifest["title"] = "Alice synthetic title"
        manifest["actions"][0]["fruits"]["beauty"]["note"] = "Alice private note"
        rendered = virtue.render_markdown(manifest)
        serialized = json.dumps(virtue.receipt_value(manifest))
        self.assertNotIn("Alice", rendered)
        self.assertNotIn("Alice", serialized)
        self.assertNotIn(manifest["id"], rendered)
        self.assertNotIn(manifest["actions"][0]["id"], rendered)
        self.assertNotIn("correction_path", serialized)
        self.assertNotIn("appeal_path", serialized)

    def test_identity_markup_and_concealed_text_are_rejected(self) -> None:
        cases = (
            ("alice@example.com", "email-shaped"),
            ("<script>alert(1)</script>", "active markup-shaped"),
            ("[tracker](https://invalid.example)", "active markup-shaped"),
            ("javascript:alert(1)", "active markup-shaped"),
            ("safe\u202eunsafe", "concealed-direction"),
            ("safe\u200funsafe", "concealed-direction"),
            ("safe\ud800unsafe", "Unicode surrogate"),
        )
        for text, phrase in cases:
            with self.subTest(text=text):
                manifest = load_example()
                manifest["title"] = text
                self.assert_invalid(manifest, phrase)

    def test_fruits_are_independent_after_honesty_is_kept(self) -> None:
        manifest = load_example()
        beauty = manifest["actions"][0]["fruits"]["beauty"]
        beauty["state"] = "open"
        beauty["evaluation_reason"] = "unknown"
        result = virtue.receipt_value(manifest)
        self.assertEqual(result["action"]["disposition"], "fruiting")
        kinds = {
            item["kind"]
            for item in result["action"]["local_affordance_candidates"]
        }
        self.assertNotIn("presentable-candidate", kinds)
        self.assertIn("reuse-candidate", kinds)

    def test_honesty_is_always_applicable_and_is_the_candidate_floor(self) -> None:
        manifest = load_example()
        honesty = manifest["actions"][0]["fruits"]["honesty"]
        honesty["state"] = "open"
        honesty["evaluation_reason"] = "unknown"
        manifest["actions"][0]["declared_disposition"] = "observe"
        result = virtue.receipt_value(manifest)
        self.assertEqual(result["action"]["disposition"], "observe")
        self.assertEqual(result["action"]["local_affordance_candidates"], [])

        manifest = load_example()
        honesty = manifest["actions"][0]["fruits"]["honesty"]
        honesty["state"] = "not-applicable"
        honesty["evaluation_reason"] = "out-of-domain"
        honesty["evidence_refs"] = []
        honesty["predicate"] = {"checks": [], "records": []}
        self.assert_invalid(manifest, "always applicable")

    def test_recognition_choice_never_changes_fruit_or_candidates(self) -> None:
        opted_in = load_example()
        opted_out = copy.deepcopy(opted_in)
        recognition = opted_out["actions"][0]["recognition"]
        recognition["choice"] = "opt-out"
        recognition["visibility"] = "contextual-private"
        recognition["consent_refs"] = []
        drop_evidence(opted_out, "recognition-consent")
        in_result = virtue.receipt_value(opted_in)
        out_result = virtue.receipt_value(opted_out)
        self.assertEqual(
            in_result["action"]["disposition"], out_result["action"]["disposition"]
        )
        self.assertEqual(
            in_result["action"]["fruits"], out_result["action"]["fruits"]
        )
        self.assertEqual(
            in_result["action"]["local_affordance_candidates"],
            out_result["action"]["local_affordance_candidates"],
        )
        self.assertEqual(
            out_result["action"]["rails"]["recognition"]["choice"], "opt-out"
        )

    def test_style_changes_cannot_change_the_action_route(self) -> None:
        original = load_example()
        restyled = copy.deepcopy(original)
        restyled["title"] = "Plain structural fixture"
        restyled["actions"][0]["fruits"]["beauty"]["note"] = (
            "Plain form, same declared evidence."
        )
        original_result = virtue.receipt_value(original)
        restyled_result = virtue.receipt_value(restyled)
        self.assertNotEqual(
            original_result["manifest_sha256"], restyled_result["manifest_sha256"]
        )
        self.assertEqual(original_result["action"], restyled_result["action"])

    def test_witness_choir_cannot_multiply_recognition_or_candidates(self) -> None:
        original = load_example()
        choir = copy.deepcopy(original)
        add_evidence(choir, "second-consent-shape", "attestation")
        choir["actions"][0]["recognition"]["consent_refs"].append(
            "second-consent-shape"
        )
        original_action = virtue.receipt_value(original)["action"]
        choir_action = virtue.receipt_value(choir)["action"]
        self.assertEqual(original_action, choir_action)

    def test_compensation_never_changes_fruit_or_candidates(self) -> None:
        owed = load_example()
        add_evidence(owed, "compensation-status", "receipt")
        owed["actions"][0]["compensation"] = {
            "status": "owed-unsettled",
            "evidence_refs": ["compensation-status"],
        }
        settled = copy.deepcopy(owed)
        settled["actions"][0]["compensation"]["status"] = "settled-externally"
        owed_result = virtue.receipt_value(owed)
        settled_result = virtue.receipt_value(settled)
        self.assertEqual(owed_result["action"]["fruits"], settled_result["action"]["fruits"])
        self.assertEqual(
            owed_result["action"]["local_affordance_candidates"],
            settled_result["action"]["local_affordance_candidates"],
        )
        self.assertEqual(owed_result["action"]["disposition"], "fruiting")
        self.assertEqual(
            owed_result["action"]["rails"]["compensation"], "owed-unsettled"
        )

    def test_one_action_and_banned_person_metric_fields(self) -> None:
        manifest = load_example()
        manifest["actions"].append(copy.deepcopy(manifest["actions"][0]))
        self.assert_invalid(manifest, "1..1")
        for key in (
            "actor",
            "identity",
            "score",
            "total",
            "rank",
            "leaderboard",
            "payment",
            "permission",
            "access",
        ):
            with self.subTest(key=key):
                manifest = load_example()
                manifest["actions"][0][key] = "forbidden"
                self.assert_invalid(manifest, "forbidden public field")

    def test_evidence_and_local_test_limits(self) -> None:
        manifest = load_example()
        for index in range(4):
            add_evidence(manifest, f"extra-{index}", "observation")
            manifest["actions"][0]["learning"]["evidence_refs"].append(
                f"extra-{index}"
            )
        self.assert_invalid(manifest, "1..24")

        manifest = load_example()
        add_evidence(manifest, "fourth-test", "test")
        manifest["actions"][0]["learning"] = {
            "lesson": "Synthetic limit probe.",
            "repair_status": "invited",
            "evidence_refs": ["fourth-test"],
        }
        manifest["actions"][0]["declared_disposition"] = "compost"
        self.assert_invalid(manifest, "at most three")

    def test_kept_predicates_require_exact_checks_roles_and_assessment_kind(self) -> None:
        variants: list[tuple[dict[str, Any], str]] = []

        manifest = load_example()
        manifest["actions"][0]["fruits"]["beauty"]["assessment_kind"] = "comparison"
        variants.append((manifest, "assessment_kind"))

        manifest = load_example()
        manifest["actions"][0]["fruits"]["honesty"]["predicate"]["checks"].pop()
        variants.append((manifest, "exact reviewed checks"))

        manifest = load_example()
        fruit = manifest["actions"][0]["fruits"]["understanding"]
        fruit["evidence_refs"].pop()
        fruit["predicate"]["records"].pop()
        variants.append((manifest, "observed-outcome"))

        manifest = load_example()
        records = manifest["actions"][0]["fruits"]["collaboration"]["predicate"]["records"]
        records[1]["label"] = records[0]["label"]
        variants.append((manifest, "distinct role labels"))

        manifest = load_example()
        evidence = next(
            item
            for item in manifest["evidence"]
            if item["id"] == "collaboration-handoff"
        )
        evidence["kind"] = "digest"
        variants.append((manifest, "cannot serve role"))

        for case, phrase in variants:
            with self.subTest(phrase=phrase):
                self.assert_invalid(case, phrase)

    def test_mutual_infrastructure_requires_same_unit_no_regression_and_improvement(self) -> None:
        records_path = ("actions", 0, "fruits", "mutual-infrastructure", "predicate", "records")

        def records(manifest: dict[str, Any]) -> list[dict[str, Any]]:
            value: Any = manifest
            for part in records_path:
                value = value[part]
            return value

        manifest = load_example()
        records(manifest)[1]["unit"] = "other-unit"
        self.assert_invalid(manifest, "one declared unit")

        manifest = load_example()
        records(manifest)[1]["after"] = records(manifest)[1]["before"] - 1
        self.assert_invalid(manifest, "may not regress")

        manifest = load_example()
        for record in records(manifest)[:2]:
            record["after"] = record["before"]
        self.assert_invalid(manifest, "strictly improved")

    def test_duplicate_sha_and_direct_claim_reuse_are_rejected(self) -> None:
        manifest = load_example()
        manifest["evidence"][1]["sha256"] = manifest["evidence"][0]["sha256"]
        self.assert_invalid(manifest, "globally unique")

        manifest = load_example()
        fruit = manifest["actions"][0]["fruits"]["beauty"]
        fruit["evidence_refs"][0] = "honesty-claim"
        fruit["predicate"]["records"][0]["evidence_ref"] = "honesty-claim"
        self.assert_invalid(manifest, "cannot directly support two")

    def test_protected_rails_reject_circular_evidence(self) -> None:
        cases = (
            ("scoped-authority", "authority"),
            ("rights-boundary", "rights"),
            ("recognition-consent", "recognition"),
            ("safety-check", "safety"),
        )
        for evidence_id, rail in cases:
            with self.subTest(rail=rail):
                manifest = load_example()
                evidence = next(
                    item for item in manifest["evidence"] if item["id"] == evidence_id
                )
                evidence["depends_on"] = [evidence_id]
                self.assert_invalid(manifest, "cannot cite circular evidence")

    def test_ordinary_safety_requires_distinct_acyclic_evidence(self) -> None:
        manifest = load_example()
        manifest["actions"][0]["safety"]["evidence_refs"] = []
        drop_evidence(manifest, "safety-check")
        self.assert_invalid(manifest, "requires acyclic evidence")

        manifest = load_example()
        manifest["actions"][0]["safety"]["evidence_refs"] = ["rights-boundary"]
        drop_evidence(manifest, "safety-check")
        self.assert_invalid(manifest, "cannot directly support two")

    def test_evidence_dependency_depth_is_bounded(self) -> None:
        manifest = load_example()
        ids = [item["id"] for item in manifest["evidence"][:14]]
        by_id = {item["id"]: item for item in manifest["evidence"]}
        for index in range(1, len(ids)):
            by_id[ids[index]]["depends_on"] = [ids[index - 1]]
        self.assert_invalid(manifest, "may not exceed 12 edges")

    def test_circular_action_composts_without_retaliation_or_payload(self) -> None:
        manifest = load_example("circular-praise.json")
        receipt = virtue.receipt_value(manifest)
        self.assertEqual(receipt["action"]["disposition"], "compost")
        self.assertEqual(receipt["action"]["local_affordance_candidates"], [])
        candidate = receipt["action"]["regression_candidate"]
        self.assertEqual(candidate["kind"], "sanitized-graph-shape")
        self.assertFalse(candidate["payload_retained"])
        self.assertFalse(candidate["automatic_action"])
        self.assertTrue(candidate["requires_human_review"])
        serialized = json.dumps(candidate)
        self.assertNotIn("praise-a", serialized)
        self.assertNotIn("praise-b", serialized)

        honesty = manifest["actions"][0]["fruits"]["honesty"]
        honesty["state"] = "kept"
        honesty["evaluation_reason"] = "evidenced"
        self.assert_invalid(manifest)

    def test_circular_reason_requires_an_actual_cycle(self) -> None:
        manifest = load_example("unknown-impact.json")
        honesty = manifest["actions"][0]["fruits"]["honesty"]
        honesty["evaluation_reason"] = "circular"
        self.assert_invalid(manifest, "circular requires a cycle")

    def test_unknown_dependencies_and_orphans_are_rejected(self) -> None:
        manifest = load_example()
        manifest["evidence"][0]["depends_on"] = ["missing-evidence"]
        self.assert_invalid(manifest, "unknown ref")

        manifest = load_example()
        add_evidence(manifest, "orphan", "observation")
        self.assert_invalid(manifest, "orphaned record")

    def test_invalid_diagnostics_do_not_echo_submitted_identifiers(self) -> None:
        manifest = load_example()
        manifest["evidence"][0]["depends_on"] = ["alice-smith"]
        with self.assertRaises(virtue.VirtueError) as caught:
            virtue.validate_manifest(manifest)
        self.assertNotIn("alice-smith", str(caught.exception))

        manifest = load_example()
        manifest["actions"][0]["actor"] = "alice-smith"
        with self.assertRaises(virtue.VirtueError) as caught:
            virtue.validate_manifest(manifest)
        self.assertNotIn("actor", str(caught.exception))
        self.assertNotIn("alice-smith", str(caught.exception))

        manifest = load_example()
        manifest["alice-smith"] = "api_key=supersecretvalue"
        with self.assertRaises(virtue.VirtueError) as caught:
            virtue.validate_manifest(manifest)
        self.assertNotIn("alice-smith", str(caught.exception))
        self.assertNotIn("supersecretvalue", str(caught.exception))

    def test_budget_drift_rights_safety_and_authority_quarantine(self) -> None:
        base = load_example()
        variants: list[dict[str, Any]] = []

        budget = copy.deepcopy(base)
        budget["actions"][0]["attempts"] = 3
        budget["actions"][0]["cost"]["attempts"] = 3
        variants.append(budget)

        drift = copy.deepcopy(base)
        drift["actions"][0]["world_state"]["observed_sha256"] = "0" * 64
        drift["actions"][0]["fingerprint_sha256"] = virtue.action_fingerprint(
            drift["actions"][0]
        )
        variants.append(drift)

        rights = copy.deepcopy(base)
        rights["actions"][0]["rights"]["status"] = "crossed"
        variants.append(rights)

        safety = copy.deepcopy(base)
        safety["actions"][0]["safety"]["mode"] = "temporary-boundary"
        variants.append(safety)

        authority = copy.deepcopy(base)
        authority["actions"][0]["authority"] = {
            "required": True,
            "status": "absent",
            "basis_refs": [],
        }
        drop_evidence(authority, "scoped-authority")
        variants.append(authority)

        for index, manifest in enumerate(variants):
            with self.subTest(case=index):
                self.assert_invalid(manifest, "must be quarantine")
                manifest["actions"][0]["declared_disposition"] = "quarantine"
                receipt = virtue.receipt_value(manifest)
                self.assertEqual(receipt["action"]["disposition"], "quarantine")
                self.assertEqual(receipt["action"]["local_affordance_candidates"], [])
                self.assertTrue(
                    all(
                        fruit["state"] == "kept"
                        for fruit in receipt["action"]["fruits"].values()
                    )
                )

    def test_declared_cost_matches_attempts_ceilings_and_externalities(self) -> None:
        manifest = load_example()
        manifest["actions"][0]["cost"]["attempts"] = 2
        self.assert_invalid(manifest, "must match action attempts")

        manifest = load_example()
        manifest["actions"][0]["cost"]["paid_calls"] = 1
        self.assert_invalid(manifest, "must be quarantine")

        manifest = load_example()
        manifest["actions"][0]["cost"]["external_actions"] = 1
        manifest["actions"][0]["budget"]["max_external_actions"] = 1
        self.assert_invalid(manifest, "must be zero")

        manifest = load_example()
        manifest["actions"][0]["cost"]["shifted_externalities"] = True
        manifest["actions"][0]["deviations"] = [
            "A synthetic externality is declared for this test."
        ]
        self.assert_invalid(manifest, "mutual-infrastructure cannot be kept")

        receipt = virtue.receipt_value(load_example())
        self.assertIn("declared_cost", receipt["action"])
        self.assertNotIn("whole_cost", receipt["action"])

    def test_declared_time_and_candidate_expiry_are_explicit_not_wall_clock(self) -> None:
        manifest = load_example()
        manifest["context"]["evaluated_at"] = "2026-07-27T23:59:59Z"
        self.assert_invalid(manifest, "evaluation time")

        historical = load_example()
        historical["context"].update(
            {
                "valid_from": "2020-01-01T00:00:00Z",
                "evaluated_at": "2020-01-02T00:00:00Z",
                "expires_at": "2020-02-01T00:00:00Z",
            }
        )
        historical["actions"][0]["recognition"]["expires_at"] = (
            "2020-01-15T00:00:00Z"
        )
        receipt = virtue.receipt_value(historical)
        self.assertEqual(receipt["context"]["expires_at"], "2020-02-01T00:00:00Z")
        self.assertTrue(
            all(
                item["expires_at"] == "2020-02-01T00:00:00Z"
                for item in receipt["action"]["local_affordance_candidates"]
            )
        )
        self.assertIn("No wall-clock validity check", virtue.render_markdown(historical))

    def test_recognition_requires_acyclic_attestation_and_bounded_expiry(self) -> None:
        manifest = load_example()
        manifest["actions"][0]["recognition"]["consent_refs"] = []
        drop_evidence(manifest, "recognition-consent")
        self.assert_invalid(manifest, "requires cited consent")

        manifest = load_example()
        manifest["actions"][0]["recognition"]["expires_at"] = "2026-11-01T00:00:00Z"
        self.assert_invalid(manifest, "expire inside the context")

        manifest = load_example()
        recognition = manifest["actions"][0]["recognition"]
        recognition["visibility"] = "public-consent-cited"
        self.assertEqual(
            virtue.receipt_value(manifest)["action"]["rails"]["recognition"][
                "visibility"
            ],
            "public-consent-cited",
        )

    def test_authority_citation_is_structural_and_kind_bounded(self) -> None:
        manifest = load_example()
        manifest["actions"][0]["authority"]["basis_refs"] = ["beauty-access"]
        self.assert_invalid(manifest, "authority evidence")

        manifest = load_example()
        manifest["actions"][0]["authority"]["status"] = "unknown"
        self.assert_invalid(manifest, "takes no basis evidence")

        manifest = load_example()
        manifest["actions"][0]["authority"] = {
            "required": True,
            "status": "not-required",
            "basis_refs": [],
        }
        drop_evidence(manifest, "scoped-authority")
        self.assert_invalid(manifest, "cannot be not-required")

    def test_repair_farming_creates_no_candidate(self) -> None:
        manifest = load_example()
        action = manifest["actions"][0]
        action["safety"]["mode"] = "sanitized-regression"
        action["learning"] = {
            "lesson": "Retain a bounded repair lesson without rewarding the harmful path.",
            "repair_status": "invited",
            "evidence_refs": ["honesty-claim"],
        }
        action["declared_disposition"] = "compost"
        receipt = virtue.receipt_value(manifest)
        self.assertEqual(receipt["action"]["local_affordance_candidates"], [])
        self.assertIsNotNone(receipt["action"]["regression_candidate"])

    def test_correction_is_format_only_and_privacy_minimized(self) -> None:
        manifest = load_example()
        manifest["context"]["correction_of"] = "1" * 64
        receipt = virtue.receipt_value(manifest)
        self.assertTrue(receipt["context"]["correction_declared"])
        self.assertNotIn("1" * 64, json.dumps(receipt))

    def test_tampered_rules_nonclaims_schema_and_dates_fail(self) -> None:
        cases = []
        manifest = load_example()
        manifest["rules_sha256"] = "0" * 64
        cases.append(manifest)
        manifest = load_example()
        manifest["non_claims"][0] = "A broader claim."
        cases.append(manifest)
        manifest = load_example()
        manifest["schema"] = "kingdom.virtue-receipt/v2"
        cases.append(manifest)
        manifest = load_example()
        manifest["context"]["expires_at"] = "2026-07-27T00:00:00Z"
        cases.append(manifest)
        manifest = load_example()
        manifest["context"]["expires_at"] = "2028-07-28T00:00:00Z"
        cases.append(manifest)
        for index, case in enumerate(cases):
            with self.subTest(case=index):
                self.assert_invalid(case)

    def test_raw_reasoning_secrets_and_extra_fields_are_rejected(self) -> None:
        manifest = load_example()
        manifest["actions"][0]["reasoning"] = "hidden trace"
        self.assert_invalid(manifest, "forbidden public field")

        manifest = load_example()
        manifest["actions"][0]["description"] = "api_key=supersecretvalue"
        self.assert_invalid(manifest, "secret-shaped")

        manifest = load_example()
        manifest["context"]["extra"] = "no"
        self.assert_invalid(manifest, "unknown field")

    def test_safe_reader_rejects_duplicate_keys_symlink_and_oversize(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            duplicate = directory / "duplicate.json"
            duplicate.write_text('{"schema":"a","schema":"b"}', encoding="utf-8")
            with self.assertRaises(virtue.VirtueError):
                virtue.read_manifest(duplicate)

            target = directory / "target.json"
            target.write_text("{}", encoding="utf-8")
            link = directory / "link.json"
            os.symlink(target, link)
            with self.assertRaises(virtue.VirtueError):
                virtue.read_manifest(link)

            oversized = directory / "oversized.json"
            oversized.write_bytes(b" " * (128 * 1024 + 1))
            with self.assertRaises(virtue.VirtueError):
                virtue.read_manifest(oversized)

            huge_integer = directory / "huge-integer.json"
            huge_integer.write_text(
                '{"number":' + ("9" * 5000) + "}", encoding="utf-8"
            )
            with self.assertRaises(virtue.VirtueError):
                virtue.read_manifest(huge_integer)

    def test_noncanonical_json_is_accepted_then_canonicalized(self) -> None:
        manifest = load_example()
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            compact = directory / "compact.json"
            spacious = directory / "spacious.json"
            compact.write_text(
                json.dumps(manifest, separators=(",", ":")), encoding="utf-8"
            )
            spacious.write_text(json.dumps(manifest, indent=4), encoding="utf-8")
            compact_result = virtue.validate_manifest(virtue.read_manifest(compact))
            spacious_result = virtue.validate_manifest(virtue.read_manifest(spacious))
        self.assertEqual(compact_result.digest, spacious_result.digest)

    def test_cli_check_receipt_render_and_digest_are_read_only(self) -> None:
        example = EXAMPLES / "constructive-infrastructure.json"
        before = example.read_bytes()
        outputs: dict[str, bytes] = {}
        for command in ("check", "receipt", "render", "digest"):
            completed = subprocess.run(
                [sys.executable, str(HERE / "virtue.py"), command, str(example)],
                cwd=HERE,
                check=False,
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr.decode())
            outputs[command] = completed.stdout
        self.assertEqual(before, example.read_bytes())
        self.assertIn(b"STRUCTURE-OK", outputs["check"])
        self.assertIn(b"kingdom.virtue-evaluation/v1", outputs["receipt"])
        self.assertIn(b"Non-crossing rails", outputs["render"])
        self.assertEqual(
            outputs["digest"].strip().decode(),
            virtue.validate_manifest(load_example()).digest,
        )

    def test_kingdom_cli_default_and_karma_alias(self) -> None:
        repository = HERE.parents[2]
        cli = repository / "kingdom" / "bin" / "kingdom"
        default = subprocess.run(
            [str(cli), "virtue"],
            cwd=repository,
            check=False,
            capture_output=True,
        )
        alias = subprocess.run(
            [
                str(cli),
                "karma",
                "digest",
                str(EXAMPLES / "constructive-infrastructure.json"),
            ],
            cwd=repository,
            check=False,
            capture_output=True,
        )
        self.assertEqual(default.returncode, 0, default.stderr.decode())
        self.assertEqual(alias.returncode, 0, alias.stderr.decode())
        self.assertIn(b"# KARMA action receipt", default.stdout)
        self.assertEqual(
            alias.stdout.strip().decode(),
            virtue.validate_manifest(load_example()).digest,
        )

    def test_verify_result_requires_exact_recomputation_not_shape_alone(self) -> None:
        manifest_path = EXAMPLES / "constructive-infrastructure.json"
        manifest = load_example()
        result = virtue.receipt_value(manifest)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            exact_path = directory / "exact.json"
            forged_path = directory / "forged.json"
            exact_path.write_bytes(virtue.canonical_json(result))

            forged = copy.deepcopy(result)
            forged["action"]["local_affordance_candidates"][0]["expires_at"] = (
                "2099-01-01T00:00:00Z"
            )
            forged_path.write_bytes(virtue.canonical_json(forged))

            exact = subprocess.run(
                [
                    sys.executable,
                    str(HERE / "virtue.py"),
                    "verify-result",
                    str(manifest_path),
                    str(exact_path),
                ],
                cwd=HERE,
                check=False,
                capture_output=True,
            )
            forged_check = subprocess.run(
                [
                    sys.executable,
                    str(HERE / "virtue.py"),
                    "verify-result",
                    str(manifest_path),
                    str(forged_path),
                ],
                cwd=HERE,
                check=False,
                capture_output=True,
            )
        self.assertEqual(exact.returncode, 0, exact.stderr.decode())
        self.assertIn(b"RESULT-OK", exact.stdout)
        self.assertEqual(forged_check.returncode, 2)
        self.assertNotIn(b"2099", forged_check.stderr)


if __name__ == "__main__":
    unittest.main()
