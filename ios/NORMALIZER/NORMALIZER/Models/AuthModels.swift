import Foundation

struct AppleSignInRequest: Codable, Sendable {
    let identityToken: String
    let authorizationCode: String
    let fullName: String?

    enum CodingKeys: String, CodingKey {
        case identityToken = "identity_token"
        case authorizationCode = "authorization_code"
        case fullName = "full_name"
    }
}

struct TokenResponse: Codable, Sendable {
    let accessToken: String
    let tokenType: String
    let expiresIn: Int

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case tokenType = "token_type"
        case expiresIn = "expires_in"
    }
}

struct CreditBalance: Codable, Sendable {
    let balance: Int
}
