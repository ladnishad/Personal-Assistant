//
//  ChatViewModel.swift
//  Personal Assistant
//
//  Created by LifeOS on 11/15/25.
//

import Foundation
import Combine

@MainActor
class ChatViewModel: ObservableObject {
    @Published var messages: [ChatMessage] = []
    @Published var inputText = ""
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var conversationId: String?

    private let apiService = APIService.shared
    private let taskId: String?

    init(conversationId: String? = nil, taskId: String? = nil) {
        self.conversationId = conversationId
        self.taskId = taskId

        if conversationId == nil {
            // Add welcome message for new conversations
            let welcomeMessage = taskId != nil ?
                "Hi! Let's work on this task together. How can I help you?" :
                "Hi! I'm your personal AI assistant. I can help you manage your emails, tasks, and more. How can I help you today?"

            messages.append(ChatMessage(
                role: .assistant,
                content: welcomeMessage
            ))
        }
    }

    func loadConversation(id: String) async {
        isLoading = true
        errorMessage = nil

        do {
            let conversation = try await apiService.getConversation(id: id)
            conversationId = conversation.id

            // Convert API messages to ChatMessage objects
            messages = conversation.messages.map { msg in
                ChatMessage(
                    role: msg.role == "user" ? .user : .assistant,
                    content: msg.content,
                    timestamp: msg.timestamp
                )
            }
        } catch let error as APIError {
            errorMessage = error.errorDescription
        } catch {
            errorMessage = "Failed to load conversation"
        }

        isLoading = false
    }

    func sendMessage() async {
        guard !inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }

        let userMessage = ChatMessage(role: .user, content: inputText)
        messages.append(userMessage)

        let messageToSend = inputText
        inputText = ""
        isLoading = true

        do {
            // Build conversation history (last 15 messages, excluding the one we just added)
            let historyMessages: [ConversationHistoryMessage]
            if messages.count > 1 {
                // Get last 15 messages before the current one (or all if less than 16)
                let startIndex = max(0, messages.count - 16)
                let endIndex = messages.count - 1 // Exclude the message we just added
                historyMessages = messages[startIndex..<endIndex].map { msg in
                    ConversationHistoryMessage(
                        role: msg.role.rawValue,
                        content: msg.content
                    )
                }
            } else {
                historyMessages = []
            }

            let response = try await apiService.sendChatMessage(
                message: messageToSend,
                useMemory: true,
                conversationId: conversationId,
                conversationHistory: historyMessages.isEmpty ? nil : historyMessages
            )

            // Store conversation ID
            conversationId = response.conversationId

            let taskRef: ChatMessage.TaskReference? = if let taskRefResp = response.taskReference {
                ChatMessage.TaskReference(
                    taskId: taskRefResp.taskId,
                    taskTitle: taskRefResp.taskTitle,
                    action: taskRefResp.action
                )
            } else {
                nil
            }

            let assistantMessage = ChatMessage(
                role: .assistant,
                content: response.message,
                toolsUsed: response.toolsUsed.isEmpty ? nil : response.toolsUsed,
                actionsTaken: response.actionsTaken.isEmpty ? nil : response.actionsTaken.map { $0.tool },
                taskReference: taskRef
            )
            messages.append(assistantMessage)
        } catch let error as APIError {
            errorMessage = error.errorDescription
            // Add error message to chat
            let errorMsg = ChatMessage(
                role: .assistant,
                content: "I'm sorry, I encountered an error: \(error.errorDescription ?? "Unknown error")"
            )
            messages.append(errorMsg)
        } catch {
            errorMessage = "Failed to send message"
        }

        isLoading = false
    }

    func clearChat() {
        messages.removeAll()
        conversationId = nil // Start a new conversation
        messages.append(ChatMessage(
            role: .assistant,
            content: "Hi! I'm your personal AI assistant. How can I help you today?"
        ))
    }
}
