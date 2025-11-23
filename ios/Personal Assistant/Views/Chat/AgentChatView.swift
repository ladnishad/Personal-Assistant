//
//  AgentChatView.swift
//  Personal Assistant
//
//  Created by LifeOS on 11/15/25.
//

import SwiftUI

struct AgentChatView: View {
    @StateObject private var viewModel: ChatViewModel
    @StateObject private var pollingService = ConfirmationPollingService.shared
    @FocusState private var isInputFocused: Bool
    @State private var showingConfirmation = false
    @State private var currentConfirmation: PendingConfirmation?
    @State private var confirmationQueue: [PendingConfirmation] = []
    @State private var processedConfirmationIds = Set<String>()

    init(conversationId: String? = nil) {
        _viewModel = StateObject(wrappedValue: ChatViewModel(conversationId: conversationId))
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Messages
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 16) {
                            ForEach(viewModel.messages) { message in
                                MessageBubble(message: message)
                                    .id(message.id)
                            }

                            if viewModel.isLoading {
                                HStack(alignment: .top, spacing: 12) {
                                    // AI Avatar
                                    ZStack {
                                        Circle()
                                            .fill(LinearGradient(
                                                colors: [.blue.opacity(0.6), .purple.opacity(0.6)],
                                                startPoint: .topLeading,
                                                endPoint: .bottomTrailing
                                            ))
                                            .frame(width: 32, height: 32)

                                        Image(systemName: "sparkles")
                                            .font(.system(size: 14))
                                            .foregroundColor(.white)
                                    }

                                    VStack(alignment: .leading, spacing: 10) {
                                        // Streaming message bubble (only if there's content)
                                        if !viewModel.streamingMessage.isEmpty {
                                            if let attributedString = try? AttributedString(markdown: viewModel.streamingMessage) {
                                                Text(attributedString)
                                                    .font(.body)
                                                    .padding(14)
                                                    .background(
                                                        RoundedRectangle(cornerRadius: 18, style: .continuous)
                                                            .fill(Color(.systemGray6))
                                                    )
                                                    .textSelection(.enabled)
                                            } else {
                                                Text(viewModel.streamingMessage)
                                                    .font(.body)
                                                    .padding(14)
                                                    .background(
                                                        RoundedRectangle(cornerRadius: 18, style: .continuous)
                                                            .fill(Color(.systemGray6))
                                                    )
                                                    .foregroundColor(.primary)
                                            }
                                        }

                                        // Real-time screenshots during streaming
                                        if !viewModel.currentScreenshots.isEmpty {
                                            ScreenshotGalleryView(screenshots: viewModel.currentScreenshots)
                                                .transition(.scale.combined(with: .opacity))
                                        }

                                        // Agent status indicator
                                        if let status = viewModel.agentStatus {
                                            HStack(spacing: 6) {
                                                ProgressView()
                                                    .scaleEffect(0.7)

                                                Text(status)
                                                    .font(.caption)
                                                    .foregroundColor(.secondary)
                                            }
                                            .padding(.horizontal, 10)
                                            .padding(.vertical, 6)
                                            .background(
                                                Capsule()
                                                    .fill(Color(.systemGray5).opacity(0.5))
                                            )
                                        }
                                    }

                                    Spacer(minLength: 50)
                                }
                                .padding(.horizontal)
                            }
                        }
                        .padding()
                    }
                    .onChange(of: viewModel.messages.count) { _, _ in
                        if let lastMessage = viewModel.messages.last {
                            withAnimation {
                                proxy.scrollTo(lastMessage.id, anchor: .bottom)
                            }
                        }
                    }
                    .onChange(of: viewModel.streamingMessage) { _, _ in
                        // Auto-scroll as streaming message updates
                        if viewModel.isLoading, let lastMessage = viewModel.messages.last {
                            withAnimation(.easeOut(duration: 0.2)) {
                                proxy.scrollTo(lastMessage.id, anchor: .bottom)
                            }
                        }
                    }
                }

                Divider()

                // Input area
                HStack(spacing: 12) {
                    TextField("Ask me anything...", text: $viewModel.inputText, axis: .vertical)
                        .textFieldStyle(.plain)
                        .padding(12)
                        .background(Color(.systemGray6))
                        .cornerRadius(20)
                        .lineLimit(1...4)
                        .focused($isInputFocused)

                    Button(action: {
                        Task {
                            await viewModel.sendMessage()
                        }
                    }) {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.title2)
                            .foregroundStyle(
                                viewModel.inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ?
                                    LinearGradient(colors: [.gray], startPoint: .leading, endPoint: .trailing) :
                                    LinearGradient(colors: [.blue, .purple], startPoint: .leading, endPoint: .trailing)
                            )
                    }
                    .disabled(viewModel.inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || viewModel.isLoading)
                }
                .padding()
            }
            .navigationTitle("AI Assistant")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    let unprocessedCount = pollingService.pendingConfirmations.filter {
                        !processedConfirmationIds.contains($0.id)
                    }.count

                    if unprocessedCount > 0 || !confirmationQueue.isEmpty {
                        Button(action: {
                            // Add all pending confirmations to queue if not already there
                            for confirmation in pollingService.pendingConfirmations {
                                if !processedConfirmationIds.contains(confirmation.id) &&
                                   !confirmationQueue.contains(where: { $0.id == confirmation.id }) {
                                    confirmationQueue.append(confirmation)
                                }
                            }

                            // Show next confirmation
                            if !showingConfirmation {
                                showNextConfirmation()
                            }
                        }) {
                            HStack(spacing: 4) {
                                Image(systemName: "exclamationmark.circle.fill")
                                    .foregroundColor(.orange)
                                Text("\(max(unprocessedCount, confirmationQueue.count))")
                                    .font(.caption)
                                    .fontWeight(.semibold)
                            }
                        }
                    }
                }

                ToolbarItem(placement: .navigationBarTrailing) {
                    Menu {
                        Button(action: {
                            viewModel.clearChat()
                        }) {
                            Label("Clear Chat", systemImage: "trash")
                        }
                    } label: {
                        Image(systemName: "ellipsis.circle")
                    }
                }
            }
            .task {
                // Load conversation if conversationId is provided
                if let conversationId = viewModel.conversationId, viewModel.messages.isEmpty {
                    await viewModel.loadConversation(id: conversationId)
                }
            }
            .onAppear {
                // Start polling for confirmations
                pollingService.startPolling()
            }
            .onDisappear {
                // Stop polling when view disappears
                pollingService.stopPolling()
            }
            .onChange(of: pollingService.pendingConfirmations) { oldValue, newValue in
                // Find all new confirmations (not just the first)
                let newConfirmations = newValue.filter { confirmation in
                    !oldValue.contains(where: { $0.id == confirmation.id }) &&
                    !processedConfirmationIds.contains(confirmation.id)
                }

                // Add new confirmations to queue
                for confirmation in newConfirmations {
                    if !confirmationQueue.contains(where: { $0.id == confirmation.id }) {
                        confirmationQueue.append(confirmation)
                    }
                }

                // Show next confirmation if not already showing one
                if !showingConfirmation && !confirmationQueue.isEmpty {
                    showNextConfirmation()
                }
            }
            .sheet(isPresented: $showingConfirmation) {
                if let confirmation = currentConfirmation {
                    ConfirmationSheet(
                        confirmation: confirmation,
                        isPresented: $showingConfirmation,
                        onDismiss: {
                            // Mark as processed and show next if any
                            if let current = currentConfirmation {
                                processedConfirmationIds.insert(current.id)
                                confirmationQueue.removeAll { $0.id == current.id }
                            }
                            currentConfirmation = nil

                            // Show next confirmation after a brief delay
                            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                                if !confirmationQueue.isEmpty {
                                    showNextConfirmation()
                                }
                            }
                        }
                    )
                }
            }
        }
    }

    private func showNextConfirmation() {
        guard !confirmationQueue.isEmpty else { return }

        // Get next confirmation that hasn't been processed
        if let next = confirmationQueue.first(where: { !processedConfirmationIds.contains($0.id) }) {
            currentConfirmation = next
            showingConfirmation = true
        }
    }
}

