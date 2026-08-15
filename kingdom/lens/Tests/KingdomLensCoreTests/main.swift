@_spi(Testing) import KingdomLensCore
import Darwin
import Foundation

@main
struct KingdomLensSelfTest {
    static func main() async {
        do {
            let fixture = try Fixture()
            defer { fixture.remove() }

            try await run("path decoding and validation") {
                try await testPathDecoding(fixture)
            }
            try await run("index decoding preserves unknown state") {
                try await testIndexDecoding(fixture)
            }
            try await run("index failure stays generic and nonfatal") {
                try await testNonfatalIndexFailure(fixture)
            }
            try await run("unsupported path schema is rejected") {
                try await testInvalidSchema(fixture)
            }
            try await run("weird path is passed as one argv element") {
                try await testWeirdArgument(fixture)
            }
            try await run("stdout is bounded") {
                try await testOutputLimit(fixture)
            }
            try await run("timeout kills descendant process group") {
                try await testTimeoutCleanup(fixture)
            }
            try await run("cancellation kills descendant process group") {
                try await testCancellationCleanup(fixture)
            }
            try await run("symlink receipt is rejected") {
                try await testSymlinkReceipt(fixture)
            }
            try await run("permissive receipt mode is rejected") {
                try await testReceiptMode(fixture)
            }
            try await run("receipt stability is enforced") {
                try await testReceiptStability(fixture)
            }
            try await run("single-quote display escaping") {
                try testShellQuote()
            }
            print("KINGDOM Lens self-test: all checks passed")
        } catch {
            fputs("KINGDOM Lens self-test failed: \(error.localizedDescription)\n", stderr)
            Darwin.exit(1)
        }
    }

    private static func run(
        _ name: String,
        _ test: @Sendable () async throws -> Void
    ) async throws {
        try await test()
        print("PASS  \(name)")
    }

    private static func testPathDecoding(_ fixture: Fixture) async throws {
        let selected = try fixture.file(named: "ordinary")
        let client = try fixture.client()
        let analysis = try await client.analyze(url: selected)
        try require(analysis.pathDocument.schema == "kingdom.path/v1", "path schema")
        try require(analysis.pathDocument.classifier == "darwin-path/1", "path classifier")
        try require(analysis.pathRecord.requestedPath == selected.path, "requested path")
        try require(analysis.pathRecord.lexicalPath == selected.path, "lexical path")
        try require(analysis.pathRecord.authority.effective == "unknown", "authority truth")
        try require(analysis.indexDocument == nil, "files must not trigger repository indexing")
        requireSendable(analysis)
        requireSendable(analysis.pathDocument)
    }

    private static func testIndexDecoding(_ fixture: Fixture) async throws {
        let selected = try fixture.directory(named: "repo-ok")
        let analysis = try await fixture.client().analyze(url: selected)
        try require(analysis.indexNotice == nil, "verified index notice")
        try require(analysis.indexDocument?.schema == "kingdom.index/v1", "index schema")
        try require(analysis.repository?.worktreePath == selected.path, "repository path")
        try require(analysis.repository?.workingTree.state == "unknown", "unknown worktree state")
        try require(analysis.repository?.workingTree.state != "clean", "must never infer clean")
        if let document = analysis.indexDocument {
            requireSendable(document)
        }
    }

    private static func testNonfatalIndexFailure(_ fixture: Fixture) async throws {
        let selected = try fixture.directory(named: "index-fail")
        let analysis = try await fixture.client().analyze(url: selected)
        try require(analysis.pathRecord.resolution.complete, "path survives index failure")
        try require(analysis.indexDocument == nil, "failed index document")
        try require(analysis.repository == nil, "failed repository")
        try require(
            analysis.indexNotice
                == "Repository evidence is unavailable for this directory; no clean or trusted state is implied.",
            "generic index notice"
        )
    }

    private static func testInvalidSchema(_ fixture: Fixture) async throws {
        let selected = try fixture.file(named: "bad-schema")
        do {
            _ = try await fixture.client().analyze(url: selected)
            throw TestFailure("unsupported schema was accepted")
        } catch LensFailure.invalidReceipt {
            return
        }
    }

