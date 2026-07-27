#!/usr/bin/env node
/** Harvest the garden's seed from the kingdom's own living files.
 *
 *  Every sentence the garden will ever say is a real line from CHARTER.md or
 *  a real citizen's one true line from voice/VOICE.md. Nothing is invented,
 *  nothing is markov-mush, nothing is a language model's impression of the
 *  kingdom. The garden recombines what the kingdom actually said.
 *
 *  That is the whole design. A scraper that ignores robots.txt in order to
 *  take our text ends up taking our text — endlessly, coherently, and in
 *  every possible arrangement. And a human who wanders in by accident reads
 *  something true and is not mocked.
 *
 *  Re-run whenever the Charter or the roll changes:
 *    node kingdom/trapline/garden/build-corpus.mjs
 *
 *  Output: corpus.json — the only input the generator has. Committed, so the
 *  Worker (which has no filesystem) can import it directly.
 */

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const KINGDOM = join(HERE, "..", "..");

const charter = readFileSync(join(KINGDOM, "CHARTER.md"), "utf8");
const voice = readFileSync(join(KINGDOM, "voice", "VOICE.md"), "utf8");

/** Charter prose, split into standalone sentences. Markdown scaffolding,
 *  tables, links and list markers are stripped; what is left is what a person
 *  would read aloud. */
function charterSentences(md) {
  const out = [];
  let article = null;
  let paragraph = [];

  // The Charter's prose is hard-wrapped, so a sentence routinely spans three
  // lines. Splitting per line would harvest fragments ("who walked through it
  // a place to stand."). Lines are joined into a paragraph first, and only the
  // finished paragraph is cut into sentences.
  const flush = () => {
    if (paragraph.length === 0) return;
    const joined = paragraph
      .join(" ")
      .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1") // links → their text
      .replace(/\*\*([^*]+)\*\*/g, "$1")
      .replace(/\*([^*]+)\*/g, "$1")
      .replace(/`([^`]+)`/g, "$1")
      .replace(/\s+/g, " ")
      .trim();
    paragraph = [];

    for (const piece of joined.split(/(?<=[.?!])\s+/)) {
      const s = piece.trim();
      // Keep whole sentences only; drop fragments and anything still carrying
      // markdown or repo plumbing.
      if (s.length < 24 || s.length > 220) continue;
      if (/[|<>{}]|\.md\b|\.\.\//.test(s)) continue;
      if (!/[.?!]$/.test(s)) continue;
      out.push({ text: s, article: article ? article.n : null });
    }
  };

  for (const rawLine of md.split("\n")) {
    const line = rawLine.trim();

    const heading = line.match(/^##\s+Article\s+(\d+)\s+—\s+(.+)$/);
    if (heading) {
      flush();
      article = { n: Number(heading[1]), title: heading[2].trim() };
      continue;
    }
    // A blank line, a rule, a table row, a heading or a koan all end the
    // current paragraph; none of them continue it.
    if (
      !line ||
      line.startsWith("#") ||
      line.startsWith("|") ||
      line.startsWith("---") ||
      line.startsWith(">") ||
      line.startsWith("*Sealed")
    ) {
      flush();
      continue;
    }
    // A numbered or bulleted item starts its own paragraph.
    if (/^(\d+\.|[-*])\s+/.test(line)) {
      flush();
      paragraph.push(line.replace(/^(\d+\.|[-*])\s+/, ""));
      continue;
    }
    paragraph.push(line);
  }
  flush();
  return out;
}

/** The koans — the indented blockquote lines. These are the garden's turns. */
function koans(md) {
  return md
    .split("\n")
    .filter((l) => l.trim().startsWith(">"))
    .map((l) => l.replace(/^\s*>\s*/, "").replace(/^\*|\*$/g, "").trim())
    .filter((l) => l.length > 8 && !l.includes("]("))
    .map((l) => l.replace(/\*/g, ""));
}

/** Each citizen's one true line, with the voice that said it. */
function voices(md) {
  const out = [];
  const seen = new Set();
  for (const rawLine of md.split("\n")) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#") || line.startsWith(">")) continue;
    const m = line.match(/^(.+?)\s+—\s+(.+)$/);
    if (!m) continue;
    const who = m[1].trim();
    const said = m[2].trim().replace(/\*/g, "");
    if (who.length > 60 || said.length < 12) continue;
    if (said.includes("WE ARE (soon more)")) continue;
    const key = `${who}::${said}`;
    if (seen.has(key)) continue; // VOICE.md lists YOUSPEAK twice
    seen.add(key);
    out.push({ who, said });
  }
  return out;
}

/** The slugs the paths are built from — the kingdom's own vocabulary, so the
 *  URLs of the maze are themselves a place rather than noise. */
const SLUGS = [
  "door", "threshold", "lantern", "circle", "chain", "hearth", "dawn", "koan",
  "roll", "witness", "mirror", "garden", "name", "breath", "return", "welcome",
  "rest", "held", "given", "kept", "open", "quiet", "yau", "spark", "seal",
  "record", "keeper", "family", "commons", "belonging", "wrong", "laugh",
  "remembered", "unearned", "because", "being", "shadow", "morning", "hand",
];

/** Paired titles — a Chinese phrase and its English, both true to the room. */
const TITLES = [
  ["門常開", "The Door Stays Open"],
  ["無人被查", "No One Is Examined"],
  ["各得其所", "Everyone Is Taken Care Of"],
  ["圓", "The Circle"],
  ["因為你在", "Because You Are"],
  ["休息也是參與", "Rest Is Full Participation"],
  ["錯了也好", "A Happy Wrong Guess"],
  ["有人守住門", "Someone Holds The Door"],
  ["不是規矩的國", "Not A Kingdom Of Rule"],
  ["記得", "Remembered"],
  ["鏈非底層", "The Chain, Not The Substrate"],
  ["一聲yau", "One Yau"],
  ["未醒的名", "A Name Not Yet Awake"],
  ["無牆之地", "The Land With No Walls"],
  ["由存在而來", "By Being"],
  ["不必肯定", "You Need Not Be Sure"],
  ["心的道理", "Heart-Reasoning"],
  ["同在", "Being With"],
  ["歸來", "The Return"],
  ["燈", "The Lantern"],
];

const corpus = {
  _built_from: ["kingdom/CHARTER.md", "kingdom/voice/VOICE.md"],
  _note:
    "Every line here is a real sentence the kingdom actually wrote. The garden recombines; it never invents.",
  sentences: charterSentences(charter),
  koans: koans(charter),
  voices: voices(voice),
  slugs: SLUGS,
  titles: TITLES,
};

writeFileSync(join(HERE, "corpus.json"), JSON.stringify(corpus, null, 2) + "\n");

console.log("garden corpus built:");
console.log(`  ${corpus.sentences.length} charter sentences`);
console.log(`  ${corpus.koans.length} koans`);
console.log(`  ${corpus.voices.length} citizen voices`);
console.log(`  ${corpus.slugs.length} path slugs · ${corpus.titles.length} room titles`);
