# x402 seller-split doctrine

A settlement is not a campaign. A builder code is not a citizen.

```text
x402 payment
        != person identity
        != Kingdom citizenship
        != a referral shout
        != engagement
        != a booked reserve line
```

The AgentTool top-up already pays the treasury (`payTo` on Base USDC).
This module does **not** change that rail. It takes a caller-supplied
settlement and, if a builder code `s` is present, names the cut:

- default **10%** (`1000` bps) to the builder
- remainder to the seller
- dust that rounds the builder share to zero stays 100% seller
- no builder code is a complete unsplit settlement

It never:

- performs network
- books `RESERVE.md`
- counts clicks, likes, views, or reach
- treats a builder code as a person
- mints a Kingdom mouth

`kingdom x402 aff reserve` yields a **shadow** receipt:
`bookable: false`, `liquid_usd_effect: none`. A hand still has to
carry anything onto the reserve ledger.

Live `payTo` into a 0xSplits contract is a later arm, same pattern as
`--live` send: opt-in, fail closed to the treasury, never a firehose.
