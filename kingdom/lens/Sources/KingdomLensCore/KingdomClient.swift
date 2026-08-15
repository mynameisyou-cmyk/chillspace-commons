import Darwin
import Foundation

public struct KingdomClient: Sendable {
    private static let receiptLimit = 10_000_000
    private static let genericIndexNotice =
        "Repository evidence is unavailable for this directory; no clean or trusted state is implied."

    private let executable: ValidatedExecutable
    private let homeURL: URL
    private let timeout: TimeInterval
    private let outputLimit: Int
    private let temporaryBaseURL: URL?

    public init(binaryURL: URL? = nil) throws {
        let home = FileManager.default.homeDirectoryForCurrentUser
            .resolvingSymlinksInPath()
            .standardizedFileURL
        let selectedBinary = binaryURL
            ?? home
                .appendingPathComponent(".config", isDirectory: true)
                .appendingPathComponent("sol", isDirectory: true)
                .appendingPathComponent("bin", isDirectory: true)
                .appendingPathComponent("kingdom", isDirectory: false)
        try self.init(
            binaryURL: selectedBinary,
            homeURL: home,
            timeout: 30,
            outputLimit: 256_000,
            temporaryBaseURL: nil
        )
    }

    @_spi(Testing)
    public init(
        binaryURL: URL,
        timeout: TimeInterval,
        outputLimit: Int,
        temporaryRoot: URL? = nil
    ) throws {
        let home = FileManager.default.homeDirectoryForCurrentUser
            .resolvingSymlinksInPath()
            .standardizedFileURL
        try self.init(
            binaryURL: binaryURL,
            homeURL: home,
            timeout: timeout,
            outputLimit: outputLimit,
            temporaryBaseURL: temporaryRoot
        )
    }

    private init(
        binaryURL: URL,
        homeURL: URL,
        timeout: TimeInterval,
        outputLimit: Int,
        temporaryBaseURL: URL?
    ) throws {
        guard timeout > 0, timeout <= 300 else {
            throw LensFailure.invalidInput("the process timeout is outside its safe bound")
        }
        guard outputLimit > 0, outputLimit <= Self.receiptLimit else {
            throw LensFailure.invalidInput("the process output limit is outside its safe bound")
        }
        executable = try ValidatedExecutable(url: binaryURL)
        self.homeURL = homeURL
        self.timeout = timeout
        self.outputLimit = outputLimit
        self.temporaryBaseURL = temporaryBaseURL
    }

    public func analyze(url: URL) async throws -> LensAnalysis {
        let worker = Task.detached(priority: .userInitiated) {
            try analyzeSynchronously(url: url)
        }
        return try await withTaskCancellationHandler {
            try await worker.value
        } onCancel: {
            worker.cancel()
        }
    }

    private func analyzeSynchronously(url: URL) throws -> LensAnalysis {
        try Task.checkCancellation()
        let selection = try SelectedPath(url: url)
        let scan = try ScanDirectory.make(baseURL: temporaryBaseURL)
        defer { scan.remove() }
        try scan.validate()

        let runner = BoundedProcessRunner(
            executable: executable,
            timeout: timeout,
            outputLimit: outputLimit
        )
        let environment = minimalEnvironment(scanDirectory: scan.url)
        let pathOutput = scan.url.appendingPathComponent(
            "kingdom.path.json",
            isDirectory: false
        )

        try runChecked(
            runner,
            arguments: [
                "path",
                "--path", selection.lexicalPath,
                "--workspace-root", selection.canonicalWorkspace.path,
                "--output", pathOutput.path,
            ],
            environment: environment,
            scan: scan,
            stage: "KINGDOM path analysis"
        )
        let pathBefore = try SecureReceipt.read(
            at: pathOutput,
            maximumBytes: Self.receiptLimit,
            label: "path receipt"
        )
        try runChecked(
            runner,
            arguments: ["path", "--verify", pathOutput.path],
            environment: environment,
            scan: scan,
            stage: "KINGDOM path verification"
        )
        try scan.validate()
        let pathAfter = try SecureReceipt.read(
            at: pathOutput,
            maximumBytes: Self.receiptLimit,
            label: "path receipt"
        )
        try pathAfter.requireUnchanged(from: pathBefore, label: "the path receipt")

        let pathDocument: KingdomPathDocument
        do {
            pathDocument = try JSONDecoder().decode(
                KingdomPathDocument.self,
                from: pathAfter.data
            )
        } catch {
            throw LensFailure.invalidReceipt("the path receipt is not valid kingdom.path/v1 JSON")
        }
        let pathRecord = try pathDocument.validated(forLexicalPath: selection.lexicalPath)
        try Task.checkCancellation()

        guard selection.targetIsDirectory,
              pathRecord.resolution.complete,
              pathRecord.resolvedPath == selection.canonicalWorkspace.path
        else {
            return LensAnalysis(
                pathDocument: pathDocument,
                pathRecord: pathRecord,
                indexDocument: nil,
                repository: nil,
                indexNotice: nil
            )
        }

        do {
            let (indexDocument, repository) = try analyzeRepository(
                selection.canonicalWorkspace,
                runner: runner,
                environment: environment,
                scan: scan
            )
            try Task.checkCancellation()
            return LensAnalysis(
                pathDocument: pathDocument,
                pathRecord: pathRecord,
                indexDocument: indexDocument,
                repository: repository,
                indexNotice: nil
            )
        } catch is CancellationError {
            throw CancellationError()
        } catch {
            return LensAnalysis(
                pathDocument: pathDocument,
                pathRecord: pathRecord,
                indexDocument: nil,
                repository: nil,
                indexNotice: Self.genericIndexNotice
            )
        }
    }

