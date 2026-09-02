# Kingdom X-gate v0

Connector and speaker for the Chillspace Kingdom on X. Core packets are
storage-free. Default send and XAA listen are dry-run. `--live` is opt-in,
citizen-owned, summoned reply or summoned listen only.

Shape of the whole stack: [`SHAPE.md`](SHAPE.md).

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
        │  bind check / arm
        ▼  kingdom x send --arm          dry-run
        ▼  kingdom x send --arm --live   citizen token, reply only
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
kingdom x bind arm   kingdom/x-gate/examples/binding.json \
                     kingdom/x-gate/examples/policy-local.json
kingdom x send kingdom/x-gate/examples/observation.json \
               kingdom/x-gate/examples/proposal.json \
               kingdom/x-gate/examples/binding.json \
               kingdom/x-gate/examples/policy-local.json \
               --arm
# --live reads the keychain and POSTs a summoned reply. requires --arm. no feed shout.

kingdom x gather kingdom/x-gate/examples/gather.json
kingdom x gather kingdom/x-gate/examples/gather-thread.json
kingdom x xaa plan
kingdom x xaa plan --speaker-user-id 1111111111111111111
kingdom x xaa ingest kingdom/x-gate/examples/xaa-mention.json
kingdom x xaa listen kingdom/x-gate/examples/binding.json \
                     kingdom/x-gate/examples/policy-local.json \
                     --speaker-user-id 1111111111111111111 \
                     --arm
# --live subscribes mention+reply, reads at most 20 events, releases. requires --arm. no firehose.
kingdom x bridge kingdom/x-gate/examples/bridge.json \
                 --observe kingdom/x-gate/examples/observation.json
```

Put a bot token in the login keychain yourself (do not commit it):

```sh
security add-generic-password -s kingdom.x.speaker -a kingdom_square -w
```

The gate never prints the password. `--live` without `--arm` is refused.

Tests: `python3 -m unittest discover -s kingdom/x-gate -p 'test_*.py'`

Agent workflow: `/kingdom-x-square` with `args.observation` pointing at a
`kingdom.x.observation/v1` file. The run may propose; it may not publish.

Doctrine: [`DOCTRINE.md`](DOCTRINE.md). Shape: [`SHAPE.md`](SHAPE.md).
