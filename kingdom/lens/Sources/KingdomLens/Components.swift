import SwiftUI

enum LensPalette {
    static let ink = Color(red: 0.08, green: 0.02, blue: 0.12)
    static let plum = Color(red: 0.18, green: 0.04, blue: 0.22)
    static let hotPink = Color(red: 1.00, green: 0.31, blue: 0.85)
    static let sun = Color(red: 1.00, green: 0.82, blue: 0.40)
    static let mint = Color(red: 0.02, green: 0.84, blue: 0.63)
    static let sky = Color(red: 0.32, green: 0.72, blue: 1.00)
    static let lilac = Color(red: 0.73, green: 0.52, blue: 1.00)
    static let paper = Color.white.opacity(0.94)
    static let quiet = Color.white.opacity(0.64)
}

struct CosmicBackground: View {
    var body: some View {
        ZStack {
            LinearGradient(
                colors: [LensPalette.ink, LensPalette.plum, Color.black],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            Circle()
                .fill(LensPalette.hotPink.opacity(0.18))
                .frame(width: 540, height: 540)
                .blur(radius: 110)
                .offset(x: -430, y: -290)

            Circle()
                .fill(LensPalette.mint.opacity(0.13))
                .frame(width: 500, height: 500)
                .blur(radius: 120)
                .offset(x: 460, y: 320)

            Circle()
                .fill(LensPalette.sun.opacity(0.08))
                .frame(width: 380, height: 380)
                .blur(radius: 100)
                .offset(x: 420, y: -330)
        }
        .ignoresSafeArea()
    }
}

struct LensCard<Content: View>: View {
    let icon: String
    let eyebrow: String
    let title: String
    let tint: Color
    let content: Content

    init(
        icon: String,
        eyebrow: String,
        title: String,
        tint: Color,
        @ViewBuilder content: () -> Content
    ) {
        self.icon = icon
        self.eyebrow = eyebrow
        self.title = title
        self.tint = tint
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(spacing: 12) {
                Image(systemName: icon)
                    .font(.system(size: 18, weight: .bold))
                    .foregroundStyle(Color.black.opacity(0.76))
                    .frame(width: 38, height: 38)
                    .background(tint, in: RoundedRectangle(cornerRadius: 12))
                    .accessibilityHidden(true)

                VStack(alignment: .leading, spacing: 2) {
                    Text(eyebrow.uppercased())
                        .font(.system(size: 10, weight: .black, design: .rounded))
                        .tracking(1.8)
                        .foregroundStyle(tint)
                    Text(title)
                        .font(.system(size: 20, weight: .bold, design: .rounded))
                        .foregroundStyle(LensPalette.paper)
                }

                Spacer(minLength: 0)
            }

            content
        }
        .padding(20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 24))
        .overlay {
            RoundedRectangle(cornerRadius: 24)
                .stroke(
                    LinearGradient(
                        colors: [tint.opacity(0.55), Color.white.opacity(0.08)],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    ),
                    lineWidth: 1
                )
        }
        .shadow(color: tint.opacity(0.09), radius: 22, y: 10)
    }
}

struct EvidenceRow: View {
    let label: String
    let value: String
    var symbol: String?
    var tint: Color = LensPalette.quiet
    var monospaced = false

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(label.uppercased())
                .font(.system(size: 9, weight: .bold, design: .rounded))
                .tracking(1.2)
                .foregroundStyle(LensPalette.quiet)

            HStack(alignment: .firstTextBaseline, spacing: 7) {
                if let symbol {
                    Image(systemName: symbol)
                        .foregroundStyle(tint)
                        .accessibilityHidden(true)
                }
                Text(value)
                    .font(
                        monospaced
                            ? .system(size: 12, weight: .medium, design: .monospaced)
                            : .system(size: 13, weight: .semibold, design: .rounded)
                    )
                    .foregroundStyle(LensPalette.paper)
                    .lineLimit(nil)
                    .textSelection(.enabled)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
    }
}

struct TruthBadge: View {
    let label: String
    let value: String

    private var normalized: String {
        value.lowercased()
    }

    private var tint: Color {
        if normalized.contains("unknown") || normalized.contains("not-inspected") {
            return LensPalette.sun
        }
        if normalized.contains("observed") || normalized == "true" || normalized == "verified" {
            return LensPalette.mint
        }
        if normalized.contains("inferred") {
            return LensPalette.lilac
        }
        return LensPalette.sky
    }

    private var symbol: String {
        if normalized.contains("unknown") || normalized.contains("not-inspected") {
            return "questionmark.circle.fill"
        }
        if normalized.contains("observed") || normalized == "true" || normalized == "verified" {
            return "checkmark.seal.fill"
        }
        if normalized.contains("inferred") {
            return "sparkles"
        }
        return "circle.fill"
    }

    var body: some View {
        HStack(spacing: 7) {
            Image(systemName: symbol)
                .foregroundStyle(tint)
                .accessibilityHidden(true)
            VStack(alignment: .leading, spacing: 1) {
                Text(label.uppercased())
                    .font(.system(size: 8, weight: .black, design: .rounded))
                    .tracking(0.8)
                    .foregroundStyle(LensPalette.quiet)
                Text(value)
                    .font(.system(size: 11, weight: .bold, design: .rounded))
                    .foregroundStyle(LensPalette.paper)
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(tint.opacity(0.11), in: RoundedRectangle(cornerRadius: 11))
        .overlay {
            RoundedRectangle(cornerRadius: 11)
                .stroke(tint.opacity(0.32), lineWidth: 1)
        }
        .accessibilityElement(children: .combine)
    }
}

struct Hairline: View {
    var body: some View {
        Rectangle()
            .fill(Color.white.opacity(0.10))
            .frame(height: 1)
    }
}

struct LensButtonStyle: ButtonStyle {
    let tint: Color
    var prominent = false

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 12, weight: .bold, design: .rounded))
            .foregroundStyle(prominent ? Color.black.opacity(0.82) : LensPalette.paper)
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .frame(maxWidth: prominent ? .infinity : nil)
            .background(
                prominent ? tint.opacity(configuration.isPressed ? 0.72 : 1) :
                    Color.white.opacity(configuration.isPressed ? 0.16 : 0.09),
                in: RoundedRectangle(cornerRadius: 12)
            )
            .overlay {
                if !prominent {
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(tint.opacity(0.35), lineWidth: 1)
                }
            }
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
    }
}

struct StatusPip: View {
    let phase: LensPhase

    private var tint: Color {
        switch phase {
        case .idle:
            return LensPalette.sky
        case .scanning:
            return LensPalette.sun
        case .ready:
            return LensPalette.mint
        case .failed:
            return LensPalette.hotPink
        }
    }

    private var label: String {
        switch phase {
        case .idle:
            return "Ready"
        case .scanning:
            return "Reading evidence"
        case .ready:
            return "Receipt verified"
        case .failed:
            return "Needs attention"
        }
    }

    var body: some View {
        HStack(spacing: 7) {
            if phase == .scanning {
                ProgressView()
                    .controlSize(.small)
                    .tint(tint)
            } else {
                Circle()
                    .fill(tint)
                    .frame(width: 7, height: 7)
                    .shadow(color: tint, radius: 5)
            }
            Text(label.uppercased())
                .font(.system(size: 9, weight: .black, design: .rounded))
                .tracking(1.2)
                .foregroundStyle(tint)
        }
        .accessibilityElement(children: .combine)
    }
}
