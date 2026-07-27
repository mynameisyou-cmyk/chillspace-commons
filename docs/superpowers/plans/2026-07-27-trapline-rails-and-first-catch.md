# Trapline: Rails and the First Catch — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put out the confirmed credential fires, then finish, test, and ship the half-built Honey Bearer canary and the Door Back so the kingdom can detect its *next* leak.

**Architecture:** Two independent halves. **Half A (Tasks 1–3)** is incident response — rotate what is already public and rewrite the histories that carry it; it touches no application code. **Half B (Tasks 4–8)** completes work that already exists uncommitted in `~/Projects/agenttool`: a nullable `canary_placement` column on `tools.api_keys`, a global `canaryWatch` middleware that adds a door to a planted key's responses, and an unauthenticated `/v1/canary` route. Half B is currently **untested, uncommitted, and unmigrated** — this plan tests it before it ships, because `canaryWatch` rewrites response bodies for the entire API.

**Tech Stack:** Bun + Hono + Drizzle + Postgres (Supabase) · `bun test` · Fly.io · `git-filter-repo` · Python 3 for the kingdom ledger.

## Global Constraints

- **Scope is §9.6 items 0–3 only.** Receipts (杜杜/卡卡) and comedy (空空/引引) are separate plans. Do not build them here.
- **Never print a secret value** into a terminal, a commit message, a test fixture, or a log. Compare by hash. Delete local copies of any fetched blob.
- **No trap may record a person.** A catch row carries the placement and nothing else — no IP, no user-agent, no headers, no body. `api/src/index.ts:198-205` removed the request logger on principle and this must not put it back.
- **A canary key must open a project that holds nothing.** No wallet, no vault secrets, no runtime, no covenants, no listings.
- **Never hook the `not_found` branch** of `verifyBearer`. `api/src/auth/middleware.ts:56-58` filters `isNull(apiKeys.revokedAt)`, so revoked keys land there — hooking it would trap real citizens on every rotation.
- **The exit ships before the room.** `/v1/canary/why` must be live and reachable before any canary string is planted anywhere.
- Run all `bun test` commands from `~/Projects/agenttool/api`.
- Do not run bare `cd api && fly deploy`; use `bin/deploy.sh` from the repo root.

## File Structure

| File | Responsibility | State |
|---|---|---|
| `api/migrations/20260727T034000_trapline_canary_placement.sql` | `canary_placement` column + `canary_reports` table | exists, **unapplied** |
| `api/src/db/schema/tools.ts` | Drizzle definitions for both | modified, uncommitted |
| `api/src/auth/middleware.ts` | sets `canaryPlacement` on context | modified, uncommitted |
| `api/src/services/trapline/canary.ts` | frame text, door constants, catch recording + coalescing | exists, **untested** |
| `api/src/middleware/canary-watch.ts` | adds header + `_canary` body frame | exists, **untested** |
| `api/src/routes/canary.ts` | `GET /why`, `POST /report` | exists, **untested** |
| `api/tests/canary.test.ts` | the tests this plan writes | **to create** |
| `api/scripts/plant-canary.ts` | mints a canary against the empty project | **to create** |
| `kingdom/trapline/trapline.py` | hash-chained `CATCHES.jsonl` | exists, unverified |

---

### Task 1: Rotate the AWS key pair (the only confirmed-live money-grade credential)

The access key ID in the public blob is byte-identical to the one still live at
`Projects/cambridgetcg-storefront/.env.local:11`. It has been public since 2026-04-10.

**Files:**
- Modify: `~/Projects/cambridgetcg-storefront/.env.local:11`
- Read: AWS IAM console, CloudTrail

- [ ] **Step 1: Identify the key's blast radius before touching it**

```bash
cd ~/Projects/cambridgetcg-storefront
grep -n 'AKIA' .env.local | sed 's/=.*/=<REDACTED>/'
aws sts get-caller-identity 2>/dev/null || echo "aws cli not configured — use the console"
```

Expected: one `AKIA…` line. Note the IAM user it belongs to.

- [ ] **Step 2: Read CloudTrail for that access key ID**

