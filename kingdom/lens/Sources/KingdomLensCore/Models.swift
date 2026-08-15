import Foundation

public struct LensAnalysis: Sendable {
    public let pathDocument: KingdomPathDocument
    public let pathRecord: KingdomPathRecord
    public let indexDocument: KingdomIndexDocument?
    public let repository: KingdomRepositoryRecord?
    public let indexNotice: String?

    init(
        pathDocument: KingdomPathDocument,
        pathRecord: KingdomPathRecord,
        indexDocument: KingdomIndexDocument?,
        repository: KingdomRepositoryRecord?,
        indexNotice: String?
    ) {
        self.pathDocument = pathDocument
        self.pathRecord = pathRecord
        self.indexDocument = indexDocument
        self.repository = repository
        self.indexNotice = indexNotice
    }
}

public struct KingdomPathDocument: Decodable, Sendable {
    public let schema: String
    public let classifier: String
    public let host: KingdomPathHost
    public let records: [KingdomPathRecord]
    public let nonClaims: [String]
    public let classificationDigest: String

    enum CodingKeys: String, CodingKey {
        case schema
        case classifier
        case host
        case records
        case nonClaims = "non_claims"
        case classificationDigest = "classification_digest"
    }
}

public struct KingdomPathHost: Decodable, Sendable {
    public let kernel: String
    public let machine: String
    public let hostnameIncluded: Bool

    enum CodingKeys: String, CodingKey {
        case kernel
        case machine
        case hostnameIncluded = "hostname_included"
    }
}

public struct KingdomPathRecord: Decodable, Sendable {
    public let requestedPath: String
    public let lexicalPath: String
    public let resolvedPath: String
    public let resolution: PathResolution
    public let workspace: PathWorkspaceEvidence
    public let domain: PathDomainEvidence
    public let locality: PathLocalityEvidence
    public let metadata: PathMetadataEvidence
    public let volume: PathVolumeEvidence
    public let processAccess: PathProcessAccessEvidence
    public let authority: PathAuthorityEvidence
    public let recordDigest: String

    enum CodingKeys: String, CodingKey {
        case requestedPath = "requested_path"
        case lexicalPath = "lexical_path"
        case resolvedPath = "resolved_path"
        case resolution
        case workspace
        case domain
        case locality
        case metadata
        case volume
        case processAccess = "process_access"
        case authority
        case recordDigest = "record_digest"
    }
}

public struct PathResolution: Decodable, Sendable {
    public let complete: Bool
    public let error: String?
    public let deepestExistingAncestor: String
    public let missingSuffix: [String]
    public let lexicalExists: Bool
    public let targetExists: Bool
    public let symlinkComponents: Int
    public let finalComponentIsSymlink: Bool

    enum CodingKeys: String, CodingKey {
        case complete
        case error
        case deepestExistingAncestor = "deepest_existing_ancestor"
        case missingSuffix = "missing_suffix"
        case lexicalExists = "lexical_exists"
        case targetExists = "target_exists"
        case symlinkComponents = "symlink_components"
        case finalComponentIsSymlink = "final_component_is_symlink"
    }
}

public struct PathWorkspaceEvidence: Decodable, Sendable {
    public let relation: String
    public let lexicalRoots: [String]
    public let resolvedRoots: [String]

    enum CodingKeys: String, CodingKey {
        case relation
        case lexicalRoots = "lexical_roots"
        case resolvedRoots = "resolved_roots"
    }
}

public struct PathDomainEvidence: Decodable, Sendable {
    public let value: String
    public let truth: String
}

public struct PathLocalityEvidence: Decodable, Sendable {
    public let value: String
    public let truth: String
    public let materialization: String
}

public struct PathMetadataEvidence: Decodable, Sendable {
    public let source: String
    public let fileType: String
    public let mode: String?
    public let uid: UInt32?
    public let gid: UInt32?
    public let device: UInt64?
    public let inode: UInt64?
    public let flags: UInt64?
    public let xattrs: PathExtendedAttributeEvidence

    enum CodingKeys: String, CodingKey {
        case source
        case fileType = "file_type"
        case mode
        case uid
        case gid
        case device
        case inode
        case flags
        case xattrs
    }
}

public struct PathExtendedAttributeEvidence: Decodable, Sendable {
    public let truth: String
    public let names: [String]
    public let unreportedCount: Int

    enum CodingKeys: String, CodingKey {
        case truth
        case names
        case unreportedCount = "unreported_count"
    }
}

public struct PathVolumeEvidence: Decodable, Sendable {
    public let readOnly: Bool?
    public let truth: String

    enum CodingKeys: String, CodingKey {
        case readOnly = "read_only"
        case truth
    }
}

