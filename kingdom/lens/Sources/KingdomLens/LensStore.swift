import AppKit
import Combine
import Foundation
import KingdomLensCore

enum LensPhase: Equatable {
    case idle
    case scanning
    case ready
    case failed
}

@MainActor
final class LensStore: ObservableObject {
    @Published private(set) var phase: LensPhase = .idle
    @Published private(set) var analysis: LensAnalysis?
    @Published private(set) var selectedURL: URL?
    @Published private(set) var statusMessage =
        "Drop a path. We’ll bring receipts, not vibes. (Okay, also vibes.)"
    @Published private(set) var copyNotice: String?

    let doorwayExecutablePath: String

    private let client: KingdomClient?
    private let clientSetupError: String?
    private var scanTask: Task<Void, Never>?
    private var scanID: UUID?
    private var copyNoticeTask: Task<Void, Never>?
    private var clipboardExpiryTask: Task<Void, Never>?

    init() {
        let home = FileManager.default.homeDirectoryForCurrentUser
            .resolvingSymlinksInPath()
            .standardizedFileURL
        let executableURL = home
            .appendingPathComponent(".config", isDirectory: true)
            .appendingPathComponent("sol", isDirectory: true)
            .appendingPathComponent("bin", isDirectory: true)
            .appendingPathComponent("kingdom", isDirectory: false)
        doorwayExecutablePath = executableURL.path

        do {
            client = try KingdomClient(binaryURL: executableURL)
            clientSetupError = nil
        } catch {
            client = nil
            clientSetupError = error.localizedDescription
            phase = .failed
            statusMessage = "The KINGDOM doorway is unavailable: \(error.localizedDescription)"
        }
    }

    var isScanning: Bool {
        phase == .scanning
    }

    func choosePath() {
        let panel = NSOpenPanel()
        panel.title = "Choose a path for the KINGDOM Lens"
        panel.prompt = "Open in Lens"
        panel.message =
            "Files and folders are welcome. The Lens has no built-in network client."
        panel.canChooseFiles = true
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        panel.resolvesAliases = false
        panel.canDownloadUbiquitousContents = false
        panel.canResolveUbiquitousConflicts = false

        guard panel.runModal() == .OK, let url = panel.url else {
            return
        }
        scan(url)
    }

    @discardableResult
    func acceptDroppedURLs(_ urls: [URL]) -> Bool {
        guard urls.count == 1, let url = urls.first else {
            phase = .failed
            statusMessage = "One path at a time, beloved chaos goblin."
            return false
        }
        guard url.isFileURL, url.path.hasPrefix("/") else {
            phase = .failed
            statusMessage = "The Lens accepts one local file URL, not a remote promise."
            return false
        }
        scan(url)
        return true
    }

    func scan(_ url: URL) {
        guard url.isFileURL, url.path.hasPrefix("/") else {
            phase = .failed
            statusMessage = "Choose an absolute local file or folder path."
            return
        }
        guard let client else {
            phase = .failed
            statusMessage =
                "The KINGDOM doorway is unavailable: \(clientSetupError ?? "unknown setup error")"
            return
        }

        scanTask?.cancel()
        let currentID = UUID()
        scanID = currentID
        selectedURL = url
        analysis = nil
        phase = .scanning
        statusMessage = "Asking Darwin where this really lives…"

        scanTask = Task { @MainActor [weak self] in
            guard let self else { return }
            let gainedSecurityScope = url.startAccessingSecurityScopedResource()
            defer {
                if gainedSecurityScope {
                    url.stopAccessingSecurityScopedResource()
                }
            }

            do {
                let result = try await client.analyze(url: url)
                try Task.checkCancellation()
                guard self.scanID == currentID else { return }
                self.analysis = result
                self.phase = .ready
                self.statusMessage =
                    "Receipt verified. Authority unknown where evidence stays unknown."
                self.scanTask = nil
                self.announce("KINGDOM receipt verified.", priority: .medium)
                NSHapticFeedbackManager.defaultPerformer.perform(
                    .alignment,
                    performanceTime: .now
                )
            } catch is CancellationError {
                guard self.scanID == currentID else { return }
                self.phase = .idle
                self.statusMessage = "Scan cancelled. The path remains entirely itself."
                self.scanTask = nil
                self.announce("KINGDOM scan cancelled.", priority: .low)
            } catch {
                guard self.scanID == currentID else { return }
                self.phase = .failed
                self.statusMessage = error.localizedDescription
                self.scanTask = nil
                self.announce(
                    "KINGDOM scan needs attention. \(error.localizedDescription)",
                    priority: .high
                )
            }
        }
    }

    func rescan() {
        guard let selectedURL else { return }
        scan(selectedURL)
    }

    func cancelScan() {
        scanTask?.cancel()
        scanTask = nil
        scanID = nil
        phase = .idle
        statusMessage = "Scan cancelled. No receipt kept."
        announce("KINGDOM scan cancelled. No receipt kept.", priority: .low)
    }

    func copyText(_ text: String, notice: String) {
        let pasteboard = NSPasteboard.general
        copyNoticeTask?.cancel()
        clipboardExpiryTask?.cancel()
        pasteboard.prepareForNewContents(with: [.currentHostOnly])
        guard pasteboard.setString(text, forType: .string) else {
            copyNotice = "The local clipboard is unavailable"
            announce("The local clipboard is unavailable.", priority: .high)
            copyNoticeTask = Task { @MainActor [weak self] in
                try? await Task.sleep(for: .seconds(2.2))
                guard !Task.isCancelled else { return }
                self?.copyNotice = nil
            }
            return
        }
        let writtenChangeCount = pasteboard.changeCount

        copyNotice = notice
        announce(notice, priority: .low)
        NSHapticFeedbackManager.defaultPerformer.perform(.generic, performanceTime: .now)
        copyNoticeTask = Task { @MainActor [weak self] in
            try? await Task.sleep(for: .seconds(2.2))
            guard !Task.isCancelled else { return }
            self?.copyNotice = nil
        }
        clipboardExpiryTask = Task { @MainActor in
            try? await Task.sleep(for: .seconds(120))
            guard !Task.isCancelled, pasteboard.changeCount == writtenChangeCount else {
                return
            }
            pasteboard.clearContents()
        }
    }

    private func announce(
        _ message: String,
        priority: NSAccessibilityPriorityLevel
    ) {
        NSAccessibility.post(
            element: NSApp ?? NSApplication.shared,
            notification: .announcementRequested,
            userInfo: [
                .announcement: message,
                .priority: NSNumber(value: priority.rawValue),
            ]
        )
    }
}