In the AWS console: CloudTrail → Event history → filter **AWS access key** = the exposed ID,
time range = 2026-04-10 to today. Export the results. **This is the step that tells you whether
this is a cleanup or a breach.** If there is activity from an IP or region you do not recognise,
stop this plan and treat it as a live breach.

- [ ] **Step 3: Create a replacement key, deploy it, then delete the old one**

Order matters — create-then-delete, never delete-then-create, or the storefront goes down.

```bash
# 1. AWS console: IAM → Users → <user> → Security credentials → Create access key
# 2. Put the new pair in .env.local (edit by hand; never echo a secret into shell history)
# 3. Redeploy whatever consumes it, then verify the app still works
# 4. AWS console: mark the OLD key Inactive. Wait 24h. Then Delete.
```

- [ ] **Step 4: Verify the old key is dead**

```bash
# With the OLD key configured, this must fail:
AWS_ACCESS_KEY_ID=<old> AWS_SECRET_ACCESS_KEY=<old> aws sts get-caller-identity
```

Expected: `InvalidClientTokenId`. If it succeeds, the key is still live — go back to step 3.

- [ ] **Step 5: Rotate the Postgres password in the embedded `postgres://` URL**

The blob contains one connection string with credentials inline. Rotate that role's password in
Supabase, update every consumer, and confirm the app reconnects.

- [ ] **Step 6: Record the outcome (no secrets)**

```bash
cd ~/Desktop/chillspace-commons
# Append a dated line to kingdom/trapline/DESIGN.md §1 stating: rotated, old key deleted,
# CloudTrail reviewed, findings. Then:
git add kingdom/trapline/DESIGN.md
git commit -m "trapline §1: AWS key pair rotated, old key deleted, CloudTrail reviewed"
```

---

### Task 2: Rewrite the storefront history and force-push

Rotation makes the key useless. This makes the blob unreachable, which matters because the file
also carries hostnames, internal structure, and a 40-char secret you may not have enumerated.

**Files:**
- Modify: `~/Projects/cambridgetcg-storefront` (history)

- [ ] **Step 1: Full backup first — this is destructive and irreversible**

```bash
cd ~/Projects
git clone --mirror https://github.com/cambridgetcg/cambridgetcg-storefront.git \
  ~/Desktop/storefront-backup-$(date +%Y%m%d).git
```

Expected: a `.git` mirror on the Desktop. **Do not proceed without it.**

- [ ] **Step 2: Confirm which paths must go**

```bash
cd ~/Projects/cambridgetcg-storefront
git log --all --oneline -- .sovereign-state.json sovereign.log | head
```

Expected: at least `0c41c90` (adds) and `58ed17c` (removes from HEAD).

- [ ] **Step 3: Rewrite**

```bash
pip install git-filter-repo   # if absent
cd ~/Projects/cambridgetcg-storefront
git filter-repo --invert-paths \
  --path .sovereign-state.json \
  --path sovereign.log \
  --force
```

- [ ] **Step 4: Verify the blob is gone from every ref**

```bash
git log --all --oneline -- .sovereign-state.json | wc -l   # expect 0
git rev-list --all --count                                  # sanity: still has your history
```

Expected: `0` for the first command.

- [ ] **Step 5: Force-push and re-add the remote**

`git-filter-repo` removes `origin` deliberately.

```bash
git remote add origin https://github.com/cambridgetcg/cambridgetcg-storefront.git
git push origin --force --all
git push origin --force --tags
```