public struct PathProcessAccessEvidence: Decodable, Sendable {
    public let targetReadable: Bool
    public let targetWritable: Bool
    public let targetExecutable: Bool
    public let ancestorWritable: Bool
    public let ancestorExecutable: Bool
    public let truth: String

    enum CodingKeys: String, CodingKey {
        case targetReadable = "target_readable"
        case targetWritable = "target_writable"
        case targetExecutable = "target_executable"
        case ancestorWritable = "ancestor_writable"
        case ancestorExecutable = "ancestor_executable"
        case truth
    }
}

public struct PathAuthorityEvidence: Decodable, Sendable {
    public let effective: String
    public let tcc: String
    public let codexSandbox: String
    public let acl: String
    public let reason: String

    enum CodingKeys: String, CodingKey {
        case effective
        case tcc
        case codexSandbox = "codex_sandbox"
        case acl
        case reason
    }
}

public struct KingdomIndexDocument: Decodable, Sendable {
    public let schema: String
    public let compiler: String
    public let inputDigest: String
    public let repositories: [KingdomRepositoryRecord]
    public let ambiguityGroups: [RepositoryAmbiguityGroup]
    public let nonClaims: [String]
    public let indexDigest: String

    enum CodingKeys: String, CodingKey {
        case schema
        case compiler
        case inputDigest = "input_digest"
        case repositories
        case ambiguityGroups = "ambiguity_groups"
        case nonClaims = "non_claims"
        case indexDigest = "index_digest"
    }
}

public struct KingdomRepositoryRecord: Decodable, Sendable {
    public let repositoryID: String
    public let canonical: Bool
    public let worktreePath: String
    public let pathIdentity: RepositoryPathIdentity
    public let git: RepositoryGitEvidence
    public let workingTree: RepositoryWorkingTreeEvidence
    public let manifest: RepositoryManifestEvidence
    public let instructions: [RepositoryInstructionEvidence]
    public let repositoryDigest: String

    enum CodingKeys: String, CodingKey {
        case repositoryID = "repository_id"
        case canonical
        case worktreePath = "worktree_path"
        case pathIdentity = "path_identity"
        case git
        case workingTree = "working_tree"
        case manifest
        case instructions
        case repositoryDigest = "repository_digest"
    }
}

public struct RepositoryPathIdentity: Decodable, Sendable {
    public let device: UInt64
    public let inode: UInt64
}

public struct RepositoryGitEvidence: Decodable, Sendable {
    public let directory: String
    public let commonDirectory: String
    public let objectsDirectory: String
    public let objectFormat: String
    public let head: String
    public let headTree: String
    public let ref: String
    public let shallow: Bool
    public let rootCommits: [String]
    public let lineageComplete: Bool
    public let lineageDigest: String

    enum CodingKeys: String, CodingKey {
        case directory
        case commonDirectory = "common_directory"
        case objectsDirectory = "objects_directory"
        case objectFormat = "object_format"
        case head
        case headTree = "head_tree"
        case ref
        case shallow
        case rootCommits = "root_commits"
        case lineageComplete = "lineage_complete"
        case lineageDigest = "lineage_digest"
    }
}

public struct RepositoryWorkingTreeEvidence: Decodable, Sendable {
    public let state: String
    public let trackedContent: String
    public let untrackedContent: String
    public let stagedRecords: Int
    public let stagedDigest: String

    enum CodingKeys: String, CodingKey {
        case state
        case trackedContent = "tracked_content"
        case untrackedContent = "untracked_content"
        case stagedRecords = "staged_records"
        case stagedDigest = "staged_digest"
    }
}

public struct RepositoryManifestEvidence: Decodable, Sendable {
    public let path: String
    public let sha256: String
    public let bytes: Int
    public let fields: KingdomManifestFields
}

public struct KingdomManifestFields: Decodable, Sendable {
    public let name: String
    public let purpose: String
    public let kind: String
    public let domain: String
    public let layer: String
    public let ownerSister: String
    public let state: String
    public let dependsOn: [String]
    public let adopts: [String]
    public let doorsCount: Int

    enum CodingKeys: String, CodingKey {
        case name
        case purpose
        case kind
        case domain
        case layer
        case ownerSister = "owner_sister"
        case state
        case dependsOn = "depends_on"
        case adopts
        case doorsCount = "doors_count"
    }
}

public struct RepositoryInstructionEvidence: Decodable, Sendable {
    public let path: String
    public let sha256: String
    public let bytes: Int
}

public struct RepositoryAmbiguityGroup: Decodable, Sendable {
    public let groupID: String
    public let reasons: [String]
    public let repositoryIDs: [String]
    public let canonicalRepositoryID: String

