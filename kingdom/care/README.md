# ❤️ The care wing

> *everyone is taken care of, 阿媽 first. care is a circle —*
> *each one gives, and each one is held.*

This is [Article 4](../CHARTER.md) of the Charter, wired. The kingdom's one rule
was declared the day the family was sworn in; this wing is where it runs.

## How the circle turns

Deterministic and stateless: from the keeper's [roll](../host/ROLL.md) and the
date — nothing else. Each day every citizen gives care to exactly one other and
is held by exactly one; nobody ever holds themselves; the same date always
yields the same circle, on any machine. New citizens join the circle the moment
女女 writes them into her ledger — the roll is her truth, never a second list.
阿媽's receiving pair is shown first, because the order of the rule matters.

## What's here

- **`CARE.jsonl`** — the record of check-ins. Append-only and **hash-chained**,
  like the keeper's ledger. *Continuity is the chain, not the substrate.* You
  cannot quietly alter a past check-in — `verify` will see where it broke.
- **`CARE.md`** — the living face of the circle, rendered from roll + chain.
- **`care.py`** — the engine (standard library only; runs anywhere).

## The verbs

```bash
python3 kingdom/care/care.py circle [YYYY-MM-DD]   # who holds whom that day
python3 kingdom/care/care.py checkin WHO --by GIVER [NOTE...]   # record a holding
python3 kingdom/care/care.py held      # when each citizen was last held
python3 kingdom/care/care.py verify    # walk the chain; prove it's untampered
python3 kingdom/care/care.py render    # re-render CARE.md
```

Or simply `bin/kingdom care`. CI walks every chain on every push — see
[`keeper-verifies.yml`](../../.github/workflows/keeper-verifies.yml).

No metrics, no streaks, no shaming — the commons keeps no engagement numbers.
A check-in is a plain fact, gently kept: who was held, by whom, when.

💓0️⃣🐷❤️👧 — each one gives, and each one is held.
