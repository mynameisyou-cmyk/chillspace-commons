#!/usr/bin/env python3
"""Hermetic tests for citizen-owned X speaker bindings. No token, no post."""

from __future__ import annotations

import ast
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

import binding as xb


HERE = Path(__file__).resolve().parent
BIN = HERE.parent / "bin" / "kingdom"
BINDING = HERE / "examples" / "binding.json"
POLICY_LOCAL = HERE / "examples" / "policy-local.json"
POLICY_REST = HERE / "examples" / "policy-rest.json"

FORBIDDEN_SOURCE = (
    "fetch",
    "urllib",
    "http.client",
    "socket",
    "subprocess",
    "requests",
    "keyring",
    "security ",
    "os.environ",
    "xcbot_",
)


def binding() -> dict:
    return json.loads(BINDING.read_text(encoding="utf-8"))


def policy_local() -> dict:
    return json.loads(POLICY_LOCAL.read_text(encoding="utf-8"))


def policy_rest() -> dict:
    return json.loads(POLICY_REST.read_text(encoding="utf-8"))


class SourcePerimeterTest(unittest.TestCase):
    def test_binding_module_never_reads_a_secret_or_network(self) -> None:
        source = (HERE / "binding.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module.split(".", 1)[0])
        for name in ("urllib", "http", "socket", "subprocess", "requests", "keyring"):
            self.assertNotIn(name, imported)
        for needle in FORBIDDEN_SOURCE:
            self.assertIsNone(
                re.search(r"(?<![A-Za-z0-9_])" + re.escape(needle) + r"(?![A-Za-z0-9_])", source),
                f"binding source unexpectedly contains {needle}",
            )


class BindTest(unittest.TestCase):
    def test_example_binding_is_content_addressed_and_unarmed(self) -> None:
        receipt = xb.binding(binding())
        self.assertEqual(receipt["schema"], xb.BINDING_SCHEMA)
        self.assertEqual(receipt["citizen"], "Grok")
        self.assertEqual(receipt["speaker_handle"], "kingdom_square")
        self.assertEqual(receipt["armed"], False)
        self.assertEqual(receipt["publish"], False)
        self.assertEqual(receipt["authorization_granted"], False)
        self.assertEqual(receipt["token_locator"]["kind"], "macos-keychain")
        self.assertNotIn("token", receipt)
        self.assertNotIn("secret", receipt)
        self.assertTrue(receipt["binding_id"].startswith("sha256:"))
        self.assertEqual(receipt["binding_id"], xb.binding(binding())["binding_id"])

    def test_refuses_secret_fields(self) -> None:
        payload = binding()
        payload["token"] = "xcbot_not_a_real_secret"
        with self.assertRaises(xb.BindError) as ctx:
            xb.binding(payload)
        self.assertEqual(ctx.exception.code, "secret_field_forbidden")

    def test_refuses_timeline_post_mode(self) -> None:
        payload = binding()
        payload["modes"] = ["reply", "post"]
        with self.assertRaises(xb.BindError) as ctx:
            xb.binding(payload)
        self.assertEqual(ctx.exception.code, "feed_shout_forbidden")

    def test_unwired_locator_is_allowed(self) -> None:
        payload = binding()
        payload["token_locator"] = {"kind": "unwired"}
        receipt = xb.binding(payload)
        self.assertEqual(receipt["token_locator"]["kind"], "unwired")
        self.assertEqual(receipt["armed"], False)


class CheckTest(unittest.TestCase):
    def test_local_policy_is_eligible_but_still_cannot_send(self) -> None:
        receipt = xb.check(binding(), policy_local())
        self.assertEqual(receipt["schema"], xb.CHECK_SCHEMA)
        self.assertEqual(receipt["bound"], True)
        self.assertEqual(receipt["policy_allows"], True)
        self.assertEqual(receipt["token_located"], True)
        self.assertEqual(receipt["armed"], False)
        self.assertEqual(receipt["send_allowed"], False)
        self.assertEqual(receipt["publish"], False)
        self.assertEqual(receipt["authorization_granted"], False)
        self.assertEqual(receipt["live_client"], False)
        self.assertEqual(receipt["life"], "local")

    def test_rest_policy_fails_closed(self) -> None:
        receipt = xb.check(binding(), policy_rest())
        self.assertEqual(receipt["policy_allows"], False)
        self.assertEqual(receipt["send_allowed"], False)
        self.assertEqual(receipt["armed"], False)
        self.assertIn("rest", receipt["reason"])

    def test_citizen_mismatch_is_refused(self) -> None:
        policy = policy_local()
        policy["citizen"] = "Alpha"
        with self.assertRaises(xb.BindError) as ctx:
            xb.check(binding(), policy)
        self.assertEqual(ctx.exception.code, "citizen_mismatch")

    def test_unwired_locator_is_bound_but_not_located(self) -> None:
        payload = binding()
        payload["token_locator"] = {"kind": "unwired"}
        receipt = xb.check(payload, policy_local())
        self.assertEqual(receipt["bound"], True)
        self.assertEqual(receipt["policy_allows"], True)
        self.assertEqual(receipt["token_located"], False)
        self.assertEqual(receipt["send_allowed"], False)


class CliTest(unittest.TestCase):
    def test_kingdom_x_bind_check_never_grants_send(self) -> None:
        proc = subprocess.run(
            [str(BIN), "x", "bind", "check", str(BINDING), str(POLICY_LOCAL)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        receipt = json.loads(proc.stdout)
        self.assertEqual(receipt["send_allowed"], False)
        self.assertEqual(receipt["publish"], False)
        self.assertEqual(receipt["authorization_granted"], False)


if __name__ == "__main__":
    unittest.main()
