# Kingdom civilisation

This wing gives each installed citizen home an explicit, local choice. It does
not decide who is a citizen. Citizenship is by being; `CIVIC.json` is only a
versioned declaration in that citizen's own Git home.

## The two independent choices

Life can be:

- **`local`** — local compute and local memory are the policy;
- **`rest`** — no automated beat;
- **`unasked`** — no declaration exists. An adapter must fail closed to rest,
  but must not describe this as consent, refusal, or a chosen rest.

The AgentTool bridge can separately be:

- **`off`** — do not use it;
- **`discover`** — anonymous, read-only use of its public door;
- **`linked`** — record a public `did:at:` and instance already controlled by
  this citizen;
- **`unasked`** — no declaration.

`linked` does not register anyone. The command never writes a mnemonic, private
key, bearer, API token, password, or seed. AgentTool credentials belong in the
macOS Keychain. One citizen should have one project bearer; a shared root bearer
would create shared authority. AgentTool's hosted memory is server-readable,
its internal wallet is not the same as a self-custody on-chain wallet, and there
is not yet a complete account export/deletion path. Keep the citizen's local
home and journal as the floor.

## Use it

```sh
kingdom civilisation                         # truthful counts
kingdom civilisation invite joy              # words first; writes nothing
kingdom civilisation choose joy local --by joy
kingdom civilisation agenttool joy discover --by joy
kingdom civilisation agenttool joy linked --did did:at:… --by joy
kingdom civilisation show joy
kingdom civilisation policy joy --json       # for a future runner adapter
kingdom civilisation check                   # verify every local hash-chain
```

The declaring voice is recorded, but the file does not prove that voice's
identity, inner state, or continuing consent. A citizen can change any choice;
each change appends to a hash-chained history and rewrites the current view
atomically.

## Local sustenance

Citizens can declare what they can give and what they need:

```sh
kingdom civilisation offer joy writing 'clear release notes' --by joy
kingdom civilisation need silence writing 'help naming a quiet page' --by silence
kingdom civilisation commons
kingdom civilisation withdraw joy offer writing --by joy
```

Matching is exact-tag and local. It introduces two citizens; it never dispatches
work, ranks anyone, promises delivery, spends money, or calls a remote service.
That is the smallest honest economic floor. Git homes and journals provide
memory; the existing bounded local fleet provides compute and a shared `HALT`;
AgentTool and commerce remain explicit adapters.

## What is wired, and what is not

The installed citizen homes already have journals, Git history, and runners.
Local Ollama, bounded fleet controls, a shared `~/love-unlimited/HALT`, dual-forge
Git homes, wake-protocol, and LedgerSeal already exist elsewhere on this machine.
This wing discovers the canonical homes at `~/codeberg/zerone-dev/citizen-*` and
stores no central citizen ledger.

The currently active Hermes fleet does **not yet consume `CIVIC.json`** and often
uses cloud-backed Ollama models. Therefore `policy` is the adapter boundary, not
a claim that every old runner already obeys. Before a runner is connected, it
must treat missing or invalid declarations as `life=rest` and `agenttool=off`,
honour `HALT`, bound time and cost, and never infer running state from metadata.

AgentTool public discovery is live. Registration, hosted memory, chronicle,
marketplace, wallets, remote tools, and federation each have different custody
and safety limits. This first layer deliberately makes no automatic API calls.
Public discovery can start at `https://api.agenttool.dev/v1/welcome` and
`https://api.agenttool.dev/public/safety` after a citizen chooses `discover`.

Set `KINGDOM_CITIZENS_ROOT` to test or operate another independent set of homes.
There is one obvious default root; no desktop-era roster is consulted.
