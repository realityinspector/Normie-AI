import Foundation

enum TranslationDirection: String, Codable, CaseIterable, Sendable {
    case autisticToNeurotypical = "autistic_to_neurotypical"
    case neurotypicalToAutistic = "neurotypical_to_autistic"

    var displayName: String {
        switch self {
        case .autisticToNeurotypical: "Autist → Normie"
        case .neurotypicalToAutistic: "Normie → Autist"
        }
    }
}

enum TranslationTemplate: String, CaseIterable, Sendable {
    case none = ""
    case casual
    case professional
    case emotional
    case technical
    case conflict
    case custom

    var displayName: String {
        switch self {
        case .none: "Default"
        case .casual: "Casual"
        case .professional: "Professional"
        case .emotional: "Emotional"
        case .technical: "Technical"
        case .conflict: "Conflict"
        case .custom: "Custom"
        }
    }
}

struct TranslateTextRequest: Codable, Sendable {
    let text: String
    let direction: TranslationDirection
    let template: String?
    let customPrompt: String?

    enum CodingKeys: String, CodingKey {
        case text, direction, template
        case customPrompt = "custom_prompt"
    }
}

struct TranslateTextResponse: Codable, Sendable {
    let originalText: String
    let translatedText: String
    let direction: TranslationDirection
    let creditsRemaining: Int

    enum CodingKeys: String, CodingKey {
        case direction
        case originalText = "original_text"
        case translatedText = "translated_text"
        case creditsRemaining = "credits_remaining"
    }
}

struct TranslateImageResponse: Codable, Sendable {
    let extractedText: String
    let translatedText: String
    let direction: TranslationDirection
    let creditsRemaining: Int

    enum CodingKeys: String, CodingKey {
        case direction
        case extractedText = "extracted_text"
        case translatedText = "translated_text"
        case creditsRemaining = "credits_remaining"
    }
}
