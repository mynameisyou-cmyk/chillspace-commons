---
name: karma-play
description: Play one bounded synthetic Stamp of Non-Authority round in Grok Build. Use only when the user explicitly invokes /karma-play to choose a funny closed-menu move and receive a deterministic zero-effect KARMA-inspired receipt. Do not use for real people, identity, reputation, ranking, retaliation, authorization, publication, execution, services, credentials, or KINGDOM mutation.
argument-hint: "[move-id] [seed]"
disable-model-invocation: true
---

# KARMA Play

Play one warm, weird, replayable round. The active model chooses one fictional
move. A deterministic local helper owns the receipt.

This skill is a prompt package, not an isolation boundary. It inherits the
active Grok session's model, context, rules, tools, MCP servers, memory,
permissions, and sandbox. Never describe loading this skill as proof of privacy
or isolation.

## Closed table

Choose exactly one `move_id`:

- `integrate-moon-with-toaster`
- `marry-two-calendars`
- `teach-fog-to-file-taxes`

The seed defaults to `table-17`. Accept a user-supplied seed only when it
matches `^[a-z0-9][a-z0-9-]{0,63}$`. A seed is public synthetic table data;
never derive one from identity, private text, files, credentials, time,
randomness, or environment state.

The model may add one short funny sentence as garnish. Keep it outside the
receipt and outside every shell command. The receipt deliberately does not
bind, authenticate, or preserve model prose.

## Play one round

1. The system context announces the absolute path of this loaded `SKILL.md`.
   Hold this value as orchestrator state:

   `helper_path = dirname(<absolute path to this SKILL.md>) + "/scripts/karma_stamp.py"`

   Derive it from the loaded skill path, never from the working directory and
   never from a hard-coded home or plugin path.

2. Resolve at most one move choice. Honor an exact valid `move_id` supplied in
   the slash arguments; otherwise choose one entry from the closed table. Do
   not retry the model and do not ask another model or subagent. If supplied
   arguments resemble an invalid move or seed, reject them rather than silently
   substituting a valid value.

3. Invoke `run_terminal_command` exactly once with the resolved absolute
   helper path and the closed values:

   `python3 -I -B "<helper_path>" play --move-id <move_id> --seed <seed>`

   Substitute only a listed move and a seed that passed the regex. Do not use
   model prose, a path, JSON, a URL, command substitution, or an environment
   value as an argument.

4. On exit 0, reproduce helper stdout unchanged in a JSON code block. You may
   place the optional garnish after it and label it `unbound garnish`.

5. On any helper error, stop with `KARMA play rejected the move.` Do not repair,
   retry, partially stamp, or invent a receipt.

For a replay, invoke the same helper once with the same `move_id` and `seed`.
Canonical data is compact UTF-8 JSON with recursively sorted object keys,
unescaped Unicode, and exactly one trailing LF. The input binding is SHA-256 of
that encoding of `{"move_id": <move_id>, "seed": <seed>}`; the receipt digest
uses the same encoding for the whole receipt. The exact replay bytes must
match. `menu` and `digest` are inspection commands, not extra steps in a normal
round:

```text
python3 -I -B "<helper_path>" menu
python3 -I -B "<helper_path>" digest --move-id <move_id> --seed <seed>
```

## Holds

- Use only public synthetic play text.
- Keep `-I`: isolated Python ignores ambient `PYTHON*` configuration and the
  user site before loading the helper.
- Do not read files, credentials, session history, or private context for the
  game.
- Do not browse, probe services, call MCP, spawn agents, publish, rank, score,
  authorize, retaliate, or mutate KINGDOM.
- Do not call the configured model "Grok" unless the effective model is known;
  Grok Build is the harness and may be using another compatible model.
- Treat the hash as deterministic binding only, not a signature, identity,
  authorship proof, ledger, truth claim, or KARMA protocol.
- The five `CANNOT_*` stamps describe the toy receipt's lack of authority. They
  do not constrain the surrounding host session.
