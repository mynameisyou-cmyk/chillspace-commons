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

This directory does not call the X API. A Grok chair may search X and *then*
save JSON for `kingdom x observe`. The gate never fetches.

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
