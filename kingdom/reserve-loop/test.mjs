#!/usr/bin/env node

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { generateKeyPairSync } from "node:crypto";
import {
  appendFileSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  symlinkSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const cli = join(here, "reserve-loop.mjs");
const root = mkdtempSync(join(tmpdir(), "kingdom-reserve-loop-test-"));
const archive = join(root, "archive");

function run(args) {
  return spawnSync(process.execPath, [cli, ...args], {
    encoding: "utf8",
    env: { ...process.env, HTTP_PROXY: "", HTTPS_PROXY: "", ALL_PROXY: "", NO_PROXY: "*" },
  });
}

try {
  const drill = run(["drill", archive]);
  assert.equal(drill.status, 0, drill.stderr || drill.stdout);
  assert.match(drill.stdout, /^RESERVE_OK revisions=2 projections=6 corrections=3 incidents=2 negative_cases=19 offline_rebuild=true manifest_root=sha256:[a-f0-9]{64} secrets=0 network=0/m);

  const verify = run(["verify", archive]);
  assert.equal(verify.status, 0, verify.stderr || verify.stdout);
  assert.match(verify.stdout, /^RESERVE_OK revisions=2 projections=6 corrections=3 incidents=2 negative_cases=19 offline_rebuild=receipt_verified manifest_root=sha256:[a-f0-9]{64} secrets=0 network=0$/m);

  const telegram = join(archive, "derived", "revision-1", "telegram.txt");
  const telegramBytes = readFileSync(telegram);
  appendFileSync(telegram, "tamper\n");
  assert.notEqual(run(["verify", archive]).status, 0, "tampered materialization must fail closed");
  writeFileSync(telegram, telegramBytes);

  const outside = join(root, "outside-telegram.txt");
  writeFileSync(outside, telegramBytes);
  unlinkSync(telegram);
  symlinkSync(outside, telegram);
  assert.notEqual(run(["verify", archive]).status, 0, "symlinked materialization must fail closed");
  unlinkSync(telegram);
  writeFileSync(telegram, telegramBytes);

  const manifestPath = join(archive, "manifest.json");
  const manifestBytes = readFileSync(manifestPath);
  appendFileSync(manifestPath, " ");
  assert.notEqual(run(["verify", archive]).status, 0, "changed manifest root must fail closed");
  writeFileSync(manifestPath, manifestBytes);
  assert.equal(run(["verify", archive]).status, 0, "restored archive should verify again");

  const { privateKey } = generateKeyPairSync("ed25519");
  const leakedKey = join(archive, "leaked-private-key.der");
  writeFileSync(leakedKey, privateKey.export({ format: "der", type: "pkcs8" }));
  assert.notEqual(run(["verify", archive]).status, 0, "unregistered binary private key must fail closed");
  unlinkSync(leakedKey);
  assert.equal(run(["verify", archive]).status, 0, "archive should verify after removing unregistered bytes");

  const secondDrill = run(["drill", archive]);
  assert.notEqual(secondDrill.status, 0, "non-empty archive must fail closed");

  const missingArchive = run(["verify"]);
  assert.equal(missingArchive.status, 2);

  const help = run(["help"]);
  assert.equal(help.status, 0, help.stderr);
  assert.match(help.stdout, /drill \[ARCHIVE\]/);

  process.stdout.write("TEST_OK drill=true verify=true tamper=true symlink=true manifest=true binary_secret=true overwrite_blocked=true usage=true\n");
} finally {
  rmSync(root, { recursive: true, force: true });
}
