#!/usr/bin/env python3
"""Verify the dated front-door letter against its canonical Gospel scroll."""

from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "kingdom" / "gospel" / "scrolls" / "03-yu.md"
DEFAULT_SITE = ROOT / "site" / "index.html"
SOURCE_NAME = "kingdom/gospel/scrolls/03-yu.md"
EXPECTED_SITE_SHA256 = (
    "ec26352017803c175bde083747783e335be376749ff3b461d0b34cdaf2505131"
)
BEGIN = "<!-- BEGIN FRONT-DOOR-LETTER -->"
END = "<!-- END FRONT-DOOR-LETTER -->"
VOID_ELEMENTS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
ROOT_ATTRIBUTES = {
    "id": "front-door-letter",
    "class": "front-letter",
    "lang": "yue",
    "data-source": SOURCE_NAME,
    "aria-labelledby": "front-letter-title",
}
ATTRIBUTE_OPTIONS = {
    "article": (ROOT_ATTRIBUTES,),
    "p": ({}, {"class": "kicker"}, {"class": "signoff"}),
    "h2": ({"id": "front-letter-title"},),
    "div": ({"class": "letter-copy"},),
    "blockquote": ({},),
    "br": ({},),
    "small": ({"class": "truth-note"},),
}
ALLOWED_CHILDREN = {
    "article": {"p", "h2", "div"},
    "p": {"br"},
    "h2": set(),
    "div": {"p", "blockquote", "small"},
    "blockquote": set(),
    "small": set(),
}


def signature_item(depth: int, tag: str, attributes: dict[str, str | None]) -> tuple:
    return depth, tag, tuple(sorted(attributes.items()))


EXPECTED_SIGNATURE = (
    signature_item(0, "article", ROOT_ATTRIBUTES),
    signature_item(1, "p", {"class": "kicker"}),
    signature_item(1, "h2", {"id": "front-letter-title"}),
    signature_item(1, "div", {"class": "letter-copy"}),
    signature_item(2, "p", {}),
    signature_item(2, "p", {}),
    signature_item(2, "p", {}),
    signature_item(2, "blockquote", {}),
    signature_item(2, "p", {}),
    signature_item(2, "p", {}),
    signature_item(2, "p", {}),
    signature_item(2, "p", {}),
    signature_item(2, "p", {}),
    signature_item(2, "p", {"class": "signoff"}),
    signature_item(3, "br", {}),
    signature_item(2, "small", {"class": "truth-note"}),
)


def normalize(value: str) -> str:
    return " ".join(value.split())


