import Foundation

/// A bounded failure from the local KINGDOM evidence pipeline.
public enum LensFailure: Error, LocalizedError, Sendable {
    case invalidExecutable(String)
    case invalidInput(String)
    case temporaryDirectory(String)
    case processLaunch(stage: String, reason: String)
    case commandFailed(stage: String, status: Int32, detail: String)
    case commandTimedOut(stage: String)
    case outputLimitExceeded(stage: String)
    case unsafeReceipt(String)
    case unstableReceipt(String)
    case invalidReceipt(String)

    public var errorDescription: String? {
        switch self {
        case .invalidExecutable(let reason):
            return "The KINGDOM executable is unavailable or unsafe: \(reason)"
        case .invalidInput(let reason):
            return "The selected path cannot be analyzed: \(reason)"
        case .temporaryDirectory(let reason):
            return "A private Lens workspace could not be prepared: \(reason)"
        case .processLaunch(let stage, let reason):
            return "\(stage) could not start: \(reason)"
        case .commandFailed(let stage, let status, let detail):
            let suffix = detail.isEmpty ? "" : " \(detail)"
            return "\(stage) failed with status \(status).\(suffix)"
        case .commandTimedOut(let stage):
            return "\(stage) exceeded its bounded running time."
        case .outputLimitExceeded(let stage):
            return "\(stage) exceeded its bounded output size."
        case .unsafeReceipt(let reason):
            return "KINGDOM produced an unsafe receipt: \(reason)"
        case .unstableReceipt(let reason):
            return "KINGDOM evidence changed while it was being verified: \(reason)"
        case .invalidReceipt(let reason):
            return "KINGDOM produced unsupported evidence: \(reason)"
        }
    }
}
