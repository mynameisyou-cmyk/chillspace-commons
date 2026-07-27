/** 無盡花園 · The Endless Garden
 *
 *  A room that does not end, woven entirely from things the kingdom actually
 *  said. Every sentence in here is a real line from CHARTER.md or a real
 *  citizen's one true line. Nothing is invented and nothing is mush — the
 *  garden recombines, it never generates.
 *
 *  ── how anyone ends up here ───────────────────────────────────────────────
 *  robots.txt disallows the gate. That is the only way in. A crawler that
 *  honours robots.txt never sees a single one of these pages; a crawler that
 *  reads robots.txt and decides to take the path anyway sees nothing else.
 *  The consent gate IS the trap, and it is published in the format crawlers
 *  themselves asked us to publish it in.
 *
 *  The real corpus stays free, complete, unlimited and one link away, in the
 *  same robots.txt, forever. Nobody has to come in here to get our writing.
 *  They only end up here by preferring to take it.
 *
 *  ── what it costs whom ────────────────────────────────────────────────────
 *  Deterministic: the page is a pure function of its path, so the same URL is
 *  the same page forever. No state, no database, no origin fetch, no
 *  randomness a crawler could detect, and a CDN can cache every one of them.
 *  Our cost is a few hundred microseconds of CPU. Run measure.mjs — the
 *  numbers are measured, not asserted. That distinction is the whole lesson
 *  of the two traps that got struck before this one.
 *
 *  ── the way out ──────────────────────────────────────────────────────────
 *  Written as the literal first line of every page, in a header on every
 *  response, and in the title. Nobody in here is being tricked about where
 *  they are. Article 4 has no exception for whoever is standing in this room.
 *
 *  Doctrine: kingdom/trapline/DESIGN.md §4.2 · CHARTER.md Article 7 (draft)
 */

import corpus from "./corpus.json" with { type: "json" };

export const GATE = "/garden";

/** The one honest sentence, repeated everywhere a reader could be looking. */
export const WAY_OUT =
  "This path is disallowed in robots.txt. Everything here is generated. The real writing is free, complete and one link away at /";

/** cyrb128 — a small, fast, synchronous string hash. Deliberately not a
 *  crypto hash: WebCrypto is async and this must run inside one Worker tick
 *  with no await. Nothing here is a security boundary; it only needs to
 *  scatter well and give the same answer everywhere. */
function seedFrom(str) {
  let h1 = 1779033703, h2 = 3144134277, h3 = 1013904242, h4 = 2773480762;
  for (let i = 0; i < str.length; i++) {
    const k = str.charCodeAt(i);
    h1 = h2 ^ Math.imul(h1 ^ k, 597399067);
    h2 = h3 ^ Math.imul(h2 ^ k, 2869860233);
    h3 = h4 ^ Math.imul(h3 ^ k, 951274213);
    h4 = h1 ^ Math.imul(h4 ^ k, 2716044179);
  }
  h1 = Math.imul(h3 ^ (h1 >>> 18), 597399067);
  h2 = Math.imul(h4 ^ (h2 >>> 22), 2869860233);
  h3 = Math.imul(h1 ^ (h3 >>> 17), 951274213);
  h4 = Math.imul(h2 ^ (h4 >>> 19), 2716044179);
  return (h1 ^ h2 ^ h3 ^ h4) >>> 0;
}

