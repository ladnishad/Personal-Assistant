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

    private let apiService = APIService.shared

    init() {
        // Add welcome message
        messages.append(ChatMessage(
            role: .assistant,
            content: "Hi! I'm your personal AI assistant. I can help you manage your emails, tasks, and more. How can I help you today?"
        ))
    }

    func sendMessage() async {
        guard !inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }

        let userMessage = ChatMessage(role: .user, content: inputText)
        messages.append(userMessage)

        let messageToSend = inputText
        inputText = ""
        isLoading = true

        do {
            let response = try await apiService.sendChatMessage(message: messageToSend, useMemory: true)

            let assistantMessage = ChatMessage(
                role: .assistant,
                content: response.message,
                toolsUsed: response.toolsUsed.isEmpty ? nil : response.toolsUsed,
                actionsTaken: response.actionsTaken.isEmpty ? nil : response.actionsTaken.map { $0.tool }
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
        messages.append(ChatMessage(
            role: .assistant,
            content: "Hi! I'm your personal AI assistant. How can I help you today?"
        ))
    }
}
