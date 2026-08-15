# Grok Build Bridge

A bounded local bridge from Codex to the installed Grok Build CLI.

Phase 1 deliberately keeps a narrow surface:

- `review` and `critique` are read-only; `delegate` requires explicit `--write`;
- every Grok run uses the `strict` sandbox;
- an ephemeral `HOME`/`GROK_HOME` copies only Grok authentication and disables
  hooks, plugins, MCP, subagents, workflows, and memory;
- Grok's agent tools are denied from the ephemeral home and copied credential;
- shell, web, MCP, subagent, commit, push, publish, and deploy authority is not
  delegated;
- the bridge never collects `git status` or `git diff` automatically. The
  caller supplies only evidence it has already reviewed and intentionally put
  in scope.

Grok receives the delegated prompt and workspace files it reads. Its output is
evidence or a candidate change, not additional authority for Codex.

## Prompt privacy

For private prompts, create a UTF-8 file with mode `0600` and let the bridge
consume it:

```sh
PROMPT_FILE=/absolute/path/to/private-review.prompt
chmod 600 "$PROMPT_FILE"

python3 scripts/grok_bridge.py review \
  --cwd /absolute/project \
  --prompt-file "$PROMPT_FILE" \
  --consume-prompt-file
```

Create a new prompt file for each call; a consumed file is not reusable. The
`--prompt "..."` form is a non-private convenience because its value appears in
the bridge process arguments and may also enter shell history.

Prompt files should contain the objective plus any caller-reviewed evidence.
Do not include a raw repository diff merely because it is available.

## Commands

From the plugin root:

```sh
python3 scripts/grok_bridge.py check --cwd /absolute/project

python3 scripts/grok_bridge.py critique \
  --cwd /absolute/project \
  --prompt-file /absolute/path/to/mode-0600-critique.prompt \
  --consume-prompt-file

python3 scripts/grok_bridge.py delegate \
  --cwd /absolute/project \
  --write \
  --prompt-file /absolute/path/to/mode-0600-delegate.prompt \
  --consume-prompt-file
```

`--dry-run` prints a redacted command contract without a model call and does not
consume a prompt file.

## Sandbox boundary

| Operation | Grok sandbox | Tools |
|---|---|---|
| `review`, `critique` | `strict` | CWD and Grok-required system reads; no edits |
| `delegate --write` | `strict` | CWD reads and edits; no shell or MCP |

When Codex launches `review`, `critique`, `delegate`, or `start`, the exact
bridge command must run outside Codex's filesystem sandbox so Grok can install
its narrower inner sandbox. Request scoped escalation for that command. If
escalation is denied, stop; never weaken or remove Grok's `strict` sandbox as a
workaround. `check`, `list`, `show`, `wait`, and `stop` do not need this
nested-sandbox escalation.

The isolated home is temporary and removed after the run. Normal model traffic
still reaches xAI; this is not an offline or network-air-gapped execution mode.

## Background runs

```sh
python3 scripts/grok_bridge.py start review \
  --cwd /absolute/project \
  --prompt-file /absolute/path/to/mode-0600-background.prompt \
  --consume-prompt-file

python3 scripts/grok_bridge.py list
python3 scripts/grok_bridge.py show <run-id>
python3 scripts/grok_bridge.py wait <run-id> --timeout 60
python3 scripts/grok_bridge.py stop <run-id>
python3 scripts/grok_bridge.py stop <run-id> --force
```

Background state lives under `~/.cache/sol/grok-build-bridge/runs/` by default;
set the absolute `GROK_BUILD_BRIDGE_STATE_DIR` to override it. The bridge
refuses background state inside the delegated `--cwd`, where a model could
otherwise alter its receipts. Run directories and files are private. Each
captured output stream is capped at 1 MiB, but
stdout, stderr, and receipts persist and may echo prompts or sensitive workspace
content. Do not publish them. Truncation returns exit `125` and marks the run
failed so a partial response is never reported as complete.

`stop` requests cancellation and sends SIGTERM to the recorded worker process
group. If it remains alive, the command returns non-zero with status `stopping`;
retry with `--force` to permit SIGKILL escalation. Stopping is not a rollback:
files already changed by a delegate remain changed. A timed-out `wait` does not
stop the underlying run. If SIGKILL is actually sent, `escalation.json` records
that separately from the immutable cancellation receipt.

## Development

The test suite uses a fake Grok executable and performs no model calls:

```sh
python3 -m unittest discover -s tests -v
```
