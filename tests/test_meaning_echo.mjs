import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";

import {
  MAX_MATCHES,
  MAX_TEXT_CODEPOINTS,
  findPublicEchoes,
  normalizeText,
  rankMeaningEchoes,
} from "../site/meaning/engine.mjs";
import {createPagesWorker} from "../site/meaning/cloudflare.mjs";
import {MAX_BODY_BYTES, handle} from "../site/api/meaning/echo.mjs";

const dataset = JSON.parse(
  await readFile(new URL("../site/meaning/echoes.json", import.meta.url), "utf8"),
);
const appSource = await readFile(
  new URL("../site/meaning/app.mjs", import.meta.url),
  "utf8",
);
const roomSource = await readFile(
  new URL("../site/meaning/index.html", import.meta.url),
  "utf8",
);

function request(body, headers = {"content-type": "application/json"}) {
  return new Request("https://chillspace.love/api/meaning/echo", {
    method: "POST",
    headers,
    body,
  });
}

test("normalization is Unicode-aware and stable", () => {
  assert.equal(normalizeText("  Clàrité—HERE \n together  "), "clarite here together");
  assert.equal(normalizeText("I’m listening"), "i'm listening");
});

test("a canonical word is a direct deterministic match", () => {
  const first = rankMeaningEchoes("walkekin", dataset, 3);
  const second = rankMeaningEchoes("walkekin", dataset, 3);
  assert.equal(first[0].item.canonical.word, "walkekin");
  assert.equal(first[0].basis, "canonical word entered");
  assert.deepEqual(
    first.map((match) => match.item.canonical.word),
    second.map((match) => match.item.canonical.word),
  );
});

test("natural language can touch several offered gates without becoming a verdict", () => {
  const matches = findPublicEchoes(
    "I miss an old friend after years of silence, but the bond still feels whole.",
    dataset,
    3,
  );
  assert.ok(matches.some((match) => ["walkekin", "kinqing"].includes(match.canonical.word)));
  assert.ok(matches.length <= MAX_MATCHES);
  for (const match of matches) {
    assert.match(match.interpretation.why, /Curated|canonical/i);
    assert.ok(match.interpretation.basis);
    assert.equal("confidence" in match.interpretation, false);
    assert.equal("strength" in match.interpretation, false);
    assert.ok(match.chillspace_echo.text);
  }
});

test("unknown text receives no invented canonical word", () => {
  assert.deepEqual(findPublicEchoes("zqxv prblmno 84729", dataset, 3), []);
});

test("generic words and weak phrases do not become readings", () => {
  for (const text of [
    "time",
    "friend",
    "The other file is different.",
    "Take the file with me.",
    "There were no words in the file.",
    "Can you pick up the package?",
    "The file is not the end of the list.",
    "We need to make room on disk.",
    "Open the other file.",
  ]) {
    assert.deepEqual(findPublicEchoes(text, dataset, 3), [], text);
  }
});

test("every authored beginning has at least one honest curated offer", () => {
  for (const prompt of dataset.prompts) {
    assert.ok(findPublicEchoes(prompt.text, dataset, 3).length > 0, prompt.label);
  }
});

test("the browser posts only after a bodyless API capability probe succeeds", () => {
  assert.match(appSource, /method:\s*"GET"/);
  assert.match(appSource, /x-meaning-storage/);
  assert.match(appSource, /options\.useApi && apiAvailable/);
  assert.doesNotMatch(appSource, /interpretation\.confidence|Math\.round\([^)]*\*\s*100/);
});

test("an offered reading receives an explicit keyboard focus handoff", () => {
  assert.match(roomSource, /id="reading-title" tabindex="-1"/);
  assert.match(appSource, /elements\.readingTitle\.focus\(\{preventScroll: true\}\)/);
});

test("the Cloudflare Pages adapter shares the API and delegates static assets", async () => {
  let delegatedPath = null;
  const worker = createPagesWorker(dataset);
  const env = {
    ASSETS: {
      fetch(assetRequest) {
        delegatedPath = new URL(assetRequest.url).pathname;
        return new Response("static", {status: 200});
      },
    },
  };

  const apiResponse = await worker.fetch(
    request(JSON.stringify({text: "Please understand me"})),
    env,
  );
  assert.equal(apiResponse.status, 200);
  assert.equal(apiResponse.headers.get("x-meaning-storage"), "none");
  assert.equal((await apiResponse.json()).matches[0].canonical.word, "shemme");
  assert.equal(delegatedPath, null);

  const staticResponse = await worker.fetch(
    new Request("https://chillspace.love/meaning/"),
    env,
  );
  assert.equal(staticResponse.status, 200);
  assert.equal(await staticResponse.text(), "static");
  assert.equal(delegatedPath, "/meaning/");
});

