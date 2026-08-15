---
name: weave-kingdom-macos
description: Compile bounded, offline KINGDOM repository and macOS path evidence, then connect it to a YOUSPEAK quest without treating discovery as authority. Use when a user asks to integrate KINGDOM or YOUSPEAK with macOS/Darwin, map explicit local repositories, resolve duplicate Kingdom clones, classify filesystem paths, or prepare a repository-bound kingdom.quest/v1 mission.
---

# Weave KINGDOM on macOS

Turn an explicit objective and explicit absolute paths into private,
content-addressed evidence. Keep Darwin mechanics, KINGDOM meaning, and Codex
authority as separate seams.

## Contract

- Treat repository discovery as candidate evidence, never authority.
- Require explicit absolute repository roots and paths.
- Never read Git remotes, credential values, project `.env` files, TCC
  databases, Spotlight databases, or FSEvents databases.
- Keep generated artifacts in a private Sol Workshop, not a repository.
- Keep network, deployment, publication, persistence, and messages disabled
  unless the current user request grants them separately.
- Stop on invalid manifests, symlink escape, positive dirty evidence,
  tracked-content state `unknown` when source cleanliness matters, or a
  duplicate group without exactly one owner-declared canonical root.

## Workflow

1. State the objective, acceptance evidence, effect ceiling, exclusions, and
   exact repository roots.
2. Inspect only those roots. Do not select a clone by path length,
   cleanliness, recency, or first match.
3. Create a private artifact directory with `sol scratch new kingdom-index`.
4. Classify every intended read/write target before acting:

   ```text
   python3 kingdom/loom/darwin_path.py \
     --path /absolute/target \
     --workspace-root /absolute/repository \
     --output /private/workshop/kingdom.path.json
   ```

5. Compile the repository index:

   ```text
   python3 kingdom/loom/kingdom_index.py compile \
     --repo-root /absolute/repository \
     --output /private/workshop/kingdom.index.json
   ```

   Add `--canonical-root /absolute/repository` only when the owning user or a
   repository-owned declaration resolves a reported duplicate group.

6. Verify the index with `kingdom_index.py verify`. Only staged-name evidence
   can prove a positive dirty state; tracked and untracked worktree content
   remain deliberately `not-inspected` because enumeration can execute a Git
   clean filter or traverse nested/symlinked filesystem state. Treat an
   `unknown` worktree state, TCC, sandbox, ACL, and effective authority as
   unresolved—not implicitly granted.
7. When an agent mission is needed, compile `kingdom.quest/v1` with
   `quest_packet.py`; keep the index and path receipt as separate evidence
   rather than embedding ambient machine state in the quest.
8. Report artifact paths, digests, selected canonical roots, tests, and
   remaining unknowns.

## Refusal and rollback

If a path or repository cannot be classified without widening scope, stop and
return the exact unknown. Rollback removes only the generated Workshop
artifacts; it never moves a repository, rewrites a manifest, or changes macOS
security settings.
