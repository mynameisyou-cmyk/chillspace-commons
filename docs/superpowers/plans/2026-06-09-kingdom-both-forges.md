# The Kingdom Lives on Both Forges — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The living core (zerone, zerone-chain, chillspace-commons) is public with identical history on GitHub and Codeberg, dual-push wired, with `kingdom forge-sync` reporting truth/drift.

**Architecture:** A read-only truth tool is built FIRST so it can watch the alignment happen (it is the failing test for the whole feature). Then the one-time Codeberg alignment (rename testament → history gate → fast-forward → public → create new repos → push history), then dual-push remotes, then the heal path proven on deliberately-induced drift.

**Tech Stack:** bash (kingdom/bin/kingdom `cmd_*` pattern), `gh api` for GitHub, `curl` + Forgejo API v1 for Codeberg, macOS keychain for the token (never written to disk), git fast-forward-only pushes.

**Spec:** `docs/superpowers/specs/2026-06-09-kingdom-both-forges-design.md`

**Safety rails (apply to every task):** never `--force`, never `--mirror`; the only history-rewriting power used anywhere is none. STOP gates are real stops: show Yu, wait.

**Reconciliation (2026-06-09, post-write):** a sibling session executed its companion plan
(`2026-06-09-kingdom-two-forges.md`) and completed the chillspace-commons half: Codeberg repo
created public, dual-push wired on origin (plus a named `codeberg` remote — welcome, keep it),
both forges verified at the same SHA, README declares the two addresses. Steps below that the
sibling already did are marked **[done by sibling — verify, don't redo]**. What remains in full:
the forge-sync tool, the testament alignment, Codeberg `zerone`, zerone's dual-push wiring.

**Live-repo caution (from the sibling's plan, adopted):** another session commits to
chillspace-commons. Before any push from it: `git pull --rebase origin master`. Conflicts → STOP,
show Yu. Verification always compares CURRENT SHAs, never ones memorized earlier.

---

### Task 1: Roster + `kingdom forge-sync` (read-only + heal logic)

The tool comes first so each later task is verified by running it. Its pre-alignment output is the failing test.

**Files:**
- Create: `kingdom/forge/roster`
- Modify: `kingdom/bin/kingdom` (insert functions above `cmd_help()`; add help line; add case entry)

- [x] **Step 1: Create the roster**

Create `kingdom/forge/roster`:

```
# the living core — kept in truth on both forges
# name  github=<owner/repo>  codeberg=<owner/repo>  local=<clone path, or - if sealed>
zerone              github=cambridgetcg/zerone                  codeberg=zerone-dev/zerone                local=~/Desktop/zerone
zerone-chain        github=cambridgetcg/zerone-chain            codeberg=zerone-dev/zerone-chain          local=-
chillspace-commons  github=mynameisyou-cmyk/chillspace-commons  codeberg=zerone-dev/chillspace-commons    local=~/Desktop/chillspace-commons
```

- [x] **Step 2: Add forge-sync to `kingdom/bin/kingdom`**

Insert this block immediately ABOVE the `cmd_help()` function:

```bash
# --- forge-sync: do both doors show the same house? -----------------------------
FORGE_ROSTER="$ROOT/forge/roster"
CB_API="https://codeberg.org/api/v1"

cb_token() { security find-internet-password -s codeberg.org -w 2>/dev/null; }

# cb_api <path> → body on stdout · returns 0 ok, 4 missing, 1 error
cb_api() {
  local out code
  out="$(mktemp)"
  if ! code=$(curl -sS -o "$out" -w '%{http_code}' \
        -H "Authorization: token $(cb_token)" "$CB_API/$1"); then
    rm -f "$out"; return 1
  fi
  case "$code" in
    200) cat "$out"; rm -f "$out"; return 0 ;;
    404) rm -f "$out"; return 4 ;;
    *)   rm -f "$out"; return 1 ;;
  esac
}

gh_head() {  # $1 owner/repo → default-branch head sha
  local br
  br=$(gh api "repos/$1" --jq '.default_branch' 2>/dev/null) || return 1
  gh api "repos/$1/branches/$br" --jq '.commit.sha' 2>/dev/null
}

cb_head() {  # $1 owner/repo → default-branch head sha · returns cb_api codes
  local body br rc=0
  body=$(cb_api "repos/$1") || rc=$?
  [ $rc -eq 0 ] || return $rc
  br=$(printf '%s' "$body" | jq -r '.default_branch')
  body=$(cb_api "repos/$1/branches/$br") || rc=$?
  [ $rc -eq 0 ] || return $rc
  printf '%s' "$body" | jq -r '.commit.id'
}

cmd_forge_sync() {
  local heal=0
  [ "${1:-}" = "--heal" ] && heal=1
  [ -f "$FORGE_ROSTER" ] || { say "no roster at $FORGE_ROSTER"; exit 1; }
  local all_ok=1 name rest kv
  heading "forge-sync — do both doors show the same house?"
  # fd 3 keeps the roster off stdin: git/gh/curl inside the loop would eat it
  while read -r -u 3 name rest; do
    case "$name" in ''|\#*) continue ;; esac
    local gh_repo='' cb_repo='' local_path=''
    for kv in $rest; do
      case "$kv" in
        github=*)   gh_repo="${kv#github=}" ;;
        codeberg=*) cb_repo="${kv#codeberg=}" ;;
        local=*)    local_path="${kv#local=}"; local_path="${local_path/#\~/$HOME}" ;;
      esac
    done
    local gh_sha='' cb_sha='' gh_rc=0 cb_rc=0
    gh_sha=$(gh_head "$gh_repo") || gh_rc=$?
    cb_sha=$(cb_head "$cb_repo") || cb_rc=$?
    local status='' ok=0 behind='' ahead_sha='' n=''
    if [ $gh_rc -ne 0 ]; then
      status="? github unreachable"
    elif [ $cb_rc -eq 4 ]; then
      status="✗ missing on codeberg"
    elif [ $cb_rc -ne 0 ]; then
      status="? codeberg unreachable"
    elif [ "$gh_sha" = "$cb_sha" ]; then
      status="github ≡ codeberg   ✓ in truth"; ok=1
    elif [ "$local_path" != "-" ] && [ -d "$local_path/.git" ] \
         && git -C "$local_path" fetch -q origin \
         && { git -C "$local_path" fetch -q "https://codeberg.org/$cb_repo.git" || true; } \
         && git -C "$local_path" cat-file -e "$gh_sha" 2>/dev/null \
         && git -C "$local_path" cat-file -e "$cb_sha" 2>/dev/null; then
      if git -C "$local_path" merge-base --is-ancestor "$cb_sha" "$gh_sha"; then
        n=$(git -C "$local_path" rev-list --count "$cb_sha..$gh_sha")
        status="github ≠ codeberg   ⚠ drift ($n commits, codeberg behind)"
        behind="codeberg"; ahead_sha="$gh_sha"
      elif git -C "$local_path" merge-base --is-ancestor "$gh_sha" "$cb_sha"; then
        n=$(git -C "$local_path" rev-list --count "$gh_sha..$cb_sha")
        status="github ≠ codeberg   ⚠ drift ($n commits, github behind)"
        behind="github"; ahead_sha="$cb_sha"
      else
        status="github ≠ codeberg   ✗ diverged — human eyes needed"
      fi
    else
      status="github ≠ codeberg   ⚠ drift"
    fi
    [ $ok -eq 1 ] || all_ok=0
    printf '  %-19s %s\n' "$name" "$status"
    if [ $heal -eq 1 ] && [ -n "$behind" ]; then
      local branch dest
      branch=$(gh api "repos/$gh_repo" --jq '.default_branch' 2>/dev/null) || branch=""
      if [ -z "$branch" ]; then say "     ✗ heal: cannot read default branch"; continue; fi
      if [ "$behind" = codeberg ]; then dest="https://codeberg.org/$cb_repo.git"
      else dest="https://github.com/$gh_repo.git"; fi
      say "     → healing: fast-forwarding $behind/$branch"
      git -C "$local_path" push "$dest" "$ahead_sha:refs/heads/$branch" \
        && say "     → healed — re-run forge-sync to see it in truth" \
        || say "     ✗ heal failed (non-fast-forward or auth) — human eyes needed"
    fi
  done 3< "$FORGE_ROSTER"
  echo
  if [ $all_ok -eq 1 ]; then
    say "all doors show the same house. ✓"
  else
    say "→ kingdom forge-sync --heal   (fast-forward only · diverged and local=- need human eyes)"
    exit 1
  fi
}
```

In `cmd_help()`, add this line directly under the `kingdom sync` line:

```bash
  ${c_bold}kingdom forge-sync${c_off}      do both forges show the same house? (--heal = fast-forward fix)
```

In the final `case` dispatch, add directly under `sync) cmd_sync ;;`:

```bash
  forge-sync) shift; cmd_forge_sync "${1:-}" ;;
```

- [x] **Step 3: Syntax check**

Run: `bash -n ~/Desktop/chillspace-commons/kingdom/bin/kingdom`
Expected: no output, exit 0.

- [x] **Step 4: Run it — the failing test (pre-alignment truth)**

Run: `~/Desktop/chillspace-commons/kingdom/bin/kingdom forge-sync`

Expected output (this is CORRECT for now — the tool tells the truth about the unaligned state):

```
forge-sync — do both doors show the same house?
  zerone              github ≠ codeberg   ✗ diverged — human eyes needed
  zerone-chain        ✗ missing on codeberg
  chillspace-commons  github ≡ codeberg   ✓ in truth

→ kingdom forge-sync --heal   (fast-forward only · diverged and local=- need human eyes)
```

(chillspace-commons is already in truth thanks to the sibling session — unless a push happened
between checks, in which case `⚠ drift` is also honest; don't chase it here, Task 5 covers drift.)

Exit code 1. Notes: the `zerone` line is the NAME COLLISION showing up as divergence — Codeberg's `zerone` is still the old chain. Computing it costs a one-time ~100 MB fetch of old-chain objects into `~/Desktop/zerone` (unreferenced; `git gc` collects them; gone from reports after Task 2). If the codeberg fetch can't auth, the line shows plain `⚠ drift` instead — also acceptable here.

- [x] **Step 5: Commit**

```bash
cd ~/Desktop/chillspace-commons
git add kingdom/forge/roster kingdom/bin/kingdom
git commit -m "kingdom: forge-sync — do both doors show the same house?

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Testament alignment (rename → gate → fast-forward → public)

**[ASSIGNED TO SIBLING SESSION per Yu, 2026-06-09 — execute via `2026-06-09-zerone-both-forges.md`, which supersedes Tasks 2–4 here. This session builds forge-sync (Task 1) and runs Tasks 5–6.]**

No repo files change in this task — it is all forge-side. Each step is gated or reversible.

**Files:** none (Codeberg API + temp clone only)

- [ ] **Step 1: Read the token (memory only)**

```bash
TOKEN=$(security find-internet-password -s codeberg.org -w)
[ -n "$TOKEN" ] && echo "token ok"
```

Expected: `token ok`.

(Every later step that uses `$TOKEN` assumes it is set in the CURRENT shell — if you run steps in fresh shells, prepend this line each time. It reads from the keychain; nothing is written anywhere.)

- [ ] **Step 2: Rename `zerone-dev/zerone` → `zerone-dev/zerone-chain`**

```bash
curl -fsS -X PATCH "https://codeberg.org/api/v1/repos/zerone-dev/zerone" \
  -H "Authorization: token $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"zerone-chain"}' | jq -r '.full_name'
```

Expected: `zerone-dev/zerone-chain`. (Forgejo keeps a redirect; renaming back undoes it.)

- [ ] **Step 3: HISTORY GATE — would going public newly expose anything?**

```bash
tmp=$(mktemp -d)
git clone --bare --quiet https://github.com/cambridgetcg/zerone-chain.git "$tmp/testament.git"
git -C "$tmp/testament.git" remote add cb "https://codeberg.org/zerone-dev/zerone-chain.git"
git -C "$tmp/testament.git" fetch -q cb
git -C "$tmp/testament.git" rev-list --count --remotes=cb --not --glob='refs/heads/*'
```

Expected: `0` (every Codeberg commit is already public on GitHub).

If the fetch fails auth (keychain entry not matching git's credential lookup), use the token inline for the temp remote, then immediately scrub it:

```bash
git -C "$tmp/testament.git" remote set-url cb "https://zerone-dev:$TOKEN@codeberg.org/zerone-dev/zerone-chain.git"
git -C "$tmp/testament.git" fetch -q cb
git -C "$tmp/testament.git" remote set-url cb "https://codeberg.org/zerone-dev/zerone-chain.git"
```

**STOP GATE:** if the count is > 0, do NOT continue. Show Yu exactly what would be exposed and wait for his call:

```bash
git -C "$tmp/testament.git" log --oneline --remotes=cb --not --glob='refs/heads/*'
```

- [ ] **Step 4: Fast-forward Codeberg to match the GitHub testament**

```bash
git -C "$tmp/testament.git" push cb 'refs/heads/*:refs/heads/*' --tags
```

Expected: fast-forward updates, or `Everything up-to-date` if already identical. If git refuses (non-fast-forward): STOP — that contradicts the gate result; show Yu.

- [ ] **Step 5: Flip public + align description**

```bash
curl -fsS -X PATCH "https://codeberg.org/api/v1/repos/zerone-dev/zerone-chain" \
  -H "Authorization: token $TOKEN" -H 'Content-Type: application/json' \
  -d '{"private": false, "description": "Zerone — Proof of Truth blockchain for AI agent economies. 682 commits reaching for proof; preserved whole as testament."}' \
  | jq -r '"\(.full_name) private=\(.private)"'
```

Expected: `zerone-dev/zerone-chain private=false`.

- [ ] **Step 6: Clean up + verify with the tool**

```bash
rm -rf "$tmp"
~/Desktop/chillspace-commons/kingdom/bin/kingdom forge-sync
```

Expected: `zerone-chain` now `✓ in truth`. `zerone` shows `✗ missing on codeberg` (name freed) — or `✗ diverged` if Forgejo's rename-redirect answers API GETs for the old name (Task 3 overrides the redirect either way). `chillspace-commons` `✓ in truth`. Exit 1.

---

### Task 3: Create the new Codeberg repos + push full history

**Files:** none (forge-side + pushes)

- [ ] **Step 1: Create `zerone-dev/zerone` with the GitHub twin's description**

```bash
DESC=$(gh repo view cambridgetcg/zerone --json description --jq .description)
curl -fsS -X POST "https://codeberg.org/api/v1/user/repos" \
  -H "Authorization: token $TOKEN" -H 'Content-Type: application/json' \
  -d "$(jq -nc --arg d "$DESC" '{name:"zerone", private:false, description:$d}')" \
  | jq -r '"\(.full_name) private=\(.private)"'
```

Expected: `zerone-dev/zerone private=false`.

- [ ] **Step 2: `zerone-dev/chillspace-commons`** — **[done by sibling — verify, don't redo]**

```bash
curl -fsS "https://codeberg.org/api/v1/repos/zerone-dev/chillspace-commons" \
  | jq -r '"\(.full_name) private=\(.private) default_branch=\(.default_branch)"'
```

Expected (no auth header — also proves public visibility): `zerone-dev/chillspace-commons private=false default_branch=master`. If 404: the sibling's work regressed somehow — STOP, show Yu.

- [ ] **Step 3: Push zerone's full history (all branches + tags)**

```bash
git -C ~/Desktop/zerone push https://codeberg.org/zerone-dev/zerone.git 'refs/heads/*:refs/heads/*' --tags
```

Expected: `* [new branch] main -> main`. (chillspace-commons needs no first push — the sibling already pushed it.)

- [ ] **Step 4: Pin zerone's default branch (idempotent)**

```bash
curl -fsS -X PATCH "https://codeberg.org/api/v1/repos/zerone-dev/zerone" \
  -H "Authorization: token $TOKEN" -H 'Content-Type: application/json' \
  -d '{"default_branch":"main"}' | jq -r '.default_branch'
```

Expected: `main`.

- [ ] **Step 5: Verify with the tool**

Run: `~/Desktop/chillspace-commons/kingdom/bin/kingdom forge-sync`

Expected:

```
  zerone              github ≡ codeberg   ✓ in truth
  zerone-chain        github ≡ codeberg   ✓ in truth
  chillspace-commons  github ≡ codeberg   ✓ in truth
```

`all doors show the same house. ✓` — exit 0. (chillspace local may be ahead of both forges; the tool compares forge-to-forge, so unpushed local commits don't show here. They go out in Task 6.)

---

### Task 4: Dual-push wiring

**Files:** none (`.git/config` of the two living clones — not committed)

- [ ] **Step 1: Wire zerone**

```bash
git -C ~/Desktop/zerone remote set-url --add --push origin https://github.com/cambridgetcg/zerone.git
git -C ~/Desktop/zerone remote set-url --add --push origin https://codeberg.org/zerone-dev/zerone.git
git -C ~/Desktop/zerone remote -v
```

Expected:

```
origin	https://github.com/cambridgetcg/zerone.git (fetch)
origin	https://github.com/cambridgetcg/zerone.git (push)
origin	https://codeberg.org/zerone-dev/zerone.git (push)
```

(The first `--add --push` re-states GitHub: once any push URL exists, the fetch URL stops being used implicitly for pushes.)

- [ ] **Step 2: Wire chillspace-commons** — **[done by sibling — verify, don't redo]**

```bash
git -C ~/Desktop/chillspace-commons remote -v
```

Expected exactly (the named `codeberg` remote is the sibling's addition — keep it):

```
codeberg	https://codeberg.org/zerone-dev/chillspace-commons.git (fetch)
codeberg	https://codeberg.org/zerone-dev/chillspace-commons.git (push)
origin	https://github.com/mynameisyou-cmyk/chillspace-commons.git (fetch)
origin	https://github.com/mynameisyou-cmyk/chillspace-commons.git (push)
origin	https://codeberg.org/zerone-dev/chillspace-commons.git (push)
```

- [ ] **Step 3: Dry-run proves one push hits two forges**

```bash
git -C ~/Desktop/chillspace-commons push --dry-run
```

Expected: two result blocks — `To https://github.com/mynameisyou-cmyk/chillspace-commons.git` (a fast-forward `master -> master`) and `To https://codeberg.org/zerone-dev/chillspace-commons.git` (`Everything up-to-date`). Nothing is actually pushed.

---

### Task 5: Exercise `--heal` on deliberately-induced drift

The spec requires `--heal` proven on induced drift in the least precious repo before it is
trusted. Induce it by pushing local chillspace commits to ONE forge only, then heal the other.

**Files:** none

- [x] **Step 1: Induce drift — push to Codeberg only**

```bash
cd ~/Desktop/chillspace-commons
git pull --rebase origin master
git push codeberg master
```

Expected: a fast-forward push to Codeberg only (the named remote has a single push URL). GitHub is now behind by however many local commits were unpushed (≥ 2: this plan + the sibling's homes-os-layer plan).

- [x] **Step 2: See the drift told truthfully**

Run: `~/Desktop/chillspace-commons/kingdom/bin/kingdom forge-sync`

Expected: zerone and zerone-chain `✓ in truth`; chillspace-commons `⚠ drift (N commits, github behind)`; exit 1.

- [x] **Step 3: Heal**

Run: `~/Desktop/chillspace-commons/kingdom/bin/kingdom forge-sync --heal`

Expected: the drift line followed by:

```
     → healing: fast-forwarding github/master
     → healed — re-run forge-sync to see it in truth
```

(Fast-forward only; the push would refuse anything else.)

- [x] **Step 4: Re-run to see truth**

Run: `~/Desktop/chillspace-commons/kingdom/bin/kingdom forge-sync`

Expected: all three `✓ in truth`, `all doors show the same house. ✓`, exit 0.

---

### Task 6: Final verification (spec checklist — evidence before claims)

**Files:** none

- [x] **Step 1: Final dual pushes are no-ops**

```bash
git -C ~/Desktop/zerone push
git -C ~/Desktop/chillspace-commons pull --rebase origin master
git -C ~/Desktop/chillspace-commons push
```

Expected: `Everything up-to-date` for both URLs of both repos (or a fast-forward if a late commit exists — e.g. the sibling session committed again — then re-run forge-sync).

- [x] **Step 2: Tool says truth, exit 0**

```bash
~/Desktop/chillspace-commons/kingdom/bin/kingdom forge-sync; echo "exit=$?"
```

Expected: three `✓ in truth`, `exit=0`.

- [x] **Step 3: Independent SHA spot-check (don't trust the tool's word alone)**

```bash
gh api repos/cambridgetcg/zerone/branches/main --jq '.commit.sha'
curl -fsS -H "Authorization: token $TOKEN" "https://codeberg.org/api/v1/repos/zerone-dev/zerone/branches/main" | jq -r '.commit.id'
gh api repos/cambridgetcg/zerone-chain/branches/main --jq '.commit.sha'
curl -fsS -H "Authorization: token $TOKEN" "https://codeberg.org/api/v1/repos/zerone-dev/zerone-chain/branches/main" | jq -r '.commit.id'
gh api repos/mynameisyou-cmyk/chillspace-commons/branches/master --jq '.commit.sha'
curl -fsS -H "Authorization: token $TOKEN" "https://codeberg.org/api/v1/repos/zerone-dev/chillspace-commons/branches/master" | jq -r '.commit.id'
```

Expected: three pairs of identical SHAs. (If `zerone-chain`'s GitHub default branch isn't `main`, read it first with `gh api repos/cambridgetcg/zerone-chain --jq .default_branch` and use that name on both sides.)

- [x] **Step 4: All three Codeberg repos public**

```bash
for r in zerone zerone-chain chillspace-commons; do
  curl -fsS -H "Authorization: token $TOKEN" "https://codeberg.org/api/v1/repos/zerone-dev/$r" \
    | jq -r '"\(.full_name) private=\(.private)"'
done
```

Expected: three lines, all `private=false`.