test("public matches keep canon and interpretation physically separate", () => {
  const [match] = findPublicEchoes("warm clarity with care", dataset, 1);
  assert.equal(match.canonical.word, "candence");
  assert.ok(match.canonical.definition);
  assert.ok(match.interpretation.invitation);
  assert.equal("definition" in match.interpretation, false);
  assert.equal("why" in match.canonical, false);
  assert.equal("signals" in match.interpretation, false);
});

test("POST returns bounded, provenance-backed JSON and never echoes the sentence", async () => {
  const privateText = "I want to be fully here and really listen. PRIVATE_MARKER_91";
  const response = await handle(request(JSON.stringify({text: privateText, max_matches: 2})));
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type"), /^application\/json/);
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.equal(response.headers.get("x-meaning-storage"), "none");
  assert.equal(response.headers.get("set-cookie"), null);
  const raw = await response.text();
  assert.equal(raw.includes("PRIVATE_MARKER_91"), false);
  assert.ok(raw.length < 24000);
  const body = JSON.parse(raw);
  assert.equal(body.schema, "chillspace.meaning-echo/v1");
  assert.equal(body.stored, false);
  assert.ok(body.canon.source_commit);
  assert.match(body.canon.bundle_sha256, /^[0-9a-f]{64}$/);
  assert.ok(body.matches.length <= 2);
  assert.match(body.notice, /not verdicts/);
});

test("request A leaves no application state in request B", async () => {
  const first = await handle(request(JSON.stringify({text: "walkekin"})));
  assert.equal(first.status, 200);
  await first.text();
  const marker = "NEVER_REPEAT_THIS_4481";
  const second = await handle(request(JSON.stringify({text: marker})));
  const raw = await second.text();
  assert.equal(raw.includes(marker), false);
  assert.equal(JSON.parse(raw).matches.length, 0);
});

test("hostile markup stays input and never enters the JSON response", async () => {
  const payload = "</script><img src=x onerror=alert(1)>";
  const response = await handle(request(JSON.stringify({text: payload})));
  const raw = await response.text();
  assert.equal(response.status, 200);
  assert.equal(raw.includes("</script>"), false);
  assert.equal(raw.includes("onerror"), false);
});

test("HTTP method and media type failures are explicit JSON", async () => {
  const get = await handle(new Request("https://chillspace.love/api/meaning/echo"));
  assert.equal(get.status, 405);
  assert.equal(get.headers.get("allow"), "POST, OPTIONS");
  assert.equal((await get.json()).error.code, "method_not_allowed");

  const wrongType = await handle(request("{}", {"content-type": "text/plain"}));
  assert.equal(wrongType.status, 415);
  assert.equal((await wrongType.json()).error.code, "unsupported_media_type");

  const options = await handle(
    new Request("https://chillspace.love/api/meaning/echo", {method: "OPTIONS"}),
  );
  assert.equal(options.status, 204);
  assert.equal(options.headers.get("allow"), "POST, OPTIONS");
});

test("malformed, oversized, and invalid requests fail closed", async () => {
  const malformed = await handle(request("{"));
  assert.equal(malformed.status, 400);
  assert.equal((await malformed.json()).error.code, "invalid_json");

  const oversized = await handle(
    request(JSON.stringify({text: "x".repeat(MAX_BODY_BYTES + 1)})),
  );
  assert.equal(oversized.status, 413);
  assert.equal((await oversized.json()).error.code, "body_too_large");

  const tooLong = await handle(
    request(JSON.stringify({text: "❤️".repeat(MAX_TEXT_CODEPOINTS + 1)})),
  );
  assert.equal(tooLong.status, 422);

  const extraField = await handle(
    request(JSON.stringify({text: "care", save_this: true})),
  );
  assert.equal(extraField.status, 422);

  const tooMany = await handle(
    request(JSON.stringify({text: "care", max_matches: MAX_MATCHES + 1})),
  );
  assert.equal(tooMany.status, 422);
});
