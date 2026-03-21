import Foundation
import Observation
import UIKit

@Observable
@MainActor
final class ScreenshotTranslateViewModel {
    var selectedImage: UIImage?
    var direction: TranslationDirection = .autisticToNeurotypical
    var template: TranslationTemplate = .none
    var result: TranslateImageResponse?
    var isLoading = false
    var error: String?
    var showPhotoPicker = false
    var showCamera = false

    func translate() async {
        guard let image = selectedImage,
              let imageData = image.jpegData(compressionQuality: 0.8) else { return }

        isLoading = true
        error = nil
        defer { isLoading = false }

        var fields: [String: String] = [
            "direction": direction.rawValue,
        ]
        if template != .none && template != .custom {
            fields["template"] = template.rawValue
        }

        do {
            result = try await APIClient.shared.upload(
                path: "/translate/image",
                imageData: imageData,
                mimeType: "image/jpeg",
                fields: fields
            )
        } catch {
            self.error = error.localizedDescription
        }
    }

    func clear() {
        selectedImage = nil
        result = nil
        error = nil
    }
}
