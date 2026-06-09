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
