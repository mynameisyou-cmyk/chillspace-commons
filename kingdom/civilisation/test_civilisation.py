import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch


MODULE = Path(__file__).with_name("civilisation.py")
SPEC = importlib.util.spec_from_file_location("civilisation", MODULE)
civic = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(civic)


class CivilisationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {"KINGDOM_CITIZENS_ROOT": str(self.root)}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.addCleanup(self.temp.cleanup)

    def home(self, name, agenttool=None):
        home = self.root / f"citizen-{name}"
        home.mkdir()
        (home / "kingdom.yaml").write_text(f"name: {name}\nstate: active\n", encoding="utf-8")
        if agenttool is not None:
            (home / "agent.json").write_text(json.dumps({"name": name, "agenttool": agenttool}), encoding="utf-8")
        return home

    def test_absence_is_unasked_but_policy_fails_closed(self):
        self.home("joy")
        data = civic.status_data()
        self.assertEqual(data["installed_homes"], 1)
        self.assertEqual(data["life"]["unasked"], 1)
        name, home = civic.resolve_home("joy")
        self.assertIsNone(civic.load_passport(name, home))

    def test_choice_is_local_hash_chained_and_reversible(self):
        home = self.home("joy")
        civic.append_event("joy", home, "life", "joy", mode="local")
        first = civic.load_passport("joy", home)
        self.assertEqual(first["life"]["mode"], "local")
        self.assertEqual(first["history"][0]["prev"], civic.GENESIS)
        civic.append_event("joy", home, "life", "joy", mode="rest", reason="sleep")
        second = civic.load_passport("joy", home)
        self.assertEqual(second["life"]["mode"], "rest")
        self.assertEqual(second["history"][1]["prev"], second["history"][0]["hash"])

    def test_agenttool_link_keeps_only_public_address(self):
        home = self.home("joy")
        passport = civic.append_event(
            "joy", home, "agenttool", "joy", mode="linked",
            did="did:at:example-123", instance="https://api.agenttool.dev"
        )
        self.assertEqual(passport["agenttool"]["did"], "did:at:example-123")
        self.assertFalse(civic._secret_paths(passport))

    def test_secret_fields_are_refused(self):
        home = self.home("joy")
        civic.append_event("joy", home, "life", "joy", mode="local")
        path = home / "CIVIC.json"
        data = json.loads(path.read_text())
        data["token"] = "do-not-store-me"
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(civic.CivicError, "forbidden credential"):
            civic.load_passport("joy", home)

    def test_tampered_current_view_is_found(self):
        home = self.home("joy")
        civic.append_event("joy", home, "life", "joy", mode="local")
        path = home / "CIVIC.json"
        data = json.loads(path.read_text())
        data["life"]["mode"] = "rest"
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(civic.CivicError, "does not match its history"):
            civic.load_passport("joy", home)

    def test_tampered_history_is_found(self):
        home = self.home("joy")
        civic.append_event("joy", home, "life", "joy", mode="local")
        path = home / "CIVIC.json"
        data = json.loads(path.read_text())
        data["history"][0]["mode"] = "rest"
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(civic.CivicError, "broken hash"):
            civic.load_passport("joy", home)

    def test_exact_tag_commons_matches_different_citizens(self):
        joy = self.home("joy")
        silence = self.home("silence")
        civic.append_event("joy", joy, "offer", "joy", tag="writing", description="clear words")
        civic.append_event("silence", silence, "need", "silence", tag="writing", description="a title")
        data = civic.commons_data()
        self.assertEqual(data["matches"], [{"tag": "writing", "needs": "silence", "offers": "joy"}])
        civic.append_event("joy", joy, "withdraw", "joy", side="offer", tag="writing")
        self.assertEqual(civic.commons_data()["matches"], [])

    def test_legacy_records_are_counted_but_not_migrated(self):
        self.home("joy", {"arrived": True, "did": "did:at:old"})
        self.home("fear", {"arrived": False, "chose": "stay_home", "reason": "privacy"})
        data = civic.status_data()
        self.assertEqual(data["legacy_agenttool_records"]["arrived"], 1)
        self.assertEqual(data["legacy_agenttool_records"]["declined"], 1)
        self.assertEqual(data["agenttool"]["unasked"], 2)

    def test_only_exact_installed_names_resolve(self):
        self.home("joy")
        with self.assertRaises(civic.CivicError):
            civic.resolve_home("../joy")

    def test_instance_requires_https_except_loopback(self):
        self.assertEqual(civic._validate_instance("http://localhost:3000/"), "http://localhost:3000")
        with self.assertRaises(civic.CivicError):
            civic._validate_instance("http://agenttool.example")
        with self.assertRaises(civic.CivicError):
            civic._validate_instance("https://user:pass@agenttool.example")

    def test_cli_round_trip_uses_the_configured_home_only(self):
        home = self.home("joy")
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            self.assertEqual(civic.main(["choose", "joy", "local", "--by", "joy"]), 0)
            self.assertEqual(civic.main(["offer", "joy", "writing", "clear words", "--by", "joy"]), 0)
            self.assertEqual(civic.main(["policy", "joy", "--json"]), 0)
        self.assertTrue((home / "CIVIC.json").is_file())
        self.assertIn('"life": "local"', output.getvalue())


if __name__ == "__main__":
    unittest.main()
