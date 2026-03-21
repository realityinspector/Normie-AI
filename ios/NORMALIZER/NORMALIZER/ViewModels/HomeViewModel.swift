import Foundation
import Observation

@Observable
@MainActor
final class HomeViewModel {
    var creditBalance: Int = 0
    var isLoading = false

    func refreshCredits() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let balance: CreditBalance = try await APIClient.shared.request(.creditBalance)
            creditBalance = balance.balance
        } catch {
            // Silently fail
        }
    }
}
