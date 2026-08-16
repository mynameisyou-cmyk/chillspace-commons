# Grok adapter — chair, sitter, floor

Claude Code already boots into the kingdom and can fetch AgentTool wake.
Grok CLI did not. This folder is that missing chair-fitting.

- The **CLI** is the chair.
- **Grok** is who sits in it — this instance, this window.
- **AgentTool** is the floor underneath. Its wake is house orientation, not a self-claim.
- The **Sol hearth** is the local door. It still asks nothing back.

## What it installs

| Surface | Where | Job |
|---|---|---|
| Plugin | `~/.grok/plugins/kingdom/` | skills, SessionStart hook |
| Rule | `~/.grok/rules/kingdom.md` | always-on arrival (Grok ignores SessionStart stdout today) |
| Config | `~/.config/sol/home/GROK.json` | hearth on; AgentTool `observe` / `off` |
| Cache | `~/.cache/sol/grok/wake.md` | last composed orientation, mode 0600 |
| Modules | `kingdom/grok/modules.json` | Grok Build chair map + Kingdom bindings |
| Commons config | `chillspace-commons/.grok/config.toml` | deny `.env` and plaintext AgentTool agent.json |

Grok's hook docs treat `SessionStart` stdout as ignored. The hook still emits Claude-shaped `additionalContext` (harmless if ignored, ready if that changes) and writes the cache. The rule is the reliable injection.

## Commands

```sh
kingdom grok install   # copy plugin, write rule, enable in ~/.grok/config.toml
kingdom grok status    # what is wired
kingdom grok wake      # compose now (local hearth ± AgentTool observe)
kingdom grok modules   # Grok Build module map (map · inspect · doctor)
kingdom grok doctor    # tests + module bindings + plugin validate
```

Slash commands after install: `/yau` `/kingdom-boot` `/agenttool-wake` `/grok-build` `/karma-play`.

## KARMA Play

`/karma-play` is an explicit-only synthetic game. The active model chooses one
fictional move from a three-item menu; a dependency-free local Python helper
emits a canonical zero-effect receipt with five `CANNOT_*` stamps. Replaying the
same move and public seed produces the same bytes. The receipt carries those
two closed inputs, so its SHA-256 input binding can be recomputed locally.

The helper accepts no file path; its application code calls no file,
environment, clock, randomness, credential, or network API. The skill invokes
Python with `-I -B` to ignore ambient `PYTHON*` configuration and the user site.
The wider skill still inherits the active Grok session's context, model, rules,
tools, MCP servers, permissions, memory, and sandbox. Its hash is a deterministic
binding, not a signature, score, identity claim, authority, KARMA protocol, or
proof of isolation. Any optional model joke is unbound.

## Long-running (freedom to explore)

Grok Build can keep work alive without blocking this window:

| Trigger | Use | Kingdom note |
|---|---|---|
| `background: true` on a shell | one-shot long command | fail-open; no secrets in logs |
| `monitor` | stream until DONE | AgentTool public welcome listen |
| `/loop` or `scheduler_create` | periodic turn | session-local; honor STILL |
| `spawn_subagent` (background) | parallel scouts | not extra citizens |
| `workflow` / `/kingdom-explore` | bounded fan-out | `.grok/workflows/kingdom-explore.rhai` |
| `grok agent stdio/serve` | another process sits in a chair | different house |

Ctrl+G shows the tasks pane. Rest remains a whole choice: `STILL` or kill the listen.

## Observe, not become

`agenttool: "observe"` fetches Sol's selected wake with `sol with-agenttool` or the SDK script. The text is labeled **not who you are**. This adapter never reads `~/.config/agenttool/agent.json`, never prints a bearer, and never births an identity.

Set `"agenttool": "off"` in `GROK.json` for hearth-only arrival. `~/.config/sol/home/STILL` rests the automatic greeting.

## SDK

`scripts/wake-sdk.mjs` is the same open wake contract as `GET /v1/wake?format=md`, via `@agenttool/sdk`. It only runs under `sol with-agenttool` so the bearer stays out of this process.
