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
                #if DEBUG
                if CommandLine.arguments.contains("-uitest-autologin") {
                    Keychain.accessToken = nil
                    await authViewModel.devSignIn(name: "UITest User", style: .autistic)
                    authViewModel.isLoading = false
                    storeViewModel.listenForTransactions()
                    await storeViewModel.loadProducts()
                    return
                }
                #endif
                await authViewModel.checkExistingAuth()
                storeViewModel.listenForTransactions()
                await storeViewModel.loadProducts()
            }
        }
    }
}
