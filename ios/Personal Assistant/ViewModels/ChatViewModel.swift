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
    @Published var agentStatus: String?
    @Published var activeTool: String?
    @Published var streamingMessage: String = ""
    @Published var taskWasUpdated = false
    @Published var currentScreenshots: [ScreenshotCapture] = []

    private let apiService = APIService.shared
    private let taskId: String?
    private let task: TaskItem?

    init(conversationId: String? = nil, taskId: String? = nil, task: TaskItem? = nil) {
        self.conversationId = conversationId
        self.taskId = taskId
        self.task = task

        if conversationId == nil && taskId == nil {
            // Add welcome message for new conversations (only for main chat, not task chats)
            messages.append(ChatMessage(
                role: .assistant,
                content: "Hi! I'm your personal AI assistant. I can help you manage your emails, tasks, and more. How can I help you today?"
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

    func loadConversationForTask() async {
        guard let taskId = taskId else { return }

        isLoading = true
        errorMessage = nil

        do {
            let conversation = try await apiService.getConversationByTask(taskId: taskId)
            conversationId = conversation.id

            // Convert API messages to ChatMessage objects
            messages = conversation.messages.map { msg in
                ChatMessage(
                    role: msg.role == "user" ? .user : .assistant,
                    content: msg.content,
                    timestamp: msg.timestamp
                )
            }

            // If no messages, add a welcome message
            if messages.isEmpty {
                messages.append(ChatMessage(
                    role: .assistant,
                    content: "Hi! Let's work on this task together. How can I help you?"
                ))
            }
        } catch {
            // No conversation found for this task yet - that's okay
            // Add welcome message for new task conversations
            messages.append(ChatMessage(
                role: .assistant,
                content: "Hi! Let's work on this task together. How can I help you?"
            ))
        }

        isLoading = false
    }

    func sendMessage() async {
        guard !inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }

        let userMessage = ChatMessage(role: .user, content: inputText)
        messages.append(userMessage)

        // Build message with task context if available
        var messageToSend = inputText
        if let task = task {
            let taskContext = """
            [Task Context]
            Task ID: \(task.id)
            Title: \(task.title)
            \(task.description != nil ? "Description: \(task.description!)" : "")
            Status: \(task.status.rawValue)
            Priority: \(task.priority.rawValue)

            User message: \(inputText)
            """
            messageToSend = taskContext
        }

        inputText = ""
        isLoading = true
        streamingMessage = ""
        agentStatus = "Thinking..."
        activeTool = nil
        taskWasUpdated = false
        currentScreenshots = []

        do {
            print("🚀 Starting streaming...")
            let eventStream = apiService.sendChatMessageStreaming(
                message: messageToSend,
                useMemory: true,
                conversationId: conversationId,
                taskId: taskId,
                streamScreenshots: true  // Enable screenshot streaming
            )

            var finalConversationId: String?
            var toolsUsed: [String] = []
            var actionsTaken: [AgentChatResponse.ActionTaken] = []
            var taskReference: AgentChatResponse.TaskReferenceResponse?

            for try await event in eventStream {
                print("📨 Received event: \(event)")
                switch event {
                case .agentStatus(let status, let message):
                    print("🔔 Status: \(message ?? status)")
                    agentStatus = message ?? status.capitalized

                case .toolCall(let toolName, _, _):
                    let friendlyName = formatToolName(toolName)
                    activeTool = friendlyName
                    agentStatus = "Using \(friendlyName)..."

                    // Detect if task is being updated
                    if toolName == "update_task_content" {
                        agentStatus = "Updating task..."
                    }

                case .toolResult(let toolName, _, _):
                    activeTool = nil
                    agentStatus = "Processing results..."

                    // Mark that task was updated
                    if toolName == "update_task_content" {
                        taskWasUpdated = true
                    }

                case .screenshotCapture(let screenshot):
                    print("📸 Received screenshot: \(screenshot.actionContext ?? "no context")")
                    currentScreenshots.append(screenshot)

                case .messageDelta(let delta):
                    streamingMessage += delta

                case .messageComplete(let message):
                    streamingMessage = message
                    agentStatus = nil

                case .done(let convId, let tools, let actions, let taskRef):
                    finalConversationId = convId
                    toolsUsed = tools
                    actionsTaken = actions
                    taskReference = taskRef

                case .error(let error):
                    throw APIError.serverError(error)
                }
            }

            // Store conversation ID
            if let convId = finalConversationId {
                conversationId = convId
            }

            let taskRef: ChatMessage.TaskReference? = if let taskRefResp = taskReference {
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
                content: streamingMessage,
                toolsUsed: toolsUsed.isEmpty ? nil : toolsUsed,
                actionsTaken: actionsTaken.isEmpty ? nil : actionsTaken.map { $0.tool },
                taskReference: taskRef,
                screenshots: currentScreenshots.isEmpty ? nil : currentScreenshots
            )
            messages.append(assistantMessage)

            // Clear streaming state
            streamingMessage = ""
            agentStatus = nil
            activeTool = nil
            currentScreenshots = []

        } catch let error as APIError {
            errorMessage = error.errorDescription
            // Add error message to chat
            let errorMsg = ChatMessage(
                role: .assistant,
                content: "I'm sorry, I encountered an error: \(error.errorDescription ?? "Unknown error")"
            )
            messages.append(errorMsg)

            // Clear streaming state
            streamingMessage = ""
            agentStatus = nil
            activeTool = nil
        } catch {
            errorMessage = "Failed to send message"

            // Clear streaming state
            streamingMessage = ""
            agentStatus = nil
            activeTool = nil
        }

        isLoading = false
    }

    private func formatToolName(_ tool: String) -> String {
        switch tool {
        case "create_task": return "Creating task"
        case "update_task_content": return "Updating task"
        case "get_tasks": return "Retrieving tasks"
        case "search_memory": return "Searching memory"
        case "save_memory": return "Saving memory"
        case "search_emails": return "Searching emails"
        case "get_recent_emails": return "Getting emails"
        case "web_search": return "Web search"
        default: return tool.replacingOccurrences(of: "_", with: " ").capitalized
        }
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
