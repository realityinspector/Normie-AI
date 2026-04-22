import SwiftUI

struct HomeView: View {
    @Environment(AuthViewModel.self) private var authVM
    @State private var vm = HomeViewModel()

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                // Credit balance card
                CreditBadge(balance: vm.creditBalance)
                    .padding(.top)

                // Action cards
                VStack(spacing: 16) {
                    NavigationLink {
                        TextTranslateView()
                    } label: {
                        ActionCard(
                            icon: "text.bubble.fill",
                            title: "Text Translate",
                            subtitle: "Translate text between communication styles",
                            color: .blue
                        )
                    }
                    .accessibilityIdentifier("home.card.text_translate")

                    NavigationLink {
                        ScreenshotTranslateView()
                    } label: {
                        ActionCard(
                            icon: "camera.viewfinder",
                            title: "Screenshot Translate",
                            subtitle: "OCR and translate from images",
                            color: .purple
                        )
                    }
                    .accessibilityIdentifier("home.card.screenshot_translate")

                    NavigationLink {
                        RoomListView()
                    } label: {
                        ActionCard(
                            icon: "bubble.left.and.bubble.right.fill",
                            title: "Live Chat Rooms",
                            subtitle: "Real-time translated conversations",
                            color: .green
                        )
                    }
                    .accessibilityIdentifier("home.card.chat_rooms")

                    NavigationLink {
                        TranscriptListView()
                    } label: {
                        ActionCard(
                            icon: "doc.text.fill",
                            title: "My Transcripts",
                            subtitle: "View saved conversation transcripts",
                            color: .orange
                        )
                    }
                    .accessibilityIdentifier("home.card.transcripts")
                }
                .padding(.horizontal)
            }
        }
        .navigationTitle("NORMALAIZER")
        .task {
            await vm.refreshCredits()
        }
        .refreshable {
            await vm.refreshCredits()
        }
    }
}

struct ActionCard: View {
    let icon: String
    let title: String
    let subtitle: String
    let color: Color

    var body: some View {
        HStack(spacing: 16) {
            Image(systemName: icon)
                .font(.title)
                .foregroundStyle(color)
                .frame(width: 50)

            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.headline)
                    .foregroundStyle(.primary)
                Text(subtitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            Image(systemName: "chevron.right")
                .foregroundStyle(.secondary)
        }
        .padding()
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}