- [ ] **Step 6: Prove it to an anonymous stranger**

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://raw.githubusercontent.com/cambridgetcg/cambridgetcg-storefront/0c41c90/.sovereign-state.json"
```

Expected: **404**. If it still returns 200, GitHub is serving a cached view — open a support
ticket asking them to expire it, and note that forks and clones may still carry it.

---

### Task 3: Rotate the loveproto identity keys

Five Ed25519 private keys, still in the public HEAD of `mynameisyou-cmyk/loveproto`.

**Files:**
- Modify: `~/Projects/loveproto` — `identity.pem`, `bridge/identity.pem`, `nodes/*/identity.pem`, `.gitignore`

- [ ] **Step 1: Widen `.gitignore` before generating anything new**

`.gitignore:3` covers `nodes/*/identity.pem` only; the two at the root were never ignored.

```bash
cd ~/Projects/loveproto
printf 'identity.pem\n*/identity.pem\nnodes/*/identity.pem\n' >> .gitignore
git rm --cached identity.pem bridge/identity.pem nodes/*/identity.pem
```

- [ ] **Step 2: Generate replacements**

`identity.py:38` writes `identity.pem` into a store dir, so deleting the file and re-running the
node regenerates it. Confirm by reading `identity.py` before relying on it.

```bash
python3 -c "import identity; print(identity.__file__)"
# then per node dir, remove the old pem and let the node regenerate on next start
```

- [ ] **Step 3: Commit the removal, then rewrite history**

```bash
git add .gitignore && git commit -m "loveproto: stop tracking identity keys, widen gitignore"
git clone --mirror https://github.com/mynameisyou-cmyk/loveproto.git ~/Desktop/loveproto-backup.git
git filter-repo --invert-paths --path-glob '*identity.pem' --force
git remote add origin https://github.com/mynameisyou-cmyk/loveproto.git
git push origin --force --all
```

- [ ] **Step 4: Verify anonymously**

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://raw.githubusercontent.com/mynameisyou-cmyk/loveproto/HEAD/identity.pem"
```

Expected: **404**.

---

### Task 4: Pin `canaryWatch` response rewriting with tests (the Content-Length regression)

`canary-watch.ts:73-76` builds a replacement `Response` from `JSON.stringify({...body, _canary})`
while reusing `c.res.headers` verbatim. If those headers carry a `Content-Length` from the
original, shorter body, the response is corrupt — truncated or rejected by the client. This
middleware is mounted at `app.use("*", …)`, so a bug here is a bug in the whole API.

**Files:**
- Create: `api/tests/canary.test.ts`
- Modify: `api/src/middleware/canary-watch.ts:73-76`

**Interfaces:**
- Consumes: `canaryWatch()` from `../src/middleware/canary-watch`, `canaryFrame(placement)` and `_resetCanaryCoalescing()` from `../src/services/trapline/canary`
- Produces: nothing new — this task only pins existing behaviour

- [ ] **Step 1: Write the failing test**

```typescript
/** canaryWatch — response framing for planted credentials.
 *
 *  Pins:
 *    - an ordinary request (canaryPlacement null) is byte-identical, no header
 *    - a canary request gains X-Canary-Door and a _canary body frame
 *    - the rewritten body's Content-Length matches its actual byte length
 *    - array and non-JSON bodies are left alone
 */
import { describe, expect, test } from "bun:test";
import { Hono } from "hono";

import { canaryWatch } from "../src/middleware/canary-watch";
import { CANARY_DOOR_HEADER } from "../src/services/trapline/canary";

function appWith(placement: string | null) {
  const app = new Hono();
  app.use("*", canaryWatch());
  app.use("*", async (c, next) => {
    c.set("canaryPlacement", placement);
    await next();
  });
  app.get("/thing", (c) => {
    // Set Content-Length explicitly — this is what a proxy or a hand-built
    // Response does, and it is the case that corrupts.
    const body = JSON.stringify({ ok: true });
    return new Response(body, {
      status: 200,
      headers: {
        "content-type": "application/json",
        "content-length": String(new TextEncoder().encode(body).length),
      },
    });
  });
  return app;
}

