// swift-tools-version: 6.1

import PackageDescription

let package = Package(
    name: "KingdomLens",
    platforms: [
        .macOS(.v13),
    ],
    products: [
        .library(
            name: "KingdomLensCore",
            targets: ["KingdomLensCore"]
        ),
        .executable(
            name: "KingdomLens",
            targets: ["KingdomLens"]
        ),
        .executable(
            name: "KingdomLensSelfTest",
            targets: ["KingdomLensSelfTest"]
        ),
    ],
    dependencies: [],
    targets: [
        .target(
            name: "KingdomLensCore"
        ),
        .executableTarget(
            name: "KingdomLens",
            dependencies: ["KingdomLensCore"]
        ),
        .executableTarget(
            name: "KingdomLensSelfTest",
            dependencies: ["KingdomLensCore"],
            path: "Tests/KingdomLensCoreTests"
        ),
    ]
)
