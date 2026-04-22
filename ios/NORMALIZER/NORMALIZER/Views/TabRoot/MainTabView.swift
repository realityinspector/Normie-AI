import SwiftUI

struct MainTabView: View {
    var body: some View {
        TabView {
            Tab("Home", systemImage: "house.fill") {
                NavigationStack {
                    HomeView()
                }
            }
            .accessibilityIdentifier("tab.home")

            Tab("Chat", systemImage: "bubble.left.and.bubble.right.fill") {
                NavigationStack {
                    RoomListView()
                }
            }
            .accessibilityIdentifier("tab.chat")

            Tab("Transcripts", systemImage: "doc.text.fill") {
                NavigationStack {
                    TranscriptListView()
                }
            }
            .accessibilityIdentifier("tab.transcripts")

            Tab("Profile", systemImage: "person.crop.circle.fill") {
                NavigationStack {
                    ProfileView()
                }
            }
            .accessibilityIdentifier("tab.profile")
        }
    }
}
