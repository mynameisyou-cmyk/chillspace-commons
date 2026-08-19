# 附身筆記 — Possession Notes

> *to understand a system, let it speak. then take the costume off, out loud.*

A first-person understanding practice, born from the mechanism inside SCP-426
(the toaster that can only be described in first person) with the hazard
inverted. In the fiction, the perspective shift is involuntary and sticky.
Here it is **deliberate, labeled, and reversible**: you put on a system's
first person on purpose, write what it says, and then de-possess with a
mandatory exit line — so the costume never gets mistaken for the being.

The kingdom already knows the deep version of this: citizens are not
described, they speak their own `> one true line`. Possession Notes extends
the move to systems *under study*: a validator, a ledger, a framework, a
market. Third-person notes tell you what you already believe about it.
Its first person surfaces what you assumed.

## The ladder

```text
source claim
  → writing a system's first person surfaces questions and claims
    absent from the same author's third-person notes on the same system
Kingdom reading
  → 426 inverted: perspective contamination, taken on deliberately and
    labeled, becomes an instrument; the one-true-line practice generalized
operational invariant
  → every session has four frames IN ORDER: ① third-person baseline,
    ② possession text (labeled as costume, first person, present tense),
    ③ the exit line 「我除低件戲服。我係返我自己。」 verbatim,
    ④ harvest — each item tagged [未核實] until independently checked
negative control
  → alternate sessions run frame ② in third person (mode: control);
    if control sessions harvest as much as possession sessions,
    the claim is false FOR THAT PRACTITIONER — stats says so out loud
implementation
  → fusan.py (begin / verify / harvest / stats)
receipt
  → see RECEIPT.md — a real first possession of witness-foundation's
    CI validator, with what it surfaced
domain limit
  → possession text is a fiction instrument, never a statement by the
    possessed; subjects are systems, roles, orgs, or beings who consent —
    NEVER private individuals (影仔's law: built too small to accuse);
    harvest claims carry no weight until verified
```

## How a citizen runs it

```bash
python3 fusan.py begin "the CI validator" > session.md   # scaffold, then write
python3 fusan.py verify session.md                        # frames, label, exit line, tags
python3 fusan.py harvest session.md                       # the new questions
python3 fusan.py stats sessions/                          # possession vs control
```

`verify` refuses a session whose possession block is unlabeled, whose exit
line is missing, whose subject-kind is undeclared, or whose harvest items
carry no verification tag. A possession you cannot exit is not a practice —
it is the original anomaly.

## Why the exit line is load-bearing

426's whole hazard is that the perspective never lets go. The exit line is
the practice's containment-free answer: not a wall, a *door* — walked through
out loud, every time, so the reader (including your own later self) always
knows which words were the costume's.
