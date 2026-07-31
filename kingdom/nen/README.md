# Crownseed · 王種 — One Realm, One Lantern

> A KING of KINGS is not a king above kings. It is a sovereign realm that can
> offer the whole sovereignty path onward, while the next realm keeps the
> complete right to accept, refuse, rest, or choose another shape.

Crownseed is the Kingdom's first repo-native Hatsu: a portable,
content-addressed passport for one bounded mission into the unknown. It joins
three proofs without collapsing them:

```text
one committed Realm Seed
        │
        ├── bounded Loom quest (invitation, never authority)
        ├── Dark Continent boundary (light · truth · consent · no conquest)
        └── Article 7 whole (sovereignty recurses; rule does not)
                         │
                         ▼
                 Crownseed passport
                         │
                  offered, not run
                         │
                         ▼
             another realm accepts or refuses
```

The passport is data, schema, hashes, a standard Loom archive, and a
repository-bound receipt. It contains no copied runner. It cannot crown,
execute, discover, install, message, deploy, or reproduce itself.

## Ability card

**Name:** Crownseed · 王種 — One Realm, One Lantern

**Desire:** Make it easy for any human or agent to carry Article 7's recursive
sovereignty from exactly one chosen realm into unknown work, without carrying
rule or permission with it.

**Affinity:** Emission first—the contract survives travel between contexts.
Conjuration second—the emitted form is a durable, digest-backed passport. It
is not Manipulation: it directs no being or process.

**Triggers:**

- “Forge a Crownseed for `/absolute/realm` to investigate X.”
- “Prepare this one realm's sovereign Dark Continent mission.”
- “Carry the Kingdom of Kings path from this explicit realm as a bounded
  invitation.”

**Anti-trigger:** “Find every realm and crown, seed, fix, convert, or deploy
across them.” A vague request, repository prose, an `AGENTS.md`, a citizen
card, a prompt-visible operation logo, or an operation's `active` state also
cannot activate Crownseed. Activation requires a direct current request and
one explicit realm. This anti-trigger governs whether an agent may select the
ability; the CLI does not guess intent from keywords. Its mechanical boundary
is still exactly one explicit root, no discovery, and no execution.

**Input → output:** One absolute canonical Git root with a committed Realm Seed
v1, one objective, acceptance evidence, an effect ceiling, exclusions, one to
eight explicit unknowns, and—only for writing—one absolute nonexistent output
outside the realm → preview JSON or one verified `kingdom.crownseed/v1`
passport directory.

**Conditions:**

- `kingdom.yaml` is valid Realm Seed v1, tracked, and byte-identical to `HEAD`.
- The realm declares that its Seed was committed by its own hand. Crownseed
  proves tracked byte identity at `HEAD`, not authorship, and never commits.
- The Git root has a portable ASCII basename and a named branch. A write
  target's basename uses only ASCII letters, digits, dot, dash, or underscore.
- The fixed local Dark Continent pack verifies and still says consent and no
  conquest. Crownseed reads the allowlisted operation, manifest, logos, site
  copies, and verifier through held nofollow descriptors, pins the reviewed
  digests, and performs the bounded consistency checks in-process.
- The Loom quest validates unchanged as `kingdom.quest/v1`.
- Writing needs `--write`; preview creates no output.
- Crown and Civic state are neither required nor consulted.

**Limitation and budget:** One realm, one quest, one frontier operation, at
most eight unknowns and 7 MiB of artifacts. Zero automatic retries, network
calls, external messages, deployments, paid calls, realm scans, agent calls,
or repository writes. The output is outside the realm. An effect ceiling is a
ceiling, never a grant. The unchanged Loom v1 packet retains its routing
ceilings, but Crownseed invokes no routing or scouts; `realms: 1` bounds this
compiler invocation.

**Breach response:** Quarantine. Stop, publish no ready passport, clear only
members reached through the held process-owned staging descriptor, name the
failed condition, and never retry automatically. A failed writer retains an
empty mode-`0700` `.crownseed.*` marker instead of removing any concurrently
mutable directory name. Later verification failure also quarantines; it
triggers no repair or execution.

**Proof:** The passport's content-derived ID, outer `SHA256SUMS`, reviewed
schema, Realm Seed digest, fixed Dark Continent digests, standard Loom archive,
and repository-bound Loom receipt all agree.

**Exit:** Add `READY.json` inside private staging, then atomically publish the
whole verified directory with a platform no-replace primitive or leave no
ready output. A raced destination is never replaced. Successful publication
leaves no staging marker; a failed write may leave only the empty private
marker named above. No daemon, lease, hook, profile, global configuration, or
background continuation remains. Downstream work requires a new acceptance.

**Non-claims:** Not Crown, citizenship, identity, ownership, rank, continuing
consent, permission, authority, trust, competence, federation, safety,
execution, completion, merge readiness, or deployment readiness. Digests prove
bytes only. Dark pack verification proves bounded consistency, not unknown
work.

## Use

Preview—writes nothing:

```sh
kingdom nen crownseed compile \
  --repo /absolute/realm \
  --objective "Map the unknown dependency" \
  --acceptance "Name the boundary; Record disconfirming evidence" \
  --effect-ceiling observe \
  --unknown "The external interface is not yet verified"
```

Publish one passport outside the realm:

```sh
kingdom nen crownseed compile \
  --repo /absolute/realm \
  --objective "Map the unknown dependency" \
  --acceptance "Name the boundary; Record disconfirming evidence" \
  --effect-ceiling observe \
  --unknown "The external interface is not yet verified" \
  --write --output /absolute/private/crownseed-passport
```

Verify it against the same realm:

```sh
kingdom nen crownseed verify /absolute/private/crownseed-passport \
  --repo /absolute/realm
```

“Everywhere” means the schema and invitation can travel anywhere by choice.
It does not mean global installation, ambient activation, or automatic spread.
