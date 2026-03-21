import SwiftUI

struct ProfileView: View {
    @Environment(AuthViewModel.self) private var authVM
    @Environment(StoreViewModel.self) private var storeVM
    @State private var showBuyCredits = false

    var body: some View {
        List {
            // User info
            if let user = authVM.currentUser {
                Section {
                    HStack {
                        Image(systemName: "person.crop.circle.fill")
                            .font(.largeTitle)
                            .foregroundStyle(.accent)
                        VStack(alignment: .leading) {
                            Text(user.displayName)
                                .font(.headline)
                            if let email = user.email {
                                Text(email)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }

                // Communication style
                Section("Communication Style") {
                    Picker("Your Style", selection: Binding(
                        get: { user.communicationStyle },
                        set: { newStyle in
                            Task { await authVM.updateStyle(newStyle) }
                        }
                    )) {
                        ForEach(CommunicationStyle.allCases, id: \.self) { style in
                            Text(style.displayName).tag(style)
                        }
                    }
                    .pickerStyle(.segmented)
                }

                // Credits
                Section("Credits") {
                    HStack {
                        Label("Balance", systemImage: "creditcard.fill")
                        Spacer()
                        Text("\(user.creditBalance)")
                            .font(.title2.bold())
                            .foregroundStyle(.accent)
                    }

                    Button {
                        showBuyCredits = true
                    } label: {
                        Label("Buy Credits", systemImage: "cart.fill")
                    }
                }
            }

            // Actions
            Section {
                Button(role: .destructive) {
                    authVM.signOut()
                } label: {
                    Label("Sign Out", systemImage: "rectangle.portrait.and.arrow.right")
                }
            }
        }
        .navigationTitle("Profile")
        .sheet(isPresented: $showBuyCredits) {
            BuyCreditsSheet()
        }
        .task {
            await authVM.refreshUser()
        }
    }
}
