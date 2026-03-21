import SwiftUI
import StoreKit

struct BuyCreditsSheet: View {
    @Environment(StoreViewModel.self) private var storeVM
    @Environment(AuthViewModel.self) private var authVM
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                // Header
                VStack(spacing: 8) {
                    Image(systemName: "sparkles")
                        .font(.system(size: 50))
                        .foregroundStyle(.accent)
                    Text("Buy Credits")
                        .font(.title.bold())
                    Text("Credits are used for translations and chat messages")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                }
                .padding(.top)

                // Products
                if storeVM.products.isEmpty {
                    ProgressView("Loading products...")
                } else {
                    VStack(spacing: 12) {
                        ForEach(storeVM.products, id: \.id) { product in
                            CreditProductCard(product: product) {
                                Task {
                                    await storeVM.purchase(product)
                                    if storeVM.purchaseSuccess {
                                        await authVM.refreshUser()
                                        dismiss()
                                    }
                                }
                            }
                        }
                    }
                    .padding(.horizontal)
                }

                if storeVM.purchaseInProgress {
                    ProgressView("Processing purchase...")
                }

                if let error = storeVM.error {
                    Text(error)
                        .font(.caption)
                        .foregroundStyle(.red)
                }

                Spacer()
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}

struct CreditProductCard: View {
    let product: Product
    let onPurchase: () -> Void

    var monthsOfAccess: Int {
        AppConfig.productMonths[product.id] ?? 0
    }

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("\(monthsOfAccess) Month\(monthsOfAccess == 1 ? "" : "s")")
                    .font(.headline)
                Text(product.description)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            Button(action: onPurchase) {
                Text(product.displayPrice)
                    .font(.subheadline.bold())
                    .padding(.horizontal, 20)
                    .padding(.vertical, 10)
                    .background(.accent)
                    .foregroundStyle(.white)
                    .clipShape(Capsule())
            }
        }
        .padding()
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}