struct MessageBubble: View {
    let message: ChatMessage
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            if message.role == .user {
                Spacer(minLength: 50)
            } else {
                aiAvatar
            }

            VStack(alignment: message.role == .user ? .trailing : .leading, spacing: 10) {
                messageContentView

                // Show screenshots from computer control agent
                if let screenshots = message.screenshots, !screenshots.isEmpty {
                    ScreenshotGalleryView(screenshots: screenshots)
                        .transition(.scale.combined(with: .opacity))
                }

                if let taskRef = message.taskReference {
                    TaskReferenceCard(taskReference: taskRef)
                        .transition(.scale.combined(with: .opacity))
                }

                if let toolsUsed = message.toolsUsed, !toolsUsed.isEmpty {
                    toolsBadge(toolsUsed)
                }

                timestampView
            }

            if message.role == .assistant {
                Spacer(minLength: 50)
            }
        }
    }

    private var aiAvatar: some View {
        ZStack {
            Circle()
                .fill(LinearGradient(
                    colors: [.blue.opacity(0.6), .purple.opacity(0.6)],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                ))
                .frame(width: 32, height: 32)

            Image(systemName: "sparkles")
                .font(.system(size: 14))
                .foregroundColor(.white)
        }
    }

    @ViewBuilder
    private var messageContentView: some View {
        if message.role == .assistant {
            if let attributedString = try? AttributedString(markdown: message.content) {
                Text(attributedString)
                    .font(.body)
                    .padding(14)
                    .background(assistantBubbleBackground)
                    .textSelection(.enabled)
            } else {
                Text(message.content)
                    .font(.body)
                    .padding(14)
                    .background(assistantBubbleBackground)
                    .foregroundColor(.primary)
            }
        } else {
            Text(message.content)
                .font(.body)
                .padding(14)
                .background(userBubbleBackground)
                .foregroundColor(.white)
        }
    }

    private var assistantBubbleBackground: some View {
        RoundedRectangle(cornerRadius: 18, style: .continuous)
            .fill(colorScheme == .dark ? Color(.systemGray6).opacity(0.6) : Color(.systemGray6))
    }

    private var userBubbleBackground: some View {
        RoundedRectangle(cornerRadius: 18, style: .continuous)
            .fill(LinearGradient(
                colors: [.blue, .purple],
                startPoint: .leading,
                endPoint: .trailing
            ))
    }

    private func toolsBadge(_ tools: [String]) -> some View {
        HStack(spacing: 6) {
            Image(systemName: "sparkles.rectangle.stack")
                .font(.caption2)

            Text(tools.map { formatToolName($0) }.joined(separator: " • "))
                .font(.caption2)
        }
        .foregroundColor(.secondary)
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(
            Capsule()
                .fill(Color(.systemGray5).opacity(0.5))
        )
    }

    private var timestampView: some View {
        Text(message.timestamp, style: .time)
            .font(.caption2)
            .foregroundColor(.secondary.opacity(0.7))
            .padding(.horizontal, 4)
    }

    private func formatToolName(_ tool: String) -> String {
        switch tool {
        case "create_task": return "Created task"
        case "update_task_content": return "Updated task"
        case "get_tasks": return "Retrieved tasks"
        case "search_memory": return "Searched memory"
        case "save_memory": return "Saved memory"
        case "search_emails": return "Searched emails"
        default: return tool.replacingOccurrences(of: "_", with: " ").capitalized
        }
    }
}

