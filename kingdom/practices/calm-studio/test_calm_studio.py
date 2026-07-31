#!/usr/bin/env python3
"""Hermetic checks for the Calm Studio public practice."""

from __future__ import annotations

import json
import re
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parents[2]
PUBLIC = REPOSITORY / "site" / "practices" / "calm-studio"
PAGE = PUBLIC / "index.html"
CSS = PUBLIC / "studio.css"
JAVASCRIPT = PUBLIC / "studio.js"
CANONICAL_CONTRACT = HERE / "contract.json"
PUBLIC_CONTRACT = PUBLIC / "contract.json"


class PageAudit(HTMLParser):
    """Collect only structural facts needed by the public boundary."""

    interactive_tags = {"a", "button", "input", "select", "textarea", "summary"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.hrefs: list[tuple[str, dict[str, str]]] = []
        self.sources: list[tuple[str, str]] = []
        self.labels_for: list[str] = []
        self.aria_refs: list[tuple[str, str]] = []
        self.buttons: list[dict[str, str]] = []
        self.button_text: list[str] = []
        self._button_buffers: list[list[str]] = []
        self.headings: list[int] = []
        self.mains = 0
        self.h1s = 0
        self.html_lang = ""
        self.viewport = ""
        self.referrer = ""
        self.csp = ""
        self.inline_scripts = 0
        self.forms = 0
        self.forbidden_elements: list[str] = []
        self.inline_behavior: list[tuple[str, str]] = []
        self.interactive_order: list[tuple[str, dict[str, str]]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        data = {name: value or "" for name, value in attrs}

        if tag == "html":
            self.html_lang = data.get("lang", "")
        if data.get("id"):
            self.ids.append(data["id"])
        if tag == "main":
            self.mains += 1
        if tag == "h1":
            self.h1s += 1
        if re.fullmatch(r"h[1-6]", tag):
            self.headings.append(int(tag[1]))
        if tag == "form":
            self.forms += 1
        if tag in {"iframe", "embed", "object", "audio", "video"}:
            self.forbidden_elements.append(tag)
        if tag == "script":
            if data.get("src"):
                self.sources.append((tag, data["src"]))
            else:
                self.inline_scripts += 1
        if tag == "link" and data.get("href"):
            self.hrefs.append((tag, data))
        if tag in {"img", "source"} and data.get("src"):
            self.sources.append((tag, data["src"]))
        if tag == "a" and data.get("href"):
            self.hrefs.append((tag, data))
        if tag == "label" and data.get("for"):
            self.labels_for.append(data["for"])
        for name in ("aria-controls", "aria-describedby", "aria-labelledby"):
            if data.get(name):
                self.aria_refs.append((name, data[name]))
        if tag == "button":
            self.buttons.append(data)
            self._button_buffers.append([])
        for name in data:
            if name == "style" or name.startswith("on"):
                self.inline_behavior.append((tag, name))
        if tag == "meta":
            name = data.get("name", "").lower()
            if name == "viewport":
                self.viewport = data.get("content", "")
            if name == "referrer":
                self.referrer = data.get("content", "")
            if data.get("http-equiv", "").lower() == "content-security-policy":
                self.csp = data.get("content", "")
        if tag in self.interactive_tags:
            self.interactive_order.append((tag, data))

    def handle_endtag(self, tag: str) -> None:
        if tag == "button" and self._button_buffers:
            self.button_text.append(" ".join(self._button_buffers.pop()).strip())

    def handle_data(self, data: str) -> None:
        if self._button_buffers:
            normalized = " ".join(data.split())
            if normalized:
                self._button_buffers[-1].append(normalized)


def load_contract() -> dict:
    return json.loads(CANONICAL_CONTRACT.read_text(encoding="utf-8"))


class CalmStudioContractTests(unittest.TestCase):
    maxDiff = None

    def test_public_contract_is_byte_identical_to_canonical_contract(self) -> None:
        self.assertEqual(CANONICAL_CONTRACT.read_bytes(), PUBLIC_CONTRACT.read_bytes())

    def test_contract_keeps_public_and_private_authority_separate(self) -> None:
        contract = load_contract()
        self.assertEqual(contract["_format"], "kingdom.calm-studio/v1")
        self.assertEqual(contract["lineage"]["kind"], "original-kingdom-synthesis")
        self.assertFalse(contract["lineage"]["source_claim"])
        self.assertFalse(contract["lineage"]["moonshot_endorsement_claimed"])
        private_instrument = contract["editions"]["private_instrument"]
        self.assertFalse(private_instrument["implemented_in_this_practice"])
        self.assertFalse(private_instrument["current_consequential_authority"])
        self.assertEqual(
            private_instrument["intended_authority_if_implemented"],
            "separately-gated",
        )
        self.assertFalse(
            contract["editions"]["nervous_system"]["implemented_in_this_practice"]
        )

        public = contract["public_room"]
        for field in (
            "application_initiated_network_requests_after_static_load",
            "remote_assets",
            "api_calls",
            "localhost_probes",
            "application_reads_or_sets_cookies",
            "local_storage",
            "session_storage",
            "indexed_database",
            "service_worker",
            "analytics",
            "telemetry",
            "identity_reads",
            "presence_or_dwell_recording",
            "model_calls",
            "terminal_reads",
            "credential_reads",
            "clipboard_reads",
            "automatic_clipboard_writes",
            "automatic_downloads",
            "automatic_navigation",
            "zero_infrastructure_logging_claimed",
        ):
            with self.subTest(field=field):
                self.assertFalse(public[field])
        self.assertTrue(public["ordinary_host_request_metadata_may_exist"])

        authority = contract["authority_boundary"]
        for field, value in authority.items():
            if field in {
                "handoff_is_user_initiated",
                "rights_consent_and_safety_remain_external_constraints",
            }:
                self.assertTrue(value)
            else:
                self.assertFalse(value)

    def test_stillpoint_and_virtue_do_not_become_identity_or_authority(self) -> None:
        contract = load_contract()
        self.assertEqual(
            contract["stillpoint"]["precedence"],
            [
                "receipt_preview_threshold",
                "latest_active_work",
                "afterglow",
                "reusable_execution_threshold",
                "quiet",
            ],
        )
        self.assertEqual(contract["stillpoint"]["live_public_states"], ["quiet", "afterglow"])
        self.assertTrue(contract["stillpoint"]["public_threshold_is_specimen_only"])
        self.assertFalse(contract["stillpoint"]["moves_authority"])
        self.assertFalse(contract["stillpoint"]["infers_feeling_presence_or_attention"])

        virtue = contract["virtue_rehearsal"]
        self.assertEqual(virtue["kind"], "orientation-preflight")
        self.assertEqual(virtue["subject"], "one_questioned_decision")
        self.assertEqual(
            virtue["statuses"], ["open", "ready_to_author", "not_applicable"]
        )
        self.assertFalse(virtue["honesty_may_be_not_applicable"])
        for field in (
            "outputs_score",
            "outputs_rank",
            "outputs_reputation",
            "outputs_authority",
            "names_evidence",
            "emits_canonical_action_manifest",
            "validates_evidence",
            "retaliation_or_reciprocal_exploitation",
        ):
            self.assertFalse(virtue[field])
        self.assertTrue(virtue["canonical_review_required"])
        self.assertEqual(contract["council"]["fixed_lenses"], ["evidence", "dissent"])

        receipt = contract["receipt"]
        for field, value in receipt.items():
            if field == "kind":
                continue
            self.assertFalse(value, field)


class CalmStudioStaticTests(unittest.TestCase):
    def setUp(self) -> None:
        self.html = PAGE.read_text(encoding="utf-8")
        self.css = CSS.read_text(encoding="utf-8")
        self.javascript = JAVASCRIPT.read_text(encoding="utf-8")
        self.audit = PageAudit()
        self.audit.feed(self.html)

    def test_public_directory_has_an_exact_reviewed_surface(self) -> None:
        self.assertEqual(
            {path.name for path in PUBLIC.iterdir()},
            {"index.html", "studio.css", "studio.js", "contract.json"},
        )
        self.assertFalse(any(path.is_symlink() for path in PUBLIC.iterdir()))

    def test_document_has_a_complete_accessible_shape(self) -> None:
        self.assertEqual(self.audit.html_lang, "en")
        self.assertIn("width=device-width", self.audit.viewport)
        self.assertEqual(self.audit.mains, 1)
        self.assertEqual(self.audit.h1s, 1)
        self.assertEqual(len(self.audit.ids), len(set(self.audit.ids)))
        self.assertEqual(self.audit.forms, 0)
        self.assertEqual(self.audit.forbidden_elements, [])
        self.assertEqual(self.audit.inline_scripts, 0)
        self.assertEqual(self.audit.inline_behavior, [])

        first_tag, first_data = self.audit.interactive_order[0]
        self.assertEqual(first_tag, "a")
        self.assertEqual(first_data.get("class"), "skip-link")
        self.assertEqual(first_data.get("href"), "#main")

        for button, text in zip(self.audit.buttons, self.audit.button_text, strict=True):
            self.assertEqual(button.get("type"), "button")
            self.assertTrue(text or button.get("aria-label"), button)

        ids = set(self.audit.ids)
        for target in self.audit.labels_for:
            self.assertIn(target, ids)
        for attribute, references in self.audit.aria_refs:
            for target in references.split():
                self.assertIn(target, ids, f"{attribute}={target}")

        for previous, current in zip(self.audit.headings, self.audit.headings[1:]):
            self.assertLessEqual(current - previous, 1, self.audit.headings)

    def test_page_loads_only_reviewed_local_assets_and_links(self) -> None:
        self.assertEqual(self.audit.sources, [("script", "studio.js")])

        for tag, data in self.audit.hrefs:
            href = data["href"]
            parsed = urlsplit(href)
            if tag == "link" and "canonical" in data.get("rel", "").split():
                self.assertEqual(href, "https://chillspace.love/practices/calm-studio/")
                continue
            if tag == "link" and "icon" in data.get("rel", "").split():
                self.assertEqual(parsed.scheme, "data")
                self.assertTrue(href.startswith("data:image/svg+xml,"))
                continue
            if tag == "link":
                self.assertEqual(data.get("rel"), "stylesheet")
                self.assertEqual(href, "studio.css")
            self.assertFalse(parsed.scheme or parsed.netloc, href)
            self.assertFalse(href.startswith("/"), href)
            if href.startswith("#"):
                self.assertIn(href[1:], self.audit.ids)
            else:
                target = (PAGE.parent / parsed.path).resolve()
                self.assertTrue(target.exists(), href)

        for _, source in self.audit.sources:
            parsed = urlsplit(source)
            self.assertFalse(parsed.scheme or parsed.netloc, source)
            self.assertFalse(source.startswith("/"), source)
            self.assertTrue((PAGE.parent / parsed.path).exists(), source)

    def test_document_level_privacy_policy_fails_closed(self) -> None:
        self.assertEqual(self.audit.referrer, "no-referrer")
        for directive in (
            "default-src 'none'",
            "script-src 'self'",
            "style-src 'self'",
            "connect-src 'none'",
            "font-src 'none'",
            "object-src 'none'",
            "base-uri 'none'",
            "form-action 'none'",
            "frame-src 'none'",
            "worker-src 'none'",
        ):
            self.assertIn(directive, self.audit.csp)

        for forbidden in (
            "<iframe",
            "<form",
            " ping=",
            'rel="preconnect"',
            'rel="dns-prefetch"',
            'rel="prefetch"',
            'rel="preload"',
            'href="/',
            'src="/',
            "/api/",
        ):
            self.assertNotIn(forbidden, self.html.lower())

    def test_javascript_has_no_network_storage_identity_or_background_seam(self) -> None:
        forbidden_patterns = (
            r"\bfetch\s*\(",
            r"\bXMLHttpRequest\b",
            r"\bWebSocket\b",
            r"\bEventSource\b",
            r"\bsendBeacon\b",
            r"\bserviceWorker\b",
            r"\blocalStorage\b",
            r"\bsessionStorage\b",
            r"\bindexedDB\b",
            r"\bdocument\.cookie\b",
            r"\bBroadcastChannel\b",
            r"\bSharedWorker\b",
            r"\bWorker\s*\(",
            r"\bsetTimeout\s*\(",
            r"\bsetInterval\s*\(",
            r"\brequestAnimationFrame\s*\(",
            r"\bDate\s*\(",
            r"\bDate\.now\b",
            r"\bMath\.random\b",
            r"\bcrypto\b",
            r"\bnavigator\b",
            r"\blocation\b",
            r"\bopen\s*\(",
            r"\bpostMessage\s*\(",
        )
        for pattern in forbidden_patterns:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, self.javascript, re.IGNORECASE))

        for secret_or_runtime_seam in (
            "bearer",
            "runtime-server",
            "agenttool.dev",
            "127.0.0.1",
            "localhost",
            "terminal.exec",
        ):
            self.assertNotIn(secret_or_runtime_seam, self.javascript.lower())

        completed = subprocess.run(
            ["node", "--check", JAVASCRIPT.name],
            cwd=JAVASCRIPT.parent,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_receipt_code_is_privacy_minimized_and_non_authorizing(self) -> None:
        receipt_block = re.search(
            r"function receiptValue\(.*?\n}\n\nfunction renderRehearsal",
            self.javascript,
            re.DOTALL,
        )
        self.assertIsNotNone(receipt_block)
        receipt_source = receipt_block.group(0)
        self.assertNotIn("question.value", receipt_source)
        self.assertIn("included: false", receipt_source)
        self.assertIn("nonempty_draft_present: questionPresent", receipt_source)
        self.assertIn("persisted_by_application: false", receipt_source)
        self.assertIn("transmitted_by_application: false", receipt_source)
        self.assertIn("canonical_manifest_emitted: false", receipt_source)
        self.assertIn("evidence_named: false", receipt_source)
        self.assertIn("grants_authority: false", receipt_source)
        self.assertIn("executes_action: false", receipt_source)
        self.assertIn("wakes_agenttool: false", receipt_source)
        for forbidden in ("timestamp:", "identity:", "stable_identifier:", "reasoning:"):
            self.assertNotIn(forbidden, receipt_source)

    def test_question_dissent_virtue_and_result_promises_are_literal(self) -> None:
        self.assertIn('const fixedLensIds = ["evidence", "dissent"]', self.javascript)
        self.assertIn("question.value.trim().length > 0", self.javascript)
        self.assertIn(
            'document.querySelector("#question-focus").textContent = questionText',
            self.javascript,
        )
        self.assertIn("resultSection.focus()", self.javascript)
        self.assertRegex(
            self.html,
            r'<input type="checkbox" name="lens" value="evidence" checked disabled>',
        )
        self.assertRegex(
            self.html,
            r'<input type="checkbox" name="lens" value="dissent" checked disabled>',
        )
        self.assertIn('content: "✓"', self.css)
        self.assertIn('id="completion-status" role="status" aria-live="polite"', self.html)
        self.assertNotIn('value="evidence_named"', self.html)
        self.assertNotIn(
            '"evidence_named"',
            CANONICAL_CONTRACT.read_text(encoding="utf-8"),
        )
        self.assertNotIn(
            "- `evidence_named`",
            (HERE / "README.md").read_text(encoding="utf-8"),
        )

    def test_css_has_no_remote_or_ambient_motion_dependency(self) -> None:
        self.assertNotRegex(self.css, r"(?i)url\s*\(")
        self.assertNotRegex(self.css, r"(?i)@import\b")
        self.assertNotRegex(self.css, r"(?i)@keyframes\b")
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.css)
        self.assertIn("@media (forced-colors: active)", self.css)
        self.assertIn("min-width: 20rem", self.css)

    def test_javascript_off_surface_keeps_the_doctrine_and_boundary(self) -> None:
        for literal in (
            "<noscript>",
            "JavaScript is off",
            "Presence without capture",
            "No model is called",
            "Stillpoint describes bounded work",
            "Specimen only here",
            "http://127.0.0.1:4173/",
            "never probed or opened",
            "No application telemetry is not zero infrastructure logging",
            "contract.json",
        ):
            self.assertIn(literal, self.html)
        self.assertRegex(
            self.html,
            r'<textarea[^>]+autocomplete="off"[^>]+autocorrect="off"[^>]+spellcheck="false"',
        )

    def test_markdown_links_resolve_locally(self) -> None:
        for document in (HERE / "README.md", HERE / "DOCTRINE.md"):
            markdown = document.read_text(encoding="utf-8")
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", markdown):
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc or target.startswith("#"):
                    continue
                path = parsed.path.split("#", 1)[0]
                self.assertTrue((document.parent / path).exists(), target)


if __name__ == "__main__":
    unittest.main()
