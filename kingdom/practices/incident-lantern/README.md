# Incident Lantern

Incident Lantern turns one replay-verified, offline Future-KARMA decision into
a compact incident record that a responder can discover, understand, review,
and carry forward as a regression candidate. It produces explanation and
decision support; it does not detect live traffic, execute containment, or
grant authority.

The local outcome is deliberately simple:

```text
closed categorical event + Future-KARMA receipt
    -> pinned fresh replay
    -> facts / inferences / unknowns
    -> proposal-only action cards
    -> human-review regression candidate
```

| Replay result | Incident result | Privacy and action boundary |
| --- | --- | --- |
| reviewed `planned` receipt | `ready-for-review` | Reviewed categorical fields may enter the candidate; actions remain unexecuted proposals. |
| valid `halted` receipt | `halted-for-review` | Unreviewed selector values are withheld, the event projection becomes digest-only, and mapping remains a human task. |
| malformed, drifted, or unverifiable source | rejected | No incident or candidate bytes are written to standard output. |

`ready-for-review` means that the explanation is ready for a person to inspect.
It does not mean that an action is approved, safe for production, or already
effective.

## What the engine accepts

`build` and `candidate` read exactly one `kingdom.incident-source/v1` wrapper
from standard input:

```json
{
  "schema": "kingdom.incident-source/v1",
  "event": { "...": "one closed kingdom.karma.event/v1 object" },
  "receipt": { "...": "its kingdom.karma.receipt/v1 object" }
}
```

The ellipses above describe the shape; they are not valid input. The event must
already satisfy Future-KARMA's closed categorical contract. Raw requests,
bodies, prompts, headers, credentials, filesystem paths, identity, and free
text do not belong in this wrapper.

For each accepted source, the engine:

1. verifies the exact pinned Future-KARMA source and bundle bindings;
2. validates the closed event;
3. freshly recomputes the expected receipt;
4. verifies the supplied receipt against that replay;
5. discards the supplied receipt object and builds from the recomputed value;
6. emits one bounded canonical JSON artifact plus one line feed.

A digest establishes deterministic content binding inside this contract. It
does not authenticate an external sensor, prove an event occurred, or supply
missing time, sequence, duplication, impact, retention, or containment state.

## Knowledge and action model

The incident schema keeps three epistemic lanes physically separate:

- **facts** are confirmed facts about the bounded computation, such as source
  contract validation, exact replay, and the policy output;
- **inferences** are explicitly policy-derived readings, not claims about a
  person or the world;
- **unknowns** name what this source cannot establish and whether resolution
  requires human review or evidence outside the source contract.

The ordered timeline records contract phases, not wall-clock events. Incident
Lantern has no trusted clock and does not invent timestamps or causality.

Every action card carries its authority requirement, automatic state, actual
effect, reversibility, blast-radius posture, preconditions, rollback, and
verification steps. All three cards are `not-executed`; external actions are
`human-required`. The engine's modelled controls remain zero-effect.

The embedded regression candidate is also proposal-only:

- promotion is `human-review-required`;
- `automatic_install` and `classifier_mutated` are false;
- authority is `none`;
- promotion requires joint review of policy, threat model, corpus, pins, and
  tests.

For a reviewed planned match, the candidate retains only the closed reviewed
categorical event. For a valid halt, it retains the original event digest but
replaces the unreviewed selector with fixed `withheld-unreviewed` values and is
`blocked-until-mapped`. Neither form contains raw traffic or identity.

## Local workflow

Run from the repository root with Python 3.11 or newer. This example also uses
the repository's existing `jq` command to select a checked-in synthetic
fixture, ask Future-KARMA for its receipt, and assemble the exact source
wrapper. The shell creates every output file;
`incident_lantern.py` reads caller data only from standard input, reads its
pinned local engine and schema dependencies, and writes artifacts only to
standard output.

For the fastest rehearsal, rebuild the checked-in synthetic golden and compare
it byte-for-byte without creating another file:

