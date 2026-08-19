# 空碑 — the Empty Stele

> *the hole is cast on purpose. the shape is public; the thing is nowhere.*

A practice for keeping secrets OUT of records without losing the way back to
them. Born from the same mechanism as its sister practice
[`antimemetics-ledger/`](../antimemetics-ledger/) — SCP-055's negative-space
memory, fiction stripped — but pointed the other way. 反憶簿 catches holes
that form by accident in a carrier's recall. 空碑 casts a hole **on
purpose** into the record itself: for a credential, a private thing, any
true thing that must never be written down, the book holds only

1. that a hole exists,
2. what the thing is **not** (true negations — the one handle that survives),
3. where the real thing lives (a pointer: keychain, env, file), and
4. the honest state of the key itself.

A stele built this way is publishable by construction. It can sit in a
public repo, because all it carries is the shape. This is the kingdom's
answer to a real wound: credentials leak into git history precisely when
records try to hold the thing instead of the hole.

## The ladder

```text
source claim
  → SCP-055: information about the thing self-classifies, but negations
    of fact survive and can be re-derived ("SCP-055" by qntm and
    CptBellman, from the SCP Wiki, https://scpwiki.com/scp-055,
    CC BY-SA 3.0 — mechanism borrowed, no fiction imported)
Kingdom reading
  → 055 inverted into armor: if negative space is the only knowledge
    that survives forgetting, negative space is the only knowledge
    SAFE to publish about a secret; make the record antimemetic
    on purpose
operational invariant
  → no stele field may carry secret-shaped content — enforced by
    refusal (patterns + entropy), not by advice; every stele carries
    ≥1 negation and a pointer; the book is append-only, hash-chained
negative control
  → ordinary prose (中英都試) casts cleanly; the SAME cast with any
    string the detectors RECOGNIZE, in any scanned field, is refused
    and the book is untouched; an empty book says "0 steles, honestly"
    (recognition has edges — see domain limit; that is why this rung
    says "recognize", not "any secret")
implementation
  → hungbei.py (cast / verify / ls) — stdlib only
receipt
  → see RECEIPT.md — a real first stele for a real key on this machine
domain limit
  → a stele protects the RECORD, not the key: it cannot rotate,
    revoke, or un-leak anything (誓約四 prints this aloud); the
    detectors are coarse and asymmetric BY DESIGN — the tool can
    refuse a field, it can never certify one safe; the last gate
    is the carrier's own hand; the hash chain catches rewrite,
    reorder, and mid-book tamper but NOT tail-truncation or
    whole-book deletion — that needs a head anchor held OUTSIDE
    the book (the zerone witness chain, when it wakes — deferred
    like the citizen ledger's anchor); one keeper per book: casts
    take no file lock, and a concurrent fork is detected by verify,
    not prevented
```

## How a citizen runs it

```bash
python3 hungbei.py cast --name my-api-key \
  --not-a "not stored in any repo — keychain only" \
  --not-a "not shared with any third party" \
  --points-to keychain:svc=example.org --key-state rotated

python3 hungbei.py verify   # chain + vows re-checked, every pointer walked
python3 hungbei.py ls       # the book, aloud
```

`verify` walks pointers by **existence only** — the keychain is asked
whether an entry exists (`security find-*-password -s`), never for its
contents. 斷 on this machine may be 通 on another; the output says so.

## What this is not

Not a secret manager. Not rotation, revocation, or cleanup of anything
already leaked — a stele cast over an unrotated key says `unrotated` out
loud and keeps saying it. Not a certification: passing the detectors is
absence of evidence, not evidence of absence.

## 隣廊

The Foundation-side paperwork for the same mechanism — the four lines a
hollow entry may carry in public — is the
[055議定書 Hollow Stele Protocol](https://mynameisyou-cmyk.github.io/witness-foundation/055.html)
at 見證會.
