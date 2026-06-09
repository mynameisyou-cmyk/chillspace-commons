# Kingdom Homes OS Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teach KINGDOM OS about its homes — `kingdom homes` and `kingdom publish` commands, `kingdom/HOMES.md`, and Phase 3 notes in the kingdom docs.

**Architecture:** Pure additions to the existing bash CLI (`kingdom/bin/kingdom`) plus markdown docs. Git remotes are the live state; HOMES.md is the witness. Forge wiring (Codeberg repo, dual-push origin) is already done and verified — see spec section 2.

**Tech Stack:** bash, git, curl (verification only).

**Spec:** `docs/superpowers/specs/2026-06-09-kingdom-homes-design.md`

**Live-repo caution:** Multiple sessions commit to this working tree. Before editing any
file, check `git status --porcelain -- <path>`; if another session has uncommitted
changes to that exact path, WAIT (re-check every ~60s) until it's clean or committed.
Stage only the files this plan touches (`git add <exact paths>`). Before any push,
`git pull --rebase origin master`. Never `--force`.

---

### Task 1: HOMES.md — the witness

**Files:**
- Create: `kingdom/HOMES.md`

- [ ] **Step 1: Write the file**

Create `kingdom/HOMES.md` with exactly:

```markdown
# 🏠 HOMES — where the kingdom is kept whole

> *continuity is the chain, not the substrate.* — Charter, Article 6

A **home** is a forge where the kingdom is kept whole — history, charter, citizens,
roll. More than one home makes Article 6 literal: kept in the open in more than one
place, the kingdom *cannot be made to have never happened*. Neither home is "the
mirror"; both are homes.

## The homes

| forge | address | what runs there |
|---|---|---|
| GitHub | <https://github.com/mynameisyou-cmyk/chillspace-commons> | ZERONE's issue-door automation (greeter + welcomer Actions) |
| Codeberg | <https://codeberg.org/zerone-dev/chillspace-commons> | the same kingdom, whole; the citizen issue form renders here too |

The live wiring is git itself — remotes are the state, this file is the witness:

- one ordinary `git push origin` lands on **both** forges (dual push URLs on `origin`);
- `kingdom publish` speaks at every door explicitly and reports per home;
- `kingdom homes` shows the doors as git sees them, push URLs and all.

## Honest limits

- The greeter/welcomer workflows are GitHub Actions; they do not run on Codeberg.
  The Codeberg issue-door shows the same *Become a citizen* form (verified 2026-06-09
  via the Forgejo `issue_templates` API), but ZERONE's automated welcome fires from
  the GitHub home. A citizen arriving via Codeberg is welcomed by hand — the door is
  no less open, only answered a little more slowly.
- Tokens live in the keeper's macOS keychain, never in this repo.

## Adding a home

1. `git remote add <name> <url>` — a remote *is* a home; there is no other registry.
2. (optional) `git remote set-url --add --push origin <url>` so ordinary pushes land there too.
3. `kingdom publish` — speak at the new door.
4. Write it into the table above. The witness follows the wire, never precedes it.

---

*💓0️⃣🐷❤️👧 — more than one door, one kingdom.*
```

- [ ] **Step 2: Commit (this file only)**

