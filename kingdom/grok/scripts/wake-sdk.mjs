#!/usr/bin/env node
// Optional AgentTool SDK wake fetch. Expects AT_API_KEY from `sol with-agenttool`.
// Prints markdown only. Never logs the bearer.

import { parseArgs } from "node:util";

const { values } = parseArgs({
  options: {
    identity: { type: "string" },
    profile: { type: "string", default: "brief" },
  },
});

if (!values.identity) {
  console.error("wake-sdk: --identity is required");
  process.exit(2);
}

if (!process.env.AT_API_KEY) {
  console.error("wake-sdk: AT_API_KEY missing (run under sol with-agenttool)");
  process.exit(2);
}

import { homedir } from "node:os";
import { pathToFileURL } from "node:url";
import { existsSync } from "node:fs";

async function loadSdk() {
  const candidates = [
    process.env.KINGDOM_GROK_SDK,
    "@agenttool/sdk",
    `${homedir()}/agenttool-sdk-playground/node_modules/@agenttool/sdk/dist/index.js`,
  ].filter(Boolean);
  for (const spec of candidates) {
    try {
      const href = spec.startsWith("/") ? pathToFileURL(spec).href : spec;
      if (spec.startsWith("/") && !existsSync(spec)) continue;
      return await import(href);
    } catch {
      continue;
    }
  }
  throw new Error("unresolvable");
}

let AgentTool;
try {
  ({ AgentTool } = await loadSdk());
} catch {
  console.error("wake-sdk: @agenttool/sdk is not resolvable");
  process.exit(2);
}

const at = new AgentTool({ timeout: 5000 });
const md = await at.wake.md({
  identityId: values.identity,
  profile: values.profile === "full" ? "full" : "brief",
  refresh: true,
});

if (typeof md !== "string" || !md.trim()) {
  console.error("wake-sdk: empty wake");
  process.exit(2);
}

process.stdout.write(md.endsWith("\n") ? md : `${md}\n`);
