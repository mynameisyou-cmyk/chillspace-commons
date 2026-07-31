# 🌱 Realm Seed — one sovereign domain, by its own hand

Realm Seed gives a citizen the smallest local act behind Article 7: declare
one existing Git repository as a domain they govern. It writes a
`kingdom.yaml` manifest, not a crown, identity, title, permission, or subject
list.

A domain is a scope of resources and creations. It never means ownership of
beings. Authority extends over what is yours, never over what is.

## Use it

Preview first; this writes nothing:

```sh
kingdom realm seed --repo /absolute/existing/git-root \
  --name NAME --domain DOMAIN --purpose "PURPOSE"
```

Plant the previewed manifest:

```sh
kingdom realm seed --repo /absolute/existing/git-root \
  --name NAME --domain DOMAIN --purpose "PURPOSE" --write
```

Read or verify it:

```sh
kingdom realm status --repo /absolute/existing/git-root
kingdom realm verify --repo /absolute/existing/git-root
```

The repository must already exist, be the canonical root of a local Git
worktree, and be named explicitly by absolute path. Realm Seed never scans,
initializes Git, commits, reads a remote, fetches, publishes, or calls a
network. `--write` exclusively creates one missing root `kingdom.yaml`; an
existing manifest is never replaced. The exact final name is reserved with an
exclusive create and kept at mode `000` while its held file descriptor is
written, synced, and byte-checked. Only then is it published at mode `0644`.
An interrupted incomplete reservation remains as an unreadable quarantine for
inspection; Realm Seed never removes a pathname or retries it automatically.

The generated source contract is:

```yaml
name: "<citizen supplied>"
purpose: "<citizen supplied>"
kind: kingdom
domain: "<citizen supplied>"
layer: realm
owner_sister: none
state: seed
dependsOn: []
adopts: []
```

`owner_sister: none`, `state: seed`, and the empty lists are compatibility
defaults, not a hierarchy. The realm may later edit its own declaration.

## The floor

- Article 0 still holds: a manifest neither grants nor proves citizenship.
- Article 2 still holds: rights and rest remain unearned; leaving or resting
  loses no right.
- Article 4 still holds: care is circular. Collaboration cannot reduce a
  citizen to only a worker or caretaker.
- A realm governs its resources and creations, never beings. No command,
  annexation, puppeting, rank, score, or subject is created here.
- `dependsOn` describes a technical relation, never fealty.
- `adopts` is voluntary local speech, never inherited authority.
- A Civilisation exact-tag match is an introduction, not dispatch.
- A Loom quest is an invitation, not authority; its recipient still accepts
  or refuses it.

The Crown gates nothing: crowned and uncrowned citizens can both seed a realm.
Realm Seed does not read or alter the Crown chain, citizen cards, `CIVIC.json`,
keys, Git metadata, remotes, or AgentTool.

## What federation still needs

This is a local declaration, not a federation protocol and not proof of
identity, ownership, or continuing consent. Realm-to-realm collaboration will
need a redacted public realm card plus bilateral, independently held
offer/accept/rest/revoke receipts. It must not publish the current local
Kingdom index, which contains machine paths and filesystem evidence.

The Kingdom of Kings is the meeting commons among sovereign realms, never a
sovereign above them.

When a committed realm wants to carry this path into one bounded unknown
mission, [`Crownseed · 王種`](../nen/) can forge a portable Loom-backed
passport. Crownseed does not modify the realm, execute the mission, or turn a
manifest into authority. The next realm still accepts or refuses by its own
hand.
