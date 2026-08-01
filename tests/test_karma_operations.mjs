import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), "utf8");
const contractText = read("site/operations/mirror-garden/contract.json");
const statusText = read("site/operations/mirror-garden/status.json");
const contractSchema = JSON.parse(read("site/operations/mirror-garden/contract.schema.json"));
const statusSchema = JSON.parse(read("site/operations/mirror-garden/status.schema.json"));
const page = read("site/operations/mirror-garden/index.html");
const contract = JSON.parse(contractText);
const status = JSON.parse(statusText);

function allKeys(value, result = []) {
  if (Array.isArray(value)) {
    value.forEach((child) => allKeys(child, result));
  } else if (value && typeof value === "object") {
    for (const [key, child] of Object.entries(value)) {
      result.push(key);
      allKeys(child, result);
    }
  }
  return result;
}

function resolveRef(ref, root) {
  assert.match(ref, /^#\//, `unsupported schema reference: ${ref}`);
  return ref.slice(2).split("/").reduce(
    (value, part) => value[part.replaceAll("~1", "/").replaceAll("~0", "~")],
    root,
  );
}

function validate(value, schema, root = schema, path = "$") {
  if (schema.$ref) return validate(value, resolveRef(schema.$ref, root), root, path);
  if ("const" in schema) assert.deepEqual(value, schema.const, `${path}: const drift`);
  if (schema.enum) assert(schema.enum.includes(value), `${path}: outside closed enum`);
  if (schema.type === "object") {
    assert(value && typeof value === "object" && !Array.isArray(value), `${path}: expected object`);
    for (const key of schema.required ?? []) assert(key in value, `${path}: missing ${key}`);
    if (schema.additionalProperties === false) {
      for (const key of Object.keys(value)) assert(key in schema.properties, `${path}: unexpected ${key}`);
    }
    for (const [key, child] of Object.entries(value)) {
      if (schema.properties?.[key]) validate(child, schema.properties[key], root, `${path}.${key}`);
    }
  } else if (schema.type === "array") {
    assert(Array.isArray(value), `${path}: expected array`);
    if (schema.minItems !== undefined) assert(value.length >= schema.minItems, `${path}: too short`);
    if (schema.maxItems !== undefined) assert(value.length <= schema.maxItems, `${path}: too long`);
    value.forEach((child, index) => validate(child, schema.items, root, `${path}[${index}]`));
  } else if (schema.type === "string") {
    assert.equal(typeof value, "string", `${path}: expected string`);
    if (schema.minLength !== undefined) assert(value.length >= schema.minLength, `${path}: too short`);
    if (schema.maxLength !== undefined) assert(value.length <= schema.maxLength, `${path}: too long`);
    if (schema.pattern) assert(new RegExp(schema.pattern).test(value), `${path}: pattern drift`);
    if (schema.format === "date") assert(/^\d{4}-\d{2}-\d{2}$/.test(value), `${path}: invalid date`);
  }
}

test("public posture is explicitly advisory and non-actuating", () => {
  assert.equal(contract.schema, "kingdom.karma.operations-contract/v1");
  assert.equal(contract.posture.live_classifier, "disabled");
  assert.equal(contract.posture.live_incident_ingestion, "disabled");
  assert.equal(contract.posture.live_telemetry, "disabled");
  assert.equal(contract.posture.automatic_actuation, "disabled");
  assert.equal(contract.posture.synthetic_mirror, "offline-only");
  assert.equal(contract.posture.provider_logging, "unknown");
  assert.equal(contract.posture.private_evidence_default, "derived-categories-only");
  assert.equal(contract.private_evidence.raw_request_retention, "forbidden-by-this-contract");
  assert.equal(contract.artifact_binding.provider_parity, "must-be-verified-per-release");
  assert.equal(status.contract_version, contract.version);
  assert.equal(status.offline_rehearsal, "source-tests-available-not-live-gate");
  assert.match(status.coverage_statement, /not evidence/i);
});

test("contract is closed, coarse, and privacy-minimized", () => {
  validate(contract, contractSchema);
  validate(status, statusSchema);
  assert.equal(contractSchema.additionalProperties, false);
  assert.equal(contractSchema.properties.posture.additionalProperties, false);
  assert.deepEqual(new Set(contractSchema.required), new Set(Object.keys(contract)));
  assert.deepEqual(
    new Set(contractSchema.properties.posture.required),
    new Set(Object.keys(contract.posture)),
  );
  assert.equal(statusSchema.additionalProperties, false);
  assert.deepEqual(new Set(statusSchema.required), new Set(Object.keys(status)));
  assert.deepEqual(
    contract.public_categories.map(({ id }) => id),
    [
      "availability-pressure",
      "protocol-invalid",
      "authority-confusion",
      "provenance-drift",
      "privacy-risk",
      "content-boundary",
      "novel-or-ambiguous",
    ],
  );
  assert.deepEqual(
    contract.response_clock.map(({ window }) => window),
    ["first-5-minutes", "first-15-minutes", "first-60-minutes"],
  );
  assert.equal(contract.coverage.length, 4);
  assert(contract.coverage.every(({ incident_observation }) =>
    ["disabled", "not-available"].includes(incident_observation)));
  const keys = new Set(allKeys(contract));
  for (const forbidden of [
    "raw_payload", "raw_request", "ip_address", "actor_id", "identity",
    "exact_timestamp", "threshold", "attacker_text", "webhook", "endpoint",
  ]) assert(!keys.has(forbidden), `forbidden public field: ${forbidden}`);
  for (const marker of [
    "BEGIN PRIVATE", "Authorization:", "Bearer ", "api_key", "secret_key",
  ]) assert(!contractText.includes(marker), `secret-shaped marker: ${marker}`);

  for (const [mutated, schema] of [
    [{ ...structuredClone(contract), posture: { ...contract.posture, surprise: "observe" } }, contractSchema],
    [{ ...structuredClone(contract), coverage: [{ ...contract.coverage[0], provider_metadata: "known" }, ...contract.coverage.slice(1)] }, contractSchema],
    [{ ...structuredClone(status), live_classifier: "enabled" }, statusSchema],
  ]) assert.throws(() => validate(mutated, schema));
});

test("operations room cannot collect, connect, execute, or embed remote content", () => {
  assert.match(page, /connect-src 'none'/);
  assert.match(page, /Live classifier disabled/);
  assert.match(page, /No incident statement is published/);
  assert.match(page, /does not mean “no incident occurred.”/);
  assert.match(page, /Raw request retention is forbidden by this contract/);
  assert.doesNotMatch(page, /<(script|form|iframe|object|embed)\b/i);
  assert.doesNotMatch(page, /\b(fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon|localStorage|sessionStorage|indexedDB)\s*[.(]/i);
  assert.doesNotMatch(page, /(?:src|href)=["'](?:https?:)?\/\//i);
  assert.doesNotMatch(page, /\/api\//i);
});

test("the room is discoverable and packaged by both workflows", () => {
  const home = read("site/index.html");
  const operations = read("site/operations/index.html");
  const registry = JSON.parse(read("site/operations/registry.json"));
  const keeper = read(".github/workflows/keeper-verifies.yml");
  const pages = read(".github/workflows/deploy-public-door.yml");
  assert.match(home, /href="operations\/mirror-garden\/"/);
  assert.match(operations, /href="mirror-garden\/"/);
  const registered = registry.operations.find(({ id }) => id === "mirror-garden-karma");
  assert(registered, "Mirror Garden must be in the public operations registry");
  assert.equal(registered.site, "site/operations/mirror-garden/index.html");
  assert.equal(registered.verify, "python3 kingdom/operations/mirror-garden-karma/verify.py");
  assert.match(keeper, /node --test tests\/test_karma_operations\.mjs/);
  assert.match(pages, /test_karma_operations\.mjs/);
  assert.match(pages, /_site\/operations\/mirror-garden\/contract\.json/);
  assert.match(pages, /_site\/operations\/mirror-garden\/status\.json/);
  assert.match(pages, /_site\/operations\/mirror-garden\/manifest\.json/);
  assert.match(pages, /_site\/operations\/mirror-garden\/contract\.schema\.json/);
  assert.match(pages, /_site\/operations\/mirror-garden\/status\.schema\.json/);
});
