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
        }
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