```sh
python3 -I -B \
  kingdom/practices/incident-lantern/incident_lantern.py build \
  < kingdom/practices/incident-lantern/examples/resource-pressure.source.json \
  | cmp - \
      kingdom/practices/incident-lantern/examples/resource-pressure.incident.json
```

The longer flow below shows how the source wrapper itself is assembled.

```sh
scratch_dir="$(mktemp -d)"
chmod 700 "$scratch_dir"

jq -c '.cases[1].event' \
  kingdom/practices/karma-defense-lab/future/examples/adversarial-corpus.json \
  > "$scratch_dir/event.json"

python3 -I -B \
  kingdom/practices/karma-defense-lab/future/future_karma.py plan \
  < "$scratch_dir/event.json" \
  > "$scratch_dir/receipt.json"

jq -cn \
  --slurpfile event "$scratch_dir/event.json" \
  --slurpfile receipt "$scratch_dir/receipt.json" \
  '{schema:"kingdom.incident-source/v1",event:$event[0],receipt:$receipt[0]}' \
  > "$scratch_dir/source.json"

python3 -I -B \
  kingdom/practices/incident-lantern/incident_lantern.py build \
  < "$scratch_dir/source.json" \
  > "$scratch_dir/incident.json"

python3 -I -B \
  kingdom/practices/incident-lantern/incident_lantern.py candidate \
  < "$scratch_dir/source.json" \
  > "$scratch_dir/candidate.json"
```

Verify that an incident is still the exact result of its source:

```sh
jq -cn \
  --slurpfile source "$scratch_dir/source.json" \
  --slurpfile incident "$scratch_dir/incident.json" \
  '{schema:"kingdom.incident-verify/v1",source:$source[0],incident:$incident[0]}' \
  > "$scratch_dir/verify.json"

python3 -I -B \
  kingdom/practices/incident-lantern/incident_lantern.py verify \
  < "$scratch_dir/verify.json"
```

Successful verification emits exactly `true`. Keep the scratch directory
private and discard it after review according to the caller's retention
policy; this engine neither owns nor proves deletion.

### CLI contract

```text
incident_lantern.py check
incident_lantern.py digest
incident_lantern.py build       < incident-source.json
incident_lantern.py candidate   < incident-source.json
incident_lantern.py verify      < incident-verify.json
```

- `check` validates the pinned contract against the reviewed Future-KARMA
  corpus and a privacy-preserving halted case.
- `digest` emits the current incident, schema, Future-KARMA, policy, and threat
  model bindings.
- `build` emits one canonical `kingdom.incident/v1` record.
- `candidate` emits the canonical embedded
  `kingdom.karma.regression-candidate/v1` projection directly.
- `verify` freshly rebuilds the expected incident and requires canonical
  equality with the supplied incident.

Exit status `0` means the requested local computation succeeded. A valid
Future-KARMA halt is a successful `halted-for-review` result, not malformed
input. Usage errors, unsafe input, pin drift, failed replay, tampering, and
budget violations return `2`, emit no standard-output bytes, and write exactly
`incident-lantern: rejected` to standard error. Interruption returns `130`;
a broken output pipe returns `141`.

## Local dashboard

The dashboard is a local reader for an already-built canonical incident. It
does not perform the Python receipt replay. It checks canonical ASCII bytes,
closed shapes, exact engine/schema/policy/threat pins, all planned selectors
against the 24-rule reviewed table, resolved evidence references, both
digests, and the complete reconstructed explanation before rendering the
timeline, epistemic lanes, action cards, and learning guidance. A persistent
warning still requires the source envelope and Python `verify` before
operational review because public pins and self-digests do not authenticate
file origin.

Serve it only on loopback:

```sh
python3 -m http.server 8765 \
  --bind 127.0.0.1 \
  --directory kingdom/practices/incident-lantern/dashboard
```

Open `http://127.0.0.1:8765/`, choose the generated `incident.json`, and stop
the server with Control-C when finished. The page uses integrity-bound local
script and stylesheet assets under a restrictive Content Security Policy. It
has no
fetch, analytics, storage, cookie, model, service-worker, or messaging path.
The chosen file is held in page memory until it is cleared or the page closes;
that is distinct from the Python engine's zero-retention contract.

