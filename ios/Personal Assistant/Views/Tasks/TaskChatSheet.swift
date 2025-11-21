//
//  TaskChatSheet.swift
//  Personal Assistant
//
//  Created by LifeOS
//

import SwiftUI

struct TaskChatSheet: View {
    let taskId: String
    let task: TaskItem
    @StateObject private var viewModel: ChatViewModel
    @FocusState private var isInputFocused: Bool
    @Environment(\.dismiss) private var dismiss

    // Callback to notify parent when task is updated
    var onTaskUpdated: (() -> Void)?

    init(taskId: String, task: TaskItem, onTaskUpdated: (() -> Void)? = nil) {
        self.taskId = taskId
        self.task = task
        self.onTaskUpdated = onTaskUpdated
        _viewModel = StateObject(wrappedValue: ChatViewModel(taskId: taskId, task: task))
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
                    .onChange(of: viewModel.taskWasUpdated) { _, wasUpdated in
                        // Notify parent when task is updated
                        if wasUpdated {
                            onTaskUpdated?()
                        }
                    }
                }

                Divider()

                // Input area
                HStack(spacing: 12) {
                    TextField("Ask about this task...", text: $viewModel.inputText, axis: .vertical)
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
            .navigationTitle(task.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
            .task {
                // Load conversation for this task if it exists
                await viewModel.loadConversationForTask()
            }
        }
    }
}

#Preview {
    TaskChatSheet(
        taskId: "preview-task-id",
        task: TaskItem(
            id: "preview-task-id",
            userId: "user-id",
            title: "Plan Austin trip",
            description: "Research and plan trip to Austin",
            status: .todo,
            priority: .medium,
            dueDate: nil,
            completedAt: nil,
            reminderAt: nil,
            reminderSent: false,
            tags: ["travel"],
            category: "planning",
            content: nil,
            createdAt: Date(),
            updatedAt: Date()
        )
    )
}
