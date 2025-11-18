//
//  APIService.swift
//  Personal Assistant
//
//  Created by LifeOS on 11/15/25.
//

import Foundation
import Combine

enum APIError: Error, LocalizedError {
    case invalidURL
    case invalidResponse
    case decodingError
    case serverError(String)
    case unauthorized
    case networkError(Error)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .invalidResponse:
            return "Invalid response from server"
        case .decodingError:
            return "Failed to decode response"
        case .serverError(let message):
            return message
        case .unauthorized:
            return "Unauthorized. Please log in again."
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        }
    }
}

class APIService {
    static let shared = APIService()

    // Change this to your backend URL
    private let baseURL = "http://localhost:8000/api/v1"

    private var accessToken: String? {
        get { UserDefaults.standard.string(forKey: "accessToken") }
        set { UserDefaults.standard.set(newValue, forKey: "accessToken") }
    }

    private var refreshToken: String? {
        get { UserDefaults.standard.string(forKey: "refreshToken") }
        set { UserDefaults.standard.set(newValue, forKey: "refreshToken") }
    }

    private let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }()

    private let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }()

    private init() {}

    // MARK: - Generic Request

    private func request<T: Decodable>(
        endpoint: String,
        method: String = "GET",
        body: Encodable? = nil,
        requiresAuth: Bool = false
    ) async throws -> T {
        guard let url = URL(string: baseURL + endpoint) else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if requiresAuth {
            if let token = accessToken {
                request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
                print("🔑 Using token for \(endpoint): \(token.prefix(20))...")
            } else {
                print("❌ No access token available for \(endpoint)")
            }
        }

        if let body = body {
            request.httpBody = try encoder.encode(body)
        }

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        switch httpResponse.statusCode {
        case 200...299:
            do {
                return try decoder.decode(T.self, from: data)
            } catch {
                print("Decoding error: \(error)")
                if let responseString = String(data: data, encoding: .utf8) {
                    print("Response data: \(responseString)")
                }
                print("Expected type: \(T.self)")
                throw APIError.decodingError
            }
        case 401:
            throw APIError.unauthorized
        case 400...499:
            if let errorResponse = try? decoder.decode([String: String].self, from: data),
               let message = errorResponse["detail"] {
                throw APIError.serverError(message)
            }
            throw APIError.serverError("Client error: \(httpResponse.statusCode)")
        case 500...599:
            throw APIError.serverError("Server error: \(httpResponse.statusCode)")
        default:
            throw APIError.invalidResponse
        }
    }

    // MARK: - Authentication

    func register(email: String, password: String, fullName: String?) async throws -> UserResponse {
        struct RegisterRequest: Codable {
            let email: String
            let password: String
            let fullName: String?
            let timezone: String

            enum CodingKeys: String, CodingKey {
                case email, password
                case fullName = "full_name"
                case timezone
            }
        }

        let request = RegisterRequest(
            email: email,
            password: password,
            fullName: fullName,
            timezone: TimeZone.current.identifier
        )

        return try await self.request(endpoint: "/auth/register", method: "POST", body: request)
    }

    func login(email: String, password: String) async throws -> TokenResponse {
        struct LoginRequest: Codable {
            let email: String
            let password: String
        }

        let request = LoginRequest(email: email, password: password)
        let response: TokenResponse = try await self.request(endpoint: "/auth/login", method: "POST", body: request)

        // Save tokens
        accessToken = response.accessToken
        refreshToken = response.refreshToken

        return response
    }

    func getCurrentUser() async throws -> UserResponse {
        return try await request(endpoint: "/auth/me", requiresAuth: true)
    }

    func logout() {
        accessToken = nil
        refreshToken = nil
    }

    // MARK: - Emails

    func getEmails(page: Int = 1, pageSize: Int = 50, isRead: Bool? = nil, search: String? = nil) async throws -> EmailListResponse {
        var endpoint = "/emails/?page=\(page)&page_size=\(pageSize)"
        if let isRead = isRead {
            endpoint += "&is_read=\(isRead)"
        }
        if let search = search, !search.isEmpty {
            endpoint += "&search=\(search.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")"
        }
        return try await request(endpoint: endpoint, requiresAuth: true)
    }

    func syncEmails() async throws -> [String: Int] {
        struct SyncResponse: Codable {
            let syncedCount: Int
            let newEmails: Int
            let updatedEmails: Int

            enum CodingKeys: String, CodingKey {
                case syncedCount = "synced_count"
                case newEmails = "new_emails"
                case updatedEmails = "updated_emails"
            }
        }

        let response: SyncResponse = try await request(endpoint: "/emails/sync", method: "POST", requiresAuth: true)
        return [
            "synced": response.syncedCount,
            "new": response.newEmails,
            "updated": response.updatedEmails
        ]
    }

    func markEmailRead(id: String, isRead: Bool) async throws {
        struct Empty: Codable {}
        let _: Empty = try await request(endpoint: "/emails/\(id)/read?is_read=\(isRead)", method: "PATCH", requiresAuth: true)
    }

    // MARK: - Tasks

    func getTasks(status: TaskStatus? = nil, page: Int = 1, pageSize: Int = 50) async throws -> TaskListResponse {
        var endpoint = "/tasks/?page=\(page)&page_size=\(pageSize)"
        if let status = status {
            endpoint += "&status=\(status.rawValue)"
        }
        return try await request(endpoint: endpoint, requiresAuth: true)
    }

    func getTask(id: String) async throws -> TaskItem {
        return try await request(endpoint: "/tasks/\(id)", requiresAuth: true)
    }

    func createTask(_ task: TaskCreateRequest) async throws -> TaskItem {
        return try await request(endpoint: "/tasks/", method: "POST", body: task, requiresAuth: true)
    }

    func updateTask(id: String, status: TaskStatus) async throws -> TaskItem {
        struct UpdateRequest: Codable {
            let status: TaskStatus
        }
        return try await request(endpoint: "/tasks/\(id)", method: "PATCH", body: UpdateRequest(status: status), requiresAuth: true)
    }

    func updateTaskContent(id: String, content: String) async throws -> TaskItem {
        struct UpdateRequest: Codable {
            let content: String
        }
        return try await request(endpoint: "/tasks/\(id)", method: "PATCH", body: UpdateRequest(content: content), requiresAuth: true)
    }

    func deleteTask(id: String) async throws {
        struct Empty: Codable {}
        let _: Empty = try await request(endpoint: "/tasks/\(id)", method: "DELETE", requiresAuth: true)
    }

    // MARK: - Agent Chat

    func sendChatMessage(
        message: String,
        useMemory: Bool = true,
        conversationId: String? = nil,
        conversationHistory: [ConversationHistoryMessage]? = nil
    ) async throws -> AgentChatResponse {
        let request = AgentChatRequest(
            message: message,
            context: nil,
            useMemory: useMemory,
            conversationId: conversationId,
            conversationHistory: conversationHistory
        )
        return try await self.request(endpoint: "/agent/chat", method: "POST", body: request, requiresAuth: true)
    }

    // MARK: - Conversations

    func getConversations(page: Int = 1, pageSize: Int = 50) async throws -> ConversationListResponse {
        let endpoint = "/conversations/?page=\(page)&page_size=\(pageSize)"
        return try await request(endpoint: endpoint, requiresAuth: true)
    }

    func getConversation(id: String) async throws -> ConversationWithMessages {
        let endpoint = "/conversations/\(id)"
        return try await request(endpoint: endpoint, requiresAuth: true)
    }

    func deleteConversation(id: String) async throws {
        struct Empty: Codable {}
        let _: Empty = try await request(endpoint: "/conversations/\(id)", method: "DELETE", requiresAuth: true)
    }
}
