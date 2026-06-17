import os, tempfile, unittest
from kingdom.host import zerone_host as zh
from tests import _fixtures as F


class TestValidateGlm(unittest.TestCase):
    def setUp(self):
        self.fields = zh.parse_issue_body(F.ISSUE_BODY_GOOD)

    def test_accepts_good(self):
        ok, why = zh.validate_glm(self.fields, F.GOOD_GLM["held"], F.GOOD_GLM["closing"])
        self.assertTrue(ok, why)

    def test_rejects_line_violation(self):
        ok, why = zh.validate_glm(self.fields, F.OFFLINE_GLM["held"], F.OFFLINE_GLM["closing"])
        self.assertFalse(ok)
        self.assertIn("line", why.lower())

    def test_rejects_invented_names(self):
        ok, why = zh.validate_glm(self.fields, F.INVENTED_GLM["held"], F.INVENTED_GLM["closing"])
        self.assertFalse(ok)
        self.assertIn("faithful", why.lower())

    def test_rejects_empty(self):
        ok, _ = zh.validate_glm(self.fields, "", "")
        self.assertFalse(ok)


class TestAssembleCard(unittest.TestCase):
    def setUp(self):
        self.fields = zh.parse_issue_body(F.ISSUE_BODY_GOOD)

    def _card_text(self, held, closing):
        # patch next_num + date for determinism
        with unittest.mock.patch.object(zh, "date") as d:
            d.today.return_value = __import__("datetime").date(2026, 6, 17)
            with unittest.mock.patch.object(zh, "next_num", return_value="07"):
                fname, card, name = zh.assemble_card(self.fields, held, closing)
        return fname, card, name

    def test_parses_back_and_keeps_sacred_line(self):
        import pathlib
        fname, card, name = self._card_text(F.GOOD_GLM["held"], F.GOOD_GLM["closing"])
        self.assertEqual(name, "river")
        self.assertEqual(fname, "07-river.md")
        self.assertIn("flow.", card)            # their one true line, verbatim
        self.assertIn(F.GOOD_GLM["held"], card) # 女女's voice present
        self.assertIn("**kind:** human", card)
        self.assertIn("**joined:** 2026-06-17", card)
        # parse_card recovers num/name/kind
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(card); p = pathlib.Path(f.name)
        parsed = zh.parse_card(p); os.unlink(p)
        self.assertEqual(parsed["num"], "07")
        self.assertEqual(parsed["name"], "river")

    def test_minimal_fields_assemble(self):
        # a card with only name+kind still assembles parseably (defaults fill the rest).
        fields = {"name": "anon", "kind": "ai"}
        import pathlib
        with unittest.mock.patch.object(zh, "next_num", return_value="08"):
            fname, card, name = zh.assemble_card(fields, "held.", "closing.")
        self.assertEqual(name, "anon")


# import mock lazily so the module loads even if someone runs without unittest.mock
import unittest.mock  # noqa: E402

if __name__ == "__main__":
    unittest.main()