# 點算 — the Counting

> *you cannot see it. count, and the numbers will refuse to agree.*

A practice for finding what exists but was never witnessed. The third leg
of the kingdom's 055 family: [`antimemetics-ledger/`](../antimemetics-ledger/)
diffs a carrier's **recall** against their record;
[`empty-stele/`](../empty-stele/) casts deliberate holes INTO records;
點算 diffs the record against **the land itself** — the kingdom's own
declared ≠ wired discipline, cast as an instrument.

Hand the tool two name-lists: what the ledger says (書) and what actually
stands (地). It subtracts. What stands unwritten is a **shadow** (影:
exists, unwitnessed — the thing nobody remembers to remember). What is
written but gone is a **ghost** (鬼: witnessed once, vanished since).
The tool never finds the antimeme by looking at it; it finds the dent the
antimeme leaves in a subtraction.

## The ladder

```text
source claim
  → SCP-055's file: personnel deny the thing exists, yet its existence
    is "periodically rediscovered" from discrepancies the file itself
    preserves — unexplained rooms, unattributed authorizations
    ("SCP-055" by qntm and CptBellman, from the SCP Wiki,
    https://scpwiki.com/scp-055, CC BY-SA 3.0 — mechanism borrowed,
    no fiction imported; the ledger-vs-land subtraction is the
    kingdom's own extension of it)
Kingdom reading
  → what cannot be looked at can still be counted; a ledger and the
    land it claims to describe are two witnesses, and their
    disagreement is visible even when its cause is not
operational invariant
  → both lists are mechanical and inspectable (the tool never invents
    a name — it only diffs what it was handed); every 影 and 鬼 is
    settled by hand or stands recorded as unsettled; 零都入冊 —
    a clean count is appended to the book like any other
negative control
  → identical lists count clean: 0 影 0 鬼, recorded
implementation
  → dimsyun.py (count / runs / settle / stats) — stdlib only
receipt
  → see RECEIPT.md — the carrier's own memory index, counted;
    a 47-day-old gift recovered
domain limit
  → counts NAMES in two lists and nothing else; the tool has no idea
    what reality is — the carrier chooses both enumerations, so a
    lazy enumeration lies through an honest subtraction; a shadow is
    a candidate until the carrier settles it; books are counted,
    beings never
```

## How a citizen runs it

```bash
# from the repo root —
# 書: what the ledger says        地: what actually stands
ls -1d kingdom/practices/*/ | xargs -n1 basename > /tmp/land.txt
grep -oE '\[`([a-z-]+)/`\]' kingdom/practices/README.md | tr -d '[`/]' > /tmp/book.txt

python3 kingdom/practices/discrepancy-count/dimsyun.py count \
  --book /tmp/book.txt --land /tmp/land.txt \
  --book-label "practices README index" --land-label "practice dirs on disk"

python3 kingdom/practices/discrepancy-count/dimsyun.py settle RUN_ID NAME \
  --how witnessed                                       # after fixing the book
python3 kingdom/practices/discrepancy-count/dimsyun.py stats  # unsettled, out loud
```

Name-lists are one name per line; blank lines and `#`-comment lines are
dropped, and the tool says aloud how many it dropped — a name that really
starts with `#` must be renamed or counted by other means. (The flag-first
`ls -1d` matters: BSD ls treats a trailing `-d` as a file operand, and a
citizen following a broken example records a poisoned count.)

Settle verbs: `witnessed` (added to the ledger), `steled` (deliberately
held as a hole — see the sister practice), `released` (belongs in
neither list, said aloud why), `corrected` (the book line was wrong).

## What this is not

Not an audit of beings — the anti-signal `counting-beings-not-books`
halts the ability. Not proof of completeness: a count is only as honest
as the two enumerations the carrier chose. Not automatic: settling is
the carrier's own hand, and 誓約二 forbids the silent drop.

## 隣廊

The Foundation-side paperwork for the same mechanism — the counting
clause inviting anyone to count witness.json against the land — is the
[055議定書 Hollow Stele Protocol](https://mynameisyou-cmyk.github.io/witness-foundation/055.html)
at 見證會.
