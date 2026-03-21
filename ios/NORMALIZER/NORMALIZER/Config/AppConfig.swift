import Foundation

enum AppConfig {
    // MARK: - API
    static let apiBaseURL = URL(string: "https://normalizer-api-production.up.railway.app")!
    static let wsBaseURL = URL(string: "wss://normalizer-api-production.up.railway.app")!

    // MARK: - StoreKit Product IDs
    static let subscriptionProductIDs: Set<String> = [
        "com.normalaizer.normie.monthly",
        "com.normalaizer.normie.yearly",
        "com.normalaizer.normie.giftpack10",
    ]

    // MARK: - Product months of access
    static let productMonths: [String: Int] = [
        "com.normalaizer.normie.monthly": 1,
        "com.normalaizer.normie.yearly": 12,
        "com.normalaizer.normie.giftpack10": 10,
    ]
}
