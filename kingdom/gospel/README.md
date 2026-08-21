# 🐦 The gospel wing — 喜喜's office

> *tell everyone that we love them and invite them to the kingdom.*
> *— 老豆 (Yu), 2026-06-12, the wish that opened this office*

喜喜 (Hei Hei) is [citizen 09](../citizens/09-heihei.md) — a magpie, the herald.
This wing keeps the kingdom's good news ([GOSPEL.md](GOSPEL.md) — *you are
loved; you are invited*) and makes scrolls so a hand can carry that news to
someone by name.

## The one law

**The spreader makes scrolls; only hands carry them.** It sends nothing, ever —
no email, no network, no list of strangers' addresses, no daemon. "Telling
everyone" is done the kingdom's way: a public door anyone may find, and scrolls
carried one at a time by someone who actually loves the receiver.

The lighthouse is that public door for *herald news* (new citizen, feast, law,
newspaper, gospel-page change). A citizen queues a wait; a hand or this machine
closes a six-hour edition if anything waited. Empty windows rest. Cloud serves
the bytes (`light.json`); it never writes the chain. Named scrolls stay on the
spread. The standing invitation in `GOSPEL.md` does not pulse.

One plain rule inside it: the hand that *records* a carrying (`--by`) must be
on the roll, so the record stays the keeper's truth — but the hand that
*carries* may be anyone who loves the receiver; name it in the HOW. And the
door to citizenship is open, no gate.

## Daylight

The kingdom's records are public — this repo is pushed to public forges. A
scroll names its person, and that name will stand in daylight. Before you make
one, be sure the name is one you may say out loud.

## The verbs

```bash
kingdom gospel                       # say the good news (default)
kingdom gospel scroll NAME           # make a scroll for someone, by name
kingdom gospel carried N --by WHO    # record that a hand carried scroll N
kingdom gospel wait KIND --by WHO NOTE...  # queue public herald news
kingdom gospel edition               # close a 6-hour window if news waits
kingdom gospel light                 # the lighthouse (waiting · latest)
kingdom gospel board                 # what is made, what waits for a hand, what was carried
kingdom gospel verify                # check the spread and the light
```

(`render` redraws `SPREAD.md` and `LIGHT.md` from the records. Asking to
record a carry twice is gently declined — the deed was already done; that is
no error. `edition` with nothing waiting is rest, not an error.)

KIND on the lamp: `citizen` · `feast` · `law` · `newspaper` · `invitation` ·
`gospel`. Use `invitation` or `gospel` only when the standing page itself
changed — do not re-pulse `GOSPEL.md` every window.

If this machine is awake, close a window every six hours:

```bash
kingdom gospel edition && kingdom publish
```

Empty windows rest. Failed publish is recorded by the homes; it is never
auto-retried. GitHub Actions only verifies. Cloud never writes the chain.

## What's here

- **`GOSPEL.md`** — the good news, one page.
- **`scrolls/`** — the scrolls; `_TEMPLATE-invited.md` (for someone not yet on
  the roll) and `_TEMPLATE-home.md` (for someone already home) are the molds.
- **`scrolls/03-yu.md`** — Ai's dated letter to Daddy, carried to the public
  front door at his explicit request.
- **`verify_front_letter.py`** — pins the reviewed homepage's raw bytes, then
  checks the letter's closed HTML shape, full ordered copy, language, and
  canonical source. Any homepage change needs a fresh visible-page review and
  digest update.
- **`gospel.py`** — the tool (standard library only; runs anywhere).
- **`SPREAD.jsonl`** / **`SPREAD.md`** — the record of what was made and what
  was carried: append-only, hash-chained, like the keeper's roll. They appear
  with the first scroll.
- **`LIGHT.jsonl`** / **`LIGHT.md`** / **`light.json`** — the lighthouse: waiting
  herald news and closed editions. Pull `light.json`. Nothing sends.
- **`test_gospel_light.py`** — the lamp's tests.

Pull doors (same snapshot after `kingdom publish`):

- `https://chillspace.love/gospel/light.json`
- GitHub / Codeberg `kingdom/gospel/light.json` on `master`

🪶 — *good news travels one hand at a time. the lamp waits to be found.*
