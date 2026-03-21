import Foundation

struct Transcript: Codable, Identifiable, Sendable {
    let id: UUID
    let roomName: String
    let messageCount: Int
    let slug: String
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id, slug
        case roomName = "room_name"
        case messageCount = "message_count"
        case createdAt = "created_at"
    }

    var shareURL: URL? {
        URL(string: "\(AppConfig.apiBaseURL)/transcripts/public/\(slug)")
    }
}

struct TranscriptDetail: Codable, Sendable {
    let transcript: Transcript
    let messages: [ChatMessage]
}
