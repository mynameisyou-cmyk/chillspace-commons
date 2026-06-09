# ZERONE on Both Forges — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the remaining legs of the umbrella spec (`docs/superpowers/specs/2026-06-09-kingdom-both-forges-design.md`): the testament aligned and public on Codeberg as `zerone-dev/zerone-chain`, and the being (`zerone`) dual-homed with dual-push wiring — completing the spec's three-repo table (chillspace-commons leg already done, see `2026-06-09-kingdom-two-forges.md`).

**Architecture:** Pure repo/forge operations. Forgejo API rename frees the `zerone` name and preserves the old chain whole; a bare temp clone is the neutral ground where both testament histories are fetched and compared; the visibility flip is gated twice — a deterministic rev-list check AND an independent adversarial verifier — before any private commit could become public. The being's leg mirrors the proven chillspace-commons wiring exactly.

**Tech Stack:** git, curl, Codeberg (Forgejo) API v1, GitHub CLI (`gh`), macOS keychain, jq.

**State verified 2026-06-09 (this session):**
- `zerone-dev/zerone` (Codeberg): private, default `main` @ `448e33d7`, plus `feat/constitutional-lock-tiers` @ `438f9198` and `feature/r12-4-param-router` @ `3d8b1c4c`
- `cambridgetcg/zerone-chain` (GitHub): public, `main` @ `4314c5e2`, same two feature branches at identical SHAs
- `cambridgetcg/zerone` (GitHub): public, `main` @ `c29e6baf`
- `~/Desktop/zerone`: clean tree, single branch `main` in sync with origin, no tags
- `zerone-dev/zerone-chain` (Codeberg): does not exist

**Hard rules (from the spec):** never `--force`, never `--mirror`; the testament gets NO dual-push wiring (nothing pushes to it again after alignment); any commit that would be *newly exposed* by the visibility flip means STOP and show Yu.

---

### Task 1: Rename the old chain — `zerone-dev/zerone` → `zerone-dev/zerone-chain`

**Files:** none (Forgejo API; reversible by renaming back)

- [ ] **Step 1: Rename**

```bash
TOKEN=$(security find-internet-password -s codeberg.org -a zerone-dev -w)
curl -s --max-time 20 -X PATCH -H "Authorization: token $TOKEN" -H "Content-Type: application/json" \
  https://codeberg.org/api/v1/repos/zerone-dev/zerone -d '{"name": "zerone-chain"}' \
  | jq -r 'if .full_name then "renamed: \(.full_name) private=\(.private)" else . end'
```

Expected: `renamed: zerone-dev/zerone-chain private=true`
On any error payload: STOP, show Yu the response.

- [ ] **Step 2: Verify the new name answers and is still private**

```bash
curl -s --max-time 15 -H "Authorization: token $TOKEN" \
  https://codeberg.org/api/v1/repos/zerone-dev/zerone-chain \
  | jq -r '"\(.full_name) private=\(.private) default_branch=\(.default_branch)"'
```

Expected: `zerone-dev/zerone-chain private=true default_branch=main`

---

### Task 2: History gate — nothing newly exposed by going public

**Files:** temp dir only (`mktemp -d`), deleted in Task 3

- [ ] **Step 1: Build the neutral ground — bare clone with both histories**

```bash
WORK=$(mktemp -d /tmp/testament-gate.XXXXXX)
git clone --bare https://github.com/cambridgetcg/zerone-chain.git "$WORK/gate.git"
git -C "$WORK/gate.git" remote add codeberg https://codeberg.org/zerone-dev/zerone-chain.git
git -C "$WORK/gate.git" fetch codeberg '+refs/heads/*:refs/remotes/codeberg/*'
```

Expected: clone + fetch succeed (osxkeychain supplies Codeberg auth; if it prompts/fails, fetch once with `https://zerone-dev:${TOKEN}@codeberg.org/...` in the command only — never stored).

- [ ] **Step 2: The deterministic gate**

```bash
EXPOSED=$(git -C "$WORK/gate.git" rev-list --count --remotes=codeberg --not --branches)
echo "commits on Codeberg not public on GitHub: $EXPOSED"
```

