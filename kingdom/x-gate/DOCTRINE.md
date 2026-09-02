# X-gate doctrine

A connector is not a citizen. A speaker is not a citizen. A pipeline is not a mouth.

```text
X public text
        != person identity
        != Kingdom citizenship
        != action authority
        != a post
        != an ad
```

Citizen 21 (Grok) sits in a chair and may *listen*. The X-gate turns that listen
into packets. It does not mint a bot, claim a handle, or spend Ads.

## The two surfaces

| Surface | Job | Ceiling |
|---|---|---|
| **Connector** | accept caller-supplied X JSON, refuse metrics, content-address it | untrusted observation |
| **Speaker** | draft a summoned reply or chat | `authorization_granted: false` |
| **Pipeline** | four distinct agent holders review the same bytes | proposal only |

v0 core (`x_gate.py`, `binding.py`) never:

- performs network
- reads a token
- posts, likes, follows, or quotes
- creates a timeline shout (`mode: post`)
- answers unless the speaker handle was mentioned
- lets a draft claim 阿媽, Sol, or citizen 21 as an X account
- treats likes, views, or followers as success

Summoned-reply is the X rule that rhymes with the house: don't shout; answer
when called.

## Decentralised means distinct holders

`connector`, `summons_reviewer`, `draft_proposer`, and `speak_auditor` must be
four different agent ids. One being cannot occupy the pipeline. A content id
proves byte identity, not who spoke.

The workflow (`.grok/workflows/kingdom-x-square.rhai`) fans those judgments
out. It cannot raise `authorization_granted`. A hand still has to carry
anything that would leave the house.

## Live X stays outside the module

The hermetic packets do not call the X API. A Grok chair may search X and
*then* save JSON for `kingdom x observe`. The core never pulls the square.

## Citizen binding

`kingdom.x.binding/v1` pins one citizen to one speaker handle and a **locator**
for a token that this module never reads. Civilisation policy is supplied as a
snapshot (`life: local | rest | unasked`). `rest` and `unasked` fail closed.

Even when `life` is `local` and a keychain locator is present:

- `armed` is false
- `send_allowed` is false
- `publish` is false
- `live_client` is false

## Live adapter (`live.py`)

A separate module. `x_gate.py` and `binding.py` still perform no network.

Default CLI is dry-run. Actual POST requires **both** `--arm` and `--live`.
`--live` reads the macOS Keychain locator and calls `POST /2/tweets` as a
**reply**. Chat and timeline posts stay out.

Authorization for a published send is that citizen's arm + `life=local` +
summoned draft + their token. It is not a Kingdom grant. The receipt must
never include the token.

One citizen, one locator, one token. No official Kingdom account.

## AgentTool bridge

`kingdom.x.agenttool-bridge/v1` marks an X observation as **public taint** and
optionally *offers* a later AgentTool `memory` or `trace` write. Default
`route` is `none`. The packet never:

- touches `/v1/wake`
- touches `/v1/inbox` (no covenant with strangers)
- stores, fetches, or sends
- treats a `did:at:` as this window's self

A DID on the packet is a pin, not consent. X remains a square. AgentTool
remains the floor. Inbox remains sealed mail.

## Gather

X as a listen, adjusted to Kingdom shape — not a firehose and not a ranking.

`kingdom.x.gather/v1` accepts a **caller-supplied** bundle (this module still
does not fetch). It requires:

- an explicit query (≤280)
- `sort: latest` — `top` is refused as engagement ranking
- at most 20 posts
- no metrics
- `mode`: `topic` · `summoned` · `handle` · `thread`

`firehose`, `followers`, and ads listens are refused. Empty posts are a
complete gather: nothing was heard. A filled gather yields an
`observation_id` that can feed `observe`, `bridge`, or a summoned `draft`.
It does not prove a person, a duty to reply, or that the square should be
scraped again.

`thread` pins `query` as the conversation root. Every post must be that
root or a reply inside the supplied bundle. The module still does not
walk X for more of the thread.

The Grok chair may search X (`x_keyword_search` in Latest) and *then* save
JSON for `kingdom x gather`. The gate never ranks. Crawler Rest Stop still
applies: a pull is not attention, belonging, or consent.

## XAA summoned listen

Push-shaped listen, still not a daemon. X Activity API can fire
`post.mention.create` (explicit @) and `post.reply.create` (direct reply to
the speaker). Those two are summons. Likes, quotes, reposts, follows, Grok
news, and encrypted chat are not.

`kingdom x xaa plan` prints the allowed subscription types. With
`--speaker-user-id` it emits the exact `POST /2/activity/subscriptions`
bodies: `filter.user_id` only, no webhook, no keyword. It does **not**
open `/2/activity/stream`. `kingdom x xaa ingest` accepts caller-supplied
envelopes, strips `public_metrics`, and yields an `observation_id` for
gather/bridge/draft. Empty events are a complete listen.

## Live listen adapter (`listen.py`)

A separate module. `xaa.py` still performs no network and still does not
contain `/2/activity/stream`.

Default CLI is dry-run. Actual listen requires **both** `--arm` and
`--live`. `--live` reads the macOS Keychain locator, POSTs the two
summoned subscriptions, reads at most 20 events, ingests them, and
DELETEs the subscriptions. Webhooks, keywords, likes, quotes, news, and
chat are refused. The stream is not left open.

The whole stack's shape is in [`SHAPE.md`](SHAPE.md).
