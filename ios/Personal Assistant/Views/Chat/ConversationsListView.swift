//
//  ConversationsListView.swift
//  Personal Assistant
//
//  Created by LifeOS on 11/17/25.
//

import SwiftUI

struct ConversationsListView: View {
    @StateObject private var viewModel = ConversationsViewModel()

    var body: some View {
        NavigationStack {
            ZStack {
                if viewModel.isLoading && viewModel.conversations.isEmpty {
                    ProgressView()
                } else if viewModel.conversations.isEmpty {
                    emptyStateView
                } else {
                    conversationsList
                }
            }
            .navigationTitle("Conversations")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    NavigationLink(destination: AgentChatView()) {
                        Image(systemName: "square.and.pencil")
                    }
                }
            }
            .task {
                await viewModel.loadConversations()
            }
            .refreshable {
                await viewModel.loadConversations()
            }
        }
    }

    private var conversationsList: some View {
        List {
            ForEach(viewModel.conversations) { conversation in
                NavigationLink(destination: AgentChatView(conversationId: conversation.id)) {
                    ConversationRowView(conversation: conversation)
                }
            }
            .onDelete { indexSet in
                for index in indexSet {
                    let conversation = viewModel.conversations[index]
                    Task {
                        await viewModel.deleteConversation(conversation)
                    }
                }
            }
        }
        .listStyle(.plain)
    }

    private var emptyStateView: some View {
        VStack(spacing: 16) {
            Image(systemName: "bubble.left.and.bubble.right")
                .font(.system(size: 60))
                .foregroundColor(.secondary)

            Text("No Conversations")
                .font(.title2)
                .fontWeight(.semibold)

            Text("Start your first conversation with your AI assistant")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)

            NavigationLink(destination: AgentChatView()) {
                Label("New Chat", systemImage: "square.and.pencil")
                    .fontWeight(.medium)
            }
            .buttonStyle(.borderedProminent)
            .padding(.top)
        }
        .padding()
    }
}

struct ConversationRowView: View {
    let conversation: ConversationItem

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(conversation.title)
                        .font(.body)
                        .fontWeight(.medium)
                        .lineLimit(1)

                    if let summary = conversation.summary {
                        Text(summary)
                            .font(.caption)
                            .foregroundColor(.secondary)
                            .lineLimit(2)
                    }

                    HStack(spacing: 12) {
                        HStack(spacing: 4) {
                            Image(systemName: "bubble.left")
                            Text("\(conversation.messageCount)")
                        }
                        .font(.caption2)
                        .foregroundColor(.secondary)

                        Text(conversation.updatedAt, style: .relative)
                            .font(.caption2)
                            .foregroundColor(.secondary)

                        if conversation.isActive {
                            HStack(spacing: 2) {
                                Circle()
                                    .fill(.green)
                                    .frame(width: 6, height: 6)
                                Text("Active")
                            }
                            .font(.caption2)
                            .foregroundColor(.green)
                        }
                    }
                }

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .padding(.vertical, 8)
    }
}

#Preview {
    ConversationsListView()
}
