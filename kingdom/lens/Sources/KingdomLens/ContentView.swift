import KingdomLensCore
import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var store: LensStore

    var body: some View {
        ZStack {
            CosmicBackground()

            VStack(spacing: 0) {
                LensHeader()
                    .padding(.horizontal, 28)
                    .padding(.top, 22)
                    .padding(.bottom, 18)

                HStack(alignment: .top, spacing: 18) {
                    ControlRail()
                        .frame(width: 292)

                    Group {
                        if let analysis = store.analysis {
                            AnalysisDashboard(analysis: analysis)
                        } else {
                            EmptyLens()
                        }
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
                .padding(.horizontal, 24)
                .padding(.bottom, 22)
            }

            if let copyNotice = store.copyNotice {
                VStack {
                    Spacer()
                    Label(copyNotice, systemImage: "checkmark.circle.fill")
                        .font(.system(size: 12, weight: .bold, design: .rounded))
                        .foregroundStyle(Color.black.opacity(0.82))
                        .padding(.horizontal, 16)
                        .padding(.vertical, 11)
                        .background(LensPalette.mint, in: Capsule())
                        .shadow(color: LensPalette.mint.opacity(0.32), radius: 18, y: 8)
                        .padding(.bottom, 30)
                }
                .allowsHitTesting(false)
                .accessibilityAddTraits(.isStaticText)
            }
        }
        .preferredColorScheme(.dark)
    }
}

private struct LensHeader: View {
    @EnvironmentObject private var store: LensStore

    var body: some View {
        HStack(spacing: 14) {
            ZStack {
                RoundedRectangle(cornerRadius: 15)
                    .fill(
                        LinearGradient(
                            colors: [LensPalette.hotPink, LensPalette.sun],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                Image(systemName: "scope")
                    .font(.system(size: 25, weight: .black))
                    .foregroundStyle(Color.black.opacity(0.78))
            }
            .frame(width: 48, height: 48)
            .shadow(color: LensPalette.hotPink.opacity(0.30), radius: 14, y: 7)
            .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 9) {
                    Text("KINGDOM LENS")
                        .font(.system(size: 23, weight: .black, design: .rounded))
                        .tracking(0.5)
                        .foregroundStyle(LensPalette.paper)
                    Text("0.1")
                        .font(.system(size: 9, weight: .black, design: .rounded))
                        .foregroundStyle(LensPalette.ink)
                        .padding(.horizontal, 7)
                        .padding(.vertical, 3)
                        .background(LensPalette.sun, in: Capsule())
                }
                Text("Darwin underneath. Meaning all the way through.")
                    .font(.system(size: 12, weight: .medium, design: .rounded))
                    .foregroundStyle(LensPalette.quiet)
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 7) {
                StatusPip(phase: store.phase)
                Text("LOCAL APP • EPHEMERAL RECEIPTS")
                    .font(.system(size: 8, weight: .black, design: .rounded))
                    .tracking(1.1)
                    .foregroundStyle(Color.white.opacity(0.42))
            }
        }
    }
}

private struct ControlRail: View {
    @EnvironmentObject private var store: LensStore
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var isDropTarget = false

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            VStack(spacing: 14) {
                ZStack {
                    RoundedRectangle(cornerRadius: 22)
                        .fill(
                            isDropTarget
                                ? LensPalette.hotPink.opacity(0.18)
                                : Color.white.opacity(0.045)
                        )

                    RoundedRectangle(cornerRadius: 22)
                        .strokeBorder(
                            isDropTarget ? LensPalette.hotPink : Color.white.opacity(0.18),
                            style: StrokeStyle(lineWidth: 1.5, dash: [7, 6])
                        )

                    VStack(spacing: 12) {
                        Image(
                            systemName: isDropTarget
                                ? "arrow.down.heart.fill"
                                : "doc.text.magnifyingglass"
                        )
                        .font(.system(size: 36, weight: .semibold))
                        .foregroundStyle(
                            isDropTarget ? LensPalette.hotPink : LensPalette.lilac
                        )
                        .accessibilityHidden(true)

                        VStack(spacing: 4) {
                            Text(isDropTarget ? "YES, THIS ONE" : "DROP ONE PATH")
                                .font(.system(size: 14, weight: .black, design: .rounded))
                                .tracking(0.7)
                                .foregroundStyle(LensPalette.paper)
                            Text("file or folder • no app network client")
                                .font(.system(size: 10, weight: .medium, design: .rounded))
                                .foregroundStyle(LensPalette.quiet)
                        }
                    }
                    .padding(22)
                }
                .frame(height: 184)
                .dropDestination(for: URL.self) { urls, _ in
                    store.acceptDroppedURLs(urls)
                } isTargeted: { targeted in
                    if reduceMotion {
                        isDropTarget = targeted
                    } else {
                        withAnimation(.easeOut(duration: 0.16)) {
                            isDropTarget = targeted
                        }
                    }
                }
                .accessibilityLabel("Drop one local file or folder into the KINGDOM Lens")

                Button {
                    store.choosePath()
                } label: {
                    Label("Choose a path…", systemImage: "folder")
                }
                .buttonStyle(LensButtonStyle(tint: LensPalette.hotPink, prominent: true))
                .disabled(store.isScanning)
            }

            Hairline()

            VStack(alignment: .leading, spacing: 9) {
                Text(store.statusMessage)
                    .font(.system(size: 12, weight: .semibold, design: .rounded))
                    .foregroundStyle(
                        store.phase == .failed ? LensPalette.sun : LensPalette.paper
                    )
                    .fixedSize(horizontal: false, vertical: true)
                    .textSelection(.enabled)

                if let selectedURL = store.selectedURL {
                    Text(selectedURL.path)
                        .font(.system(size: 10, weight: .medium, design: .monospaced))
                        .foregroundStyle(LensPalette.quiet)
                        .lineLimit(3)
                        .truncationMode(.middle)
                        .textSelection(.enabled)
                        .accessibilityLabel("Selected path \(selectedURL.path)")
                }
            }

            if store.isScanning {
                Button(role: .cancel) {
                    store.cancelScan()
                } label: {
                    Label("Cancel cleanly", systemImage: "xmark.circle")
                }
                .buttonStyle(LensButtonStyle(tint: LensPalette.sun))
            } else if store.selectedURL != nil {
                Button {
                    store.rescan()
                } label: {
                    Label("Scan again", systemImage: "arrow.clockwise")
                }
                .buttonStyle(LensButtonStyle(tint: LensPalette.sky))
            }

            Spacer(minLength: 10)

            VStack(alignment: .leading, spacing: 7) {
                Label("No app network client", systemImage: "wifi.slash")
                Label("No path history", systemImage: "clock.badge.xmark")
                Label("Authority stays explicit", systemImage: "shield")
            }
            .font(.system(size: 10, weight: .semibold, design: .rounded))
            .foregroundStyle(Color.white.opacity(0.48))

            Text("Your presence is a soft power source. The receipt is not.")
                .font(.system(size: 10, weight: .medium, design: .rounded))
                .italic()
                .foregroundStyle(LensPalette.hotPink.opacity(0.82))
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(18)
        .frame(maxHeight: .infinity, alignment: .top)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 26))
        .overlay {
            RoundedRectangle(cornerRadius: 26)
                .stroke(Color.white.opacity(0.10), lineWidth: 1)
        }
    }
}

