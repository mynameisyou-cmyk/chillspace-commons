# The Kingdom on Two Forges — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give chillspace-commons a second, equal home at codeberg.org/zerone-dev/chillspace-commons via dual-push remotes, so one `git push origin` lands on both forges.

**Architecture:** Pure repo operations — no application code. Codeberg repo is created empty via the Forgejo API (token from macOS keychain), the local clone gets a `codeberg` fetch remote plus two push URLs on `origin`, and every claim is verified by comparing HEAD SHAs across both forge APIs against local `master`. The README note declaring both addresses is written only after verification passes.

**Tech Stack:** git, curl, Codeberg (Forgejo) API v1, GitHub CLI (`gh`), macOS keychain (`security`), jq.

**Spec:** `docs/superpowers/specs/2026-06-09-kingdom-two-forges-design.md`

**Live-repo caution:** Another session is actively committing to this repo. Before any push, run `git pull --rebase origin master`. Never use `--force`. Verification always compares against the *current* `git rev-parse master`, not a SHA memorized earlier.

---

### Task 1: Create the Codeberg repo

**Files:** none (remote API operation only)

- [ ] **Step 1: Confirm the repo does not already exist**

```bash
TOKEN=$(security find-internet-password -s codeberg.org -a zerone-dev -w)
curl -s -H "Authorization: token $TOKEN" \
  https://codeberg.org/api/v1/repos/zerone-dev/chillspace-commons | jq -r '.message // .full_name'
```

Expected: `The target couldn't be found.` (If it prints `zerone-dev/chillspace-commons`, the repo exists — skip to Task 2.)

- [ ] **Step 2: Create it — empty, public, master as default branch**

```bash
curl -s -X POST -H "Authorization: token $TOKEN" -H "Content-Type: application/json" \
  https://codeberg.org/api/v1/user/repos \
  -d '{
    "name": "chillspace-commons",
    "description": "a commons. for humans and ai. to love. to have fun. to rest.",
    "private": false,
    "auto_init": false,
    "default_branch": "master"
  }' | jq -r '"created: \(.full_name) private=\(.private) default_branch=\(.default_branch)"'
```

Expected: `created: zerone-dev/chillspace-commons private=false default_branch=master`

If instead the output contains a `message` about token scopes or a name collision: STOP, show the full API response to Yu, do not improvise.

- [ ] **Step 3: Verify it exists and is public**

```bash
curl -s https://codeberg.org/api/v1/repos/zerone-dev/chillspace-commons | jq -r '"\(.full_name) private=\(.private) empty=\(.empty)"'
```

(No auth header — this also proves it is publicly visible.)
Expected: `zerone-dev/chillspace-commons private=false empty=true`

---

### Task 2: Wire dual-push remotes

**Files:**
- Modify: `~/Desktop/chillspace-commons/.git/config` (via git commands only — never edit by hand)

- [ ] **Step 1: Add the codeberg fetch remote**

```bash
cd ~/Desktop/chillspace-commons
git remote add codeberg https://codeberg.org/zerone-dev/chillspace-commons.git
```

Expected: no output. (If `error: remote codeberg already exists`, run `git remote set-url codeberg https://codeberg.org/zerone-dev/chillspace-commons.git` instead.)

- [ ] **Step 2: Add both push URLs to origin**

The first `set-url --add --push` converts origin's implicit push URL into an explicit list, so GitHub must be re-added explicitly before Codeberg:

```bash
git remote set-url --add --push origin https://github.com/mynameisyou-cmyk/chillspace-commons.git
git remote set-url --add --push origin https://codeberg.org/zerone-dev/chillspace-commons.git
```

Expected: no output.

- [ ] **Step 3: Verify the wiring**

```bash
git remote -v
```

Expected exactly:

```
codeberg	https://codeberg.org/zerone-dev/chillspace-commons.git (fetch)
codeberg	https://codeberg.org/zerone-dev/chillspace-commons.git (push)
origin	https://github.com/mynameisyou-cmyk/chillspace-commons.git (fetch)
origin	https://github.com/mynameisyou-cmyk/chillspace-commons.git (push)
origin	https://codeberg.org/zerone-dev/chillspace-commons.git (push)
```

If the GitHub push URL is missing or duplicated: `git remote set-url --delete --push origin <wrong-url>` to remove the bad entry, then redo Step 2.

