//
//  ChatMessage.swift
//  Personal Assistant
//
//  Created by LifeOS on 11/15/25.
//

import Foundation

struct ChatMessage: Identifiable, Equatable {
    let id: UUID
    let role: MessageRole
    let content: String
    let timestamp: Date
    let toolsUsed: [String]?
    let actionsTaken: [String]?
    let taskReference: TaskReference?

    enum MessageRole: String {
        case user, assistant, system
    }

    struct TaskReference: Equatable {
        let taskId: String
        let taskTitle: String
        let action: String // "created", "updated", "completed"
    }

    init(id: UUID = UUID(), role: MessageRole, content: String, timestamp: Date = Date(), toolsUsed: [String]? = nil, actionsTaken: [String]? = nil, taskReference: TaskReference? = nil) {
        self.id = id
        self.role = role
        self.content = content
        self.timestamp = timestamp
        self.toolsUsed = toolsUsed
        self.actionsTaken = actionsTaken
        self.taskReference = taskReference
    }
}

struct AgentChatRequest: Codable {
    let message: String
    let context: [String: String]?
    let useMemory: Bool
    let conversationId: String?
    let conversationHistory: [ConversationHistoryMessage]?
    let streamScreenshots: Bool

    enum CodingKeys: String, CodingKey {
        case message, context
        case useMemory = "use_memory"
        case conversationId = "conversation_id"
        case conversationHistory = "conversation_history"
        case streamScreenshots = "stream_screenshots"
    }

    init(message: String, context: [String: String]? = nil, useMemory: Bool = true, conversationId: String? = nil, conversationHistory: [ConversationHistoryMessage]? = nil, streamScreenshots: Bool = false) {
        self.message = message
        self.context = context
        self.useMemory = useMemory
        self.conversationId = conversationId
        self.conversationHistory = conversationHistory
        self.streamScreenshots = streamScreenshots
    }
}

struct ConversationHistoryMessage: Codable {
    let role: String
    let content: String
}

struct ScreenshotCapture: Codable, Identifiable {
    let id: UUID
    let timestamp: String
    let screenshot: String  // Base64-encoded image
    let width: Int
    let height: Int
    let actionContext: String?

    enum CodingKeys: String, CodingKey {
        case timestamp, screenshot, width, height
        case actionContext = "action_context"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.id = UUID()
        self.timestamp = try container.decode(String.self, forKey: .timestamp)
        self.screenshot = try container.decode(String.self, forKey: .screenshot)
        self.width = try container.decode(Int.self, forKey: .width)
        self.height = try container.decode(Int.self, forKey: .height)
        self.actionContext = try? container.decode(String.self, forKey: .actionContext)
    }
}

struct AgentChatResponse: Codable {
    let message: String
    let conversationId: String
    let toolsUsed: [String]
    let contextRetrieved: Int
    let actionsTaken: [ActionTaken]
    let memoriesSaved: Int
    let taskReference: TaskReferenceResponse?
    let screenshots: [ScreenshotCapture]

    enum CodingKeys: String, CodingKey {
        case message
        case conversationId = "conversation_id"
        case toolsUsed = "tools_used"
        case contextRetrieved = "context_retrieved"
        case actionsTaken = "actions_taken"
        case memoriesSaved = "memories_saved"
        case taskReference = "task_reference"
        case screenshots
    }

    struct TaskReferenceResponse: Codable {
        let taskId: String
        let taskTitle: String
        let action: String

        enum CodingKeys: String, CodingKey {
            case taskId = "task_id"
            case taskTitle = "task_title"
            case action
        }
    }

    struct ActionTaken: Codable {
        let tool: String
        let args: [String: AnyCodable]?
        let result: [String: AnyCodable]?

        enum CodingKeys: String, CodingKey {
            case tool, args, result
        }

        init(from decoder: Decoder) throws {
            let container = try decoder.container(keyedBy: CodingKeys.self)
            tool = try container.decode(String.self, forKey: .tool)
            args = try? container.decode([String: AnyCodable].self, forKey: .args)
            result = try? container.decode([String: AnyCodable].self, forKey: .result)
        }
    }
}

// Helper for decoding arbitrary JSON values
struct AnyCodable: Codable {
    let value: Any

    init(_ value: Any) {
        self.value = value
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()

        if let bool = try? container.decode(Bool.self) {
            value = bool
        } else if let int = try? container.decode(Int.self) {
            value = int
        } else if let double = try? container.decode(Double.self) {
            value = double
        } else if let string = try? container.decode(String.self) {
            value = string
        } else if let array = try? container.decode([AnyCodable].self) {
            value = array.map { $0.value }
        } else if let dictionary = try? container.decode([String: AnyCodable].self) {
            value = dictionary.mapValues { $0.value }
        } else {
            value = NSNull()
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()

        switch value {
        case let bool as Bool:
            try container.encode(bool)
        case let int as Int:
            try container.encode(int)
        case let double as Double:
            try container.encode(double)
        case let string as String:
            try container.encode(string)
        case let array as [Any]:
            try container.encode(array.map { AnyCodable($0) })
        case let dictionary as [String: Any]:
            try container.encode(dictionary.mapValues { AnyCodable($0) })
        default:
            try container.encodeNil()
        }
    }
}

// MARK: - Conversation Models

struct ConversationItem: Codable, Identifiable {
    let id: String
    let userId: String
    let title: String
    let messageCount: Int
    let isActive: Bool
    let taskId: String?
    let summary: String?
    let summaryUpdatedAt: Date?
    let createdAt: Date
    let updatedAt: Date

    enum CodingKeys: String, CodingKey {
        case id = "_id"
        case userId = "user_id"
        case title
        case messageCount = "message_count"
        case isActive = "is_active"
        case taskId = "task_id"
        case summary
        case summaryUpdatedAt = "summary_updated_at"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct ConversationListResponse: Codable {
    let conversations: [ConversationItem]
    let total: Int
}

struct ConversationMessageItem: Codable, Identifiable {
    let id: String
    let conversationId: String
    let role: String
    let content: String
    let timestamp: Date

    enum CodingKeys: String, CodingKey {
        case id = "_id"
        case conversationId = "conversation_id"
        case role, content, timestamp
    }
}

struct ConversationWithMessages: Codable {
    let id: String
    let userId: String
    let title: String
    let messageCount: Int
    let isActive: Bool
    let taskId: String?
    let createdAt: Date
    let updatedAt: Date
    let messages: [ConversationMessageItem]

    enum CodingKeys: String, CodingKey {
        case id = "_id"
        case userId = "user_id"
        case title
        case messageCount = "message_count"
        case isActive = "is_active"
        case taskId = "task_id"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case messages
    }
}
