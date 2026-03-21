import StoreKit
import Foundation
import Observation

@Observable
@MainActor
final class StoreViewModel {
    private let storeService = StoreService()

    var products: [Product] { storeService.products }
    var purchaseInProgress: Bool { storeService.purchaseInProgress }
    var error: String?
    var purchaseSuccess = false

    func loadProducts() async {
        await storeService.loadProducts()
    }

    func listenForTransactions() {
        storeService.listenForTransactions()
    }

    func purchase(_ product: Product) async {
        error = nil
        purchaseSuccess = false

        do {
            guard let jwsRepresentation = try await storeService.purchase(product) else {
                return // User cancelled or pending
            }

            // Verify with backend
            let _: CreditBalance = try await APIClient.shared.request(
                .verifyPurchase(jwsTransaction: jwsRepresentation, productId: product.id)
            )
            purchaseSuccess = true
        } catch {
            self.error = error.localizedDescription
        }
    }
}
