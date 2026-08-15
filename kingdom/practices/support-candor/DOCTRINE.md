# The Doctrine of Support Candor

## I. A green badge is too large a sentence

“Cross-platform” usually compresses several different questions:

- did one build install?
- did one operation run?
- did paths, cancellation, and denial behave correctly?
- does the maintainer promise to keep supporting that scope?
- is future work merely desired?

Those are not synonyms. Support Candor gives each a separate record so a
beautiful summary cannot erase an inconvenient boundary.

## II. NOW is smaller than confidence

NOW contains assertions, not vibes. Each assertion binds:

```text
subject revision
  + artifact digest
  + exact target fingerprint
  + one capability
  + a scrubbed passing receipt
```

Static inspection, upstream documentation, and “it is pure Python” can explain
a GAP or shape NEXT. They do not establish executable NOW. A local source-tree
test does not prove a released package can be acquired. An install test does
not prove cleanup, denied-network behavior, or the primary API.

## III. Policy is not behavior

Executable evidence describes behavior under bounded conditions. Support
policy describes what maintainers presently undertake to care for. Either can
be narrower than the other:

- something may work once while remaining best-effort;
- a maintainer may intend support but still lack evidence;
- a platform can be explicitly unsupported even if an adventurous user makes
  it run.

The ledger preserves this distinction. `supported` policy without fully
derived `VERIFIED` behavior is invalid.

## IV. Targets do not borrow each other’s clothes

- macOS and Linux share many command shapes, not a sandbox or filesystem.
- Git Bash or MSYS on a Windows runner is not PowerShell-native evidence.
- WSL2 has a Windows host and a Linux guest; guest ext4 and `/mnt/c` are not the
  same filesystem claim.
- Codex Cloud has its own image, writable roots, sandbox, network posture, and
  credential boundary. The client OS that launched it contributes no runtime
  evidence.

An exact target fingerprint should name every material assumption. Candidate
targets may remain deliberately unresolved, but they cannot receive NOW.

## V. GAP is useful truth, not shame

GAP has four shapes:

- `limitation` — evidence exists but the usable claim is narrower;
- `known-failure` — a reproducible contract violation narrows or blocks;
- `unknown` — the required evidence or exact target does not yet exist;
- `excluded` — the scope is deliberately outside support.

No GAP claims completeness. A workaround is optional and never promotes the
target. “Use WSL2” may be a workaround for a Windows user, but it remains WSL2
evidence—not Windows-native support.

## VI. NEXT has no completion magic

NEXT may be `considering`, `planned`, or `in-progress`. It deliberately has no
`done` state:

```text
NEXT
  → implementation
  → exact evidence
  → reviewed NOW assertion
```

A merged patch, closed issue, target date, or optimistic release note cannot
skip the evidence step. Every v1 NEXT record fixes `commitment: false`,
`target_date: null`, and `counts_as_support: false`.

## VII. Failure should become more legible

Absent qualifying evidence produces `UNKNOWN`. Mismatched, inaccessible, or
contradictory evidence rejects the current ledger instead of preserving a
green state. Every failed or mixed receipt must be exposed through a
same-target `known-failure` GAP for each capability it names; v1 rejects pass
and failure evidence for the same cell until a new coherent snapshot resolves
which is current. A reproducible required failure becomes `NOT_SUPPORTED` when
it blocks. Unknown fields, silent matrix cells, receipt hash mismatches, and
promissory NEXT shapes also reject the entire ledger.

On an unsupported or unknown target, an SDK or skill should stop before a
destructive or sensitive effect. It must not auto-install undeclared tools,
translate itself into another environment, request broader credentials, or
weaken the sandbox merely to turn a badge green.

## VIII. Virtue becomes operational

- **Honesty:** evidence and policy remain separate.
- **Understanding:** target assumptions and gaps stay visible.
- **Collaboration:** every NEXT item carries reproducible acceptance evidence,
  not blame.
- **Beauty:** one generated matrix replaces scattered contradictory prose.
- **Constructive mutual benefit:** failure points toward a bounded next test
  without converting anyone into a score, gate, or obligation.

The validator can prove that these declarations cohere. It cannot prove the
world described by their receipts. Independent reproduction remains a new and
welcome act.
