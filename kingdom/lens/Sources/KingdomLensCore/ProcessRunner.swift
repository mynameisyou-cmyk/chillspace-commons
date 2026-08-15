import Darwin
import Dispatch
import Foundation

struct ValidatedExecutable: Sendable {
    let url: URL
    private let identity: ExecutableIdentity

    init(url: URL) throws {
        guard url.isFileURL,
              KingdomPathDocument.isAbsoluteCanonical(url.path)
        else {
            throw LensFailure.invalidExecutable("its path must be canonical and absolute")
        }
        guard let resolved = canonicalPath(url.path), resolved == url.path else {
            throw LensFailure.invalidExecutable(
                "its path contains a symbolic link or alias (\(url.path) → \(canonicalPath(url.path) ?? "missing"))"
            )
        }
        identity = try Self.inspect(url)
        self.url = url
    }

    func revalidate() throws {
        guard let resolved = canonicalPath(url.path), resolved == url.path else {
            throw LensFailure.invalidExecutable("its path changed or contains a symbolic link")
        }
        guard try Self.inspect(url) == identity else {
            throw LensFailure.invalidExecutable("its identity changed after validation")
        }
    }

    private static func inspect(_ url: URL) throws -> ExecutableIdentity {
        var metadata = stat()
        guard Darwin.lstat(url.path, &metadata) == 0 else {
            throw LensFailure.invalidExecutable("it is missing (\(errnoText()))")
        }
        guard (metadata.st_mode & S_IFMT) == S_IFREG else {
            throw LensFailure.invalidExecutable("it is not a regular file")
        }
        guard metadata.st_uid == Darwin.geteuid() else {
            throw LensFailure.invalidExecutable("it is not owned by the current user")
        }
        guard metadata.st_mode & mode_t(S_IXUSR) != 0 else {
            throw LensFailure.invalidExecutable("its owner execute bit is not set")
        }
        guard metadata.st_mode & mode_t(S_IWGRP | S_IWOTH | S_ISUID | S_ISGID) == 0 else {
            throw LensFailure.invalidExecutable("its mode permits unsafe mutation or elevation")
        }
        return ExecutableIdentity(metadata)
    }
}

private struct ExecutableIdentity: Equatable, Sendable {
    let device: UInt64
    let inode: UInt64
    let owner: UInt32
    let mode: UInt16
    let size: Int64
    let modifiedSeconds: Int64
    let modifiedNanoseconds: Int64

    init(_ metadata: stat) {
        device = UInt64(metadata.st_dev)
        inode = UInt64(metadata.st_ino)
        owner = metadata.st_uid
        mode = UInt16(metadata.st_mode & mode_t(0o7777))
        size = Int64(metadata.st_size)
        modifiedSeconds = Int64(metadata.st_mtimespec.tv_sec)
        modifiedNanoseconds = Int64(metadata.st_mtimespec.tv_nsec)
    }
}

struct BoundedProcessResult: Sendable {
    let status: Int32
    let standardOutput: Data
    let standardError: Data
}

struct BoundedProcessRunner: Sendable {
    let executable: ValidatedExecutable
    let timeout: TimeInterval
    let outputLimit: Int

