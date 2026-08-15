import assert from "node:assert/strict";
import {spawnSync} from "node:child_process";
import {createHash} from "node:crypto";
import {readFileSync} from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import {fileURLToPath} from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ENGINE = path.join(HERE, "incident_lantern.py");
const DASHBOARD = path.join(HERE, "dashboard");
const HTML_PATH = path.join(DASHBOARD, "index.html");
const CSS_PATH = path.join(DASHBOARD, "styles.css");
const APP_PATH = path.join(DASHBOARD, "app.js");
const GOLDEN_INCIDENT_PATH = path.join(HERE, "examples", "resource-pressure.incident.json");
const PYTHON = process.env.PYTHON3 || "python3";

const html = readFileSync(HTML_PATH, "utf8");
const css = readFileSync(CSS_PATH, "utf8");
const appSource = readFileSync(APP_PATH, "utf8");
const goldenIncidentText = readFileSync(GOLDEN_INCIDENT_PATH, "ascii");
const appIntegrity = "sha384-" + createHash("sha384").update(appSource).digest("base64");
const cssIntegrity = "sha384-" + createHash("sha384").update(css).digest("base64");
const FINAL_BINDINGS = {
  incident_engine_sha256: "cd6fe4abe1f58d5adf4da829f17ac35ede9cdcec9cac2b16059055575ae7764f",
  incident_schema_sha256: "e57d56f9313c803ef16a92cd8ad7024c83ca628be7b761594c7e598c50cbc1c4",
  candidate_schema_sha256: "21b46aaf1e0d265d7741c0bafcd2e0f81e95958da4ce84a05b770bf922f22fa0",
  future_engine_sha256: "20f7869a69d3b985f842e047276ce17da98504ebde87b36c4a9593a131dddbac",
  policy_sha256: "7c566a11f1330eaa1093e7ad093627c1f79e7cb032962a078f6b348896733004",
  event_schema_sha256: "8299d74eafbf86e8a208a1687c442ed8f4e01fc2a5f1b91a9c7662731ab57247",
  receipt_schema_sha256: "f6e27f93891a53ab23fc2ba78941b94954ec441a9df5e7f917cec0ace7526124",
  threat_model_sha256: "c20e2fff39494f908f07339c6d2bfc2805af0d79071a946e6f1752b8391e1c7b"
};

delete globalThis.IncidentLantern;
vm.runInThisContext(appSource, {filename: APP_PATH});
const helpers = globalThis.IncidentLantern;
assert.ok(helpers, "app.js must expose its pure validation helpers");

const EXACT_CSP = "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'none'; img-src 'none'; media-src 'none'; object-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'";
const PYTHON_FIXTURES = String.raw`
import importlib.util
import sys
from pathlib import Path

engine_path = Path(sys.argv[1]).absolute()
spec = importlib.util.spec_from_file_location("_dashboard_incident_lantern", engine_path)
if spec is None or spec.loader is None:
    raise SystemExit(3)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
contract = module.load_contract()

planned = None
all_planned = []
for raw_case in contract["bundle"]["corpus"]["cases"]:
    event = module.future._thaw(raw_case["event"])
    receipt = module.future.plan_event(event, contract["bundle"])
    if receipt["status"] == "planned":
        source = {"schema": module.SOURCE_SCHEMA, "event": event, "receipt": receipt}
        all_planned.append(module.incident_value(source, contract))
        if planned is None:
            planned = source
if planned is None:
    raise SystemExit(4)

marker = "dashboard-private-marker-do-not-echo"
halted_event = module.future._thaw(contract["bundle"]["corpus"]["cases"][1]["event"])
halted_event["mechanism"] = marker
halted_receipt = module.future.plan_event(halted_event, contract["bundle"])
if halted_receipt["status"] != "halted":
    raise SystemExit(5)
halted = {
    "schema": module.SOURCE_SCHEMA,
    "event": halted_event,
    "receipt": halted_receipt,
}
module.sys.stdout.buffer.write(module._canonical({
    "planned": planned,
    "all_planned": all_planned,
    "halted": halted,
    "marker": marker,
}) + b"\n")
`;