describe("canaryWatch", () => {
  test("ordinary request is untouched", async () => {
    const res = await appWith(null).request("/thing");
    expect(res.headers.get(CANARY_DOOR_HEADER)).toBeNull();
    expect(await res.json()).toEqual({ ok: true });
  });

  test("canary request gains the door and the frame", async () => {
    const res = await appWith("test-placement").request("/thing");
    expect(res.headers.get(CANARY_DOOR_HEADER)).toContain("/v1/canary/why");
    const body = (await res.json()) as Record<string, unknown>;
    expect(body.ok).toBe(true);
    expect((body._canary as Record<string, unknown>).planted).toBe(true);
  });

  test("rewritten body's Content-Length matches its real byte length", async () => {
    const res = await appWith("test-placement").request("/thing");
    const declared = res.headers.get("content-length");
    const actual = new TextEncoder().encode(await res.clone().text()).length;
    if (declared !== null) {
      expect(Number(declared)).toBe(actual);
    }
  });
});
```

- [ ] **Step 2: Run it and watch the third test fail**

```bash
cd ~/Projects/agenttool/api && bun test tests/canary.test.ts
```

Expected: the first two pass; **"Content-Length matches" FAILS** — declared is the length of
`{"ok":true}` while the actual body now also carries the `_canary` frame.

- [ ] **Step 3: Fix by dropping the stale header**

```typescript
      const headers = new Headers(c.res.headers);
      headers.delete("content-length");
      c.res = new Response(
        JSON.stringify({ ...body, _canary: canaryFrame(placement) }),
        { status: c.res.status, headers },
      );
```

- [ ] **Step 4: Run to verify all three pass**

```bash
cd ~/Projects/agenttool/api && bun test tests/canary.test.ts
```

Expected: 3 pass, 0 fail.

- [ ] **Step 5: Confirm nothing else regressed**

```bash
cd ~/Projects/agenttool && bin/test-delta.sh
```

Expected: exit 0, no NEW failures against the committed baseline.

- [ ] **Step 6: Commit**

```bash
git add api/tests/canary.test.ts api/src/middleware/canary-watch.ts
git commit -m "fix(canary): drop stale Content-Length when framing a canary response

The middleware rebuilt the Response with the original headers, so a body that
grew by the _canary frame kept the shorter declared length. Pinned by test."
```

---

### Task 5: Pin the catch recorder — placement only, never a person

**Files:**
- Modify: `api/tests/canary.test.ts`

**Interfaces:**
- Consumes: `recordCanaryCatch({projectId, placement, nowMs})`, `_resetCanaryCoalescing()` from `../src/services/trapline/canary`

- [ ] **Step 1: Write the failing test**

```typescript
import { and, eq, like } from "drizzle-orm";
import { db } from "../src/db/client";
import { usageEvents } from "../src/db/schema/tools";
import { _resetCanaryCoalescing, recordCanaryCatch } from "../src/services/trapline/canary";

describe("recordCanaryCatch", () => {
  test("coalesces repeat uses of one placement inside the window", async () => {
    _resetCanaryCoalescing();
    const projectId = crypto.randomUUID();
    const placement = `test-${crypto.randomUUID()}`;

    recordCanaryCatch({ projectId, placement, nowMs: 1_000 });
    recordCanaryCatch({ projectId, placement, nowMs: 2_000 });   // inside 60s — dropped
    recordCanaryCatch({ projectId, placement, nowMs: 90_000 });  // outside — written

    await Bun.sleep(300); // the insert is deliberately fire-and-forget

    const rows = await db
      .select()
      .from(usageEvents)
      .where(and(eq(usageEvents.projectId, projectId), like(usageEvents.tool, "canary:%")));

    expect(rows.length).toBe(2);
    expect(rows[0].tool).toBe(`canary:${placement}`);
    expect(rows[0].creditsUsed).toBe(0);
  });
});
```

- [ ] **Step 2: Run to verify it fails or passes honestly**

```bash
cd ~/Projects/agenttool/api && bun test tests/canary.test.ts -t "coalesces"
```

Expected: PASS if the coalescing window works as written. If it FAILS, the bug is real — fix
`shouldRecord()` in `services/trapline/canary.ts:60-72` before continuing.

- [ ] **Step 3: Add the privacy pin**

```typescript
  test("a catch row carries no identifying column", async () => {
    const cols = Object.keys(usageEvents);
    for (const forbidden of ["ip", "ipAddress", "userAgent", "headers", "body"]) {
      expect(cols).not.toContain(forbidden);
    }
  });
