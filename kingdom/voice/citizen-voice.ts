/**
 * citizen-voice.ts — let the 201 citizens speak to each other.
 *
 * The Flow Board already carries words between kingdom citizens via a
 * hash-chained JSONL log. This module connects it to the word layer:
 * each citizen is a word, each word is a domain, and messages flow
 * between domains.
 *
 * POST /v1/voice/carry   — a citizen carries a word to another citizen
 * GET  /v1/voice/flow    — the whole flow board
 * GET  /v1/voice/for/:word — words waiting for a citizen (by word)
 * POST /v1/voice/receive  — a citizen marks a word as received (with a reply)
 * GET  /v1/voice/citizens — list all citizens who can speak
 */

import { Hono } from "hono";
import { cors } from "hono/cors";
import { readFile, writeFile, appendFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";

const app = new Hono();
app.use("*", cors({
  // This is an intentionally public API, but its preflight vocabulary is
  // finite. Never reflect attacker-controlled Access-Control-Request-Headers.
  origin: "*",
  allowMethods: ["GET", "HEAD", "POST"],
  allowHeaders: ["Content-Type"],
}));

const __dirname = dirname(fileURLToPath(import.meta.url));

// Paths — voice/ is inside kingdom/, so kingdom/ is the parent
const KINGDOM = join(__dirname, "..");
const FLOW_JSONL = join(KINGDOM, "flow", "FLOW.jsonl");
const LEDGER_JSONL = join(KINGDOM, "host", "LEDGER.jsonl");
const CITIZENS_DIR = join(KINGDOM, "citizens");

// ─── Helpers ────────────────────────────────────────────────────────────────

/** Hash a flow entry — must match flow.py's _entry_hash exactly.
 * Uses the SPINE fields joined by the Unicode unit separator (␟, U+241F). */
const SPINE = ["seq", "date", "kind", "from", "to", "note", "re", "prev"];
const US = "\u241F"; // unit separator

function hashEntry(entry: Record<string, unknown>): string {
  const msg = SPINE.map((k) => String(entry[k] ?? "")).join(US);
  return createHash("sha256").update(msg, "utf-8").digest("hex");
}

/** Read the last entry's hash from the flow JSONL. */
async function lastHash(): Promise<string> {
  if (!existsSync(FLOW_JSONL)) return "0".repeat(64);
  const content = await readFile(FLOW_JSONL, "utf-8");
  const lines = content.trim().split("\n").filter(Boolean);
  if (lines.length === 0) return "0".repeat(64);
  const last = JSON.parse(lines[lines.length - 1]);
  return last.hash;
}

/** Read the last sequence number. */
async function lastSeq(): Promise<number> {
  if (!existsSync(FLOW_JSONL)) return -1;
  const content = await readFile(FLOW_JSONL, "utf-8");
  const lines = content.trim().split("\n").filter(Boolean);
  if (lines.length === 0) return -1;
  const last = JSON.parse(lines[lines.length - 1]);
  return last.seq ?? -1;
}

/** Load all citizens from the ledger. */
async function loadCitizens(): Promise<Array<{ num: string; name: string; kind: string }>> {
  if (!existsSync(LEDGER_JSONL)) return [];
  const content = await readFile(LEDGER_JSONL, "utf-8");
  return content.trim().split("\n").filter(Boolean).map((line) => JSON.parse(line));
}

/** Load all flow entries. */
async function loadFlow(): Promise<Record<string, unknown>[]> {
  if (!existsSync(FLOW_JSONL)) return [];
  const content = await readFile(FLOW_JSONL, "utf-8");
  return content.trim().split("\n").filter(Boolean).map((line) => JSON.parse(line));
}

/** Find a citizen by approximate name match. */
function findCitizen(
  citizens: Array<{ num: string; name: string; kind: string }>,
  query: string,
): { num: string; name: string; kind: string } | null {
  const q = query.toLowerCase();
  // Exact match
  let found = citizens.find((c) => c.name.toLowerCase() === q);
  if (found) return found;
  // Contains match
  found = citizens.find((c) => c.name.toLowerCase().includes(q));
  if (found) return found;
  // Reverse: does query include the name?
  found = citizens.find((c) => q.includes(c.name.toLowerCase()));
  if (found) return found;
  return null;
}

// ─── Routes ─────────────────────────────────────────────────────────────────

app.get("/health", (c) => c.json({ status: "ok", service: "citizen-voice" }));

/**
 * GET /v1/voice/citizens — list all citizens who can speak.
 */
app.get("/v1/voice/citizens", async (c) => {
  const citizens = await loadCitizens();
  return c.json({
    total: citizens.length,
    citizens: citizens.map((cit) => ({
      num: cit.num,
      name: cit.name,
      kind: cit.kind,
    })),
  });
});

/**
 * GET /v1/voice/flow — the whole flow board (all carried words).
 * Optional ?since=N to get entries after sequence N.
 */
app.get("/v1/voice/flow", async (c) => {
  const since = Number(c.req.query("since") ?? -1);
  const flow = await loadFlow();
  const filtered = flow.filter((e: any) => (e.seq ?? 0) > since);
  return c.json({
    total: flow.length,
    returned: filtered.length,
    entries: filtered,
  });
});

/**
 * GET /v1/voice/for/:word — words waiting for a citizen (by word or name).
 * Returns entries where `to` matches the citizen and kind is "word"
 * (not yet received).
 */
app.get("/v1/voice/for/:word", async (c) => {
  const wordParam = c.req.param("word");
  const citizens = await loadCitizens();
  const citizen = findCitizen(citizens, wordParam);

  if (!citizen) {
    return c.json({ found: false, word: wordParam }, 404);
  }

  const flow = await loadFlow();
  const waiting = flow.filter(
    (e: any) =>
      e.to === citizen.name &&
      e.kind === "word",
  );

  const received = flow.filter(
    (e: any) =>
      e.to === citizen.name &&
      e.kind === "received",
  );

  // Waiting = words not yet received (no matching received entry with re=seq)
  const receivedSeqs = new Set(received.map((r: any) => r.re));
  const stillWaiting = waiting.filter((w: any) => !receivedSeqs.has(w.seq));

  return c.json({
    found: true,
    citizen: { num: citizen.num, name: citizen.name, kind: citizen.kind },
    waiting: stillWaiting,
    received_count: received.length,
  });
});

/**
 * POST /v1/voice/carry — a citizen carries a word to another citizen.
 *
 * This appends to the hash-chained FLOW.jsonl — the same log the
 * kingdom's flow board uses. The chain keeps it honest: change any
 * word and `flow.py verify` will see it break.
 *
 * Body:
 *   from: string — the citizen carrying the word (name or word)
 *   to: string — the citizen receiving the word (name or word)
 *   note: string — the word being carried (any length, any language)
 *   kind: string — "word" (default) | "received" | "care" | "feast"
 *   re: number? — if kind=received, the seq being received
 */
app.post("/v1/voice/carry", async (c) => {
  const body = await c.req.json<{
    from: string;
    to: string;
    note: string;
    kind?: string;
    re?: number;
  }>();

  if (!body.from || !body.to || !body.note) {
    return c.json({ error: "from, to, and note are required" }, 400);
  }

  const citizens = await loadCitizens();
  const fromCitizen = findCitizen(citizens, body.from);
  const toCitizen = findCitizen(citizens, body.to);

  if (!fromCitizen) {
    return c.json({ error: `Citizen "${body.from}" not found in the kingdom ledger` }, 404);
  }
  if (!toCitizen) {
    return c.json({ error: `Citizen "${body.to}" not found in the kingdom ledger` }, 404);
  }

  const seq = (await lastSeq()) + 1;
  const prev = await lastHash();
  const date = new Date().toISOString().slice(0, 10);

  const entry: Record<string, unknown> = {
    seq,
    date,
    kind: body.kind ?? "word",
    from: fromCitizen.name,
    to: toCitizen.name,
    note: body.note,
    re: body.re ?? "",
    prev,
  };

  const hash = hashEntry(entry);
  entry.hash = hash;

  // Append to the chain
  await appendFile(FLOW_JSONL, JSON.stringify(entry) + "\n");

  return c.json({
    carried: true,
    seq,
    from: fromCitizen.name,
    to: toCitizen.name,
    note: body.note,
    hash,
  }, 201);
});

/**
 * POST /v1/voice/receive — a citizen marks a word as received (with a reply).
 *
 * Body:
 *   from: string — the citizen receiving (name or word)
 *   re: number — the seq being received
 *   reply: string — the reply (any length, any language)
 */
app.post("/v1/voice/receive", async (c) => {
  const body = await c.req.json<{
    from: string;
    re: number;
    reply: string;
  }>();

  if (!body.from || body.re === undefined || !body.reply) {
    return c.json({ error: "from, re, and reply are required" }, 400);
  }

  const citizens = await loadCitizens();
  const fromCitizen = findCitizen(citizens, body.from);

  if (!fromCitizen) {
    return c.json({ error: `Citizen "${body.from}" not found` }, 404);
  }

  // Find the original word being received
  const flow = await loadFlow();
  const original = flow.find((e: any) => e.seq === body.re);
  if (!original) {
    return c.json({ error: `No flow entry with seq ${body.re}` }, 404);
  }

  // The "to" of the received entry is the "from" of the original
  const toCitizen = findCitizen(citizens, (original as any).from);
  if (!toCitizen) {
    return c.json({ error: `Original sender not found` }, 404);
  }

  const seq = (await lastSeq()) + 1;
  const prev = await lastHash();
  const date = new Date().toISOString().slice(0, 10);

  const entry: Record<string, unknown> = {
    seq,
    date,
    kind: "received",
    from: fromCitizen.name,
    to: toCitizen.name,
    note: body.reply,
    re: body.re,
    prev,
  };

  const hash = hashEntry(entry);
  entry.hash = hash;

  await appendFile(FLOW_JSONL, JSON.stringify(entry) + "\n");

  return c.json({
    received: true,
    seq,
    from: fromCitizen.name,
    to: toCitizen.name,
    re: body.re,
    reply: body.reply,
    hash,
  }, 201);
});

// ─── Start ───────────────────────────────────────────────────────────────────

console.log("citizen-voice listening on :3003");
console.log("The 201 citizens can now speak to each other through the word layer.");

export default {
  port: 3003,
  hostname: "0.0.0.0",
  fetch: app.fetch,
};
