import StoreKit
import Foundation

@Observable
@MainActor
final class StoreService {
    private(set) var products: [Product] = []
    private(set) var purchaseInProgress = false
    private var updateListenerTask: Task<Void, Never>?

    func loadProducts() async {
        do {
            let storeProducts = try await Product.products(for: AppConfig.subscriptionProductIDs)
            products = storeProducts.sorted { $0.price < $1.price }
        } catch {
            print("Failed to load products: \(error)")
        }
    }

    func purchase(_ product: Product) async throws -> String? {
        purchaseInProgress = true
        defer { purchaseInProgress = false }

        let result = try await product.purchase()
        switch result {
        case .success(let verification):
            let transaction = try checkVerified(verification)
            let jwsRepresentation = verification.jwsRepresentation
            await transaction.finish()
            return jwsRepresentation
        case .userCancelled:
            return nil
        case .pending:
            return nil
        @unknown default:
            return nil
        }
    }

    func listenForTransactions() {
        updateListenerTask = Task.detached {
            for await result in Transaction.updates {
                if case .verified(let transaction) = result {
                    await transaction.finish()
                }
            }
        }
    }

    nonisolated private func checkVerified<T>(_ result: VerificationResult<T>) throws -> T {
        switch result {
        case .unverified(_, let error):
            throw error
        case .verified(let value):
            return value
        }
    }
}
