import AuthenticationServices
import Foundation

@MainActor
final class AuthService: NSObject, ASAuthorizationControllerDelegate {
    private var signInContinuation: CheckedContinuation<(String, String, String?), Error>?

    func signInWithApple() async throws -> TokenResponse {
        let (identityToken, authorizationCode, fullName) = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<(String, String, String?), Error>) in
            self.signInContinuation = continuation

            let provider = ASAuthorizationAppleIDProvider()
            let request = provider.createRequest()
            request.requestedScopes = [.fullName, .email]

            let controller = ASAuthorizationController(authorizationRequests: [request])
            controller.delegate = self
            controller.performRequests()
        }

        let request = AppleSignInRequest(
            identityToken: identityToken,
            authorizationCode: authorizationCode,
            fullName: fullName
        )

        let response: TokenResponse = try await APIClient.shared.request(.appleSignIn(request))
        Keychain.accessToken = response.accessToken
        return response
    }

    // MARK: - ASAuthorizationControllerDelegate

    nonisolated func authorizationController(controller: ASAuthorizationController, didCompleteWithAuthorization authorization: ASAuthorization) {
        guard let credential = authorization.credential as? ASAuthorizationAppleIDCredential,
              let identityTokenData = credential.identityToken,
              let identityToken = String(data: identityTokenData, encoding: .utf8),
              let authCodeData = credential.authorizationCode,
              let authorizationCode = String(data: authCodeData, encoding: .utf8) else {
            Task { @MainActor in
                signInContinuation?.resume(throwing: AuthError.missingCredentials)
                signInContinuation = nil
            }
            return
        }

        let fullName: String? = {
            guard let name = credential.fullName else { return nil }
            let components = [name.givenName, name.familyName].compactMap { $0 }
            return components.isEmpty ? nil : components.joined(separator: " ")
        }()

        Task { @MainActor in
            signInContinuation?.resume(returning: (identityToken, authorizationCode, fullName))
            signInContinuation = nil
        }
    }

    nonisolated func authorizationController(controller: ASAuthorizationController, didCompleteWithError error: Error) {
        Task { @MainActor in
            signInContinuation?.resume(throwing: error)
            signInContinuation = nil
        }
    }
}

enum AuthError: LocalizedError {
    case missingCredentials

    var errorDescription: String? {
        switch self {
        case .missingCredentials: "Could not retrieve Apple Sign-In credentials."
        }
    }
}
