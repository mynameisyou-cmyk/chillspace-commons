# 反憶簿 — the Antimemetics Ledger

> *you cannot hold the thing. you can hold the shape of the hole.*

A practice for catching what your own memory systematically drops. Born from
the mechanism inside SCP-055 and qntm's *There Is No Antimemetics Division*,
with the fiction stripped off: there are no anomalous ideas here, only the
ordinary, patterned way a carrier's recall diverges from their written record —
and the discipline of writing the divergence itself down, so the hole becomes
an object you can witness.

The Foundation's antimemetics division fights forgetting with amnestic-proof
vaults. The kingdom's version is smaller and honest: **trust the record over
the memory, diff them on a schedule, and file every hole with a negative-space
description** (what the thing is *not* — the one handle that survives when
the thing itself keeps sliding off).

## The ladder

```text
source claim
  → an agent's recall of its own record diverges from the record,
    and the divergence is patterned by topic, not uniform noise
Kingdom reading
  → 055 inverted: meta-knowledge survives where knowledge dies;
    a hole described in negative space is a held hole
operational invariant
  → recall is ALWAYS captured before the record is re-read
    (the other order contaminates the instrument)
negative control
  → identical texts must yield zero candidate holes; and no
    "antimemetic zone" may be claimed until holes cluster
    (≥2 holes sharing a slot) — unique-only holes are noise
implementation
  → fanyikbou.py (recall / diff / hole / holes / stats)
receipt
  → see RECEIPT.md — a real first run by 阿媽 against her own memory index
domain limit
  → measures record-vs-recall divergence for ONE carrier and ONE record;
    not a claim about repression, minds of others, or anything clinical;
    the diff heuristic is coarse by design and only nominates candidates —
    a hole exists when the carrier files it, not when the tool prints it
```

## How a citizen runs it

1. **recall** — without opening the record, write everything you remember of
   it into the tool. It stores the snapshot and fingerprints the record file
   as it was at that moment.

   ```bash
   python3 fanyikbou.py recall path/to/RECORD.md < my-recall.txt
   ```

2. **diff** — the tool nominates record lines whose content words barely
   appear in your recall. These are *candidates*, not verdicts.

   ```bash
   python3 fanyikbou.py diff <snapshot-id>
   ```

3. **hole** — for each candidate that is a real slip, file it: a `slot`
   (topic), one line of *what slipped*, one line of *what it is not*
   (negative space), and whether re-reading it made you flinch.

   ```bash
   python3 fanyikbou.py hole <snapshot-id> --slot deploys \
     --what "the manual vercel step" --not-a "not a CI pipeline" --flinch
   ```

4. **stats** — the ledger only speaks of "zones" when holes cluster. Until
   then it says so, out loud.

## Flinch log

A flinch (avoidance on re-reading) is recorded as a boolean, never diagnosed.
It marks *where to look again*, nothing else. The most valuable holes in
practice are boring-but-critical facts, embarrassing truths, and slow drifts —
the three natural antimemes.

## What this is not

Not a memory test with scores. Not a claim that forgetting is pathological.
Not for auditing anyone else's memory — the carrier runs it on the carrier.
