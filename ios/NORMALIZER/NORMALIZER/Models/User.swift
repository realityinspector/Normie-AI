import Foundation

enum CommunicationStyle: String, Codable, CaseIterable, Sendable {
    case neurotypical
    case autistic

    var displayName: String {
        switch self {
        case .neurotypical: "Normie"
        case .autistic: "Autist"
        }
    }
}

struct AppUser: Codable, Identifiable, Sendable {
    let id: UUID
    var displayName: String
    var email: String?
    var communicationStyle: CommunicationStyle
    var creditBalance: Int
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case displayName = "display_name"
        case email
        case communicationStyle = "communication_style"
        case creditBalance = "credit_balance"
        case createdAt = "created_at"
    }
}
