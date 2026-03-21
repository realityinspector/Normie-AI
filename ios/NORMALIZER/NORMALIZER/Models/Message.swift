import Foundation

struct ChatMessage: Codable, Identifiable, Sendable {
    let id: UUID
    let roomId: UUID
    let senderId: UUID
    let senderName: String
    let originalText: String
    let translatedText: String?
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case roomId = "room_id"
        case senderId = "sender_id"
        case senderName = "sender_name"
        case originalText = "original_text"
        case translatedText = "translated_text"
        case createdAt = "created_at"
    }
}

// WebSocket incoming message types
enum WSIncoming: Sendable {
    case message(ChatMessage)
    case userJoined(name: String)
    case userLeft(userId: String)
    case error(String)
}
