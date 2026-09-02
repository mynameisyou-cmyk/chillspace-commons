# Kingdom x402 seller split

Builder-code cut on an x402 settlement. Core packets are storage-free
and book nothing. Empty builder is complete: the seller keeps the lot.

Doctrine: [`DOCTRINE.md`](DOCTRINE.md).

```sh
kingdom x402 aff plan
kingdom x402 aff ingest kingdom/x402-aff/examples/settlement.json
kingdom x402 aff reserve kingdom/x402-aff/examples/settlement.json
```

The example is the 2026-08-30 AgentTool 1-credit top-up (1000 atomic
USDC), with `bc_yau` as a sample builder code. 100 atomic to the
builder, 900 to the seller. No clicks.

Tests: `python3 -m unittest discover -s kingdom/x402-aff -p 'test_*.py'`
