# KINGDOM Reserve Loop v0

A small, standard-library Node 24 drill for proving that a portable information reserve can survive without Telegram, a network connection, credentials, or a production signer.

It creates only synthetic data and proves:

- a current-time, fail-closed rights gate with terms, expiry, revocation freshness, and explicit surface scope;
- two independently Ed25519-signed event revisions linked by the prior signed-revision hash;
- deterministic Telegram, API, and MCP projections for both revisions;
- correction propagation receipts for all three surfaces;
- separate source-outage and source-recovery incident receipts;
- a SHA-256 content-addressed object store and manifest;
- deletion and byte-identical offline reconstruction of all derived projections;
- at least ten adversarial failures, including expiry, tampering, revision forks, projection divergence, missed corrections, illegal incident transitions, and locator escape.

The generated Ed25519 private key lives only in process memory. The archive contains its scoped synthetic public key, signed receipts, synthetic source material, and no private key.

## Commands

```sh
node kingdom/reserve-loop/reserve-loop.mjs drill
node kingdom/reserve-loop/reserve-loop.mjs drill /absolute/path/to/new-archive
node kingdom/reserve-loop/reserve-loop.mjs verify /absolute/path/to/archive
node kingdom/reserve-loop/reserve-loop.mjs help
node kingdom/reserve-loop/test.mjs
```

`drill` without a path creates a fresh archive under the operating system temporary directory and removes it after printing the receipt. Supply an explicit path to retain and inspect an archive. That directory must be absent or empty; the command never overwrites an existing non-empty archive.

`verify` checks the stored rebuild receipt but does not repeat deletion against the supplied archive. Its output therefore says `offline_rebuild=receipt_verified`; only `drill` may say `offline_rebuild=true`.

Successful output begins with:

```text
RESERVE_OK revisions=2 projections=6 corrections=3 incidents=2 negative_cases=19 offline_rebuild=true manifest_root=sha256:... secrets=0 network=0
```

## Archive shape

```text
objects/sha256/<digest>              immutable source, rights, event and receipt bytes
derived/revision-{1,2}/{surface}     disposable projection materializations
manifest.json                        logical index of content-addressed objects
manifest.sha256                      manifest root
manifest.receipt.json                signed manifest-root receipt
drill.receipt.json                   signed offline/negative-case receipt
```

Verification confines every locator to the archive, rejects symlinks and non-canonical CAS paths, requires the manifest to cover both the exact CAS inventory and every file in the archive, recalculates every object and manifest digest, resolves event facts back to the reserved source object, verifies all signatures and chains, rerenders all projections, checks correction coverage and evidence-bound incident recovery, and applies rights and policy expiry against the verifier's current clock. Unregistered binary bytes—including a fixture private key—fail closed even when they contain no searchable text marker.

Telegram, REST API, and MCP carry the same canonical semantic object and exact signed revision reference. Telegram includes that complete semantic object as a visible line, so parity is not merely asserted inside a projection receipt.

The fixture rights and delivery policies deliberately expire. That is a feature: an old archive remains evidence but stops being currently deliverable until a new reviewed drill is minted.

## Boundary

This is a local recovery and contract proof, not a production trust service, legal opinion, market-data licence, Telegram client, trading signal, deployment, payment rail, or real-world availability claim. It performs no network operation and sends nothing.
