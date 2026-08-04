from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock
from urllib.parse import urlsplit


HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "facet.py"
REPOSITORY = HERE.parents[5]
PUBLIC = REPOSITORY / "site" / "practices" / "virtue-garden" / "mirror" / "foresight" / "facet"
EXAMPLE = HERE / "examples" / "synthetic-authority-boundary.json"
EXAMPLE_PROJECTION = HERE / "examples" / "authority-foresight-projection.json"

sys.path.insert(0, str(ENGINE.parent))
import facet  # noqa: E402


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def catalog() -> dict[str, Any]:
    return load_json(HERE / "catalog.json")


def playbook() -> dict[str, Any]:
    return load_json(HERE / "playbook.json")


def foresight_scenario(source_rule: dict[str, Any]) -> dict[str, Any]:
    source = facet.foresight_core._catalog()
    return {
        "schema": source["scenario_schema"],
        "kind": "offline-system-effect-projection",
        "catalog_sha256": facet.foresight_core.EXPECTED_CATALOG_SHA256,
        "declaration": {
            "constellation": source_rule["constellation"],
            "mechanism": source_rule["mechanism"],
            "system_effect_hypothesis": source_rule["system_effect_hypothesis"],
            "boundary_signal": source_rule["boundary_signal"],
            "alternative_hypothesis": source_rule["alternative_hypothesis"],
        },
        "contract": copy.deepcopy(source["contract"]),
        "budget": copy.deepcopy(source["budget"]),
        "breach": copy.deepcopy(source["breach"]),
        "exit": copy.deepcopy(source["exit"]),
        "non_claims": copy.deepcopy(source["non_claims"]),
    }


