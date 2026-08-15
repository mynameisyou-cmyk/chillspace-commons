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
| Codeberg | <https://codeberg.org/zerone-dev/chillspace-commons> | **held** — fetch works, push deliberately disabled (`codeberg-push-disabled://policy-hold` as the push URL); frozen at `269efb6` (2026-08-01) and drifting behind since |
| GitLab | <https://gitlab.com/mynameisyou-cmyk/chillspace-commons> | **unverified** — the remote exists in the wiring, but no credential on this machine can fetch it, so its freshness is honestly unknown |

The live wiring is git itself — remotes are the state, this file is the witness:

- pushes currently land on **GitHub only**; the earlier dual-push (both forges from
  one `git push origin`) has been dismantled;
- `kingdom publish` speaks at every door explicitly and reports per home;
- `kingdom homes` shows the doors as git sees them, push URLs and all — including
  the hold, which it already reports truthfully.

### The Codeberg hold

Someone deliberately set the Codeberg push URL to the sentinel
`codeberg-push-disabled://policy-hold` — a crafted, intentional act, not an
accident. **No reason was written down anywhere findable** (repo, Sol's hearth,
the collab journal): that gap is itself a defect this witness now records. Until
the reason is recovered or the keeper decides, the hold stands — overriding an
explicit control without knowing why it exists is how protections quietly die.

To lift it, a human decides, then:

```sh
git remote set-url --push codeberg https://codeberg.org/zerone-dev/chillspace-commons.git
kingdom forge-sync --heal   # fast-forward only; refuses divergence
```

If the hold is meant to be permanent, retire the Codeberg row to "testament,
frozen" instead — either way the witness must match the wire.

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