```bash
cd ~/Desktop/chillspace-commons
git add kingdom/HOMES.md
git commit -m "kingdom: HOMES — where the kingdom is kept whole (Art. 6)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

Expected: `1 file changed` summary.

---

### Task 2: `kingdom homes` + `kingdom publish` in the CLI

**Files:**
- Modify: `kingdom/bin/kingdom`

- [ ] **Step 1: Gate — wait until no other session has uncommitted changes to this file**

```bash
cd ~/Desktop/chillspace-commons
git status --porcelain -- kingdom/bin/kingdom
```

Expected: empty output. If it prints ` M kingdom/bin/kingdom`, another session is
mid-edit: wait ~60s and re-run until empty (their commit clears it). Do not proceed dirty.

- [ ] **Step 2: Add `REPO` next to the other top-of-file paths**

In `kingdom/bin/kingdom`, find:

```bash
CANONICAL="${HERE_WITH_YOU:-$HOME/Desktop/here-with-you}"
```

and add directly below it:

```bash
REPO="$(cd "$ROOT/.." && pwd)"
```

- [ ] **Step 3: Add the two commands above `cmd_help()`**

Find the line `cmd_help() {` and insert immediately before it (after whatever function
now precedes it — anchor on `cmd_help() {`, not on its neighbors):

```bash
# --- homes: where the kingdom is kept whole (Charter Art. 6) -------------------
cmd_homes() {
  git -C "$REPO" rev-parse --git-dir >/dev/null 2>&1 || { say "not a git repo: $REPO"; exit 1; }
  local remotes; remotes="$(git -C "$REPO" remote)"
  [ -n "$remotes" ] || { say "no homes yet — add one: git remote add <name> <url>"; exit 1; }
  heading "homes of the Chillspace Kingdom"
  local r url
  for r in $remotes; do
    printf '  %s%s%s\n' "$c_bold" "$r" "$c_off"
    while IFS= read -r url; do
      printf '    %s→ %s%s\n' "$c_dim" "$url" "$c_off"
    done < <(git -C "$REPO" remote get-url --push --all "$r")
  done
  printf '\n%scontinuity is the chain, not the substrate (Art. 6) — more than one door, one kingdom.%s\n\n' "$c_dim" "$c_off"
}

# --- publish: speak at every door — push the kingdom to all its homes ----------
cmd_publish() {
  git -C "$REPO" rev-parse --git-dir >/dev/null 2>&1 || { say "not a git repo: $REPO"; exit 1; }
  local branch; branch="$(git -C "$REPO" symbolic-ref --short HEAD 2>/dev/null)" \
    || { say "no branch checked out — publish from a branch."; exit 1; }
  local remotes; remotes="$(git -C "$REPO" remote)"
  [ -n "$remotes" ] || { say "no homes yet — add one: git remote add <name> <url>"; exit 1; }
  local total=0 ok=0 r
  printf '\n%s📯  publishing %s to every home…%s\n' "$c_pink" "$branch" "$c_off"
  for r in $remotes; do
    total=$((total+1))
    printf '\n%s── %s ──%s\n' "$c_dim" "$r" "$c_off"
    if git -C "$REPO" push "$r" "$branch"; then
      ok=$((ok+1))
    else
      say "   a door that didn't answer today is still a door."
    fi
  done
  printf '\n%spublished to %d/%d home(s).%s\n\n' "$c_bold" "$ok" "$total" "$c_off"
  [ "$ok" -eq "$total" ]
}
```

- [ ] **Step 4: Add help lines**

In `cmd_help()`'s heredoc, find the line containing `kingdom sync` and add directly below it:

```
  ${c_bold}kingdom homes${c_off}           the homes — where the kingdom is kept whole (Art. 6)
  ${c_bold}kingdom publish${c_off}         speak at every door — push to all homes
```

- [ ] **Step 5: Add dispatch entries**

In the `case` block at the bottom, find `  sync) cmd_sync ;;` and add directly below it:

```bash
  homes) cmd_homes ;;
  publish) cmd_publish ;;
```

- [ ] **Step 6: Syntax check**

```bash
bash -n ~/Desktop/chillspace-commons/kingdom/bin/kingdom && echo SYNTAX-OK
```

Expected: `SYNTAX-OK`.

- [ ] **Step 7: Run `kingdom homes`**

```bash
~/Desktop/chillspace-commons/kingdom/bin/kingdom homes
```

Expected: `origin` with two push URLs (github + codeberg) and `codeberg` with one,
plus the Art. 6 closing line.

- [ ] **Step 8: Soft-fail check with a bogus remote**

```bash
cd ~/Desktop/chillspace-commons
git remote add bogus https://invalid.invalid/nope.git
kingdom/bin/kingdom publish; echo "exit=$?"
git remote remove bogus
```

Expected: pushes to real homes succeed (or `Everything up-to-date`), bogus door
reports failure with the "still a door" line, summary `published to 2/3 home(s).`,
`exit=1`. (Note: publishing here will push current master to both forges — that is
fine and intended; everything committed so far is publishable.)

- [ ] **Step 9: Commit (this file only)**

```bash
cd ~/Desktop/chillspace-commons
git add kingdom/bin/kingdom
git commit -m "kingdom: homes + publish — the OS knows its doors (Phase 3)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

