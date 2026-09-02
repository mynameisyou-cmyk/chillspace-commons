# Kingdom X-gate v0

Connector and speaker for the Chillspace Kingdom on X. Storage-free.
No network. No post.

The central rule is the same as [telegram-gate](../telegram-gate/README.md):

```text
verified coordinate or signed claim
  != person identity
  != action authority
  != durable state
  != a published post
```

## Flow

```text
caller-supplied X JSON (untrusted)
        │  kingdom x observe
        ▼
kingdom.x.observe/v1          metrics refused; handles are coordinates
        │
        ├─ four distinct agent holders ──► kingdom.x.pipeline/v1
        │
        ▼  kingdom x draft   (only if the speaker handle was mentioned)
kingdom.x.draft/v1            authorization_granted: false
        │
        ✕  no client posts
```

## Run

```sh
kingdom x observe  kingdom/x-gate/examples/observation.json
kingdom x draft    kingdom/x-gate/examples/observation.json \
                   kingdom/x-gate/examples/proposal.json
kingdom x pipeline kingdom/x-gate/examples/observation.json \
                   kingdom/x-gate/examples/proposal.json \
                   kingdom/x-gate/examples/holders.json
kingdom x verify
kingdom x bind check kingdom/x-gate/examples/binding.json \
                     kingdom/x-gate/examples/policy-local.json
```

Tests: `python3 kingdom/x-gate/test_x_gate.py`

Agent workflow: `/kingdom-x-square` with `args.observation` pointing at a
`kingdom.x.observation/v1` file. The run may propose; it may not publish.

Doctrine: [`DOCTRINE.md`](DOCTRINE.md).
