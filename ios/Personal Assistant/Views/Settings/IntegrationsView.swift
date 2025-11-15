//
//  IntegrationsView.swift
//  Personal Assistant
//
//  Created by LifeOS on 11/15/25.
//

import SwiftUI

struct IntegrationsView: View {
    @State private var connectedAccounts: [IntegrationItem] = []

    var body: some View {
        List {
            Section {
                Text("Connect your email and calendar accounts to sync your data with LifeOS.")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }

            Section("Available Integrations") {
                IntegrationRowView(
                    icon: "envelope.fill",
                    name: "Gmail",
                    color: .red,
                    isConnected: false,
                    action: {}
                )

                IntegrationRowView(
                    icon: "envelope.fill",
                    name: "Outlook",
                    color: .blue,
                    isConnected: false,
                    action: {}
                )

                IntegrationRowView(
                    icon: "calendar",
                    name: "Google Calendar",
                    color: .green,
                    isConnected: false,
                    action: {}
                )

                IntegrationRowView(
                    icon: "calendar",
                    name: "Outlook Calendar",
                    color: .blue,
                    isConnected: false,
                    action: {}
                )
            }

            Section {
                Text("Note: OAuth integration requires the backend API to be running. This is a placeholder UI.")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .navigationTitle("Integrations")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct IntegrationRowView: View {
    let icon: String
    let name: String
    let color: Color
    let isConnected: Bool
    let action: () -> Void

    var body: some View {
        HStack(spacing: 16) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(.white)
                .frame(width: 44, height: 44)
                .background(color)
                .cornerRadius(8)

            VStack(alignment: .leading, spacing: 2) {
                Text(name)
                    .font(.body)
                    .fontWeight(.medium)

                if isConnected {
                    HStack(spacing: 4) {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundColor(.green)
                        Text("Connected")
                            .foregroundColor(.secondary)
                    }
                    .font(.caption)
                } else {
                    Text("Not connected")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }

            Spacer()

            Button(action: action) {
                Text(isConnected ? "Disconnect" : "Connect")
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .foregroundColor(isConnected ? .red : .blue)
            }
        }
        .padding(.vertical, 4)
    }
}

struct IntegrationItem {
    let id: String
    let name: String
    let type: String
    let isActive: Bool
}

#Preview {
    NavigationStack {
        IntegrationsView()
    }
}
