import SwiftUI

struct LaunchScreen: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "brain.head.profile")
                .font(.system(size: 80))
                .foregroundStyle(
                    LinearGradient(
                        colors: [Color(red: 0.39, green: 0.40, blue: 0.95),
                                 Color(red: 0.55, green: 0.36, blue: 0.96)],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
            BrandWordmark(size: 28)
            ProgressView()
        }
    }
}

/// Reusable NORMAL-AI-ZER wordmark with highlighted AI
struct BrandWordmark: View {
    var size: CGFloat = 36

    private var indigo: Color { Color(red: 0.12, green: 0.11, blue: 0.29) }

    var body: some View {
        HStack(spacing: 0) {
            Text("NORMAL")
                .font(.system(size: size, weight: .black))
                .foregroundStyle(indigo)
            Text("AI")
                .font(.system(size: size, weight: .black))
                .foregroundStyle(
                    LinearGradient(
                        colors: [Color(red: 0.39, green: 0.40, blue: 0.95),
                                 Color(red: 0.55, green: 0.36, blue: 0.96)],
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                )
            Text("ZER")
                .font(.system(size: size, weight: .black))
                .foregroundStyle(indigo)
        }
    }
}
