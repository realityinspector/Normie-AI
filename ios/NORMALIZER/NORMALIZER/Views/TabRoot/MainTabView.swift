import SwiftUI

struct MainTabView: View {
    var body: some View {
        TabView {
            Tab("Home", systemImage: "house.fill") {
                NavigationStack {
                    HomeView()
                }
            }

            Tab("Chat", systemImage: "bubble.left.and.bubble.right.fill") {
                NavigationStack {
                    RoomListView()
                }
            }

            Tab("Transcripts", systemImage: "doc.text.fill") {
                NavigationStack {
                    TranscriptListView()
                }
            }

            Tab("Profile", systemImage: "person.crop.circle.fill") {
                NavigationStack {
                    ProfileView()
                }
            }
        }
    }
}