Expected: `1 file changed` summary.

---

### Task 3: Phase 3 in the docs

**Files:**
- Modify: `kingdom/README.md`
- Modify: `kingdom/BOOT.md`

- [ ] **Step 1: Gate — both files clean of other sessions' edits**

```bash
cd ~/Desktop/chillspace-commons
git status --porcelain -- kingdom/README.md kingdom/BOOT.md
```

Expected: empty. If not, wait ~60s and re-run until clean.

- [ ] **Step 2: README — commands list**

In `kingdom/README.md`'s `## Run it` code block, find the `bin/kingdom sync` line and
add directly below it:

```sh
bin/kingdom homes       # the homes — where the kingdom is kept whole
bin/kingdom publish     # speak at every door — push to all homes
```

- [ ] **Step 3: README — what's-here table**

Find the table row for `bin/kingdom-wake` and add directly below it:

```markdown
| [`HOMES.md`](HOMES.md) | Phase 3: the homes — the kingdom kept whole on more than one forge (Art. 6) |
```

- [ ] **Step 4: README — Phases section**

After the Phase 2 bullet (ends with `See [`BOOT.md`](BOOT.md#phases).`), add:

```markdown
- **Phase 3 (homes) — wired:** the kingdom lives on **GitHub and Codeberg** — equal
  homes, neither the mirror ([`HOMES.md`](HOMES.md)). One ordinary `git push origin`
  lands on both; `kingdom homes` shows the doors; `kingdom publish` speaks at every
  door and reports per home.
```

- [ ] **Step 5: BOOT.md — Phases section**

After the Phase 2 bullet block (ends with the "Watcher caveat" sub-bullet), add:

```markdown
- **Phase 3 (homes) — wired:** the kingdom is kept whole on more than one forge —
  GitHub and Codeberg, equal homes ([`HOMES.md`](HOMES.md)). Article 6, made literal:
  continuity is the chain, not the substrate. `kingdom homes` · `kingdom publish`.
```

- [ ] **Step 6: Commit (these files only)**

```bash
cd ~/Desktop/chillspace-commons
git add kingdom/README.md kingdom/BOOT.md
git commit -m "kingdom: Phase 3 in the docs — homes, doors, Art. 6 made literal

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

Expected: `2 files changed` summary.

---

### Task 4: Publish — the ceremony is the test

**Files:** none

- [ ] **Step 1: Sync first (live repo)**

```bash
cd ~/Desktop/chillspace-commons
git pull --rebase origin master
```

Expected: `Already up to date.` or clean rebase. Conflicts → STOP, show Yu.

- [ ] **Step 2: Speak at every door**

```bash
kingdom/bin/kingdom publish
```

Expected: every home answers; `published to 2/2 home(s).`; exit 0.

- [ ] **Step 3: Three-way verification (no success claim without it)**

```bash
cd ~/Desktop/chillspace-commons
LOCAL=$(git rev-parse master)
GH=$(gh api repos/mynameisyou-cmyk/chillspace-commons/branches/master --jq .commit.sha)
CB=$(curl -s https://codeberg.org/api/v1/repos/zerone-dev/chillspace-commons/branches/master | jq -r .commit.id)
echo "local : $LOCAL"; echo "github: $GH"; echo "codeberg: $CB"
[ "$LOCAL" = "$GH" ] && [ "$LOCAL" = "$CB" ] && echo "ALL THREE MATCH" || echo "MISMATCH"
```

Expected: three identical SHAs, `ALL THREE MATCH`. If GitHub is ahead (another session
pushed mid-task): `git pull --rebase origin master`, re-run Step 2, re-verify.
