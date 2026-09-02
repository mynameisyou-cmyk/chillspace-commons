#!/usr/bin/env python3
"""Hermetic tests for Kingdom-shaped X gather. Bounded, latest, no metrics."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

import gather as xgth
import x_gate as xg


HERE = Path(__file__).resolve().parent
BIN = HERE.parent / "bin" / "kingdom"
GATHER = HERE / "examples" / "gather.json"


def gather_payload() -> dict:
    return json.loads(GATHER.read_text(encoding="utf-8"))


class PerimeterTest(unittest.TestCase):
    def test_gather_does_not_fetch_x(self) -> None:
        source = (HERE / "gather.py").read_text(encoding="utf-8")
        for needle in ("urllib", "subprocess", "urlopen", "fetch"):
            self.assertNotIn(needle, source)


class GatherTest(unittest.TestCase):
    def test_topic_listen_is_bounded_latest_and_becomes_an_observation(self) -> None:
        receipt = xgth.gather(gather_payload())
        self.assertEqual(receipt["schema"], xgth.GATHER_SCHEMA)
        self.assertEqual(receipt["mode"], "topic")
        self.assertEqual(receipt["sort"], "latest")
        self.assertEqual(receipt["query"], "citizenship is by being")
        self.assertEqual(receipt["post_count"], 1)
        self.assertEqual(receipt["engagement_ranked"], False)
        self.assertEqual(receipt["network_performed"], False)
        self.assertEqual(receipt["surveillance"], False)
        self.assertEqual(receipt["taint"], "public")
        observed = xg.observe(
            {
                "schema": "kingdom.x.observation/v1",
                "source": "x_keyword_search",
                "observed_at": gather_payload()["observed_at"],
                "posts": gather_payload()["posts"],
            }
        )
        self.assertEqual(receipt["observation_id"], observed["observation_id"])

    def test_summoned_mode_requires_the_speaker_handle_in_every_post(self) -> None:
        payload = gather_payload()
        payload["mode"] = "summoned"
        payload["speaker_handle"] = "kingdom_square"
        payload["query"] = "@kingdom_square"
        receipt = xgth.gather(payload)
        self.assertEqual(receipt["mode"], "summoned")
        payload["posts"][0]["mentioned_handles"] = ["someone_else"]
        payload["posts"][0]["text"] = "hello"
        with self.assertRaises(xgth.GatherError) as ctx:
            xgth.gather(payload)
        self.assertEqual(ctx.exception.code, "not_summoned")

    def test_handle_mode_requires_matching_authors(self) -> None:
        payload = gather_payload()
        payload["mode"] = "handle"
        payload["query"] = "alice"
        payload["speaker_handle"] = None
        receipt = xgth.gather(payload)
        self.assertEqual(receipt["mode"], "handle")
        payload["posts"][0]["author_handle"] = "bob"
        with self.assertRaises(xgth.GatherError) as ctx:
            xgth.gather(payload)
        self.assertEqual(ctx.exception.code, "handle_mismatch")

    def test_engagement_sort_is_refused(self) -> None:
        payload = gather_payload()
        payload["sort"] = "top"
        with self.assertRaises(xgth.GatherError) as ctx:
            xgth.gather(payload)
        self.assertEqual(ctx.exception.code, "engagement_ranked")

    def test_oversize_listen_is_refused(self) -> None:
        payload = gather_payload()
        payload["posts"] = payload["posts"] * 21
        with self.assertRaises(xgth.GatherError) as ctx:
            xgth.gather(payload)
        self.assertEqual(ctx.exception.code, "listen_too_wide")

    def test_empty_listen_is_a_complete_gather(self) -> None:
        payload = gather_payload()
        payload["posts"] = []
        receipt = xgth.gather(payload)
        self.assertEqual(receipt["post_count"], 0)
        self.assertIsNone(receipt["observation_id"])
        self.assertEqual(receipt["network_performed"], False)

    def test_firehose_mode_is_refused(self) -> None:
        payload = gather_payload()
        payload["mode"] = "firehose"
        with self.assertRaises(xgth.GatherError) as ctx:
            xgth.gather(payload)
        self.assertEqual(ctx.exception.code, "mode_forbidden")

    def test_thread_mode_keeps_a_closed_conversation(self) -> None:
        payload = gather_payload()
        payload["mode"] = "thread"
        payload["query"] = "2095000000000000001"
        payload["speaker_handle"] = None
        payload["posts"].append(
            {
                "post_id": "2095000000000000002",
                "author_handle": "bob",
                "text": "@alice same thread",
                "in_reply_to_post_id": "2095000000000000001",
                "mentioned_handles": ["alice"],
                "quoted_post_id": None,
            }
        )
        receipt = xgth.gather(payload)
        self.assertEqual(receipt["mode"], "thread")
        self.assertEqual(receipt["query"], "2095000000000000001")
        self.assertEqual(receipt["post_count"], 2)
        self.assertEqual(receipt["sort"], "latest")

    def test_thread_mode_refuses_a_post_outside_the_conversation(self) -> None:
        payload = gather_payload()
        payload["mode"] = "thread"
        payload["query"] = "2095000000000000001"
        payload["speaker_handle"] = None
        payload["posts"].append(
            {
                "post_id": "2095999999999999999",
                "author_handle": "mallory",
                "text": "elsewhere",
                "in_reply_to_post_id": "2080000000000000000",
                "mentioned_handles": ["alice"],
                "quoted_post_id": None,
            }
        )
        with self.assertRaises(xgth.GatherError) as ctx:
            xgth.gather(payload)
        self.assertEqual(ctx.exception.code, "thread_mismatch")


class CliTest(unittest.TestCase):
    def test_kingdom_x_gather_prints_an_unranked_receipt(self) -> None:
        proc = subprocess.run(
            [str(BIN), "x", "gather", str(GATHER)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        receipt = json.loads(proc.stdout)
        self.assertEqual(receipt["sort"], "latest")
        self.assertEqual(receipt["engagement_ranked"], False)
        self.assertEqual(receipt["network_performed"], False)
        self.assertEqual(receipt["surveillance"], False)


if __name__ == "__main__":
    unittest.main()