The Download button is the dashboard's one intentional write capability. Only
an explicit click creates one local Blob download of the revalidated canonical
candidate; the temporary object URL is immediately revoked. That browser
download does not edit this repository, install a fixture, change the
classifier, publish anything, or authorize an action. The downloaded file
persists under the browser and user's retention choices.

## Artifact map

| File | Role |
| --- | --- |
| [`incident_lantern.py`](incident_lantern.py) | Pinned replay, minimized projection, canonical build/candidate/verify CLI. |
| [`incident.schema.json`](incident.schema.json) | Closed `kingdom.incident/v1` shape for source, headline, epistemics, timeline, actions, learning, controls, and nonclaims. |
| [`regression-candidate.schema.json`](regression-candidate.schema.json) | Closed proposal-only regression candidate and promotion boundary. |
| [`dashboard/index.html`](dashboard/index.html) | Accessible local import and incident presentation structure. |
| [`dashboard/app.js`](dashboard/app.js) | Local validation, safe DOM rendering, clear, and explicit candidate download. |
| [`dashboard/styles.css`](dashboard/styles.css) | Responsive, focus-visible, reduced-motion-aware presentation. |
| [`examples/resource-pressure.source.json`](examples/resource-pressure.source.json) | Reviewed synthetic `planned` source wrapper for local rehearsal. |
| [`examples/resource-pressure.incident.json`](examples/resource-pressure.incident.json) | Canonical golden incident that can be loaded directly into the dashboard. |
| [`test_incident_lantern.py`](test_incident_lantern.py) | Replay, tamper, privacy, closure, determinism, effect, CLI, and non-mutation tests. |
| [`test_dashboard.mjs`](test_dashboard.mjs) | CSP, no-egress, accessibility structure, validation, rendering, and explicit-download tests. |
| [`DOCTRINE.md`](DOCTRINE.md) | Design doctrine for discoverable, understandable, actionable, and learnable incidents. |

## Verification

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -I -B \
  kingdom/practices/incident-lantern/test_incident_lantern.py -v

PYTHONDONTWRITEBYTECODE=1 python3.11 -I -B \
  kingdom/practices/incident-lantern/test_incident_lantern.py -v

node --test kingdom/practices/incident-lantern/test_dashboard.mjs

python3 -I -B \
  kingdom/practices/incident-lantern/incident_lantern.py check

python3 -I -B \
  kingdom/practices/incident-lantern/incident_lantern.py digest

python3 -I -B \
  kingdom/practices/karma-defense-lab/future/test_future_karma.py -q

git diff --check
```

On macOS, a deny-network, deny-write, deny-fork `sandbox-exec` rehearsal can
add host-specific evidence for one invocation:

```sh
/usr/bin/sandbox-exec \
  -p '(version 1) (allow default) (deny network*) (deny file-write*) (deny process-fork)' \
  python3 -I -B \
  kingdom/practices/incident-lantern/incident_lantern.py check
```

A passing sandbox rehearsal is evidence about that command, profile, host, and
moment. It is not proof of macOS-wide confinement, a production sandbox, or
deployment safety.

## Boundaries and remaining verification debt

Incident Lantern has no production route, live adapter, telemetry feed,
identity store, intent model, raw-traffic intake, automatic response, or
deployment authority. It neither retaliates nor acts on an external system.
Caller-owned systems remain responsible for authentic collection, clocks,
deduplication, access control, retention, deletion, rate limiting, live blast
radius, authorization, rollout, rollback, and observation after a change.

Automated checks can cover byte determinism, schema closure, replay, privacy
projection, CSP/source boundaries, DOM construction, keyboard structure, and
the one-click lifecycle. They do not replace a manual Safari and VoiceOver
review. Before claiming browser-level readiness, verify on macOS that keyboard
order, spoken grouping, 200% zoom, narrow reflow, status announcements, local
file clearing, and the immediately revoked candidate download work as
intended, while Safari's Network inspector shows no unexpected request.