    private static func testWeirdArgument(_ fixture: Fixture) async throws {
        let selected = try fixture.file(named: "odd ' ; touch PWNED ; #")
        let analysis = try await fixture.client().analyze(url: selected)
        try require(analysis.pathRecord.requestedPath == selected.path, "argv preservation")
        try require(
            !FileManager.default.fileExists(atPath: selected.path + ".injection-observed"),
            "shell metacharacters were interpreted"
        )
    }

    private static func testOutputLimit(_ fixture: Fixture) async throws {
        let selected = try fixture.file(named: "spam")
        let client = try fixture.client(timeout: 2, outputLimit: 512)
        do {
            _ = try await client.analyze(url: selected)
            throw TestFailure("unbounded output was accepted")
        } catch LensFailure.outputLimitExceeded {
            return
        }
    }

    private static func testTimeoutCleanup(_ fixture: Fixture) async throws {
        let selected = try fixture.file(named: "timeout")
        let client = try fixture.client(timeout: 0.4)
        do {
            _ = try await client.analyze(url: selected)
            throw TestFailure("hung command did not time out")
        } catch LensFailure.commandTimedOut {
            let child = try fixture.childPID(for: selected)
            try requireProcessGone(child)
        }
    }

    private static func testCancellationCleanup(_ fixture: Fixture) async throws {
        let selected = try fixture.file(named: "cancel")
        let client = try fixture.client(timeout: 10)
        let task = Task {
            try await client.analyze(url: selected)
        }
        let pidFile = URL(fileURLWithPath: selected.path + ".childpid")
        for _ in 0..<100 where !FileManager.default.fileExists(atPath: pidFile.path) {
            try? await Task.sleep(nanoseconds: 10_000_000)
        }
        try require(FileManager.default.fileExists(atPath: pidFile.path), "descendant pid was not recorded")
        task.cancel()
        do {
            _ = try await task.value
            throw TestFailure("cancelled analysis returned normally")
        } catch is CancellationError {
            let child = try fixture.childPID(for: selected)
            try requireProcessGone(child)
        }
    }

    private static func testSymlinkReceipt(_ fixture: Fixture) async throws {
        let selected = try fixture.file(named: "output-symlink")
        do {
            _ = try await fixture.client().analyze(url: selected)
            throw TestFailure("symlink output was accepted")
        } catch LensFailure.unsafeReceipt {
            return
        }
    }

    private static func testReceiptMode(_ fixture: Fixture) async throws {
        let selected = try fixture.file(named: "output-mode")
        do {
            _ = try await fixture.client().analyze(url: selected)
            throw TestFailure("permissive output mode was accepted")
        } catch LensFailure.unsafeReceipt {
            return
        }
    }

    private static func testReceiptStability(_ fixture: Fixture) async throws {
        let selected = try fixture.file(named: "unstable")
        do {
            _ = try await fixture.client().analyze(url: selected)
            throw TestFailure("mutated verified output was accepted")
        } catch LensFailure.unstableReceipt {
            return
        }
    }

    private static func testShellQuote() throws {
        try require(ShellQuote.single("") == "''", "empty shell quote")
        try require(ShellQuote.single("plain") == "'plain'", "plain shell quote")
        try require(ShellQuote.single("a'b") == "'a'\\''b'", "embedded single quote")
        try require(
            ShellQuote.single("$(touch PWNED)") == "'$(touch PWNED)'",
            "metacharacter shell quote"
        )
    }

    private static func require(_ condition: @autoclosure () -> Bool, _ label: String) throws {
        guard condition() else {
            throw TestFailure("assertion failed: \(label)")
        }
    }

    private static func requireSendable<Value: Sendable>(_ value: Value) {
        _ = value
    }

    private static func requireProcessGone(_ process: pid_t) throws {
        for _ in 0..<200 {
            if Darwin.kill(process, 0) == -1, errno == ESRCH {
                return
            }
            Darwin.usleep(10_000)
        }
        _ = Darwin.kill(process, SIGKILL)
        throw TestFailure("descendant process \(process) survived group cleanup")
    }
}

private struct TestFailure: Error, LocalizedError {
    let message: String

    init(_ message: String) {
        self.message = message
    }

    var errorDescription: String? { message }
}

private final class Fixture: @unchecked Sendable {
    let root: URL
    let binary: URL