def pair_for(rule: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    source_rule = next(
        item
        for item in facet.foresight_core._catalog()["rules"]
        if item["constellation"] == rule["constellation"]
    )
    scenario = foresight_scenario(source_rule)
    return scenario, facet.foresight_core.project_value(scenario)


def card_for(
    rule: dict[str, Any],
    scenario: dict[str, Any],
    projection: dict[str, Any],
    *,
    stimulus: str | None = None,
    review_request: str = "triage",
) -> dict[str, Any]:
    reviewed_catalog = catalog()
    reviewed_playbook = playbook()
    if stimulus is None:
        stimulus = (
            "unresolved-novelty"
            if rule["constellation"] == "uncharted-future-shape"
            else "new-authored-claim"
        )
    allowed = next(
        item["allowed"]
        for item in reviewed_playbook["rung_allowlists"]
        if item["rung"] == rule["response_rung"]
    )
    return {
        "schema": "kingdom.karma-facet/v1",
        "kind": "offline-incident-legibility",
        "catalog_sha256": facet.EXPECTED_CATALOG_SHA256,
        "playbook_sha256": facet.EXPECTED_PLAYBOOK_SHA256,
        "lineage": {"mode": "genesis", "previous_snapshot_sha256": None},
        "foresight_binding": {
            "scenario_sha256": facet.digest_value(scenario),
            "projection_sha256": facet.digest_value(projection),
            "constellation": rule["constellation"],
            "response_rung": rule["response_rung"],
        },
        "stimulus": stimulus,
        "review_request": review_request,
        "planes": {
            "observed": [
                {
                    "fact_code": rule["fact_code"],
                    "evidence_shape": "none",
                    "check_state": "unresolved",
                }
            ],
            "declared": {
                "scope_code": rule["scope_code"],
                "constellation": rule["constellation"],
                "alternative_hypothesis": rule["alternative_hypothesis"],
            },
            "inferred": {
                "system_effect_hypothesis": rule["system_effect_hypothesis"],
                "effect_established": False,
                "person_intent_inferred": False,
            },
            "unknown": [reviewed_catalog["unknown_codes"][0]],
        },
        "precommit": [
            {"safety_shim_code": allowed[0], "condition_state": "unknown"}
        ],
        "receipts": {slot: None for slot in facet.RECEIPT_SLOTS},
        "contract": copy.deepcopy(reviewed_catalog["contract"]),
        "budget": copy.deepcopy(reviewed_catalog["budget"]),
        "breach": copy.deepcopy(reviewed_catalog["breach"]),
        "exit": copy.deepcopy(reviewed_catalog["exit"]),
        "non_claims": copy.deepcopy(reviewed_catalog["non_claims"]),
    }


def cited_receipt(slot: str, *, digest: str | None = None, lineage: str = "single-source") -> dict[str, Any]:
    if digest is None:
        digest = hashlib.sha256(f"synthetic-facet-{slot}".encode("utf-8")).hexdigest()
    return {
        "status": "receipt-cited",
        "sanitized_receipt_sha256": digest,
        "method": "canonical-byte-check",
        "lineage": lineage,
    }


class KarmaFacetTests(unittest.TestCase):
    maxDiff = None

    def assert_invalid(self, value: dict[str, Any], code: str | None = None) -> None:
        with self.assertRaises(facet.FacetError) as caught:
            facet.validate_card(value)
        if code is not None:
            self.assertEqual(caught.exception.code, code)

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [sys.executable, "-B", str(ENGINE), *args],
            cwd=ENGINE.parent,
            env=environment,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )

    def test_reviewed_documents_are_canonical_digest_pinned(self) -> None:
        documents = {
            "catalog.json": facet.EXPECTED_CATALOG_SHA256,
            "playbook.json": facet.EXPECTED_PLAYBOOK_SHA256,
            "facet.schema.json": facet.EXPECTED_FACET_SCHEMA_SHA256,
            "brief.schema.json": facet.EXPECTED_BRIEF_SCHEMA_SHA256,
        }
        for name, expected in documents.items():
            with self.subTest(name=name):
                self.assertEqual(facet.digest_value(load_json(HERE / name)), expected)

    def test_catalog_exactly_binds_all_ten_foresight_rule_pairs(self) -> None:
        facet_rules = catalog()["rules"]
        foresight_rules = facet.foresight_core._catalog()["rules"]
        self.assertEqual(len(facet_rules), 10)
        self.assertEqual(
            [rule["constellation"] for rule in facet_rules],
            [rule["constellation"] for rule in foresight_rules],
        )
        for rule, source in zip(facet_rules, foresight_rules, strict=True):
            with self.subTest(constellation=rule["constellation"]):
                self.assertEqual(
                    (
                        rule["constellation"],
                        rule["response_rung"],
                        rule["system_effect_hypothesis"],
                        rule["alternative_hypothesis"],
                    ),
                    (
                        source["constellation"],
                        source["response_rung"],
                        source["system_effect_hypothesis"],
                        source["alternative_hypothesis"],
                    ),
                )

    def test_input_schema_four_planes_are_enum_closed_and_match_catalog(self) -> None:
        schema = load_json(HERE / "facet.schema.json")
        rules = catalog()["rules"]
        planes = schema["$defs"]["planes"]["properties"]
        observed = schema["$defs"]["observed"]["properties"]
        declared = planes["declared"]["properties"]
        inferred = planes["inferred"]["properties"]
        self.assertEqual(set(observed["fact_code"]["enum"]), {rule["fact_code"] for rule in rules})
        self.assertEqual(set(declared["scope_code"]["enum"]), {rule["scope_code"] for rule in rules})
        self.assertIn("enum", declared["constellation"], "declared constellation must be enum-closed")
        self.assertEqual(set(declared["constellation"]["enum"]), {rule["constellation"] for rule in rules})
        self.assertIn(
            "enum",
            declared["alternative_hypothesis"],
            "declared alternative must be enum-closed",
        )
        self.assertEqual(
            set(declared["alternative_hypothesis"]["enum"]),
            {rule["alternative_hypothesis"] for rule in rules},
        )
        self.assertIn(
            "enum",
            inferred["system_effect_hypothesis"],
            "inferred system effect must be enum-closed",
        )
        self.assertEqual(
            set(inferred["system_effect_hypothesis"]["enum"]),
            {rule["system_effect_hypothesis"] for rule in rules},
        )
        self.assertEqual(set(planes["unknown"]["items"]["enum"]), set(catalog()["unknown_codes"]))

    def test_synthetic_fixture_and_projection_are_exactly_recomputable(self) -> None:
        self.assertTrue(EXAMPLE.exists(), "synthetic fixture must be present once integration lands")
        card = load_json(EXAMPLE)
        rule = catalog()["rules"][0]
        scenario, projection = pair_for(rule)
        self.assertEqual(projection, load_json(EXAMPLE_PROJECTION))
        self.assertEqual(facet.digest_value(scenario), card["foresight_binding"]["scenario_sha256"])
        self.assertEqual(facet.digest_value(projection), card["foresight_binding"]["projection_sha256"])
        self.assertEqual(facet.validate_card(card), rule)
        brief = facet.brief_value(card, scenario, projection)
        self.assertEqual(facet.verify_result(card, scenario, projection, brief), facet.digest_value(brief))

    def test_all_ten_rules_compile_deterministic_inert_briefs(self) -> None:
        for rule in catalog()["rules"]:
            with self.subTest(constellation=rule["constellation"]):
                scenario, projection = pair_for(rule)
                card = card_for(rule, scenario, projection)
                first = facet.brief_value(card, scenario, projection)
                second = facet.brief_value(copy.deepcopy(card), copy.deepcopy(scenario), copy.deepcopy(projection))
                self.assertEqual(facet.canonical_json(first), facet.canonical_json(second))
                self.assertLessEqual(len(facet.canonical_json(first)), facet.MAX_OUTPUT_BYTES)
                self.assertEqual(first["card_sha256"], facet.digest_value(card))
                self.assertEqual(first["foresight_binding"]["constellation"], rule["constellation"])
                self.assertEqual(first["foresight_binding"]["response_rung"], rule["response_rung"])
                self.assertTrue(first["foresight_binding"]["exact_recomputation"])
                self.assertEqual(first["planes"], card["planes"])
                self.assertEqual(first["lessons"][0]["repair_grain"], rule["repair_grain"])
                self.assertEqual([item["slot"] for item in first["evidence_debt"]], facet.RECEIPT_SLOTS)
                self.assertTrue(all(item["state"] == "open" for item in first["evidence_debt"]))
                self.assertTrue(all(not item["compiler_can_pay"] for item in first["evidence_debt"]))
                for key in (
                    "automatic_alert",
                    "automatic_ticket",
                    "automatic_enforcement",
                    "execution_authorized",
                    "executed",
                    "closure_authorized",
                    "publication_authorized",
                    "authority_granted",
                    "person_classified",
                    "external_effect",
                ):
                    self.assertFalse(first["response"][key], key)
                for key in (
                    "incident_occurrence_established",
                    "source_authenticity_verified",
                    "system_effect_established",
                    "cause_established",
                    "person_intent_inferred",
                    "person_attributed",
                ):
                    self.assertFalse(first["incident_claim"][key], key)

    def test_render_is_deterministic_bounded_and_omits_receipt_digests(self) -> None:
        rule = catalog()["rules"][0]
        scenario, projection = pair_for(rule)
        card = card_for(rule, scenario, projection)
        card["receipts"]["occurrence"] = cited_receipt("occurrence")
        first = facet.render_markdown(card, scenario, projection)
        second = facet.render_markdown(copy.deepcopy(card), copy.deepcopy(scenario), copy.deepcopy(projection))
        self.assertEqual(first, second)
        self.assertTrue(first.endswith("\n"))
        self.assertEqual(len(first.splitlines()), 12)
        self.assertIn("KARMA FACET · 稜面", first)
        self.assertIn("not established", first)
        self.assertIn("no detection, identity, blame, alert, action, closure", first)
        self.assertNotIn(card["receipts"]["occurrence"]["sanitized_receipt_sha256"], first)

    def test_every_stimulus_selects_one_exact_playbook_response(self) -> None:
        table = playbook()["response_table"]
        authority_rule = catalog()["rules"][0]
        unknown_rule = catalog()["rules"][-1]
        for stimulus in facet.STIMULI:
            rule = unknown_rule if stimulus == "unresolved-novelty" else authority_rule
            scenario, projection = pair_for(rule)
            card = card_for(
                rule,
                scenario,
                projection,
                stimulus=stimulus,
                review_request="closure-review" if stimulus == "closure-review-requested" else "triage",
            )
            result = facet.brief_value(card, scenario, projection)
            expected_order = "g6a" if stimulus == "closure-review-requested" else next(
                item["order"] for item in table if item["stimulus"] == stimulus
            )
            selected = next(item for item in table if item["order"] == expected_order)
            with self.subTest(stimulus=stimulus):
                self.assertEqual(result["response"]["rule"], expected_order)
                for key in ("guard", "candidate", "verification_candidate", "halt_if"):
                    self.assertEqual(result["response"][key], selected[key])
                self.assertFalse(result["response"]["external_effect"])

    def test_all_cited_distinct_g6b_is_only_a_human_review_candidate(self) -> None:
        rule = catalog()["rules"][0]
        scenario, projection = pair_for(rule)
        card = card_for(
            rule,
            scenario,
            projection,
            stimulus="closure-review-requested",
            review_request="closure-review",
        )
        card["receipts"] = {
            slot: cited_receipt(slot) for slot in facet.RECEIPT_SLOTS
        }
        result = facet.brief_value(card, scenario, projection)
        self.assertEqual(result["response"]["rule"], "g6b")
        self.assertEqual(result["response"]["candidate"], "fresh-human-closure-review-candidate")
        self.assertEqual(result["readiness"]["critical_open_slots"], [])
        self.assertTrue(result["readiness"]["all_receipt_shapes_cited"])
        self.assertTrue(result["readiness"]["distinct_receipt_commitments"])
        self.assertTrue(result["readiness"]["fresh_human_closure_review_candidate"])
        self.assertFalse(result["readiness"]["incident_truth_verified"])
        self.assertFalse(result["readiness"]["authenticity_verified"])
        self.assertFalse(result["readiness"]["privacy_release_authorized"])
        self.assertFalse(result["readiness"]["closure_authorized"])
        self.assertFalse(result["response"]["closure_authorized"])
        self.assertFalse(result["exit"]["closure_created"])
        self.assertTrue(all(item["state"] == "receipt-cited" for item in result["evidence_debt"]))
        self.assertTrue(all(not item["compiler_can_pay"] for item in result["evidence_debt"]))

    def test_receipt_independence_conflicts_and_shared_commitments_do_not_multiply_support(self) -> None:
        rule = catalog()["rules"][0]
        scenario, projection = pair_for(rule)
        card = card_for(
            rule,
            scenario,
            projection,
            stimulus="closure-review-requested",
            review_request="closure-review",
        )
        shared = hashlib.sha256(b"one-shared-synthetic-receipt").hexdigest()
        card["receipts"]["scope-authority"] = cited_receipt(
            "scope-authority", digest=shared, lineage="independence-claimed"
        )
        card["receipts"]["containment"] = cited_receipt(
            "containment", digest=shared, lineage="shared-source"
        )
        self.assert_invalid(card, "receipt-independence-conflict")

        card["receipts"] = {
            slot: cited_receipt(slot) for slot in facet.RECEIPT_SLOTS
        }
        card["receipts"]["scope-authority"] = cited_receipt(
            "scope-authority", digest=shared, lineage="shared-source"
        )
        card["receipts"]["containment"] = cited_receipt(
            "containment", digest=shared, lineage="shared-source"
        )
        result = facet.brief_value(card, scenario, projection)
        debts = {item["slot"]: item for item in result["evidence_debt"]}
        self.assertEqual(result["response"]["rule"], "g6a")
        self.assertFalse(result["readiness"]["distinct_receipt_commitments"])
        self.assertTrue(debts["scope-authority"]["receipt_cites_shared_digest"])
        self.assertTrue(debts["containment"]["receipt_cites_shared_digest"])
        self.assertIn("scope-authority", result["readiness"]["critical_open_slots"])
        self.assertIn("containment", result["readiness"]["critical_open_slots"])

    def test_receipt_object_key_order_is_not_semantic(self) -> None:
        rule = catalog()["rules"][0]
        scenario, projection = pair_for(rule)
        card = card_for(rule, scenario, projection)
        card["receipts"] = dict(reversed(list(card["receipts"].items())))
        try:
            validated = facet.validate_card(card)
        except facet.FacetError as error:
            self.fail(f"JSON object member order changed card semantics: {error.code}")
        self.assertEqual(validated, rule)

    def test_engine_canonical_json_round_trip_remains_a_valid_card(self) -> None:
        rule = catalog()["rules"][0]
        scenario, projection = pair_for(rule)
        card = card_for(rule, scenario, projection)
        decoded = json.loads(facet.canonical_json(card))
        try:
            validated = facet.validate_card(decoded)
        except facet.FacetError as error:
            self.fail(f"engine canonical JSON does not round-trip through its validator: {error.code}")
        self.assertEqual(validated, rule)

    def test_uncharted_rule_is_novelty_observe_only(self) -> None:
        rule = catalog()["rules"][-1]
        scenario, projection = pair_for(rule)
        card = card_for(rule, scenario, projection)
        result = facet.brief_value(card, scenario, projection)
        self.assertEqual(card["stimulus"], "unresolved-novelty")
        self.assertEqual(result["foresight_binding"]["response_rung"], "observe")
        self.assertEqual(result["response"]["rule"], "g8")
        self.assertEqual(result["response"]["candidate"], "observe-only")
        self.assertFalse(result["response"]["execution_authorized"])

        card["stimulus"] = "new-authored-claim"
        self.assert_invalid(card, "novelty-binding-mismatch")
        ordinary = catalog()["rules"][0]
        scenario, projection = pair_for(ordinary)
        card = card_for(ordinary, scenario, projection, stimulus="unresolved-novelty")
        self.assert_invalid(card, "novelty-binding-mismatch")

    def test_cross_rule_recombination_fails_closed(self) -> None:
        first, second = catalog()["rules"][:2]
        scenario, projection = pair_for(first)
        mutations = [
            ("observed", "fact_code", second["fact_code"], "observed-value-mismatch"),
            ("declared", "scope_code", second["scope_code"], "declared-plane-mismatch"),
            (
                "declared",
                "alternative_hypothesis",
                second["alternative_hypothesis"],
                "declared-plane-mismatch",
            ),
            (
                "inferred",
                "system_effect_hypothesis",
                second["system_effect_hypothesis"],
                "inferred-plane-mismatch",
            ),
        ]
        for plane, key, replacement, code in mutations:
            with self.subTest(plane=plane, key=key):
                card = card_for(first, scenario, projection)
                target = card["planes"][plane]
                if isinstance(target, list):
                    target[0][key] = replacement
                else:
                    target[key] = replacement
                self.assert_invalid(card, code)

        card = card_for(first, scenario, projection)
        card["foresight_binding"]["constellation"] = second["constellation"]
        self.assert_invalid(card, "foresight-binding-category-mismatch")

    def test_foresight_binding_rejects_other_valid_pairs_and_tampering(self) -> None:
        first, second = catalog()["rules"][:2]
        first_scenario, first_projection = pair_for(first)
        second_scenario, second_projection = pair_for(second)
        card = card_for(first, first_scenario, first_projection)
        with self.assertRaises(facet.FacetError) as caught:
            facet.brief_value(card, second_scenario, second_projection)
        self.assertEqual(caught.exception.code, "foresight-binding-mismatch")

        changed = copy.deepcopy(first_projection)
        changed["response"]["executed"] = True
        with self.assertRaises(facet.FacetError) as caught:
            facet.brief_value(card, first_scenario, changed)
        self.assertEqual(caught.exception.code, "foresight-binding-invalid")

        changed = copy.deepcopy(card)
        changed["foresight_binding"]["projection_sha256"] = "0" * 64
        with self.assertRaises(facet.FacetError) as caught:
            facet.brief_value(changed, first_scenario, first_projection)
        self.assertEqual(caught.exception.code, "foresight-binding-mismatch")

    def test_unknown_fields_and_forbidden_raw_person_time_severity_cause_fields_reject(self) -> None:
        rule = catalog()["rules"][0]
        scenario, projection = pair_for(rule)
        forbidden = (
            "raw_evidence",
            "evidence_body",
            "payload",
            "log",
            "trace",
            "prompt",
            "address",
            "ip",
            "identity",
            "credential",
            "target",
            "command",
            "url",
            "timestamp",
            "time",
            "ttl",
            "actor",
            "person",
            "suspect",
            "attacker",
            "victim",
            "intent",
            "guilt",
            "blame",
            "severity",
            "confidence",
            "score",
            "rank",
            "root_cause",
            "closed",
            "resolved",
        )
        for field in forbidden:
            with self.subTest(field=field):
                card = card_for(rule, scenario, projection)
                card[field] = "SENTINEL-NEVER-ECHO"
                self.assert_invalid(card, "card-shape-mismatch")

        nested_mutations = (
            ("planes", "extra"),
            ("foresight_binding", "actor"),
            ("lineage", "timestamp"),
        )
        for section, field in nested_mutations:
            with self.subTest(section=section, field=field):
                card = card_for(rule, scenario, projection)
                card[section][field] = "SENTINEL-NEVER-ECHO"
                expected = {
                    "planes": "planes-shape-mismatch",
                    "foresight_binding": "foresight-binding-shape-mismatch",
                    "lineage": "lineage-shape-mismatch",
                }[section]
                self.assert_invalid(card, expected)

    def test_card_contract_is_json_type_strict(self) -> None:
        rule = catalog()["rules"][0]
        scenario, projection = pair_for(rule)
        mutations: list[tuple[str, str, Any, str]] = [
            ("contract", "occurrence_established", 0, "contract-mismatch"),
            ("contract", "automatic_closure", 0, "contract-mismatch"),
            ("budget", "network_calls", False, "budget-mismatch"),
            ("budget", "clock_reads", False, "budget-mismatch"),
            ("breach", "submitted_values_echoed", 0, "breach-mismatch"),
            ("exit", "closure_created", 0, "exit-mismatch"),
        ]
        for section, key, replacement, code in mutations:
            with self.subTest(section=section, key=key):
                card = card_for(rule, scenario, projection)
                card[section][key] = replacement
                self.assert_invalid(card, code)

        card = card_for(rule, scenario, projection)
        card["planes"]["inferred"]["effect_established"] = 0
        self.assert_invalid(card, "inferred-plane-mismatch")
        card = card_for(rule, scenario, projection)
        card["lineage"] = [card["lineage"]]
        self.assert_invalid(card, "lineage-shape-mismatch")
        card = card_for(rule, scenario, projection)
        card["planes"]["unknown"] = [0]
        self.assert_invalid(card, "unknown-plane-mismatch")

    def test_card_rejects_duplicate_observations_unknowns_and_shims(self) -> None:
        rule = catalog()["rules"][0]
        scenario, projection = pair_for(rule)
        card = card_for(rule, scenario, projection)
        card["planes"]["observed"].append(copy.deepcopy(card["planes"]["observed"][0]))
        self.assert_invalid(card, "duplicate-observation")

        card = card_for(rule, scenario, projection)
        card["planes"]["unknown"].append(card["planes"]["unknown"][0])
        self.assert_invalid(card, "unknown-plane-mismatch")

        card = card_for(rule, scenario, projection)
        duplicate = copy.deepcopy(card["precommit"][0])
        duplicate["condition_state"] = "met"
        card["precommit"].append(duplicate)
        self.assert_invalid(card, "precommit-value-mismatch")

    def test_none_evidence_shape_requires_an_unresolved_check_state(self) -> None:
        rule = catalog()["rules"][0]
        scenario, projection = pair_for(rule)
        for check_state in ("receipt-cited", "contested"):
            with self.subTest(check_state=check_state):
                card = card_for(rule, scenario, projection)
                card["planes"]["observed"][0]["check_state"] = check_state
                self.assert_invalid(card, "observed-value-mismatch")

    def test_brief_tampering_fails_exact_recomputation_type_strictly(self) -> None:
        rule = catalog()["rules"][0]
        scenario, projection = pair_for(rule)
        card = card_for(rule, scenario, projection)
        result = facet.brief_value(card, scenario, projection)
        mutations = [
            ("response", "executed", True),
            ("response", "executed", 0),
            ("response", "closure_authorized", True),
            ("incident_claim", "person_attributed", True),
            ("readiness", "closure_authorized", True),
            ("lineage_claim", "latest_state_established", True),
            ("exit", "closure_created", True),
        ]
        for section, key, replacement in mutations:
            with self.subTest(section=section, key=key):
                changed = copy.deepcopy(result)
                changed[section][key] = replacement
                with self.assertRaises(facet.FacetError) as caught:
                    facet.verify_result(card, scenario, projection, changed)
                self.assertEqual(caught.exception.code, "result-mismatch")
        changed = copy.deepcopy(result)
        changed["extra"] = False
        with self.assertRaises(facet.FacetError):
            facet.verify_result(card, scenario, projection, changed)

    def test_predecessor_link_proves_only_one_canonical_content_relation(self) -> None:
        rule = catalog()["rules"][0]
        scenario, projection = pair_for(rule)
        previous = card_for(rule, scenario, projection)
        current = copy.deepcopy(previous)
        current["lineage"] = {
            "mode": "successor",
            "previous_snapshot_sha256": facet.digest_value(previous),
        }
        self.assertEqual(facet.verify_link(previous, current), facet.digest_value(current))
        result = facet.brief_value(current, scenario, projection)
        self.assertFalse(result["lineage_claim"]["predecessor_verified"])
        self.assertFalse(result["lineage_claim"]["chronology_established"])
        self.assertFalse(result["lineage_claim"]["latest_state_established"])

        changed_previous = copy.deepcopy(previous)
        changed_previous["review_request"] = "investigation"
        with self.assertRaises(facet.FacetError) as caught:
            facet.verify_link(changed_previous, current)
        self.assertEqual(caught.exception.code, "snapshot-link-mismatch")
        with self.assertRaises(facet.FacetError):
            facet.verify_link(previous, previous)

    def test_reader_rejects_unsafe_paths_and_pathological_json(self) -> None:
        rule = catalog()["rules"][0]
        scenario, projection = pair_for(rule)
        card = card_for(rule, scenario, projection)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid = root / "valid.json"
            valid.write_bytes(facet.canonical_json(card))
            link = root / "link.json"
            link.symlink_to(valid)
            cases: list[tuple[Path, str]] = [
                (root, "facet-card-not-regular"),
                (link, "facet-card-unreadable"),
            ]

            oversized = root / "oversized.json"
            oversized.write_bytes(b"{" + b" " * facet.MAX_FILE_BYTES + b"}")
            cases.append((oversized, "facet-card-too-large"))
            duplicate = root / "duplicate.json"
            duplicate.write_text('{"schema":"a","schema":"b"}', encoding="utf-8")
            cases.append((duplicate, "duplicate-key"))
            nonfinite = root / "nonfinite.json"
            nonfinite.write_text('{"value":NaN}', encoding="utf-8")
            cases.append((nonfinite, "non-finite-number"))
            floating = root / "floating.json"
            floating.write_text('{"value":1.5}', encoding="utf-8")
            cases.append((floating, "unsupported-number"))
            huge = root / "huge.json"
            huge.write_text('{"value":12345678901}', encoding="utf-8")
            cases.append((huge, "number-out-of-range"))
            invalid_utf8 = root / "invalid-utf8.json"
            invalid_utf8.write_bytes(b'{"value":"\xff"}')
            cases.append((invalid_utf8, "facet-card-invalid-json"))
            control = root / "control.json"
            control.write_text('{"value":"\\u001b]52;clipboard"}', encoding="utf-8")
            cases.append((control, "control-character"))
            concealed = root / "concealed.json"
            concealed.write_text('{"value":"\\u202ehidden"}', encoding="utf-8")
            cases.append((concealed, "concealed-codepoint"))
            surrogate = root / "surrogate.json"
            surrogate.write_text('{"value":"\\ud800"}', encoding="utf-8")
            cases.append((surrogate, "invalid-unicode"))
            long_string = root / "long-string.json"
            long_string.write_text(json.dumps({"value": "x" * (facet.MAX_STRING + 1)}), encoding="utf-8")
            cases.append((long_string, "string-too-long"))
            too_deep: Any = "leaf"
            for _ in range(facet.MAX_DEPTH + 2):
                too_deep = {"x": too_deep}
            deep = root / "deep.json"
            deep.write_text(json.dumps(too_deep), encoding="utf-8")
            cases.append((deep, "too-deep"))
            parser_deep = root / "parser-deep.json"
            parser_deep.write_text('{"x":' * 1_500 + '"leaf"' + "}" * 1_500, encoding="utf-8")
            cases.append((parser_deep, "too-deep"))
            wide = root / "wide.json"
            wide.write_text(json.dumps({"x": list(range(facet.MAX_NODES + 1))}), encoding="utf-8")
            cases.append((wide, "too-many-nodes"))
            array_root = root / "array.json"
            array_root.write_text("[]", encoding="utf-8")
            cases.append((array_root, "facet-card-root-not-object"))
            if hasattr(os, "mkfifo"):
                fifo = root / "pipe.json"
                os.mkfifo(fifo)
                cases.append((fifo, "facet-card-not-regular"))

            for path, code in cases:
                with self.subTest(path=path.name, code=code):
                    with self.assertRaises(facet.FacetError) as caught:
                        facet._read_json(path, label="facet-card")
                    self.assertEqual(caught.exception.code, code)

    def test_reader_detects_change_during_held_read(self) -> None:
        rule = catalog()["rules"][0]
        scenario, projection = pair_for(rule)
        card = card_for(rule, scenario, projection)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "card.json"
            path.write_bytes(facet.canonical_json(card))
            real_fstat = facet.foresight_core.os.fstat
            calls = 0

            def changed_fstat(descriptor: int) -> Any:
                nonlocal calls
                current = real_fstat(descriptor)
                calls += 1
                if calls != 2:
                    return current
                return SimpleNamespace(
                    st_mode=current.st_mode,
                    st_size=current.st_size,
                    st_dev=current.st_dev,
                    st_ino=current.st_ino,
                    st_mtime_ns=current.st_mtime_ns,
                    st_ctime_ns=current.st_ctime_ns + 1,
                )

            with mock.patch.object(facet.foresight_core.os, "fstat", side_effect=changed_fstat):
                with self.assertRaises(facet.FacetError) as caught:
                    facet._read_json(path, label="facet-card")
            self.assertEqual(caught.exception.code, "facet-card-changed-during-read")

    def test_cli_round_trip_verify_result_and_link(self) -> None:
        rule = catalog()["rules"][0]
        scenario, projection = pair_for(rule)
        card = card_for(rule, scenario, projection)
        brief = facet.brief_value(card, scenario, projection)
        current = copy.deepcopy(card)
        current["lineage"] = {
            "mode": "successor",
            "previous_snapshot_sha256": facet.digest_value(card),
        }
        help_result = self.run_cli("--help")
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("kingdom incident", help_result.stdout)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            card_path = root / "card.json"
            scenario_path = root / "scenario.json"
            projection_path = root / "projection.json"
            brief_path = root / "brief.json"
            current_path = root / "current.json"
            card_path.write_text(
                json.dumps(card, ensure_ascii=False, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            scenario_path.write_bytes(facet.canonical_json(scenario))
            projection_path.write_bytes(facet.canonical_json(projection))
            brief_path.write_bytes(facet.canonical_json(brief))
            current_path.write_text(
                json.dumps(current, ensure_ascii=False, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            for command in ("check", "digest", "render"):
                with self.subTest(command=command):
                    result = self.run_cli(command, str(card_path), str(scenario_path), str(projection_path))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, "")
            result = self.run_cli("brief", str(card_path), str(scenario_path), str(projection_path))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.encode("utf-8"), facet.canonical_json(brief))
            result = self.run_cli(
                "verify-result",
                str(card_path),
                str(scenario_path),
                str(projection_path),
                str(brief_path),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("KARMA-FACET-RESULT-OK", result.stdout)
            self.assertIn("no incident truth", result.stdout)
            result = self.run_cli("verify-link", str(card_path), str(current_path))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("canonical predecessor relation only", result.stdout)

    def test_cli_rejections_never_echo_submitted_values_or_paths(self) -> None:
        sentinel = "SENTINEL-DO-NOT-ECHO"
        rule = catalog()["rules"][0]
        scenario, projection = pair_for(rule)
        card = card_for(rule, scenario, projection)
        card["payload"] = sentinel
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            card_path = root / f"{sentinel}.json"
            scenario_path = root / "scenario.json"
            projection_path = root / "projection.json"
            card_path.write_text(json.dumps(card), encoding="utf-8")
            scenario_path.write_bytes(facet.canonical_json(scenario))
            projection_path.write_bytes(facet.canonical_json(projection))
            result = self.run_cli("brief", str(card_path), str(scenario_path), str(projection_path))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("REJECTED", result.stderr)
        self.assertNotIn(sentinel, result.stdout + result.stderr)
        result = self.run_cli(sentinel, sentinel)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(sentinel, result.stdout + result.stderr)

    def test_engine_ast_denies_effectful_and_nondeterministic_capabilities(self) -> None:
        tree = ast.parse(ENGINE.read_text(encoding="utf-8"))
        imported: set[str] = set()
        dangerous: list[str] = []
        forbidden_modules = {
            "asyncio",
            "ctypes",
            "datetime",
            "ftplib",
            "http",
            "imaplib",
            "importlib",
            "random",
            "requests",
            "secrets",
            "shutil",
            "smtplib",
            "socket",
            "ssl",
            "subprocess",
            "tempfile",
            "time",
            "urllib",
            "uuid",
        }
        forbidden_names = {"eval", "exec", "compile", "__import__", "open"}
        forbidden_attributes = {
            "chmod",
            "chown",
            "connect",
            "import_module",
            "makedirs",
            "mkdir",
            "popen",
            "remove",
            "removedirs",
            "rename",
            "replace",
            "request",
            "rmdir",
            "send",
            "sendall",
            "sleep",
            "spawn",
            "system",
            "touch",
            "truncate",
            "unlink",
            "urlopen",
            "write_bytes",
            "write_text",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in forbidden_names:
                    dangerous.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    call_name = qualified_attribute(node.func)
                    if node.func.attr in forbidden_attributes:
                        dangerous.append(call_name)
                    elif node.func.attr == "open" and call_name != "os.open":
                        dangerous.append(call_name)
                    elif node.func.attr == "write" and call_name != "sys.stdout.buffer.write":
                        dangerous.append(call_name)
        self.assertTrue(imported.isdisjoint(forbidden_modules), imported & forbidden_modules)
        self.assertEqual(dangerous, [])

    def test_schema_objects_are_closed(self) -> None:
        for name in ("facet.schema.json", "brief.schema.json"):
            schema = load_json(HERE / name)
            for node in objects_with_properties(schema):
                self.assertIs(node.get("additionalProperties"), False, name)

    def test_public_artifacts_are_exact_local_copies(self) -> None:
        for relative in (
            "catalog.json",
            "playbook.json",
            "facet.schema.json",
            "brief.schema.json",
            "examples/synthetic-authority-boundary.json",
            "examples/authority-foresight-projection.json",
        ):
            with self.subTest(relative=relative):
                self.assertTrue((PUBLIC / relative).exists(), relative)
                self.assertEqual((HERE / relative).read_bytes(), (PUBLIC / relative).read_bytes())

    def test_public_door_is_scriptless_local_and_synthetic_only(self) -> None:
        page = PUBLIC / "index.html"

        class Audit(HTMLParser):
            def __init__(self) -> None:
                super().__init__()
                self.ids: list[str] = []
                self.hrefs: list[str] = []
                self.sources: list[str] = []
                self.active: list[str] = []
                self.label_refs: list[str] = []
                self.events: list[str] = []

            def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
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
        self.assertNotIn("http://", text.casefold())
        self.assertNotIn("https://", text.casefold())
        self.assertNotIn("url(", text.casefold())
        for reference in audit.label_refs:
            self.assertIn(reference, audit.ids)
        for href in audit.hrefs:
            parsed = urlsplit(href)
            self.assertFalse(parsed.scheme or parsed.netloc, href)
            if href.startswith("#"):
                self.assertIn(href[1:], audit.ids)
            else:
                self.assertTrue((page.parent / parsed.path).exists(), href)
        folded = text.casefold()
        for literal in (
            "karma facet",
            "稜面",
            "synthetic-only rehearsal",
            "zero effect",
            "four planes",
            "eight open angles",
            "g6b",
            "closure-still-requires-human-authority",
            "kingdom.karma-facet-catalog/v1",
            "kingdom.karma-facet-playbook/v1",
            "kingdom.karma-facet/v1",
            "kingdom.karma-facet-brief/v1",
        ):
            self.assertIn(literal.casefold(), folded)
        readme = (HERE / "README.md").read_text(encoding="utf-8").casefold()
        for row in playbook()["response_table"]:
            for key in (
                "order",
                "stimulus",
                "guard",
                "candidate",
                "verification_candidate",
                "halt_if",
            ):
                with self.subTest(surface="response-table", order=row["order"], key=key):
                    needle = str(row[key]).casefold()
                    self.assertIn(needle, folded)
                    self.assertIn(needle, readme)


def objects_with_properties(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if value.get("type") == "object" and "properties" in value:
            found.append(value)
        for child in value.values():
            found.extend(objects_with_properties(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(objects_with_properties(child))
    return found


def qualified_attribute(value: ast.Attribute) -> str:
    parts = [value.attr]
    current: ast.expr = value.value
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


if __name__ == "__main__":
    unittest.main()
