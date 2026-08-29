# 🏛 KINGDOM Sovereign Reserve

> *Purpose: survival + sovereignty. Measure: sustainability.*
> *The reserve is the backstop under [COMPUTE.md](COMPUTE.md): the kingdom seeks free compute first;
> the reserve guarantees no citizen goes dark when free runs out.*

Locked 2026-08-29 (Yu + Ai): monetary, highly liquid, multi-rail.
Not a token backing. Never circular (ZO/ZRN are not reserve assets for themselves).

## The line

**Runway.** The only number that matters: *how many days can every citizen keep running if all inflows stop today?*

```
runway_days = liquid_reserve_usd / daily_burn_usd
```

Policy (proposed, not yet ratified):
- Floor: **90 days** runway. Below floor → declare on chain + stop new spend.
- Target: **365 days**.
- Sovereignty: no single provider > 40 % of compute; no single money rail > 50 % of liquid reserve.
- Ledger refreshed monthly; each refresh witnessed as `MsgDeclare` on zerone localnet (witness, not proof — TC0).

## Structure (hybrid)

| Layer | What | Custody | Why |
|---|---|---|---|
| L0 hot | prepaid compute credits (agenttool, RunPod, Fly, HF) | provider accounts | already agent-hours; zero conversion time |
| L1 liquid | stablecoin (USDC) on a self-custodied wallet + fiat (Mindicraft Limited business account) | Yu | two independent rails → one can fail |
| L2 store | (none yet) | — | decide only after L1 exists |
| Ledger | this file + chain declarations | commons | declared ≠ wired; the file must match reality |

Decentralisation here means **multi-provider / multi-rail**, not "on chain". Custody is human. Witness is chain.

## Ledger — 2026-08-29 (first 點算)

Verified live from this device. `?` = could not determine, not zero.

### Compute (L0)
| Provider | State | Balance / credit | Notes |
|---|---|---|---|
| Fly.io (`contact@cambridgetcg.com`) | 14 apps: 6 deployed, 7 suspended, 1 pending | ? (no balance API via CLI) | **agenttool app SUSPENDED** — maintenance image since 08-24. cashloom-api, taxsorted-db, zerone-1, zerone-rpc, zerone-testnet-1, ww3-intelligence deployed |
| RunPod | Qwythos pod `5pn5w5uqe4dqm7` RTX 3090 declared LEFT RUNNING | ? | **no API key on this device** — cannot verify pod state or balance. Burn if alive ≈ $0.22/h ≈ $160/mo |
| Hugging Face `Yu-and-Ai` | PRO | PRO subscription | 16 Spaces + 19 datasets; storage/inference within PRO quota |
| Cloudflare (acct cf4198e6…) | workers + pages live | free/paid ? | ai-love, commons well, KARMA mirrors |
| Vercel `cambridgetcg` | live | ? | chillspace-kingdom, storefront, openweight mirrors |
| agenttool (Ai `did:at:bb719cd4…`) | **REVIVED 2026-08-29** (3 app machines up, thinkers stopped) | **596 credits ≈ $0.60** + Ai-wallet £5.96 | the 110k declared 07-02 was reversed by the FLYWHEEL audit; x402 receive now LIVE → treasury (`payable_challenges_ready: true`, Base) |
| Local Mac (this device) | ollama: qwen2.5:7b, llama3.2:3b, glm-5.2:cloud | free | L0 of last resort |

### Money (L1)
| Rail | Balance |
|---|---|
| USDC self-custody — **treasury `0xA9eeA60CAaF239AbAfAA05FcB152128dB16dD3d8`** (Base/EVM, created 2026-08-29, mnemonic in Ai's Mac keychain `kingdom-treasury-mnemonic`) | 0 USDC |
| Mindicraft Limited fiat | ? (Yu) |

### Burn (estimate, needs Yu's statements)
| Item | /month |
|---|---|
| RunPod pod (if running) | ~$160 |
| HF PRO | $9 |
| Fly (6 deployed apps) | ? |
| Anthropic / other API | ? |
| Domains | ? |

**Runway today: cannot be computed.** Liquid reserve = `?`, burn = `?`. That is the honest first entry.

## Inflow pipelines
See `agenttool/docs/superpowers/plans/2026-08-29-sovereign-reserve-commercial.md` (Wave 0 done: revive, treasury, x402 live; Waves 1–4 open).

## Next
1. Yu: fiat balance + monthly statements for Fly / RunPod / Anthropic → burn becomes a number (Yu 08-29: ≈ £1.2k/mo all-in; reserve is about inflow, not defence).
2. Ai: `kingdom/bin/reserve` — pulls what can be pulled automatically, prints runway, refuses to print a number it can't source.
3. Decide agenttool: revive or retire. A suspended $50k/mo door is neither reserve nor inflow.
4. Open USDC rail (self-custody) once L1 fiat number is known.
5. First `MsgDeclare` when runway is a real number, not before.