    func run(
        arguments: [String],
        environment: [String: String],
        workingDirectory: URL,
        stage: String
    ) throws -> BoundedProcessResult {
        guard timeout > 0, timeout <= 300, outputLimit > 0 else {
            throw LensFailure.processLaunch(stage: stage, reason: "invalid process bounds")
        }
        guard arguments.allSatisfy({ !$0.utf8.contains(0) }),
              environment.allSatisfy({
                  !$0.key.contains("=")
                      && !$0.key.utf8.contains(0)
                      && !$0.value.utf8.contains(0)
              })
        else {
            throw LensFailure.processLaunch(stage: stage, reason: "an argument contains NUL")
        }
        try executable.revalidate()

        var stdoutPipe = [Int32](repeating: -1, count: 2)
        var stderrPipe = [Int32](repeating: -1, count: 2)
        guard Darwin.pipe(&stdoutPipe) == 0 else {
            throw LensFailure.processLaunch(stage: stage, reason: "stdout pipe: \(errnoText())")
        }
        guard Darwin.pipe(&stderrPipe) == 0 else {
            closePair(stdoutPipe)
            throw LensFailure.processLaunch(stage: stage, reason: "stderr pipe: \(errnoText())")
        }

        var actions: posix_spawn_file_actions_t?
        var attributes: posix_spawnattr_t?
        guard posix_spawn_file_actions_init(&actions) == 0,
              posix_spawnattr_init(&attributes) == 0
        else {
            closePair(stdoutPipe)
            closePair(stderrPipe)
            throw LensFailure.processLaunch(stage: stage, reason: "spawn setup failed")
        }
        defer {
            posix_spawn_file_actions_destroy(&actions)
            posix_spawnattr_destroy(&attributes)
        }

        let actionResults = [
            posix_spawn_file_actions_adddup2(&actions, stdoutPipe[1], STDOUT_FILENO),
            posix_spawn_file_actions_adddup2(&actions, stderrPipe[1], STDERR_FILENO),
            posix_spawn_file_actions_addclose(&actions, stdoutPipe[0]),
            posix_spawn_file_actions_addclose(&actions, stdoutPipe[1]),
            posix_spawn_file_actions_addclose(&actions, stderrPipe[0]),
            posix_spawn_file_actions_addclose(&actions, stderrPipe[1]),
            posix_spawn_file_actions_addchdir_np(&actions, workingDirectory.path),
        ]
        guard actionResults.allSatisfy({ $0 == 0 }) else {
            closePair(stdoutPipe)
            closePair(stderrPipe)
            throw LensFailure.processLaunch(stage: stage, reason: "spawn file actions failed")
        }

        let flags = Int16(POSIX_SPAWN_SETPGROUP | POSIX_SPAWN_CLOEXEC_DEFAULT)
        guard posix_spawnattr_setflags(&attributes, flags) == 0,
              posix_spawnattr_setpgroup(&attributes, 0) == 0
        else {
            closePair(stdoutPipe)
            closePair(stderrPipe)
            throw LensFailure.processLaunch(stage: stage, reason: "process-group setup failed")
        }

        setNonBlocking(stdoutPipe[0])
        setNonBlocking(stderrPipe[0])

        var argv = try CStringVector([executable.url.path] + arguments)
        var envp = try CStringVector(
            environment.map { "\($0.key)=\($0.value)" }.sorted()
        )
        defer {
            argv.release()
            envp.release()
        }
        var child = pid_t()
        let spawnResult = executable.url.path.withCString { executablePath in
            argv.withUnsafeMutablePointer { argvPointer in
                envp.withUnsafeMutablePointer { environmentPointer in
                    posix_spawn(
                        &child,
                        executablePath,
                        &actions,
                        &attributes,
                        argvPointer,
                        environmentPointer
                    )
                }
            }
        }

        Darwin.close(stdoutPipe[1])
        Darwin.close(stderrPipe[1])
        stdoutPipe[1] = -1
        stderrPipe[1] = -1
        guard spawnResult == 0, child > 0 else {
            Darwin.close(stdoutPipe[0])
            Darwin.close(stderrPipe[0])
            throw LensFailure.processLaunch(
                stage: stage,
                reason: String(cString: Darwin.strerror(spawnResult))
            )
        }

        do {
            try executable.revalidate()
        } catch {
            killAndReap(processGroup: child)
            Darwin.close(stdoutPipe[0])
            Darwin.close(stderrPipe[0])
            throw error
        }

        let stdout = BoundedPipeCapture(descriptor: stdoutPipe[0], limit: outputLimit)
        let stderr = BoundedPipeCapture(descriptor: stderrPipe[0], limit: outputLimit)
        let readers = DispatchGroup()
        DispatchQueue.global(qos: .userInitiated).async(group: readers) {
            stdout.consume()
        }
        DispatchQueue.global(qos: .userInitiated).async(group: readers) {
            stderr.consume()
        }

        var waitStatus: Int32 = 0
        var reaped = false
        var terminalFailure: LensFailure?
        var wasCancelled = false
        let timeoutNanoseconds = UInt64(timeout * 1_000_000_000)
        let start = DispatchTime.now().uptimeNanoseconds

        while !reaped {
            let waited = Darwin.waitpid(child, &waitStatus, WNOHANG)
            if waited == child {
                reaped = true
                break
            }
            if waited == -1 {
                if errno == EINTR {
                    continue
                }
                terminalFailure = .processLaunch(stage: stage, reason: "waitpid: \(errnoText())")
                break
            }
            if Task.isCancelled {
                wasCancelled = true
                break
            }
            if stdout.exceededLimit || stderr.exceededLimit {
                terminalFailure = .outputLimitExceeded(stage: stage)
                break
            }
            if stdout.readError != nil || stderr.readError != nil {
                terminalFailure = .processLaunch(stage: stage, reason: "captured output could not be read")
                break
            }
            if DispatchTime.now().uptimeNanoseconds - start >= timeoutNanoseconds {
                terminalFailure = .commandTimedOut(stage: stage)
                break
            }
            Darwin.usleep(5_000)
        }

        // A command is not allowed to leave descendants behind. The negative
        // pid addresses the isolated process group created by posix_spawn.
        _ = Darwin.kill(-child, SIGKILL)
        if !reaped {
            while Darwin.waitpid(child, &waitStatus, 0) == -1, errno == EINTR {}
        }

        stdout.stop()
        stderr.stop()
        readers.wait()

        if wasCancelled {
            throw CancellationError()
        }
        if let terminalFailure {
            throw terminalFailure
        }
        if stdout.exceededLimit || stderr.exceededLimit {
            throw LensFailure.outputLimitExceeded(stage: stage)
        }
        if let readError = stdout.readError ?? stderr.readError {
            throw LensFailure.processLaunch(
                stage: stage,
                reason: "captured output: \(errnoText(readError))"
            )
        }
        return BoundedProcessResult(
            status: decodedExitStatus(waitStatus),
            standardOutput: stdout.data,
            standardError: stderr.data
        )
    }

