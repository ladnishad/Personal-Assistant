//
//  EmailDetailView.swift
//  Personal Assistant
//
//  Created by LifeOS on 11/15/25.
//

import SwiftUI

struct EmailDetailView: View {
    @Environment(\.dismiss) var dismiss
    let email: Email

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // Header
                    VStack(alignment: .leading, spacing: 12) {
                        Text(email.subject ?? "(No Subject)")
                            .font(.title2)
                            .fontWeight(.bold)

                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                HStack {
                                    Text("From:")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                    Text(email.fromName ?? email.fromEmail)
                                        .font(.subheadline)
                                }

                                if !email.to.isEmpty {
                                    HStack {
                                        Text("To:")
                                            .font(.caption)
                                            .foregroundColor(.secondary)
                                        Text(email.to.joined(separator: ", "))
                                            .font(.subheadline)
                                            .lineLimit(1)
                                    }
                                }

                                if !email.cc.isEmpty {
                                    HStack {
                                        Text("CC:")
                                            .font(.caption)
                                            .foregroundColor(.secondary)
                                        Text(email.cc.joined(separator: ", "))
                                            .font(.subheadline)
                                            .lineLimit(1)
                                    }
                                }
                            }

                            Spacer()

                            Text(email.receivedAt, style: .date)
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                    .padding()
                    .background(Color(.systemGray6))
                    .cornerRadius(12)

                    // Attachments
                    if email.hasAttachments {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Attachments")
                                .font(.headline)

                            ForEach(email.attachments, id: \.attachmentId) { attachment in
                                HStack {
                                    Image(systemName: iconForMimeType(attachment.mimeType))
                                        .foregroundColor(.blue)

                                    VStack(alignment: .leading) {
                                        Text(attachment.filename)
                                            .font(.subheadline)

                                        Text(formatFileSize(attachment.size))
                                            .font(.caption)
                                            .foregroundColor(.secondary)
                                    }

                                    Spacer()

                                    Image(systemName: "arrow.down.circle")
                                        .foregroundColor(.blue)
                                }
                                .padding()
                                .background(Color(.systemGray6))
                                .cornerRadius(8)
                            }
                        }
                    }

                    // Body
                    Divider()

                    if let bodyText = email.bodyText {
                        Text(bodyText)
                            .font(.body)
                    } else {
                        Text("(No content)")
                            .foregroundColor(.secondary)
                            .italic()
                    }
                }
                .padding()
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Done") {
                        dismiss()
                    }
                }

                ToolbarItem(placement: .navigationBarTrailing) {
                    HStack(spacing: 16) {
                        Button(action: {}) {
                            Image(systemName: email.isStarred ? "star.fill" : "star")
                                .foregroundColor(email.isStarred ? .yellow : .primary)
                        }

                        Button(action: {}) {
                            Image(systemName: "arrowshape.turn.up.left")
                        }
                    }
                }
            }
        }
    }

    private func iconForMimeType(_ mimeType: String) -> String {
        switch mimeType {
        case let type where type.hasPrefix("image"):
            return "photo"
        case let type where type.hasPrefix("video"):
            return "video"
        case let type where type.contains("pdf"):
            return "doc.text"
        case let type where type.contains("zip"):
            return "doc.zipper"
        default:
            return "doc"
        }
    }

    private func formatFileSize(_ bytes: Int) -> String {
        let formatter = ByteCountFormatter()
        formatter.countStyle = .file
        return formatter.string(fromByteCount: Int64(bytes))
    }
}
