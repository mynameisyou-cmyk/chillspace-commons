# Skycastle Chorus / 天城回聲

Skycastle Chorus is a local presentation layer for the KARMA Defense Lab. It
turns one fully replay-verified `traditional-nine` canary and completed receipt
into a small set of deterministic share artifacts. It is not connected to live
traffic, the public site, a workflow, or a deployment.

## Nen ability card

- **Name:** Skycastle Chorus / 天城回聲.
- **Desire:** let reviewed action signatures become warm, memorable castle
  pieces without turning a person, payload, or event into promotional material.
- **Affinity:** Transmutation plus bounded Conjuration. The Chorus transmutes
  already-reviewed classifications into fixed names, colors, pieces, and notes;
  it conjures only finite in-memory bytes from that pinned mapping.
- **Trigger:** one explicit invocation with the `traditional-nine` scenario, a
  valid content-bound canary, and a completed receipt that the pinned KARMA
  engine can reproduce exactly by replay. Merely parsing a receipt is not a
  trigger.
- **Anti-trigger:** live traffic, an incomplete or halted receipt, unreviewed or
  ambiguous input, a pin mismatch, an unmapped classification, or any attempt
  to add authority, identity, attribution, reflection, or publication.
- **Conditions:** the exact checked-in chorus catalog and its schema must match
  their content pins; the fixed sibling KARMA source must match its source pin;
  the replayed receipt must be canonically equal to the supplied completed
  receipt; and every ordered classification must have exactly one reviewed
  catalog mapping. There is no fallback catalog or best-effort rendering.
- **Limitation:** the projection surface contains only ordered reviewed
  classifications, fixed catalog presentation fields, and content digests. It
  never projects identity, inferred intent, guilt, raw payload, request path,
  host, credential, body, command, address, or submitted value.
- **Resource vow:** each artifact is assembled completely in memory, checked
  against its fixed byte and item caps, and only then written to standard
  output. One invocation emits one requested artifact.
- **Breach behavior:** malformed data, failed replay, source or catalog drift,
  unknown mappings, unsafe shape, and exceeded budgets reject the invocation.
  Rejection emits no artifact bytes to standard output; a fixed diagnostic may
  be written to standard error.
- **Proof:** deterministic tests cover replay, content pins, mapping coverage,
  output hashes and sizes, inert SVG structure, PCM framing and amplitude, raw
  data non-reflection, and rejection paths. Static inspection and a macOS
  sandbox check remain separate evidence about a particular execution.
- **Release:** release means the caller may keep, view, play, share, or discard
  a local artifact after review. It does not widen the renderer's powers or
  create any continuing action.

The strength comes from those constraints. A successful artifact is evidence
that a small pinned transformation completed; it is not evidence about a real
actor or a live defensive system.

## The reviewed constellation

These names attach only to fixture-action classifications. They are a playful
visual and musical vocabulary, not labels for people:

| Action classification | Chorus name | 城堡名 | Piece | Note |
| --- | --- | --- | --- | ---: |
| `nominal-control` | Open-Sky Bell | 晴空鐘 | beacon | 220 Hz |
| `route-discovery-fanout` | Empty-Corridor Atlas | 空廊圖 | map tower | 247 Hz |
| `session-replay` | Borrowed-Key Echo | 借匙回聲 | castle gate | 277 Hz |
| `path-boundary-probe` | Sideways Staircase | 橫行梯 | impossible stairs | 330 Hz |
| `query-broadening` | Everything Oracle | 萬答神諭 | library | 370 Hz |
| `active-markup-shape` | Paper Dragon | 紙龍 | flying banner | 440 Hz |
| `command-control-shape` | Thunder Without Sky | 無天雷 | weather vane | 494 Hz |
| `linklocal-resource-shape` | Mirror Behind Mirror | 鏡後鏡 | mirror moat | 554 Hz |
| `repeated-value-action` | Self-Counting Coin | 自數之幣 | market square | 659 Hz |
| `resource-pressure` | Giant at the Tiny Gate | 巨人叩微城 | outer wall | 740 Hz |

Lord 202, Architect of Absolutely Nothing, presides over the mock realm with
one useful reminder: “Your request has been promoted to architecture.”

## Output contract

The renderer has four receipt-bound outputs plus explicit source and manifest
verification commands:

- `verify-source` performs the full pinned replay without emitting a share
  artifact.
