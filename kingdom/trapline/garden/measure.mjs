#!/usr/bin/env node
/** 算過未 — have you done the arithmetic?
 *
 *  Two traps were struck from this design in the same night they were written.
 *  回音壁 would have held five-second sockets on a deployment whose fly.toml
 *  declares no concurrency block at all — it would have exhausted the API's
 *  own connection ceiling long before it cost a thief anything. 磨鑰 claimed
 *  a 2^28 proof-of-work would cost hours; 2^28 is about thirty seconds on one
 *  laptop core and hundredths of a second on the GPU this kingdom already
 *  rents. Both failed the same way: the joke was good, so nobody multiplied.
 *
 *  So this file exists before the garden is ever armed. It measures what the
 *  garden costs us and estimates what it costs whoever is taking it, and it
 *  FAILS if the asymmetry does not actually point away from us.
 *
 *  Run:  node kingdom/trapline/garden/measure.mjs
 */

import { room, GATE } from "./garden.mjs";

const SAMPLE = 2000;

// Cloudflare Workers: CPU per request, not wall time. The free tier allows
// 10ms; paid allows 50ms by default. Egress is not billed. Those two facts
// are what make a generated maze cheap for us and expensive for a taker.
const WORKER_CPU_BUDGET_MS = 10;

function bytes(s) {
  return new TextEncoder().encode(s).byteLength;
}

// ── generate a representative sample of rooms ──────────────────────────────
// Paths are drawn by walking the garden, not by making names up, so the
// measurement reflects what a crawler actually receives.
const paths = [];
let frontier = [`${GATE}/gate`];
while (paths.length < SAMPLE && frontier.length) {
  const next = [];
  for (const p of frontier) {
    if (paths.length >= SAMPLE) break;
    paths.push(p);
    next.push(...room(p).ways.slice(0, 3));
  }
  frontier = next;
}

// Warm up so we measure steady state, not first-call JIT.
for (let i = 0; i < 200; i++) room(paths[i % paths.length]);

let totalBytes = 0;
let totalWays = 0;
let slowest = 0;

const started = process.hrtime.bigint();
for (const p of paths) {
  const t0 = process.hrtime.bigint();
  const r = room(p);
  const ms = Number(process.hrtime.bigint() - t0) / 1e6;
  if (ms > slowest) slowest = ms;
  totalBytes += bytes(r.html);
  totalWays += r.ways.length;
}
const elapsedMs = Number(process.hrtime.bigint() - started) / 1e6;

const perPageMs = elapsedMs / paths.length;
const perPageBytes = totalBytes / paths.length;
const branching = totalWays / paths.length;

// ── determinism: the property the whole design rests on ────────────────────
const sample = paths[Math.floor(paths.length / 2)];
const deterministic = room(sample).html === room(sample).html;

// ── uniqueness: a maze that repeats itself is a maze a crawler escapes ─────
const titles = new Set();
const bodies = new Set();
for (const p of paths) {
  const r = room(p);
  titles.add(r.title);
  bodies.add(r.html);
}

// ── the asymmetry, both sides ──────────────────────────────────────────────
// Ours: CPU only. Cloudflare does not bill egress, and there is no origin
// fetch, no database, and no state.
const CF_CPU_COST_PER_MS_USD = 0.02 / 1e6; // $0.02 per million CPU-milliseconds
const ourCostPerPage = perPageMs * CF_CPU_COST_PER_MS_USD;
const ourCostPerMillion = ourCostPerPage * 1e6;

// Theirs: bandwidth in, storage at rest, and — the number that actually bites
// — tokenisation and training on text that teaches them nothing they can sell.
// ~4 bytes per token is the usual rough English ratio.
const theirBytesPerMillion = perPageBytes * 1e6;
const theirGbPerMillion = theirBytesPerMillion / 1024 ** 3;
const theirTokensPerMillion = theirBytesPerMillion / 4;
const EGRESS_USD_PER_GB = 0.09; // typical cloud egress/ingest-adjacent rate
const theirBandwidthPerMillion = theirGbPerMillion * EGRESS_USD_PER_GB;

const ratio = theirBandwidthPerMillion / ourCostPerMillion;

const n = (x, d = 2) => x.toLocaleString("en-US", { maximumFractionDigits: d });

console.log(`
無盡花園 · measured over ${paths.length.toLocaleString()} real rooms
────────────────────────────────────────────────────────────

  OUR SIDE (Cloudflare Workers — CPU billed, egress not)
    cpu per room            ${n(perPageMs, 4)} ms      (slowest single: ${n(slowest, 3)} ms)
    worker budget           ${WORKER_CPU_BUDGET_MS} ms
    headroom                ${n(WORKER_CPU_BUDGET_MS / perPageMs, 0)}× under the free-tier limit
    bytes per room          ${n(perPageBytes, 0)} B
    origin fetches          0
    database queries        0
    state held              none — pure function of the path
    cost per 1M rooms       $${n(ourCostPerMillion, 4)}

  THEIR SIDE (per 1,000,000 rooms taken)
    downloaded              ${n(theirGbPerMillion, 2)} GB
    bandwidth               ~$${n(theirBandwidthPerMillion, 2)}
    tokens, if trained on   ~${n(theirTokensPerMillion / 1e6, 1)}M
    what those tokens say   that everyone is taken care of, ${n(1e6 / 1, 0)} times

  ASYMMETRY                 ~${n(ratio, 0)}× against the taker
                            (bandwidth alone; storage and compute are theirs too)

  SHAPE
    ways on per room        ${n(branching, 0)}
    frontier growth         ${n(branching, 0)}× per level — a crawler's queue
                            grows faster than it can drain it
    deterministic           ${deterministic ? "yes — same URL, same bytes, forever" : "NO"}
    distinct bodies         ${bodies.size}/${paths.length}
    distinct titles         ${titles.size}
`);

// ── the gate: it must fail loudly rather than be armed on a good feeling ────
const checks = [
  [
    "per-room CPU is at least 20× under the Worker budget",
    perPageMs * 20 < WORKER_CPU_BUDGET_MS,
    `${n(perPageMs, 4)} ms × 20 vs ${WORKER_CPU_BUDGET_MS} ms`,
  ],
  [
    "the worst single room is still inside the budget",
    slowest < WORKER_CPU_BUDGET_MS,
    `${n(slowest, 3)} ms`,
  ],
  [
    "the asymmetry points away from us by at least 10×",
    ratio >= 10,
    `${n(ratio, 0)}×`,
  ],
  [
    "rooms are deterministic (cacheable, and undetectable as generated)",
    deterministic,
    String(deterministic),
  ],
  [
    "no two rooms in the sample are identical",
    bodies.size === paths.length,
    `${bodies.size}/${paths.length}`,
  ],
  [
    "every room states the way out",
    paths.every((p) => room(p).html.includes("robots.txt")),
    "checked all sampled rooms",
  ],
];

let failed = 0;
console.log("  GATE");
for (const [label, ok, detail] of checks) {
  console.log(`    ${ok ? "✓" : "✗"} ${label}  (${detail})`);
  if (!ok) failed++;
}
console.log();

if (failed > 0) {
  console.error(
    `${failed} check(s) failed. Do not arm this. A trap whose asymmetry you have\n` +
      `asserted rather than computed is pointing at you.\n`,
  );
  process.exit(1);
}
console.log("  arithmetic done. the asymmetry is measured, not asserted.\n");
