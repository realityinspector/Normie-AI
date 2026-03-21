import Foundation

actor WebSocketClient {
    private var task: URLSessionWebSocketTask?
    private var continuation: AsyncStream<WSIncoming>.Continuation?
    private var isConnected = false
    private var reconnectAttempts = 0
    private let maxReconnectDelay: TimeInterval = 30

    private var roomId: UUID?
    private var token: String?

    var messages: AsyncStream<WSIncoming> {
        AsyncStream { continuation in
            self.continuation = continuation
        }
    }

    func connect(roomId: UUID, token: String) {
        self.roomId = roomId
        self.token = token
        self.reconnectAttempts = 0
        doConnect()
    }

    func disconnect() {
        isConnected = false
        task?.cancel(with: .goingAway, reason: nil)
        task = nil
        continuation?.finish()
        continuation = nil
    }

    func send(text: String) async throws {
        let payload = ["type": "send_message", "text": text]
        let data = try JSONSerialization.data(withJSONObject: payload)
        let string = String(data: data, encoding: .utf8)!
        try await task?.send(.string(string))
    }

    // MARK: - Private

    private func doConnect() {
        guard let roomId, let token else { return }

        var components = URLComponents(url: AppConfig.wsBaseURL.appendingPathComponent("/ws/rooms/\(roomId)"), resolvingAgainstBaseURL: false)!
        components.queryItems = [URLQueryItem(name: "token", value: token)]

        let request = URLRequest(url: components.url!)
        let session = URLSession(configuration: .default)
        let wsTask = session.webSocketTask(with: request)
        self.task = wsTask
        wsTask.resume()
        isConnected = true
        reconnectAttempts = 0

        Task { await receiveLoop() }
    }

    private func receiveLoop() async {
        guard let task else { return }

        while isConnected {
            do {
                let message = try await task.receive()
                switch message {
                case .string(let text):
                    if let data = text.data(using: .utf8) {
                        parseMessage(data)
                    }
                case .data(let data):
                    parseMessage(data)
                @unknown default:
                    break
                }
            } catch {
                if isConnected {
                    await attemptReconnect()
                }
                return
            }
        }
    }

    private func parseMessage(_ data: Data) {
        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let type = json["type"] as? String else { return }

        switch type {
        case "message":
            if let msgData = json["data"] as? [String: Any] {
                let decoder = JSONDecoder()
                decoder.dateDecodingStrategy = .iso8601
                if let jsonData = try? JSONSerialization.data(withJSONObject: msgData),
                   let msg = try? decoder.decode(ChatMessage.self, from: jsonData) {
                    continuation?.yield(.message(msg))
                }
            }
        case "user_joined":
            if let data = json["data"] as? [String: Any],
               let name = data["display_name"] as? String {
                continuation?.yield(.userJoined(name: name))
            }
        case "user_left":
            if let data = json["data"] as? [String: Any],
               let userId = data["user_id"] as? String {
                continuation?.yield(.userLeft(userId: userId))
            }
        case "error":
            if let data = json["data"] as? [String: Any],
               let message = data["message"] as? String {
                continuation?.yield(.error(message))
            }
        default:
            break
        }
    }

    private func attemptReconnect() async {
        guard isConnected else { return }
        reconnectAttempts += 1
        let delay = min(pow(2.0, Double(reconnectAttempts)), maxReconnectDelay)
        try? await Task.sleep(for: .seconds(delay))
        if isConnected {
            doConnect()
        }
    }
}