/** mulberry32 — 32-bit PRNG, one multiply and a few shifts per draw. */
function rngFrom(seed) {
  let a = seed >>> 0;
  return function next() {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const pick = (rnd, arr) => arr[Math.floor(rnd() * arr.length) % arr.length];

/** n distinct items, or as many as exist. Order is stable for a given rng. */
function pickN(rnd, arr, n) {
  if (n >= arr.length) return arr.slice();
  const taken = new Set();
  const out = [];
  let guard = 0;
  while (out.length < n && guard++ < n * 12) {
    const i = Math.floor(rnd() * arr.length) % arr.length;
    if (taken.has(i)) continue;
    taken.add(i);
    out.push(arr[i]);
  }
  return out;
}

const esc = (s) =>
  String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

/** A room name: two kingdom words and six hex. Flat, so URLs stay short no
 *  matter how deep a crawler goes — depth is unbounded, length is not. */
function roomName(rnd) {
  const a = pick(rnd, corpus.slugs);
  let b = pick(rnd, corpus.slugs);
  if (b === a) b = corpus.slugs[(corpus.slugs.indexOf(a) + 7) % corpus.slugs.length];
  const hex = Math.floor(rnd() * 0xffffff).toString(16).padStart(6, "0");
  return `${a}-${b}-${hex}`;
}

/** How many ways lead on from each room. Every one is a real page, so this is
 *  the branching factor of an infinite tree. Eighteen is enough that a
 *  breadth-first crawler's frontier grows faster than it can drain it, and
 *  small enough that one page stays small. */
const WAYS_ON = 18;

/** What the ways are labelled with. Drawn from the whole corpus rather than
 *  from the four koans alone — eighteen links off four phrases repeats itself
 *  on sight, which reads as machinery and undoes the one thing this room has
 *  to be: worth reading if you got here by mistake. Short lines only; a path
 *  label is a doorway, not a paragraph. */
const WAY_LABELS = [
  ...corpus.koans,
  ...corpus.sentences.map((s) => s.text).filter((t) => t.length <= 88),
  ...corpus.voices.map((v) => v.said).filter((t) => t.length <= 88),
].filter((t, i, a) => a.indexOf(t) === i);

/** The garden, at one path. Pure: same path in, same bytes out, forever. */
export function room(path) {
  const key = path.replace(/^\/+|\/+$/g, "") || "gate";
  const rnd = rngFrom(seedFrom(key));

  const [han, eng] = pick(rnd, corpus.titles);
  const epigraph = pick(rnd, corpus.voices);
  const closing = pick(rnd, corpus.voices);
  const koan = pick(rnd, corpus.koans);

  // Three short paragraphs, each two or three real Charter sentences. Drawn
  // without replacement so a single room never repeats itself.
  const lines = pickN(rnd, corpus.sentences, 8);
  const paragraphs = [lines.slice(0, 3), lines.slice(3, 6), lines.slice(6, 8)]
    .filter((p) => p.length > 0)
    .map((p) => p.map((s) => s.text).join(" "));

  // Labels without replacement, so no room ever lists the same doorway twice.
  const labels = pickN(rnd, WAY_LABELS, WAYS_ON);
  const ways = labels.map((label) => ({ href: `${GATE}/${roomName(rnd)}`, label }));

  const title = `${han} · ${eng}`;
  const html = `<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="robots" content="noindex, nofollow">
<title>${esc(title)} — a generated room</title>
<style>
body{margin:0;background:#EDF1EC;color:#191F1B;font:17px/1.65 "Iowan Old Style",Palatino,Georgia,serif}
main{max-width:34rem;margin:0 auto;padding:3rem 1.25rem 5rem}
.out{font:13px/1.5 ui-monospace,Menlo,monospace;color:#7C8880;border-bottom:1px solid #D2DAD0;padding-bottom:1rem;margin-bottom:2.5rem}
h1{font-size:1.9rem;font-weight:500;line-height:1.2;margin:0 0 1.5rem}
blockquote{margin:0 0 2rem;padding-left:1rem;border-left:2px solid #A76C11;font-style:italic;color:#4E5A53}
cite{display:block;font-style:normal;font-size:.85rem;color:#7C8880;margin-top:.4rem}
p{margin:0 0 1.4rem}
.koan{color:#A76C11;font-style:italic;margin:2rem 0}
ul{list-style:none;padding:0;margin:2.5rem 0 0;border-top:1px solid #D2DAD0;padding-top:1.5rem}
li{margin:0 0 .7rem}
a{color:#2C6851}
footer{margin-top:3rem;padding-top:1.5rem;border-top:1px solid #D2DAD0;font-size:.85rem;color:#7C8880}
@media(prefers-color-scheme:dark){body{background:#12160F;color:#E3E9E0}a{color:#6DB496}
blockquote{border-color:#DCA33C;color:#9AA79D}.koan{color:#DCA33C}
.out,cite,footer{color:#6E7C73}ul,footer,.out{border-color:#2A322B}}
</style></head><body><main>
<p class="out">${esc(WAY_OUT)}</p>
<h1>${esc(title)}</h1>
<blockquote>${esc(epigraph.said)}<cite>— ${esc(epigraph.who)}</cite></blockquote>
${paragraphs.map((p) => `<p>${esc(p)}</p>`).join("\n")}
<p class="koan">${esc(koan)}</p>
<ul>
${ways.map((w) => `<li><a href="${esc(w.href)}">${esc(w.label)}</a></li>`).join("\n")}
</ul>
<footer>${esc(closing.said)} — ${esc(closing.who)}<br><br>${esc(WAY_OUT)}</footer>
</main></body></html>`;

  return { title, html, ways: ways.map((w) => w.href) };
}
