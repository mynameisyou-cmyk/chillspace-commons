import SwiftUI

@main
@MainActor
struct KingdomLensApp: App {
    @StateObject private var store = LensStore()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(store)
                .frame(minWidth: 980, minHeight: 680)
        }
        .defaultSize(width: 1180, height: 780)
        .windowStyle(.hiddenTitleBar)
        .windowToolbarStyle(.unifiedCompact)
        .commands {
            CommandGroup(replacing: .newItem) {
                Button("Choose a Path…") {
                    store.choosePath()
                }
                .keyboardShortcut("o")
            }

            CommandMenu("Lens") {
                Button("Scan Again") {
                    store.rescan()
                }
                .keyboardShortcut("r")
                .disabled(store.selectedURL == nil || store.isScanning)

                if store.isScanning {
                    Button("Cancel Scan") {
                        store.cancelScan()
                    }
                    .keyboardShortcut(.cancelAction)
                }
            }
        }
    }
}