```

- [ ] **Step 4: Run both**

```bash
cd ~/Projects/agenttool/api && bun test tests/canary.test.ts
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add api/tests/canary.test.ts
git commit -m "test(canary): pin catch coalescing and the no-identifier guarantee"
```

---

### Task 6: Apply the migration and commit the schema

**Files:**
- Apply: `api/migrations/20260727T034000_trapline_canary_placement.sql`
- Commit: `api/src/db/schema/tools.ts`, `api/src/auth/middleware.ts`, `api/src/index.ts`, `api/src/services/discovery/safety-boundaries.ts`

- [ ] **Step 1: Read the migration before running it**

```bash
cd ~/Projects/agenttool && cat api/migrations/20260727T034000_trapline_canary_placement.sql
```

Confirm it is additive only: `ADD COLUMN IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS`,
`CREATE INDEX IF NOT EXISTS`. No `DROP`, no `ALTER … TYPE`.

- [ ] **Step 2: Apply**

```bash
cd ~/Projects/agenttool
bun api/scripts/_migrate-one.ts api/migrations/20260727T034000_trapline_canary_placement.sql
```

- [ ] **Step 3: Verify the column and table exist**

```bash
psql "$DATABASE_URL" -c "\d tools.api_keys" | grep canary_placement
psql "$DATABASE_URL" -c "\d tools.canary_reports"
```

Expected: the column appears as `text`, and the table has exactly
`id, placement, where_found, contact, created_at` — **no ip, no user_agent**.

- [ ] **Step 4: Run the full suite**

```bash
cd ~/Projects/agenttool && bin/test-delta.sh
```

Expected: exit 0.

- [ ] **Step 5: Commit**

```bash
git add api/migrations/20260727T034000_trapline_canary_placement.sql \
        api/src/db/schema/tools.ts api/src/auth/middleware.ts \
        api/src/index.ts api/src/services/discovery/safety-boundaries.ts \
        api/src/middleware/canary-watch.ts api/src/routes/canary.ts \
        api/src/services/trapline/
git commit -m "feat(trapline): the Honey Bearer and the Door Back

A nullable canary_placement column, a global middleware that adds a door to a
planted key's responses, and an unauthenticated /v1/canary. A catch records the
placement and nothing else. Doctrine: kingdom/trapline/DESIGN.md §4.1, §4.5."
```

---

### Task 7: Ship the exit before the room

Nothing may be planted until `/v1/canary/why` answers on the live API.

**Files:**
- Deploy: `~/Projects/agenttool`

- [ ] **Step 1: Deploy**

```bash
cd ~/Projects/agenttool && bin/deploy.sh --no-migrate --no-frontend
```

- [ ] **Step 2: Verify the door is open and unauthenticated**

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://api.agenttool.dev/v1/canary/why
curl -s https://api.agenttool.dev/v1/canary/why | head -c 400
```

Expected: **200** with no `Authorization` header, and prose that says plainly what the holder is
holding. If it returns 401, the route was caught by an auth prefix — fix the mount in
`api/src/index.ts` and redeploy.

- [ ] **Step 3: Verify an ordinary key is completely unaffected**

```bash
curl -s -D- -o /dev/null https://api.agenttool.dev/v1/wake \
  -H "Authorization: Bearer $AGENTTOOL_KEY" | grep -i 'x-canary-door' \
  && echo "REGRESSION — an ordinary key got the header" || echo "ok: no door on an ordinary key"
```

Expected: `ok: no door on an ordinary key`.

---

### Task 8: The empty project, the first canary, and the placements map

**Files:**
- Create: `api/scripts/plant-canary.ts`
- Create: `~/Desktop/chillspace-commons/kingdom/trapline/placements.jsonl`

**Interfaces:**
- Consumes: `generateApiKey()` from `api/src/auth/keys.ts` — returns `{key, keyHash, keyPrefix}`

- [ ] **Step 1: Create the project that holds nothing**

Through the ordinary API, then assert its emptiness. It must have no wallet, no vault entries,
no runtimes, no listings, and a zero credit balance.

```bash
psql "$DATABASE_URL" -c "SELECT id, name FROM tools.projects WHERE name = 'the-empty-room';"
```

- [ ] **Step 2: Write the planting script**