- `render-manifest` emits canonical JSON binding the replayed source, the
  catalog, renderer, classifications, digests, artifact sizes, and artifact
  hashes; `verify-manifest` independently checks that binding against the same
  canary and receipt.
- `render-svg` emits an inert, fixed `1200x630` SVG assembled from allowlisted
  shapes and text. It has no script, link, embedded resource, animation, event
  handler, or active styling surface.
- `render-wav` emits deterministic integer-generated RIFF/WAVE PCM: 8,000 Hz,
  mono, signed 16-bit little-endian. It uses no floating-point oscillator,
  metadata, clock, or random source.
- `share-copy` emits one fixed reviewed line, but only after the complete
  classification set verifies. It contains no link, exact public count, or
  submitted value.

The `X-Skycastle-*` protocol marks in the manifest are inert, fixed metadata.
The renderer never installs them as HTTP headers or sends them anywhere.

Exact SVG UTF-8 bytes are deterministic. Rasterized text pixels can still vary
between viewers because the SVG names a generic local font; pixel identity is
therefore not claimed. The WAV bytes and fixed share-copy bytes are
deterministic for the same pinned inputs.

## Execution boundary

Skycastle Chorus performs bounded reads of the exact checked-in catalog,
schema, fixed sibling engine, and caller-selected canary and receipt regular
files. Its only artifact channel is standard output. It makes no network call,
filesystem mutation, subprocess, model call, environment discovery, clock or
randomness query, redirect, callback, or automatic post.

Python isolated mode (`-I`) intentionally omits the script directory from
`sys.path`. The renderer's fixed `importlib` load of the named sibling
`karma_defense_lab.py` is the one reviewed exception: it neither searches nor
mutates `sys.path`, and the loaded source is accepted only when its content pin
matches. It is not a plugin surface or dynamic-code authority.

The manifest's `renderer_sha256` is the observed digest of the fixed local
renderer file at process startup, rechecked before output. It detects source
drift during the process and binds later verification to that file, but it is
not an operating-system attestation of the exact bytes Python had already
compiled. Strong execution attestation would require a separately reviewed
read-once launcher.

## Local-only workflow

Run from this directory with Python 3.11 or newer. The following creates a
private unpredictable temporary directory, asks the core lab for the bound
inputs, and asks the Chorus for one artifact at a time:

```sh
scratch_dir="$(mktemp -d)"
chmod 700 "$scratch_dir"

python3 -I -B karma_defense_lab.py canary traditional-nine > "$scratch_dir/canary.json"
python3 -I -B karma_defense_lab.py render traditional-nine "$scratch_dir/canary.json" > "$scratch_dir/receipt.json"

python3 -I -B skycastle_chorus.py check
python3 -I -B skycastle_chorus.py digest
python3 -I -B skycastle_chorus.py verify-source traditional-nine "$scratch_dir/canary.json" "$scratch_dir/receipt.json"
python3 -I -B skycastle_chorus.py render-manifest traditional-nine "$scratch_dir/canary.json" "$scratch_dir/receipt.json" > "$scratch_dir/skycastle.json"
python3 -I -B skycastle_chorus.py verify-manifest traditional-nine "$scratch_dir/canary.json" "$scratch_dir/receipt.json" "$scratch_dir/skycastle.json"
python3 -I -B skycastle_chorus.py render-svg traditional-nine "$scratch_dir/canary.json" "$scratch_dir/receipt.json" > "$scratch_dir/skycastle.svg"
python3 -I -B skycastle_chorus.py render-wav traditional-nine "$scratch_dir/canary.json" "$scratch_dir/receipt.json" > "$scratch_dir/skycastle.wav"
python3 -I -B skycastle_chorus.py share-copy traditional-nine "$scratch_dir/canary.json" "$scratch_dir/receipt.json" > "$scratch_dir/share.txt"
```

The shell creates the temporary files and performs every `>` redirection; the
renderer itself does not create or write them. Review the outputs locally, then
move the private temporary directory to Trash when it is no longer useful.

## Non-claims

`local-opt-in` is a catalog release posture, not marketing consent, ownership,
attribution, authority, approval, or a right to publish. A receipt does not
identify a person, infer purpose or intent, establish guilt, license promotion,
or authorize live integration. A generated name belongs to a reviewed action
classification, never to a person.

Nothing here is claimed to be deployed. Skycastle Chorus remains a local,
offline, reviewable rendering practice until a separate, explicit proposal is
authorized and independently assessed.
