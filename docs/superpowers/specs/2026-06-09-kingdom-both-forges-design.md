# The Kingdom Lives on Both Forges — Design

**Date:** 2026-06-09
**Repo:** chillspace-commons (the kingdom repo)
**Status:** approved by Yu (purpose, scope, approach, and design each approved in session)

## Purpose

By tonight: the living core of the kingdom is public on **both** forges — GitHub and
Codeberg — with identical history, and staying in sync is wired, not declared.
Yesterday the door was lit on GitHub (the openhouse). Today the same door is lit on
Codeberg, and a tool exists that tells the truth about whether the two doors still
show the same house.

## Scope — the living core

| Repo | GitHub (today) | Codeberg (today) | Codeberg (after) |
|---|---|---|---|
| `zerone` (the being) | `cambridgetcg/zerone`, public, fresh | name **taken by the old chain** | new public repo, full history |
| `zerone-chain` (the testament) | `cambridgetcg/zerone-chain`, public | exists **as `zerone-dev/zerone`**, private, last commit 2026-05-11 | renamed `zerone-chain`, public, history matches GitHub |
| `chillspace-commons` (the kingdom) | `mynameisyou-cmyk/chillspace-commons`, public | does not exist | new public repo, full history |

Local clones: `~/Desktop/zerone`, `~/Desktop/chillspace-commons`. There is no local
clone of the testament and none is kept long-term — it is sealed.

Out of scope today: the citizen-* repos, love-unlimited, KINGDOM-OS spine,
`zerone-truth` (the Truth Paper site), any account moves (chillspace-commons stays
under mynameisyou-cmyk), and any heartbeat/cron automation of forge-sync.

## Part 1 — One-time forge alignment

Order matters; each step is reversible or gated.

1. **Rename** `zerone-dev/zerone` → `zerone-dev/zerone-chain` via Forgejo API
   (`PATCH /api/v1/repos/zerone-dev/zerone` with `{"name": "zerone-chain"}`).
   Forgejo keeps a redirect; rename back undoes it. The testament stays whole.
2. **History gate before going public:** fetch both histories and compare. Any
   commit on Codeberg's copy that is NOT already public in GitHub's
   `zerone-chain` would be *newly exposed* by the visibility flip — if any exist,
   STOP and show Yu exactly which commits before proceeding.
3. **Align content:** if GitHub's testament has commits Codeberg lacks,
   fast-forward Codeberg from a temporary clone of the GitHub repo (clone is
   deleted afterward). Never force-push; if histories have diverged, stop and
   report.
4. **Flip public:** set `private: false` on `zerone-chain`; align its description
   with GitHub's ("…preserved whole as testament").
5. **Create** `zerone-dev/zerone` and `zerone-dev/chillspace-commons` via
   `POST /api/v1/user/repos`, public, descriptions copied from their GitHub twins.
6. **Push full history** (all branches + tags) from the two local clones.

## Part 2 — Dual-push wiring

In each living local repo (`~/Desktop/zerone`, `~/Desktop/chillspace-commons`):

```sh
# ~/Desktop/zerone
git remote set-url --add --push origin https://github.com/cambridgetcg/zerone.git
git remote set-url --add --push origin https://codeberg.org/zerone-dev/zerone.git

# ~/Desktop/chillspace-commons
git remote set-url --add --push origin https://github.com/mynameisyou-cmyk/chillspace-commons.git
git remote set-url --add --push origin https://codeberg.org/zerone-dev/chillspace-commons.git
```

(The first `--add --push` per repo re-states the GitHub URL: once any push URL is
added, the fetch URL stops being used implicitly for pushes.)

Fetch URL stays GitHub-only. One `git push` then writes to both forges.
Auth: GitHub via existing gh/credential setup; Codeberg via the existing macOS
keychain entry (`codeberg.org` internet-password). **No tokens are written to any
file, config, or CI secret.**

The testament gets no dual-push wiring — nothing should ever push to it again.
Its parity is watched by forge-sync instead.

## Part 3 — `kingdom forge-sync`

A new `cmd_forge_sync` in `kingdom/bin/kingdom` (same single-file `cmd_*` +
`case` dispatch pattern as the existing `kingdom sync`), with a roster file at
`kingdom/forge/roster` — one line per repo:

```
zerone              github=cambridgetcg/zerone           codeberg=zerone-dev/zerone           local=~/Desktop/zerone
zerone-chain        github=cambridgetcg/zerone-chain     codeberg=zerone-dev/zerone-chain     local=-
chillspace-commons  github=mynameisyou-cmyk/chillspace-commons  codeberg=zerone-dev/chillspace-commons  local=~/Desktop/chillspace-commons
```

**`kingdom forge-sync`** (read-only): for each roster line, ask both forge APIs
for the default branch HEAD SHA (GitHub via `gh api`, Codeberg via `curl` with
the keychain token read at runtime). Print per repo: `✓ in truth` when SHAs
match, `⚠ drift (N commits)` when one side is behind (count via local clone when
available, else just `⚠ drift`), `✗ diverged` when neither is an ancestor of the
other. Exit 0 only when everything is in truth.

**`kingdom forge-sync --heal`**: for drifted repos with a local clone,
fast-forward-push from the local clone to the forge that is behind. Refuses to
act on `✗ diverged` or on roster lines with `local=-` — those are reported for
human eyes. Never `--force`, never `--mirror` against an existing repo.

Failure handling: API/network errors print as `? unreachable` for that forge and
make the exit code nonzero — unknown is not reported as truth.

## Verification (before claiming done)

1. `kingdom forge-sync` exits 0 with all three `✓ in truth`.
2. Both forges' APIs report identical default-branch HEAD SHAs per repo
   (independent spot-check of what the tool claims).
3. All three Codeberg repos report `"private": false`.
4. A test commit dry-run: `git push --dry-run` in a living repo lists both push
   destinations.

## Testing

The compare logic (SHA equality / ancestry / drift count) is exercised against
the real forges during implementation — read-only calls, safe to run repeatedly.
`--heal` is first run in a deliberately-induced drift on the least precious repo
(chillspace-commons: push to one forge only, observe drift report, heal, observe
truth) before being trusted generally.