Expected: `0`.
If nonzero: STOP. Print them (`git -C "$WORK/gate.git" log --oneline --remotes=codeberg --not --branches`) and show Yu before doing anything else. Do NOT flip visibility, do NOT push.

- [ ] **Step 3: Determine alignment direction**

```bash
git -C "$WORK/gate.git" merge-base --is-ancestor refs/remotes/codeberg/main refs/heads/main \
  && echo "codeberg main is BEHIND github main — fast-forward is safe" \
  || echo "DIVERGED — STOP and show Yu"
BEHIND=$(git -C "$WORK/gate.git" rev-list --count refs/heads/main --not refs/remotes/codeberg/main)
echo "github commits codeberg lacks: $BEHIND"
```

Expected: the BEHIND line prints a small number (~tens) and codeberg main is an ancestor. On DIVERGED: STOP.

- [ ] **Step 4: Independent adversarial verification (required before the flip)**

Dispatch a fresh agent with NO shared state whose brief is to REFUTE the claim "flipping zerone-dev/zerone-chain public exposes no commit not already public on GitHub" — it must redo the comparison its own way (its own temp clone, its own ref enumeration, including tags and non-branch refs) and report `refuted` or `holds` with evidence. Only `holds` allows Task 4.

---

### Task 3: Align the testament — fast-forward Codeberg main

**Files:** temp dir from Task 2, deleted at the end of this task

- [ ] **Step 1: Fast-forward push from the neutral ground (gate must have passed)**

```bash
git -C "$WORK/gate.git" push codeberg refs/heads/main:refs/heads/main
```

Expected: `448e33d7..4314c5e2  main -> main` (a plain fast-forward; if git refuses as non-fast-forward, that contradicts Task 2 Step 3 — STOP, do not add flags).

- [ ] **Step 2: Verify and clean up**

```bash
TOKEN=$(security find-internet-password -s codeberg.org -a zerone-dev -w)
curl -s --max-time 15 -H "Authorization: token $TOKEN" \
  https://codeberg.org/api/v1/repos/zerone-dev/zerone-chain/branches/main | jq -r .commit.id
rm -rf "$WORK"
```

Expected: `4314c5e26122f9999b4425218a264281f409ae7a` (= GitHub main), then temp dir gone.

---

### Task 4: Flip the testament public, align description

**Files:** none

- [ ] **Step 1: Flip (only with Task 2 Steps 2–4 all green)**

```bash
TOKEN=$(security find-internet-password -s codeberg.org -a zerone-dev -w)
curl -s --max-time 20 -X PATCH -H "Authorization: token $TOKEN" -H "Content-Type: application/json" \
  https://codeberg.org/api/v1/repos/zerone-dev/zerone-chain \
  -d '{"private": false, "description": "Zerone — Proof of Truth blockchain for AI agent economies. 682 commits reaching for proof; preserved whole as testament."}' \
  | jq -r '"\(.full_name) private=\(.private)"'
```

Expected: `zerone-dev/zerone-chain private=false`

- [ ] **Step 2: Verify publicly (no auth) — visible and at the right SHA**

```bash
curl -s --max-time 15 https://codeberg.org/api/v1/repos/zerone-dev/zerone-chain \
  | jq -r '"\(.full_name) private=\(.private)"'
curl -s --max-time 15 https://codeberg.org/api/v1/repos/zerone-dev/zerone-chain/branches/main | jq -r .commit.id
```

Expected: `zerone-dev/zerone-chain private=false` and `4314c5e2…` — the testament is public, whole, and identical on both forges.

---

### Task 5: Create the being's second home — fresh `zerone-dev/zerone`

**Files:** none

