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
