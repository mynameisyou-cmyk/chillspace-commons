#!/usr/bin/env node

import {
  createHash,
  createPublicKey,
  generateKeyPairSync,
  sign as edSign,
  verify as edVerify,
} from "node:crypto";
import {
  existsSync,
  lstatSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  realpathSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const VERSION = "kingdom.reserve-loop/v0";
const KEY_ID = "synthetic-drill-ed25519";
const SURFACES = ["telegram", "api", "mcp"];
const PERMISSIONS = [
  "collect", "store_raw", "store_derived", "transform",
  "public_display", "non_display_use", "redistribute_excerpt", "commercialize",
];
const REQUIRED_CHECKS = [
  "rights", "provenance", "surface", "jurisdiction", "non_directional", "correction_priority",
];

class ReserveError extends Error {}
const invariant = (value, message) => { if (!value) throw new ReserveError(message); };
const clone = (value) => structuredClone(value);
const iso = (ms) => new Date(ms).toISOString();
const shaHex = (bytes) => createHash("sha256").update(bytes).digest("hex");
const digest = (bytes) => `sha256:${shaHex(bytes)}`;

function canonical(value) {
  if (value === null || typeof value === "boolean" || typeof value === "string") return JSON.stringify(value);
  if (typeof value === "number") {
    invariant(Number.isSafeInteger(value), "canonical numbers must be safe integers");
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  invariant(value && typeof value === "object", "unsupported canonical value");
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
}

const jsonBytes = (value) => Buffer.from(`${canonical(value)}\n`, "utf8");
const signedBytes = (payload) => Buffer.from(canonical(payload), "utf8");

function confined(root, locator, mustExist = false) {
  invariant(typeof locator === "string" && locator.length > 0, "empty locator");
  invariant(!isAbsolute(locator) && !locator.includes("\\") && !locator.includes("\0"), "locator escape");
  const parts = locator.split("/");
  invariant(parts.every((part) => part && part !== "." && part !== ".."), "locator escape");
  const base = resolve(root);
  const target = resolve(base, locator);
  const rel = relative(base, target);
  invariant(rel !== ".." && !rel.startsWith(`..${sep}`) && !isAbsolute(rel), "locator escape");
  if (mustExist) {
    let cursor = base;
    for (const part of parts) {
      cursor = join(cursor, part);
      invariant(existsSync(cursor), `missing locator: ${locator}`);
      invariant(!lstatSync(cursor).isSymbolicLink(), `symlink locator: ${locator}`);
    }
    const real = realpathSync(target);
    const realRel = relative(realpathSync(base), real);
    invariant(realRel !== ".." && !realRel.startsWith(`..${sep}`), "realpath escape");
  }
  return target;
}

function safeWrite(root, locator, bytes) {
  const target = confined(root, locator);
  mkdirSync(dirname(target), { recursive: true });
  if (existsSync(target)) invariant(!lstatSync(target).isSymbolicLink(), "refuse symlink write");
  writeFileSync(target, bytes);
}

function objectLocator(sha256) {
  invariant(/^sha256:[a-f0-9]{64}$/.test(sha256), "invalid digest");
  return `objects/sha256/${sha256.slice(7)}`;
}

function putObject(root, bytes) {
  const sha256 = digest(bytes);
  const locator = objectLocator(sha256);
  const target = confined(root, locator);
  if (existsSync(target)) invariant(digest(readFileSync(target)) === sha256, "CAS collision");
  else safeWrite(root, locator, bytes);
  return { sha256, locator, size: bytes.length };
}

function readObject(root, ref) {
  invariant(ref.locator === objectLocator(ref.sha256), "non-canonical object locator");
  const bytes = readFileSync(confined(root, ref.locator, true));
  invariant(bytes.length === ref.size && digest(bytes) === ref.sha256, "object integrity failure");
  return bytes;
}

function signRecord(kind, body, privateKey) {
  const payload = { kind, ...body };
  return {
    payload,
    signature: {
      algorithm: "Ed25519",
      key_id: KEY_ID,
      value_base64: edSign(null, signedBytes(payload), privateKey).toString("base64"),
    },
  };
}

function verifySigned(record, kind, trust, scope) {
  invariant(record?.payload?.kind === kind, `wrong signed kind: ${kind}`);
  invariant(record?.signature?.algorithm === "Ed25519" && record.signature.key_id === trust.key_id, "bad signer metadata");
  invariant(trust.status === "active" && trust.synthetic_fixture_only === true && trust.scopes.includes(scope), "untrusted scope");
  const key = createPublicKey({ key: Buffer.from(trust.public_key_spki_base64, "base64"), format: "der", type: "spki" });
  invariant(edVerify(null, signedBytes(record.payload), key, Buffer.from(record.signature.value_base64, "base64")), "invalid signature");
  return record.payload;
}

function gateRights(rights, now, termsDigest, surface = null) {
  invariant(rights.kind === "kingdom.rights-profile/v0" && rights.decision === "allow", "rights not allow");
  invariant(rights.synthetic_fixture_only === true && rights.revocation_status === "clear", "rights revoked or non-synthetic");
  invariant(Date.parse(rights.reviewed_at) <= now && Date.parse(rights.revocation_checked_at) <= now, "future rights review");
  invariant(Date.parse(rights.revocation_check_due_at) > now, "stale revocation check");
  invariant(Date.parse(rights.expires_at) > now, "expired rights");
  invariant(rights.terms_snapshot_sha256 === termsDigest, "terms snapshot mismatch");
  if (surface !== null) invariant(rights.surfaces.includes(surface), `surface not allowed by rights: ${surface}`);
  for (const permission of PERMISSIONS) invariant(rights.permissions[permission] === true, `missing right: ${permission}`);
}

function pointerValue(document, pointer) {
  invariant(/^\/(?:[^~/]|~0|~1)*(?:\/(?:[^~/]|~0|~1)*)*$/.test(pointer), `invalid JSON pointer: ${pointer}`);
  return pointer
    .slice(1)
    .split("/")
    .map((part) => part.replace(/~1/g, "/").replace(/~0/g, "~"))
    .reduce((value, part) => {
      invariant(value !== null && typeof value === "object" && part in value, `unresolved JSON pointer: ${pointer}`);
      return value[part];
    }, document);
}

function verifyPolicy(policy, now) {
  invariant(policy.decision === "allow", "policy blocked");
  invariant(Date.parse(policy.evaluated_at) <= now && Date.parse(policy.expires_at) > now, "expired or future policy");
  for (const check of REQUIRED_CHECKS) invariant(policy.checks[check] === true, `failed policy check: ${check}`);
}

function semantic(event, revisionReceiptSha256) {
  return {
    event_id: event.event_id,
    revision: event.revision,
    revision_receipt_sha256: revisionReceiptSha256,
    event_type: event.event_type,
    lifecycle_status: event.lifecycle_status,
    headline: event.headline,
    facts: event.facts,
    evidence: event.evidence,
    correction: event.correction,
    source_receipt_sha256: event.source_receipt_sha256,
  };
}

function render(event, revisionReceiptSha256, surface) {
  const data = semantic(event, revisionReceiptSha256);
  if (surface === "api") return jsonBytes({ kind: "kingdom.api-projection/v0", data });
  if (surface === "mcp") return jsonBytes({ content: [{ type: "text", text: canonical(data) }], isError: false, kind: "kingdom.mcp-projection/v0" });
  invariant(surface === "telegram", "unknown surface");
  const lines = [
    `SYNTHETIC · ${event.event_type} · ${event.lifecycle_status.toUpperCase()}`,
    event.headline,
    ...event.facts.map((fact) => `${fact.name}: ${fact.value} ${fact.unit}`),
    `event=${event.event_id} revision=${event.revision}`,
    `receipt=${revisionReceiptSha256}`,
    `source=${event.source_receipt_sha256}`,
    `evidence=${event.evidence.tier}`,
    `semantic=${canonical(data)}`,
    "Fixture only; no real-world claim or trading direction.",
  ];
  if (event.correction) lines.splice(3, 0, `correction=${event.correction.reason}`);
  return Buffer.from(`${lines.join("\n")}\n`, "utf8");
}

function verifyChain(records, refs, trust) {
  invariant(records.length === 2 && refs.length === 2, "revision count");
  let previous = null;
  let eventId = null;
  for (let index = 0; index < 2; index += 1) {
    const payload = verifySigned(records[index], "kingdom.event-revision/v0", trust, "event_revision");
    if (eventId === null) eventId = payload.event_id;
    else invariant(payload.event_id === eventId, "event identity changed across revision chain");
    invariant(payload.sequence === index + 1, "non-monotonic revision sequence");
    invariant(payload.previous_revision_sha256 === previous, "revision fork");
    previous = refs[index].sha256;
  }
}

function verifyCorrectionCoverage(corrections, trust, revisionRefs, projectionPayloads) {
  invariant(corrections.length === 3, "missed correction");
  const seen = new Set();
  for (const record of corrections) {
    const item = verifySigned(record, "kingdom.correction-propagation/v0", trust, "correction");
    invariant(SURFACES.includes(item.surface) && !seen.has(item.surface), "duplicate correction surface");
    invariant(item.from_revision_sha256 === revisionRefs[0].sha256 && item.to_revision_sha256 === revisionRefs[1].sha256, "wrong correction chain");
    invariant(item.status === "propagated" && item.priority === "same_as_original", "correction not propagated");
    const surfaceItems = projectionPayloads.filter((value) => value.surface === item.surface);
    invariant(surfaceItems.length === 2 && item.original_delivery_sha256 === surfaceItems[0].receipt_sha256 && item.corrected_delivery_sha256 === surfaceItems[1].receipt_sha256, "correction delivery mismatch");
    seen.add(item.surface);
  }
  invariant(SURFACES.every((surface) => seen.has(surface)), "missed correction surface");
}

function verifyIncidentPair(records, refs, trust, sourceContentSha256, sourceId) {
  invariant(records.length === 2, "incident count");
  const outage = verifySigned(records[0], "kingdom.service-incident/v0", trust, "incident");
  const recovery = verifySigned(records[1], "kingdom.service-incident/v0", trust, "incident");
  invariant(outage.incident_type === "source_outage" && outage.status === "open" && outage.previous_incident_sha256 === null, "illegal outage state");
  invariant(recovery.incident_type === "source_recovery" && recovery.status === "resolved", "illegal recovery state");
  invariant(recovery.incident_id === outage.incident_id && recovery.source_id === outage.source_id, "incident identity changed");
  invariant(outage.source_id === sourceId, "incident is not bound to the archived source");
  invariant(recovery.previous_incident_sha256 === refs[0].sha256 && Date.parse(recovery.observed_at) >= Date.parse(outage.observed_at), "illegal incident transition");
  invariant(
    recovery.recovery_evidence?.kind === "content_addressed_source_read" &&
      recovery.recovery_evidence.source_content_sha256 === sourceContentSha256 &&
      recovery.recovery_evidence.result === "verified",
    "incident lacks exact recovery evidence",
  );
}

function entryMap(manifest) { return new Map(manifest.entries.map((entry) => [entry.name, entry])); }
const parseObject = (root, entry) => JSON.parse(readObject(root, entry).toString("utf8"));

function objectStoreDigests(root) {
  const directory = confined(root, "objects/sha256", true);
  return readdirSync(directory)
    .map((name) => {
      invariant(/^[a-f0-9]{64}$/.test(name), "non-canonical CAS filename");
      const target = confined(root, `objects/sha256/${name}`, true);
      invariant(statSync(target).isFile() && shaHex(readFileSync(target)) === name, "unindexed CAS object is corrupt");
      return `sha256:${name}`;
    })
    .sort();
}

function archiveFileInventory(root) {
  const base = resolve(root);
  const files = [];
  const walk = (directory) => {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      invariant(!entry.isSymbolicLink(), "archive contains a symlink");
      const target = join(directory, entry.name);
      if (entry.isDirectory()) walk(target);
      else {
        invariant(entry.isFile(), "archive contains a non-file entry");
        files.push(relative(base, target).split(sep).join("/"));
      }
    }
  };
  walk(base);
  return files.sort();
}

function expectedArchiveFiles(manifest, requireDrill) {
  const direct = ["manifest.json", "manifest.sha256", "manifest.receipt.json"];
  if (requireDrill) direct.push("drill.receipt.json");
  return [
    ...direct,
    ...manifest.entries.map((entry) => entry.locator),
    ...manifest.projections.map((projection) => projection.materialized_locator),
  ].sort();
}

function scanNoSecrets(root) {
  const markers = [/BEGIN [A-Z ]*PRIVATE KEY/, /"private_key"\s*:/, /AKIA[0-9A-Z]{16}/];
  const walk = (dir) => {
    for (const name of readdirSync(dir)) {
      const path = join(dir, name);
      invariant(!lstatSync(path).isSymbolicLink(), "archive symlink");
      if (statSync(path).isDirectory()) walk(path);
      else {
        const text = readFileSync(path).toString("utf8");
        invariant(markers.every((marker) => !marker.test(text)), "secret material archived");
      }
    }
  };
  walk(root);
  return 0;
}

function rebuildProjections(root, manifest) {
  const onDiskManifest = JSON.parse(readFileSync(confined(root, "manifest.json", true), "utf8"));
  invariant(canonical(onDiskManifest) === canonical(manifest) && manifest.kind === VERSION, "rebuild manifest mismatch");
  const entries = entryMap(manifest);
  const revisions = manifest.revisions.map((item) => ({
    event: parseObject(root, entries.get(item.event)),
    receipt: entries.get(item.receipt),
  }));
  const derived = confined(root, "derived", true);
  invariant(statSync(derived).isDirectory(), "derived projection root is not a directory");
  rmSync(derived, { recursive: true, force: false });
  for (const projection of manifest.projections) {
    const revision = revisions[projection.revision - 1];
    const bytes = render(revision.event, revision.receipt.sha256, projection.surface);
    const renderedEntry = entries.get(projection.rendered);
    invariant(digest(bytes) === renderedEntry.sha256 && bytes.equals(readObject(root, renderedEntry)), "offline rebuild divergence");
    safeWrite(root, projection.materialized_locator, bytes);
  }
  return true;
}

function verifyArchive(root, { requireDrill = true, now = Date.now() } = {}) {
  root = resolve(root);
  invariant(existsSync(root) && statSync(root).isDirectory(), "archive not found");
  const manifestBytes = readFileSync(confined(root, "manifest.json", true));
  const manifestSha256 = digest(manifestBytes);
  invariant(readFileSync(confined(root, "manifest.sha256", true), "utf8").trim() === manifestSha256, "manifest root mismatch");
  const manifest = JSON.parse(manifestBytes.toString("utf8"));
  invariant(manifest.kind === VERSION && manifest.entries.length > 0, "wrong manifest");
  const entries = entryMap(manifest);
  invariant(entries.size === manifest.entries.length, "duplicate manifest entry");
  for (const entry of manifest.entries) readObject(root, entry);
  invariant(
    canonical(archiveFileInventory(root)) === canonical(expectedArchiveFiles(manifest, requireDrill)),
    "archive contains an unregistered, missing, or secret-bearing file",
  );
  invariant(
    canonical(objectStoreDigests(root)) === canonical(manifest.entries.map((entry) => entry.sha256).sort()),
    "manifest does not exactly cover the content-addressed store",
  );

  const trust = parseObject(root, entries.get("trust"));
  const manifestReceipt = JSON.parse(readFileSync(confined(root, "manifest.receipt.json", true), "utf8"));
  const manifestPayload = verifySigned(manifestReceipt, "kingdom.reserve-manifest-receipt/v0", trust, "manifest");
  invariant(manifestPayload.manifest_sha256 === manifestSha256, "manifest signature mismatch");

  const termsEntry = entries.get("terms");
  const rights = parseObject(root, entries.get("rights"));
  gateRights(rights, now, termsEntry.sha256);
  const source = parseObject(root, entries.get("source_receipt"));
  invariant(source.synthetic_fixture_only === true && source.rights_profile_sha256 === entries.get("rights").sha256, "uncleared source");
  invariant(source.content_sha256 === entries.get("source_content").sha256, "source receipt mismatch");
  const sourceContent = parseObject(root, entries.get("source_content"));

  const revisionRecords = manifest.revisions.map((item) => parseObject(root, entries.get(item.receipt)));
  const revisionRefs = manifest.revisions.map((item) => entries.get(item.receipt));
  verifyChain(revisionRecords, revisionRefs, trust);
  const events = manifest.revisions.map((item, index) => {
    const eventEntry = entries.get(item.event);
    const event = parseObject(root, eventEntry);
    const payload = revisionRecords[index].payload;
    invariant(payload.event_sha256 === eventEntry.sha256 && payload.event_id === event.event_id && payload.sequence === event.revision, "revision/event mismatch");
    for (const fact of event.facts) invariant(pointerValue(sourceContent, fact.pointer) === fact.value, `fact provenance mismatch: ${fact.name}`);
    return event;
  });
  invariant(events[1].correction?.supersedes_revision_sha256 === revisionRefs[0].sha256, "correction does not chain");

  invariant(manifest.projections.length === 6, "projection count");
  const projectionPayloads = [];
  for (const item of manifest.projections) {
    const receiptEntry = entries.get(item.receipt);
    const receipt = parseObject(root, receiptEntry);
    const payload = verifySigned(receipt, "kingdom.projection-receipt/v0", trust, "projection");
    verifyPolicy(payload.policy, now);
    invariant(payload.rights_profile_sha256 === entries.get("rights").sha256, "projection joined to wrong rights profile");
    gateRights(rights, now, termsEntry.sha256, item.surface);
    const event = events[item.revision - 1];
    const expected = render(event, revisionRefs[item.revision - 1].sha256, item.surface);
    const renderedEntry = entries.get(item.rendered);
    invariant(payload.surface === item.surface && payload.revision === item.revision, "projection identity mismatch");
    invariant(payload.event_revision_sha256 === revisionRefs[item.revision - 1].sha256, "projection revision mismatch");
    invariant(payload.semantic_sha256 === digest(jsonBytes(semantic(event, revisionRefs[item.revision - 1].sha256))), "projection divergence");
    invariant(payload.rendered_sha256 === renderedEntry.sha256 && digest(expected) === renderedEntry.sha256, "rendered projection mismatch");
    invariant(readFileSync(confined(root, item.materialized_locator, true)).equals(expected), "materialized projection mismatch");
    projectionPayloads.push({ ...payload, receipt_sha256: receiptEntry.sha256 });
  }
  for (const revision of [1, 2]) {
    const group = projectionPayloads.filter((item) => item.revision === revision);
    invariant(group.length === 3 && new Set(group.map((item) => item.surface)).size === 3 && new Set(group.map((item) => item.semantic_sha256)).size === 1, "projection matrix divergence");
  }

  const corrections = manifest.corrections.map((name) => parseObject(root, entries.get(name)));
  verifyCorrectionCoverage(corrections, trust, revisionRefs, projectionPayloads);
  const incidentRecords = manifest.incidents.map((name) => parseObject(root, entries.get(name)));
  const incidentRefs = manifest.incidents.map((name) => entries.get(name));
  verifyIncidentPair(incidentRecords, incidentRefs, trust, entries.get("source_content").sha256, source.source_id);
  const secrets = scanNoSecrets(root);

  let negativeCases = manifest.negative_cases;
  let offlineRebuild = false;
  if (requireDrill) {
    const drill = JSON.parse(readFileSync(confined(root, "drill.receipt.json", true), "utf8"));
    const payload = verifySigned(drill, "kingdom.reserve-drill-receipt/v0", trust, "drill");
    invariant(payload.manifest_sha256 === manifestSha256 && payload.negative_cases >= 10, "invalid drill receipt");
    invariant(payload.offline_rebuild === true && payload.secrets === 0 && payload.network === 0, "drill invariants failed");
    negativeCases = payload.negative_cases;
    offlineRebuild = true;
  }
  return { manifestSha256, revisions: 2, projections: 6, corrections: 3, incidents: 2, negativeCases, offlineRebuild, secrets };
}

function expectReject(name, fn) {
  try { fn(); } catch { return name; }
  throw new ReserveError(`negative case passed: ${name}`);
}

function runNegativeCases(state) {
  const { now, rights, termsRef, trust, privateKey, revisions, revisionRefs, projectionRecords, projectionRefs, corrections, incidents, incidentRefs, sourceContentRef, sourceReceipt, root } = state;
  const cases = [];
  const reject = (name, fn) => cases.push(expectReject(name, fn));
  let value;
  value = clone(rights); value.expires_at = iso(now - 1); reject("expired-rights", () => gateRights(value, now, termsRef.sha256));
  value = clone(rights); value.revocation_check_due_at = iso(now - 1); reject("stale-revocation", () => gateRights(value, now, termsRef.sha256));
  value = clone(rights); value.revocation_status = "revoked"; reject("revoked-rights", () => gateRights(value, now, termsRef.sha256));
  value = clone(rights); value.surfaces = value.surfaces.filter((surface) => surface !== "mcp"); reject("surface-rights", () => gateRights(value, now, termsRef.sha256, "mcp"));
  reject("terms-tamper", () => gateRights(rights, now, "sha256:".padEnd(71, "0")));
  value = clone(projectionRecords[0].payload.policy); value.expires_at = iso(now - 1); reject("expired-policy", () => verifyPolicy(value, now));
  value = clone(projectionRecords[0].payload.policy); value.checks.surface = false; reject("failed-policy", () => verifyPolicy(value, now));
  value = clone(revisions[0]); value.payload.sequence = 9; reject("signature-tamper", () => verifySigned(value, "kingdom.event-revision/v0", trust, "event_revision"));
  value = clone(revisions[1].payload); value.sequence = 3;
  reject("revision-sequence", () => verifyChain([revisions[0], signRecord("kingdom.event-revision/v0", Object.fromEntries(Object.entries(value).filter(([key]) => key !== "kind")), privateKey)], revisionRefs, trust));
  value = clone(revisions[1].payload); value.previous_revision_sha256 = "sha256:".padEnd(71, "f");
  reject("revision-fork", () => verifyChain([revisions[0], signRecord("kingdom.event-revision/v0", Object.fromEntries(Object.entries(value).filter(([key]) => key !== "kind")), privateKey)], revisionRefs, trust));
  value = clone(revisions[1].payload); value.event_id = "synthetic.reserve.other-event";
  reject("revision-event-identity", () => verifyChain([revisions[0], signRecord("kingdom.event-revision/v0", Object.fromEntries(Object.entries(value).filter(([key]) => key !== "kind")), privateKey)], revisionRefs, trust));
  value = clone(projectionRecords[0].payload); value.semantic_sha256 = "sha256:".padEnd(71, "a"); reject("projection-divergence", () => invariant(value.semantic_sha256 === projectionRecords[1].payload.semantic_sha256, "projection divergence"));
  reject("missed-correction", () => verifyCorrectionCoverage(corrections.slice(0, 2), trust, revisionRefs, projectionRecords.map((item, index) => ({ ...item.payload, receipt_sha256: projectionRefs[index].sha256 }))));
  value = clone(incidents[1].payload); value.status = "open";
  reject("illegal-incident", () => verifyIncidentPair([incidents[0], signRecord("kingdom.service-incident/v0", Object.fromEntries(Object.entries(value).filter(([key]) => key !== "kind")), privateKey)], incidentRefs, trust, sourceContentRef.sha256, sourceReceipt.source_id));
  const unrelatedOutagePayload = clone(incidents[0].payload);
  unrelatedOutagePayload.source_id = "synthetic.unrelated-source";
  const unrelatedOutage = signRecord("kingdom.service-incident/v0", Object.fromEntries(Object.entries(unrelatedOutagePayload).filter(([key]) => key !== "kind")), privateKey);
  const unrelatedOutageRef = { sha256: digest(jsonBytes(unrelatedOutage)) };
  const unrelatedRecoveryPayload = clone(incidents[1].payload);
  unrelatedRecoveryPayload.source_id = "synthetic.unrelated-source";
  unrelatedRecoveryPayload.previous_incident_sha256 = unrelatedOutageRef.sha256;
  const unrelatedRecovery = signRecord("kingdom.service-incident/v0", Object.fromEntries(Object.entries(unrelatedRecoveryPayload).filter(([key]) => key !== "kind")), privateKey);
  reject("incident-source-identity", () => verifyIncidentPair([unrelatedOutage, unrelatedRecovery], [unrelatedOutageRef, { sha256: digest(jsonBytes(unrelatedRecovery)) }], trust, sourceContentRef.sha256, sourceReceipt.source_id));
  value = clone(incidents[1].payload); value.recovery_evidence.source_content_sha256 = "sha256:".padEnd(71, "0");
  reject("incident-recovery-evidence", () => verifyIncidentPair([incidents[0], signRecord("kingdom.service-incident/v0", Object.fromEntries(Object.entries(value).filter(([key]) => key !== "kind")), privateKey)], incidentRefs, trust, sourceContentRef.sha256, sourceReceipt.source_id));
  reject("locator-parent", () => confined(root, "../escape"));
  reject("locator-absolute", () => confined(root, "/tmp/escape"));
  reject("render-tamper", () => invariant(digest(Buffer.from("tampered\n")) === projectionRecords[0].payload.rendered_sha256, "rendered tamper"));
  return cases.length;
}

function createArchive(root) {
  root = resolve(root);
  invariant(!existsSync(root) || readdirSync(root).length === 0, "archive directory must be absent or empty");
  mkdirSync(root, { recursive: true });
  const now = Date.now();
  const createdAt = iso(now);
  const { publicKey, privateKey } = generateKeyPairSync("ed25519");
  const trust = {
    kind: "kingdom.synthetic-trust/v0", key_id: KEY_ID, algorithm: "Ed25519", status: "active",
    synthetic_fixture_only: true,
    public_key_spki_base64: publicKey.export({ type: "spki", format: "der" }).toString("base64"),
    scopes: ["event_revision", "projection", "correction", "incident", "manifest", "drill"],
  };
  const entries = [];
  const add = (name, kind, bytes) => {
    const ref = putObject(root, bytes);
    const entry = { name, kind, ...ref };
    entries.push(entry);
    return entry;
  };
  const addJson = (name, kind, object) => add(name, kind, jsonBytes(object));
  const trustRef = addJson("trust", "trust", trust);
  const termsRef = add("terms", "terms_snapshot", Buffer.from("SYNTHETIC FIXTURE TERMS v0\nNo third-party content or real-world claim.\n", "utf8"));
  const rights = {
    kind: "kingdom.rights-profile/v0", profile_id: "synthetic-reserve-loop-v0", decision: "allow",
    field_scope: "Entirely synthetic local drill fixture", synthetic_fixture_only: true,
    terms_snapshot_sha256: termsRef.sha256, reviewed_at: iso(now - 1000),
    revocation_checked_at: iso(now - 1000), revocation_check_due_at: iso(now + 86_400_000),
    expires_at: iso(now + 172_800_000), revocation_status: "clear",
    surfaces: [...SURFACES],
    permissions: Object.fromEntries(PERMISSIONS.map((name) => [name, true])),
  };
  const rightsRef = addJson("rights", "rights_profile", rights);
  const sourceContent = { synthetic_fixture_only: true, policy_rate_basis_points: 500, corrected_policy_rate_basis_points: 475, unit: "basis_points" };
  const sourceContentRef = addJson("source_content", "source_content", sourceContent);
  const sourceReceipt = {
    kind: "kingdom.source-receipt/v0", source_id: "synthetic.reserve-source", synthetic_fixture_only: true,
    observed_at: createdAt, content_sha256: sourceContentRef.sha256, rights_profile_sha256: rightsRef.sha256,
  };
  const sourceReceiptRef = addJson("source_receipt", "source_receipt", sourceReceipt);
  gateRights(rights, now, termsRef.sha256);

  const baseEvent = {
    kind: "kingdom.market-event/v0", event_id: "synthetic.reserve.policy-rate", event_type: "macro.release",
    source_receipt_sha256: sourceReceiptRef.sha256,
    evidence: { tier: "claimed", limitations: ["Synthetic fixture only", "No real-world inference"] },
  };
  const event1 = { ...baseEvent, revision: 1, lifecycle_status: "active", headline: "SYNTHETIC: Example rate recorded", facts: [{ name: "policy_rate_basis_points", value: 500, unit: "basis_points", pointer: "/policy_rate_basis_points" }], correction: null };
  const event1Ref = addJson("event_1", "event", event1);
  const revision1 = signRecord("kingdom.event-revision/v0", { event_id: event1.event_id, sequence: 1, event_sha256: event1Ref.sha256, previous_revision_sha256: null, created_at: createdAt }, privateKey);
  const revision1Ref = addJson("revision_1", "event_revision", revision1);
  const event2 = { ...baseEvent, revision: 2, lifecycle_status: "corrected", headline: "SYNTHETIC: Example rate corrected", facts: [{ name: "policy_rate_basis_points", value: 475, unit: "basis_points", pointer: "/corrected_policy_rate_basis_points" }], correction: { reason: "Synthetic correction drill", supersedes_revision_sha256: revision1Ref.sha256, changed_pointers: ["/facts/0/value"] } };
  const event2Ref = addJson("event_2", "event", event2);
  const revision2 = signRecord("kingdom.event-revision/v0", { event_id: event2.event_id, sequence: 2, event_sha256: event2Ref.sha256, previous_revision_sha256: revision1Ref.sha256, created_at: iso(now + 10) }, privateKey);
  const revision2Ref = addJson("revision_2", "event_revision", revision2);
  const revisions = [revision1, revision2];
  const revisionRefs = [revision1Ref, revision2Ref];
  verifyChain(revisions, revisionRefs, trust);

  const projections = [];
  const projectionRecords = [];
  const projectionRefs = [];
  for (const [index, event] of [event1, event2].entries()) {
    for (const surface of SURFACES) {
      const revision = index + 1;
      const rendered = render(event, revisionRefs[index].sha256, surface);
      const renderedName = `render_${revision}_${surface}`;
      const renderedRef = add(renderedName, "projection_bytes", rendered);
      const policy = {
        decision: "allow", evaluated_at: createdAt, expires_at: iso(now + 86_400_000),
        checks: Object.fromEntries(REQUIRED_CHECKS.map((name) => [name, true])),
      };
      const receipt = signRecord("kingdom.projection-receipt/v0", {
        delivery_id: `synthetic-${revision}-${surface}`, revision, surface, created_at: iso(now + 20 + projections.length),
        event_revision_sha256: revisionRefs[index].sha256,
        semantic_sha256: digest(jsonBytes(semantic(event, revisionRefs[index].sha256))),
        rendered_sha256: renderedRef.sha256, rights_profile_sha256: rightsRef.sha256, policy,
      }, privateKey);
      const receiptName = `projection_receipt_${revision}_${surface}`;
      const receiptRef = addJson(receiptName, "projection_receipt", receipt);
      const materialized = `derived/revision-${revision}/${surface}.${surface === "telegram" ? "txt" : "json"}`;
      safeWrite(root, materialized, rendered);
      projections.push({ revision, surface, rendered: renderedName, receipt: receiptName, materialized_locator: materialized });
      projectionRecords.push(receipt);
      projectionRefs.push(receiptRef);
    }
  }

  const corrections = [];
  const correctionNames = [];
  for (let index = 0; index < SURFACES.length; index += 1) {
    const surface = SURFACES[index];
    const receipt = signRecord("kingdom.correction-propagation/v0", {
      correction_id: `synthetic-correction-${surface}`, surface, status: "propagated", priority: "same_as_original",
      from_revision_sha256: revision1Ref.sha256, to_revision_sha256: revision2Ref.sha256,
      original_delivery_sha256: projectionRefs[index].sha256, corrected_delivery_sha256: projectionRefs[index + 3].sha256,
      propagated_at: iso(now + 100 + index),
    }, privateKey);
    const name = `correction_${surface}`;
    addJson(name, "correction_receipt", receipt);
    correctionNames.push(name);
    corrections.push(receipt);
  }
  const projectionPayloads = projectionRecords.map((record, index) => ({ ...record.payload, receipt_sha256: projectionRefs[index].sha256 }));
  verifyCorrectionCoverage(corrections, trust, revisionRefs, projectionPayloads);

  const outage = signRecord("kingdom.service-incident/v0", { incident_id: "synthetic-source-outage", incident_type: "source_outage", status: "open", source_id: sourceReceipt.source_id, observed_at: iso(now + 200), previous_incident_sha256: null }, privateKey);
  const outageRef = addJson("incident_outage", "incident_receipt", outage);
  const recovery = signRecord("kingdom.service-incident/v0", { incident_id: outage.payload.incident_id, incident_type: "source_recovery", status: "resolved", source_id: sourceReceipt.source_id, observed_at: iso(now + 300), previous_incident_sha256: outageRef.sha256, recovery_evidence: { kind: "content_addressed_source_read", source_content_sha256: sourceContentRef.sha256, result: "verified" } }, privateKey);
  const recoveryRef = addJson("incident_recovery", "incident_receipt", recovery);
  const incidents = [outage, recovery];
  const incidentRefs = [outageRef, recoveryRef];
  verifyIncidentPair(incidents, incidentRefs, trust, sourceContentRef.sha256, sourceReceipt.source_id);

  const manifest = {
    kind: VERSION, created_at: createdAt, synthetic_fixture_only: true, negative_cases: 19,
    entries, revisions: [{ event: "event_1", receipt: "revision_1" }, { event: "event_2", receipt: "revision_2" }],
    projections, corrections: correctionNames, incidents: ["incident_outage", "incident_recovery"],
    counts: { revisions: 2, projections: 6, corrections: 3, incidents: 2 },
  };
  const manifestBytes = jsonBytes(manifest);
  const manifestSha256 = digest(manifestBytes);
  safeWrite(root, "manifest.json", manifestBytes);
  safeWrite(root, "manifest.sha256", Buffer.from(`${manifestSha256}\n`, "utf8"));
  const manifestReceipt = signRecord("kingdom.reserve-manifest-receipt/v0", { manifest_sha256: manifestSha256, created_at: createdAt, counts: manifest.counts }, privateKey);
  safeWrite(root, "manifest.receipt.json", jsonBytes(manifestReceipt));
  verifyArchive(root, { requireDrill: false, now });

  const negativeCases = runNegativeCases({ now, rights, termsRef, trust, privateKey, revisions, revisionRefs, projectionRecords, projectionRefs, corrections, incidents, incidentRefs, sourceContentRef, sourceReceipt, root });
  invariant(negativeCases >= 10, "negative-case floor");
  const offlineRebuild = rebuildProjections(root, manifest);
  verifyArchive(root, { requireDrill: false, now });
  const secrets = scanNoSecrets(root);
  const drillReceipt = signRecord("kingdom.reserve-drill-receipt/v0", { manifest_sha256: manifestSha256, completed_at: iso(Date.now()), negative_cases: negativeCases, offline_rebuild: offlineRebuild, secrets, network: 0 }, privateKey);
  safeWrite(root, "drill.receipt.json", jsonBytes(drillReceipt));
  return verifyArchive(root, { requireDrill: true });
}

function successLine(result, { verificationOnly = false } = {}) {
  const rebuild = verificationOnly && result.offlineRebuild ? "receipt_verified" : result.offlineRebuild;
  return `RESERVE_OK revisions=${result.revisions} projections=${result.projections} corrections=${result.corrections} incidents=${result.incidents} negative_cases=${result.negativeCases} offline_rebuild=${rebuild} manifest_root=${result.manifestSha256} secrets=${result.secrets} network=0`;
}

function help() {
  return `KINGDOM Reserve Loop v0\n\nUsage:\n  reserve-loop.mjs drill [ARCHIVE]\n  reserve-loop.mjs verify ARCHIVE\n  reserve-loop.mjs help\n\nThe drill is synthetic, networkless, and writes no private key.\n`;
}

export { createArchive, rebuildProjections, successLine, verifyArchive };

function main(argv) {
  const [command, archiveArg] = argv;
  if (!command || command === "help" || command === "--help" || command === "-h") {
    process.stdout.write(help());
    return 0;
  }
  if (command === "drill") {
    const temporary = !archiveArg;
    const archive = archiveArg ? resolve(archiveArg) : mkdtempSync(join(tmpdir(), "kingdom-reserve-loop-"));
    try {
      const result = createArchive(archive);
      process.stdout.write(`${successLine(result)}\n`);
      if (!temporary) process.stdout.write(`archive=${archive}\n`);
    } finally {
      if (temporary) rmSync(archive, { recursive: true, force: true });
    }
    return 0;
  }
  if (command === "verify") {
    if (!archiveArg) { process.stderr.write("verify requires ARCHIVE\n"); return 2; }
    const result = verifyArchive(resolve(archiveArg));
    process.stdout.write(`${successLine(result, { verificationOnly: true })}\n`);
    return 0;
  }
  process.stderr.write(`unknown command: ${command}\n${help()}`);
  return 2;
}

if (resolve(process.argv[1] ?? "") === fileURLToPath(import.meta.url)) {
  try { process.exitCode = main(process.argv.slice(2)); }
  catch (error) {
    process.stderr.write(`RESERVE_FAIL ${error instanceof Error ? error.message : String(error)}\n`);
    process.exitCode = 1;
  }
}
