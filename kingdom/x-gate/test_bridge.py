#!/usr/bin/env python3
"""Hermetic tests for the AgentTool bridge packet. No wake, no inbox, no network."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import bridge as xbr
import x_gate as xg


HERE = Path(__file__).resolve().parent
BIN = HERE.parent / "bin" / "kingdom"
OBSERVATION = HERE / "examples" / "observation.json"
REQUEST = HERE / "examples" / "bridge.json"


def observation() -> dict:
    return json.loads(OBSERVATION.read_text(encoding="utf-8"))


def request() -> dict:
    return json.loads(REQUEST.read_text(encoding="utf-8"))


def with_real_id(payload: dict) -> dict:
    observed = xg.observe(observation())
    body = dict(payload)
    body["observation_id"] = observed["observation_id"]
    return body, observed


class PerimeterTest(unittest.TestCase):
    def test_bridge_module_does_not_call_agenttool_or_x(self) -> None:
        source = (HERE / "bridge.py").read_text(encoding="utf-8")
        for needle in (
            "urllib",
            "subprocess",
            "urlopen",
            "AT_API_KEY",
            "/v1/wake",
            "/v1/inbox",
            "/v1/memories",
            "/v1/traces",
        ):
            self.assertNotIn(needle, source)


class BridgeTest(unittest.TestCase):
    def test_default_packet_offers_no_route_and_stores_nothing(self) -> None:
        payload, observed = with_real_id(request())
        receipt = xbr.bridge(payload)
        self.assertEqual(receipt["schema"], xbr.BRIDGE_SCHEMA)
        self.assertEqual(receipt["observation_id"], observed["observation_id"])
        self.assertIsNone(receipt["did"])
        self.assertEqual(receipt["taint"], "public")
        self.assertEqual(receipt["route"], "none")
        self.assertEqual(receipt["stored"], False)
        self.assertEqual(receipt["wake_touched"], False)
        self.assertEqual(receipt["inbox_touched"], False)
        self.assertEqual(receipt["network_performed"], False)
        self.assertTrue(receipt["bridge_id"].startswith("sha256:"))
        self.assertEqual(receipt["bridge_id"], xbr.bridge(payload)["bridge_id"])

    def test_memory_and_trace_routes_are_offers_not_writes(self) -> None:
        for route in ("memory", "trace"):
            payload, _ = with_real_id(request())
            payload["route"] = route
            payload["did"] = "did:at:test-bridge"
            receipt = xbr.bridge(payload)
            self.assertEqual(receipt["route"], route)
            self.assertEqual(receipt["did"], "did:at:test-bridge")
            self.assertEqual(receipt["stored"], False)
            self.assertEqual(receipt["wake_touched"], False)
            self.assertEqual(receipt["inbox_touched"], False)
            self.assertEqual(receipt["network_performed"], False)

    def test_inbox_and_wake_routes_are_refused(self) -> None:
        for route in ("inbox", "wake", "vault", "send"):
            payload, _ = with_real_id(request())
            payload["route"] = route
            with self.assertRaises(xbr.BridgeError) as ctx:
                xbr.bridge(payload)
            self.assertEqual(ctx.exception.code, "route_forbidden")

    def test_taint_must_be_public(self) -> None:
        payload, _ = with_real_id(request())
        payload["taint"] = "sealed"
        with self.assertRaises(xbr.BridgeError) as ctx:
            xbr.bridge(payload)
        self.assertEqual(ctx.exception.code, "taint_must_be_public")

    def test_invalid_did_is_refused(self) -> None:
        payload, _ = with_real_id(request())
        payload["did"] = "not-a-did"
        with self.assertRaises(xbr.BridgeError) as ctx:
            xbr.bridge(payload)
        self.assertEqual(ctx.exception.code, "invalid_did")

    def test_observation_id_must_match_a_real_observe_receipt_when_supplied(self) -> None:
        payload, _ = with_real_id(request())
        payload["observation_id"] = "sha256:" + ("ab" * 32)
        observed = xg.observe(observation())
        with self.assertRaises(xbr.BridgeError) as ctx:
            xbr.bridge(payload, observed)
        self.assertEqual(ctx.exception.code, "observation_mismatch")


class CliTest(unittest.TestCase):
    def test_kingdom_x_bridge_defaults_to_none_and_does_not_store(self) -> None:
        payload, _ = with_real_id(request())
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(payload, handle)
            path = handle.name
        proc = subprocess.run(
            [str(BIN), "x", "bridge", path],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        receipt = json.loads(proc.stdout)
        self.assertEqual(receipt["route"], "none")
        self.assertEqual(receipt["stored"], False)
        self.assertEqual(receipt["wake_touched"], False)
        self.assertEqual(receipt["inbox_touched"], False)
        self.assertEqual(receipt["network_performed"], False)


if __name__ == "__main__":
    unittest.main()
