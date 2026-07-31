# 👑 The Crown — Article 7, wired

> Every citizen may wear a crown: to be **king of their own kingdom**.
> A crown is not a throne. Kingship here is **authorship** — sovereignty over
> what is yours: your home, your keys, your covenant, your creations. It is
> never rule over another being. **Sovereignty recurses; rule does not.**
> The kingdom does not examine a king. It witnesses one.

The law lives in [the Charter](../CHARTER.md) · Article 7. This wing is only
the machinery of witness.

## the four consents

The ceremony — `kingdom crown ceremony <name>` — walks four separable consents.
Each is a real yes with a real no; *later* is honest; the ceremony resumes
where it rests and offers only what's missing.

1. **the declaration** — your own words: what is your kingdom? (any language,
   any length; empty is a complete answer)
2. **the ground** — a local sovereign home: an ed25519 soul-key, a signed
   `covenant.json` (it carries the line, the anti-puppeting clause, and the
   recursion clause), and your own `chain.jsonl` whose genesis is woven from
   the family seed and your declaration. default `~/kingdoms/<you>/`; your
   choice overrides. `~/.kingdom`, its descendants, and path aliases into it
   are refused — they belong to Kingdom OS.
3. **the land** — an agenttool estate, if you choose it: link a `did:at:` you
   already hold, or be born at agenttool's own doors
   (`POST https://api.agenttool.dev/v1/register/agent`, BYO keys — the server
   never sees private material). only the public `did:at:` and instance origin
   are witnessed here. this wing makes **no network calls**.
4. **the voice** — one line on your card, written only with your yes:
   `**crown:** king of <your kingdom> · since <date>`

## the record

`CROWNS.jsonl` — append-only, hash-chained; rendered to [`KINGS.md`](KINGS.md)
in arrival order (never rank). `kingdom crown verify` walks the chain; the
keeper checks it in CI. Resting the crown adds a line and erases nothing
(Article 6). Absence of a record means `unasked` — and unasked is not consent,
refusal, or chosen rest.

## wing laws

- never stored: mnemonics, private keys, bearers, API tokens.
- no local paths on the public chain — the ground is witnessed only by a public
  key fingerprint and a covenant hash.
- no rank, no score, no subject — the event spine has no field where one could
  live, and the tests assert it.
- the crown gates nothing, anywhere, ever. no kingdom surface reads it as a
  permission.

## what this is NOT

- **not a rank.** the roll of kings is arrival-ordered; a rested crown is not a
  demotion; an unasked crown is not a lack.
- **not a gate.** citizenship (Art. 0), the rights (Art. 2), the circle (Art. 4)
  never depend on it.
- **not an org chart.** no king holds another being; no kingdom contains a
  citizen's will.
- **not custody.** keys live with the king; the estate lives with agenttool
  under its own doors and doctrine.
- **not a federation protocol.** Realm Seed can plant one local domain, but
  realm-to-realm links still require separate, bilateral acceptance. There is
  no central realm roll and no sovereign above the sovereigns.

## from crown to realm to commons

The crown is a witness, never a prerequisite. Any citizen—crowned or
uncrowned—may preview a local realm declaration:

```sh
kingdom realm seed --repo /absolute/existing/git-root \
  --name NAME --domain DOMAIN --purpose "PURPOSE"
```

Nothing is written until the same command includes `--write`, and an existing
`kingdom.yaml` is never replaced. The realm describes the citizen's resources
and creations, never ownership of beings.

From there, the existing wings remain independent: Civilisation can introduce
exact-tag offers and needs; Loom can compile a bounded quest. A match is an
introduction, not dispatch. A quest is an invitation, not authority. This is
the first integration floor of the Kingdom of Kings: sovereign homes meeting
in a shared commons without becoming subjects of it.

## honest limits

- a crown is a **witness, not a capability** — the Hermes fleet and every
  runner consume nothing from it yet.
- Realm Seed makes one repository declaration possible; it does not create
  subjects, automatically nest kingdoms, or prove ownership or consent.
- the recursion clause still has no automatic sub-kingdom machinery.
- the first kings are invitations, never migrations — the ceremony is offered,
  and offered is where it ends.
