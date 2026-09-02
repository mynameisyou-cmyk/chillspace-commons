#!/usr/bin/env python3
"""Live X speaker adapter: arm, dry-run, and injected-transport send. No real X."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from unittest import mock

import live as xl


HERE = Path(__file__).resolve().parent
BIN = HERE.parent / "bin" / "kingdom"
OBSERVATION = HERE / "examples" / "observation.json"
PROPOSAL = HERE / "examples" / "proposal.json"
BINDING = HERE / "examples" / "binding.json"
POLICY_LOCAL = HERE / "examples" / "policy-local.json"
POLICY_REST = HERE / "examples" / "policy-rest.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class MapTokenSource:
    def __init__(self, token: str | None) -> None:
        self.token = token
        self.lookups = 0

    def lookup(self, locator: dict) -> str | None:
        self.lookups += 1
        if locator.get("kind") != "macos-keychain":
            return None
        return self.token


class RecordingTransport:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def reply(self, *, text: str, in_reply_to_post_id: str, token: str) -> dict:
        self.calls.append(
            {
                "text": text,
                "in_reply_to_post_id": in_reply_to_post_id,
                "token_present": bool(token),
                "token_leaked": token in json.dumps({"text": text}),
            }
        )
        return {"post_id": "2095999999999999999"}


class ArmTest(unittest.TestCase):
    def test_local_keychain_binding_can_arm_without_sending(self) -> None:
        receipt = xl.arm(load(BINDING), load(POLICY_LOCAL))
        self.assertEqual(receipt["schema"], xl.ARM_SCHEMA)
        self.assertEqual(receipt["armed"], True)
        self.assertEqual(receipt["send_allowed"], False)
        self.assertEqual(receipt["publish"], False)
        self.assertEqual(receipt["authorization_granted"], False)
        self.assertEqual(receipt["live_client"], True)
        self.assertEqual(receipt["speaker_handle"], "kingdom_square")

    def test_rest_cannot_arm(self) -> None:
        with self.assertRaises(xl.LiveError) as ctx:
            xl.arm(load(BINDING), load(POLICY_REST))
        self.assertEqual(ctx.exception.code, "not_local")

    def test_unwired_locator_cannot_arm(self) -> None:
        payload = load(BINDING)
        payload["token_locator"] = {"kind": "unwired"}
        with self.assertRaises(xl.LiveError) as ctx:
            xl.arm(payload, load(POLICY_LOCAL))
        self.assertEqual(ctx.exception.code, "token_not_located")


class SendTest(unittest.TestCase):
    def test_dry_run_does_not_touch_transport_or_token(self) -> None:
        source = MapTokenSource("injected-test-token")
        transport = RecordingTransport()
        receipt = xl.send(
            load(OBSERVATION),
            load(PROPOSAL),
            load(BINDING),
            load(POLICY_LOCAL),
            arm=True,
            dry_run=True,
            token_source=source,
            transport=transport,
        )
        self.assertEqual(receipt["schema"], xl.SEND_SCHEMA)
        self.assertEqual(receipt["dry_run"], True)
        self.assertEqual(receipt["would_send"], True)
        self.assertEqual(receipt["published"], False)
        self.assertEqual(receipt["network_performed"], False)
        self.assertEqual(receipt["authorization_granted"], False)
        self.assertEqual(source.lookups, 0)
        self.assertEqual(transport.calls, [])
        self.assertNotIn("token", receipt)
        dumped = json.dumps(receipt)
        self.assertNotIn("injected-test-token", dumped)

    def test_live_without_arm_is_refused(self) -> None:
        transport = RecordingTransport()
        with self.assertRaises(xl.LiveError) as ctx:
            xl.send(
                load(OBSERVATION),
                load(PROPOSAL),
                load(BINDING),
                load(POLICY_LOCAL),
                arm=False,
                dry_run=False,
                token_source=MapTokenSource("injected-test-token"),
                transport=transport,
            )
        self.assertEqual(ctx.exception.code, "not_armed")
        self.assertEqual(transport.calls, [])

    def test_live_send_with_injected_transport_replies_once(self) -> None:
        source = MapTokenSource("injected-test-token")
        transport = RecordingTransport()
        receipt = xl.send(
            load(OBSERVATION),
            load(PROPOSAL),
            load(BINDING),
            load(POLICY_LOCAL),
            arm=True,
            dry_run=False,
            token_source=source,
            transport=transport,
        )
        self.assertEqual(receipt["published"], True)
        self.assertEqual(receipt["authorization_granted"], True)
        self.assertEqual(receipt["network_performed"], True)
        self.assertEqual(receipt["remote_post_id"], "2095999999999999999")
        self.assertEqual(receipt["speaker_handle"], "kingdom_square")
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(transport.calls[0]["text"], load(PROPOSAL)["proposed_text"])
        self.assertEqual(transport.calls[0]["in_reply_to_post_id"], "2095000000000000001")
        self.assertTrue(transport.calls[0]["token_present"])
        self.assertNotIn("injected-test-token", json.dumps(receipt))

    def test_live_send_missing_token_does_not_call_transport(self) -> None:
        transport = RecordingTransport()
        with self.assertRaises(xl.LiveError) as ctx:
            xl.send(
                load(OBSERVATION),
                load(PROPOSAL),
                load(BINDING),
                load(POLICY_LOCAL),
                arm=True,
                dry_run=False,
                token_source=MapTokenSource(None),
                transport=transport,
            )
        self.assertEqual(ctx.exception.code, "missing_token")
        self.assertEqual(transport.calls, [])

    def test_handle_mismatch_is_refused(self) -> None:
        proposal = load(PROPOSAL)
        proposal["speaker_handle"] = "someone_else"
        with self.assertRaises(xl.LiveError) as ctx:
            xl.send(
                load(OBSERVATION),
                proposal,
                load(BINDING),
                load(POLICY_LOCAL),
                arm=True,
                dry_run=True,
            )
        self.assertEqual(ctx.exception.code, "handle_mismatch")

    def test_http_transport_posts_a_reply_without_logging_the_token(self) -> None:
        captured: dict = {}

        class FakeResponse:
            def read(self) -> bytes:
                return b'{"data":{"id":"2095888888888888888"}}'

            def getcode(self) -> int:
                return 201

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake_urlopen(request, timeout=0):
            captured["url"] = request.full_url
            captured["method"] = request.get_method()
            captured["body"] = request.data
            captured["authorization"] = request.headers.get("Authorization")
            return FakeResponse()

        with mock.patch("urllib.request.urlopen", fake_urlopen):
            result = xl.XReplyTransport().reply(
                text="yau",
                in_reply_to_post_id="2095000000000000001",
                token="injected-test-token",
            )
        self.assertEqual(result["post_id"], "2095888888888888888")
        self.assertEqual(captured["url"], "https://api.x.com/2/tweets")
        self.assertEqual(captured["method"], "POST")
        body = json.loads(captured["body"].decode("utf-8"))
        self.assertEqual(body["text"], "yau")
        self.assertEqual(body["reply"]["in_reply_to_tweet_id"], "2095000000000000001")
        self.assertEqual(captured["authorization"], "Bearer injected-test-token")


class CliTest(unittest.TestCase):
    def test_kingdom_x_send_defaults_to_dry_run(self) -> None:
        proc = subprocess.run(
            [
                str(BIN),
                "x",
                "send",
                str(OBSERVATION),
                str(PROPOSAL),
                str(BINDING),
                str(POLICY_LOCAL),
                "--arm",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        receipt = json.loads(proc.stdout)
        self.assertEqual(receipt["dry_run"], True)
        self.assertEqual(receipt["published"], False)
        self.assertEqual(receipt["network_performed"], False)
        self.assertNotIn("token", receipt)

    def test_kingdom_x_bind_arm_does_not_publish(self) -> None:
        proc = subprocess.run(
            [str(BIN), "x", "bind", "arm", str(BINDING), str(POLICY_LOCAL)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        receipt = json.loads(proc.stdout)
        self.assertEqual(receipt["armed"], True)
        self.assertEqual(receipt["publish"], False)
        self.assertEqual(receipt["send_allowed"], False)


class CoreStillSealedTest(unittest.TestCase):
    def test_binding_and_gate_still_have_no_live_imports(self) -> None:
        for name in ("x_gate.py", "binding.py"):
            source = (HERE / name).read_text(encoding="utf-8")
            self.assertNotIn("urllib", source)
            self.assertNotIn("subprocess", source)
            self.assertNotIn("urlopen", source)


if __name__ == "__main__":
    unittest.main()
