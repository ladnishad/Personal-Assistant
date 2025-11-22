//
//  SettingsView.swift
//  Personal Assistant
//
//  Created by LifeOS on 11/15/25.
//

import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @State private var showingLogoutAlert = false

    var body: some View {
        NavigationStack {
            List {
                // Profile Section
                Section {
                    if let user = authViewModel.currentUser {
                        HStack(spacing: 16) {
                            Image(systemName: "person.circle.fill")
                                .font(.system(size: 60))
                                .foregroundStyle(
                                    LinearGradient(
                                        colors: [.blue, .purple],
                                        startPoint: .topLeading,
                                        endPoint: .bottomTrailing
                                    )
                                )

                            VStack(alignment: .leading, spacing: 4) {
                                Text(user.fullName ?? "User")
                                    .font(.title3)
                                    .fontWeight(.semibold)

                                Text(user.email)
                                    .font(.subheadline)
                                    .foregroundColor(.secondary)

                                HStack(spacing: 4) {
                                    if user.isVerified {
                                        Image(systemName: "checkmark.seal.fill")
                                            .foregroundColor(.blue)
                                    }
                                    Text(user.isVerified ? "Verified" : "Not Verified")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                            }

                            Spacer()
                        }
                        .padding(.vertical, 8)
                    }
                }

                // Your Data Section
                Section("Your Data") {
                    NavigationLink {
                        EmailInboxView()
                    } label: {
                        HStack {
                            Label("Email Inbox", systemImage: "envelope.fill")
                            Spacer()
                        }
                    }
                }

                // Integrations Section
                Section("Integrations") {
                    NavigationLink {
                        IntegrationsView()
                    } label: {
                        Label("Connected Accounts", systemImage: "link")
                    }

                    Label("Sync Settings", systemImage: "arrow.triangle.2.circlepath")
                }

                // App Settings Section
                Section("Preferences") {
                    Label("Notifications", systemImage: "bell")
                    Label("Appearance", systemImage: "paintbrush")
                    Label("Privacy", systemImage: "hand.raised")
                }

                // About Section
                Section("About") {
                    HStack {
                        Text("Version")
                        Spacer()
                        Text("1.0.0")
                            .foregroundColor(.secondary)
                    }

                    Link(destination: URL(string: "https://github.com/yourusername/lifeos")!) {
                        Label("GitHub Repository", systemImage: "chevron.right")
                    }

                    Label("Help & Support", systemImage: "questionmark.circle")
                }

                // Account Section
                Section {
                    Button(role: .destructive, action: {
                        showingLogoutAlert = true
                    }) {
                        Label("Sign Out", systemImage: "arrow.right.square")
                    }
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.large)
            .alert("Sign Out", isPresented: $showingLogoutAlert) {
                Button("Cancel", role: .cancel) {}
                Button("Sign Out", role: .destructive) {
                    authViewModel.logout()
                }
            } message: {
                Text("Are you sure you want to sign out?")
            }
        }
    }
}

#Preview {
    SettingsView()
        .environmentObject(AuthViewModel())
}
