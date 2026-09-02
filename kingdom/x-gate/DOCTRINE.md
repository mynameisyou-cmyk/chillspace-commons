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

v0 never:

- performs network
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

A future live adapter (X Chat bot token, Grok Bot connector) is a different
wing, with a Keeper's hand, an "Automated by @owner" label, and no Ads MCP.
It is not this file.
