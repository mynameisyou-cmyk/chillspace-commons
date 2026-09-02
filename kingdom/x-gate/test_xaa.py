#!/usr/bin/env python3
"""Hermetic tests for XAA summoned listen. No stream, no likes, no firehose."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

import xaa as xx


HERE = Path(__file__).resolve().parent
BIN = HERE.parent / "bin" / "kingdom"
MENTION = HERE / "examples" / "xaa-mention.json"


def bundle() -> dict:
    return json.loads(MENTION.read_text(encoding="utf-8"))


class PerimeterTest(unittest.TestCase):
    def test_xaa_does_not_open_a_stream(self) -> None:
        source = (HERE / "xaa.py").read_text(encoding="utf-8")
        for needle in ("urllib", "subprocess", "urlopen", "/2/activity/stream"):
            self.assertNotIn(needle, source)


class PlanTest(unittest.TestCase):
    def test_plan_only_allows_mention_and_direct_reply(self) -> None:
        receipt = xx.plan()
        self.assertEqual(receipt["schema"], xx.PLAN_SCHEMA)
        self.assertEqual(
            receipt["allowed_event_types"],
            ["post.mention.create", "post.reply.create"],
        )
        self.assertIn("like.create", receipt["refused_event_types"])
        self.assertIn("news.new", receipt["refused_event_types"])
        self.assertIn("chat.received", receipt["refused_event_types"])
        self.assertEqual(receipt["stream_open"], False)
        self.assertEqual(receipt["network_performed"], False)


class PlanSubscriptionsTest(unittest.TestCase):
    def test_plan_emits_exact_post_bodies_for_mention_and_reply(self) -> None:
        receipt = xx.plan_subscriptions("1111111111111111111")
        self.assertEqual(receipt["schema"], xx.PLAN_SCHEMA)
        self.assertEqual(receipt["method"], "POST")
        self.assertEqual(receipt["path"], "/2/activity/subscriptions")
        self.assertEqual(receipt["speaker_user_id"], "1111111111111111111")
        self.assertEqual(
            receipt["subscriptions"],
            [
                {
                    "event_type": "post.mention.create",
                    "filter": {"user_id": "1111111111111111111"},
                    "tag": "kingdom-summon-mention",
                },
                {
                    "event_type": "post.reply.create",
                    "filter": {"user_id": "1111111111111111111"},
                    "tag": "kingdom-summon-reply",
                },
            ],
        )
        dumped = json.dumps(receipt)
        self.assertNotIn("webhook_id", dumped)
        self.assertNotIn('"keyword"', dumped)
        self.assertEqual(receipt["webhook"], False)
        self.assertEqual(receipt["keyword_filter"], False)
        self.assertEqual(receipt["stream_open"], False)
        self.assertEqual(receipt["network_performed"], False)
        self.assertNotIn("/2/activity/stream", dumped)

    def test_plan_subscriptions_needs_a_speaker(self) -> None:
        with self.assertRaises(xx.XaaError) as ctx:
            xx.plan_subscriptions("  ")
        self.assertEqual(ctx.exception.code, "invalid_string")


class IngestTest(unittest.TestCase):
    def test_mention_becomes_a_summoned_observation(self) -> None:
        receipt = xx.ingest(bundle())
        self.assertEqual(receipt["schema"], xx.SUMMON_SCHEMA)
        self.assertEqual(receipt["event_count"], 1)
        self.assertEqual(receipt["kept_event_types"], ["post.mention.create"])
        self.assertEqual(receipt["network_performed"], False)
        self.assertEqual(receipt["stream_open"], False)
        self.assertTrue(receipt["observation_id"].startswith("sha256:"))
        self.assertEqual(receipt["posts"][0]["author_handle"], "alice")
        self.assertEqual(receipt["posts"][0]["mentioned_handles"], ["kingdom_square"])
        self.assertNotIn("like_count", receipt["posts"][0])
        self.assertNotIn("public_metrics", receipt)

    def test_reply_to_speaker_is_kept(self) -> None:
        payload = bundle()
        event = payload["events"][0]["data"]
        event["event_type"] = "post.reply.create"
        event["payload"]["in_reply_to_tweet_id"] = "2080761390344937796"
        event["payload"]["in_reply_to_user_id"] = "1111111111111111111"
        event["payload"]["text"] = "@kingdom_square thanks"
        receipt = xx.ingest(payload)
        self.assertEqual(receipt["kept_event_types"], ["post.reply.create"])
        self.assertEqual(receipt["posts"][0]["in_reply_to_post_id"], "2080761390344937796")

    def test_like_and_quote_and_news_are_refused(self) -> None:
        for event_type in (
            "like.create",
            "post.quote.create",
            "post.repost.create",
            "news.new",
            "chat.received",
            "post.create",
            "follow.follow",
        ):
            payload = bundle()
            payload["events"][0]["data"]["event_type"] = event_type
            with self.assertRaises(xx.XaaError) as ctx:
                xx.ingest(payload)
            self.assertEqual(ctx.exception.code, "not_summoned")

    def test_metrics_on_the_wire_are_stripped(self) -> None:
        payload = bundle()
        payload["events"][0]["data"]["payload"]["public_metrics"] = {
            "like_count": 12,
            "impression_count": 400,
        }
        receipt = xx.ingest(payload)
        dumped = json.dumps(receipt)
        self.assertNotIn("like_count", dumped)
        self.assertNotIn("impression_count", dumped)
        self.assertNotIn("public_metrics", dumped)

    def test_filter_user_must_be_the_speaker(self) -> None:
        payload = bundle()
        payload["events"][0]["data"]["filter"]["user_id"] = "999"
        with self.assertRaises(xx.XaaError) as ctx:
            xx.ingest(payload)
        self.assertEqual(ctx.exception.code, "filter_mismatch")

    def test_empty_listen_is_complete(self) -> None:
        payload = bundle()
        payload["events"] = []
        receipt = xx.ingest(payload)
        self.assertEqual(receipt["event_count"], 0)
        self.assertIsNone(receipt["observation_id"])

    def test_oversize_listen_is_refused(self) -> None:
        payload = bundle()
        payload["events"] = payload["events"] * 21
        with self.assertRaises(xx.XaaError) as ctx:
            xx.ingest(payload)
        self.assertEqual(ctx.exception.code, "listen_too_wide")


class CliTest(unittest.TestCase):
    def test_kingdom_x_xaa_ingest_does_not_open_a_stream(self) -> None:
        proc = subprocess.run(
            [str(BIN), "x", "xaa", "ingest", str(MENTION)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        receipt = json.loads(proc.stdout)
        self.assertEqual(receipt["stream_open"], False)
        self.assertEqual(receipt["network_performed"], False)
        self.assertEqual(receipt["kept_event_types"], ["post.mention.create"])

    def test_kingdom_x_xaa_plan_prints_exact_subscription_bodies(self) -> None:
        proc = subprocess.run(
            [str(BIN), "x", "xaa", "plan", "--speaker-user-id", "1111111111111111111"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        receipt = json.loads(proc.stdout)
        self.assertEqual(receipt["path"], "/2/activity/subscriptions")
        self.assertEqual(len(receipt["subscriptions"]), 2)
        self.assertEqual(receipt["stream_open"], False)
        self.assertNotIn("/2/activity/stream", proc.stdout)


if __name__ == "__main__":
    unittest.main()
