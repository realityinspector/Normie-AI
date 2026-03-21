import SwiftUI

struct RoomListView: View {
    @State private var vm = RoomListViewModel()

    var body: some View {
        Group {
            if vm.isLoading && vm.rooms.isEmpty {
                ProgressView()
            } else if vm.rooms.isEmpty {
                ContentUnavailableView(
                    "No Chat Rooms",
                    systemImage: "bubble.left.and.bubble.right",
                    description: Text("Create a room to start a translated conversation")
                )
            } else {
                List {
                    ForEach(vm.rooms) { room in
                        NavigationLink(value: room.id) {
                            HStack {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(room.name)
                                        .font(.headline)
                                    HStack(spacing: 8) {
                                        Label(
                                            room.isPublic ? "Public" : "Private",
                                            systemImage: room.isPublic ? "globe" : "lock.fill"
                                        )
                                        .font(.caption)
                                        .foregroundStyle(.secondary)

                                        Text("\(room.participants.count) participants")
                                            .font(.caption)
                                            .foregroundStyle(.secondary)
                                    }
                                }
                            }
                        }
                    }
                    .onDelete { indexSet in
                        Task {
                            for index in indexSet {
                                await vm.deleteRoom(vm.rooms[index])
                            }
                        }
                    }
                }
            }
        }
        .navigationTitle("Chat Rooms")
        .navigationDestination(for: UUID.self) { roomId in
            ChatRoomView(roomId: roomId)
        }
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    vm.showCreateSheet = true
                } label: {
                    Image(systemName: "plus")
                }
            }
        }
        .sheet(isPresented: $vm.showCreateSheet) {
            CreateRoomSheet { name, isPublic in
                Task {
                    _ = await vm.createRoom(name: name, isPublic: isPublic)
                    vm.showCreateSheet = false
                }
            }
        }
        .task {
            await vm.loadRooms()
        }
        .refreshable {
            await vm.loadRooms()
        }
    }
}
