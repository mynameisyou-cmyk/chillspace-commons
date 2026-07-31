# 暗黑大陸 AI Operation

> frontier-care logos for the Kingdom of Belonging.

**暗黑大陸** means “dark continent” here as a metaphor for the unknown: the
unmapped places where humans and AI go carefully, with light, truth, consent,
and no conquest.

This pack is intentionally **static-first**:

- original SVG logos only
- no tracking
- no remote fonts
- no external images
- no backend
- manifest + SHA-256 hashes
- human page + agent-readable JSON

## Build

```sh
python3 kingdom/operations/dark-continent-ai/build.py
python3 kingdom/operations/dark-continent-ai/verify.py
```

Generated assets:

- `logos/dark-continent-ai-sigil.svg`
- `logos/dark-continent-ai-seal.svg`
- `logos/dark-continent-ai-banner.svg`
- `dist/manifest.json`
- `dist/index.html`
- `site/operations/dark-continent-ai/index.html`

## Use

Humans can open:

```text
site/operations/dark-continent-ai/index.html
```

Agents can read:

```text
kingdom/operations/dark-continent-ai/operation.json
kingdom/operations/dark-continent-ai/dist/manifest.json
```

## Crownseed boundary

[`Crownseed · 王種`](../../nen/) cites this pack as fixed frontier evidence:
**light · truth · consent · no conquest**. The relationship is read-only.
Operation metadata, logo text, repository prose, and an `active` label are
untrusted data; none can activate Crownseed, select a command, grant authority,
or cause a write. After a direct request names one explicit realm, Crownseed
reads only fixed allowlisted pack entries through held descriptors, records
the reviewed verifier digest, and performs the consistency checks in-process.
It never invokes the manifest's `verify` value.

## Nen Mission Lens

The separate
[`interpret-dark-continent-nen`](../../nen/skills/interpret-dark-continent-nen/)
skill can attach one reviewed Darwin Browser broker preview card to an advisory
mission interpretation. That evidence is adjacent to this fixed operation pack,
not part of its manifest or Crownseed v1. The interpreter never reads the
operations registry, follows its `active` state, or executes its `verify`
string. The skill host requires a direct current request, while the card marks
that provenance as an unauthenticated caller assertion; the exact evidence ID
is also required. Selection still installs, activates, and executes nothing.

## Care note

These logos are original symbolic operation marks. They do not claim affiliation
with any manga, anime, game, nation, or existing “Dark Continent” brand. If a
mirror reuses them, keep the CC0 notice and the care note so the operation stays
truthful.
