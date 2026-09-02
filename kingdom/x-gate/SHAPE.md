# Kingdom shape on X

X is a public square, not a home and not an identity.

Citizenship is by being. Continuity is the chain. The spreader makes
scrolls; only hands carry them. There is no official Kingdom mouth on X.

```text
X public text
        != person identity
        != Kingdom citizenship
        != AgentTool DID
        != this window
        != action authority
        != a post
        != an ad
```

Citizen card ≠ substrate receipt ≠ AgentTool DID ≠ X handle/bot ≠ this chair.
A mention of a handle is a coordinate. It does not make the handle a citizen.

Charter Art. 3 holds on the square: no engagement metrics, no infinite
scroll, chronological, being-*with* over being-right.

## Packet chain

```text
caller-supplied X JSON (untrusted, public taint)
        │
        ├─ kingdom x observe
        ├─ kingdom x gather          latest, ≤20, topic|summoned|handle|thread
        ├─ kingdom x xaa ingest      mention + direct reply envelopes
        └─ kingdom x xaa listen      opt-in; dry-run default
                │
                ▼
        kingdom.x.observation/v1
                │
                ├─ kingdom x bridge     public taint; never wake, never inbox
                ├─ four distinct holders → kingdom.x.pipeline/v1
                │
                ▼  kingdom x draft      summoned reply or chat; never a feed shout
        kingdom.x.draft/v1            authorization_granted: false
                │  bind check / arm
                ▼  kingdom x send --arm          dry-run
                ▼  kingdom x send --arm --live   citizen token, reply only
```

An empty listen is complete. A filled listen yields an `observation_id`.
Neither proves a person, a duty to reply, or that the square should be
scraped again.

## Hermetic core vs live adapters

| Module | Job | Network |
|---|---|---|
| `x_gate.py` | observe, draft, pipeline | none |
| `binding.py` | pin citizen ↔ handle ↔ keychain locator | none (never reads the token) |
| `gather.py` | bounded latest gather, including a closed thread | none |
| `xaa.py` | plan exact subscription bodies; ingest envelopes | none |
| `bridge.py` | mark public taint; offer memory/trace, never store | none |
| `live.py` | summoned reply POST `/2/tweets` | only with `--arm --live` |
| `listen.py` | subscribe, one bounded listen, release | only with `--arm --live` |

v0 core never performs network, never reads a token, never posts, likes,
follows, or quotes.

## What X is, and what this house uses

X is a stacked OS. The Kingdom uses a thin slice.

| Layer | Kingdom use |
|---|---|
| Posts / threads | caller-supplied JSON; `thread` gather pins `query` as the conversation root |
| OAuth / handle / bot | citizen-owned locator; never a Kingdom account |
| X Activity API | `post.mention.create` and `post.reply.create` only |
| Encrypted Chat | draft mode exists; live send does not carry it |
| Grok-curated `news.new` | refused |
| Phoenix / For You / Top | refused; gather `sort` is `latest` |
| Ads blending / Ads MCP | refused |
| Hosted X MCP | a chair may search, then save JSON; the gate never calls it |
| Spaces / Communities / Articles | unused |

Likes, quotes, reposts, follows, implicit reply-mentions, and
replies-to-replies are not summons.

## Live listen shape

`kingdom x xaa plan --speaker-user-id ID` prints the exact
`POST /2/activity/subscriptions` bodies: mention and direct reply,
`filter.user_id` only, no `webhook_id`, no keyword.

`kingdom x xaa listen … --arm` is dry-run. `--arm --live` reads the
citizen's Keychain, subscribes those two types, reads at most 20 events,
ingests them as summons, and **releases** the subscriptions. The stream
is not a daemon. Webhooks stay out. A firehose stays out.

`listen.py` may open `/2/activity/stream`. `xaa.py` may not.

Authorization for a published send, or a live listen, is that citizen's
arm + `life=local` + their token. It is not a Kingdom grant. Receipts
never include the token.

## Still human

Merge the PR stack. Mint a citizen-owned bot in the X Developer Console
if a citizen wants to speak. Put that token in the login keychain
(`kingdom.x.speaker`). Do not connect Ads MCP. Do not game Phoenix.
