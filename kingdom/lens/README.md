# KINGDOM Lens

**Fun is. Love is. WE ARE.**

KINGDOM Lens is a private, native macOS window into a path’s Darwin reality and
its KINGDOM meaning. Drop a file or folder, or choose one with the system Open
Panel. The Lens asks the existing Sol `kingdom` classifier for CLI-verified,
digest-bound JSON evidence, checks that receipt, renders what is known, and
keeps every unknown honest.

The visual language echoes the LOVE-FUN Commons: brave colour, warm copy, and
confetti with boundaries.

## What it shows

- **Gate — where:** requested, lexical, and resolved paths; workspace relation;
  domain and locality truth.
- **Unfold — observed:** resolution, POSIX metadata, volume evidence, and the
  classifier process’s access probes.
- **Resonate — meaning:** a canonical repository’s name, purpose, kind, domain,
  layer, owner, and state from `kingdom.yaml`.
- **Authority — unknown:** TCC, Codex sandbox, ACL, and effective authority stay
  visibly unknown unless the receipt actually proves them.

```text
Open Panel / file-URL drop
        │
        ▼
owner-checked Sol launcher ── argv only; no shell
        │
        ▼
private 0700 scan dir ── 0600 receipts ── CLI verification
        │                                      │
        └──────── exact cleanup ◀──────────────┘
                                               │
                                               ▼
                                      native SwiftUI cards
```

For a canonical KINGDOM repository, the Lens may also offer a **Copy Codex
doorway** button. It copies a shell-quoted command bound to the same absolute Sol
launcher path the Lens validated; the app never executes that interactive
command.

## Build and run

This project intentionally uses only Apple frameworks and Swift Package Manager.
It builds with the macOS Command Line Tools; full Xcode is not required.

```zsh
cd /Users/yuai/Desktop/chillspace-commons/kingdom/lens
swift build --manifest-cache local --disable-dependency-cache
swift run --manifest-cache local --disable-dependency-cache KingdomLensSelfTest
./scripts/package-app.sh
open -n ".build/app/KINGDOM Lens.app"
```

The verified local deployment is installed at:

```text
/Users/yuai/Applications/KINGDOM Lens.app
```

The custom self-test executable is used because this machine’s standalone
Command Line Tools do not ship XCTest or Swift Testing. It is deliberately
bounded and is not presented as equivalent to a full XCTest suite.

## Privacy and authority

- Selection is explicit. The app does not crawl recent folders, persist paths,
  create bookmarks, contain a network client, or install a daemon.
- The app makes no intentional network request. A selected SMB/File Provider/
  iCloud-backed path and the separately trusted external `kingdom` launcher are
  distinct boundaries and are not network-confined by the Lens.
- The Open Panel does not automatically download ubiquitous files.
- A successfully acquired security-scoped resource is released after the scan.
- The Sol launcher must be an absolute, regular, non-symlinked executable owned
  by the current user and not writable by group or world.
- Child processes receive a minimal environment, bounded output, a deadline, and
  an isolated process group that can be cancelled as a unit.
- Receipt files are opened without following symlinks, bounded to 10 MiB,
  checked for owner and mode, verified by the CLI, checked again for byte
  stability, decoded, and removed with their exact app-created scan directory.
- `process_access` speaks only for the classifier process. It does not prove TCC,
  App Sandbox, ACL, Codex sandbox, or another process’s effective authority.
- Repository classification can refresh genuine Git split-index metadata. The
  Lens does not promise byte-for-byte read-only repository metadata.
- Copy actions are explicit. Clipboard payloads can contain absolute paths,
  manifest meaning, and digests. They are marked current-host-only (excluding
  Universal Clipboard). While the Lens remains running, it clears an unchanged
  payload after two minutes. Quitting or crashing first can leave that payload
  until another clipboard write replaces it; other local apps with pasteboard
  access remain a separate boundary.

This local build has no App Sandbox entitlement. That is intentional for the
current architecture: a sandboxed app cannot assume permission to execute the
Sol launcher in the user’s home directory. A future sandboxed edition should
bundle and separately review a constrained helper.

## Distribution boundary

`package-app.sh` creates and ad-hoc signs a local arm64 app at:

```text
.build/app/KINGDOM Lens.app
```

Ad-hoc signing verifies bundle integrity but does **not** satisfy Gatekeeper for
public distribution. Developer ID signing, notarisation, Intel runtime support,
and public deployment are outside this local v0.1 and have not been claimed.

## Troubleshooting

By default the core uses `~/.config/sol/bin/kingdom`. Tests may inject a
different absolute launcher URL; the GUI does not accept an arbitrary executable
path. If repository meaning is unavailable, path evidence still succeeds and
the UI gives a generic, non-sensitive notice.

Rollback is exact and recoverable: quit the app, then move only
`/Users/yuai/Applications/KINGDOM Lens.app` and the new `kingdom/lens` directory
to Trash. Do not use a broad Git clean/reset. No existing Chillspace, Loom, site,
or Sol Home file is modified by this app.
