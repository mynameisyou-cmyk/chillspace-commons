import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import {createRequire} from "node:module";
import {fileURLToPath} from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
require(path.join(HERE, "dashboard", "app.js"));

const api = globalThis.PlainCommonsDashboard;
const GOLDEN_PATH = path.join(HERE, "examples", "picnic.receipt.json");
const ENGINE_PATH = path.join(HERE, "plain_commons.py");
const SOURCE_SCHEMA_PATH = path.join(HERE, "source.schema.json");
const RECEIPT_SCHEMA_PATH = path.join(HERE, "receipt.schema.json");
const HTML_PATH = path.join(HERE, "dashboard", "index.html");
const CSS_PATH = path.join(HERE, "dashboard", "styles.css");
const APP_PATH = path.join(HERE, "dashboard", "app.js");

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function sha256File(file) {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}

function sri(file) {
  return "sha384-" + crypto.createHash("sha384").update(fs.readFileSync(file)).digest("base64");
}

function goldenText() {
  return fs.readFileSync(GOLDEN_PATH, "utf8");
}

function goldenReceipt() {
  const text = goldenText();
  return api.parseCanonicalReceipt(text, Buffer.byteLength(text));
}

test("golden receipt survives exact browser reconstruction", () => {
  const receipt = goldenReceipt();
  assert.equal(receipt.source_sha256, "d079e43462eb78d12de10fe1d9b332e73462ca6f334856e61da3211e9190bc18");
  assert.equal(receipt.receipt_sha256, "b3fd38b8a2ab2d12162e63aafe90721bf540cd66ce657b95982a716336d6e32a");
  assert.equal(receipt.matches.length, 2);
  assert.deepEqual(api.reconstructReceipt(receipt.source), receipt);
});

test("browser pins exactly the reviewed engine and schema bytes", () => {
  assert.deepEqual(api.PINNED_BINDINGS, {
    engine_sha256: sha256File(ENGINE_PATH),
    receipt_schema_sha256: sha256File(RECEIPT_SCHEMA_PATH),
    source_schema_sha256: sha256File(SOURCE_SCHEMA_PATH)
  });
});

test("browser SHA-256 and canonical JSON agree with known vectors", () => {
  assert.equal(
    api.sha256Ascii("abc"),
    "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
  );
  assert.equal(
    api.canonicalStringify({z: "❤️", a: [true, 2]}),
    "{\"a\":[true,2],\"z\":\"\\u2764\\ufe0f\"}"
  );
});

test("redigested match and policy forgeries fail exact reconstruction", () => {
  const forgedMatch = clone(goldenReceipt());
  forgedMatch.matches[0].offer_participant_ref = "forged-participant";
  forgedMatch.receipt_sha256 = api.digestWithout(forgedMatch, "receipt_sha256");
  assert.throws(() => api.validateReceipt(forgedMatch), /pinned reviewed build/);

  const forgedControl = clone(goldenReceipt());
  forgedControl.controls.rank_effects = 1;
  forgedControl.receipt_sha256 = api.digestWithout(forgedControl, "receipt_sha256");
  assert.throws(() => api.validateReceipt(forgedControl), /pinned reviewed build|unexpected value/);
});

