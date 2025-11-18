//
//  ConversationsViewModel.swift
//  Personal Assistant
//
//  Created by LifeOS on 11/17/25.
//

import Foundation
import Combine

@MainActor
class ConversationsViewModel: ObservableObject {
    @Published var conversations: [ConversationItem] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let apiService = APIService.shared

    func loadConversations() async {
        isLoading = true
        errorMessage = nil

        do {
            let response = try await apiService.getConversations()
            conversations = response.conversations
        } catch let error as APIError {
            errorMessage = error.errorDescription
        } catch {
            errorMessage = "Failed to load conversations"
        }

        isLoading = false
    }

    func deleteConversation(_ conversation: ConversationItem) async {
        do {
            try await apiService.deleteConversation(id: conversation.id)
            // Remove from local list
            conversations.removeAll { $0.id == conversation.id }
        } catch let error as APIError {
            errorMessage = error.errorDescription
        } catch {
            errorMessage = "Failed to delete conversation"
        }
    }
}
