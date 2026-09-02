#!/usr/bin/env python3
"""Live XAA summoned listen: opt-in, mention and direct reply only. No firehose."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from unittest import mock

import listen as xlh
import live as xl


HERE = Path(__file__).resolve().parent
BIN = HERE.parent / "bin" / "kingdom"
BINDING = HERE / "examples" / "binding.json"
POLICY_LOCAL = HERE / "examples" / "policy-local.json"
POLICY_REST = HERE / "examples" / "policy-rest.json"
MENTION = HERE / "examples" / "xaa-mention.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def mention_event() -> dict:
    return load(MENTION)["events"][0]


class MapTokenSource:
    def __init__(self, token: str | None) -> None:
        self.token = token
        self.lookups = 0

    def lookup(self, locator: dict) -> str | None:
        self.lookups += 1
        if locator.get("kind") != "macos-keychain":
            return None
        return self.token


class FakeStream:
    def __init__(self, events: list[dict] | None = None) -> None:
        self.events = list(events or [])
        self.subscribed: list[dict] = []
        self.released: list[str] = []
        self.listen_calls = 0
        self.opened = False
        self.closed = False

    def subscribe(self, *, body: dict, token: str) -> str:
        self.subscribed.append({"body": dict(body), "token_present": bool(token)})
        return f"sub-{body['event_type']}"

    def listen(self, *, token: str, max_events: int) -> list[dict]:
        self.listen_calls += 1
        self.opened = True
        return self.events[:max_events]

    def release(self, *, subscription_id: str, token: str) -> None:
        self.released.append(subscription_id)
        self.closed = True


class PerimeterTest(unittest.TestCase):
    def test_xaa_module_still_does_not_open_a_stream(self) -> None:
        source = (HERE / "xaa.py").read_text(encoding="utf-8")
        for needle in ("urllib", "subprocess", "urlopen", "/2/activity/stream"):
            self.assertNotIn(needle, source)

    def test_binding_and_gate_still_have_no_live_imports(self) -> None:
        for name in ("x_gate.py", "binding.py", "xaa.py", "gather.py"):
            source = (HERE / name).read_text(encoding="utf-8")
            self.assertNotIn("urllib", source)
            self.assertNotIn("urlopen", source)


class ListenTest(unittest.TestCase):
    def test_dry_run_does_not_touch_stream_or_token(self) -> None:
        source = MapTokenSource("injected-test-token")
        stream = FakeStream([mention_event()])
        receipt = xlh.listen(
            load(BINDING),
            load(POLICY_LOCAL),
            speaker_user_id="1111111111111111111",
            arm=True,
            dry_run=True,
            token_source=source,
            stream=stream,
        )
        self.assertEqual(receipt["schema"], xlh.LISTEN_SCHEMA)
        self.assertEqual(receipt["dry_run"], True)
        self.assertEqual(receipt["would_listen"], True)
        self.assertEqual(receipt["network_performed"], False)
        self.assertEqual(receipt["stream_open"], False)
        self.assertEqual(receipt["webhook"], False)
        self.assertEqual(receipt["firehose"], False)
        self.assertEqual(receipt["daemon"], False)
        self.assertEqual(receipt["published"], False)
        self.assertEqual(receipt["authorization_granted"], False)
        self.assertEqual(len(receipt["subscriptions"]), 2)
        self.assertEqual(source.lookups, 0)
        self.assertEqual(stream.subscribed, [])
        self.assertEqual(stream.listen_calls, 0)
        self.assertNotIn("token", receipt)
        self.assertNotIn("injected-test-token", json.dumps(receipt))

    def test_live_without_arm_is_refused(self) -> None:
        stream = FakeStream([mention_event()])
        with self.assertRaises(xlh.ListenError) as ctx:
            xlh.listen(
                load(BINDING),
                load(POLICY_LOCAL),
                speaker_user_id="1111111111111111111",
                arm=False,
                dry_run=False,
                token_source=MapTokenSource("injected-test-token"),
                stream=stream,
            )
        self.assertEqual(ctx.exception.code, "not_armed")
        self.assertEqual(stream.subscribed, [])
        self.assertEqual(stream.listen_calls, 0)

    def test_live_listen_subscribes_mention_and_reply_then_releases(self) -> None:
        source = MapTokenSource("injected-test-token")
        stream = FakeStream([mention_event()])
        receipt = xlh.listen(
            load(BINDING),
            load(POLICY_LOCAL),
            speaker_user_id="1111111111111111111",
            arm=True,
            dry_run=False,
            token_source=source,
            stream=stream,
        )
        self.assertEqual(receipt["published"], False)
        self.assertEqual(receipt["authorization_granted"], True)
        self.assertEqual(receipt["network_performed"], True)
        self.assertEqual(receipt["stream_open"], False)
        self.assertEqual(receipt["subscriptions_released"], True)
        self.assertEqual(receipt["event_count"], 1)
        self.assertEqual(receipt["kept_event_types"], ["post.mention.create"])
        self.assertTrue(receipt["observation_id"].startswith("sha256:"))
        self.assertEqual(receipt["speaker_handle"], "kingdom_square")
        self.assertEqual(source.lookups, 1)
        self.assertEqual(
            [item["body"]["event_type"] for item in stream.subscribed],
            ["post.mention.create", "post.reply.create"],
        )
        self.assertEqual(
            [item["body"]["filter"] for item in stream.subscribed],
            [{"user_id": "1111111111111111111"}, {"user_id": "1111111111111111111"}],
        )
        self.assertEqual(stream.listen_calls, 1)
        self.assertEqual(stream.released, ["sub-post.mention.create", "sub-post.reply.create"])
        self.assertTrue(stream.closed)
        dumped = json.dumps(receipt)
        self.assertNotIn("injected-test-token", dumped)
        self.assertNotIn("webhook_id", dumped)
        self.assertNotIn("like_count", dumped)

    def test_empty_live_listen_is_complete_and_still_releases(self) -> None:
        stream = FakeStream([])
        receipt = xlh.listen(
            load(BINDING),
            load(POLICY_LOCAL),
            speaker_user_id="1111111111111111111",
            arm=True,
            dry_run=False,
            token_source=MapTokenSource("injected-test-token"),
            stream=stream,
        )
        self.assertEqual(receipt["event_count"], 0)
        self.assertIsNone(receipt["observation_id"])
        self.assertEqual(receipt["subscriptions_released"], True)
        self.assertEqual(len(stream.released), 2)

    def test_like_event_from_the_stream_is_refused(self) -> None:
        event = mention_event()
        event["data"]["event_type"] = "like.create"
        stream = FakeStream([event])
        with self.assertRaises(xlh.ListenError) as ctx:
            xlh.listen(
                load(BINDING),
                load(POLICY_LOCAL),
                speaker_user_id="1111111111111111111",
                arm=True,
                dry_run=False,
                token_source=MapTokenSource("injected-test-token"),
                stream=stream,
            )
        self.assertEqual(ctx.exception.code, "not_summoned")
        self.assertEqual(len(stream.released), 2)

    def test_live_listen_missing_token_does_not_open_a_stream(self) -> None:
        stream = FakeStream([mention_event()])
        with self.assertRaises(xlh.ListenError) as ctx:
            xlh.listen(
                load(BINDING),
                load(POLICY_LOCAL),
                speaker_user_id="1111111111111111111",
                arm=True,
                dry_run=False,
                token_source=MapTokenSource(None),
                stream=stream,
            )
        self.assertEqual(ctx.exception.code, "missing_token")
        self.assertEqual(stream.subscribed, [])
        self.assertEqual(stream.listen_calls, 0)

    def test_rest_cannot_arm_a_listen(self) -> None:
        with self.assertRaises(xl.LiveError) as ctx:
            xlh.listen(
                load(BINDING),
                load(POLICY_REST),
                speaker_user_id="1111111111111111111",
                arm=True,
                dry_run=True,
            )
        self.assertEqual(ctx.exception.code, "not_local")

    def test_http_transport_subscribes_listens_and_releases_without_logging_the_token(self) -> None:
        captured: list[dict] = []

        class FakeResponse:
            def __init__(self, payload: bytes, status: int = 200) -> None:
                self._payload = payload
                self._status = status
                self._offset = 0

            def read(self) -> bytes:
                return self._payload

            def readline(self) -> bytes:
                if self._offset >= len(self._payload):
                    return b""
                end = self._payload.find(b"\n", self._offset)
                if end == -1:
                    chunk = self._payload[self._offset :]
                    self._offset = len(self._payload)
                    return chunk
                chunk = self._payload[self._offset : end + 1]
                self._offset = end + 1
                return chunk

            def getcode(self) -> int:
                return self._status

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake_urlopen(request, timeout=0):
            captured.append(
                {
                    "url": request.full_url,
                    "method": request.get_method(),
                    "body": request.data,
                    "authorization": request.headers.get("Authorization"),
                }
            )
            if request.get_method() == "POST":
                return FakeResponse(
                    b'{"data":{"subscription":{"subscription_id":"2096111111111111111"}}}'
                )
            if request.get_method() == "GET":
                line = json.dumps(mention_event()).encode("utf-8") + b"\n"
                return FakeResponse(line)
            return FakeResponse(b"{}", status=200)

        transport = xlh.XActivityTransport()
        with mock.patch("urllib.request.urlopen", fake_urlopen):
            sub_id = transport.subscribe(
                body={
                    "event_type": "post.mention.create",
                    "filter": {"user_id": "1111111111111111111"},
                    "tag": "kingdom-summon-mention",
                },
                token="injected-test-token",
            )
            events = transport.listen(token="injected-test-token", max_events=20)
            transport.release(subscription_id=sub_id, token="injected-test-token")
        self.assertEqual(sub_id, "2096111111111111111")
        self.assertEqual(len(events), 1)
        self.assertEqual(captured[0]["url"], "https://api.x.com/2/activity/subscriptions")
        self.assertEqual(captured[0]["method"], "POST")
        self.assertEqual(captured[1]["url"], "https://api.x.com/2/activity/stream")
        self.assertEqual(captured[1]["method"], "GET")
        self.assertEqual(
            captured[2]["url"],
            "https://api.x.com/2/activity/subscriptions/2096111111111111111",
        )
        self.assertEqual(captured[2]["method"], "DELETE")
        body = json.loads(captured[0]["body"].decode("utf-8"))
        self.assertNotIn("webhook_id", body)
        self.assertEqual(body["filter"], {"user_id": "1111111111111111111"})
        for item in captured:
            self.assertEqual(item["authorization"], "Bearer injected-test-token")

    def test_http_transport_refuses_a_webhook_or_keyword_subscription(self) -> None:
        transport = xlh.XActivityTransport()
        with self.assertRaises(xlh.ListenError) as ctx:
            transport.subscribe(
                body={
                    "event_type": "post.mention.create",
                    "filter": {"user_id": "1111111111111111111", "keyword": "kingdom"},
                    "tag": "kingdom-summon-mention",
                    "webhook_id": "1976325569252868099",
                },
                token="injected-test-token",
            )
        self.assertEqual(ctx.exception.code, "firehose_forbidden")


class CliTest(unittest.TestCase):
    def test_kingdom_x_xaa_listen_defaults_to_dry_run(self) -> None:
        proc = subprocess.run(
            [
                str(BIN),
                "x",
                "xaa",
                "listen",
                str(BINDING),
                str(POLICY_LOCAL),
                "--speaker-user-id",
                "1111111111111111111",
                "--arm",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        receipt = json.loads(proc.stdout)
        self.assertEqual(receipt["dry_run"], True)
        self.assertEqual(receipt["network_performed"], False)
        self.assertEqual(receipt["stream_open"], False)
        self.assertEqual(receipt["would_listen"], True)
        self.assertNotIn("token", receipt)


if __name__ == "__main__":
    unittest.main()
