import Foundation

struct Room: Codable, Identifiable, Sendable {
    let id: UUID
    var name: String
    var isPublic: Bool
    let ownerId: UUID
    var participants: [Participant]
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id, name, participants
        case isPublic = "is_public"
        case ownerId = "owner_id"
        case createdAt = "created_at"
    }

    struct Participant: Codable, Identifiable, Sendable {
        let id: UUID
        let displayName: String
        let communicationStyle: CommunicationStyle

        enum CodingKeys: String, CodingKey {
            case id
            case displayName = "display_name"
            case communicationStyle = "communication_style"
        }
    }
}