test("duplicate keys and noncanonical JSON never reach the dashboard", () => {
  const text = goldenText();
  const duplicate = text.replace(/^\{/, "{\"schema\":\"kingdom.plain-commons\/v1\",");
  assert.throws(
    () => api.parseCanonicalReceipt(duplicate, Buffer.byteLength(duplicate)),
    /canonical JSON/
  );
  const pretty = JSON.stringify(JSON.parse(text), null, 2) + "\n";
  assert.throws(
    () => api.parseCanonicalReceipt(pretty, Buffer.byteLength(pretty)),
    /canonical JSON/
  );
});

test("ad-shaped fields and repeated slots cannot enter the source", () => {
  const source = clone(goldenReceipt().source);
  source.declarations[0].boost = 999;
  assert.throws(() => api.validateSource(source), /unexpected shape/);

  const repeated = clone(goldenReceipt().source);
  const duplicate = clone(repeated.declarations[0]);
  duplicate.declaration_id = "repeat-cannot-buy-a-chair";
  duplicate.evidence[0].evidence_id = "repeat-evidence";
  repeated.declarations.push(duplicate);
  repeated.declarations.sort((left, right) =>
    left.participant_ref.localeCompare(right.participant_ref, "en") ||
    left.side.localeCompare(right.side, "en") ||
    left.tag.localeCompare(right.tag, "en") ||
    left.declaration_id.localeCompare(right.declaration_id, "en")
  );
  assert.throws(() => api.validateSource(repeated), /duplicates a participant-side-tag slot/);
});

test("wording and evidence volume cannot change eligibility or order", () => {
  const source = clone(goldenReceipt().source);
  const declaration = source.declarations.find((item) => item.declaration_id === "blanket-offer");
  declaration.statement = "Plain blankets, with an intentionally different sentence.";
  declaration.evidence.push({
    evidence_id: "zz-extra-evidence",
    type: "artifact-digest",
    note: "A caller-supplied artifact digest for separate human review.",
    sha256: "f".repeat(64)
  });
  declaration.evidence.sort((left, right) => left.evidence_id.localeCompare(right.evidence_id, "en"));
  api.validateSource(source);
  assert.deepEqual(api.buildMatches(source), goldenReceipt().matches);
});

test("withdrawal removes the declaration without inventing another fit", () => {
  const source = clone(goldenReceipt().source);
  const declaration = source.declarations.find((item) => item.declaration_id === "tool-box-offer");
  declaration.state = "withdrawn";
  declaration.consent = "withdrawn";
  const rebuilt = api.reconstructReceipt(source);
  assert.equal(rebuilt.summary.withdrawn_declarations, 2);
  assert.equal(rebuilt.summary.matches, 1);
  assert.equal(rebuilt.matches[0].tag, "picnic-blankets");
  assert.deepEqual(api.validateReceipt(rebuilt), rebuilt);
});

test("dashboard assets are content-bound and the page is egress-closed", () => {
  const html = fs.readFileSync(HTML_PATH, "utf8");
  const app = fs.readFileSync(APP_PATH, "utf8");
  assert.match(html, /connect-src 'none'/);
  assert.match(html, /frame-ancestors 'none'/);
  assert.match(html, /referrer[^>]+no-referrer/);
  assert.match(html, new RegExp(`integrity="${sri(CSS_PATH).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}"`));
  assert.match(html, new RegExp(`integrity="${sri(APP_PATH).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}"`));
  assert.doesNotMatch(html, /https?:\/\//i);
  assert.doesNotMatch(app, /\b(?:fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon)\s*\(/);
  assert.doesNotMatch(app, /\b(?:localStorage|sessionStorage|indexedDB)\b/);
  assert.doesNotMatch(app, /\b(?:innerHTML|outerHTML|document\.write|Blob|createObjectURL)\b/);
  assert.match(app, /\.textContent\s*=/);
});

test("local reviewer keeps basic keyboard, status, contrast, and motion rails", () => {
  const html = fs.readFileSync(HTML_PATH, "utf8");
  const css = fs.readFileSync(CSS_PATH, "utf8");
  assert.match(html, /class="skip-link"/);
  assert.match(html, /for="receipt-file"/);
  assert.match(html, /role="status" aria-live="polite"/);
  assert.match(html, /class="origin-note"/);
  assert.match(css, /:focus-visible/);
  assert.match(css, /prefers-reduced-motion/);
  assert.match(css, /prefers-contrast: more/);
  assert.match(css, /@media \(max-width: 31rem\)/);
});

test("a simulated browser import renders and clears the golden receipt", () => {
  class FakeElement {
    constructor(id = "") {
      this.id = id;
      this.children = [];
      this.listeners = new Map();
      this.dataset = {};
      this.hidden = false;
      this.disabled = false;
      this.value = "";
      this.files = [];
      this.className = "";
      this._text = "";
    }

    set textContent(value) {
      this._text = String(value);
      this.children = [];
    }

    get textContent() {
      return this._text;
    }

    get firstChild() {
      return this.children[0] ?? null;
    }

    append(...children) {
      this.children.push(...children);
    }

    removeChild(child) {
      const index = this.children.indexOf(child);
      if (index >= 0) this.children.splice(index, 1);
      return child;
    }

    addEventListener(name, listener) {
      this.listeners.set(name, listener);
    }

    dispatch(name) {
      const listener = this.listeners.get(name);
      if (listener) listener({target: this});
    }
  }

  class FakeFileReader {
    constructor() {
      this.listeners = new Map();
      this.result = null;
    }

    addEventListener(name, listener) {
      this.listeners.set(name, listener);
    }

    readAsText(file) {
      this.result = file.text;
      this.listeners.get("load")();
    }
  }

  const ids = [
    "receipt-file", "clear-button", "status", "empty-state", "dashboard",
    "matches", "no-matches", "unknowns", "controls", "metric-matches",
    "metric-active", "metric-withdrawn", "receipt-id"
  ];
  const elements = new Map(ids.map((id) => [id, new FakeElement(id)]));
  elements.get("dashboard").hidden = true;
  const document = {
    readyState: "complete",
    getElementById(id) {
      return elements.get(id);
    },
    createElement() {
      return new FakeElement();
    }
  };
  const context = vm.createContext({document, FileReader: FakeFileReader});
  vm.runInContext(fs.readFileSync(APP_PATH, "utf8"), context, {filename: APP_PATH});

  const text = goldenText();
  const input = elements.get("receipt-file");
  input.files = [{size: Buffer.byteLength(text), text}];
  input.dispatch("change");

  assert.equal(elements.get("dashboard").hidden, false);
  assert.equal(elements.get("empty-state").hidden, true);
  assert.equal(elements.get("metric-matches").textContent, "2");
  assert.equal(elements.get("metric-active").textContent, "5");
  assert.equal(elements.get("metric-withdrawn").textContent, "1");
  assert.equal(elements.get("matches").children.length, 2);
  assert.equal(elements.get("unknowns").children.length, 4);
  assert.equal(elements.get("controls").children.length, 20);
  assert.match(elements.get("status").textContent, /exact local reconstruction/);

  elements.get("clear-button").dispatch("click");
  assert.equal(elements.get("dashboard").hidden, true);
  assert.equal(elements.get("empty-state").hidden, false);
  assert.equal(input.value, "");
  assert.equal(elements.get("matches").children.length, 0);
});
