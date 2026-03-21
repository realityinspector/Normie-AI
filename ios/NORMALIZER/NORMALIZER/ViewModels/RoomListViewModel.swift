import Foundation
import Observation

@Observable
@MainActor
final class RoomListViewModel {
    var rooms: [Room] = []
    var isLoading = false
    var error: String?
    var showCreateSheet = false

    func loadRooms() async {
        isLoading = true
        defer { isLoading = false }
        do {
            rooms = try await APIClient.shared.request(.listRooms)
        } catch {
            self.error = error.localizedDescription
        }
    }

    func createRoom(name: String, isPublic: Bool) async -> Room? {
        do {
            let room: Room = try await APIClient.shared.request(.createRoom(name: name, isPublic: isPublic))
            rooms.insert(room, at: 0)
            return room
        } catch {
            self.error = error.localizedDescription
            return nil
        }
    }

    func deleteRoom(_ room: Room) async {
        do {
            try await APIClient.shared.requestVoid(.deleteRoom(id: room.id))
            rooms.removeAll { $0.id == room.id }
        } catch {
            self.error = error.localizedDescription
        }
    }
}
