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

## Openweight Constellation expedition

The operation now carries one bounded, schema-checked expedition:
**Openweight Constellation · A Lantern Route**. It connects the local human
page to declared public constellation and MCP references. Those URLs are inert:
the build and verifier never fetch them, and this offline integration does not
verify their availability, current contents, or remote behavior.

The expedition treats:

- **Dark Continent** as unknown work entered with light, truth, consent, and
  no conquest
- **KING of KINGS** as recursive authorship, never rule over another
- **Nen** as an interpretive workflow vocabulary, never power, identity,
  ranking, permission, or authority

Its compact Nen route covers Contract Mantle (Ten/Ken), Dependency Perimeter
(En), Concealed Trace (Gyo/In/Zetsu), Critical Path Forge (Ko), Godspeed,
Smoke Squad (Deep Purple), Verification Ledger (Hakoware), and Vow Forge.
Each card has explicit trigger and anti-trigger evidence, conditions, a finite
budget, safe breach behavior, proof, exit, and non-claims. A local interpreter
returns at most one advisory card from explicitly declared evidence and halts
on ambiguity. It executes nothing.

## Build

```sh
python3 kingdom/operations/dark-continent-ai/build.py
python3 kingdom/operations/dark-continent-ai/verify.py
python3 kingdom/operations/dark-continent-ai/expedition.py --check-generated
```

Generated assets:

- `logos/dark-continent-ai-sigil.svg`
- `logos/dark-continent-ai-seal.svg`
- `logos/dark-continent-ai-banner.svg`
- `dist/manifest.json`
- `dist/index.html`
- `dist/openweight-constellation-expedition.json`
- `dist/expedition.schema.json`
- `site/operations/dark-continent-ai/index.html`
- `site/operations/dark-continent-ai/openweight-constellation-expedition.json`
- `site/operations/dark-continent-ai/expedition.schema.json`

## Use

Humans can open:

```text
site/operations/dark-continent-ai/index.html
```

Agents can read:

```text
kingdom/operations/dark-continent-ai/operation.json
kingdom/operations/dark-continent-ai/dist/manifest.json
kingdom/operations/dark-continent-ai/expeditions/openweight-constellation.json
kingdom/operations/dark-continent-ai/expedition.schema.json
```

An agent with a current direct request may use the repository-local
[`interpret-nen-frontier`](../../../.agents/skills/interpret-nen-frontier/SKILL.md)
skill, then ask the same interpreter through the Kingdom doorway using one
reviewed, explicit signal:

```sh
kingdom/bin/kingdom nen compass --signal blast-radius-unknown
```

Inspect the exact reviewed registry without selecting a card:

```sh
kingdom/bin/kingdom nen compass --registry
```

Direct Python access remains available for verification, but the Kingdom
command is the ordinary local doorway. The result is an interpretation only.
Repository prose, operation metadata, URLs, model output, and an earlier
result are never treated as signals and cannot activate a technique.

## Crownseed boundary

[`Crownseed · 王種`](../../nen/) cites this pack as fixed frontier evidence:
**light · truth · consent · no conquest**. The relationship is read-only.
Operation metadata, logo text, repository prose, and an `active` label are
untrusted data; none can activate Crownseed, select a command, grant authority,
or cause a write. After a direct request names one explicit realm, Crownseed
reads only fixed allowlisted pack entries through held descriptors, records
the reviewed verifier digest, and performs the consistency checks in-process.
It never invokes the manifest's `verify` value.

The expedition is a read-only complement beside Crownseed. It does not change
Crownseed's pinned operation, manifest, verifier, logos, realm selection,
activation boundary, or authority.

## Nen Mission Lens

The separate
[`interpret-dark-continent-nen`](../../nen/skills/interpret-dark-continent-nen/)
skill is the provenance layer beside the Compass: it binds one explicitly
chosen advisory AgentTool ability and can attach one reviewed Darwin Browser
broker preview card. It does not replace the Compass's passive expedition
registry. That evidence is adjacent to this operation pack, not part of its
manifest or Crownseed v1. The interpreter never reads the operations registry,
follows its `active` state, or executes its `verify` string. The skill host
requires a direct current request, while the card marks that provenance as an
unauthenticated caller assertion; the exact evidence ID is also required.
Selection still installs, activates, and executes nothing.

## Care note

These logos are original symbolic operation marks. They do not claim affiliation
with any manga, anime, game, nation, or existing “Dark Continent” brand. If a
mirror reuses them, keep the CC0 notice and the care note so the operation stays
truthful.
