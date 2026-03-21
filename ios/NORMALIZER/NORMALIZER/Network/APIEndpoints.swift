import Foundation

enum APIEndpoint {
    // Auth
    case appleSignIn(AppleSignInRequest)
    case devSignIn(name: String, communicationStyle: String)

    // User
    case getMe
    case updateMe(displayName: String?, communicationStyle: CommunicationStyle?)

    // Rooms
    case listRooms
    case createRoom(name: String, isPublic: Bool)
    case getRoom(id: UUID)
    case deleteRoom(id: UUID)
    case joinRoom(id: UUID)

    // Messages
    case roomMessages(roomId: UUID, before: Date?, limit: Int)

    // Translate
    case translateText(TranslateTextRequest)

    // Transcripts
    case listTranscripts
    case createTranscript(roomId: UUID)
    case getTranscript(id: UUID)

    // Credits
    case creditBalance
    case verifyPurchase(jwsTransaction: String, productId: String)

    var path: String {
        switch self {
        case .appleSignIn: "/auth/apple"
        case .devSignIn: "/auth/dev"
        case .getMe, .updateMe: "/users/me"
        case .listRooms, .createRoom: "/rooms"
        case .getRoom(let id): "/rooms/\(id)"
        case .deleteRoom(let id): "/rooms/\(id)"
        case .joinRoom(let id): "/rooms/\(id)/join"
        case .roomMessages(let roomId, _, _): "/rooms/\(roomId)/messages"
        case .translateText: "/translate/text"
        case .listTranscripts, .createTranscript: "/transcripts"
        case .getTranscript(let id): "/transcripts/\(id)"
        case .creditBalance: "/credits/balance"
        case .verifyPurchase: "/credits/verify-purchase"
        }
    }

    var method: String {
        switch self {
        case .getMe, .listRooms, .getRoom, .roomMessages, .listTranscripts, .getTranscript, .creditBalance:
            "GET"
        case .appleSignIn, .devSignIn, .createRoom, .joinRoom, .translateText, .createTranscript, .verifyPurchase:
            "POST"
        case .updateMe:
            "PATCH"
        case .deleteRoom:
            "DELETE"
        }
    }

    var body: AnyEncodable? {
        switch self {
        case .appleSignIn(let req):
            AnyEncodable(req)
        case .devSignIn(let name, let style):
            AnyEncodable(DevSignInBody(name: name, communicationStyle: style))
        case .updateMe(let displayName, let style):
            AnyEncodable(UpdateMeBody(displayName: displayName, communicationStyle: style))
        case .createRoom(let name, let isPublic):
            AnyEncodable(CreateRoomBody(name: name, isPublic: isPublic))
        case .translateText(let req):
            AnyEncodable(req)
        case .createTranscript(let roomId):
            AnyEncodable(CreateTranscriptBody(roomId: roomId))
        case .verifyPurchase(let jws, let productId):
            AnyEncodable(VerifyPurchaseBody(jwsTransaction: jws, productId: productId))
        default:
            nil
        }
    }
}

// MARK: - Request bodies

private struct UpdateMeBody: Encodable {
    let displayName: String?
    let communicationStyle: CommunicationStyle?

    enum CodingKeys: String, CodingKey {
        case displayName = "display_name"
        case communicationStyle = "communication_style"
    }
}

private struct CreateRoomBody: Encodable {
    let name: String
    let isPublic: Bool

    enum CodingKeys: String, CodingKey {
        case name
        case isPublic = "is_public"
    }
}

private struct CreateTranscriptBody: Encodable {
    let roomId: UUID

    enum CodingKeys: String, CodingKey {
        case roomId = "room_id"
    }
}

private struct DevSignInBody: Encodable {
    let name: String
    let communicationStyle: String

    enum CodingKeys: String, CodingKey {
        case name
        case communicationStyle = "communication_style"
    }
}

private struct VerifyPurchaseBody: Encodable {
    let jwsTransaction: String
    let productId: String

    enum CodingKeys: String, CodingKey {
        case jwsTransaction = "jws_transaction"
        case productId = "product_id"
    }
}