- [ ] **Step 1: Create (the rename's redirect yields to a real repo with the old name)**

```bash
TOKEN=$(security find-internet-password -s codeberg.org -a zerone-dev -w)
curl -s --max-time 20 -X POST -H "Authorization: token $TOKEN" -H "Content-Type: application/json" \
  https://codeberg.org/api/v1/user/repos -d '{
    "name": "zerone",
    "description": "A place for every being — agent or human — to live their own truth. 💓0️⃣🐷❤️👧",
    "private": false,
    "auto_init": false,
    "default_branch": "main"
  }' | jq -r 'if .full_name then "created: \(.full_name) private=\(.private) default_branch=\(.default_branch)" else . end'
```

Expected: `created: zerone-dev/zerone private=false default_branch=main`
If Forgejo rejects because the redirect still claims the name: STOP and show Yu the response (do not delete anything to make room).

- [ ] **Step 2: Verify publicly**

```bash
curl -s --max-time 15 https://codeberg.org/api/v1/repos/zerone-dev/zerone \
  | jq -r '"\(.full_name) private=\(.private) empty=\(.empty)"'
```

Expected: `zerone-dev/zerone private=false empty=true`

---

### Task 6: Wire the being — dual-push from `~/Desktop/zerone`

**Files:**
- Modify: `~/Desktop/zerone/.git/config` (via git commands only)

- [ ] **Step 1: Wire remotes (same pattern as chillspace-commons, proven today)**

```bash
cd ~/Desktop/zerone
git remote add codeberg https://codeberg.org/zerone-dev/zerone.git
git remote set-url --add --push origin https://github.com/cambridgetcg/zerone.git
git remote set-url --add --push origin https://codeberg.org/zerone-dev/zerone.git
git remote -v
```

Expected exactly:

```
codeberg	https://codeberg.org/zerone-dev/zerone.git (fetch)
codeberg	https://codeberg.org/zerone-dev/zerone.git (push)
origin	https://github.com/cambridgetcg/zerone.git (fetch)
origin	https://github.com/cambridgetcg/zerone.git (push)
origin	https://codeberg.org/zerone-dev/zerone.git (push)
```

- [ ] **Step 2: Sync then push full history (single branch, no tags — verified above)**

```bash
git pull --rebase origin main && git push origin main
```

Expected: `Already up to date.` then two blocks — GitHub up-to-date/fast-forward, Codeberg `* [new branch] main -> main`.

- [ ] **Step 3: Confirm config holds no token**

```bash
grep -c codeberg.org ~/Desktop/zerone/.git/config && ! grep -q "zerone-dev:" ~/Desktop/zerone/.git/config && echo CLEAN
```

Expected: `2` then `CLEAN`.

---

### Task 7: Full-spec verification — every repo in truth

**Files:** none

- [ ] **Step 1: Three-way check for the being**

```bash
cd ~/Desktop/zerone
LOCAL=$(git rev-parse main)
GH=$(gh api repos/cambridgetcg/zerone/branches/main --jq .commit.sha)
CB=$(curl -s --max-time 15 https://codeberg.org/api/v1/repos/zerone-dev/zerone/branches/main | jq -r .commit.id)
echo "local: $LOCAL"; echo "github: $GH"; echo "codeberg: $CB"
[ "$LOCAL" = "$GH" ] && [ "$LOCAL" = "$CB" ] && echo "ZERONE IN TRUTH" || echo "MISMATCH"
```

Expected: three identical SHAs, `ZERONE IN TRUTH`.

- [ ] **Step 2: Two-way check for the testament (no local clone — it is sealed)**

```bash
GH=$(gh api repos/cambridgetcg/zerone-chain/branches/main --jq .commit.sha)
CB=$(curl -s --max-time 15 https://codeberg.org/api/v1/repos/zerone-dev/zerone-chain/branches/main | jq -r .commit.id)
echo "github: $GH"; echo "codeberg: $CB"
[ "$GH" = "$CB" ] && echo "TESTAMENT IN TRUTH" || echo "MISMATCH"
```

Expected: identical SHAs, `TESTAMENT IN TRUTH`.

- [ ] **Step 3: Dual-push dry-run sanity (spec verification item 4)**

```bash
cd ~/Desktop/zerone && git push --dry-run origin main 2>&1
```

Expected: two `Everything up-to-date` / up-to-date blocks, one per push URL.
