import Foundation
import Observation

@Observable
@MainActor
final class AuthViewModel {
    var isAuthenticated = false
    var isLoading = true
    var currentUser: AppUser?
    var error: String?

    private let authService = AuthService()

    func checkExistingAuth() async {
        guard Keychain.accessToken != nil else {
            isLoading = false
            return
        }

        do {
            let user: AppUser = try await APIClient.shared.request(.getMe)
            currentUser = user
            isAuthenticated = true
        } catch {
            // Token expired or invalid
            Keychain.accessToken = nil
        }
        isLoading = false
    }

    func signIn() async {
        error = nil
        do {
            _ = try await authService.signInWithApple()
            let user: AppUser = try await APIClient.shared.request(.getMe)
            currentUser = user
            isAuthenticated = true
        } catch {
            self.error = error.localizedDescription
        }
    }

    // DEV ONLY: Sign in with a test name (no Apple ID required)
    func devSignIn(name: String, style: CommunicationStyle) async {
        error = nil
        do {
            let response: TokenResponse = try await APIClient.shared.request(
                .devSignIn(name: name, communicationStyle: style.rawValue)
            )
            Keychain.accessToken = response.accessToken
            let user: AppUser = try await APIClient.shared.request(.getMe)
            currentUser = user
            isAuthenticated = true
        } catch {
            self.error = error.localizedDescription
        }
    }

    func signOut() {
        Keychain.accessToken = nil
        currentUser = nil
        isAuthenticated = false
    }

    func refreshUser() async {
        do {
            let user: AppUser = try await APIClient.shared.request(.getMe)
            currentUser = user
        } catch {
            // Silently fail refresh
        }
    }

    func updateStyle(_ style: CommunicationStyle) async {
        do {
            let user: AppUser = try await APIClient.shared.request(
                .updateMe(displayName: nil, communicationStyle: style)
            )
            currentUser = user
        } catch {
            self.error = error.localizedDescription
        }
    }
}
