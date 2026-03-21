import SwiftUI

@main
struct NORMALIZERApp: App {
    @State private var authViewModel = AuthViewModel()
    @State private var storeViewModel = StoreViewModel()

    var body: some Scene {
        WindowGroup {
            Group {
                if authViewModel.isLoading {
                    LaunchScreen()
                } else if authViewModel.isAuthenticated {
                    MainTabView()
                } else {
                    SignInView()
                }
            }
            .environment(authViewModel)
            .environment(storeViewModel)
            .task {
                await authViewModel.checkExistingAuth()
                storeViewModel.listenForTransactions()
                await storeViewModel.loadProducts()
            }
        }
    }
}
