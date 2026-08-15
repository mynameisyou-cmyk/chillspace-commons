/// Shell quoting is for copyable display text only. KINGDOM processes are
/// always launched with an argv vector and never through a shell.
public enum ShellQuote {
    public static func single(_ value: String) -> String {
        "'" + value.replacingOccurrences(of: "'", with: "'\\''") + "'"
    }
}
