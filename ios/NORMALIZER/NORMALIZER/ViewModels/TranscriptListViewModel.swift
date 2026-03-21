import Foundation
import Observation

@Observable
@MainActor
final class TranscriptListViewModel {
    var transcripts: [Transcript] = []
    var isLoading = false
    var error: String?

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            transcripts = try await APIClient.shared.request(.listTranscripts)
        } catch {
            self.error = error.localizedDescription
        }
    }
}
