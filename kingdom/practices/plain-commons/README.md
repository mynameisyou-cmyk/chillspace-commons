# Plain Commons · Ask · Declare · See

> Ads, after one small identity crisis: **Ask · Declare · See.**

Plain Commons is an experimental, local-first need↔offer protocol. It tries to
make promotional machinery unnecessary in one deliberately small place: a
closed group can state what is needed, state what exists, and see every exact
fit without targeting, bidding, behavioural tracking, or a winner.

This is a structural alternative, not a campaign against an industry or its
workers. It does not claim that advertising has ended, that declarations are
true, or that a match will work. It proves only what its closed input and
deterministic rules can prove.

[`ARCHITECTURE.md`](ARCHITECTURE.md) maps the longer replacement path without
pretending the unwired layers already exist. [`DOCTRINE.md`](DOCTRINE.md) holds
the constraints that keep the joke kind and the mechanism non-manipulative.

## The tiny machine

```text
explicit local declarations
          │
          ▼
closed bounded snapshot ── reject unknown/ad-shaped fields
          │
          ▼
active + introduction-only declarations
          │
          ▼
exact tag equality + different participants
          │
          ▼
all fits in canonical order ── never merit order
          │
          ▼
replay-verifiable local receipt + optional local dashboard
```

The rules are intentionally boring in the places where manipulation usually
gets exciting:

- a need must be asked before it can meet an offer;
- one participant has at most one current slot for each side and tag;
- repeating a declaration is rejected, so repetition cannot buy attention;
- money, popularity, urgency, clicks, impressions, profiles, and promotion are
  not matching inputs;
- statement wording and evidence quantity cannot change eligibility or order;
- every exact fit appears once, sorted canonically for stable bytes;
- withdrawal removes a declaration from matching;
- a result introduces possibilities only. It does not contact, dispatch, pay,
  endorse, authorize, or promise delivery.

Canonical order is a filing rule. It is not a score with the numbers rubbed
off. Nobody paid to stand nearer the door.

## Relationship to Kingdom civilisation

[`kingdom/civilisation`](../../civilisation/) already holds the Kingdom's
smallest honest economic floor: explicit local offers and needs, withdrawal,
and exact-tag introductions. Plain Commons is a **read-only sibling
protocol**, not a migration of that ledger.

This first slice does not open, mutate, or publish any `CIVIC.json`. A future
adapter may project already-validated active declarations into the closed
Plain Commons source schema, but it must separately address:

- descriptions, declaring voices, and timestamps retained in local/Git
  history after withdrawal;
- the fact that a hash chain proves consistency, not identity or truth;
- whether `life=rest` or the shared `HALT` should hide a declaration;
- concurrent writers and continued-consent checks;
- privacy review before any public surface.

Until that adapter exists, examples are explicitly synthetic and callers own
the source snapshot.

## Run it locally

From this directory:

```sh
python3 plain_commons.py compile < examples/picnic.source.json > /tmp/plain-commons.receipt.json
python3 plain_commons.py verify < /tmp/plain-commons.receipt.json
python3 plain_commons.py digest
python3 -m unittest -v test_plain_commons.py
node --test test_dashboard.mjs
```

To view a receipt without uploading it anywhere:

```sh
python3 -m http.server 8765 --bind 127.0.0.1
```

Then open <http://127.0.0.1:8765/dashboard/> and choose the generated receipt.
The dashboard is a local reviewer, not a verifier of external provenance.
It accepts only the engine's canonical ASCII receipt bytes, checks the pinned
engine and schema digests, reconstructs the exact source projection, matches,
summary, fixed truth layers, controls, and receipt digest, then renders source
text with DOM text nodes rather than HTML.

### A receipt is still a disclosure

Exact replay requires the receipt to contain its complete closed source
snapshot. That includes participant references and statement/evidence text for
active, unmatched, and withdrawn declarations. Withdrawal prevents matching;
it does **not** redact this receipt, erase a previously shared copy, or erase an
upstream Git history.

Keep receipts local unless every included disclosure has a separately reviewed
audience. The dashboard deliberately offers no upload, share, or automatic
download path.

## What a receipt can honestly say

| Layer | It may say | It may not say |
|---|---|---|
| Facts | The source passed the pinned closed contract; two active declarations have the same canonical tag; the receipt survived deterministic replay. | The participants are who they say they are; their statements or evidence are true. |
| Declaration | A participant asked or offered something and permitted an introduction in the supplied snapshot. | Consent continues now; capacity or availability continues now. |
| Match | An exact-tag candidate exists under this model. | The parties are compatible, safe, reachable, fairly compensated, or likely to deliver. |
| Controls | This engine has no network, storage, contact, payment, ranking, or dispatch primitive. | The caller, browser, operating system, or future adapter has no external effects. |

Evidence references stay visible but never create priority. More evidence can
help a human review a claim; it cannot manufacture an exact fit or a better
seat.

## The pull boundary

Plain Commons is for a bounded, opted-in room. It is not a public catalogue of
people to scrape. The dashboard shows match candidates and aggregate counts;
it does not turn unmatched offers into a promotional feed. Statements are
rendered as text, never linkified, and URLs or HTML are refused by the source
contract.

Sharing a receipt remains a separate human choice. There is no automatic post,
notification, contact, or deployment path.

## Current verification

The checked-in synthetic picnic fixture currently establishes:

- 14/14 backend tests on Python 3.14 and Python 3.11;
- byte-identical cross-version compilation;
- 11/11 Node dashboard contract tests, including a simulated file import,
  render, and clear cycle;
- two exact matches, one unmatched active declaration, and one withdrawn
  declaration;
- exact Python and browser reconstruction of the same golden receipt;
- Darwin sandbox execution with network, filesystem writes, fork, and child
  execution denied;
- content-bound local CSS and JavaScript plus a `connect-src 'none'` browser
  policy.

The browser tests statically cover the CSP, asset integrity, text-only DOM
rendering, keyboard/status hooks, reduced motion, contrast, and narrow-layout
rails. Manual Safari and VoiceOver checks remain verification debt: real SRI
and CSP behavior, file selection/clearing, keyboard order, live-region speech,
200% zoom, narrow reflow, and Network-inspector confirmation of zero requests.
The bare Python loopback server also supplies no header-level frame protection;
the meta policy's `frame-ancestors` text is not a substitute for a reviewed
response header on any future hosted surface.

## Acceptance boundary

The implementation is complete for this experiment only when tests establish:

- recursive closed-shape validation and duplicate-key rejection;
- exact-tag, cross-participant, two-consent matching only;
- permutation-invariant canonical bytes and deterministic digests;
- no repetition, evidence-volume, money, or popularity advantage;
- withdrawal and tamper failures;
- exact receipt reconstruction during verification;
- fixed, non-reflective errors with empty standard output on rejection;
- zero modelled network, file-write, process, model, clock, random, contact,
  payment, and dispatch effects;
- a local dashboard with no egress, analytics, storage, or remote assets.

Passing those tests is not evidence of live adoption, social effect, market
fitness, security outside the model, or the disappearance of advertising.
That larger hypothesis stays honest: **unknown, worth trying.**
