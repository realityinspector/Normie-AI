import SwiftUI

struct TranscriptDetailView: View {
    let transcriptId: UUID
    @State private var detail: TranscriptDetail?
    @State private var isLoading = true
    @State private var errorMessage: String?

    var body: some View {
        Group {
            if isLoading {
                ProgressView()
            } else if let loadedDetail = detail {
                TranscriptMessageList(detail: loadedDetail)
            } else if let errorMessage {
                ContentUnavailableView("Error", systemImage: "exclamationmark.triangle", description: Text(errorMessage))
            }
        }
        .navigationTitle(detail?.transcript.roomName ?? "Transcript")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if let url = detail?.transcript.shareURL {
                ToolbarItem(placement: .topBarTrailing) {
                    ShareLink(item: url) {
                        Image(systemName: "square.and.arrow.up")
                    }
                }
            }
        }
        .task {
            await load()
        }
    }

    private func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            detail = try await APIClient.shared.request(.getTranscript(id: transcriptId))
        } catch {
            self.errorMessage = error.localizedDescription
        }
    }
}

private struct TranscriptMessageList: View {
    let detail: TranscriptDetail

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 12) {
                ForEach(Array(detail.messages.enumerated()), id: \.offset) { _, message in
                VStack(alignment: .leading, spacing: 8) {
                    Text(message.senderName)
                        .font(.caption.bold())
                        .foregroundStyle(.secondary)

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Original")
                            .font(.caption2)
                            .foregroundStyle(.tertiary)
                        Text(message.originalText)
                            .font(.body)
                    }

                    if let translated = message.translatedText {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Translated")
                                .font(.caption2)
                                .foregroundStyle(.tertiary)
                            Text(translated)
                                .font(.body)
                                .foregroundStyle(.accent)
                        }
                    }

                    Text(message.createdAt, style: .time)
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                }
                .padding(.vertical, 4)
                .padding(.horizontal)
                }
            }
            .padding(.vertical)
        }
    }
}
