// Every door names its own home. chillspace.love is the commons' canonical
// site; the same bytes are also served at chillspace-love.pages.dev, at the
// Vercel mirror and (for a subset of the rooms) at the GitHub Pages copy, and
// search engines were indexing those copies. A page's
// canonical is the absolute chillspace.love URL that answers 200: directories
// keep their slash, and Pages 308s /room.html to /room. we-are.html is the
// we-are.love front door, so it points there and stays out of this sitemap.
import assert from "node:assert/strict";
import { existsSync, readFileSync, statSync } from "node:fs";
import test from "node:test";

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), "utf8");
const HOME = "https://chillspace.love/";

// These rooms' own checks forbid any absolute href or pin their reviewed
// bytes, so they carry no canonical yet; changing that is their owners' call.
// A guarded page may carry no canonical, or exactly its own, never another.
const GUARDED = new Set([
  "site/operations/dark-continent-ai/index.html",
  "site/operations/mirror-garden/index.html",
  "site/practices/virtue-garden/index.html",
  "site/practices/virtue-garden/mirror/index.html",
  "site/practices/virtue-garden/mirror/foresight/index.html",
  "site/practices/virtue-garden/mirror/foresight/facet/index.html",
]);

const canonicals = (html) =>
  [...html.matchAll(/<link\b[^>]*\brel="canonical"[^>]*>/gu)].map(([tag]) => tag.match(/\bhref="([^"]*)"/u)?.[1]);

// https://chillspace.love/a/b/ -> site/a/b/index.html; https://chillspace.love/room -> site/room.html
function sourceFor(url) {
  const path = url.slice(HOME.length);
  if (path === "") return "site/index.html";
  const candidate = path.endsWith("/") ? `site/${path}index.html` : `site/${path}.html`;
  return candidate;
}

const sitemap = [...read("site/sitemap.xml").matchAll(/<loc>([^<]+)<\/loc>/gu)].map(([, loc]) => loc);

test("every sitemap URL is an absolute chillspace.love page that is really there", () => {
  assert.ok(sitemap.length > 0);
  assert.equal(new Set(sitemap).size, sitemap.length);
  for (const url of sitemap) {
    assert.ok(url.startsWith(HOME), url);
    assert.ok(!url.endsWith(".html"), `${url}: Pages answers .html with a 308`);
    const source = sourceFor(url);
    assert.ok(existsSync(new URL(`../${source}`, import.meta.url)) && statSync(new URL(`../${source}`, import.meta.url)).isFile(), `${url}: no ${source}`);
  }
  assert.ok(read("site/robots.txt").includes("\nSitemap: https://chillspace.love/sitemap.xml\n"));
});

test("each listed page names itself as canonical, unless its own guard forbids it", () => {
  for (const url of sitemap) {
    const source = sourceFor(url);
    const found = canonicals(read(source));
    if (GUARDED.has(source) && found.length === 0) continue;
    assert.deepEqual(found, [url], source);
  }
});

// These four stay out of the sitemap on purpose: no page links to them, and
// neither curated copy (deploy-public-door.yml, the Codeberg recipe) carries
// them; they reach chillspace.love only because the whole site/ tree is
// uploaded there. Listing them is a choice about what the site offers, not an
// index fix. The mirrors that carry them still point here.
test("rooms outside the sitemap still point at their chillspace.love URL", () => {
  for (const [source, url] of [
    ["site/arcade.html", "https://chillspace.love/arcade"],
    ["site/games.html", "https://chillspace.love/games"],
    ["site/sound.html", "https://chillspace.love/sound"],
    ["site/truth-or-noise.html", "https://chillspace.love/truth-or-noise"],
  ]) {
    assert.deepEqual(canonicals(read(source)), [url], source);
  }
});

test("the WE ARE page points at we-are.love, its own front door", () => {
  assert.deepEqual(canonicals(read("site/we-are.html")), ["https://we-are.love/"]);
  assert.ok(!sitemap.some((url) => url.includes("we-are")), "a page whose canonical is elsewhere stays out of this sitemap");
});

test("no page still names the old GitHub Pages copy as its home", () => {
  for (const source of ["site/coop-leveling.html", "site/exchange/model-release/index.html"]) {
    const html = read(source);
    assert.ok(!/(?:canonical|og:url)"[^>]*mynameisyou-cmyk\.github\.io/u.test(html), source);
  }
});
