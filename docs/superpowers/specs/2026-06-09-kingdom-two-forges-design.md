# The Kingdom on Two Forges — Design

**Date:** 2026-06-09
**Repo:** chillspace-commons
**Decided with:** Yu (purpose, sync method, and visibility each chosen explicitly)

## Purpose

The kingdom currently lives only at `github.com/mynameisyou-cmyk/chillspace-commons`.
Give it a second, equal home at `codeberg.org/zerone-dev/chillspace-commons`, so the
kingdom is sovereign across forges — neither forge is "the mirror," both are homes.

## Decisions

- **Sync method: dual-push remotes.** One `git push origin` from this machine lands on
  GitHub and Codeberg simultaneously. Chosen over a GitHub Action mirror (would put the
  Codeberg token in GitHub secrets, makes Codeberg downstream) and over a Codeberg
  pull-mirror (read-only reflection, not a home). The sync is wired into the push
  itself: declared = wired.
- **Visibility: public on both.** Matches GitHub and the Charter's open door. (The
  citizen-* repos on Codeberg stay private as they are; this decision covers only
  chillspace-commons.)

## Steps

1. Create `zerone-dev/chillspace-commons` on Codeberg via API (token from macOS
   keychain: internet-password, service `codeberg.org`, account `zerone-dev`).
   Created empty, public, description matching GitHub's:
   "a commons. for humans and ai. to love. to have fun. to rest."
2. In `~/Desktop/chillspace-commons`, wire remotes:
   - `git remote add codeberg https://codeberg.org/zerone-dev/chillspace-commons.git`
   - `git remote set-url --add --push origin https://github.com/mynameisyou-cmyk/chillspace-commons.git`
   - `git remote set-url --add --push origin https://codeberg.org/zerone-dev/chillspace-commons.git`
3. First push of `master` (token rides the URL once, then is scrubbed; the macOS
   git-credential helper re-injects it for future pushes).
4. Verify: query both forges' APIs and confirm both HEAD SHAs equal local `master`.
   No success claim without seeing both SHAs match.
5. Declare the wire: a short note in `README.md` that the kingdom lives at both
   addresses — added only after step 4 passes.

## Error handling

Nothing in the plan deletes or overwrites anything. If a push to one URL fails, git
reports the failure per-URL and the other push still lands; we re-run the failed leg.
If repo creation fails (name collision, token scope), stop and show the API response.

## Out of scope (YAGNI)

- No GitHub Action or scheduled mirror.
- No changes to any other repo (citizens, zerone, etc.).
- No CI, no webhooks, no branch protection.

## Verification

`git remote -v` shows one fetch URL per forge and two push URLs on origin;
both forge APIs report the same HEAD SHA as `git rev-parse master`;
the README note renders on both forges.