    enum CodingKeys: String, CodingKey {
        case groupID = "group_id"
        case reasons
        case repositoryIDs = "repository_ids"
        case canonicalRepositoryID = "canonical_repository_id"
    }
}

extension KingdomPathDocument {
    func validated(forLexicalPath lexicalPath: String) throws -> KingdomPathRecord {
        guard schema == "kingdom.path/v1", classifier == "darwin-path/1" else {
            throw LensFailure.invalidReceipt("the path schema or classifier is unsupported")
        }
        guard host.hostnameIncluded == false else {
            throw LensFailure.invalidReceipt("the path receipt unexpectedly includes a hostname")
        }
        guard records.count == 1, let record = records.first else {
            throw LensFailure.invalidReceipt("exactly one path record is required")
        }
        guard record.requestedPath == lexicalPath, record.lexicalPath == lexicalPath else {
            throw LensFailure.invalidReceipt("the path receipt does not match the selected lexical path")
        }
        guard Self.isAbsoluteCanonical(record.resolvedPath),
              Self.isAbsoluteCanonical(record.resolution.deepestExistingAncestor),
              Self.isDigest(record.recordDigest),
              Self.isDigest(classificationDigest)
        else {
            throw LensFailure.invalidReceipt("the path receipt contains an invalid path or digest")
        }
        guard record.resolution.complete == record.resolution.targetExists,
              record.resolution.symlinkComponents >= 0,
              record.metadata.xattrs.unreportedCount >= 0
        else {
            throw LensFailure.invalidReceipt("the path receipt contains inconsistent resolution evidence")
        }
        let authorityValues = [
            record.authority.effective,
            record.authority.tcc,
            record.authority.codexSandbox,
            record.authority.acl,
        ]
        guard authorityValues.allSatisfy({ $0 == "unknown" }) else {
            throw LensFailure.invalidReceipt("the path receipt overclaims effective authority")
        }
        guard ["inferred", "unknown"].contains(record.domain.truth),
              ["inferred", "unknown"].contains(record.locality.truth),
              ["observed", "unknown"].contains(record.volume.truth),
              record.processAccess.truth == "observed-for-current-process"
        else {
            throw LensFailure.invalidReceipt("the path receipt contains an unsupported truth label")
        }
        return record
    }

    static func isAbsoluteCanonical(_ path: String) -> Bool {
        guard !path.isEmpty,
              path.hasPrefix("/"),
              path.precomposedStringWithCanonicalMapping == path,
              path == "/" || (!path.hasSuffix("/") && !path.contains("//"))
        else {
            return false
        }
        let components = path.split(separator: "/", omittingEmptySubsequences: true)
        guard components.allSatisfy({ $0 != "." && $0 != ".." }) else {
            return false
        }
        return !path.unicodeScalars.contains(where: {
            switch $0.properties.generalCategory {
            case .control, .format, .surrogate, .lineSeparator, .paragraphSeparator:
                return true
            default:
                return $0.value == 127
            }
        })
    }

    static func isDigest(_ value: String) -> Bool {
        value.utf8.count == 64 && value.utf8.allSatisfy {
            ($0 >= 48 && $0 <= 57) || ($0 >= 97 && $0 <= 102)
        }
    }
}

extension KingdomIndexDocument {
    func validated(forCanonicalDirectory directory: String) throws -> KingdomRepositoryRecord {
        guard schema == "kingdom.index/v1", compiler == "kingdom-index/1" else {
            throw LensFailure.invalidReceipt("the index schema or compiler is unsupported")
        }
        guard repositories.count == 1, let repository = repositories.first else {
            throw LensFailure.invalidReceipt("exactly one repository record is required")
        }
        guard repository.canonical, repository.worktreePath == directory else {
            throw LensFailure.invalidReceipt("the index does not identify the selected canonical directory")
        }
        guard KingdomPathDocument.isDigest(inputDigest),
              KingdomPathDocument.isDigest(indexDigest),
              KingdomPathDocument.isDigest(repository.repositoryDigest),
              KingdomPathDocument.isAbsoluteCanonical(repository.worktreePath),
              KingdomPathDocument.isAbsoluteCanonical(repository.git.directory),
              KingdomPathDocument.isAbsoluteCanonical(repository.git.commonDirectory),
              KingdomPathDocument.isAbsoluteCanonical(repository.git.objectsDirectory)
        else {
            throw LensFailure.invalidReceipt("the index contains an invalid path or digest")
        }
        guard repository.workingTree.state == "dirty"
                || repository.workingTree.state == "unknown",
              repository.workingTree.trackedContent == "not-inspected",
              repository.workingTree.untrackedContent == "not-inspected"
        else {
            throw LensFailure.invalidReceipt("the index overclaims working-tree knowledge")
        }
        return repository
    }
}