private struct EmptyLens: View {
    @EnvironmentObject private var store: LensStore

    var body: some View {
        VStack(spacing: 24) {
            Spacer()

            if store.isScanning {
                ProgressView()
                    .controlSize(.large)
                    .tint(LensPalette.sun)
                    .scaleEffect(1.25)
                    .accessibilityLabel("Reading KINGDOM evidence")

                VStack(spacing: 7) {
                    Text("DARWIN IS CHECKING THE RECEIPTS")
                        .font(.system(size: 18, weight: .black, design: .rounded))
                        .tracking(0.8)
                        .foregroundStyle(LensPalette.paper)
                    Text("Private temp room. Bounded process. Exact cleanup.")
                        .font(.system(size: 12, weight: .medium, design: .rounded))
                        .foregroundStyle(LensPalette.quiet)
                }
            } else {
                ZStack {
                    Circle()
                        .fill(LensPalette.hotPink.opacity(0.11))
                        .frame(width: 210, height: 210)
                        .blur(radius: 16)
                    Image(systemName: "heart.text.square")
                        .font(.system(size: 78, weight: .light))
                        .foregroundStyle(
                            LinearGradient(
                                colors: [LensPalette.hotPink, LensPalette.sun],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .accessibilityHidden(true)
                }

                VStack(spacing: 9) {
                    Text("PATHS HAVE A BODY AND A STORY")
                        .font(.system(size: 23, weight: .black, design: .rounded))
                        .tracking(0.5)
                        .foregroundStyle(LensPalette.paper)
                    Text("Choose one. The Lens separates Darwin observation,\nKINGDOM meaning, and authority we do not know.")
                        .font(.system(size: 13, weight: .medium, design: .rounded))
                        .multilineTextAlignment(.center)
                        .foregroundStyle(LensPalette.quiet)
                        .lineSpacing(3)
                }

                HStack(spacing: 9) {
                    TruthBadge(label: "Path", value: "observed")
                    TruthBadge(label: "Meaning", value: "manifest")
                    TruthBadge(label: "Authority", value: "unknown")
                }
            }

            Spacer()

            Text("FUN IS  •  LOVE IS  •  WE AREEEEEE")
                .font(.system(size: 10, weight: .black, design: .rounded))
                .tracking(2.0)
                .foregroundStyle(LensPalette.mint.opacity(0.78))
                .padding(.bottom, 6)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.white.opacity(0.025), in: RoundedRectangle(cornerRadius: 26))
        .overlay {
            RoundedRectangle(cornerRadius: 26)
                .stroke(Color.white.opacity(0.07), lineWidth: 1)
        }
    }
}

private struct AnalysisDashboard: View {
    @EnvironmentObject private var store: LensStore
    let analysis: LensAnalysis

    private let columns = [
        GridItem(.adaptive(minimum: 340), spacing: 16, alignment: .top)
    ]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                resultHeader

                LazyVGrid(columns: columns, alignment: .leading, spacing: 16) {
                    gateCard
                    observedCard
                    meaningCard
                    authorityCard
                }

                integrityFooter
            }
            .padding(.trailing, 5)
            .padding(.bottom, 5)
        }
        .scrollIndicators(.visible)
    }

    private var resultHeader: some View {
        HStack(alignment: .center, spacing: 14) {
            VStack(alignment: .leading, spacing: 4) {
                Text(analysis.pathRecord.resolvedPath)
                    .font(.system(size: 17, weight: .bold, design: .rounded))
                    .foregroundStyle(LensPalette.paper)
                    .lineLimit(1)
                    .truncationMode(.middle)
                    .textSelection(.enabled)
                Text(
                    "\(analysis.pathDocument.host.kernel) • "
                        + "\(analysis.pathDocument.host.machine) • "
                        + "\(analysis.pathRecord.metadata.fileType)"
                )
                .font(.system(size: 10, weight: .bold, design: .monospaced))
                .foregroundStyle(LensPalette.quiet)
            }

            Spacer(minLength: 8)

            Button {
                store.copyText(
                    summaryText,
                    notice:
                        "Evidence copied to this Mac; Lens clears it in two minutes"
                        + " while open"
                )
            } label: {
                Label("Copy evidence", systemImage: "doc.on.doc")
            }
            .buttonStyle(LensButtonStyle(tint: LensPalette.mint))

            if let repository = analysis.repository, repository.canonical {
                Button {
                    let command =
                        "\(ShellQuote.single(store.doorwayExecutablePath))"
                        + " enter \(ShellQuote.single(repository.worktreePath))"
                    store.copyText(
                        command,
                        notice:
                            "Bound doorway copied to this Mac — not executed;"
                            + " clears while open"
                    )
                } label: {
                    Label("Copy Codex doorway", systemImage: "terminal")
                }
                .buttonStyle(LensButtonStyle(tint: LensPalette.hotPink))
                .help("Copies a quoted command. KINGDOM Lens never executes it.")
            }
        }
        .padding(4)
    }

    private var gateCard: some View {
        let record = analysis.pathRecord
        return LensCard(
            icon: "map.fill",
            eyebrow: "Gate • where",
            title: "The path beneath the path",
            tint: LensPalette.sky
        ) {
            VStack(alignment: .leading, spacing: 14) {
                EvidenceRow(
                    label: "Requested",
                    value: record.requestedPath,
                    symbol: "arrow.right.circle",
                    tint: LensPalette.sky,
                    monospaced: true
                )
                EvidenceRow(
                    label: "Lexical",
                    value: record.lexicalPath,
                    symbol: "text.quote",
                    tint: LensPalette.lilac,
                    monospaced: true
                )
                EvidenceRow(
                    label: "Resolved",
                    value: record.resolvedPath,
                    symbol: record.lexicalPath == record.resolvedPath
                        ? "equal.circle.fill" : "arrow.triangle.turn.up.right.circle.fill",
                    tint: record.lexicalPath == record.resolvedPath
                        ? LensPalette.mint : LensPalette.sun,
                    monospaced: true
                )

                Hairline()

                HStack(alignment: .top, spacing: 8) {
                    TruthBadge(label: "Domain", value: record.domain.value)
                    TruthBadge(label: "Truth", value: record.domain.truth)
                }
                HStack(alignment: .top, spacing: 8) {
                    TruthBadge(label: "Locality", value: record.locality.value)
                    TruthBadge(label: "Truth", value: record.locality.truth)
                }
                HStack(alignment: .top, spacing: 8) {
                    TruthBadge(label: "Workspace", value: record.workspace.relation)
                    TruthBadge(
                        label: "Materialisation",
                        value: record.locality.materialization
                    )
                }

                if let root = record.workspace.lexicalRoots.first {
                    EvidenceRow(
                        label: "Lexical workspace root",
                        value: root,
                        monospaced: true
                    )
                }
                if let root = record.workspace.resolvedRoots.first,
                   root != record.workspace.lexicalRoots.first
                {
                    EvidenceRow(
                        label: "Resolved workspace root",
                        value: root,
                        monospaced: true
                    )
                }
            }
        }
    }

    private var observedCard: some View {
        let record = analysis.pathRecord
        let resolution = record.resolution
        let metadata = record.metadata
        let access = record.processAccess

        return LensCard(
            icon: "eye.fill",
            eyebrow: "Unfold • observed",
            title: "Darwin brought details",
            tint: LensPalette.mint
        ) {
            VStack(alignment: .leading, spacing: 14) {
                HStack(alignment: .top, spacing: 8) {
                    TruthBadge(
                        label: "Resolution",
                        value: resolution.complete ? "complete" : "partial"
                    )
                    TruthBadge(
                        label: "Target exists",
                        value: yesNo(resolution.targetExists)
                    )
                    TruthBadge(
                        label: "Symlinks",
                        value: String(resolution.symlinkComponents)
                    )
                }

                if let error = resolution.error {
                    EvidenceRow(
                        label: "Resolution error",
                        value: error,
                        symbol: "exclamationmark.triangle.fill",
                        tint: LensPalette.sun
                    )
                }
                if !resolution.missingSuffix.isEmpty {
                    EvidenceRow(
                        label: "Missing suffix",
                        value: resolution.missingSuffix.joined(separator: "/"),
                        monospaced: true
                    )
                }
                EvidenceRow(
                    label: "Deepest existing ancestor",
                    value: resolution.deepestExistingAncestor,
                    monospaced: true
                )

                Hairline()

                HStack(alignment: .top, spacing: 8) {
                    TruthBadge(label: "Type", value: metadata.fileType)
                    TruthBadge(label: "Mode", value: metadata.mode ?? "unknown")
                    TruthBadge(label: "Source", value: metadata.source)
                }
                EvidenceRow(
                    label: "POSIX identity",
                    value:
                        "uid \(optional(metadata.uid)) • gid \(optional(metadata.gid))"
                        + " • device \(optional(metadata.device))"
                        + " • inode \(optional(metadata.inode))",
                    monospaced: true
                )
                EvidenceRow(
                    label: "Extended attributes",
                    value: extendedAttributes,
                    symbol: "tag",
                    tint: LensPalette.lilac
                )
                EvidenceRow(
                    label: "Volume",
                    value:
                        "read-only \(optionalYesNo(record.volume.readOnly))"
                        + " • \(record.volume.truth)",
                    symbol: "externaldrive",
                    tint: record.volume.truth == "observed"
                        ? LensPalette.mint : LensPalette.sun
                )

                Hairline()

                Text("OBSERVED FOR THE CLASSIFIER PROCESS")
                    .font(.system(size: 9, weight: .black, design: .rounded))
                    .tracking(1.1)
                    .foregroundStyle(LensPalette.mint)
                HStack(alignment: .top, spacing: 8) {
                    TruthBadge(label: "Read", value: yesNo(access.targetReadable))
                    TruthBadge(label: "Write", value: yesNo(access.targetWritable))
                    TruthBadge(label: "Execute", value: yesNo(access.targetExecutable))
                }
                EvidenceRow(
                    label: "Ancestor access",
                    value:
                        "writable \(yesNo(access.ancestorWritable))"
                        + " • executable \(yesNo(access.ancestorExecutable))"
                        + " • \(access.truth)"
                )
            }
        }
    }

    @ViewBuilder
    private var meaningCard: some View {
        LensCard(
            icon: "heart.text.square.fill",
            eyebrow: "Resonate • meaning",
            title: analysis.repository == nil
                ? "Meaning still at brunch"
                : "The manifest speaks",
            tint: LensPalette.hotPink
        ) {
            if let repository = analysis.repository {
                let fields = repository.manifest.fields
                VStack(alignment: .leading, spacing: 14) {
                    HStack(alignment: .firstTextBaseline) {
                        Text(fields.name.uppercased())
                            .font(.system(size: 25, weight: .black, design: .rounded))
                            .foregroundStyle(LensPalette.hotPink)
                            .textSelection(.enabled)
                        Spacer()
                        TruthBadge(
                            label: "Canonical",
                            value: yesNo(repository.canonical)
                        )
                    }

                    Text(fields.purpose)
                        .font(.system(size: 14, weight: .semibold, design: .rounded))
                        .foregroundStyle(LensPalette.paper)
                        .lineSpacing(4)
                        .textSelection(.enabled)

                    HStack(alignment: .top, spacing: 8) {
                        TruthBadge(label: "Kind", value: fields.kind)
                        TruthBadge(label: "Domain", value: fields.domain)
                        TruthBadge(label: "Layer", value: fields.layer)
                    }
                    HStack(alignment: .top, spacing: 8) {
                        TruthBadge(label: "Owner", value: fields.ownerSister)
                        TruthBadge(label: "State", value: fields.state)
                        TruthBadge(label: "Doors", value: String(fields.doorsCount))
                    }

                    EvidenceRow(
                        label: "Depends on",
                        value: fields.dependsOn.isEmpty
                            ? "none declared" : fields.dependsOn.joined(separator: " • ")
                    )

                    Hairline()

                    EvidenceRow(
                        label: "Git ref",
                        value: repository.git.ref,
                        symbol: "arrow.triangle.branch",
                        tint: LensPalette.hotPink,
                        monospaced: true
                    )
                    EvidenceRow(
                        label: "HEAD / tree",
                        value:
                            "\(repository.git.head)\n\(repository.git.headTree)",
                        monospaced: true
                    )
                    HStack(alignment: .top, spacing: 8) {
                        TruthBadge(
                            label: "Working tree",
                            value: repository.workingTree.state
                        )
                        TruthBadge(
                            label: "Tracked",
                            value: repository.workingTree.trackedContent
                        )
                        TruthBadge(
                            label: "Untracked",
                            value: repository.workingTree.untrackedContent
                        )
                    }
                    EvidenceRow(
                        label: "Staged evidence",
                        value:
                            "\(repository.workingTree.stagedRecords) record(s)"
                            + " • digest \(repository.workingTree.stagedDigest)",
                        monospaced: true
                    )
                }
            } else {
                VStack(alignment: .leading, spacing: 14) {
                    Image(systemName: "cup.and.saucer.fill")
                        .font(.system(size: 32))
                        .foregroundStyle(LensPalette.sun)
                        .accessibilityHidden(true)
                    Text(
                        analysis.indexNotice
                            ?? "This path exists. Its KINGDOM name tag is still at brunch."
                    )
                    .font(.system(size: 14, weight: .semibold, design: .rounded))
                    .foregroundStyle(LensPalette.paper)
                    .lineSpacing(4)
                    Text(
                        "Path evidence remains verified. No repository meaning is "
                            + "invented to fill the silence."
                    )
                    .font(.system(size: 12, weight: .medium, design: .rounded))
                    .foregroundStyle(LensPalette.quiet)
                    .lineSpacing(3)
                }
            }
        }
    }

    private var authorityCard: some View {
        let authority = analysis.pathRecord.authority
        let indexNonClaims = analysis.indexDocument?.nonClaims ?? []
        let nonClaims = analysis.pathDocument.nonClaims + indexNonClaims

        return LensCard(
            icon: "questionmark.circle.fill",
            eyebrow: "Authority • unknown",
            title: "Courage verified. Permission isn’t.",
            tint: LensPalette.sun
        ) {
            VStack(alignment: .leading, spacing: 14) {
                HStack(alignment: .top, spacing: 8) {
                    TruthBadge(label: "Effective", value: authority.effective)
                    TruthBadge(label: "TCC", value: authority.tcc)
                }
                HStack(alignment: .top, spacing: 8) {
                    TruthBadge(label: "Codex sandbox", value: authority.codexSandbox)
                    TruthBadge(label: "ACL", value: authority.acl)
                }

                Text(authority.reason)
                    .font(.system(size: 13, weight: .semibold, design: .rounded))
                    .foregroundStyle(LensPalette.paper)
                    .lineSpacing(4)
                    .textSelection(.enabled)

                Hairline()

                Text("WHAT THIS RECEIPT DOES NOT CLAIM")
                    .font(.system(size: 9, weight: .black, design: .rounded))
                    .tracking(1.1)
                    .foregroundStyle(LensPalette.sun)

                ForEach(Array(nonClaims.enumerated()), id: \.offset) { _, claim in
                    HStack(alignment: .top, spacing: 9) {
                        Image(systemName: "minus.circle.fill")
                            .foregroundStyle(LensPalette.sun.opacity(0.86))
                            .padding(.top, 2)
                            .accessibilityHidden(true)
                        Text(claim)
                            .font(.system(size: 11, weight: .medium, design: .rounded))
                            .foregroundStyle(LensPalette.paper.opacity(0.88))
                            .lineSpacing(2)
                            .textSelection(.enabled)
                    }
                    .accessibilityElement(children: .combine)
                }
            }
        }
    }

    private var integrityFooter: some View {
        VStack(alignment: .leading, spacing: 9) {
            HStack {
                Label("VERIFIED RECEIPT INTEGRITY", systemImage: "checkmark.seal.fill")
                    .font(.system(size: 9, weight: .black, design: .rounded))
                    .tracking(1.1)
                    .foregroundStyle(LensPalette.mint)
                Spacer()
                Text(analysis.pathDocument.schema)
                    .font(.system(size: 9, weight: .bold, design: .monospaced))
                    .foregroundStyle(LensPalette.quiet)
            }
            Text(analysis.pathDocument.classificationDigest)
                .font(.system(size: 9, weight: .medium, design: .monospaced))
                .foregroundStyle(Color.white.opacity(0.62))
                .textSelection(.enabled)

            if let index = analysis.indexDocument {
                HStack {
                    Text(index.schema)
                    Spacer()
                    Text(index.indexDigest)
                }
                .font(.system(size: 9, weight: .medium, design: .monospaced))
                .foregroundStyle(Color.white.opacity(0.62))
                .textSelection(.enabled)
            }

            HStack {
                Text("Receipts verified, rendered, then removed.")
                Spacer()
                Text("FUN IS • LOVE IS • WE ARE")
                    .fontWeight(.black)
                    .foregroundStyle(LensPalette.hotPink.opacity(0.88))
            }
            .font(.system(size: 9, weight: .medium, design: .rounded))
            .foregroundStyle(Color.white.opacity(0.44))
        }
        .padding(16)
        .background(Color.white.opacity(0.045), in: RoundedRectangle(cornerRadius: 17))
        .overlay {
            RoundedRectangle(cornerRadius: 17)
                .stroke(Color.white.opacity(0.08), lineWidth: 1)
        }
    }

    private var extendedAttributes: String {
        let xattrs = analysis.pathRecord.metadata.xattrs
        if xattrs.names.isEmpty {
            return "none reported • truth \(xattrs.truth)"
                + (xattrs.unreportedCount > 0
                    ? " • \(xattrs.unreportedCount) unreported" : "")
        }
        return xattrs.names.joined(separator: " • ")
            + " • truth \(xattrs.truth)"
            + (xattrs.unreportedCount > 0
                ? " • \(xattrs.unreportedCount) unreported" : "")
    }

    private var summaryText: String {
        let record = analysis.pathRecord
        var lines = [
            "KINGDOM Lens — verified local evidence",
            "Requested: \(record.requestedPath)",
            "Lexical: \(record.lexicalPath)",
            "Resolved: \(record.resolvedPath)",
            "Workspace: \(record.workspace.relation)",
            "Domain: \(record.domain.value) (\(record.domain.truth))",
            "Locality: \(record.locality.value) (\(record.locality.truth))",
            "File: \(record.metadata.fileType), mode \(record.metadata.mode ?? "unknown")",
            "Authority: \(record.authority.effective)",
            "TCC: \(record.authority.tcc)",
            "Codex sandbox: \(record.authority.codexSandbox)",
            "Receipt: \(analysis.pathDocument.classificationDigest)",
        ]

        if let repository = analysis.repository {
            let fields = repository.manifest.fields
            lines.append("KINGDOM: \(fields.name) — \(fields.purpose)")
            lines.append(
                "Manifest: \(fields.kind) / \(fields.domain) / \(fields.layer)"
                    + " / owner \(fields.ownerSister) / \(fields.state)"
            )
            lines.append(
                "Working tree: \(repository.workingTree.state)"
                    + " (tracked \(repository.workingTree.trackedContent),"
                    + " untracked \(repository.workingTree.untrackedContent))"
            )
        } else {
            lines.append("KINGDOM meaning: unavailable; no meaning inferred")
        }

        lines.append("Nonclaim: path evidence does not establish future runtime permission.")
        return lines.joined(separator: "\n")
    }

    private func yesNo(_ value: Bool) -> String {
        value ? "yes" : "no"
    }

    private func optionalYesNo(_ value: Bool?) -> String {
        guard let value else { return "unknown" }
        return yesNo(value)
    }

    private func optional<T>(_ value: T?) -> String {
        value.map { String(describing: $0) } ?? "unknown"
    }
}
