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

    enum MessageRole: String {
        case user, assistant, system
    }

    init(id: UUID = UUID(), role: MessageRole, content: String, timestamp: Date = Date(), toolsUsed: [String]? = nil, actionsTaken: [String]? = nil) {
        self.id = id
        self.role = role
        self.content = content
        self.timestamp = timestamp
        self.toolsUsed = toolsUsed
        self.actionsTaken = actionsTaken
    }
}

struct AgentChatRequest: Codable {
    let message: String
    let context: [String: String]?
    let useMemory: Bool

    enum CodingKeys: String, CodingKey {
        case message, context
        case useMemory = "use_memory"
    }
}

struct AgentChatResponse: Codable {
    let message: String
    let toolsUsed: [String]
    let contextRetrieved: Int
    let actionsTaken: [ActionTaken]

    enum CodingKeys: String, CodingKey {
        case message
        case toolsUsed = "tools_used"
        case contextRetrieved = "context_retrieved"
        case actionsTaken = "actions_taken"
    }

    struct ActionTaken: Codable {
        let tool: String
        let args: [String: String]
        let result: [String: String]
    }
}
