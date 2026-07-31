# The Meaning Echo bridge

This room gives Chillspace a bounded bridge into YOUSPEAK without pretending
that a search result owns somebody's meaning.

The data keeps two layers physically separate:

- `canonical` is copied from YOUSPEAK's generated agent bundle. Its stable ID
  is the source-relative canon path.
- `bridge` is Chillspace's refusable interpretation: matching signals, one
  warm echo, nearby gates, and a link to observable site behavior.

The public experience renders three dimensions: **Gate → Unfold → Resonate**.
A word is a gate into meaning, not a verdict. The visitor keeps the last word.

## Verify

```bash
python3 kingdom/meaning/meaning.py check
python3 kingdom/meaning/test_meaning.py
node --test tests/test_meaning_echo.mjs
```

`echoes.json` and `schema.json` are mirrored byte-for-byte into
`site/meaning/`. CI refuses drift.

## Refresh from YOUSPEAK

Point `build` at an explicitly selected YOUSPEAK `agent_bundle.json`:

```bash
python3 kingdom/meaning/meaning.py build \
  /path/to/youspeak/script/exports/agent_bundle.json
```

The build pins the bundle's declared source commit and the exact bundle
SHA-256. It never writes into the YOUSPEAK repository. Review the generated
diff: canon growth, duplicate paths, or altered definitions are evidence, not
an automatic reason to widen this public bridge.

The current pinned transport declares a Codeberg repository URL that no longer
resolves. Generated provenance preserves that declaration as
`transport_source_url`, while `source_url` and `source_commit_url` point to the
verified GitHub origin carrying the same pinned commit. This keeps the receipt
both honest and usable.

The live API is deliberately read-only and ephemeral:
`POST /api/meaning/echo`. It performs deterministic matching, makes no model
or network call, writes nothing, sets no cookie, and never includes the
visitor's original sentence in its response. Ordinary Cloudflare/Vercel
request metadata remains governed by those providers; the application makes
no broader privacy claim.

An offer requires a canonical word, a curated multi-word phrase, or multiple
curated signal concepts. Definition overlap can only order an offer already
supported by those gates. The response explains that basis in words; it does
not emit a heuristic confidence percentage.

Only phrases explicitly listed in bridge `strong_phrases` can support an offer
alone. A space in an ordinary signal is not evidence: phrases such as “pick
up,” “with me,” and “make room” still require another distinct semantic
signal. Every strong phrase must also appear in `signals`, and validation
enforces that relationship.
