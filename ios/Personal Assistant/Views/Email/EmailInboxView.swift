//
//  EmailInboxView.swift
//  Personal Assistant
//
//  Created by LifeOS on 11/15/25.
//

import SwiftUI

struct EmailInboxView: View {
    @StateObject private var viewModel = EmailViewModel()
    @State private var showingSearchBar = false
    @State private var selectedEmail: Email?
    @State private var showingClassifyAlert = false
    @State private var showingClassifyResults = false
    @State private var singleClassifyResult: EmailClassifyResponse?
    @State private var showingSingleClassifyResult = false

    var body: some View {
        NavigationStack {
            ZStack {
                if viewModel.isLoading && viewModel.emails.isEmpty {
                    ProgressView()
                } else if viewModel.emails.isEmpty {
                    emptyStateView
                } else {
                    emailList
                }
            }
            .navigationTitle("Inbox")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    HStack(spacing: 16) {
                        Button(action: {
                            showingSearchBar.toggle()
                        }) {
                            Image(systemName: "magnifyingglass")
                        }

                        Button(action: {
                            viewModel.toggleUnreadFilter()
                        }) {
                            Image(systemName: viewModel.showUnreadOnly ? "envelope.badge.fill" : "envelope.badge")
                                .foregroundColor(viewModel.showUnreadOnly ? .blue : .primary)
                        }

                        // 🧪 EXPERIMENTAL: Classify all emails button
                        Button(action: {
                            showingClassifyAlert = true
                        }) {
                            if viewModel.isClassifying {
                                ProgressView()
                            } else {
                                Image(systemName: "brain")
                                    .foregroundColor(.purple)
                            }
                        }
                        .disabled(viewModel.isClassifying)

                        Button(action: {
                            Task {
                                await viewModel.syncEmails()
                            }
                        }) {
                            if viewModel.isSyncing {
                                ProgressView()
                            } else {
                                Image(systemName: "arrow.clockwise")
                            }
                        }
                        .disabled(viewModel.isSyncing)
                    }
                }
            }
            .searchable(text: $viewModel.searchText, isPresented: $showingSearchBar, prompt: "Search emails")
            .onChange(of: viewModel.searchText) { _, _ in
                Task {
                    await viewModel.loadEmails()
                }
            }
            .task {
                await viewModel.loadEmails()
            }
            .refreshable {
                await viewModel.loadEmails()
            }
            .sheet(item: $selectedEmail) { email in
                EmailDetailView(email: email)
            }
            .alert("🧪 Classify All Emails", isPresented: $showingClassifyAlert) {
                Button("Cancel", role: .cancel) {}
                Button("Classify Unclassified") {
                    Task {
                        await viewModel.classifyAllEmails(forceReclassify: false)
                        showingClassifyResults = true
                    }
                }
                Button("Re-classify All", role: .destructive) {
                    Task {
                        await viewModel.classifyAllEmails(forceReclassify: true)
                        showingClassifyResults = true
                    }
                }
            } message: {
                Text("This experimental feature uses AI to categorize your emails. Choose whether to classify only new emails or re-classify all emails.")
            }
            .alert("Classification Complete", isPresented: $showingClassifyResults) {
                Button("OK", role: .cancel) {}
            } message: {
                if let result = viewModel.classificationResult {
                    Text("""
                    ✅ Classified: \(result.classifiedCount)
                    ⏭️ Skipped: \(result.skippedCount)
                    ❌ Errors: \(result.errorCount)
                    ⏱️ Duration: \(String(format: "%.1f", result.durationSeconds))s

                    Categories:
                    \(categoryBreakdown(result.categories))
                    """)
                } else {
                    Text("No results available")
                }
            }
            .alert("Email Classified", isPresented: $showingSingleClassifyResult) {
                Button("OK", role: .cancel) {}
            } message: {
                if let result = singleClassifyResult {
                    Text("""
                    📧 Category: \(result.category)
                    📊 Confidence: \(String(format: "%.0f", result.confidence * 100))%

                    💭 Reasoning:
                    \(result.reasoning)
                    """)
                } else {
                    Text("No classification result available")
                }
            }
        }
    }

    private func categoryBreakdown(_ categories: [String: Int]) -> String {
        categories
            .sorted { $0.value > $1.value }
            .map { "• \($0.key): \($0.value)" }
            .joined(separator: "\n")
    }

    private var emailList: some View {
        List {
            ForEach(viewModel.emails) { email in
                EmailRowView(email: email)
                    .contentShape(Rectangle())
                    .onTapGesture {
                        selectedEmail = email
                        Task {
                            await viewModel.markAsRead(email)
                        }
                    }
                    .contextMenu {
                        Button {
                            Task {
                                if let result = await viewModel.classifySingleEmail(email, forceReclassify: false) {
                                    singleClassifyResult = result
                                    showingSingleClassifyResult = true
                                }
                            }
                        } label: {
                            Label("🧪 Classify Email", systemImage: "brain")
                        }

                        Button {
                            Task {
                                if let result = await viewModel.classifySingleEmail(email, forceReclassify: true) {
                                    singleClassifyResult = result
                                    showingSingleClassifyResult = true
                                }
                            }
                        } label: {
                            Label("🔄 Re-classify Email", systemImage: "arrow.clockwise")
                        }

                        Divider()

                        Button {
                            Task {
                                await viewModel.markAsRead(email)
                            }
                        } label: {
                            Label(email.isRead ? "Mark as Unread" : "Mark as Read", systemImage: email.isRead ? "envelope.badge" : "envelope.open")
                        }
                    }
            }
        }
        .listStyle(.plain)
    }

    private var emptyStateView: some View {
        VStack(spacing: 16) {
            Image(systemName: "envelope.open")
                .font(.system(size: 60))
                .foregroundColor(.secondary)

            Text("No Emails")
                .font(.title2)
                .fontWeight(.semibold)

            Text("Sync your email accounts to get started")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)

            Button(action: {
                Task {
                    await viewModel.syncEmails()
                }
            }) {
                Label("Sync Now", systemImage: "arrow.clockwise")
                    .fontWeight(.medium)
            }
            .buttonStyle(.borderedProminent)
            .padding(.top)
        }
        .padding()
    }
}

struct EmailRowView: View {
    let email: Email

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(email.fromName ?? email.fromEmail)
                        .font(.subheadline)
                        .fontWeight(email.isRead ? .regular : .semibold)
                        .foregroundColor(email.isRead ? .secondary : .primary)

                    Text(email.subject ?? "(No Subject)")
                        .font(.body)
                        .fontWeight(email.isRead ? .regular : .medium)
                        .lineLimit(1)
                }

                Spacer()

                VStack(alignment: .trailing, spacing: 4) {
                    Text(email.receivedAt, style: .relative)
                        .font(.caption)
                        .foregroundColor(.secondary)

                    if email.isStarred {
                        Image(systemName: "star.fill")
                            .font(.caption)
                            .foregroundColor(.yellow)
                    }

                    if !email.isRead {
                        Circle()
                            .fill(.blue)
                            .frame(width: 8, height: 8)
                    }
                }
            }

            if let snippet = email.snippet {
                Text(snippet)
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .lineLimit(2)
            }

            if email.hasAttachments {
                HStack(spacing: 4) {
                    Image(systemName: "paperclip")
                    Text("\(email.attachments.count) attachment\(email.attachments.count > 1 ? "s" : "")")
                }
                .font(.caption2)
                .foregroundColor(.secondary)
            }
        }
        .padding(.vertical, 8)
    }
}

#Preview {
    EmailInboxView()
}