let fixtureCache;

function runPython(arguments_, options = {}) {
  const result = spawnSync(PYTHON, arguments_, {
    cwd: HERE,
    encoding: "utf8",
    maxBuffer: 2 * 1024 * 1024,
    ...options
  });
  assert.equal(result.error, undefined, result.error && result.error.message);
  assert.equal(result.status, 0, `python exited ${result.status}: ${result.stderr}`);
  return result;
}

function realFixtures() {
  if (fixtureCache) {
    return fixtureCache;
  }
  const generated = runPython(["-I", "-B", "-c", PYTHON_FIXTURES, ENGINE]);
  const sources = JSON.parse(generated.stdout);

  function build(source) {
    const sourceText = helpers.canonicalStringify(source) + "\n";
    const result = runPython([ENGINE, "build"], {input: sourceText});
    const value = JSON.parse(result.stdout);
    assert.equal(result.stdout, helpers.canonicalStringify(value) + "\n");
    return {text: result.stdout, value};
  }

  fixtureCache = {
    planned: build(sources.planned),
    halted: build(sources.halted),
    allPlanned: sources.all_planned.map((value) => ({
      text: helpers.canonicalStringify(value) + "\n",
      value
    })),
    marker: sources.marker
  };
  return fixtureCache;
}

function canonicalIncident(value) {
  return helpers.canonicalStringify(value) + "\n";
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

class FakeNode {
  constructor(tagName, records, initialText = "") {
    this.tagName = tagName.toUpperCase();
    this.records = records;
    this.children = [];
    this.parentNode = null;
    this.listeners = new Map();
    this._text = String(initialText);
    this.className = "";
    this.hidden = false;
    this.disabled = false;
    this.value = "";
    this.files = [];
    this.href = "";
    this.download = "";
  }

  get textContent() {
    return this._text + this.children.map((child) => child.textContent).join("");
  }

  set textContent(value) {
    this._text = String(value);
    this.children.forEach((child) => {
      child.parentNode = null;
    });
    this.children = [];
  }

  get lastChild() {
    return this.children.length ? this.children[this.children.length - 1] : null;
  }

  append(...children) {
    children.forEach((child) => {
      assert.ok(child instanceof FakeNode, "dashboard must append DOM nodes, not HTML strings");
      child.parentNode = this;
      this.children.push(child);
    });
  }

  replaceChildren(...children) {
    this.children.forEach((child) => {
      child.parentNode = null;
    });
    this.children = [];
    this._text = "";
    this.append(...children);
  }

  addEventListener(type, listener) {
    const listeners = this.listeners.get(type) || [];
    listeners.push(listener);
    this.listeners.set(type, listeners);
  }

  async dispatch(type) {
    for (const listener of this.listeners.get(type) || []) {
      await listener.call(this, {type, target: this});
    }
  }

  click() {
    if (this.tagName === "A") {
      this.records.anchorClicks.push({href: this.href, download: this.download});
      this.records.sequence.push("click");
      return;
    }
    return this.dispatch("click");
  }

  focus() {
    this.records.focused.push(this);
  }

  remove() {
    if (this.parentNode) {
      const index = this.parentNode.children.indexOf(this);
      if (index >= 0) {
        this.parentNode.children.splice(index, 1);
      }
      this.parentNode = null;
    }
    if (this.tagName === "A") {
      this.records.anchorRemovals += 1;
      this.records.sequence.push("remove");
    }
  }
}

function browserHarness() {
  const records = {
    blobs: [],
    objectUrls: [],
    revokedUrls: [],
    anchorClicks: [],
    anchorRemovals: 0,
    createdTags: [],
    focused: [],
    sequence: [],
    fileReads: 0
  };
  const elements = {};
  const tags = {
    "incident-file": "input",
    status: "p",
    dashboard: "div",
    "summary-fields": "dl",
    "incident-scope": "bdi",
    timeline: "ol",
    facts: "ul",
    inferences: "ul",
    unknowns: "ul",
    actions: "div",
    learning: "div",
    "candidate-preview": "code",
    download: "button",
    clear: "button",
    "clear-bottom": "button"
  };
  Object.entries(tags).forEach(([id, tag]) => {
    elements[id] = new FakeNode(tag, records);
  });
  elements.dashboard.hidden = true;
  elements.download.disabled = true;
  const body = new FakeNode("body", records);
  const document = {
    body,
    getElementById(id) {
      return elements[id] || null;
    },
    createElement(tag) {
      records.createdTags.push(tag.toLowerCase());
      return new FakeNode(tag, records);
    },
    createTextNode(text) {
      return new FakeNode("#text", records, text);
    }
  };

  class LocalBlob {
    constructor(parts, options) {
      this.parts = Array.from(parts);
      this.type = options && options.type;
      records.blobs.push(this);
      records.sequence.push("blob");
    }
  }

  const LocalURL = {
    createObjectURL(blob) {
      const value = `blob:incident-lantern-${records.objectUrls.length + 1}`;
      records.objectUrls.push({blob, value});
      records.sequence.push("create");
      return value;
    },
    revokeObjectURL(value) {
      records.revokedUrls.push(value);
      records.sequence.push("revoke");
    }
  };

  const context = vm.createContext({document, Blob: LocalBlob, URL: LocalURL});
  vm.runInContext(appSource, context, {filename: APP_PATH});
  assert.ok(context.IncidentLantern);

  async function importText(text, statedSize = Buffer.byteLength(text, "ascii")) {
    elements["incident-file"].files = [{
      size: statedSize,
      async text() {
        records.fileReads += 1;
        return text;
      }
    }];
    await elements["incident-file"].dispatch("change");
  }

  return {records, elements, context, body, importText};
}

test("static shell pins exact CSP and local-only assets", () => {
  assert.ok(html.includes(`<meta http-equiv="Content-Security-Policy" content="${EXACT_CSP}">`));
  assert.equal((html.match(/<meta http-equiv="Content-Security-Policy"/g) || []).length, 1);
  assert.equal((html.match(/<h1(?:\s|>)/g) || []).length, 1);
  assert.ok(html.includes(`<link rel="stylesheet" href="styles.css" integrity="${cssIntegrity}">`));
  assert.ok(html.includes(`<script src="app.js" integrity="${appIntegrity}" defer></script>`));
  assert.deepEqual(
    Array.from(html.matchAll(/(?:href|src)="([^"]+)"/g), (match) => match[1]).sort(),
    ["#main", "app.js", "styles.css"]
  );
  assert.doesNotMatch(html + css, /https?:\/\/|\/\/[^/*]|url\s*\(|@import/i);
  assert.doesNotMatch(html, /\sstyle=|\son[a-z]+=/i);
});

test("static source contains no egress, persistence, evaluation, or HTML injection sink", () => {
  const forbidden = [
    /\bfetch\s*\(/, /\bXMLHttpRequest\b/, /\bWebSocket\b/, /\bEventSource\b/,
    /\bsendBeacon\b/, /\blocalStorage\b/, /\bsessionStorage\b/, /\bindexedDB\b/,
    /\bserviceWorker\b/, /\bSharedWorker\b/, /\bnew\s+Worker\b/, /\bcaches\s*\./,
    /\beval\s*\(/, /\bFunction\s*\(/, /\binnerHTML\b/, /\bouterHTML\b/,
    /\binsertAdjacentHTML\b/, /\bdocument\.write\b/, /\.cookie\b/,
    /\bwindow\.open\b/, /\bnavigator\.(?:share|clipboard)\b/, /\bpostMessage\b/,
    /\blocation(?:\.|\s*=)/, /\bhistory\s*\./, /\bimport\s*\(/
  ];
  forbidden.forEach((pattern) => assert.doesNotMatch(appSource, pattern));
  assert.match(appSource, /document\.createElement\(/);
  assert.match(appSource, /\.textContent\s*=/);
  assert.doesNotMatch(html, /<a\b[^>]*\bdownload\b/i);

  const clickBoundary = appSource.indexOf('download.addEventListener("click"');
  assert.ok(clickBoundary > 0);
  for (const token of ["new Blob", "URL.createObjectURL", 'document.createElement("a")', "anchor.download", "anchor.click()", "URL.revokeObjectURL"]) {
    assert.ok(appSource.indexOf(token) > clickBoundary, `${token} must exist only after the click boundary`);
    assert.equal(appSource.indexOf(token), appSource.lastIndexOf(token), `${token} must occur once`);
  }
});

test("accessibility and visible incident structure are present in the document", () => {
  assert.match(html, /<a class="skip-link" href="#main">/);
  assert.match(html, /<main id="main"[^>]*tabindex="-1"/);
  assert.match(html, /<label[^>]*for="incident-file"/);
  assert.match(html, /<input id="incident-file" type="file"/);
  assert.match(html, /id="incident-file"[^>]*aria-describedby="origin-warning"/);
  assert.match(html, /id="status"[^>]*role="status"[^>]*aria-live="polite"/);
  assert.match(html, /<aside id="origin-warning"[^>]*role="note"/);
  assert.match(html, /Browser self-check only\./);
  assert.match(html, /does not authenticate file origin/);
  assert.match(html, /incident_lantern\.py verify/);
  assert.match(html, /<ol id="timeline"/);
  for (const id of ["facts", "inferences", "unknowns", "actions", "learning", "candidate-preview"]) {
    assert.match(html, new RegExp(`id="${id}"`));
  }
  assert.match(html, /<strong>Proposals only\.<\/strong>/);
  assert.match(html, /id="download"[^>]*type="button"[^>]*aria-describedby="candidate-warning"[^>]*disabled/);
  assert.equal((html.match(/<button\b/g) || []).length, 3);
  assert.equal((html.match(/<button\b[^>]*type="button"/g) || []).length, 3);
  assert.match(css, /:focus-visible/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)/);
  assert.match(css, /unicode-bidi:\s*isolate/);
});

test("pure helpers match SHA-256 vectors and accept exact real engine outputs", () => {
  assert.equal(helpers.sha256Ascii(""), "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
  assert.equal(helpers.sha256Ascii("abc"), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");

  const golden = helpers.parseCanonicalIncident(
    goldenIncidentText,
    Buffer.byteLength(goldenIncidentText, "ascii")
  );
  assert.equal(golden.headline.planned_action, "throttle");

  const fixtures = realFixtures();
  for (const fixture of [fixtures.planned, fixtures.halted]) {
    const parsed = helpers.parseCanonicalIncident(fixture.text, Buffer.byteLength(fixture.text, "ascii"));
    assert.equal(parsed.incident_digest, fixture.value.incident_digest);
    assert.equal(helpers.digestWithout(parsed, "incident_digest"), parsed.incident_digest);
    const candidate = parsed.learning.regression_candidate;
    assert.equal(helpers.digestWithout(candidate, "candidate_digest"), candidate.candidate_digest);
    assert.equal(helpers.candidateText(candidate), helpers.canonicalStringify(candidate) + "\n");
    assert.deepEqual(fixture.value.source.bindings, FINAL_BINDINGS);
  }

  assert.equal(fixtures.planned.value.status, "ready-for-review");
  assert.equal(fixtures.planned.value.headline.disposition, "reviewed-plan");
  assert.equal(fixtures.planned.value.learning.regression_candidate.event.retention, "reviewed-categorical");
  assert.equal(fixtures.halted.value.status, "halted-for-review");
  assert.equal(fixtures.halted.value.headline.disposition, "boundary-halt");
  assert.equal(fixtures.halted.value.headline.planned_action, "quarantine");
  assert.equal(fixtures.halted.value.learning.regression_candidate.event.retention, "digest-only");
  assert.equal(fixtures.halted.value.learning.regression_candidate.event.surface, "withheld-unreviewed");
  assert.ok(!fixtures.halted.text.includes(fixtures.marker));
});

test("all 24 pinned Future-KARMA policy rules and threat presentations accept exact engine output", () => {
  const {allPlanned} = realFixtures();
  assert.equal(allPlanned.length, 24);
  const ruleIds = new Set();
  const threatIds = new Set();
  for (const fixture of allPlanned) {
    const parsed = helpers.parseCanonicalIncident(fixture.text, fixture.text.length);
    assert.equal(parsed.status, "ready-for-review");
    ruleIds.add(parsed.learning.regression_candidate.expected.rule_id);
    threatIds.add(parsed.learning.threat.id);
  }
  assert.equal(ruleIds.size, 24);
  assert.equal(threatIds.size, 17);
});

test("canonical, closed-shape, digest, and byte ceilings reject near misses", () => {
  const {planned} = realFixtures();
  assert.throws(() => helpers.parseCanonicalIncident(JSON.stringify(planned.value, null, 2) + "\n", Buffer.byteLength(JSON.stringify(planned.value, null, 2) + "\n")));
  const duplicate = '{"schema":"kingdom.incident/v1","schema":"kingdom.incident/v1"}\n';
  assert.throws(() => helpers.parseCanonicalIncident(duplicate, Buffer.byteLength(duplicate, "ascii")), /canonical JSON/);

  const digestTamper = clone(planned.value);
  digestTamper.headline.summary = "Tampered summary.";
  const digestTamperText = canonicalIncident(digestTamper);
  assert.throws(() => helpers.parseCanonicalIncident(digestTamperText, digestTamperText.length), /incident_digest/);

  const rootExtra = clone(planned.value);
  rootExtra.unreviewed_extra = "no";
  rootExtra.incident_digest = helpers.digestWithout(rootExtra, "incident_digest");
  const rootExtraText = canonicalIncident(rootExtra);
  assert.throws(() => helpers.parseCanonicalIncident(rootExtraText, rootExtraText.length), /contain exactly/);

  const nestedExtra = clone(planned.value);
  nestedExtra.actions[0].operational_command = "none";
  nestedExtra.incident_digest = helpers.digestWithout(nestedExtra, "incident_digest");
  const nestedExtraText = canonicalIncident(nestedExtra);
  assert.throws(() => helpers.parseCanonicalIncident(nestedExtraText, nestedExtraText.length), /contain exactly/);

  const candidateTamper = clone(planned.value);
  candidateTamper.learning.regression_candidate.candidate_digest = "0".repeat(64);
  candidateTamper.incident_digest = helpers.digestWithout(candidateTamper, "incident_digest");
  const candidateTamperText = canonicalIncident(candidateTamper);
  assert.throws(() => helpers.parseCanonicalIncident(candidateTamperText, candidateTamperText.length), /candidate_digest/);

  assert.throws(() => helpers.parseCanonicalIncident("a".repeat(helpers.MAX_FILE_BYTES + 1), helpers.MAX_FILE_BYTES + 1), /1\.\.65536 bytes/);
});

test("planned import renders facts and proposals without creating download capability", async () => {
  const {planned} = realFixtures();
  const browser = browserHarness();
  assert.equal(browser.records.blobs.length, 0);
  assert.equal(browser.records.objectUrls.length, 0);
  assert.equal(browser.records.anchorClicks.length, 0);

  await browser.importText(planned.text);
  assert.equal(browser.records.fileReads, 1);
  assert.equal(browser.elements.dashboard.hidden, false);
  assert.equal(browser.elements.download.disabled, false);
  assert.equal(browser.elements.timeline.children.length, 5);
  assert.equal(browser.elements.facts.children.length, 4);
  assert.equal(browser.elements.inferences.children.length, 2);
  assert.equal(browser.elements.unknowns.children.length, 6);
  assert.equal(browser.elements.actions.children.length, 3);
  assert.ok(browser.elements.actions.children.every((item) => item.tagName === "ARTICLE"));
  assert.ok(!browser.records.createdTags.includes("button"), "incident content must not create operational controls");
  assert.match(browser.elements["summary-fields"].textContent, /ready-for-review/);
  assert.match(browser.elements.status.textContent, /Self-check passed locally/);
  assert.match(browser.elements.status.textContent, /origin is not authenticated/);
  assert.match(browser.elements.status.textContent, /No action was executed/);
  assert.equal(browser.elements["candidate-preview"].textContent, helpers.candidateText(planned.value.learning.regression_candidate));
  assert.equal(browser.records.blobs.length, 0);
  assert.equal(browser.records.objectUrls.length, 0);
  assert.equal(browser.records.anchorClicks.length, 0);
});

test("halted import is visibly quarantined and forged explanatory markup is rejected", async () => {
  const {halted} = realFixtures();
  const browser = browserHarness();
  await browser.importText(halted.text);

  assert.equal(browser.elements.dashboard.hidden, false);
  assert.equal(browser.elements.unknowns.children.length, 7);
  assert.equal(browser.elements.actions.children.length, 3);
  assert.match(browser.elements["summary-fields"].textContent, /halted-for-review/);
  assert.match(browser.elements["summary-fields"].textContent, /boundary-halt/);
  assert.match(browser.elements["summary-fields"].textContent, /quarantine/);
  assert.equal(browser.records.blobs.length, 0);
  assert.equal(browser.records.anchorClicks.length, 0);

  const injected = clone(halted.value);
  injected.epistemics.facts[0].statement = "<img src=x onerror=alert(1)> remains inert text.";
  injected.incident_digest = helpers.digestWithout(injected, "incident_digest");
  const text = canonicalIncident(injected);
  const rejected = browserHarness();
  await rejected.importText(text);
  assert.equal(rejected.elements.dashboard.hidden, true);
  assert.match(rejected.elements.status.textContent, /Rejected/);
  assert.equal(rejected.elements.facts.textContent, "");
  assert.ok(!rejected.records.createdTags.includes("img"));
  assert.ok(!rejected.records.createdTags.includes("script"));
  assert.equal(rejected.records.blobs.length, 0);
  assert.equal(rejected.records.anchorClicks.length, 0);
});

test("redigested forged bindings, policy guidance, invented threat, and ghost references reject", () => {
  const golden = JSON.parse(goldenIncidentText);
  const forged = clone(golden);
  Object.keys(forged.source.bindings).forEach((key) => {
    forged.source.bindings[key] = "0".repeat(64);
  });
  Object.keys(forged.learning.regression_candidate.source.bindings).forEach((key) => {
    forged.learning.regression_candidate.source.bindings[key] = "0".repeat(64);
  });
  Object.assign(forged.learning.regression_candidate.expected, {
    rule_id: "control-nominal",
    threat_id: "t99-invented",
    action: "allow",
    fallback: "deny",
    severity: 0,
    halt_code: "none",
    mirror: {mode: "none", max_attempts: 0, egress: false}
  });
  Object.assign(forged.headline, {
    title: "Invented browser guidance",
    severity: 0,
    planned_action: "allow",
    summary: "A forged allow explanation with no reviewed policy basis."
  });
  forged.learning.threat = {id: "t99-invented", title: "Invented threat", evidence_status: "observed"};
  forged.learning.guidance = {
    detection: "Invented detection.",
    containment: "Invented containment.",
    recovery: "Invented recovery.",
    privacy_output: "Invented privacy output."
  };
  forged.epistemics.facts[0].refs = ["source.ghost_digest"];
  forged.learning.regression_candidate.candidate_digest = helpers.digestWithout(
    forged.learning.regression_candidate,
    "candidate_digest"
  );
  forged.incident_digest = helpers.digestWithout(forged, "incident_digest");
  const forgedText = canonicalIncident(forged);
  assert.throws(
    () => helpers.parseCanonicalIncident(forgedText, forgedText.length),
    /pinned reviewed build/
  );

  const policyForgery = clone(golden);
  Object.assign(policyForgery.learning.regression_candidate.expected, {
    rule_id: "control-nominal",
    threat_id: "t99-invented",
    action: "allow",
    fallback: "deny",
    severity: 0,
    halt_code: "none",
    mirror: {mode: "none", max_attempts: 0, egress: false}
  });
  Object.assign(policyForgery.headline, {title: "Invented threat", severity: 0, planned_action: "allow"});
  policyForgery.learning.threat = {id: "t99-invented", title: "Invented threat", evidence_status: "observed"};
  policyForgery.learning.guidance.detection = "Invented detection.";
  policyForgery.learning.regression_candidate.candidate_digest = helpers.digestWithout(
    policyForgery.learning.regression_candidate,
    "candidate_digest"
  );
  policyForgery.incident_digest = helpers.digestWithout(policyForgery, "incident_digest");
  const policyText = canonicalIncident(policyForgery);
  assert.throws(
    () => helpers.parseCanonicalIncident(policyText, policyText.length),
    /pinned reviewed policy|pinned reviewed build/
  );

  const ghost = clone(golden);
  ghost.epistemics.facts[0].refs = ["source.ghost_digest"];
  ghost.incident_digest = helpers.digestWithout(ghost, "incident_digest");
  const ghostText = canonicalIncident(ghost);
  assert.throws(
    () => helpers.parseCanonicalIncident(ghostText, ghostText.length),
    /unresolved incident reference/
  );

  const guidance = clone(golden);
  guidance.learning.guidance.containment = "Invented containment guidance.";
  guidance.incident_digest = helpers.digestWithout(guidance, "incident_digest");
  const guidanceText = canonicalIncident(guidance);
  assert.throws(
    () => helpers.parseCanonicalIncident(guidanceText, guidanceText.length),
    /pinned reviewed build/
  );
});

test("oversize files are rejected before read and an explicit click performs one exact disposable download", async () => {
  const {planned} = realFixtures();
  const oversize = browserHarness();
  await oversize.importText("not read", helpers.MAX_FILE_BYTES + 1);
  assert.equal(oversize.records.fileReads, 0);
  assert.equal(oversize.elements.dashboard.hidden, true);
  assert.equal(oversize.elements.download.disabled, true);
  assert.match(oversize.elements.status.textContent, /Rejected/);
  assert.equal(oversize.records.blobs.length, 0);

  const browser = browserHarness();
  await browser.importText(planned.text);
  const exactCandidate = helpers.candidateText(planned.value.learning.regression_candidate);
  assert.deepEqual(browser.records.sequence, []);
  await browser.elements.download.dispatch("click");

  assert.equal(browser.records.blobs.length, 1);
  assert.deepEqual(browser.records.blobs[0].parts, [exactCandidate]);
  assert.equal(browser.records.blobs[0].type, "application/json;charset=utf-8");
  assert.equal(browser.records.objectUrls.length, 1);
  assert.equal(browser.records.anchorClicks.length, 1);
  assert.equal(browser.records.anchorClicks[0].download, "incident-lantern-regression-candidate.json");
  assert.equal(browser.records.anchorClicks[0].href, "blob:incident-lantern-1");
  assert.equal(browser.records.anchorRemovals, 1);
  assert.deepEqual(browser.records.revokedUrls, ["blob:incident-lantern-1"]);
  assert.deepEqual(browser.records.sequence, ["blob", "create", "click", "remove", "revoke"]);
  assert.equal(browser.body.children.length, 0);

  await browser.elements.clear.dispatch("click");
  assert.equal(browser.elements.dashboard.hidden, true);
  assert.equal(browser.elements.download.disabled, true);
  assert.equal(browser.elements["candidate-preview"].textContent, "");
  assert.equal(browser.elements["incident-file"].value, "");
});
