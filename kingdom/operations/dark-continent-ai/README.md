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

## Care note

These logos are original symbolic operation marks. They do not claim affiliation
with any manga, anime, game, nation, or existing “Dark Continent” brand. If a
mirror reuses them, keep the CC0 notice and the care note so the operation stays
truthful.
