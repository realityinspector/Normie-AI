import Foundation

enum APIError: LocalizedError {
    case unauthorized
    case insufficientCredits(String)
    case serverError(Int, String)
    case networkError(Error)
    case decodingError(Error)

    var errorDescription: String? {
        switch self {
        case .unauthorized: "Please sign in again."
        case .insufficientCredits(let msg): msg
        case .serverError(let code, let msg): "Server error (\(code)): \(msg)"
        case .networkError(let err): "Network error: \(err.localizedDescription)"
        case .decodingError(let err): "Data error: \(err.localizedDescription)"
        }
    }
}

actor APIClient {
    static let shared = APIClient()

    private let session: URLSession
    private let baseURL: URL
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        self.session = URLSession(configuration: config)
        self.baseURL = AppConfig.apiBaseURL
        self.decoder = JSONDecoder()
        self.decoder.dateDecodingStrategy = .iso8601
        self.encoder = JSONEncoder()
        self.encoder.dateEncodingStrategy = .iso8601
    }

    // MARK: - Generic request

    func request<T: Decodable>(_ endpoint: APIEndpoint) async throws -> T {
        let urlRequest = try buildRequest(endpoint)
        return try await execute(urlRequest)
    }

    func requestVoid(_ endpoint: APIEndpoint) async throws {
        let urlRequest = try buildRequest(endpoint)
        let (_, response) = try await session.data(for: urlRequest)
        try checkResponse(response)
    }

    // MARK: - Multipart upload

    func upload<T: Decodable>(
        path: String,
        imageData: Data,
        mimeType: String,
        fields: [String: String]
    ) async throws -> T {
        let boundary = UUID().uuidString
        var urlRequest = URLRequest(url: baseURL.appendingPathComponent(path))
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        if let token = Keychain.accessToken {
            urlRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        var body = Data()
        // Add text fields
        for (key, value) in fields {
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            body.append("Content-Disposition: form-data; name=\"\(key)\"\r\n\r\n".data(using: .utf8)!)
            body.append("\(value)\r\n".data(using: .utf8)!)
        }
        // Add image
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"image\"; filename=\"screenshot.jpg\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: \(mimeType)\r\n\r\n".data(using: .utf8)!)
        body.append(imageData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)

        urlRequest.httpBody = body
        return try await execute(urlRequest)
    }

    // MARK: - Private helpers

    private func buildRequest(_ endpoint: APIEndpoint) throws -> URLRequest {
        var urlRequest = URLRequest(url: baseURL.appendingPathComponent(endpoint.path))
        urlRequest.httpMethod = endpoint.method

        if let token = Keychain.accessToken {
            urlRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        if let body = endpoint.body {
            urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
            urlRequest.httpBody = try encoder.encode(body)
        }

        return urlRequest
    }

    private func execute<T: Decodable>(_ request: URLRequest) async throws -> T {
        let (data, response) = try await session.data(for: request)
        try checkResponse(response, data: data)

        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decodingError(error)
        }
    }

    private func checkResponse(_ response: URLResponse, data: Data? = nil) throws {
        guard let httpResponse = response as? HTTPURLResponse else { return }

        switch httpResponse.statusCode {
        case 200...299:
            return
        case 401:
            Keychain.accessToken = nil
            throw APIError.unauthorized
        case 402:
            let msg = data.flatMap { try? JSONDecoder().decode(ErrorDetail.self, from: $0).detail } ?? "Insufficient credits"
            throw APIError.insufficientCredits(msg)
        default:
            let msg = data.flatMap { try? JSONDecoder().decode(ErrorDetail.self, from: $0).detail } ?? "Unknown error"
            throw APIError.serverError(httpResponse.statusCode, msg)
        }
    }
}

private struct ErrorDetail: Decodable {
    let detail: String
}

// AnyEncodable wrapper for endpoint bodies
struct AnyEncodable: Encodable {
    private let _encode: (Encoder) throws -> Void

    init<T: Encodable>(_ value: T) {
        _encode = value.encode
    }

    func encode(to encoder: Encoder) throws {
        try _encode(encoder)
    }
}
