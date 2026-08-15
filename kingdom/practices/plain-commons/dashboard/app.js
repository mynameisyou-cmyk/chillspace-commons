(function () {
  "use strict";

  const MAX_FILE_BYTES = 4194304;
  const MAX_DEPTH = 12;
  const MAX_NODES = 60000;
  const SOURCE_SCHEMA = "kingdom.plain-commons-source/v1";
  const RECEIPT_SCHEMA = "kingdom.plain-commons/v1";
  const ENGINE = "plain-commons/1";
  const TOKEN_PATTERN = /^[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?$/;
  const REFERENCE_PATTERN = /^[a-z0-9](?:[a-z0-9._-]{0,94}[a-z0-9])?$/;
  const SHA_PATTERN = /^[0-9a-f]{64}$/;
  const MATCH_PATTERN = /^match-[0-9a-f]{64}$/;
  const URL_PATTERN = /(?:[a-z][a-z0-9+.-]{1,15}:\/\/|(?:https?|mailto|ftp):|www\.|\b[a-z0-9](?:[a-z0-9-]{0,62}\.)+[a-z]{2,63}(?:[\/?:#][^\s]*)?|\b[^\s@]+@[^\s@]+\.[a-z]{2,63}\b)/i;
  const SECRET_KEY_FORMS = new Set([
    "apikey", "apitoken", "bearer", "credential", "credentials", "mnemonic",
    "password", "privatekey", "secret", "seed", "token"
  ]);

  // Replaced only after the backend, schemas, and golden receipt are final.
  const PINNED_BINDINGS = Object.freeze({
    engine_sha256: "46d77d7b9dc080b208b1c5ab4ae9a7b857bab5e631146cb281f8c5666479d7c2",
    receipt_schema_sha256: "b522a9795c1064c156c7eeaf3c9bcc6d6cb814e65fceabb6c1ee3f3191f0133c",
    source_schema_sha256: "d8e1da607b0c3951b6ed4adb6f9b1c4ee3ccbfd42cf33e58aeecd7e0aecfdf3d"
  });

  const SELECTION = Object.freeze({
    eligibility: "active-consent-exact-tag-cross-participant",
    interpretation: "canonical-not-merit",
    ordering: "tag-need-participant-id-offer-participant-id"
  });

  const CONTROLS = Object.freeze({
    authority: "none",
    boost_effects: 0,
    click_effects: 0,
    clock_effects: 0,
    contact_effects: 0,
    dispatch_effects: 0,
    filesystem_write_effects: 0,
    impression_effects: 0,
    model_effects: 0,
    network_effects: 0,
    payment_effects: 0,
    personalization_effects: 0,
    price_effects: 0,
    process_effects: 0,
    profile_effects: 0,
    random_effects: 0,
    rank_effects: 0,
    score_effects: 0,
    tracking_effects: 0,
    urgency_effects: 0
  });

  const FACTS = Object.freeze([
    "The receipt was rebuilt from the included closed source snapshot.",
    "Every match joins active introduction-only declarations with equal tags and different participant references.",
    "Evidence is visible in the included source and does not affect eligibility or ordering.",
    "Match order is canonical and does not express merit."
  ]);
  const UNKNOWNS = Object.freeze([
    "Whether any statement or evidence claim is true.",
    "Whether a participant reference identifies any particular person.",
    "Whether any need or offer remains available after the source snapshot.",
    "Whether caller-supplied source hashes were independently witnessed or authenticated."
  ]);
  const NONCLAIMS = Object.freeze([
    "This receipt does not authenticate identity, provenance, event time, truth, availability, or continuing consent.",
    "It does not recommend, endorse, score, rank, boost, price, or personalize any declaration.",
    "It does not contact anyone, dispatch work, move money, or grant authority.",
    "It performs no network call, tracking, impression logging, click logging, model call, or filesystem write.",
    "Its hashes establish deterministic internal integrity only, not independent provenance."
  ]);

  const RECEIPT_KEYS = Object.freeze([
    "schema", "engine", "bindings", "source_sha256", "source", "selection",
    "summary", "matches", "epistemics", "controls", "nonclaims", "receipt_sha256"
  ]);
  const SUMMARY_KEYS = Object.freeze([
    "total_declarations", "active_declarations", "withdrawn_declarations",
    "active_needs", "active_offers", "matches", "matched_declarations",
    "unmatched_declarations"
  ]);
  const MATCH_KEYS = Object.freeze([
    "match_id", "tag", "need_declaration_id", "need_participant_ref",
    "offer_declaration_id", "offer_participant_ref", "reason", "authority"
  ]);
  const DECLARATION_KEYS = Object.freeze([
    "declaration_id", "participant_ref", "side", "tag", "statement", "state",
    "consent", "source", "evidence"
  ]);
  const SOURCE_REFERENCE_KEYS = Object.freeze([
    "kind", "schema", "reference", "event_seq", "event_sha256", "chain_head_sha256"
  ]);
  const BINDING_KEYS = Object.freeze([
    "engine_sha256", "source_schema_sha256", "receipt_schema_sha256"
  ]);
  const EPISTEMIC_KEYS = Object.freeze(["facts", "inferences", "unknowns"]);
  const SELF_EVIDENCE_KEYS = Object.freeze(["evidence_id", "type", "note"]);
  const ARTIFACT_EVIDENCE_KEYS = Object.freeze(["evidence_id", "type", "note", "sha256"]);
  const ATTESTATION_EVIDENCE_KEYS = Object.freeze(["evidence_id", "type", "note", "reference"]);

  function fail(message) {
    throw new Error(message);
  }

  function isRecord(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value) &&
      Object.getPrototypeOf(value) === Object.prototype;
  }

  function exactKeys(value, expected, path) {
    if (!isRecord(value)) {
      fail(path + " must be an object");
    }
    const actual = Object.keys(value).sort();
    const wanted = [...expected].sort();
    if (actual.length !== wanted.length || actual.some(function (key, index) {
      return key !== wanted[index];
    })) {
      fail(path + " has an unexpected shape");
    }
  }

  function assertLiteral(value, expected, path) {
    if (value !== expected) {
      fail(path + " has an unexpected value");
    }
  }

  function assertPattern(value, pattern, path) {
    if (typeof value !== "string" || !pattern.test(value)) {
      fail(path + " has an invalid format");
    }
  }

  function assertInteger(value, minimum, maximum, path) {
    if (!Number.isSafeInteger(value) || value < minimum || value > maximum) {
      fail(path + " must be an integer from " + minimum + " to " + maximum);
    }
  }

  function assertArray(value, minimum, maximum, path) {
    if (!Array.isArray(value) || value.length < minimum || value.length > maximum) {
      fail(path + " must contain " + minimum + ".." + maximum + " items");
    }
  }

  function assertText(value, maximum, path) {
    if (typeof value !== "string" || [...value].length < 1 || [...value].length > maximum || value.trim() !== value) {
      fail(path + " must contain 1.." + maximum + " characters");
    }
    if (/[\p{Cc}\p{Cf}]/u.test(value)) {
      fail(path + " contains unsafe control characters");
    }
    if (value.includes("<") || value.includes(">") || URL_PATTERN.test(value)) {
      fail(path + " contains URL- or markup-shaped text");
    }
  }

  function secretShapedKey(key) {
    if (typeof key !== "string") return true;
    const normalized = key.toLocaleLowerCase("en").replace(/[^a-z0-9]/g, "");
    if (SECRET_KEY_FORMS.has(normalized)) return true;
    return [
      "apikey", "apitoken", "bearer", "credential", "mnemonic", "password",
      "privatekey", "secret", "token"
    ].some(function (form) { return normalized.endsWith(form); });
  }

  function assertLiteralArray(value, expected, path) {
    if (!Array.isArray(value) || value.length !== expected.length || value.some(function (item, index) {
      return item !== expected[index];
    })) {
      fail(path + " does not match the pinned reviewed build");
    }
  }

  function safeTree(value, path, depth, state) {
    if (depth > MAX_DEPTH) {
      fail(path + " exceeds the maximum nesting depth");
    }
    state.nodes += 1;
    if (state.nodes > MAX_NODES) {
      fail("receipt contains too many values");
    }
    if (isRecord(value)) {
      Object.keys(value).forEach(function (key) {
        if (!/^[A-Za-z][A-Za-z0-9_]*$/.test(key) || secretShapedKey(key)) {
          fail(path + " contains a forbidden field name");
        }
        safeTree(value[key], path + "." + key, depth + 1, state);
      });
      return;
    }
    if (Array.isArray(value)) {
      if (value.length > 4096) {
        fail(path + " contains too many items");
      }
      value.forEach(function (item, index) {
        safeTree(item, path + "[" + index + "]", depth + 1, state);
      });
      return;
    }
    if (typeof value === "string") {
      if (value.length > 1000 || /[\u0000-\u001f\u007f]|[\u202a-\u202e\u2066-\u2069]/.test(value)) {
        fail(path + " contains unsafe text");
      }
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
    if (value === null) return "null";
    if (value === true) return "true";
    if (value === false) return "false";
    if (typeof value === "number" && Number.isSafeInteger(value)) return String(value);
    if (typeof value === "string") return quoteAscii(value);
    if (Array.isArray(value)) return "[" + value.map(canonicalStringify).join(",") + "]";
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
      if (code > 127) fail("SHA-256 input must be canonical ASCII");
      bytes.push(code);
    }
    const bitLength = bytes.length * 8;
    bytes.push(128);
    while (bytes.length % 64 !== 56) bytes.push(0);
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
      if (key !== field) projection[key] = value[key];
    });
    return sha256Ascii(canonicalStringify(projection));
  }

  function canonicalEqual(actual, expected, path) {
    if (canonicalStringify(actual) !== canonicalStringify(expected)) {
      fail(path + " does not match the pinned reviewed build");
    }
  }

  function validateEvidence(item, path, evidenceIds) {
    if (!isRecord(item)) fail(path + " must be an object");
    if (item.type === "self-declaration") {
      exactKeys(item, SELF_EVIDENCE_KEYS, path);
    } else if (item.type === "artifact-digest") {
      exactKeys(item, ARTIFACT_EVIDENCE_KEYS, path);
      assertPattern(item.sha256, SHA_PATTERN, path + ".sha256");
    } else if (item.type === "attestation-reference") {
      exactKeys(item, ATTESTATION_EVIDENCE_KEYS, path);
      assertPattern(item.reference, REFERENCE_PATTERN, path + ".reference");
    } else {
      fail(path + ".type has an unexpected value");
    }
    assertPattern(item.evidence_id, TOKEN_PATTERN, path + ".evidence_id");
    assertText(item.note, 200, path + ".note");
    if (evidenceIds.has(item.evidence_id)) fail(path + ".evidence_id is duplicated");
    evidenceIds.add(item.evidence_id);
  }

  function validateSource(source) {
    exactKeys(source, ["schema", "declarations"], "$.source");
    assertLiteral(source.schema, SOURCE_SCHEMA, "$.source.schema");
    assertArray(source.declarations, 0, 128, "$.source.declarations");
    const declarationIds = new Set();
    const evidenceIds = new Set();
    const slots = new Set();
    source.declarations.forEach(function (item, index) {
      const path = "$.source.declarations[" + index + "]";
      exactKeys(item, DECLARATION_KEYS, path);
      assertPattern(item.declaration_id, TOKEN_PATTERN, path + ".declaration_id");
      assertPattern(item.participant_ref, TOKEN_PATTERN, path + ".participant_ref");
      if (item.side !== "need" && item.side !== "offer") fail(path + ".side has an unexpected value");
      assertPattern(item.tag, TOKEN_PATTERN, path + ".tag");
      if (item.tag.includes("--")) fail(path + ".tag has an invalid format");
      assertText(item.statement, 280, path + ".statement");
      if (item.state !== "active" && item.state !== "withdrawn") fail(path + ".state has an unexpected value");
      const expectedConsent = item.state === "active" ? "introduction-only" : "withdrawn";
      assertLiteral(item.consent, expectedConsent, path + ".consent");
      exactKeys(item.source, SOURCE_REFERENCE_KEYS, path + ".source");
      if (item.source.kind === "synthetic-fixture") {
        assertLiteral(item.source.schema, "kingdom.plain-commons-synthetic/v1", path + ".source.schema");
      } else if (item.source.kind === "civilisation-event-projection") {
        assertLiteral(item.source.schema, "kingdom.civilisation/v1", path + ".source.schema");
      } else {
        fail(path + ".source.kind has an unexpected value");
      }
      assertPattern(item.source.reference, REFERENCE_PATTERN, path + ".source.reference");
      assertInteger(item.source.event_seq, 0, 1000000, path + ".source.event_seq");
      assertPattern(item.source.event_sha256, SHA_PATTERN, path + ".source.event_sha256");
      assertPattern(item.source.chain_head_sha256, SHA_PATTERN, path + ".source.chain_head_sha256");
      assertArray(item.evidence, 1, 8, path + ".evidence");
      item.evidence.forEach(function (evidence, evidenceIndex) {
        validateEvidence(evidence, path + ".evidence[" + evidenceIndex + "]", evidenceIds);
      });
      const sortedEvidence = [...item.evidence].sort(function (left, right) {
        return left.evidence_id.localeCompare(right.evidence_id, "en");
      });
      canonicalEqual(item.evidence, sortedEvidence, path + ".evidence");
      if (declarationIds.has(item.declaration_id)) fail(path + ".declaration_id is duplicated");
      declarationIds.add(item.declaration_id);
      const slot = item.participant_ref + "\u001f" + item.side + "\u001f" + item.tag;
      if (slots.has(slot)) fail(path + " duplicates a participant-side-tag slot");
      slots.add(slot);
    });
    const sorted = [...source.declarations].sort(function (left, right) {
      return left.participant_ref.localeCompare(right.participant_ref, "en") ||
        left.side.localeCompare(right.side, "en") ||
        left.tag.localeCompare(right.tag, "en") ||
        left.declaration_id.localeCompare(right.declaration_id, "en");
    });
    canonicalEqual(source.declarations, sorted, "$.source.declarations");
    return source;
  }

  function matchDigestInput(need, offer) {
    return {
      schema: "kingdom.plain-commons-match-id/v1",
      tag: need.tag,
      need: {
        declaration_id: need.declaration_id,
        participant_ref: need.participant_ref
      },
      offer: {
        declaration_id: offer.declaration_id,
        participant_ref: offer.participant_ref
      },
    };
  }

  function buildMatches(source) {
    const needs = source.declarations.filter(function (item) {
      return item.state === "active" && item.consent === "introduction-only" && item.side === "need";
    });
    const offers = source.declarations.filter(function (item) {
      return item.state === "active" && item.consent === "introduction-only" && item.side === "offer";
    });
    const matches = [];
    needs.forEach(function (need) {
      offers.forEach(function (offer) {
        if (need.tag === offer.tag && need.participant_ref !== offer.participant_ref) {
          matches.push({
            match_id: "match-" + sha256Ascii(canonicalStringify(matchDigestInput(need, offer))),
            tag: need.tag,
            need_declaration_id: need.declaration_id,
            need_participant_ref: need.participant_ref,
            offer_declaration_id: offer.declaration_id,
            offer_participant_ref: offer.participant_ref,
            reason: "active-introduction-only-exact-tag-cross-participant",
            authority: "none"
          });
        }
      });
    });
    return matches.sort(function (left, right) {
      return left.tag.localeCompare(right.tag, "en") ||
        left.need_participant_ref.localeCompare(right.need_participant_ref, "en") ||
        left.need_declaration_id.localeCompare(right.need_declaration_id, "en") ||
        left.offer_participant_ref.localeCompare(right.offer_participant_ref, "en") ||
        left.offer_declaration_id.localeCompare(right.offer_declaration_id, "en");
    });
  }

  function buildSummary(source, matches) {
    const active = source.declarations.filter(function (item) { return item.state === "active"; });
    const matched = new Set();
    matches.forEach(function (item) {
      matched.add(item.need_declaration_id);
      matched.add(item.offer_declaration_id);
    });
    return {
      total_declarations: source.declarations.length,
      active_declarations: active.length,
      withdrawn_declarations: source.declarations.length - active.length,
      active_needs: active.filter(function (item) { return item.side === "need"; }).length,
      active_offers: active.filter(function (item) { return item.side === "offer"; }).length,
      matches: matches.length,
      matched_declarations: matched.size,
      unmatched_declarations: active.length - matched.size
    };
  }

  function reconstructReceipt(source) {
    validateSource(source);
    const matches = buildMatches(source);
    const receipt = {
      schema: RECEIPT_SCHEMA,
      engine: ENGINE,
      bindings: {...PINNED_BINDINGS},
      source_sha256: sha256Ascii(canonicalStringify(source)),
      source: source,
      selection: {...SELECTION},
      summary: buildSummary(source, matches),
      matches: matches,
      epistemics: {
        facts: [...FACTS],
        inferences: [],
        unknowns: [...UNKNOWNS]
      },
      controls: {...CONTROLS},
      nonclaims: [...NONCLAIMS]
    };
    receipt.receipt_sha256 = sha256Ascii(canonicalStringify(receipt));
    return receipt;
  }

  function validateReceipt(receipt) {
    exactKeys(receipt, RECEIPT_KEYS, "$");
    assertLiteral(receipt.schema, RECEIPT_SCHEMA, "$.schema");
    assertLiteral(receipt.engine, ENGINE, "$.engine");
    exactKeys(receipt.bindings, BINDING_KEYS, "$.bindings");
    canonicalEqual(receipt.bindings, PINNED_BINDINGS, "$.bindings");
    assertPattern(receipt.source_sha256, SHA_PATTERN, "$.source_sha256");
    validateSource(receipt.source);
    if (sha256Ascii(canonicalStringify(receipt.source)) !== receipt.source_sha256) {
      fail("$.source_sha256 does not match the canonical source");
    }
    exactKeys(receipt.selection, ["eligibility", "interpretation", "ordering"], "$.selection");
    canonicalEqual(receipt.selection, SELECTION, "$.selection");
    exactKeys(receipt.summary, SUMMARY_KEYS, "$.summary");
    SUMMARY_KEYS.forEach(function (key) {
      assertInteger(receipt.summary[key], 0, key === "matches" ? 4096 : 128, "$.summary." + key);
    });
    assertArray(receipt.matches, 0, 4096, "$.matches");
    receipt.matches.forEach(function (item, index) {
      const path = "$.matches[" + index + "]";
      exactKeys(item, MATCH_KEYS, path);
      assertPattern(item.match_id, MATCH_PATTERN, path + ".match_id");
      assertPattern(item.tag, TOKEN_PATTERN, path + ".tag");
      assertPattern(item.need_declaration_id, TOKEN_PATTERN, path + ".need_declaration_id");
      assertPattern(item.need_participant_ref, TOKEN_PATTERN, path + ".need_participant_ref");
      assertPattern(item.offer_declaration_id, TOKEN_PATTERN, path + ".offer_declaration_id");
      assertPattern(item.offer_participant_ref, TOKEN_PATTERN, path + ".offer_participant_ref");
      assertLiteral(item.reason, "active-introduction-only-exact-tag-cross-participant", path + ".reason");
      assertLiteral(item.authority, "none", path + ".authority");
    });
    exactKeys(receipt.epistemics, EPISTEMIC_KEYS, "$.epistemics");
    assertLiteralArray(receipt.epistemics.facts, FACTS, "$.epistemics.facts");
    assertLiteralArray(receipt.epistemics.inferences, [], "$.epistemics.inferences");
    assertLiteralArray(receipt.epistemics.unknowns, UNKNOWNS, "$.epistemics.unknowns");
    exactKeys(receipt.controls, Object.keys(CONTROLS), "$.controls");
    canonicalEqual(receipt.controls, CONTROLS, "$.controls");
    assertLiteralArray(receipt.nonclaims, NONCLAIMS, "$.nonclaims");
    assertPattern(receipt.receipt_sha256, SHA_PATTERN, "$.receipt_sha256");
    if (digestWithout(receipt, "receipt_sha256") !== receipt.receipt_sha256) {
      fail("$.receipt_sha256 does not match the canonical receipt");
    }
    canonicalEqual(receipt, reconstructReceipt(receipt.source), "$");
    return receipt;
  }

  function parseCanonicalReceipt(text, byteLength) {
    if (!Number.isSafeInteger(byteLength) || byteLength < 1 || byteLength > MAX_FILE_BYTES) {
      fail("receipt file must be 1.." + MAX_FILE_BYTES + " bytes");
    }
    if (typeof text !== "string" || text.length !== byteLength) {
      fail("receipt file must be canonical ASCII JSON");
    }
    for (let index = 0; index < text.length; index += 1) {
      if (text.charCodeAt(index) > 127) fail("receipt file must be canonical ASCII JSON");
    }
    if (!text.endsWith("\n")) fail("receipt file must end with exactly one LF");
    let receipt;
    try {
      receipt = JSON.parse(text);
    } catch (error) {
      fail("receipt file is not valid JSON");
    }
    safeTree(receipt, "$", 0, {nodes: 0});
    if (canonicalStringify(receipt) + "\n" !== text) {
      fail("receipt file must be exact sorted-key canonical JSON plus one LF");
    }
    return validateReceipt(receipt);
  }

  const api = Object.freeze({
    MAX_FILE_BYTES: MAX_FILE_BYTES,
    SOURCE_SCHEMA: SOURCE_SCHEMA,
    RECEIPT_SCHEMA: RECEIPT_SCHEMA,
    ENGINE: ENGINE,
    PINNED_BINDINGS: PINNED_BINDINGS,
    canonicalStringify: canonicalStringify,
    sha256Ascii: sha256Ascii,
    digestWithout: digestWithout,
    validateSource: validateSource,
    buildMatches: buildMatches,
    buildSummary: buildSummary,
    reconstructReceipt: reconstructReceipt,
    validateReceipt: validateReceipt,
    parseCanonicalReceipt: parseCanonicalReceipt
  });
  globalThis.PlainCommonsDashboard = api;

  function setupDashboard() {
    if (typeof document === "undefined") return;
    const fileInput = document.getElementById("receipt-file");
    const clearButton = document.getElementById("clear-button");
    const status = document.getElementById("status");
    const emptyState = document.getElementById("empty-state");
    const dashboard = document.getElementById("dashboard");
    const matchesNode = document.getElementById("matches");
    const noMatches = document.getElementById("no-matches");
    const unknownsNode = document.getElementById("unknowns");
    const controlsNode = document.getElementById("controls");
    const state = {generation: 0, receipt: null};

    function node(name, className, content) {
      const result = document.createElement(name);
      if (className) result.className = className;
      if (content !== undefined) result.textContent = String(content);
      return result;
    }

    function bdi(content, className) {
      return node("bdi", className || "", content);
    }

    function setStatus(message, kind) {
      status.textContent = message;
      if (kind) status.dataset.kind = kind;
      else delete status.dataset.kind;
    }

    function clearChildren(element) {
      while (element.firstChild) element.removeChild(element.firstChild);
    }

    function evidenceList(declaration) {
      const list = node("ul", "evidence");
      declaration.evidence.forEach(function (item) {
        const line = node("li");
        const type = item.type.replaceAll("-", " ");
        line.append(bdi(type + ": "));
        line.append(bdi(item.note));
        if (item.sha256) line.append(bdi(" · sha256 " + item.sha256.slice(0, 12) + "...", "mono"));
        if (item.reference) line.append(bdi(" · ref " + item.reference, "mono"));
        list.append(line);
      });
      return list;
    }

    function declarationCard(declaration, label) {
      const card = node("div", "declaration");
      card.append(node("span", "declaration__side", label));
      const title = node("h4");
      title.append(bdi(declaration.participant_ref));
      card.append(title);
      const statement = node("p");
      statement.append(bdi(declaration.statement));
      card.append(statement);
      card.append(evidenceList(declaration));
      return card;
    }

    function renderMatch(match, declarations) {
      const card = node("article", "match-card");
      const top = node("div", "match-card__top");
      top.append(bdi(match.tag, "tag"));
      top.append(bdi(match.match_id, "match-card__id mono"));
      card.append(top);

      const pair = node("div", "pair");
      pair.append(declarationCard(declarations.get(match.need_declaration_id), "ASK"));
      pair.append(node("span", "pair__meets", "↔"));
      pair.append(declarationCard(declarations.get(match.offer_declaration_id), "DECLARE"));
      card.append(pair);
      card.append(node("p", "match-card__why", "Why this appears: both active declarations chose introduction-only consent and share the exact tag."));
      return card;
    }

    function render(receipt) {
      const declarations = new Map(receipt.source.declarations.map(function (item) {
        return [item.declaration_id, item];
      }));
      document.getElementById("metric-matches").textContent = String(receipt.summary.matches);
      document.getElementById("metric-active").textContent = String(receipt.summary.active_declarations);
      document.getElementById("metric-withdrawn").textContent = String(receipt.summary.withdrawn_declarations);
      document.getElementById("receipt-id").textContent = "receipt sha256 " + receipt.receipt_sha256;

      clearChildren(matchesNode);
      receipt.matches.forEach(function (match) {
        matchesNode.append(renderMatch(match, declarations));
      });
      noMatches.hidden = receipt.matches.length !== 0;

      clearChildren(unknownsNode);
      receipt.epistemics.unknowns.forEach(function (unknown) {
        const item = node("li");
        item.append(bdi(unknown));
        unknownsNode.append(item);
      });

      clearChildren(controlsNode);
      Object.keys(receipt.controls).sort().forEach(function (key) {
        const chip = node("div", "control-chip");
        chip.append(node("span", "", key.replaceAll("_effects", "").replaceAll("_", " ")));
        chip.append(node("strong", "mono", String(receipt.controls[key])));
        controlsNode.append(chip);
      });

      emptyState.hidden = true;
      dashboard.hidden = false;
      clearButton.disabled = false;
      setStatus("Receipt survived exact local reconstruction. Still not proof of external truth or origin.", "success");
    }

    function reset() {
      state.generation += 1;
      state.receipt = null;
      fileInput.value = "";
      dashboard.hidden = true;
      emptyState.hidden = false;
      clearButton.disabled = true;
      clearChildren(matchesNode);
      clearChildren(unknownsNode);
      clearChildren(controlsNode);
      setStatus("Waiting quietly. No need means no targeting.");
    }

    fileInput.addEventListener("change", function () {
      state.generation += 1;
      const generation = state.generation;
      const file = fileInput.files && fileInput.files[0];
      if (!file) {
        reset();
        return;
      }
      if (!Number.isSafeInteger(file.size) || file.size < 1 || file.size > MAX_FILE_BYTES) {
        dashboard.hidden = true;
        emptyState.hidden = false;
        clearButton.disabled = false;
        setStatus("Receipt rejected: file size is outside the local review limit.", "error");
        return;
      }
      const reader = new FileReader();
      reader.addEventListener("load", function () {
        if (generation !== state.generation) return;
        try {
          const receipt = parseCanonicalReceipt(String(reader.result), file.size);
          state.receipt = receipt;
          render(receipt);
        } catch (error) {
          state.receipt = null;
          dashboard.hidden = true;
          emptyState.hidden = false;
          clearButton.disabled = false;
          setStatus("Receipt rejected: " + error.message, "error");
        }
      });
      reader.addEventListener("error", function () {
        if (generation !== state.generation) return;
        setStatus("Receipt rejected: the local file could not be read.", "error");
      });
      reader.readAsText(file, "utf-8");
    });

    clearButton.addEventListener("click", reset);
  }

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", setupDashboard, {once: true});
    } else {
      setupDashboard();
    }
  }
}());
