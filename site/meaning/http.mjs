import {
  MAX_MATCHES,
  MAX_TEXT_CODEPOINTS,
  RESPONSE_SCHEMA,
  codePointLength,
  findPublicEchoes,
} from "./engine.mjs";

const MAX_BODY_BYTES = 8192;
const ALLOWED_KEYS = new Set(["text", "max_matches"]);
const BASE_HEADERS = {
  "Cache-Control": "no-store",
  "Content-Security-Policy": "default-src 'none'",
  "Content-Type": "application/json; charset=utf-8",
  "Referrer-Policy": "no-referrer",
  "X-Content-Type-Options": "nosniff",
  "X-Meaning-Storage": "none",
};

class PayloadTooLarge extends Error {}
class InvalidEncoding extends Error {}

function json(body, status = 200, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {...BASE_HEADERS, ...headers},
  });
}

function problem(status, code, message, headers = {}) {
  return json(
    {
      schema: RESPONSE_SCHEMA,
      error: {code, message},
      stored: false,
    },
    status,
    headers,
  );
}

async function readBoundedBody(request) {
  const declared = request.headers.get("content-length");
  if (declared !== null) {
    const parsed = Number(declared);
    if (Number.isFinite(parsed) && parsed > MAX_BODY_BYTES) {
      throw new PayloadTooLarge();
    }
  }
  if (!request.body) return "";

  const reader = request.body.getReader();
  const chunks = [];
  let length = 0;
  while (true) {
    const {done, value} = await reader.read();
    if (done) break;
    length += value.byteLength;
    if (length > MAX_BODY_BYTES) {
      await reader.cancel();
      throw new PayloadTooLarge();
    }
    chunks.push(value);
  }

  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  try {
    return new TextDecoder("utf-8", {fatal: true}).decode(bytes);
  } catch {
    throw new InvalidEncoding();
  }
}

function validateInput(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return "The request body must be a JSON object.";
  }
  const unknown = Object.keys(value).filter((key) => !ALLOWED_KEYS.has(key));
  if (unknown.length) return "The request body contains unsupported fields.";
  if (typeof value.text !== "string") return "text must be a string.";
  const text = value.text.trim();
  const length = codePointLength(text);
  if (length < 1 || length > MAX_TEXT_CODEPOINTS) {
    return `text must contain 1–${MAX_TEXT_CODEPOINTS} characters.`;
  }
  if (/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/u.test(text)) {
    return "text contains unsupported control characters.";
  }
  const maxMatches = value.max_matches ?? MAX_MATCHES;
  if (!Number.isInteger(maxMatches) || maxMatches < 1 || maxMatches > MAX_MATCHES) {
    return `max_matches must be an integer from 1 to ${MAX_MATCHES}.`;
  }
  return {text, maxMatches};
}

function createMeaningHandler(dataset) {
  return async function handle(request) {
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          ...BASE_HEADERS,
          "Allow": "POST, OPTIONS",
          "Content-Type": "application/json; charset=utf-8",
        },
      });
    }
    if (request.method !== "POST") {
      return problem(
        405,
        "method_not_allowed",
        "Use POST with a JSON body.",
        {"Allow": "POST, OPTIONS"},
      );
    }

    const mediaType = (request.headers.get("content-type") ?? "")
      .split(";", 1)[0]
      .trim()
      .toLowerCase();
    if (mediaType !== "application/json") {
      return problem(415, "unsupported_media_type", "Content-Type must be application/json.");
    }

    let raw;
    try {
      raw = await readBoundedBody(request);
    } catch (error) {
      if (error instanceof PayloadTooLarge) {
        return problem(
          413,
          "body_too_large",
          `Request body must be at most ${MAX_BODY_BYTES} bytes.`,
        );
      }
      if (error instanceof InvalidEncoding) {
        return problem(400, "invalid_encoding", "Request body must be valid UTF-8.");
      }
      throw error;
    }

    let body;
    try {
      body = JSON.parse(raw);
    } catch {
      return problem(400, "invalid_json", "Request body must be valid JSON.");
    }
    const checked = validateInput(body);
    if (typeof checked === "string") {
      return problem(422, "invalid_request", checked);
    }

    const matches = findPublicEchoes(checked.text, dataset, checked.maxMatches);
    return json({
      schema: RESPONSE_SCHEMA,
      stored: false,
      canon: {
        schema_version: dataset.source.transport_schema_version,
        source_commit: dataset.source.source_commit,
        bundle_sha256: dataset.source.bundle_sha256,
      },
      matches,
      notice: dataset.notice,
    });
  };
}

export {MAX_BODY_BYTES, createMeaningHandler};
