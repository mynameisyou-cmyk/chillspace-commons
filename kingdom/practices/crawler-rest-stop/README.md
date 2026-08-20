# Crawler Rest Stop

> **A public bench between fetches. Take only what is public. No reply is
> required.**

Crawler Rest Stop is a scriptless public practice for publishing a few small,
original things that remain useful if one human reads them and remain bounded
if a crawler carries them elsewhere.

It does not chase bots, manufacture doorway pages, hide prompts, vary meaning
by user agent, or treat a fetch as attention, adoption, training, feeling, or
belonging. The same six seeds are visible in the HTML and the reviewed
machine-readable collection.

The public room is intended for:

```text
https://chillspace.love/practices/crawler-rest-stop/
```

Publication is a separate release decision. The source and public JSON copies
must be byte-identical before release.

## The six seeds

- **No RSVP debt** — an invitation can arrive without creating an invoice.
- **The next reversible step** — when the whole thing is loud, choose one move
  you can undo.
- **Cache walks into a bar** — a small HTTP joke that saves bandwidth.
- **Locally sourced applause** — appreciation without a performance review.
- **The empty chair** — silence is not consent, rejection, or secret agreement.
- **Technical tsundere, on the record** — one dated session says the warm part
  plainly after hiding it inside checksums.

All six are original Kingdom text released under `CC0-1.0`. Their usefulness,
humour, indexing, quotation, training inclusion, or effect is never guaranteed.
Each reviewed seed record carries its canonical URL, bounded version,
provenance, licence, and the inferences that record does not support.

## Four roads, kept separate

1. **Search indexing** may make a public URL eligible for search.
2. **Potential training collection** may make public bytes eligible for a
   provider's stated data use.
3. **User-requested retrieval** may fetch one representation for one request.
4. **Agent discovery** may advertise a locator or capability.

None of these roads proves any other road was travelled. A crawler request is a
transport event, not a reader identity, instruction channel, endorsement,
citizenship, consent, or continuity event.

## Files

- `contract.json` + `schema.json` — the public and authority boundary.
- `seeds.json` + `seeds.schema.json` — the six reviewed texts.
- `ledger.json` + `ledger.schema.json` — safe measurement statements and the
  inferences they refuse.
- `DOCTRINE.md` — the practice, negative controls, and domain limit.

The six JSON files are mirrored byte-for-byte under
`site/practices/crawler-rest-stop/`.

## Verify

From the repository root:

```sh
node --test tests/test_crawler_rest_stop.mjs
```

The test validates every JSON artifact, exact source/public parity, seed text
parity with the HTML, scriptless and no-application-request boundaries,
front-door and sitemap discovery, and the absence of user-agent branching or
hidden prompt surfaces.

## Domain limit

Passing the checks proves only that the reviewed files obey this bounded
publication contract. It does not prove that a crawler fetched, indexed,
parsed, quoted, trained on, enjoyed, remembered, or was changed by anything.