// MARK: - Task Reference Card
struct TaskReferenceCard: View {
    let taskReference: ChatMessage.TaskReference
    @Environment(\.colorScheme) private var colorScheme
    @State private var isPressed = false

    var body: some View {
        NavigationLink(destination: TaskDetailView(taskId: taskReference.taskId)) {
            HStack(spacing: 12) {
                // Icon based on action
                ZStack {
                    Circle()
                        .fill(actionColor.opacity(0.15))
                        .frame(width: 40, height: 40)

                    Image(systemName: actionIcon)
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundColor(actionColor)
                }

                VStack(alignment: .leading, spacing: 4) {
                    Text(actionText)
                        .font(.caption)
                        .fontWeight(.medium)
                        .foregroundColor(.secondary)

                    Text(taskReference.taskTitle)
                        .font(.body)
                        .fontWeight(.semibold)
                        .foregroundColor(.primary)
                        .lineLimit(2)

                    HStack(spacing: 4) {
                        Text("View task")
                            .font(.caption)
                            .foregroundColor(.blue)

                        Image(systemName: "arrow.right")
                            .font(.caption2)
                            .foregroundColor(.blue)
                    }
                }

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.caption)
                    .foregroundColor(.secondary.opacity(0.5))
            }
            .padding(14)
            .background(
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .fill(colorScheme == .dark ? Color(.systemGray5).opacity(0.3) : .white)
                    .shadow(color: .black.opacity(colorScheme == .dark ? 0.3 : 0.08), radius: 8, x: 0, y: 2)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .strokeBorder(actionColor.opacity(0.2), lineWidth: 1)
            )
            .scaleEffect(isPressed ? 0.97 : 1.0)
            .animation(.spring(response: 0.3, dampingFraction: 0.6), value: isPressed)
        }
        .buttonStyle(.plain)
        .simultaneousGesture(
            DragGesture(minimumDistance: 0)
                .onChanged { _ in isPressed = true }
                .onEnded { _ in isPressed = false }
        )
    }

    private var actionColor: Color {
        switch taskReference.action {
        case "created": return .green
        case "updated": return .blue
        case "completed": return .purple
        default: return .orange
        }
    }

    private var actionIcon: String {
        switch taskReference.action {
        case "created": return "plus.circle.fill"
        case "updated": return "doc.text.fill"
        case "completed": return "checkmark.circle.fill"
        default: return "pencil.circle.fill"
        }
    }

    private var actionText: String {
        switch taskReference.action {
        case "created": return "CREATED TASK"
        case "updated": return "UPDATED TASK"
        case "completed": return "COMPLETED TASK"
        default: return "TASK ACTION"
        }
    }
}

#Preview {
    AgentChatView()
}
