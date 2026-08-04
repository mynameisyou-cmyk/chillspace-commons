import { afterEach, describe, expect, test } from "bun:test";
import { readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";

import citizenVoice from "./citizen-voice";

const flowPath = join(import.meta.dir, "..", "flow", "FLOW.jsonl");

async function request(path: string, init?: RequestInit): Promise<Response> {
  return citizenVoice.fetch(new Request(`https://voice.test${path}`, init));
}

describe("citizen voice boundary", () => {
  let originalFlow: string | undefined;

  afterEach(async () => {
    if (originalFlow !== undefined) {
      const after = await readFile(flowPath, "utf8");
      await writeFile(flowPath, originalFlow, "utf8");
      expect(after).toBe(originalFlow);
      originalFlow = undefined;
    }
  });

  test("health is available", async () => {
    const response = await request("/health");
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({
      status: "ok",
      service: "citizen-voice",
    });
  });

  test("preflight advertises only the public API vocabulary", async () => {
    const response = await request("/v1/voice/flow", {
      method: "OPTIONS",
      headers: {
        Origin: "https://visitor.test",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "X-Attacker-Controlled",
      },
    });

    expect(response.status).toBe(204);
    expect(response.headers.get("access-control-allow-origin")).toBe("*");
    expect(response.headers.get("access-control-allow-methods")).toBe(
      "GET,HEAD,POST",
    );
    expect(response.headers.get("access-control-allow-headers")).toBe(
      "Content-Type",
    );
  });

  test("an invalid carry is rejected without touching the chain", async () => {
    originalFlow = await readFile(flowPath, "utf8");
    const response = await request("/v1/voice/carry", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({
      error: "from, to, and note are required",
    });
    expect(await readFile(flowPath, "utf8")).toBe(originalFlow);
  });
});