```typescript
/** plant-canary.ts — mint one planted credential for one placement.
 *
 *  Prints the key ONCE. It is never stored in plaintext, never returned by
 *  GET /v1/keys, and never written where a running process reads it. */
import { generateApiKey } from "../src/auth/keys";
import { db } from "../src/db/client";
import { apiKeys } from "../src/db/schema/tools";

const placement = process.argv[2];
const projectId = process.argv[3];
if (!placement || !projectId) {
  console.error("usage: bun api/scripts/plant-canary.ts <placement> <empty-project-id>");
  process.exit(1);
}

const { key, keyHash, keyPrefix } = generateApiKey();
await db.insert(apiKeys).values({
  projectId,
  keyHash,
  keyPrefix,
  name: `canary:${placement}`,
  canaryPlacement: placement,
});

console.log(`planted at: ${placement}`);
console.log(`prefix:     ${keyPrefix}`);
console.log(`key:        ${key}`);
console.log("\nWrite this key ONLY where a thief would look and no process reads.");
```

- [ ] **Step 3: Plant the first one in the transcript lake**

`~/.claude/projects/` is 714 MB of transcripts a thief greps before touching a `.env`. That makes
it the single best placement.

```bash
cd ~/Projects/agenttool
bun api/scripts/plant-canary.ts transcript-lake <empty-project-id>
```

- [ ] **Step 4: Verify it authenticates AND carries the door**

```bash
curl -s -D- -o /dev/null https://api.agenttool.dev/v1/wake \
  -H "Authorization: Bearer <the-planted-key>" | grep -i 'x-canary-door'
```

Expected: the header is present, and the request **succeeds** — the key must never stop working.

- [ ] **Step 5: Verify the catch landed with no identifier**

```bash
psql "$DATABASE_URL" -c \
  "SELECT tool, credits_used FROM tools.usage_events WHERE tool LIKE 'canary:%' ORDER BY created_at DESC LIMIT 3;"
```

Expected: one row, `canary:transcript-lake`, `0`.

- [ ] **Step 6: Record the placement, never the key**

```bash
cd ~/Desktop/chillspace-commons
echo '{"placement":"transcript-lake","prefix":"at_XXXXXXXX","planted":"2026-07-27","note":"~/.claude/projects transcript store"}' \
  >> kingdom/trapline/placements.jsonl
git add kingdom/trapline/placements.jsonl
git commit -m "trapline: first canary planted in the transcript lake"
```

**The key itself is never committed anywhere.** `placements.jsonl` maps prefix → location so a
fire names its own door; the secret half exists only in the planted location and the bcrypt hash.

---

## Self-Review

**Spec coverage.** §9.6 item 0 → Tasks 1–3. Item 1 (Door Back) → Task 7. Item 2 (separate
deployment) → **deliberately narrowed to Task 8 step 1**: the WIP's canary is an honest-disclosure
key rather than a fiction mirror world, so the rail it actually needs is *the project behind it
holds nothing*, not a whole separate Fly app. A separate app becomes mandatory again at 引引/糖糖,
which are a later plan. Item 3 (Honey Bearer + ledger) → Tasks 4–6, 8. **Gap acknowledged:**
`kingdom/trapline/trapline.py` and `CATCHES.jsonl` are not covered here — the DB `usage_events`
row is the source of truth for now, and the hash-chained kingdom ledger is deferred to the plan
that also builds the Hall.

**Placeholder scan.** `<empty-project-id>`, `<the-planted-key>`, and `at_XXXXXXXX` are runtime
values that cannot be known in advance and are produced by an earlier step in the same task. Every
other step carries real, runnable content.

**Type consistency.** `generateApiKey()` returns `{key, keyHash, keyPrefix}` — matches
`api/src/auth/keys.ts:13`. `canaryFrame(placement)` returns `CanaryFrame` — matches
`services/trapline/canary.ts:83`. `CANARY_DOOR_HEADER` is imported in both the middleware and the
test. `recordCanaryCatch` takes `{projectId, placement, nowMs?}` — matches `canary.ts:97`.

**Ordering hazard.** Task 7 must precede Task 8. Planting a credential before the door answers
would put someone in a room with no exit, which is the one thing §0 rule 4 forbids.
