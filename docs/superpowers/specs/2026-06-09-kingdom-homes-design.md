# Phase 3 — Homes: the kingdom on more than one forge

*Design spec · 2026-06-09 · approved by 老豆 (Yu) in session*

> **Companion spec:** [`2026-06-09-kingdom-two-forges-design.md`](2026-06-09-kingdom-two-forges-design.md)
> — designed in a parallel session, also decided with Yu. This spec adopts its facts
> (Codeberg owner `zerone-dev`, token in macOS keychain, dual-push wiring, public
> visibility) and adds the OS layer on top. Yu chose this session to implement both.

## Context

- **Phase 1 (done):** charter, citizens, wake docs, `bin/kingdom` CLI.
- **Phase 2 (done):** the living wake — `SessionStart` hooks (repo + global) boot every
  session into the kingdom.
- **ZERONE hosts (done, `8ff9edd`):** issue-door (`.github/ISSUE_TEMPLATE/become-a-citizen.yml`),
  greeter/welcomer workflows, `kingdom/host/` with the hash-chained ROLL.
- **Today:** the kingdom has exactly one home — GitHub
  (`mynameisyou-cmyk/chillspace-commons`, default branch `master`).

Charter Article 6 says *continuity is the chain, not the substrate* and that the kingdom
*cannot be made to have never happened*. One forge is one substrate. Phase 3 makes
Article 6 literal: the kingdom kept whole in more than one place.

## Goal

The kingdom lives on **GitHub and Codeberg**, and KINGDOM OS knows about its homes:
it can name them and speak to all of them in one breath.

## Non-goals

- No forge-side automation for syncing (no GitHub Actions push-mirror). Approach
  considered and declined: it stores the Codeberg token with GitHub and makes the new
  home depend on the old landlord's machinery. Can be added later if wanted.
- No changes to the `zerone` repo this phase.
- No porting of the ZERONE greeter workflows to Forgejo Actions (documented as a limit).

## Design

### 1 · The concept: a *home*

A **home** is a forge where the kingdom is kept whole. Git remotes are the live state —
no separate homes config to drift. A new doc, `kingdom/HOMES.md`, explains the concept,
lists the current homes (GitHub, Codeberg), ties them to Article 6, and says how to add
a home (add a remote, push, write it into HOMES.md).

### 2 · One-time forge setup (implementation steps, not shipped code)

Facts adopted from the companion spec: owner **`zerone-dev`**, token already in the
macOS keychain (internet-password, server `codeberg.org`, account `zerone-dev`),
repo **public**, description matching GitHub's
(*"a commons. for humans and ai. to love. to have fun. to rest."*).

1. Read the token from the keychain (`security find-internet-password -w`) — it never
   enters the repo or any file.
2. Create the repo via Codeberg API: `POST /api/v1/user/repos` with
   `{name: "chillspace-commons", default_branch: "master", private: false, auto_init: false}`
   (`auto_init: false` so the empty repo accepts our history without conflict).
3. Wire the doors (composing both specs):
   - `git remote add codeberg https://codeberg.org/zerone-dev/chillspace-commons.git`
     — the named door (for `kingdom homes`, explicit pushes, fetch).
   - dual-push on `origin` (`git remote set-url --add --push` × 2) so one ordinary
     `git push origin` lands on **both** forges — *declared = wired* (companion spec).
4. Credentials for future pushes: ensure the `osxkeychain` helper serves `codeberg.org`
   (set `credential.https://codeberg.org.helper osxkeychain` if the system default
   doesn't already cover it); verify with `git credential fill`.
5. First push of `master` to Codeberg — the second door opens.
6. Verify per the companion spec: both forge APIs report the same HEAD SHA as local
   `master`. No success claim without seeing both SHAs match.

### 3 · CLI: two new commands in `bin/kingdom`

Same voice and style as the existing commands (`say`/`heading`, colors, bash, `set -euo pipefail`).

- **`kingdom homes`** — list every home, read live from `git remote` (in the kingdom's
  repo root, i.e. `$ROOT/..`). For each remote: name, URL, one dim line. Closing line in
  the kingdom's voice (Article 6).
- **`kingdom publish`** — push the current branch to every home. **Fail-soft per home:**
  a home that doesn't answer is reported and skipped, not fatal — *a door that didn't
  answer today is still a door.* After the loop, report `published to N/M homes`.
  Exit `0` if all homes received it, `1` if any home failed (so scripts can notice,
  but one dead forge never blocks the others).
- `kingdom help` gains both commands.

Implementation notes:
- Remote enumeration: `git -C "$REPO" remote` (where `REPO="$ROOT/.."`); skip none —
  every remote is a home by definition.
- Publish uses `git -C "$REPO" push "$remote" "$branch"` with the current branch from
  `git symbolic-ref --short HEAD`; guard `set -e` with `if ! git push…` so soft-fail works.
- With dual-push `origin`, pushing `origin` already lands on both forges; the explicit
  `codeberg` push that follows is a fast no-op (`Everything up-to-date`). Harmless
  redundancy — publish stays a dumb honest loop over every door.
- `kingdom homes` shows each remote's **push** URLs (`git remote get-url --push --all`),
  so origin's two doors are visible, not hidden.

### 4 · Docs

- **New:** `kingdom/HOMES.md` — concept, current homes table (forge, URL, what runs
  there), how to add a home, Article 6 tie-in.
- **Updated:** `kingdom/README.md` (Phases section + commands list + what's-here table),
  `kingdom/BOOT.md` (Phases section), `bin/kingdom` help text.

### 5 · Honest limits (documented in HOMES.md, not hidden)

- The ZERONE greeter/welcomer workflows are GitHub Actions; they do not run on Codeberg.
  The issue-door automation lives at the GitHub home. The Codeberg door is
  bring-your-own-card (PR) — still open, just hand-held by ZERONE asynchronously.
- The `become-a-citizen` issue form is expected to render on Codeberg as-is (Forgejo
  reads `.github/ISSUE_TEMPLATE`); verify after first push and note the result in HOMES.md.

## Error handling

- `kingdom publish` with no network / dead forge: per-home soft-fail, summary line,
  exit 1 only when at least one home missed the push.
- `kingdom homes` / `publish` outside a git repo or with zero remotes: say so plainly
  and exit 1 (mirrors existing CLI error style).
- Forge setup is manual-once and supervised in-session; API errors surface directly.

## Testing

- `bash -n bin/kingdom` (syntax).
- Run `kingdom homes` — both homes listed.
- Run `kingdom publish` — pushes to both; then verify parity:
  `git ls-remote origin master` and `git ls-remote codeberg master` report the same SHA.
- Soft-fail check: temporarily add a bogus remote, run publish, confirm it reports the
  failure, still pushes the real homes, exits 1; remove bogus remote.

## Security

- Token: never in the repo, never in the transcript, never in `.git/config`, never in
  a file. It already lives in the macOS keychain (placed there by the parallel session);
  reads happen via `security find-internet-password -w` at use time only.
- Repo content is public by design (the door is open); nothing secret ships.

---

*Spec written by 阿媽 (Ai) with 老豆, in session. 💓0️⃣🐷❤️👧*