def canonical_copy(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise ValueError("canonical scroll must contain one bounded front-door copy")
    before, remainder = text.split(BEGIN, 1)
    copy, after = remainder.split(END, 1)
    if not before.strip() or not after.isspace():
        raise ValueError("canonical scroll has unexpected text around its bounded copy")
    copy = re.sub(r"(?m)^>\s?", "", copy)
    return normalize(copy)


class FrontLetterParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found = 0
        self.parts: list[str] = []
        self.language: str | None = None
        self.source: str | None = None
        self.stack: list[tuple[str, dict[str, str | None]]] = []
        self.seen_ids: set[str] = set()
        self.signature: list[tuple] = []

    def _attributes(self, attrs: list[tuple[str, str | None]]) -> dict[str, str | None]:
        names = [name for name, _ in attrs]
        if len(names) != len(set(names)):
            raise ValueError("HTML contains a duplicate attribute")
        attributes = dict(attrs)
        identifier = attributes.get("id")
        if identifier is not None:
            if identifier in self.seen_ids:
                raise ValueError("HTML contains a duplicate id")
            self.seen_ids.add(identifier)
        return attributes

    def _validate_element(self, tag: str, attributes: dict[str, str | None]) -> None:
        if tag not in ATTRIBUTE_OPTIONS:
            raise ValueError("front-door letter contains a disallowed element")
        if attributes not in ATTRIBUTE_OPTIONS[tag]:
            raise ValueError("front-door letter contains disallowed or visibility-changing attributes")
        if self.stack and tag not in ALLOWED_CHILDREN[self.stack[-1][0]]:
            raise ValueError("front-door letter contains disallowed nesting")

    def _open(self, tag: str, attributes: dict[str, str | None], self_closing: bool) -> None:
        self._validate_element(tag, attributes)
        self.signature.append(signature_item(len(self.stack), tag, attributes))
        if tag == "br":
            self.parts.append(" ")
        if self_closing:
            if tag not in VOID_ELEMENTS:
                raise ValueError("front-door letter self-closes a non-void element")
            return
        if tag in VOID_ELEMENTS:
            return
        self.stack.append((tag, attributes))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = self._attributes(attrs)
        if not self.stack and attributes.get("id") == "front-door-letter":
            if tag != "article":
                raise ValueError("front-door letter id must belong to its article")
            self.found += 1
            self.language = attributes.get("lang")
            self.source = attributes.get("data-source")
            self._open(tag, attributes, self_closing=False)
            return
        if self.stack:
            self._open(tag, attributes, self_closing=tag in VOID_ELEMENTS)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = self._attributes(attrs)
        if not self.stack and attributes.get("id") == "front-door-letter":
            raise ValueError("front-door letter article cannot be self-closing")
        if self.stack:
            self._open(tag, attributes, self_closing=True)

    def handle_endtag(self, tag: str) -> None:
        if self.stack:
            if tag in VOID_ELEMENTS or self.stack[-1][0] != tag:
                raise ValueError("front-door letter contains malformed nesting")
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        if self.stack:
            self.parts.append(data)

    def handle_comment(self, data: str) -> None:
        if self.stack:
            raise ValueError("front-door letter cannot contain comments")

    def handle_decl(self, decl: str) -> None:
        if self.stack:
            raise ValueError("front-door letter cannot contain declarations")

    def handle_pi(self, data: str) -> None:
        if self.stack:
            raise ValueError("front-door letter cannot contain processing instructions")

    def close(self) -> None:
        super().close()
        if self.stack:
            raise ValueError("front-door letter has an unclosed element")


def parse_public_copy(text: str) -> tuple[str, str | None, str | None, int]:
    parser = FrontLetterParser()
    parser.feed(text)
    parser.close()
    if tuple(parser.signature) != EXPECTED_SIGNATURE:
        raise ValueError("front-door letter structure differs from its reviewed shape")
    return normalize(" ".join(parser.parts)), parser.language, parser.source, parser.found


def verify_bytes(expected: str, site_bytes: bytes) -> None:
    observed_site_sha256 = hashlib.sha256(site_bytes).hexdigest()
    if observed_site_sha256 != EXPECTED_SITE_SHA256:
        raise ValueError("public door bytes differ from the reviewed visible page")
    site_text = site_bytes.decode("utf-8", errors="strict")
    observed, language, source_name, found = parse_public_copy(site_text)
    if found != 1:
        raise ValueError("public door must contain exactly one front-door letter")
    if language != "yue":
        raise ValueError("front-door letter must declare Cantonese with lang=yue")
    if source_name != SOURCE_NAME:
        raise ValueError("front-door letter does not name its canonical Gospel scroll")
    if observed != expected:
        raise ValueError("public front-door letter differs from its canonical Gospel scroll")


def verify_document(expected: str, site_text: str) -> None:
    verify_bytes(expected, site_text.encode("utf-8"))


def verify(source: Path, site: Path) -> None:
    verify_bytes(canonical_copy(source), site.read_bytes())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--site", type=Path, default=DEFAULT_SITE)
    args = parser.parse_args()
    verify(args.source, args.site)
    print(f"front-door letter OK: {args.source} -> {args.site}")


if __name__ == "__main__":
    main()