    private func killAndReap(processGroup child: pid_t) {
        _ = Darwin.kill(-child, SIGKILL)
        var status: Int32 = 0
        while Darwin.waitpid(child, &status, 0) == -1, errno == EINTR {}
    }
}

private final class BoundedPipeCapture: @unchecked Sendable {
    private let descriptor: Int32
    private let limit: Int
    private let lock = NSLock()
    private var storage = Data()
    private var shouldStop = false
    private var limitWasExceeded = false
    private var storedReadError: Int32?

    init(descriptor: Int32, limit: Int) {
        self.descriptor = descriptor
        self.limit = limit
        storage.reserveCapacity(min(limit, 64 * 1024))
    }

    var data: Data {
        lock.withLock { storage }
    }

    var exceededLimit: Bool {
        lock.withLock { limitWasExceeded }
    }

    var readError: Int32? {
        lock.withLock { storedReadError }
    }

    func stop() {
        lock.withLock { shouldStop = true }
    }

    func consume() {
        defer { Darwin.close(descriptor) }
        var buffer = [UInt8](repeating: 0, count: 16_384)
        while true {
            let count = buffer.withUnsafeMutableBytes { bytes -> Int in
                Darwin.read(descriptor, bytes.baseAddress, bytes.count)
            }
            if count > 0 {
                let accepted = lock.withLock { () -> Bool in
                    guard storage.count <= limit - count else {
                        limitWasExceeded = true
                        shouldStop = true
                        return false
                    }
                    storage.append(buffer, count: count)
                    return true
                }
                if !accepted {
                    return
                }
                continue
            }
            if count == 0 {
                return
            }
            if errno == EINTR {
                continue
            }
            if errno == EAGAIN || errno == EWOULDBLOCK {
                if lock.withLock({ shouldStop }) {
                    return
                }
                Darwin.usleep(2_000)
                continue
            }
            lock.withLock {
                storedReadError = errno
                shouldStop = true
            }
            return
        }
    }
}

private struct CStringVector {
    private var pointers: [UnsafeMutablePointer<CChar>?]

    init(_ strings: [String]) throws {
        pointers = []
        pointers.reserveCapacity(strings.count + 1)
        for string in strings {
            guard let pointer = Darwin.strdup(string) else {
                for case let existing? in pointers {
                    Darwin.free(existing)
                }
                throw LensFailure.processLaunch(stage: "KINGDOM", reason: "argument allocation failed")
            }
            pointers.append(pointer)
        }
        pointers.append(nil)
    }

    mutating func withUnsafeMutablePointer<Result>(
        _ body: (UnsafeMutablePointer<UnsafeMutablePointer<CChar>?>) -> Result
    ) -> Result {
        pointers.withUnsafeMutableBufferPointer { buffer in
            body(buffer.baseAddress!)
        }
    }

    mutating func release() {
        for case let pointer? in pointers {
            Darwin.free(pointer)
        }
        pointers.removeAll(keepingCapacity: false)
    }
}

private func closePair(_ pair: [Int32]) {
    for descriptor in pair where descriptor >= 0 {
        Darwin.close(descriptor)
    }
}

private func setNonBlocking(_ descriptor: Int32) {
    let existing = Darwin.fcntl(descriptor, F_GETFL)
    if existing >= 0 {
        _ = Darwin.fcntl(descriptor, F_SETFL, existing | O_NONBLOCK)
    }
}

private func decodedExitStatus(_ status: Int32) -> Int32 {
    let signal = status & 0x7f
    if signal == 0 {
        return (status >> 8) & 0xff
    }
    return 128 + signal
}

private extension NSLock {
    func withLock<Result>(_ body: () throws -> Result) rethrows -> Result {
        lock()
        defer { unlock() }
        return try body()
    }
}
