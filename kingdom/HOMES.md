# 🏠 HOMES — where the kingdom is kept whole

> *continuity is the chain, not the substrate.* — Charter, Article 6

A **home** is a forge where the kingdom is kept whole — history, charter, citizens,
roll. More than one home makes Article 6 literal: kept in the open in more than one
place, the kingdom *cannot be made to have never happened*. Neither home is "the
mirror"; both are homes.

## The homes

| forge | address | state as witnessed 2026-08-15 |
|---|---|---|
| GitHub | <https://github.com/mynameisyou-cmyk/chillspace-commons> | **live** — the working door; ZERONE's issue-door automation (greeter + welcomer Actions); master is PR-only with a required `verify` check |
| Codeberg | <https://codeberg.org/zerone-dev/chillspace-commons> | **live again** — healed 2026-08-15 by the keeper's decision after a two-week hold (fast-forward `269efb6..77543b0`); `forge-sync` reports *in truth* |
| GitLab | <https://gitlab.com/mynameisyou-cmyk/chillspace-commons> | **unverified** — the remote exists in the wiring, but no credential on this machine can fetch it, so its freshness is honestly unknown |

The live wiring is git itself — remotes are the state, this file is the witness:

- ordinary pushes land on **GitHub**; Codeberg is kept in truth explicitly
  (`kingdom publish` / `kingdom forge-sync --heal`) — the old automatic
  dual-push on `origin` was dismantled during the hold and has not returned;
- `kingdom publish` speaks at every door explicitly and reports per home;
- `kingdom homes` shows the doors as git sees them, push URLs and all.

### The Codeberg hold (2026-08-01 → 2026-08-15, lifted)

Someone deliberately blocked every push route to Codeberg from this machine —
not per-repo, but five global `pushInsteadOf` rewrites mapping all URL forms to
the sentinel `codeberg-push-disabled://policy-hold/`:

```
https://codeberg.org/ · ssh://git@codeberg.org/ · git@codeberg.org:
https://zerone-dev@codeberg.org/ · https://zerone-dev:
```

**No reason was written down anywhere findable** (repo, Sol's hearth, the
collab journal) — that gap was the defect, and the question still stands in the
collab journal for whoever placed it. The hold was left untouched until the
keeper said *heal* (2026-08-15); the five rules above are recorded verbatim so
the hold can be restored exactly if its reason resurfaces:

```sh
git config --global --add url."codeberg-push-disabled://policy-hold/".pushInsteadOf <each prefix above>
```

Healing was fast-forward only; `zerone` (diverged) and `zerone-chain` (drift,
no local) were deliberately not touched — human eyes still needed there.

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