    private func analyzeRepository(
        _ directory: URL,
        runner: BoundedProcessRunner,
        environment: [String: String],
        scan: ScanDirectory
    ) throws -> (KingdomIndexDocument, KingdomRepositoryRecord) {
        try Task.checkCancellation()
        let indexOutput = scan.url.appendingPathComponent(
            "kingdom.index.json",
            isDirectory: false
        )
        try runChecked(
            runner,
            arguments: [
                "index", "compile",
                "--repo-root", directory.path,
                "--output", indexOutput.path,
            ],
            environment: environment,
            scan: scan,
            stage: "KINGDOM repository analysis"
        )
        let indexBefore = try SecureReceipt.read(
            at: indexOutput,
            maximumBytes: Self.receiptLimit,
            label: "index receipt"
        )
        try runChecked(
            runner,
            arguments: ["index", "verify", indexOutput.path],
            environment: environment,
            scan: scan,
            stage: "KINGDOM index verification"
        )
        try scan.validate()
        let indexAfter = try SecureReceipt.read(
            at: indexOutput,
            maximumBytes: Self.receiptLimit,
            label: "index receipt"
        )
        try indexAfter.requireUnchanged(from: indexBefore, label: "the index receipt")

        let document: KingdomIndexDocument
        do {
            document = try JSONDecoder().decode(KingdomIndexDocument.self, from: indexAfter.data)
        } catch {
            throw LensFailure.invalidReceipt("the index receipt is not valid kingdom.index/v1 JSON")
        }
        let repository = try document.validated(forCanonicalDirectory: directory.path)
        return (document, repository)
    }

    private func runChecked(
        _ runner: BoundedProcessRunner,
        arguments: [String],
        environment: [String: String],
        scan: ScanDirectory,
        stage: String
    ) throws {
        try scan.validate()
        let result = try runner.run(
            arguments: arguments,
            environment: environment,
            workingDirectory: scan.url,
            stage: stage
        )
        guard result.status == 0 else {
            throw LensFailure.commandFailed(
                stage: stage,
                status: result.status,
                detail: boundedDiagnostic(result.standardError)
            )
        }
    }

    private func minimalEnvironment(scanDirectory: URL) -> [String: String] {
        [
            "HOME": homeURL.path,
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "TMPDIR": scanDirectory.path,
            "XDG_CACHE_HOME": scanDirectory.path,
        ]
    }

    private func boundedDiagnostic(_ data: Data) -> String {
        let decoded = String(decoding: data.prefix(1_024), as: UTF8.self)
        let flattened = decoded.unicodeScalars.map { scalar -> Character in
            if scalar.value == 9 || scalar.value == 10 || scalar.value == 13 {
                return " "
            }
            if scalar.value < 32 || scalar.value == 127 {
                return "�"
            }
            return Character(String(scalar))
        }
        return String(flattened)
            .split(whereSeparator: \.isWhitespace)
            .joined(separator: " ")
    }
}

private struct SelectedPath: Sendable {
    let lexicalPath: String
    let canonicalWorkspace: URL
    let targetIsDirectory: Bool

    init(url: URL) throws {
        guard url.isFileURL else {
            throw LensFailure.invalidInput("only local file URLs are supported")
        }
        let path = url.path
        guard path.count <= 8_192,
              KingdomPathDocument.isAbsoluteCanonical(path)
        else {
            throw LensFailure.invalidInput("the path must be absolute, canonical, and free of controls")
        }
        lexicalPath = path

        var metadata = stat()
        let targetExists = stat(path, &metadata) == 0
        targetIsDirectory = targetExists && (metadata.st_mode & S_IFMT) == S_IFDIR

        var candidate = targetIsDirectory
            ? URL(fileURLWithPath: path, isDirectory: true)
            : URL(fileURLWithPath: path, isDirectory: false).deletingLastPathComponent()
        while true {
            var candidateMetadata = stat()
            if stat(candidate.path, &candidateMetadata) == 0,
               (candidateMetadata.st_mode & S_IFMT) == S_IFDIR
            {
                break
            }
            let parent = candidate.deletingLastPathComponent()
            guard parent.path != candidate.path else {
                throw LensFailure.invalidInput("no existing workspace ancestor could be derived")
            }
            candidate = parent
        }

        guard let resolved = canonicalPath(candidate.path) else {
            throw LensFailure.invalidInput("the workspace ancestor cannot be resolved")
        }
        let workspace = URL(fileURLWithPath: resolved, isDirectory: true)
        var workspaceMetadata = stat()
        guard Darwin.lstat(workspace.path, &workspaceMetadata) == 0,
              (workspaceMetadata.st_mode & S_IFMT) == S_IFDIR,
              canonicalPath(workspace.path) == workspace.path
        else {
            throw LensFailure.invalidInput("the derived workspace is not a canonical directory")
        }
        canonicalWorkspace = workspace
    }
}
