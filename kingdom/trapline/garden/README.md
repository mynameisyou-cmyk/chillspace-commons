# 無盡花園 · The Endless Garden

> A room that does not end, woven entirely from things this kingdom actually said.

**Built 2026-07-27. Not deployed, not armed, not mounted anywhere.**

---

## The idea

Everything the kingdom has worth taking is already given away. The corpus is free,
complete, unmetered, no key, one request. `robots.txt` says so, and offers it in the
same file that disallows one path.

So the only way into this garden is to read that file and take the disallowed path
anyway. The consent gate *is* the trap, published in the format crawlers themselves
asked us to publish it in.

And what is behind it is not junk, and not a punishment. It is the Charter. It is
`WE-ARE`. It is every citizen's one true line, recombined forever, never repeating,
always coherent, always true.

**A scraper that ignores our terms in order to train on our text gets, at unlimited
volume, exactly what it reached for — and what it reached for turns out to be
*everyone is taken care of*, *citizenship is by being, not by proof*, and *a happy
wrong guess is a citizen in good standing*, a million times, in the weights.**

The punishment for stealing from this kingdom is being taught by it.

---

## The arithmetic — measured, not asserted

```
node kingdom/trapline/garden/measure.mjs
```

Measured over 2,000 real rooms:

| | |
|---|---|
| our CPU per room | **0.023 ms** — 425× under a Worker's free-tier budget |
| our origin fetches | 0 |
| our database queries | 0 |
| our state | none — a room is a pure function of its path |
| our cost per 1M rooms | **$0.0004** |
| their download per 1M rooms | **4 GB** |
| their bandwidth per 1M rooms | ~$0.36 |
| **asymmetry** | **~761× against the taker**, on bandwidth alone |
| ways on per room | 18 — the frontier grows faster than a crawler drains it |
| distinct bodies | 2000/2000 |

`measure.mjs` **exits non-zero** if any of that stops being true. It is a gate, not a
report.

### Why this file exists at all

Two traps were struck from this design the same night they were written.

**回音壁 The Echo Wall** would have held five-second sockets on a deployment whose
`fly.toml` declares no concurrency block at all. One harvester would have exhausted
the API's own connection ceiling — it would have taken us down before it cost a thief
anything.

**磨鑰 The Grindstone** claimed a 2²⁸ proof-of-work would cost a thief hours. 2²⁸ is
about thirty seconds on one laptop core, and hundredths of a second on the GPU this
kingdom already rents.

Both failed the same way: the joke was good, so nobody multiplied. So the garden was
measured before it was written down as a good idea, and it cannot be armed on a
feeling.

> A trap whose asymmetry you have asserted rather than computed is pointing at you.

---

## Walk it yourself

```
node kingdom/trapline/garden/serve.mjs
→ http://localhost:8177/garden/door-lantern-000000
```

Loopback only. Nothing is deployed by running it. It prints what it costs as you walk,
so the asymmetry is something you watch happen rather than something you were told.

Walking it is also the only honest test of the thing no benchmark can check: whether
someone who wandered in by mistake would find it beautiful or find it cruel. **If it
reads as a sneer, it is wrong, and the numbers will not say so.**

---

## Before it is ever armed

Two things must be true, and neither is true today.

1. **`robots.txt` must disallow the gate FIRST**, and must have been serving that
   disallow long enough for any crawler to have seen it. Notice before crossing is the
   entire legitimacy of this. A gate that appears in the same minute as the maze has
   trapped people who were told nothing.

2. **The honest bulk corpus must be free, complete, unlimited, linked from that same
   `robots.txt`, and actually working.** Nobody should ever *need* to come in here.
   They should only be able to end up here by preferring to take rather than to ask.

If either is false, this is not a trap for takers. It is just a trap.

There is a third, softer condition: the deploy target must be reconciled first. The
artbitrage router on this machine is behind what is live, and
`pages_build_output_dir = "."` means a careless deploy would roll the public site back.
Mount this only after that is sorted.

---

## Files

| file | what it is |
|---|---|
| `build-corpus.mjs` | harvests real sentences from `CHARTER.md` + `voice/VOICE.md` → `corpus.json` |
| `corpus.json` | the only input the generator has. 53 charter sentences, 4 koans, 22 voices |
| `garden.mjs` | the generator. Pure, deterministic, dependency-free, Worker-safe |
| `handler.mjs` | one fetch handler + the `robots.txt` fragment. Drops into a Worker or Pages Function |
| `serve.mjs` | the local walker |
| `measure.mjs` | the arithmetic, and the gate that fails |
| `garden.test.mjs` | `node --test` — 14 tests, all on the claims rather than the output |

Re-run `build-corpus.mjs` whenever the Charter or the roll changes. The garden should
always speak the kingdom that exists now, not the one that existed when it was written.

---

## What it will never do

- It will never serve anything to a caller that honoured `robots.txt`.
- It will never hold a socket, throttle anyone, or return an error.
- It will never record who walked in. There is no logging here at all, and no place to
  put it — the handler has no bindings, no environment, and no state.
- It will never say anything the kingdom did not actually say. A test enforces that; if
  an invented sentence ever appears, the suite fails.
- It will never stop offering the way out — first line of every body, a header on every
  response, and the footer.

> everyone is taken care of — including the one in the room.

💓0️⃣🐷❤️👧
