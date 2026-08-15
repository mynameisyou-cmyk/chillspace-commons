import Darwin
import Foundation

struct SecureReceiptSnapshot: Sendable {
    let data: Data
    let identity: SecureFileIdentity

    func requireUnchanged(from earlier: SecureReceiptSnapshot, label: String) throws {
        guard identity == earlier.identity, data == earlier.data else {
            throw LensFailure.unstableReceipt("\(label) changed across offline verification")
        }
    }
}

struct SecureFileIdentity: Equatable, Sendable {
    let device: UInt64
    let inode: UInt64
    let owner: UInt32
    let mode: UInt16
    let links: UInt64
    let size: Int64
    let modifiedSeconds: Int64
    let modifiedNanoseconds: Int64

    init(_ metadata: stat) {
        device = UInt64(metadata.st_dev)
        inode = UInt64(metadata.st_ino)
        owner = metadata.st_uid
        mode = UInt16(metadata.st_mode & mode_t(0o777))
        links = UInt64(metadata.st_nlink)
        size = Int64(metadata.st_size)
        modifiedSeconds = Int64(metadata.st_mtimespec.tv_sec)
        modifiedNanoseconds = Int64(metadata.st_mtimespec.tv_nsec)
    }
}

enum SecureReceipt {
    static func read(
        at url: URL,
        maximumBytes: Int,
        label: String
    ) throws -> SecureReceiptSnapshot {
        guard url.isFileURL,
              url.path.hasPrefix("/"),
              maximumBytes > 0,
              !url.path.utf8.contains(0)
        else {
            throw LensFailure.unsafeReceipt("\(label) has an invalid location")
        }

        let descriptor = Darwin.open(
            url.path,
            O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK
        )
        guard descriptor >= 0 else {
            throw LensFailure.unsafeReceipt(
                "\(label) could not be opened without following links (\(errnoText()))"
            )
        }
        defer { Darwin.close(descriptor) }

        let before = try checkedMetadata(
            descriptor: descriptor,
            maximumBytes: maximumBytes,
            label: label
        )
        var data = Data()
        data.reserveCapacity(Int(before.size))
        var buffer = [UInt8](repeating: 0, count: 16_384)

        while true {
            let count = buffer.withUnsafeMutableBytes { bytes -> Int in
                Darwin.read(descriptor, bytes.baseAddress, bytes.count)
            }
            if count > 0 {
                guard data.count <= maximumBytes - count else {
                    throw LensFailure.unsafeReceipt("\(label) exceeds the size bound")
                }
                data.append(buffer, count: count)
                continue
            }
            if count == 0 {
                break
            }
            if errno == EINTR {
                continue
            }
            throw LensFailure.unsafeReceipt("\(label) could not be read (\(errnoText()))")
        }

        let after = try checkedMetadata(
            descriptor: descriptor,
            maximumBytes: maximumBytes,
            label: label
        )
        guard before == after, data.count == Int(after.size) else {
            throw LensFailure.unstableReceipt("\(label) changed while it was read")
        }
        return SecureReceiptSnapshot(data: data, identity: after)
    }

    private static func checkedMetadata(
        descriptor: Int32,
        maximumBytes: Int,
        label: String
    ) throws -> SecureFileIdentity {
        var metadata = stat()
        guard Darwin.fstat(descriptor, &metadata) == 0 else {
            throw LensFailure.unsafeReceipt("\(label) metadata is unavailable (\(errnoText()))")
        }
        guard (metadata.st_mode & S_IFMT) == S_IFREG else {
            throw LensFailure.unsafeReceipt("\(label) is not a regular file")
        }
        guard metadata.st_uid == Darwin.geteuid() else {
            throw LensFailure.unsafeReceipt("\(label) is not owned by the current user")
        }
        let permissions = metadata.st_mode & mode_t(0o777)
        guard permissions == mode_t(S_IRUSR | S_IWUSR) else {
            throw LensFailure.unsafeReceipt("\(label) permissions are not 0600")
        }
        guard metadata.st_nlink == 1 else {
            throw LensFailure.unsafeReceipt("\(label) has unexpected hard links")
        }
        guard metadata.st_size >= 0, metadata.st_size <= maximumBytes else {
            throw LensFailure.unsafeReceipt("\(label) exceeds the size bound")
        }
        return SecureFileIdentity(metadata)
    }
}