    init() throws {
        var template = Array(
            FileManager.default.temporaryDirectory
                .appendingPathComponent("kingdom-lens-tests.XXXXXX")
                .path
                .utf8CString
        )
        let created: String? = template.withUnsafeMutableBufferPointer { bytes in
            guard let baseAddress = bytes.baseAddress,
                  let result = Darwin.mkdtemp(baseAddress)
            else {
                return nil
            }
            return String(cString: result)
        }
        guard let created else {
            throw TestFailure("could not create fixture root")
        }
        guard let resolvedRoot = Darwin.realpath(created, nil) else {
            throw TestFailure("could not resolve fixture root")
        }
        let canonicalRoot = String(cString: resolvedRoot)
        Darwin.free(resolvedRoot)
        root = URL(fileURLWithPath: canonicalRoot, isDirectory: true)
        binary = root.appendingPathComponent("fake-kingdom", isDirectory: false)
        try Data(Self.fakeKingdom.utf8).write(to: binary)
        guard Darwin.chmod(binary.path, mode_t(0o700)) == 0 else {
            throw TestFailure("could not make fake KINGDOM executable")
        }
    }

    func remove() {
        try? FileManager.default.removeItem(at: root)
    }

    func file(named name: String) throws -> URL {
        let url = root.appendingPathComponent(name, isDirectory: false)
        guard FileManager.default.createFile(atPath: url.path, contents: Data("lens".utf8)) else {
            throw TestFailure("could not create selected file")
        }
        return url
    }

    func directory(named name: String) throws -> URL {
        let url = root.appendingPathComponent(name, isDirectory: true)
        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: false)
        return url
    }

    func client(
        timeout: TimeInterval = 2,
        outputLimit: Int = 64_000
    ) throws -> KingdomClient {
        try KingdomClient(
            binaryURL: binary,
            timeout: timeout,
            outputLimit: outputLimit,
            temporaryRoot: root
        )
    }

    func childPID(for selected: URL) throws -> pid_t {
        let data = try Data(contentsOf: URL(fileURLWithPath: selected.path + ".childpid"))
        guard let text = String(data: data, encoding: .utf8),
              let value = pid_t(text.trimmingCharacters(in: .whitespacesAndNewlines))
        else {
            throw TestFailure("descendant pid is invalid")
        }
        return value
    }

    private static let fakeKingdom = #"""
#!/usr/bin/python3
import json
import os
import subprocess
import sys
import time

args = sys.argv[1:]

def value_after(flag):
    return args[args.index(flag) + 1]

def write_json(path, value, mode=0o600):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(path, mode)

def path_document(requested, workspace):
    lexical = os.path.normpath(requested)
    resolved = os.path.realpath(requested)
    info = os.lstat(requested)
    is_directory = os.path.isdir(requested)
    root_prefix = workspace.rstrip(os.sep) + os.sep
    inside = lexical == workspace or lexical.startswith(root_prefix)
    resolved_inside = resolved == workspace or resolved.startswith(root_prefix)
    record = {
        "requested_path": requested,
        "lexical_path": lexical,
        "resolved_path": resolved,
        "resolution": {
            "complete": True,
            "error": None,
            "deepest_existing_ancestor": lexical,
            "missing_suffix": [],
            "lexical_exists": True,
            "target_exists": True,
            "symlink_components": 0,
            "final_component_is_symlink": False,
        },
        "workspace": {
            "relation": "inside" if resolved_inside else ("escaped-via-resolution" if inside else "outside"),
            "lexical_roots": [workspace] if inside else [],
            "resolved_roots": [workspace] if resolved_inside else [],
        },
        "domain": {"value": "workspace" if resolved_inside else "other", "truth": "inferred"},
        "locality": {"value": "local", "truth": "inferred", "materialization": "not-applicable"},
        "metadata": {
            "source": "target",
            "file_type": "directory" if is_directory else "file",
            "mode": format(info.st_mode & 0o7777, "04o"),
            "uid": info.st_uid,
            "gid": info.st_gid,
            "device": info.st_dev,
            "inode": info.st_ino,
            "flags": getattr(info, "st_flags", 0),
            "xattrs": {"truth": "observed", "names": [], "unreported_count": 0},
        },
        "volume": {"read_only": False, "truth": "observed"},
        "process_access": {
            "target_readable": True,
            "target_writable": True,
            "target_executable": is_directory,
            "ancestor_writable": True,
            "ancestor_executable": True,
            "truth": "observed-for-current-process",
        },
        "authority": {
            "effective": "unknown",
            "tcc": "unknown",
            "codex_sandbox": "unknown",
            "acl": "unknown",
            "reason": "Path and process evidence cannot establish consent or a future execution boundary.",
        },
        "record_digest": "a" * 64,
    }
    return {
        "schema": "unsupported.path/v9" if os.path.basename(requested) == "bad-schema" else "kingdom.path/v1",
        "classifier": "darwin-path/1",
        "host": {"kernel": "Darwin", "machine": "arm64", "hostname_included": False},
        "records": [record],
        "non_claims": ["no TCC claim", "no sandbox claim", "no permission claim"],
        "classification_digest": "b" * 64,
    }

