import SwiftUI

struct TranslationResultView: View {
    let original: String
    let translated: String
    let creditsRemaining: Int

    @State private var copied = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Translation")
                    .font(.headline)
                Spacer()
                Text("\(creditsRemaining) credits left")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Text(translated)
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.accentColor.opacity(0.1))
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .accessibilityIdentifier("translate.result")

            HStack(spacing: 12) {
                Button {
                    UIPasteboard.general.string = translated
                    copied = true
                    Task {
                        try? await Task.sleep(for: .seconds(2))
                        copied = false
                    }
                } label: {
                    Label(copied ? "Copied!" : "Copy", systemImage: copied ? "checkmark" : "doc.on.doc")
                        .font(.subheadline)
                }

                ShareLink(item: translated) {
                    Label("Share", systemImage: "square.and.arrow.up")
                        .font(.subheadline)
                }
            }
        }
        .padding()
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}
