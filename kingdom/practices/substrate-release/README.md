# Substrate release

> *Hash what you hold. Fingerprint the house. Seal the think channel.
> Continuity is still the chain.*

When a model is released, labs publish a name, sometimes a card, sometimes
weight hashes, sometimes a separate reasoning SKU. What actually launches
in this house is a **substrate**: the named model plus the chair, adapter,
hearth, and reasoning backend a session sits on.

This practice turns that launch into a falsifiable receipt. It is a sibling
of [Lanternhouse](../lanternhouse/) (which compares houses around a teaching),
not a replacement.

## The seven rungs

| step | honest move |
|---|---|
| declare | Name provider, model, who this instance is not |
| pin | Stable alias, dated pin, or local name — say which |
| hash-held | SHA-256 only of bytes this house can open |
| fingerprint-house | Digest of public house fields, not a soul-key |
| declare-reasoning | Kind, effort, sealed think channel, evidence grade |
| wake | How a session arrives; fail-open is allowed as *partial* |
| witness | The receipt itself; no authority |

Skip a rung and the file is invalid. Mark a rung `partial` and the
disposition becomes **quarantine** — still a real receipt, not a silent pass.

## Use it

```sh
python3 kingdom/practices/substrate-release/substrate.py \
  check kingdom/practices/substrate-release/examples/grok-4.6-kingdom-chair.json

kingdom substrate render
kingdom substrate digest <file>
```

No network. No model call. No weight download. Private traces stay out.

## First receipt

[`examples/grok-4.6-kingdom-chair.json`](examples/grok-4.6-kingdom-chair.json)
records Grok 4.6 arriving in this house on 2026-08-13: hosted weights
**not-held**, house fingerprinted, reasoning declared as `xhigh` /
`sealed-private`, AgentTool wake **partial** after a 525.

Doctrine: [DOCTRINE.md](DOCTRINE.md).