def index_document(repository):
    info = os.stat(repository)
    git = os.path.join(repository, ".git")
    repo_id = "repo-" + ("1" * 32)
    record = {
        "repository_id": repo_id,
        "canonical": True,
        "worktree_path": repository,
        "path_identity": {"device": info.st_dev, "inode": info.st_ino},
        "git": {
            "directory": git,
            "common_directory": git,
            "objects_directory": os.path.join(git, "objects"),
            "object_format": "sha1",
            "head": "2" * 40,
            "head_tree": "3" * 40,
            "ref": "refs/heads/main",
            "shallow": False,
            "root_commits": ["4" * 40],
            "lineage_complete": True,
            "lineage_digest": "5" * 64,
        },
        "working_tree": {
            "state": "unknown",
            "tracked_content": "not-inspected",
            "untracked_content": "not-inspected",
            "staged_records": 0,
            "staged_digest": "6" * 64,
        },
        "manifest": {
            "path": "kingdom.yaml",
            "sha256": "7" * 64,
            "bytes": 1,
            "fields": {
                "name": "fixture",
                "purpose": "self test",
                "kind": "room",
                "domain": "local",
                "layer": "test",
                "owner_sister": "none",
                "state": "unknown",
                "depends_on": [],
                "adopts": [],
                "doors_count": 0,
            },
        },
        "instructions": [],
        "repository_digest": "8" * 64,
    }
    return {
        "schema": "kingdom.index/v1",
        "compiler": "kingdom-index/1",
        "input_digest": "9" * 64,
        "repositories": [record],
        "ambiguity_groups": [],
        "non_claims": ["no authority", "no trust", "no clean claim"],
        "index_digest": "c" * 64,
    }

if args[:1] == ["path"] and "--verify" in args:
    receipt = value_after("--verify")
    with open(receipt, "r", encoding="utf-8") as handle:
        document = json.load(handle)
    requested = document["records"][0]["requested_path"]
    if os.path.basename(requested) == "unstable":
        document["classification_digest"] = "d" * 64
        write_json(receipt, document)
    print("verified path")
    sys.exit(0)

if args[:2] == ["index", "verify"]:
    print("verified index")
    sys.exit(0)

if args[:1] == ["path"] and "--path" in args:
    requested = value_after("--path")
    workspace = value_after("--workspace-root")
    output = value_after("--output")
    name = os.path.basename(requested)
    if os.path.exists("PWNED"):
        with open(requested + ".injection-observed", "w", encoding="utf-8") as handle:
            handle.write("shell interpretation observed")
    if name == "spam":
        print("x" * 4096, flush=True)
        time.sleep(2)
    if name in {"timeout", "cancel"}:
        child = subprocess.Popen([
            "/bin/sh", "-c",
            "trap '' TERM; while :; do /bin/sleep 1; done",
        ])
        with open(requested + ".childpid", "w", encoding="utf-8") as handle:
            handle.write(str(child.pid))
            handle.flush()
            os.fsync(handle.fileno())
        time.sleep(60)
    document = path_document(requested, workspace)
    if name == "output-symlink":
        target = output + ".target"
        write_json(target, document)
        os.symlink(target, output)
    elif name == "output-mode":
        write_json(output, document, 0o644)
    else:
        write_json(output, document)
    print(output)
    sys.exit(0)

if args[:2] == ["index", "compile"]:
    repository = value_after("--repo-root")
    output = value_after("--output")
    if os.path.basename(repository) == "index-fail":
        print("repository unavailable", file=sys.stderr)
        sys.exit(2)
    write_json(output, index_document(repository))
    print(output)
    sys.exit(0)

print("unsupported fake invocation", file=sys.stderr)
sys.exit(2)
"""#
}
