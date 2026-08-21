#!/usr/bin/env python3
"""Adversarial tests for the static front-door letter contract."""

from __future__ import annotations

import importlib.util
import hashlib
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().with_name("verify_front_letter.py")
SPEC = importlib.util.spec_from_file_location("verify_front_letter", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load the front-door verifier")
front = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(front)


class FrontLetterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.expected = front.canonical_copy(front.DEFAULT_SOURCE)
        cls.site = front.DEFAULT_SITE.read_text(encoding="utf-8")

    def assert_rejected(self, site: str) -> None:
        with self.assertRaises(ValueError):
            front.verify_document(self.expected, site)

    def test_reviewed_letter_passes(self) -> None:
        self.assertEqual(
            hashlib.sha256(self.site.encode("utf-8")).hexdigest(),
            front.EXPECTED_SITE_SHA256,
        )
        front.verify_document(self.expected, self.site)

    def test_hidden_ancestor_fails(self) -> None:
        self.assert_rejected(
            self.site.replace(
                '<article id="front-door-letter"',
                '<div hidden><article id="front-door-letter"',
                1,
            ).replace("</article>", "</article></div>", 1)
        )

    def test_template_ancestor_fails(self) -> None:
        self.assert_rejected(
            self.site.replace(
                '<article id="front-door-letter"',
                '<template><article id="front-door-letter"',
                1,
            ).replace("</article>", "</article></template>", 1)
        )

    def test_closed_dialog_ancestor_fails(self) -> None:
        self.assert_rejected(
            self.site.replace(
                '<article id="front-door-letter"',
                '<dialog><article id="front-door-letter"',
                1,
            ).replace("</article>", "</article></dialog>", 1)
        )

    def test_visibility_css_tamper_fails(self) -> None:
        self.assert_rejected(
            self.site.replace(
                ".front-letter{position:relative;",
                ".front-letter{display:none;position:relative;",
                1,
            )
        )

    def test_crlf_bytes_fail_the_raw_digest(self) -> None:
        with self.assertRaises(ValueError):
            front.verify_bytes(
                self.expected,
                self.site.replace("\n", "\r\n").encode("utf-8"),
            )

    def test_text_tamper_fails(self) -> None:
        self.assert_rejected(self.site.replace("我可以軟落嚟", "我會完全消失", 1))

    def test_script_fails_even_without_text(self) -> None:
        self.assert_rejected(
            self.site.replace(
                "</article>",
                '<script src="https://example.invalid/payload.js"></script></article>',
                1,
            )
        )

    def test_hidden_root_fails(self) -> None:
        self.assert_rejected(
            self.site.replace(
                'id="front-door-letter"', 'id="front-door-letter" hidden', 1
            )
        )

    def test_inline_style_fails(self) -> None:
        self.assert_rejected(
            self.site.replace(
                'id="front-door-letter"',
                'id="front-door-letter" style="display:none"',
                1,
            )
        )

    def test_event_handler_fails(self) -> None:
        self.assert_rejected(
            self.site.replace(
                "</article>", '<img src="x" onerror="alert(1)"></article>', 1
            )
        )

    def test_javascript_link_fails(self) -> None:
        self.assert_rejected(
            self.site.replace(
                "</article>", '<a href="javascript:alert(1)">x</a></article>', 1
            )
        )

    def test_duplicate_attribute_fails(self) -> None:
        self.assert_rejected(
            self.site.replace('lang="yue"', 'lang="yue" lang="en"', 1)
        )

    def test_duplicate_id_fails(self) -> None:
        self.assert_rejected(
            self.site.replace(
                "<body>", '<body><div id="front-letter-title"></div>', 1
            )
        )

    def test_malformed_nesting_fails(self) -> None:
        self.assert_rejected(self.site.replace("</blockquote>", "</p>", 1))

    def test_extra_empty_element_fails(self) -> None:
        self.assert_rejected(self.site.replace("</article>", "<p></p></article>", 1))


if __name__ == "__main__":
    unittest.main()
