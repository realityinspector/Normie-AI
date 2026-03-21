import SwiftUI
import AuthenticationServices

struct SignInView: View {
    @Environment(AuthViewModel.self) private var authVM
    @State private var showDevLogin = false
    @State private var devName = ""
    @State private var devStyle: CommunicationStyle = .neurotypical

    var body: some View {
        VStack(spacing: 32) {
            Spacer()

            VStack(spacing: 16) {
                Image(systemName: "brain.head.profile")
                    .font(.system(size: 90))
                    .foregroundStyle(
                        LinearGradient(
                            colors: [Color(red: 0.39, green: 0.40, blue: 0.95),
                                     Color(red: 0.55, green: 0.36, blue: 0.96)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )

                // NORMAL-AI-ZER with AI highlighted
                HStack(spacing: 0) {
                    Text("NORMAL")
                        .font(.system(size: 36, weight: .black))
                        .foregroundStyle(Color(red: 0.12, green: 0.11, blue: 0.29))
                    Text("AI")
                        .font(.system(size: 36, weight: .black))
                        .foregroundStyle(
                            LinearGradient(
                                colors: [Color(red: 0.39, green: 0.40, blue: 0.95),
                                         Color(red: 0.55, green: 0.36, blue: 0.96)],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                    Text("ZER")
                        .font(.system(size: 36, weight: .black))
                        .foregroundStyle(Color(red: 0.12, green: 0.11, blue: 0.29))
                }

                Text("Cultural Communication Translator")
                    .font(.title3)
                    .foregroundStyle(.secondary)

                // Free badge
                Text("FREE FOR NEURODIVERGENT")
                    .font(.caption.bold())
                    .foregroundStyle(.white)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 6)
                    .background(
                        LinearGradient(
                            colors: [Color(red: 0.39, green: 0.40, blue: 0.95),
                                     Color(red: 0.55, green: 0.36, blue: 0.96)],
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
                    .clipShape(Capsule())

                Text("Bridge the gap between neurotypical and autistic communication styles")
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 40)
            }

            Spacer()

            SignInWithAppleButton(.signIn) { request in
                request.requestedScopes = [.fullName, .email]
            } onCompletion: { _ in
                // Handled by AuthService delegate
            }
            .signInWithAppleButtonStyle(.whiteOutline)
            .frame(height: 50)
            .padding(.horizontal, 40)
            .onTapGesture {
                Task {
                    await authVM.signIn()
                }
            }

            // DEV LOGIN - remove before App Store submission
            #if DEBUG
            Button("Dev Login") {
                showDevLogin = true
            }
            .font(.caption)
            .foregroundStyle(.secondary)
            #endif

            if let error = authVM.error {
                Text(error)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .padding(.horizontal)
            }

            Spacer()
                .frame(height: 40)
        }
        .sheet(isPresented: $showDevLogin) {
            NavigationStack {
                Form {
                    Section("Test User") {
                        TextField("Display Name", text: $devName)
                        Picker("Communication Style", selection: $devStyle) {
                            Text("Normie").tag(CommunicationStyle.neurotypical)
                            Text("Autist").tag(CommunicationStyle.autistic)
                        }
                        .pickerStyle(.segmented)
                    }
                }
                .navigationTitle("Dev Login")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("Cancel") { showDevLogin = false }
                    }
                    ToolbarItem(placement: .confirmationAction) {
                        Button("Sign In") {
                            showDevLogin = false
                            Task {
                                await authVM.devSignIn(name: devName, style: devStyle)
                            }
                        }
                        .disabled(devName.trimmingCharacters(in: .whitespaces).isEmpty)
                    }
                }
            }
            .presentationDetents([.medium])
        }
    }
}
