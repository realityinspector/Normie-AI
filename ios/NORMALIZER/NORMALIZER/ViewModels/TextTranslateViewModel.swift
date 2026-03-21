import Foundation
import Observation

@Observable
@MainActor
final class TextTranslateViewModel {
    var inputText = ""
    var direction: TranslationDirection = .autisticToNeurotypical
    var template: TranslationTemplate = .none
    var customPrompt = ""
    var result: TranslateTextResponse?
    var isLoading = false
    var error: String?

    func translate() async {
        guard !inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }

        isLoading = true
        error = nil
        defer { isLoading = false }

        let request = TranslateTextRequest(
            text: inputText,
            direction: direction,
            template: template == .custom ? nil : (template == .none ? nil : template.rawValue),
            customPrompt: template == .custom ? customPrompt : nil
        )

        do {
            result = try await APIClient.shared.request(.translateText(request))
        } catch {
            self.error = error.localizedDescription
        }
    }

    func clear() {
        inputText = ""
        result = nil
        error = nil
    }
}
