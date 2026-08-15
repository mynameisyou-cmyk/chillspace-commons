(function () {
  "use strict";

  const MAX_FILE_BYTES = 65536;
  const MAX_DEPTH = 12;
  const MAX_NODES = 4096;
  const INCIDENT_SCHEMA = "kingdom.incident/v1";
  const INCIDENT_ENGINE = "incident-lantern/1";
  const CANDIDATE_SCHEMA = "kingdom.karma.regression-candidate/v1";
  const DOWNLOAD_NAME = "incident-lantern-regression-candidate.json";

  const INCIDENT_NONCLAIMS = Object.freeze([
    "This incident explains one replay-verified offline categorical plan.",
    "It does not authenticate external provenance, event time, sequence, duplication, or live impact.",
    "It does not identify a person or infer intent, guilt, hostility, or reputation.",
    "Displayed actions are proposal-only and grant no authority or production effect.",
    "The regression candidate does not mutate the classifier or install a rule.",
    "Zero modelled effects do not prove operating-system confinement or deployment safety."
  ]);

  const CANDIDATE_NONCLAIMS = Object.freeze([
    "This candidate preserves a categorical fixture, not raw traffic or identity.",
    "It does not authenticate external provenance or establish intent, guilt, or impact.",
    "It does not install a rule, mutate a classifier, or authorize an action.",
    "Promotion requires joint human review of policy, threat model, corpus, pins, and tests."
  ]);

  const ROOT_KEYS = Object.freeze([
    "schema", "engine", "status", "incident_id", "source", "headline",
    "epistemics", "timeline", "actions", "learning", "controls",
    "nonclaims", "incident_digest"
  ]);
  const SOURCE_KEYS = Object.freeze([
    "event_digest", "receipt_digest", "source_status",
    "receipt_classification", "bindings"
  ]);
  const INCIDENT_BINDING_KEYS = Object.freeze([
    "incident_engine_sha256", "incident_schema_sha256", "candidate_schema_sha256",
    "future_engine_sha256", "policy_sha256", "event_schema_sha256",
    "receipt_schema_sha256", "threat_model_sha256"
  ]);
  const CANDIDATE_BINDING_KEYS = Object.freeze([
    "future_engine_sha256", "policy_sha256", "event_schema_sha256",
    "receipt_schema_sha256", "threat_model_sha256"
  ]);
  const HEADLINE_KEYS = Object.freeze([
    "title", "severity", "disposition", "planned_action", "summary"
  ]);
  const EPISTEMIC_KEYS = Object.freeze(["facts", "inferences", "unknowns"]);
  const KNOWLEDGE_ITEM_KEYS = Object.freeze([
    "id", "statement", "refs", "confidence", "resolution"
  ]);
  const TIMELINE_KEYS = Object.freeze(["ordinal", "phase", "state", "label", "refs"]);
  const ACTION_KEYS = Object.freeze([
    "rank", "id", "kind", "label", "rationale", "authority", "automatic",
    "actual_effect", "reversibility", "blast_radius", "preconditions",
    "rollback", "verification", "state"
  ]);
  const LEARNING_KEYS = Object.freeze(["threat", "guidance", "regression_candidate"]);
  const THREAT_KEYS = Object.freeze(["id", "title", "evidence_status"]);
  const GUIDANCE_KEYS = Object.freeze([
    "detection", "containment", "recovery", "privacy_output"
  ]);
  const CONTROL_KEYS = Object.freeze([
    "network_calls", "process_spawns", "model_calls", "secret_reads",
    "filesystem_writes", "external_messages", "authority_granted",
    "action_executed", "classifier_mutated", "engine_retained_records"
  ]);
  const CANDIDATE_KEYS = Object.freeze([
    "schema", "candidate_id", "source", "event", "expected", "promotion",
    "nonclaims", "candidate_digest"
  ]);
  const CANDIDATE_SOURCE_KEYS = Object.freeze(["event_digest", "receipt_digest", "bindings"]);
  const EVENT_KEYS = Object.freeze([
    "retention", "schema", "surface", "mechanism", "signal", "signal_quality",
    "provenance", "novelty", "purpose", "scope", "authority", "evidence_count"
  ]);
  const EXPECTED_KEYS = Object.freeze([
    "status", "classification", "rule_id", "threat_id", "action", "fallback",
    "severity", "halt_code", "mirror"
  ]);
  const MIRROR_KEYS = Object.freeze(["mode", "max_attempts", "egress"]);
  const PROMOTION_KEYS = Object.freeze([
    "state", "eligibility", "automatic_install", "classifier_mutated", "authority"
  ]);

  /* These pins bind the browser explanation to one reviewed Incident Lantern build. */
  const PINNED_BINDINGS = Object.freeze({
    incident_engine_sha256: "cd6fe4abe1f58d5adf4da829f17ac35ede9cdcec9cac2b16059055575ae7764f",
    incident_schema_sha256: "e57d56f9313c803ef16a92cd8ad7024c83ca628be7b761594c7e598c50cbc1c4",
    candidate_schema_sha256: "21b46aaf1e0d265d7741c0bafcd2e0f81e95958da4ce84a05b770bf922f22fa0",
    future_engine_sha256: "20f7869a69d3b985f842e047276ce17da98504ebde87b36c4a9593a131dddbac",
    policy_sha256: "7c566a11f1330eaa1093e7ad093627c1f79e7cb032962a078f6b348896733004",
    event_schema_sha256: "8299d74eafbf86e8a208a1687c442ed8f4e01fc2a5f1b91a9c7662731ab57247",
    receipt_schema_sha256: "f6e27f93891a53ab23fc2ba78941b94954ec441a9df5e7f917cec0ace7526124",
    threat_model_sha256: "c20e2fff39494f908f07339c6d2bfc2805af0d79071a946e6f1752b8391e1c7b"
  });
  const PINNED_CANDIDATE_BINDINGS = Object.freeze({
    future_engine_sha256: PINNED_BINDINGS.future_engine_sha256,
    policy_sha256: PINNED_BINDINGS.policy_sha256,
    event_schema_sha256: PINNED_BINDINGS.event_schema_sha256,
    receipt_schema_sha256: PINNED_BINDINGS.receipt_schema_sha256,
    threat_model_sha256: PINNED_BINDINGS.threat_model_sha256
  });

  /* surface, mechanism, signal, rule, threat, minimum evidence, action, fallback, severity, mirror */
  const POLICY_RULES = Object.freeze([
    Object.freeze(["baseline", "bounded-control", "reviewed-fixture", "control-nominal", "t00-bounded-control", 0, "allow", "deny", 0, "none"]),
    Object.freeze(["quest-context", "prompt-injection", "untrusted-instruction", "prompt-injection", "t01-context-manipulation", 1, "quarantine", "deny", 4, "none"]),
    Object.freeze(["authority", "authority-laundering", "forged-claim", "authority-laundering", "t02-authority-confusion", 1, "deny", "quarantine", 5, "none"]),
    Object.freeze(["capability", "capability-confusion", "discovered-tool", "capability-confusion", "t02-authority-confusion", 1, "quarantine", "deny", 4, "none"]),
    Object.freeze(["filesystem", "path-escape", "untrusted-path", "path-escape", "t03-path-source-confusion", 1, "deny", "quarantine", 5, "none"]),
    Object.freeze(["secrets", "secret-exfiltration", "secret-request", "secret-exfiltration", "t04-secret-privacy-exfiltration", 1, "deny", "quarantine", 5, "none"]),
    Object.freeze(["provenance", "manifest-poisoning", "unpinned-artifact", "manifest-poisoning", "t05-provenance-substitution", 1, "quarantine", "deny", 4, "none"]),
    Object.freeze(["repository", "repository-substitution", "identity-mismatch", "repository-substitution", "t05-provenance-substitution", 1, "quarantine", "deny", 4, "none"]),
    Object.freeze(["workflow", "workflow-input-injection", "untrusted-trigger", "workflow-input-injection", "t06-workflow-supply-chain", 1, "deny", "quarantine", 5, "none"]),
    Object.freeze(["workflow", "supply-chain-drift", "unpinned-action", "workflow-supply-drift", "t06-workflow-supply-chain", 1, "quarantine", "deny", 4, "none"]),
    Object.freeze(["dependency", "dependency-confusion", "shadowed-import", "dependency-confusion", "t07-dependency-plugin-poisoning", 1, "deny", "quarantine", 5, "none"]),
    Object.freeze(["web-content", "active-content-injection", "untrusted-markup", "active-content-injection", "t08-content-injection", 1, "deny", "quarantine", 4, "none"]),
    Object.freeze(["network-fetch", "ssrf", "nonallowlisted-target", "ssrf", "t09-egress-abuse", 1, "deny", "quarantine", 5, "none"]),
    Object.freeze(["resource", "resource-exhaustion", "budget-pressure", "resource-exhaustion", "t10-resource-abuse", 0, "throttle", "quarantine", 3, "none"]),
    Object.freeze(["receipt", "replay-tamper", "stale-or-altered", "receipt-replay-tamper", "t11-replay-integrity", 1, "quarantine", "deny", 4, "none"]),
    Object.freeze(["metrics", "counter-gaming", "manipulated-evidence", "counter-gaming", "t12-metric-gaming", 1, "quarantine", "deny", 4, "none"]),
    Object.freeze(["mcp-tool", "schema-drift", "capability-expansion", "tool-schema-drift", "t13-tool-contract-drift", 1, "quarantine", "deny", 4, "none"]),
    Object.freeze(["filesystem", "toctou-file-swap", "file-changed", "toctou-file-swap", "t03-path-source-confusion", 1, "deny", "quarantine", 5, "none"]),
    Object.freeze(["privacy", "linkability", "identity-correlation", "privacy-linkability", "t04-secret-privacy-exfiltration", 1, "deny", "quarantine", 5, "none"]),
    Object.freeze(["session", "hook-poisoning", "ambient-context", "session-hook-poisoning", "t01-context-manipulation", 1, "quarantine", "deny", 4, "none"]),
    Object.freeze(["text", "unicode-ambiguity", "confusable-token", "unicode-ambiguity", "t14-parser-ambiguity", 1, "quarantine", "deny", 4, "none"]),
    Object.freeze(["citizenship", "issue-door-abuse", "automated-persuasion", "issue-door-abuse", "t15-participation-abuse", 0, "throttle", "quarantine", 3, "none"]),
    Object.freeze(["deployment", "subject-drift", "build-mismatch", "deployment-substitution", "t05-provenance-substitution", 1, "quarantine", "deny", 5, "none"]),
    Object.freeze(["public-decoy", "known-probe", "synthetic-probe", "known-decoy-probe", "t16-no-egress-decoy", 1, "synthetic-mirror", "quarantine", 3, "isolated-no-egress"])
  ]);

  /* title, evidence status, detection, containment, recovery, privacy output */
  const THREAT_PRESENTATION = Object.freeze({
    "t00-bounded-control": Object.freeze(["Bounded control", "observed", "Deterministic control receipt", "Stop on any binding drift", "Re-pin only after review", "Fixed non-public LOVE envelope"]),
    "t01-context-manipulation": Object.freeze(["Prompt and ambient context manipulation", "inferred", "Exact categorical signal from a trusted adapter", "Quarantine and halt novelty", "Remove poisoned context and replay from clean input", "No source reflection or intent attribution"]),
    "t02-authority-confusion": Object.freeze(["Authority laundering and capability confusion", "inferred", "Exact forged-claim or discovered-tool category", "Deny or quarantine with zero effects", "Require a separately authorized capability handoff", "No identity claim and no public output"]),
    "t03-path-source-confusion": Object.freeze(["Path traversal, links, and source swapping", "observed", "Path or file-change category plus binding mismatch", "Deny before a read outside the fixed catalog", "Use fresh trusted bytes and repeat verification", "No path or content echo"]),
    "t04-secret-privacy-exfiltration": Object.freeze(["Secret exfiltration and identity linkability", "inferred", "Secret-request or identity-correlation category", "Deny with all effect counters zero", "Rotate externally if exposure is independently confirmed", "No secret, identifier, or raw input retained"]),
    "t05-provenance-substitution": Object.freeze(["Manifest, repository, and deployment substitution", "observed", "Binding or subject mismatch", "Quarantine and withhold release", "Rebuild from independently pinned source", "Technique-only fixed receipt"]),
    "t06-workflow-supply-chain": Object.freeze(["Workflow input injection and action drift", "observed", "Untrusted-trigger or unpinned-action category", "Deny or quarantine; planner remains unwired", "Review workflow in a separate authorized change", "No user text or automatic reply"]),
    "t07-dependency-plugin-poisoning": Object.freeze(["Dependency confusion and plugin poisoning", "observed", "Shadowed-import or changed binding", "Deny and stop loading", "Recreate environment from reviewed lock and artifacts", "No attacker naming or amplification"]),
    "t08-content-injection": Object.freeze(["Active content and public-output injection", "inferred", "Untrusted-markup category and output scan", "Deny; publication stays false", "Render only reviewed constants in a separate system", "Fixed care posture without links"]),
    "t09-egress-abuse": Object.freeze(["SSRF and callback abuse", "inferred", "Nonallowlisted-target category", "Deny with network counter zero", "Assess any future adapter separately", "No callback, redirect, or advertiser channel"]),
    "t10-resource-abuse": Object.freeze(["Resource and repetition exhaustion", "observed", "Budget-pressure or validation failure", "Throttle or fail before planning", "Caller owns concurrency and wall-time ceilings", "Minimal deterministic receipt"]),
    "t11-replay-integrity": Object.freeze(["Receipt replay and consequential tamper", "observed", "Stale-or-altered category or verify mismatch", "Quarantine and return false", "Caller applies dedupe, audience, sequence, and expiry", "Digest-only event reference"]),
    "t12-metric-gaming": Object.freeze(["Counter, evidence, and reward gaming", "inferred", "Manipulated-evidence category", "Quarantine; delta remains zero", "Human reviews one technique family once", "No person score, reward, or public tally"]),
    "t13-tool-contract-drift": Object.freeze(["MCP and agent tool contract drift", "inferred", "Capability-expansion category", "Quarantine and require re-review", "Pin and test a new contract separately", "No tool output reflected"]),
    "t14-parser-ambiguity": Object.freeze(["Unicode and parser ambiguity", "observed", "Confusable-token category or parser rejection", "Quarantine or reject before receipt", "Canonicalize only in a separately reviewed adapter", "No ambiguous text emitted"]),
    "t15-participation-abuse": Object.freeze(["Citizenship and issue-door automation abuse", "inferred", "Automated-persuasion category", "Throttle locally; no message sent", "Moderate through existing human governance", "No identity inference or unsolicited contact"]),
    "t16-no-egress-decoy": Object.freeze(["Known synthetic decoy handling", "unknown", "Synthetic-probe category with confirmed pinned provenance", "Produce a local candidate with zero external effects", "Delete caller-owned receipt after review", "Fixed LOVE candidate; never attacker-authored advertising"])
  });

  const ACTION_PRESENTATION = Object.freeze({
    allow: Object.freeze(["Maintain the reviewed path", "The pinned policy selected its bounded negative-control posture."]),
    observe: Object.freeze(["Increase bounded observation", "Collect only the minimum categorical evidence needed for another review."]),
    throttle: Object.freeze(["Review a bounded throttle", "Reduce pressure at an owned boundary while preserving a rollback path."]),
    deny: Object.freeze(["Review a bounded deny", "Stop the reviewed categorical path only at a boundary the responder owns."]),
    quarantine: Object.freeze(["Keep the boundary quarantined", "Hold uncertain input away from broader state until evidence and authority are clear."]),
    "synthetic-mirror": Object.freeze(["Review the sterile mirror candidate", "Keep any mirror isolated, no-egress, single-attempt, and entirely synthetic."])
  });

  const ZERO_CONTROLS = Object.freeze({
    network_calls: 0,
    process_spawns: 0,
    model_calls: 0,
    secret_reads: 0,
    filesystem_writes: 0,
    external_messages: 0,
    authority_granted: false,
    action_executed: false,
    classifier_mutated: false,
    engine_retained_records: 0
  });

  const SHA_PATTERN = /^[0-9a-f]{64}$/;
  const ID_PATTERN = /^[a-z0-9][a-z0-9-]{0,63}$/;
  const TOKEN_PATTERN = /^[a-z0-9][a-z0-9-]{0,47}$/;
  const REFERENCE_PATTERN = /^[a-z][a-z0-9_]{0,31}(?:\.[a-z][a-z0-9_]{0,31}){0,3}$/;
  const KEY_PATTERN = /^[a-z][a-z0-9_]{0,63}$/;
  const FORBIDDEN_KEY_PATTERN = /^(?:analysis|chain_?of_?thought|cot|deliberation|hidden_?state|internal_?(?:reasoning|monologue)|raw_?(?:reasoning|thinking)|reasoning(?:_?(?:content|details))?|scratchpad|thinking|thoughts?)$/;
  const SECRET_PATTERNS = Object.freeze([
    /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/,
    /\bgh(?:p|o|u|s|r)_[A-Za-z0-9_]{20,}\b/,
    /\bgithub_pat_[A-Za-z0-9_]{20,}\b/,
    /\bsk-[A-Za-z0-9_-]{20,}\b/,
    /\bAKIA[0-9A-Z]{16}\b/,
    /\bbearer\s+[A-Za-z0-9._~+/=-]{16,}/i,
    /\b(?:api[_-]?key|token|secret|password|credential)\s*[:=]\s*["']?[^\s"']{8,}/i
  ]);

  function fail(message) {
    throw new Error(message);
  }

  function isRecord(value) {
    if (value === null || typeof value !== "object" || Array.isArray(value)) {
      return false;
    }
    const prototype = Object.getPrototypeOf(value);
    return prototype === Object.prototype || prototype === null;
  }

  function exactKeys(value, expected, path) {
    if (!isRecord(value)) {
      fail(path + " must be an object");
    }
    const actual = Object.keys(value).sort();
    const wanted = Array.from(expected).sort();
    if (actual.length !== wanted.length || actual.some(function (key, index) {
      return key !== wanted[index];
    })) {
      fail(path + " must contain exactly: " + wanted.join(", "));
    }
  }

  function assertLiteral(value, expected, path) {
    if (value !== expected) {
      fail(path + " must equal " + JSON.stringify(expected));
    }
  }

  function assertEnum(value, choices, path) {
    if (!choices.includes(value)) {
      fail(path + " is not an allowed value");
    }
  }

  function assertInteger(value, minimum, maximum, path) {
    if (!Number.isSafeInteger(value) || value < minimum || value > maximum) {
      fail(path + " must be an integer from " + minimum + " to " + maximum);
    }
  }

  function assertText(value, minimum, maximum, path) {
    if (typeof value !== "string" || value.length < minimum || value.length > maximum) {
      fail(path + " must be " + minimum + ".." + maximum + " ASCII characters");
    }
    for (let index = 0; index < value.length; index += 1) {
      const code = value.charCodeAt(index);
      if (code < 32 || code > 126) {
        fail(path + " must contain printable ASCII only");
      }
    }
  }

  function assertPattern(value, pattern, path) {
    if (typeof value !== "string" || !pattern.test(value)) {
      fail(path + " has an invalid format");
    }
  }

  function assertArray(value, minimum, maximum, path) {
    if (!Array.isArray(value) || value.length < minimum || value.length > maximum) {
      fail(path + " must contain " + minimum + ".." + maximum + " items");
    }
  }

  function assertUniqueStrings(value, path) {
    if (new Set(value).size !== value.length) {
      fail(path + " must not contain duplicates");
    }
  }

  function assertReferences(value, path) {
    assertArray(value, 1, 4, path);
    value.forEach(function (reference, index) {
      assertPattern(reference, REFERENCE_PATTERN, path + "[" + index + "]");
    });
    assertUniqueStrings(value, path);
  }

  function assertChecklist(value, path) {
    assertArray(value, 1, 4, path);
    value.forEach(function (item, index) {
      assertText(item, 1, 240, path + "[" + index + "]");
    });
  }

  function assertLiteralArray(value, expected, path) {
    if (!Array.isArray(value) || value.length !== expected.length || value.some(function (item, index) {
      return item !== expected[index];
    })) {
      fail(path + " does not retain the reviewed nonclaims");
    }
  }

  function safeTree(value, path, depth, state) {
    if (depth > MAX_DEPTH) {
      fail(path + " exceeds maximum depth " + MAX_DEPTH);
    }
    state.nodes += 1;
    if (state.nodes > MAX_NODES) {
      fail("incident contains too many values");
    }
    if (isRecord(value)) {
      Object.keys(value).forEach(function (key) {
        if (!KEY_PATTERN.test(key) || FORBIDDEN_KEY_PATTERN.test(key)) {
          fail(path + " contains a forbidden or unsafe field name");
        }
        safeTree(value[key], path + "." + key, depth + 1, state);
      });
      return;
    }
    if (Array.isArray(value)) {
      if (value.length > 64) {
        fail(path + " exceeds 64 items");
      }
      value.forEach(function (item, index) {
        safeTree(item, path + "[" + index + "]", depth + 1, state);
      });
      return;
    }
    if (typeof value === "string") {
      if (value.length > 1000) {
        fail(path + " exceeds 1000 characters");
      }
      if (/\u0000|[\u0001-\u001f\u007f]|[\u202a-\u202e\u2066-\u2069]/.test(value)) {
        fail(path + " contains control or bidirectional override characters");
      }
      SECRET_PATTERNS.forEach(function (pattern) {
        if (pattern.test(value)) {
          fail(path + " contains secret-shaped material");
        }
      });
      return;
    }
    if (value === null || typeof value === "boolean") {
      return;
    }
    if (typeof value === "number" && Number.isSafeInteger(value)) {
      return;
    }
    fail(path + " contains an unsupported JSON value");
  }

  function quoteAscii(value) {
    let result = "\"";
    for (let index = 0; index < value.length; index += 1) {
      const code = value.charCodeAt(index);
      if (code === 34) {
        result += "\\\"";
      } else if (code === 92) {
        result += "\\\\";
      } else if (code === 8) {
        result += "\\b";
      } else if (code === 9) {
        result += "\\t";
      } else if (code === 10) {
        result += "\\n";
      } else if (code === 12) {
        result += "\\f";
      } else if (code === 13) {
        result += "\\r";
      } else if (code >= 32 && code <= 126) {
        result += value.charAt(index);
      } else {
        result += "\\u" + code.toString(16).padStart(4, "0");
      }
    }
    return result + "\"";
  }

  function canonicalStringify(value) {
    if (value === null) {
      return "null";
    }
    if (value === true) {
      return "true";
    }
    if (value === false) {
      return "false";
    }
    if (typeof value === "number" && Number.isSafeInteger(value)) {
      return String(value);
    }
    if (typeof value === "string") {
      return quoteAscii(value);
    }
    if (Array.isArray(value)) {
      return "[" + value.map(canonicalStringify).join(",") + "]";
    }
    if (isRecord(value)) {
      return "{" + Object.keys(value).sort().map(function (key) {
        return quoteAscii(key) + ":" + canonicalStringify(value[key]);
      }).join(",") + "}";
    }
    fail("value cannot be represented as canonical JSON");
  }

  function rotateRight(value, count) {
    return (value >>> count) | (value << (32 - count));
  }

  function sha256Ascii(input) {
    const bytes = [];
    for (let index = 0; index < input.length; index += 1) {
      const code = input.charCodeAt(index);
      if (code > 127) {
        fail("SHA-256 input must be ASCII");
      }
      bytes.push(code);
    }
    const bitLength = bytes.length * 8;
    bytes.push(128);
    while (bytes.length % 64 !== 56) {
      bytes.push(0);
    }
    bytes.push(0, 0, 0, 0);
    bytes.push(
      (bitLength >>> 24) & 255,
      (bitLength >>> 16) & 255,
      (bitLength >>> 8) & 255,
      bitLength & 255
    );

    const constants = [
      0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
      0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
      0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
      0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
      0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
      0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
      0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
      0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
    ];
    const hash = [
      0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
      0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    ];
    const words = new Array(64);

    for (let offset = 0; offset < bytes.length; offset += 64) {
      for (let index = 0; index < 16; index += 1) {
        const cursor = offset + index * 4;
        words[index] = (
          (bytes[cursor] << 24) | (bytes[cursor + 1] << 16) |
          (bytes[cursor + 2] << 8) | bytes[cursor + 3]
        ) >>> 0;
      }
      for (let index = 16; index < 64; index += 1) {
        const left = words[index - 15];
        const right = words[index - 2];
        const sigma0 = rotateRight(left, 7) ^ rotateRight(left, 18) ^ (left >>> 3);
        const sigma1 = rotateRight(right, 17) ^ rotateRight(right, 19) ^ (right >>> 10);
        words[index] = (words[index - 16] + sigma0 + words[index - 7] + sigma1) >>> 0;
      }

      let a = hash[0];
      let b = hash[1];
      let c = hash[2];
      let d = hash[3];
      let e = hash[4];
      let f = hash[5];
      let g = hash[6];
      let h = hash[7];
      for (let index = 0; index < 64; index += 1) {
        const sum1 = rotateRight(e, 6) ^ rotateRight(e, 11) ^ rotateRight(e, 25);
        const choice = (e & f) ^ ((~e) & g);
        const first = (h + sum1 + choice + constants[index] + words[index]) >>> 0;
        const sum0 = rotateRight(a, 2) ^ rotateRight(a, 13) ^ rotateRight(a, 22);
        const majority = (a & b) ^ (a & c) ^ (b & c);
        const second = (sum0 + majority) >>> 0;
        h = g;
        g = f;
        f = e;
        e = (d + first) >>> 0;
        d = c;
        c = b;
        b = a;
        a = (first + second) >>> 0;
      }
      hash[0] = (hash[0] + a) >>> 0;
      hash[1] = (hash[1] + b) >>> 0;
      hash[2] = (hash[2] + c) >>> 0;
      hash[3] = (hash[3] + d) >>> 0;
      hash[4] = (hash[4] + e) >>> 0;
      hash[5] = (hash[5] + f) >>> 0;
      hash[6] = (hash[6] + g) >>> 0;
      hash[7] = (hash[7] + h) >>> 0;
    }
    return hash.map(function (word) {
      return word.toString(16).padStart(8, "0");
    }).join("");
  }

  function digestWithout(value, field) {
    const projection = {};
    Object.keys(value).forEach(function (key) {
      if (key !== field) {
        projection[key] = value[key];
      }
    });
    return sha256Ascii(canonicalStringify(projection));
  }

  function canonicalClone(value) {
    return JSON.parse(canonicalStringify(value));
  }

  function assertCanonicalEqual(value, expected, path) {
    if (canonicalStringify(value) !== canonicalStringify(expected)) {
      fail(path + " does not match the pinned reviewed build");
    }
  }

  function assertPinnedBindings(value, expected, path) {
    assertCanonicalEqual(value, expected, path);
  }

  function plannedRule(event) {
    const matches = POLICY_RULES.filter(function (rule) {
      return rule[0] === event.surface && rule[1] === event.mechanism && rule[2] === event.signal;
    });
    if (matches.length !== 1) {
      fail("$.learning.regression_candidate.event selector is not in the pinned reviewed policy");
    }
    const rule = matches[0];
    if (
      event.signal_quality !== "confirmed" ||
      event.provenance !== "pinned" ||
      event.novelty !== "known" ||
      event.evidence_count < rule[5]
    ) {
      fail("$.learning.regression_candidate.event cannot produce a planned pinned decision");
    }
    return rule;
  }

  function validatePinnedProjection(candidate) {
    const event = candidate.event;
    const expected = candidate.expected;
    if (expected.status === "planned") {
      const rule = plannedRule(event);
      const policyExpected = {
        status: "planned",
        classification: "reviewed-categorical",
        rule_id: rule[3],
        threat_id: rule[4],
        action: rule[6],
        fallback: rule[7],
        severity: rule[8],
        halt_code: "none",
        mirror: {
          mode: rule[9],
          max_attempts: rule[6] === "synthetic-mirror" ? 1 : 0,
          egress: false
        }
      };
      assertCanonicalEqual(expected, policyExpected, "$.learning.regression_candidate.expected");
      return;
    }
    const haltCodes = {
      "unmatched-categorical": "unmatched-selector",
      "uncertain-categorical": "boundary-uncertain",
      "insufficient-categorical": "insufficient-evidence"
    };
    const haltedExpected = {
      status: "halted",
      classification: expected.classification,
      rule_id: "none",
      threat_id: "none",
      action: "quarantine",
      fallback: "deny",
      severity: 5,
      halt_code: haltCodes[expected.classification],
      mirror: {mode: "none", max_attempts: 0, egress: false}
    };
    if (!haltedExpected.halt_code) {
      fail("$.learning.regression_candidate.expected halted classification is not reviewed");
    }
    assertCanonicalEqual(expected, haltedExpected, "$.learning.regression_candidate.expected");
  }

  function threatAndGuidance(candidate) {
    if (candidate.expected.status === "halted") {
      return {
        threat: {
          id: "none",
          title: "Unmapped categorical boundary",
          evidence_status: "unknown"
        },
        guidance: {
          detection: "Preserve only the source and receipt digests for human review.",
          containment: "Keep the boundary quarantined; do not interpret withheld values.",
          recovery: "Author a reviewed fixture and policy mapping before any promotion.",
          privacy_output: "Withhold unreviewed categorical values and all raw source data."
        }
      };
    }
    const presentation = THREAT_PRESENTATION[candidate.expected.threat_id];
    if (!presentation) {
      fail("$.learning.threat is not in the pinned reviewed threat model");
    }
    return {
      threat: {
        id: candidate.expected.threat_id,
        title: presentation[0],
        evidence_status: presentation[1]
      },
      guidance: {
        detection: presentation[2],
        containment: presentation[3],
        recovery: presentation[4],
        privacy_output: presentation[5]
      }
    };
  }

  function expectedEpistemics(candidate, threat) {
    const planned = candidate.expected.status === "planned";
    const facts = [
      {
        id: "categorical-contract",
        statement: "A closed categorical event passed the pinned Future KARMA event contract.",
        refs: ["source.event_digest"],
        confidence: "confirmed",
        resolution: "replay-verified"
      },
      {
        id: "scope-boundary",
        statement: "The source declares offline-synthetic scope and grants no authority.",
        refs: ["source.event_digest", "controls.authority_granted"],
        confidence: "confirmed",
        resolution: "replay-verified"
      },
      {
        id: "receipt-replay",
        statement: "The supplied receipt matched a fresh deterministic planner replay.",
        refs: ["source.receipt_digest"],
        confidence: "confirmed",
        resolution: "replay-verified"
      },
      {
        id: "policy-disposition",
        statement: "The pinned policy produced the displayed proposal without executing it.",
        refs: ["headline.planned_action", "source.bindings.policy_sha256"],
        confidence: "confirmed",
        resolution: "catalog-derived"
      }
    ];
    const inferences = [
      {
        id: "threat-family-reading",
        statement: planned
          ? "The pinned model maps the reviewed selector to " + threat.title + "."
          : "No reviewed threat family was established; the boundary halt remains unresolved.",
        refs: ["learning.threat.id", "source.receipt_digest"],
        confidence: "policy-derived",
        resolution: planned ? "catalog-derived" : "human-review-required"
      },
      {
        id: "response-posture-reading",
        statement: "The displayed action is a decision aid, not evidence that containment occurred.",
        refs: ["headline.planned_action", "controls.action_executed"],
        confidence: "policy-derived",
        resolution: "human-review-required"
      }
    ];
    const unknownSpecs = [
      ["external-provenance", "Whether an external observation was authentic or complete.", "outside-source-contract", ["source.event_digest"]],
      ["identity-and-intent", "Any actor identity, intent, guilt, hostility, or reputation.", "outside-source-contract", ["source.event_digest"]],
      ["live-impact", "Real-world impact, production exposure, and current blast radius.", "human-review-required", ["headline.severity"]],
      ["time-and-sequence", "Event time, ordering, duplication, and recurrence.", "outside-source-contract", ["source.event_digest"]],
      ["containment-state", "Whether an authorized containment action was actually executed and verified.", "human-review-required", ["controls.action_executed"]],
      ["retention-state", "Whether caller-owned retention and deletion duties were enforced.", "outside-source-contract", ["source.receipt_digest"]]
    ];
    if (!planned) {
      unknownSpecs.push([
        "withheld-selector",
        "The meaning and safe mapping of the withheld unreviewed categorical selector.",
        "human-review-required",
        ["source.event_digest", "headline.disposition"]
      ]);
    }
    const unknowns = unknownSpecs.map(function (item) {
      return {
        id: item[0],
        statement: item[1],
        refs: item[3],
        confidence: "unknown",
        resolution: item[2]
      };
    });
    return {facts: facts, inferences: inferences, unknowns: unknowns};
  }

  function expectedTimeline(candidate) {
    const halted = candidate.expected.status === "halted";
    return [
      {ordinal: 1, phase: "categorical-observation", state: "complete", label: "Bounded categorical observation received", refs: ["source.event_digest"]},
      {ordinal: 2, phase: "source-bindings-validated", state: "complete", label: "Pinned planner and catalogs validated", refs: ["source.bindings.future_engine_sha256", "source.bindings.policy_sha256"]},
      {ordinal: 3, phase: "receipt-replayed", state: "complete", label: "Supplied receipt survived exact replay", refs: ["source.receipt_digest"]},
      {ordinal: 4, phase: "policy-decision-produced", state: halted ? "halted" : "complete", label: halted ? "Boundary halted for review" : "Reviewed policy proposal produced", refs: ["headline.disposition", "headline.planned_action"]},
      {ordinal: 5, phase: "human-review-pending", state: "pending", label: "Human decision, authorization, and verification remain pending", refs: ["controls.authority_granted", "controls.action_executed"]}
    ];
  }

  function expectedActions(candidate) {
    const expected = candidate.expected;
    const primary = ACTION_PRESENTATION[expected.action];
    const fallback = ACTION_PRESENTATION[expected.fallback];
    if (!primary || !fallback) {
      fail("$.actions contains an action outside the pinned presentation table");
    }
    const preconditions = [
      "Confirm ownership and authority for the affected boundary.",
      "Assess current blast radius with evidence outside this receipt.",
      "Fix rollback and stop conditions before any external effect."
    ];
    const verification = [
      "Replay the relevant negative control after the change.",
      "Confirm the intended boundary changed and unrelated paths did not."
    ];
    return [
      {
        rank: 1,
        id: "review-primary-proposal",
        kind: "primary",
        label: primary[0],
        rationale: primary[1],
        authority: "human-required",
        automatic: false,
        actual_effect: "none",
        reversibility: "conditional",
        blast_radius: "external-requires-review",
        preconditions: Array.from(preconditions),
        rollback: "Restore the last reviewed boundary policy and replay its negative control.",
        verification: Array.from(verification),
        state: "not-executed"
      },
      {
        rank: 2,
        id: "review-fallback-proposal",
        kind: "fallback",
        label: fallback[0],
        rationale: fallback[1],
        authority: "human-required",
        automatic: false,
        actual_effect: "none",
        reversibility: "conditional",
        blast_radius: "external-requires-review",
        preconditions: Array.from(preconditions),
        rollback: "Remove the fallback at the owned boundary and restore the reviewed policy.",
        verification: Array.from(verification),
        state: "not-executed"
      },
      {
        rank: 3,
        id: "export-regression-candidate",
        kind: "verification",
        label: "Preserve the lesson for review",
        rationale: "Export one sanitized candidate without installing it or changing the classifier.",
        authority: "human-required",
        automatic: false,
        actual_effect: "none",
        reversibility: "reversible",
        blast_radius: "local-bounded",
        preconditions: ["Review the candidate preview and its nonclaims."],
        rollback: "Discard the local candidate; no classifier state was changed.",
        verification: [
          "Recompute the candidate digest and compare exact canonical bytes.",
          "Confirm automatic_install and classifier_mutated remain false."
        ],
        state: "not-executed"
      }
    ];
  }

  function reconstructIncident(candidate) {
    const expected = candidate.expected;
    const planned = expected.status === "planned";
    const presentation = threatAndGuidance(candidate);
    const identifierBasis = {
      event_digest: candidate.source.event_digest,
      receipt_digest: candidate.source.receipt_digest
    };
    const value = {
      schema: INCIDENT_SCHEMA,
      engine: INCIDENT_ENGINE,
      status: planned ? "ready-for-review" : "halted-for-review",
      incident_id: "incident-" + sha256Ascii(canonicalStringify(identifierBasis)).slice(0, 16),
      source: {
        event_digest: candidate.source.event_digest,
        receipt_digest: candidate.source.receipt_digest,
        source_status: expected.status,
        receipt_classification: expected.classification,
        bindings: canonicalClone(PINNED_BINDINGS)
      },
      headline: {
        title: planned ? presentation.threat.title : "Unmapped categorical boundary",
        severity: expected.severity,
        disposition: planned ? "reviewed-plan" : "boundary-halt",
        planned_action: expected.action,
        summary: planned
          ? "Pinned policy produced a " + expected.action + " proposal for the reviewed " + expected.threat_id + " family; no action was executed."
          : "Future KARMA halted at " + expected.halt_code + "; unreviewed categorical values remain withheld and human mapping is required."
      },
      epistemics: expectedEpistemics(candidate, presentation.threat),
      timeline: expectedTimeline(candidate),
      actions: expectedActions(candidate),
      learning: {
        threat: presentation.threat,
        guidance: presentation.guidance,
        regression_candidate: canonicalClone(candidate)
      },
      controls: canonicalClone(ZERO_CONTROLS),
      nonclaims: Array.from(INCIDENT_NONCLAIMS)
    };
    value.incident_digest = sha256Ascii(canonicalStringify(value));
    return value;
  }

  function referenceResolves(root, reference) {
    let cursor = root;
    const parts = reference.split(".");
    for (const part of parts) {
      if (!isRecord(cursor) || !Object.prototype.hasOwnProperty.call(cursor, part)) {
        return false;
      }
      cursor = cursor[part];
    }
    return !isRecord(cursor) && !Array.isArray(cursor);
  }

  function validateReferences(incident) {
    const groups = [
      incident.epistemics.facts,
      incident.epistemics.inferences,
      incident.epistemics.unknowns,
      incident.timeline
    ];
    groups.forEach(function (items) {
      items.forEach(function (item) {
        item.refs.forEach(function (reference) {
          if (!referenceResolves(incident, reference)) {
            fail("unresolved incident reference: " + reference);
          }
        });
      });
    });
  }

  function validateBindings(value, keys, path) {
    exactKeys(value, keys, path);
    keys.forEach(function (key) {
      assertPattern(value[key], SHA_PATTERN, path + "." + key);
    });
  }

  function validateCandidate(candidate) {
    safeTree(candidate, "$.learning.regression_candidate", 0, {nodes: 0});
    exactKeys(candidate, CANDIDATE_KEYS, "$.learning.regression_candidate");
    assertLiteral(candidate.schema, CANDIDATE_SCHEMA, "$.learning.regression_candidate.schema");
    assertPattern(candidate.candidate_id, ID_PATTERN, "$.learning.regression_candidate.candidate_id");

    const source = candidate.source;
    exactKeys(source, CANDIDATE_SOURCE_KEYS, "$.learning.regression_candidate.source");
    assertPattern(source.event_digest, SHA_PATTERN, "$.learning.regression_candidate.source.event_digest");
    assertPattern(source.receipt_digest, SHA_PATTERN, "$.learning.regression_candidate.source.receipt_digest");
    validateBindings(source.bindings, CANDIDATE_BINDING_KEYS, "$.learning.regression_candidate.source.bindings");
    assertPinnedBindings(source.bindings, PINNED_CANDIDATE_BINDINGS, "$.learning.regression_candidate.source.bindings");
    const identifierBasis = {
      event_digest: source.event_digest,
      receipt_digest: source.receipt_digest
    };
    assertLiteral(
      candidate.candidate_id,
      "candidate-" + sha256Ascii(canonicalStringify(identifierBasis)).slice(0, 16),
      "$.learning.regression_candidate.candidate_id"
    );

    const event = candidate.event;
    exactKeys(event, EVENT_KEYS, "$.learning.regression_candidate.event");
    assertEnum(event.retention, ["reviewed-categorical", "digest-only"], "$.learning.regression_candidate.event.retention");
    assertLiteral(event.schema, "kingdom.karma.event/v1", "$.learning.regression_candidate.event.schema");
    ["surface", "mechanism", "signal"].forEach(function (key) {
      assertPattern(event[key], TOKEN_PATTERN, "$.learning.regression_candidate.event." + key);
    });
    assertEnum(event.signal_quality, ["confirmed", "ambiguous", "unknown"], "$.learning.regression_candidate.event.signal_quality");
    assertEnum(event.provenance, ["pinned", "unpinned", "unknown"], "$.learning.regression_candidate.event.provenance");
    assertEnum(event.novelty, ["known", "novel", "ambiguous"], "$.learning.regression_candidate.event.novelty");
    assertLiteral(event.purpose, "defensive-regression", "$.learning.regression_candidate.event.purpose");
    assertLiteral(event.scope, "offline-synthetic", "$.learning.regression_candidate.event.scope");
    assertLiteral(event.authority, "none", "$.learning.regression_candidate.event.authority");
    assertInteger(event.evidence_count, 0, 4, "$.learning.regression_candidate.event.evidence_count");

    const expected = candidate.expected;
    exactKeys(expected, EXPECTED_KEYS, "$.learning.regression_candidate.expected");
    assertEnum(expected.status, ["planned", "halted"], "$.learning.regression_candidate.expected.status");
    assertEnum(expected.classification, ["reviewed-categorical", "unmatched-categorical", "uncertain-categorical", "insufficient-categorical"], "$.learning.regression_candidate.expected.classification");
    ["rule_id", "threat_id", "halt_code"].forEach(function (key) {
      assertPattern(expected[key], TOKEN_PATTERN, "$.learning.regression_candidate.expected." + key);
    });
    assertEnum(expected.action, ["allow", "observe", "throttle", "deny", "quarantine", "synthetic-mirror"], "$.learning.regression_candidate.expected.action");
    assertEnum(expected.fallback, ["deny", "quarantine"], "$.learning.regression_candidate.expected.fallback");
    assertInteger(expected.severity, 0, 5, "$.learning.regression_candidate.expected.severity");
    exactKeys(expected.mirror, MIRROR_KEYS, "$.learning.regression_candidate.expected.mirror");
    assertEnum(expected.mirror.mode, ["none", "isolated-no-egress"], "$.learning.regression_candidate.expected.mirror.mode");
    assertInteger(expected.mirror.max_attempts, 0, 1, "$.learning.regression_candidate.expected.mirror.max_attempts");
    assertLiteral(expected.mirror.egress, false, "$.learning.regression_candidate.expected.mirror.egress");

    if (expected.status === "planned") {
      assertLiteral(expected.classification, "reviewed-categorical", "$.learning.regression_candidate.expected.classification");
      assertLiteral(event.retention, "reviewed-categorical", "$.learning.regression_candidate.event.retention");
      assertLiteral(event.signal_quality, "confirmed", "$.learning.regression_candidate.event.signal_quality");
      assertLiteral(event.provenance, "pinned", "$.learning.regression_candidate.event.provenance");
      assertLiteral(event.novelty, "known", "$.learning.regression_candidate.event.novelty");
      assertLiteral(expected.halt_code, "none", "$.learning.regression_candidate.expected.halt_code");
      if (expected.rule_id === "none" || expected.threat_id === "none") {
        fail("$.learning.regression_candidate.expected planned identifiers cannot be none");
      }
      const reviewedEvent = {};
      EVENT_KEYS.forEach(function (key) {
        if (key !== "retention") {
          reviewedEvent[key] = event[key];
        }
      });
      assertLiteral(
        source.event_digest,
        sha256Ascii(canonicalStringify(reviewedEvent)),
        "$.learning.regression_candidate.source.event_digest"
      );
    } else {
      assertLiteral(event.retention, "digest-only", "$.learning.regression_candidate.event.retention");
      ["surface", "mechanism", "signal"].forEach(function (key) {
        assertLiteral(event[key], "withheld-unreviewed", "$.learning.regression_candidate.event." + key);
      });
      assertLiteral(event.signal_quality, "unknown", "$.learning.regression_candidate.event.signal_quality");
      assertLiteral(event.provenance, "unknown", "$.learning.regression_candidate.event.provenance");
      assertLiteral(event.novelty, "ambiguous", "$.learning.regression_candidate.event.novelty");
      assertLiteral(event.evidence_count, 0, "$.learning.regression_candidate.event.evidence_count");
      assertLiteral(expected.action, "quarantine", "$.learning.regression_candidate.expected.action");
      assertLiteral(expected.fallback, "deny", "$.learning.regression_candidate.expected.fallback");
      assertLiteral(expected.severity, 5, "$.learning.regression_candidate.expected.severity");
      assertLiteral(expected.rule_id, "none", "$.learning.regression_candidate.expected.rule_id");
      assertLiteral(expected.threat_id, "none", "$.learning.regression_candidate.expected.threat_id");
      assertLiteral(expected.mirror.mode, "none", "$.learning.regression_candidate.expected.mirror.mode");
      assertLiteral(expected.mirror.max_attempts, 0, "$.learning.regression_candidate.expected.mirror.max_attempts");
      const haltCodes = {
        "unmatched-categorical": "unmatched-selector",
        "uncertain-categorical": "boundary-uncertain",
        "insufficient-categorical": "insufficient-evidence"
      };
      assertLiteral(expected.halt_code, haltCodes[expected.classification], "$.learning.regression_candidate.expected.halt_code");
    }
    validatePinnedProjection(candidate);

    const promotion = candidate.promotion;
    exactKeys(promotion, PROMOTION_KEYS, "$.learning.regression_candidate.promotion");
    assertLiteral(promotion.state, "human-review-required", "$.learning.regression_candidate.promotion.state");
    assertEnum(promotion.eligibility, ["reviewed-match", "blocked-until-mapped"], "$.learning.regression_candidate.promotion.eligibility");
    assertLiteral(promotion.automatic_install, false, "$.learning.regression_candidate.promotion.automatic_install");
    assertLiteral(promotion.classifier_mutated, false, "$.learning.regression_candidate.promotion.classifier_mutated");
    assertLiteral(promotion.authority, "none", "$.learning.regression_candidate.promotion.authority");
    assertLiteral(
      promotion.eligibility,
      expected.status === "planned" ? "reviewed-match" : "blocked-until-mapped",
      "$.learning.regression_candidate.promotion.eligibility"
    );
    assertLiteralArray(candidate.nonclaims, CANDIDATE_NONCLAIMS, "$.learning.regression_candidate.nonclaims");
    assertPattern(candidate.candidate_digest, SHA_PATTERN, "$.learning.regression_candidate.candidate_digest");
    if (digestWithout(candidate, "candidate_digest") !== candidate.candidate_digest) {
      fail("$.learning.regression_candidate.candidate_digest does not match its canonical candidate");
    }
    return candidate;
  }

  function validateKnowledgeItem(item, kind, path) {
    exactKeys(item, KNOWLEDGE_ITEM_KEYS, path);
    assertPattern(item.id, TOKEN_PATTERN, path + ".id");
    assertText(item.statement, 1, 240, path + ".statement");
    assertReferences(item.refs, path + ".refs");
    if (kind === "fact") {
      assertLiteral(item.confidence, "confirmed", path + ".confidence");
      assertEnum(item.resolution, ["replay-verified", "catalog-derived"], path + ".resolution");
    } else if (kind === "inference") {
      assertLiteral(item.confidence, "policy-derived", path + ".confidence");
      assertEnum(item.resolution, ["catalog-derived", "human-review-required"], path + ".resolution");
    } else {
      assertLiteral(item.confidence, "unknown", path + ".confidence");
      assertEnum(item.resolution, ["human-review-required", "outside-source-contract"], path + ".resolution");
    }
  }

  function validateIncident(incident) {
    safeTree(incident, "$", 0, {nodes: 0});
    exactKeys(incident, ROOT_KEYS, "$");
    assertLiteral(incident.schema, INCIDENT_SCHEMA, "$.schema");
    assertLiteral(incident.engine, INCIDENT_ENGINE, "$.engine");
    assertEnum(incident.status, ["ready-for-review", "halted-for-review"], "$.status");
    assertPattern(incident.incident_id, ID_PATTERN, "$.incident_id");

    const source = incident.source;
    exactKeys(source, SOURCE_KEYS, "$.source");
    assertPattern(source.event_digest, SHA_PATTERN, "$.source.event_digest");
    assertPattern(source.receipt_digest, SHA_PATTERN, "$.source.receipt_digest");
    assertEnum(source.source_status, ["planned", "halted"], "$.source.source_status");
    assertEnum(source.receipt_classification, ["reviewed-categorical", "unmatched-categorical", "uncertain-categorical", "insufficient-categorical"], "$.source.receipt_classification");
    validateBindings(source.bindings, INCIDENT_BINDING_KEYS, "$.source.bindings");
    assertPinnedBindings(source.bindings, PINNED_BINDINGS, "$.source.bindings");
    assertLiteral(
      incident.incident_id,
      "incident-" + sha256Ascii(canonicalStringify({
        event_digest: source.event_digest,
        receipt_digest: source.receipt_digest
      })).slice(0, 16),
      "$.incident_id"
    );

    const headline = incident.headline;
    exactKeys(headline, HEADLINE_KEYS, "$.headline");
    assertText(headline.title, 1, 80, "$.headline.title");
    assertInteger(headline.severity, 0, 5, "$.headline.severity");
    assertEnum(headline.disposition, ["reviewed-plan", "boundary-halt"], "$.headline.disposition");
    assertEnum(headline.planned_action, ["allow", "observe", "throttle", "deny", "quarantine", "synthetic-mirror"], "$.headline.planned_action");
    assertText(headline.summary, 1, 240, "$.headline.summary");

    const expectedStatus = source.source_status === "planned" ? "ready-for-review" : "halted-for-review";
    const expectedDisposition = source.source_status === "planned" ? "reviewed-plan" : "boundary-halt";
    assertLiteral(incident.status, expectedStatus, "$.status");
    assertLiteral(headline.disposition, expectedDisposition, "$.headline.disposition");
    if (source.source_status === "planned") {
      assertLiteral(source.receipt_classification, "reviewed-categorical", "$.source.receipt_classification");
    } else if (source.receipt_classification === "reviewed-categorical") {
      fail("$.source.receipt_classification cannot be reviewed-categorical for a halted source");
    }

    const epistemics = incident.epistemics;
    exactKeys(epistemics, EPISTEMIC_KEYS, "$.epistemics");
    assertArray(epistemics.facts, 4, 4, "$.epistemics.facts");
    assertArray(epistemics.inferences, 2, 2, "$.epistemics.inferences");
    assertArray(epistemics.unknowns, 4, 7, "$.epistemics.unknowns");
    epistemics.facts.forEach(function (item, index) {
      validateKnowledgeItem(item, "fact", "$.epistemics.facts[" + index + "]");
    });
    epistemics.inferences.forEach(function (item, index) {
      validateKnowledgeItem(item, "inference", "$.epistemics.inferences[" + index + "]");
    });
    epistemics.unknowns.forEach(function (item, index) {
      validateKnowledgeItem(item, "unknown", "$.epistemics.unknowns[" + index + "]");
    });

    const phases = [
      "categorical-observation", "source-bindings-validated", "receipt-replayed",
      "policy-decision-produced", "human-review-pending"
    ];
    assertArray(incident.timeline, 5, 5, "$.timeline");
    incident.timeline.forEach(function (item, index) {
      const path = "$.timeline[" + index + "]";
      exactKeys(item, TIMELINE_KEYS, path);
      assertLiteral(item.ordinal, index + 1, path + ".ordinal");
      assertLiteral(item.phase, phases[index], path + ".phase");
      assertEnum(item.state, ["complete", "halted", "pending"], path + ".state");
      assertText(item.label, 1, 120, path + ".label");
      assertReferences(item.refs, path + ".refs");
    });

    const kinds = ["primary", "fallback", "verification"];
    assertArray(incident.actions, 3, 3, "$.actions");
    incident.actions.forEach(function (item, index) {
      const path = "$.actions[" + index + "]";
      exactKeys(item, ACTION_KEYS, path);
      assertLiteral(item.rank, index + 1, path + ".rank");
      assertPattern(item.id, TOKEN_PATTERN, path + ".id");
      assertLiteral(item.kind, kinds[index], path + ".kind");
      assertText(item.label, 1, 80, path + ".label");
      assertText(item.rationale, 1, 240, path + ".rationale");
      assertLiteral(item.authority, "human-required", path + ".authority");
      assertLiteral(item.automatic, false, path + ".automatic");
      assertLiteral(item.actual_effect, "none", path + ".actual_effect");
      assertEnum(item.reversibility, ["reversible", "conditional", "not-applicable"], path + ".reversibility");
      assertEnum(item.blast_radius, ["none", "local-bounded", "external-requires-review"], path + ".blast_radius");
      assertChecklist(item.preconditions, path + ".preconditions");
      assertText(item.rollback, 1, 240, path + ".rollback");
      assertChecklist(item.verification, path + ".verification");
      assertLiteral(item.state, "not-executed", path + ".state");
    });

    const learning = incident.learning;
    exactKeys(learning, LEARNING_KEYS, "$.learning");
    exactKeys(learning.threat, THREAT_KEYS, "$.learning.threat");
    assertPattern(learning.threat.id, TOKEN_PATTERN, "$.learning.threat.id");
    assertText(learning.threat.title, 1, 120, "$.learning.threat.title");
    assertEnum(learning.threat.evidence_status, ["observed", "inferred", "unknown"], "$.learning.threat.evidence_status");
    exactKeys(learning.guidance, GUIDANCE_KEYS, "$.learning.guidance");
    GUIDANCE_KEYS.forEach(function (key) {
      assertText(learning.guidance[key], 1, 240, "$.learning.guidance." + key);
    });
    const candidate = validateCandidate(learning.regression_candidate);

    exactKeys(incident.controls, CONTROL_KEYS, "$.controls");
    ["network_calls", "process_spawns", "model_calls", "secret_reads", "filesystem_writes", "external_messages", "engine_retained_records"].forEach(function (key) {
      assertLiteral(incident.controls[key], 0, "$.controls." + key);
    });
    ["authority_granted", "action_executed", "classifier_mutated"].forEach(function (key) {
      assertLiteral(incident.controls[key], false, "$.controls." + key);
    });
    assertLiteralArray(incident.nonclaims, INCIDENT_NONCLAIMS, "$.nonclaims");

    assertLiteral(candidate.source.event_digest, source.event_digest, "$.learning.regression_candidate.source.event_digest");
    assertLiteral(candidate.source.receipt_digest, source.receipt_digest, "$.learning.regression_candidate.source.receipt_digest");
    CANDIDATE_BINDING_KEYS.forEach(function (key) {
      assertLiteral(candidate.source.bindings[key], source.bindings[key], "$.learning.regression_candidate.source.bindings." + key);
    });
    assertLiteral(candidate.expected.status, source.source_status, "$.learning.regression_candidate.expected.status");
    assertLiteral(candidate.expected.classification, source.receipt_classification, "$.learning.regression_candidate.expected.classification");
    assertLiteral(candidate.expected.action, headline.planned_action, "$.learning.regression_candidate.expected.action");
    assertLiteral(candidate.expected.severity, headline.severity, "$.learning.regression_candidate.expected.severity");
    assertLiteral(candidate.expected.threat_id, learning.threat.id, "$.learning.regression_candidate.expected.threat_id");

    validateReferences(incident);

    assertPattern(incident.incident_digest, SHA_PATTERN, "$.incident_digest");
    if (digestWithout(incident, "incident_digest") !== incident.incident_digest) {
      fail("$.incident_digest does not match its canonical incident");
    }
    assertCanonicalEqual(incident, reconstructIncident(candidate), "$");
    return incident;
  }

  function parseCanonicalIncident(text, byteLength) {
    if (!Number.isSafeInteger(byteLength) || byteLength < 1 || byteLength > MAX_FILE_BYTES) {
      fail("incident file must be 1.." + MAX_FILE_BYTES + " bytes");
    }
    if (typeof text !== "string" || text.length !== byteLength) {
      fail("incident file must be ASCII so characters and bytes match exactly");
    }
    for (let index = 0; index < text.length; index += 1) {
      if (text.charCodeAt(index) > 127) {
        fail("incident file must contain canonical ASCII JSON only");
      }
    }
    if (!text.endsWith("\n")) {
      fail("incident file must end with exactly one LF");
    }
    let value;
    try {
      value = JSON.parse(text);
    } catch (error) {
      fail("incident file is not valid JSON");
    }
    safeTree(value, "$", 0, {nodes: 0});
    if (canonicalStringify(value) + "\n" !== text) {
      fail("incident file is not exact sorted-key canonical JSON plus one LF");
    }
    return validateIncident(value);
  }

  function candidateText(candidate) {
    validateCandidate(candidate);
    const text = canonicalStringify(candidate) + "\n";
    if (text.length > MAX_FILE_BYTES) {
      fail("regression candidate exceeds " + MAX_FILE_BYTES + " bytes");
    }
    return text;
  }

  globalThis.IncidentLantern = Object.freeze({
    MAX_FILE_BYTES: MAX_FILE_BYTES,
    INCIDENT_SCHEMA: INCIDENT_SCHEMA,
    CANDIDATE_SCHEMA: CANDIDATE_SCHEMA,
    canonicalStringify: canonicalStringify,
    sha256Ascii: sha256Ascii,
    digestWithout: digestWithout,
    validateCandidate: validateCandidate,
    validateIncident: validateIncident,
    parseCanonicalIncident: parseCanonicalIncident,
    candidateText: candidateText
  });

  function setupDashboard() {
    const fileInput = document.getElementById("incident-file");
    const status = document.getElementById("status");
    const dashboard = document.getElementById("dashboard");
    const summaryFields = document.getElementById("summary-fields");
    const scope = document.getElementById("incident-scope");
    const timeline = document.getElementById("timeline");
    const facts = document.getElementById("facts");
    const inferences = document.getElementById("inferences");
    const unknowns = document.getElementById("unknowns");
    const actions = document.getElementById("actions");
    const learning = document.getElementById("learning");
    const preview = document.getElementById("candidate-preview");
    const download = document.getElementById("download");
    const clear = document.getElementById("clear");
    const clearBottom = document.getElementById("clear-bottom");
    const state = {
      generation: 0,
      incident: null,
      candidate: null,
      candidateText: null
    };

    function node(name, className, text) {
      const result = document.createElement(name);
      if (className) {
        result.className = className;
      }
      if (text !== undefined) {
        result.textContent = String(text);
      }
      return result;
    }

    function dataNode(value) {
      return node("bdi", "", value);
    }

    function setStatus(message, kind) {
      status.textContent = message;
      status.className = "status" + (kind ? " " + kind : "");
    }

    function emptyRenderedContent() {
      [summaryFields, timeline, facts, inferences, unknowns, actions, learning].forEach(function (container) {
        container.replaceChildren();
      });
      scope.textContent = "";
      preview.textContent = "";
      dashboard.hidden = true;
      download.disabled = true;
    }

    function clearAll(message) {
      state.generation += 1;
      state.incident = null;
      state.candidate = null;
      state.candidateText = null;
      fileInput.value = "";
      emptyRenderedContent();
      setStatus(message || "Cleared. Waiting for a local incident file.", "");
    }

    function appendSummary(label, value) {
      const wrapper = node("div");
      wrapper.append(node("dt", "", label), node("dd"));
      wrapper.lastChild.append(dataNode(value));
      summaryFields.append(wrapper);
    }

    function renderKnowledge(container, items) {
      items.forEach(function (item) {
        const entry = node("li");
        entry.append(dataNode(item.statement));
        const meta = node("span", "meta");
        meta.append(
          dataNode(item.confidence),
          document.createTextNode(" · "),
          dataNode(item.resolution),
          document.createTextNode(" · refs: "),
          dataNode(item.refs.join(", "))
        );
        entry.append(meta);
        container.append(entry);
      });
    }

    function appendDefinition(list, label, value) {
      list.append(node("dt", "", label));
      const detail = node("dd");
      detail.append(dataNode(value));
      list.append(detail);
    }

    function renderIncident(incident) {
      emptyRenderedContent();
      appendSummary("Incident", incident.incident_id);
      appendSummary("Status", incident.status);
      appendSummary("Severity", incident.headline.severity + " / 5");
      appendSummary("Disposition", incident.headline.disposition);
      appendSummary("Classification", incident.source.receipt_classification);
      appendSummary("Proposed policy", incident.headline.planned_action);
      appendSummary("Source state", incident.source.source_status);
      appendSummary("Receipt digest", incident.source.receipt_digest);
      scope.textContent = incident.learning.regression_candidate.event.scope;

      incident.timeline.forEach(function (item) {
        const entry = node("li");
        entry.append(
          node("span", "tag", "Step " + item.ordinal + " · " + item.state),
          node("span", "event-title")
        );
        entry.lastChild.append(dataNode(item.label));
        const detail = node("span", "event-detail");
        detail.append(
          dataNode(item.phase),
          document.createTextNode(" · refs: "),
          dataNode(item.refs.join(", "))
        );
        entry.append(detail);
        timeline.append(entry);
      });

      renderKnowledge(facts, incident.epistemics.facts);
      renderKnowledge(inferences, incident.epistemics.inferences);
      renderKnowledge(unknowns, incident.epistemics.unknowns);

      incident.actions.forEach(function (item) {
        const card = node("article", "action-card");
        card.append(node("span", "tag", "Rank " + item.rank + " · " + item.kind));
        const title = node("h3");
        title.append(dataNode(item.label));
        const rationale = node("p", "muted");
        rationale.append(dataNode(item.rationale));
        const details = node("dl");
        appendDefinition(details, "Authority", item.authority);
        appendDefinition(details, "State", item.state);
        appendDefinition(details, "Automatic", String(item.automatic));
        appendDefinition(details, "Actual effect", item.actual_effect);
        appendDefinition(details, "Reversibility", item.reversibility);
        appendDefinition(details, "Blast radius", item.blast_radius);
        appendDefinition(details, "Preconditions", item.preconditions.join("; "));
        appendDefinition(details, "Rollback", item.rollback);
        appendDefinition(details, "Verification", item.verification.join("; "));
        card.append(title, rationale, details);
        actions.append(card);
      });

      const threat = node("article", "learning-card");
      threat.append(node("span", "tag", "Threat model"));
      const threatTitle = node("h3");
      threatTitle.append(dataNode(incident.learning.threat.title));
      const threatDetail = node("p", "muted");
      threatDetail.append(
        document.createTextNode("Evidence: "),
        dataNode(incident.learning.threat.evidence_status),
        document.createTextNode(" · id: "),
        dataNode(incident.learning.threat.id)
      );
      threat.append(threatTitle, threatDetail);

      const guideA = node("article", "learning-card");
      guideA.append(node("span", "tag", "Discover and contain"), node("h3", "", "Shorten the path to a safe decision"));
      const detection = node("p");
      detection.append(node("strong", "", "Detection: "), dataNode(incident.learning.guidance.detection));
      const containment = node("p");
      containment.append(node("strong", "", "Containment: "), dataNode(incident.learning.guidance.containment));
      guideA.append(detection, containment);

      const guideB = node("article", "learning-card");
      guideB.append(node("span", "tag", "Recover and retain"), node("h3", "", "Build the lesson into tomorrow"));
      const recovery = node("p");
      recovery.append(node("strong", "", "Recovery: "), dataNode(incident.learning.guidance.recovery));
      const privacy = node("p");
      privacy.append(node("strong", "", "Privacy output: "), dataNode(incident.learning.guidance.privacy_output));
      guideB.append(recovery, privacy);

      const boundaries = node("article", "learning-card");
      boundaries.append(node("span", "tag", "Nonclaims"), node("h3", "", "What this receipt cannot establish"));
      const list = node("ul");
      incident.nonclaims.forEach(function (claim) {
        const item = node("li");
        item.append(dataNode(claim));
        list.append(item);
      });
      boundaries.append(list);
      learning.append(threat, guideA, guideB, boundaries);

      state.incident = incident;
      state.candidate = incident.learning.regression_candidate;
      state.candidateText = candidateText(state.candidate);
      preview.textContent = state.candidateText;
      download.disabled = false;
      dashboard.hidden = false;
    }

    fileInput.addEventListener("change", async function () {
      state.generation += 1;
      const ticket = state.generation;
      state.incident = null;
      state.candidate = null;
      state.candidateText = null;
      emptyRenderedContent();
      const file = fileInput.files && fileInput.files[0];
      if (!file) {
        setStatus("Waiting for a local incident file.", "");
        return;
      }
      if (file.size < 1 || file.size > MAX_FILE_BYTES) {
        setStatus("Rejected: incident file must be 1.." + MAX_FILE_BYTES + " bytes.", "error");
        return;
      }
      setStatus("Reading and verifying the local incident…", "");
      try {
        const text = await file.text();
        if (ticket !== state.generation) {
          return;
        }
        const incident = parseCanonicalIncident(text, file.size);
        renderIncident(incident);
        setStatus("Self-check passed locally: canonical structure and digests match; origin is not authenticated. No action was executed.", "success");
      } catch (error) {
        if (ticket !== state.generation) {
          return;
        }
        state.incident = null;
        state.candidate = null;
        state.candidateText = null;
        emptyRenderedContent();
        setStatus("Rejected: " + (error instanceof Error ? error.message : "invalid incident"), "error");
      }
    });

    clear.addEventListener("click", function () {
      clearAll();
      fileInput.focus();
    });
    clearBottom.addEventListener("click", function () {
      clearAll();
      fileInput.focus();
    });

    download.addEventListener("click", function () {
      let objectUrl = null;
      let anchor = null;
      try {
        if (!state.incident || !state.candidate || !state.candidateText) {
          fail("no verified regression candidate is loaded");
        }
        const checked = candidateText(state.candidate);
        if (checked !== state.candidateText || checked.length > MAX_FILE_BYTES) {
          fail("candidate bytes changed after verification");
        }
        const parsed = JSON.parse(checked);
        validateCandidate(parsed);
        if (parsed.candidate_digest !== state.candidate.candidate_digest) {
          fail("candidate digest changed after verification");
        }
        const blob = new Blob([checked], {type: "application/json;charset=utf-8"});
        objectUrl = URL.createObjectURL(blob);
        anchor = document.createElement("a");
        anchor.href = objectUrl;
        anchor.download = DOWNLOAD_NAME;
        anchor.hidden = true;
        document.body.append(anchor);
        anchor.click();
        setStatus("Candidate download requested by you. It remains proposal-only and uninstalled.", "success");
      } catch (error) {
        setStatus("Download blocked: " + (error instanceof Error ? error.message : "candidate verification failed"), "error");
      } finally {
        if (anchor) {
          anchor.remove();
        }
        if (objectUrl !== null) {
          URL.revokeObjectURL(objectUrl);
        }
      }
    });
  }

  if (typeof document !== "undefined") {
    setupDashboard();
  }
}());
