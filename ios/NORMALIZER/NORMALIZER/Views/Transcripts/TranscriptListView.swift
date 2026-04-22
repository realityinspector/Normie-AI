import SwiftUI

struct TranscriptListView: View {
    @State private var vm = TranscriptListViewModel()

    var body: some View {
        Group {
            if vm.isLoading && vm.transcripts.isEmpty {
                ProgressView()
            } else if vm.transcripts.isEmpty {
                ContentUnavailableView(
                    "No Transcripts",
                    systemImage: "doc.text",
                    description: Text("Saved conversation transcripts will appear here")
                )
            } else {
                List(vm.transcripts) { transcript in
                    NavigationLink(value: transcript.id) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(transcript.roomName)
                                .font(.headline)
                                .accessibilityIdentifier("transcript.row.\(transcript.roomName)")
                            HStack {
                                Label("\(transcript.messageCount) messages", systemImage: "message")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                Spacer()
                                Text(transcript.createdAt, style: .date)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .padding(.vertical, 4)
                    }
                }
            }
        }
        .navigationTitle("Transcripts")
        .navigationDestination(for: UUID.self) { transcriptId in
            TranscriptDetailView(transcriptId: transcriptId)
        }
        .task {
            await vm.load()
        }
        .refreshable {
            await vm.load()
        }
    }
}
