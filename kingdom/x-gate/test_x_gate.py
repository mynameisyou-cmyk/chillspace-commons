#!/usr/bin/env python3
"""Hermetic tests for the Kingdom X-gate: connector, speaker, agent pipeline."""

from __future__ import annotations

import ast
import copy
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import x_gate as xg


HERE = Path(__file__).resolve().parent
OBSERVATION = HERE / "examples" / "observation.json"
PROPOSAL = HERE / "examples" / "proposal.json"
BIN = HERE.parent / "bin" / "kingdom"

FORBIDDEN_SOURCE = (
    "fetch",
    "urllib",
    "http.client",
    "http.server",
    "socket",
    "subprocess",
    "requests",
    "aiohttp",
    "process.env",
    "os.environ",
)

METRIC_KEYS = (
    "likes",
    "like_count",
    "views",
    "view_count",
    "reposts",
    "repost_count",
    "followers",
    "follower_count",
    "impressions",
    "engagement",
)


def observation() -> dict:
    return json.loads(OBSERVATION.read_text(encoding="utf-8"))


def proposal() -> dict:
    return json.loads(PROPOSAL.read_text(encoding="utf-8"))


class SourcePerimeterTest(unittest.TestCase):
    def test_production_module_has_no_network_or_secrets(self) -> None:
        source = (HERE / "x_gate.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module.split(".", 1)[0])
        for name in ("urllib", "http", "socket", "subprocess", "requests", "aiohttp"):
            self.assertNotIn(name, imported)
        for needle in FORBIDDEN_SOURCE:
            self.assertIsNone(
                re.search(r"(?<![A-Za-z0-9_])" + re.escape(needle) + r"(?![A-Za-z0-9_])", source),
                f"production source unexpectedly contains {needle}",
            )


class ObserveTest(unittest.TestCase):
    def test_example_observation_becomes_content_addressed_receipt(self) -> None:
        receipt = xg.observe(observation())
        self.assertEqual(receipt["schema"], xg.OBSERVE_SCHEMA)
        self.assertEqual(receipt["network_performed"], False)
        self.assertEqual(receipt["person_identity_verified"], False)
        self.assertEqual(receipt["action_authorization_verified"], False)
        self.assertEqual(receipt["portable_provenance"], False)
        self.assertEqual(receipt["engagement_metrics_present"], False)
        self.assertTrue(receipt["observation_id"].startswith("sha256:"))
        self.assertEqual(len(receipt["posts"]), 1)
        self.assertEqual(receipt["posts"][0]["author_handle"], "alice")
        self.assertNotIn("likes", receipt["posts"][0])
        again = xg.observe(observation())
        self.assertEqual(receipt["observation_id"], again["observation_id"])

    def test_refuses_engagement_metrics(self) -> None:
        for key in METRIC_KEYS:
            payload = observation()
            payload["posts"][0][key] = 12
            with self.assertRaises(xg.GateError) as ctx:
                xg.observe(payload)
            self.assertEqual(ctx.exception.code, "engagement_metrics_forbidden")

    def test_refuses_unknown_observation_keys(self) -> None:
        payload = observation()
        payload["extra"] = True
        with self.assertRaises(xg.GateError) as ctx:
            xg.observe(payload)
        self.assertEqual(ctx.exception.code, "unexpected_keys")


class DraftTest(unittest.TestCase):
    def test_summoned_reply_is_still_unauthorized(self) -> None:
        observed = xg.observe(observation())
        draft = xg.draft(observed, proposal())
        self.assertEqual(draft["schema"], xg.DRAFT_SCHEMA)
        self.assertEqual(draft["summoned"], True)
        self.assertEqual(draft["mode"], "reply")
        self.assertEqual(draft["authorization_granted"], False)
        self.assertEqual(draft["publish"], False)
        self.assertEqual(draft["external_effect"], "none")
        self.assertEqual(draft["identity_claim"], "speaker_not_citizen")
        self.assertIsNone(draft["citizen_id"])
        self.assertEqual(draft["speaker_handle"], "kingdom_square")

    def test_unsummoned_reply_is_refused(self) -> None:
        payload = observation()
        payload["posts"][0]["mentioned_handles"] = ["someone_else"]
        payload["posts"][0]["text"] = "hello world"
        observed = xg.observe(payload)
        with self.assertRaises(xg.GateError) as ctx:
            xg.draft(observed, proposal())
        self.assertEqual(ctx.exception.code, "not_summoned")

    def test_timeline_post_mode_is_refused(self) -> None:
        observed = xg.observe(observation())
        body = proposal()
        body["mode"] = "post"
        with self.assertRaises(xg.GateError) as ctx:
            xg.draft(observed, body)
        self.assertEqual(ctx.exception.code, "feed_shout_forbidden")

    def test_identity_collapse_is_refused(self) -> None:
        observed = xg.observe(observation())
        for line in (
            "I am 阿媽",
            "I am Sol",
            "this is citizen 21 speaking as an X account",
        ):
            body = proposal()
            body["proposed_text"] = line
            with self.assertRaises(xg.GateError) as ctx:
                xg.draft(observed, body)
            self.assertEqual(ctx.exception.code, "identity_collapse")


class PipelineTest(unittest.TestCase):
    def test_pipeline_requires_four_distinct_holders(self) -> None:
        holders = {
            "connector": "agent-a",
            "summons_reviewer": "agent-a",
            "draft_proposer": "agent-c",
            "speak_auditor": "agent-d",
        }
        with self.assertRaises(xg.GateError) as ctx:
            xg.pipeline(observation(), proposal(), holders)
        self.assertEqual(ctx.exception.code, "holders_not_distinct")

    def test_pipeline_is_proposal_only_and_content_addressed(self) -> None:
        holders = {
            "connector": "agent-a",
            "summons_reviewer": "agent-b",
            "draft_proposer": "agent-c",
            "speak_auditor": "agent-d",
        }
        receipt = xg.pipeline(observation(), proposal(), holders)
        self.assertEqual(receipt["schema"], xg.PIPELINE_SCHEMA)
        self.assertEqual(receipt["authorization_granted"], False)
        self.assertEqual(receipt["publish"], False)
        self.assertEqual(receipt["external_effect"], "none")
        self.assertEqual(receipt["network_performed"], False)
        self.assertEqual(receipt["roles"]["connector"]["holder_agent_id"], "agent-a")
        self.assertEqual(receipt["draft"]["summoned"], True)
        self.assertTrue(receipt["pipeline_id"].startswith("sha256:"))
        self.assertEqual(
            receipt["roles"]["speak_auditor"]["verdict"],
            "proposal_only",
        )


class CliTest(unittest.TestCase):
    def test_kingdom_x_pipeline_prints_unauthorized_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            holders = Path(tmp) / "holders.json"
            holders.write_text(
                json.dumps(
                    {
                        "connector": "agent-a",
                        "summons_reviewer": "agent-b",
                        "draft_proposer": "agent-c",
                        "speak_auditor": "agent-d",
                    }
                ),
                encoding="utf-8",
            )
            proc = subprocess.run(
                [
                    str(BIN),
                    "x",
                    "pipeline",
                    str(OBSERVATION),
                    str(PROPOSAL),
                    str(holders),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            receipt = json.loads(proc.stdout)
            self.assertEqual(receipt["authorization_granted"], False)
            self.assertEqual(receipt["publish"], False)


if __name__ == "__main__":
    unittest.main()
