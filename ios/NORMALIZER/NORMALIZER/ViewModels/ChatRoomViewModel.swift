import Foundation
import Observation

@Observable
@MainActor
final class ChatRoomViewModel {
    var room: Room?
    var messages: [ChatMessage] = []
    var inputText = ""
    var isLoading = false
    var isSending = false
    var error: String?

    private let wsClient = WebSocketClient()
    private var listenTask: Task<Void, Never>?

    let roomId: UUID

    init(roomId: UUID) {
        self.roomId = roomId
    }

    func load() async {
        isLoading = true
        defer { isLoading = false }

        do {
            room = try await APIClient.shared.request(.getRoom(id: roomId))
            messages = try await APIClient.shared.request(.roomMessages(roomId: roomId, before: nil, limit: 100))
        } catch {
            self.error = error.localizedDescription
        }

        // Connect WebSocket
        guard let token = Keychain.accessToken else { return }
        let stream = await wsClient.messages
        await wsClient.connect(roomId: roomId, token: token)

        listenTask = Task {
            for await incoming in stream {
                await handleIncoming(incoming)
            }
        }
    }

    func sendMessage() async {
        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }

        isSending = true
        inputText = ""
        defer { isSending = false }

        do {
            try await wsClient.send(text: text)
        } catch {
            self.error = "Failed to send message"
            inputText = text
        }
    }

    func saveTranscript() async -> Bool {
        do {
            let _: Transcript = try await APIClient.shared.request(.createTranscript(roomId: roomId))
            return true
        } catch {
            self.error = error.localizedDescription
            return false
        }
    }

    func disconnect() async {
        listenTask?.cancel()
        await wsClient.disconnect()
    }

    // MARK: - Private

    private func handleIncoming(_ incoming: WSIncoming) async {
        switch incoming {
        case .message(let msg):
            messages.append(msg)
        case .userJoined(let name):
            // Could show a toast
            print("\(name) joined")
        case .userLeft(let userId):
            print("\(userId) left")
        case .error(let msg):
            error = msg
        }
    }
}
