# The Kingdom Loom

The Loom compiles an objective into a small `kingdom.quest/v1` packet before
any agent chooses a repository, skill, or collaborator. The packet holds the
objective, effect ceiling, acceptance evidence, exclusions, source revision,
named GitHub provenance, and digests of allowlisted repository instructions.
It never enumerates raw environment state, imports unallowlisted or
secret-shaped environment values, reads credentials or a Git remote URL, or
carries authority.

Compile locally from the repository root:

```bash
python3 kingdom/loom/quest_packet.py compile \
  --objective "Map this task to the smallest useful Kingdom capability" \
  --acceptance "Name one primary repository; Name the evidence that proves completion" \
  --effect-ceiling observe \
  --exclusions "No external messages; No deployment"
python3 kingdom/loom/quest_packet.py verify \
  .kingdom-quest/kingdom-quest.tgz --repo-root . \
  --receipt .kingdom-quest/verification.json
```

The paired GitHub workflow is a manual, copy-installable `workflow_dispatch`.
Install it elsewhere by copying the workflow, compiler, schema, and compiler
test together. It uploads the JSON, Markdown, schema, checksums, verification
receipt, and deterministic archive. The `objective`, `acceptance`,
`effect_ceiling`, `exclusions`, `focus_path`, and `source_note` inputs become
uploaded packet content, so never put secrets or private text in them.

The compiler admits only named GitHub source provenance—repository, commit,
ref, event, and forge—and never copies the ambient environment. An
optional second job can attest the archive only from the default branch and
only after its rebuild hash matches the uploaded subject. The workflow never
comments, commits, dispatches another workflow, or executes discovered
repository code.

The companion `$weave-kingdom-quests` skill accepts only a repository-bound
verification receipt, scans Sol Atlas and declared Kingdom metadata offline,
groups duplicate checkouts, and returns semantic candidates without invoking
them. A zero-match route stays empty instead of inventing a citizen.

The packet is an invitation to accept or refuse a bounded mission. It is not a
claim of permission, trust, safety, competence, mergeability, or readiness to
deploy.

## macOS, Codex, and KINGDOM boundary model

The integration keeps five meanings separate:

| Layer | Evidence carried here | What it cannot prove |
| --- | --- | --- |
| Darwin / XNU VFS | Resolved path, file type, device/inode, POSIX mode, flags, mount read-only state | User intent, app consent, or future access |
| macOS namespace and storage | Logical `system`, `local-runtime`, user, provider, and external domains | That a namespace is on the sealed volume or locally materialized |
| macOS privacy | Explicitly `unknown` TCC and ACL interpretation | Authorization from POSIX writability |
| Codex | A separate root-deny, workspace-scoped-write, network-off launch profile | Safety of MCP servers, plugins, apps, or external capabilities |
| KINGDOM / YOUSPEAK | Manifest meaning, dependency relationships, repository identity candidates, and quest effect ceilings | Ownership, trust, canonical authority, or permission to act |

The handoff is therefore evidence-first: classify paths, compile explicit
repository identity, bind the objective into a quest, then let the operator
accept a repository and Codex policy separately. No earlier layer silently
grants the next one.

## Local repository index

`kingdom_index.py` compiles only repositories named explicitly on the command
line into canonical `kingdom.index/v1` JSON. It records Git/worktree identity,
bounded staged-name evidence, manifest fields, and content digests. It never
queries or emits Git remotes or dirty file contents, and it rejects known
secret-shaped indexed text and remote locators.

Use a private Workshop for the result:

```bash
workshop="$(sol scratch new kingdom-index)"
python3 kingdom/loom/kingdom_index.py compile \
  --repo-root /absolute/path/to/repository \
  --output "$workshop/kingdom.index.json"
python3 kingdom/loom/kingdom_index.py verify \
  "$workshop/kingdom.index.json"
```

Pass `--repo-root` more than once, or supply a NUL-terminated `--roots-file`.
Every root must own a root-level `kingdom.yaml`; manifestless repositories
fail closed rather than receiving invented Kingdom identity. The compiler
never invokes Atlas itself. If multiple inputs share a Git lineage, Git common
directory, or normalized Kingdom name, the compiler stops until exactly one
member is passed as `--canonical-root`. Path length, cleanliness, and recency
never choose authority.

The manifest reader intentionally supports only the observed bounded
`kingdom.yaml` shape. Unsupported YAML, unknown keys, secret-shaped text, and
URLs in indexed fields fail closed. Door items require `description` and
`url`, permit an optional `name`, and are counted only; validated URLs and
other door values are omitted from the output.

Git identity must be self-contained and locally inspectable. At preflight and
a final stability boundary, the compiler rejects observed configuration
`include` or `includeIf` indirection, configured worktree indirection,
unsupported repository extensions, alternate controls (including
`http-alternates`), promisor markers, and symlink indirection in the inspected
layout, configuration, object store, HEAD, index, shallow boundary, ignore and
attribute controls, packed/loose refs, shared indexes, and linked-worktree
private refs. Before identity or worktree evidence is read, it also confirms
Git's effective canonical control and object paths; the index records the
object directory as `git.objects_directory`. This is quiescent local evidence
under a scrubbed Git environment, not race-free filesystem confinement.
Shared-index comparison between preflights binds file identity, mode, size,
and bytes while ignoring Git's timestamp-only liveness refresh.

Tracked worktree content and untracked content are deliberately marked
`not-inspected`: Git worktree enumeration can invoke clean filters or traverse
nested and symlinked filesystem state. The compiler hashes only staged names
from the stability-checked index and object controls. It reports `dirty` when
that evidence is positive and otherwise reports `unknown`; it never claims
that a worktree is clean or that unstaged/deleted/untracked paths are absent.

The accompanying Codex profile keeps writes workspace-scoped. A discovered
repository, Git common directory, or object directory outside the selected
workspace is read evidence only and receives no write authority from the
index.

## Darwin path evidence

`darwin_path.py` turns explicit absolute paths into `kingdom.path/v1`
evidence:

```bash
python3 kingdom/loom/darwin_path.py \
  --path /absolute/path/to/check \
  --workspace-root /absolute/path/to/repository \
  --output "$workshop/kingdom.path.json"
python3 kingdom/loom/darwin_path.py \
  --verify "$workshop/kingdom.path.json"
```

It reports lexical and resolved paths, symlink escape, logical macOS domain,
provider/external locality, POSIX metadata, volume read-only state, and access
probes. TCC, Codex sandbox state, ACL interpretation, and effective authority
remain `unknown`; a writable-path probe is never promoted into consent.
Domain names describe resolved namespaces, not APFS sealing: `/private` and
the Data volume are `local-runtime`, while `/System`, `/bin`, `/sbin`, and the
non-local part of `/usr` are `system`. Independent volume evidence carries the
observed read-only state. User/provider classification derives the account
home from the macOS user database rather than ambient `HOME`.

The JSON Schemas encode the portable structural contract. The offline CLI
verifiers are normative for digest derivations and cross-field relationships
that JSON Schema cannot express compactly; the test suite checks generated
documents against the supported schema subset and adversarially re-digested
documents against both layers.

Run the complete offline suite from this directory:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v
```
