import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { Hono } from "hono";
import { cors } from "hono/cors";

const EXPECTED_VERSION = "4.13.0";
const EXPECTED_INTEGRITY =
  "sha512-jhunvfHWxd7J5EFfSgH4xsYJzSe/lfqbUCxiyyeaQasUsXeEHXtzVid+7EOGByc5JnFa23SSFL3Y2RV/z1T+eQ==";

const read = (path) => readFileSync(path, "utf8");

test("the locked and vendored Hono release is the reviewed patched artifact", () => {
  const rootPackage = JSON.parse(read("package.json"));
  const vendorPackage = JSON.parse(read("node_modules/hono/package.json"));
  const lock = read("bun.lock");

  assert.equal(rootPackage.dependencies.hono, EXPECTED_VERSION);
  assert.equal(vendorPackage.version, EXPECTED_VERSION);
  assert.match(lock, new RegExp(`hono@${EXPECTED_VERSION.replaceAll(".", "\\.")}`));
  assert.ok(lock.includes(EXPECTED_INTEGRITY));

  const corsSource = read("node_modules/hono/dist/middleware/cors/index.js");
  assert.ok(!corsSource.includes("split(/\\s*,\\s*/)"));
  assert.ok(corsSource.includes('split(",").map((h) => h.trim())'));
});

test("the patched default CORS path handles a long whitespace run", async () => {
  const app = new Hono();
  app.use("*", cors());
  app.get("/health", (context) => context.json({ status: "ok" }));

  const requestedHeaders = `x${" ".repeat(80_000)}y`;
  const started = performance.now();
  const response = await app.request("https://castle.test/health", {
    method: "OPTIONS",
    headers: {
      Origin: "https://visitor.test",
      "Access-Control-Request-Method": "GET",
      "Access-Control-Request-Headers": requestedHeaders,
    },
  });

  assert.equal(response.status, 204);
  assert.equal(
    response.headers.get("access-control-allow-headers"),
    requestedHeaders,
  );
  assert.ok(
    performance.now() - started < 1_000,
    "the formerly quadratic preflight path must complete within one second",
  );
});

test("citizen voice uses a finite preflight vocabulary", () => {
  const source = read("kingdom/voice/citizen-voice.ts");

  assert.ok(source.includes('allowMethods: ["GET", "HEAD", "POST"]'));
  assert.ok(source.includes('allowHeaders: ["Content-Type"]'));
  assert.ok(!source.includes('app.use("*", cors())'));
});
