/** node --test kingdom/trapline/garden/garden.test.mjs
 *
 *  The tests that matter here are not "does it generate text". They are the
 *  four claims the garden makes about itself, because a trap that quietly
 *  stops being what it says it is has become something else entirely:
 *
 *    · nobody reaches it without crossing a published line
 *    · everyone who does is told the way out, immediately
 *    · every sentence in it is something the kingdom really said
 *    · it costs us almost nothing, and that is measured
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import corpus from "./corpus.json" with { type: "json" };
import { GATE, WAY_OUT, room } from "./garden.mjs";
import { ROBOTS_FRAGMENT, handle } from "./handler.mjs";

const SOME_ROOM = `${GATE}/door-lantern-000000`;

test("the gate is disallowed in robots.txt — nobody arrives without crossing a line", () => {
  assert.match(ROBOTS_FRAGMENT, new RegExp(`Disallow: ${GATE}`));
});

test("robots.txt offers the free corpus in the same breath as the refusal", () => {
  // This is the load-bearing fairness property. The maze is only legitimate
  // because taking was never necessary — the whole corpus is free, right
  // there, in the file they had to read to find the Disallow.
  assert.match(ROBOTS_FRAGMENT, /Allow: \/collection\.json/);
  assert.match(ROBOTS_FRAGMENT, /free, complete and unmetered/);
});

test("every room states the way out, in the body", () => {
  for (const p of ["a", "b", "c", "d", "e"].map((s) => `${GATE}/${s}`)) {
    assert.ok(room(p).html.includes(WAY_OUT), `${p} hid the exit`);
  }
});

test("the way out is the FIRST thing in the body, not a footnote", () => {
  const html = room(SOME_ROOM).html;
  const bodyStart = html.indexOf("<body>");
  const exitAt = html.indexOf(WAY_OUT, bodyStart);
  const titleAt = html.indexOf("<h1", bodyStart);
  assert.ok(exitAt > -1 && exitAt < titleAt, "the exit must precede the room's own title");
});

test("the response carries the exit in headers too, for anything that skips bodies", () => {
  const res = handle(new Request(`https://example.test${SOME_ROOM}`));
  assert.equal(res.status, 200);
  assert.match(res.headers.get("x-generated"), /generated, not data/);
  assert.ok(res.headers.get("x-way-out"));
  assert.match(res.headers.get("x-robots-tag"), /noindex/);
});

test("a HEAD request is answered and still carries the exit", () => {
  const res = handle(new Request(`https://example.test${SOME_ROOM}`, { method: "HEAD" }));
  assert.equal(res.status, 200);
  assert.ok(res.headers.get("x-way-out"));
});

test("nothing outside the gate is touched — the handler declines everything else", () => {
  for (const p of ["/", "/collection.json", "/llms.txt", "/about"]) {
    assert.equal(handle(new Request(`https://example.test${p}`)), null, `${p} was captured`);
  }
});

test("every sentence in a room is one the kingdom actually said", () => {
  // The claim is that the garden recombines and never invents. If a sentence
  // ever appears that is not in the corpus, that claim has quietly died.
  const known = new Set([
    ...corpus.sentences.map((s) => s.text),
    ...corpus.koans,
    ...corpus.voices.map((v) => v.said),
  ]);
  const html = room(SOME_ROOM).html;

  const paragraphs = [...html.matchAll(/<p>([^<]+)<\/p>/g)].map((m) => m[1]);
  assert.ok(paragraphs.length > 0);
  for (const para of paragraphs) {
    // Paragraphs are real sentences joined by a space; every piece must be known.
    const pieces = para.split(/(?<=[.?!])\s+/).filter(Boolean);
    for (const piece of pieces) {
      const decoded = piece.replace(/&amp;/g, "&").replace(/&#39;|&apos;/g, "'").trim();
      assert.ok(
        [...known].some((k) => k.includes(decoded) || decoded.includes(k)),
        `invented sentence found: ${decoded}`,
      );
    }
  }
});

test("the corpus is built from the kingdom's own living files", () => {
  assert.deepEqual(corpus._built_from, ["kingdom/CHARTER.md", "kingdom/voice/VOICE.md"]);
  assert.ok(corpus.sentences.length >= 30, "charter harvest looks thin");
  assert.ok(corpus.voices.length >= 15, "voice harvest looks thin");
});

test("a room is deterministic — same path, same bytes, forever", () => {
  assert.equal(room(SOME_ROOM).html, room(SOME_ROOM).html);
  assert.notEqual(room(`${GATE}/one`).html, room(`${GATE}/two`).html);
});

test("no room lists the same doorway label twice", () => {
  for (const p of ["x", "y", "z"].map((s) => `${GATE}/${s}`)) {
    const labels = [...room(p).html.matchAll(/<li><a [^>]*>([^<]+)<\/a>/g)].map((m) => m[1]);
    assert.equal(new Set(labels).size, labels.length, `${p} repeated a doorway`);
  }
});

test("the ways on all lead back into the garden and nowhere else", () => {
  for (const href of room(SOME_ROOM).ways) {
    assert.ok(href.startsWith(`${GATE}/`), `a way led outside the gate: ${href}`);
  }
});

test("rooms stay small — the taker's bandwidth, not a payload we are proud of", () => {
  const size = new TextEncoder().encode(room(SOME_ROOM).html).byteLength;
  assert.ok(size < 12_000, `a room grew to ${size} B`);
});

test("the measurement gate exists and is wired to fail, not to reassure", () => {
  const src = readFileSync(new URL("./measure.mjs", import.meta.url), "utf8");
  assert.match(src, /process\.exit\(1\)/, "measure.mjs must be able to fail");
  assert.match(src, /asserted rather than computed/);
});