struct ScanDirectory: Sendable {
    let appRoot: URL
    let url: URL

    static func make(baseURL: URL? = nil) throws -> ScanDirectory {
        let suppliedBase = baseURL ?? FileManager.default.temporaryDirectory
        guard suppliedBase.isFileURL else {
            throw LensFailure.temporaryDirectory("the temporary root is not a file URL")
        }
        guard let canonicalBasePath = canonicalPath(suppliedBase.path) else {
            throw LensFailure.temporaryDirectory("the temporary root cannot be resolved")
        }
        let canonicalBase = URL(fileURLWithPath: canonicalBasePath, isDirectory: true)
        try requireSafeDirectory(canonicalBase, exactMode: nil, label: "temporary root")

        let root = canonicalBase.appendingPathComponent(
            "love.chillspace.kingdom-lens.\(Darwin.geteuid())",
            isDirectory: true
        )
        if Darwin.mkdir(root.path, mode_t(0o700)) != 0, errno != EEXIST {
            throw LensFailure.temporaryDirectory(
                "the app directory could not be created (\(errnoText()))"
            )
        }
        try requireSafeDirectory(root, exactMode: 0o700, label: "app directory")

        var template = Array(
            root.appendingPathComponent("scan.XXXXXX", isDirectory: true)
                .path
                .utf8CString
        )
        let createdPath: String? = template.withUnsafeMutableBufferPointer { bytes in
            guard let baseAddress = bytes.baseAddress,
                  let result = Darwin.mkdtemp(baseAddress)
            else {
                return nil
            }
            return String(cString: result)
        }
        guard let createdPath else {
            throw LensFailure.temporaryDirectory(
                "a private scan directory could not be created (\(errnoText()))"
            )
        }
        let scan = URL(fileURLWithPath: createdPath, isDirectory: true)
        do {
            try requireSafeDirectory(scan, exactMode: 0o700, label: "scan directory")
        } catch {
            try? FileManager.default.removeItem(at: scan)
            throw error
        }
        return ScanDirectory(appRoot: root, url: scan)
    }

    func validate() throws {
        guard url.deletingLastPathComponent().path == appRoot.path,
              url.lastPathComponent.hasPrefix("scan.")
        else {
            throw LensFailure.temporaryDirectory("the scan directory left its fixed app root")
        }
        try Self.requireSafeDirectory(url, exactMode: 0o700, label: "scan directory")
    }

    func remove() {
        guard url.deletingLastPathComponent().path == appRoot.path,
              url.lastPathComponent.hasPrefix("scan.")
        else {
            return
        }
        try? FileManager.default.removeItem(at: url)
    }

    private static func requireSafeDirectory(
        _ directory: URL,
        exactMode: mode_t?,
        label: String
    ) throws {
        var metadata = stat()
        guard Darwin.lstat(directory.path, &metadata) == 0 else {
            throw LensFailure.temporaryDirectory("\(label) is missing (\(errnoText()))")
        }
        guard (metadata.st_mode & S_IFMT) == S_IFDIR,
              metadata.st_uid == Darwin.geteuid()
        else {
            throw LensFailure.temporaryDirectory("\(label) is not a user-owned directory")
        }
        if let exactMode {
            guard metadata.st_mode & mode_t(0o777) == exactMode else {
                throw LensFailure.temporaryDirectory("\(label) permissions are not 0700")
            }
        }
        guard let resolved = canonicalPath(directory.path),
              resolved == directory.path
        else {
            throw LensFailure.temporaryDirectory("\(label) is not canonical or contains a link")
        }
    }
}

func canonicalPath(_ path: String) -> String? {
    guard let result = Darwin.realpath(path, nil) else {
        return nil
    }
    defer { Darwin.free(result) }
    return String(cString: result)
}

func errnoText(_ value: Int32 = errno) -> String {
    String(cString: Darwin.strerror(value))
}