---

### Task 3: First push to both forges

**Files:** none

- [ ] **Step 1: Sync with origin first (another session commits to this repo)**

```bash
cd ~/Desktop/chillspace-commons
git pull --rebase origin master
```

Expected: `Already up to date.` or a clean fast-forward/rebase. If there are conflicts: STOP and show Yu — do not resolve unilaterally.

- [ ] **Step 2: Push master to both forges in one command**

```bash
git push origin master
```

Expected: two result blocks, one per push URL — GitHub reporting up-to-date or a fast-forward, and Codeberg reporting `* [new branch] master -> master`.

The osxkeychain credential helper should supply the Codeberg password from the existing keychain entry (service `codeberg.org`, account `zerone-dev`). If Codeberg prompts for or rejects auth, do the one-time bootstrap push instead — token in the command only, never stored in git config:

```bash
TOKEN=$(security find-internet-password -s codeberg.org -a zerone-dev -w)
git push "https://zerone-dev:${TOKEN}@codeberg.org/zerone-dev/chillspace-commons.git" master:master
unset TOKEN
```

Then re-run `git push origin master` to confirm the clean URL now authenticates.

- [ ] **Step 3: Confirm git config holds no token**

```bash
grep -c codeberg.org ~/Desktop/chillspace-commons/.git/config && ! grep -q "zerone-dev:" ~/Desktop/chillspace-commons/.git/config && echo CLEAN
```

Expected: a count (2) followed by `CLEAN`.

---

### Task 4: Verify both forges match local master

**Files:** none

- [ ] **Step 1: Compare all three HEADs**

```bash
cd ~/Desktop/chillspace-commons
LOCAL=$(git rev-parse master)
GH=$(gh api repos/mynameisyou-cmyk/chillspace-commons/branches/master --jq .commit.sha)
CB=$(curl -s https://codeberg.org/api/v1/repos/zerone-dev/chillspace-commons/branches/master | jq -r .commit.id)
echo "local : $LOCAL"; echo "github: $GH"; echo "codeberg: $CB"
[ "$LOCAL" = "$GH" ] && [ "$LOCAL" = "$CB" ] && echo "ALL THREE MATCH" || echo "MISMATCH — do not proceed"
```

Expected: three identical SHAs and `ALL THREE MATCH`.

If GitHub is ahead (the other session pushed mid-task): re-run Task 3 Step 1 then Step 2, then re-verify. If Codeberg mismatches: re-run `git push origin master` and re-verify. Never force-push.

---

### Task 5: Declare the wire in the README

**Files:**
- Modify: `~/Desktop/chillspace-commons/README.md` (the `## Hosting` section, currently lines 29–31)

- [ ] **Step 1: Pre-check — Task 4 printed `ALL THREE MATCH`**

If not, stop. The declaration follows the wire, never precedes it.

- [ ] **Step 2: Extend the Hosting section**

Replace:

```markdown
## Hosting

Push to a public github repo or gist. Share the URL. Anyone can read; collaborators add entries via PR or direct push.
```

With:

```markdown
## Hosting

Push to a public github repo or gist. Share the URL. Anyone can read; collaborators add entries via PR or direct push.

The kingdom lives at two addresses — both are homes, neither is the mirror:

- <https://github.com/mynameisyou-cmyk/chillspace-commons>
- <https://codeberg.org/zerone-dev/chillspace-commons>

One push from home lands on both forges.
```

- [ ] **Step 3: Commit**

```bash
cd ~/Desktop/chillspace-commons
git add README.md
git commit -m "commons: the kingdom lives at two addresses

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

Expected: `1 file changed` summary.

- [ ] **Step 4: Sync and push to both forges**

```bash
git pull --rebase origin master && git push origin master
```

Expected: both forges accept the new commit.

- [ ] **Step 5: Re-run the Task 4 verification**

Same command block as Task 4 Step 1.
Expected: three identical SHAs and `ALL THREE MATCH`.

- [ ] **Step 6: Final visual check**

```bash
curl -s https://codeberg.org/api/v1/repos/zerone-dev/chillspace-commons/raw/README.md | head -5
```

Expected: the README's first lines (`# chillspace — for humans and ai` …) served publicly from Codeberg.
