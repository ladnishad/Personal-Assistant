//
//  ScreenshotStreamView.swift
//  Personal Assistant
//
//  Created by LifeOS on 11/22/25.
//

import SwiftUI

/// View component for displaying agent screenshot stream
/// Shows a collapsible preview of what the computer control agent is doing
struct ScreenshotStreamView: View {
    let screenshots: [ScreenshotCapture]
    @State private var isExpanded: Bool = false
    @State private var selectedScreenshotIndex: Int = 0

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Header with toggle
            Button(action: {
                withAnimation {
                    isExpanded.toggle()
                }
            }) {
                HStack {
                    Image(systemName: isExpanded ? "chevron.down" : "chevron.right")
                        .font(.caption)
                    Text("Agent Screen Preview")
                        .font(.subheadline)
                        .fontWeight(.medium)
                    Spacer()
                    Text("\(screenshots.count) screenshot\(screenshots.count == 1 ? "" : "s")")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(Color.secondary.opacity(0.1))
                .cornerRadius(8)
            }
            .buttonStyle(PlainButtonStyle())

            // Screenshot display (when expanded)
            if isExpanded && !screenshots.isEmpty {
                VStack(spacing: 12) {
                    // Current screenshot display
                    if let currentScreenshot = screenshots[safe: selectedScreenshotIndex] {
                        VStack(alignment: .leading, spacing: 8) {
                            // Screenshot image
                            if let imageData = Data(base64Encoded: currentScreenshot.screenshot),
                               let uiImage = UIImage(data: imageData) {
                                Image(uiImage: uiImage)
                                    .resizable()
                                    .aspectRatio(contentMode: .fit)
                                    .frame(maxHeight: 300)
                                    .cornerRadius(8)
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 8)
                                            .stroke(Color.secondary.opacity(0.3), lineWidth: 1)
                                    )
                            } else {
                                Rectangle()
                                    .fill(Color.secondary.opacity(0.2))
                                    .frame(height: 200)
                                    .cornerRadius(8)
                                    .overlay(
                                        Text("Failed to load screenshot")
                                            .foregroundColor(.secondary)
                                    )
                            }

                            // Screenshot metadata
                            VStack(alignment: .leading, spacing: 4) {
                                if let actionContext = currentScreenshot.actionContext {
                                    Text(actionContext)
                                        .font(.caption)
                                        .foregroundColor(.primary)
                                }

                                HStack {
                                    Text(formatTimestamp(currentScreenshot.timestamp))
                                        .font(.caption2)
                                        .foregroundColor(.secondary)
                                    Spacer()
                                    Text("\(currentScreenshot.width)×\(currentScreenshot.height)")
                                        .font(.caption2)
                                        .foregroundColor(.secondary)
                                }
                            }
                            .padding(.horizontal, 4)
                        }
                    }

                    // Screenshot navigation (if multiple)
                    if screenshots.count > 1 {
                        HStack {
                            Button(action: {
                                if selectedScreenshotIndex > 0 {
                                    selectedScreenshotIndex -= 1
                                }
                            }) {
                                Image(systemName: "chevron.left")
                                    .font(.caption)
                            }
                            .disabled(selectedScreenshotIndex == 0)

                            Spacer()

                            Text("\(selectedScreenshotIndex + 1) / \(screenshots.count)")
                                .font(.caption)
                                .foregroundColor(.secondary)

                            Spacer()

                            Button(action: {
                                if selectedScreenshotIndex < screenshots.count - 1 {
                                    selectedScreenshotIndex += 1
                                }
                            }) {
                                Image(systemName: "chevron.right")
                                    .font(.caption)
                            }
                            .disabled(selectedScreenshotIndex >= screenshots.count - 1)
                        }
                        .padding(.horizontal, 8)
                    }
                }
                .padding(12)
                .background(Color.secondary.opacity(0.05))
                .cornerRadius(8)
            }
        }
        .onChange(of: screenshots.count) { newCount in
            // Auto-select latest screenshot when new ones arrive
            if newCount > 0 {
                selectedScreenshotIndex = newCount - 1
            }
        }
    }

    private func formatTimestamp(_ timestamp: String) -> String {
        let formatter = ISO8601DateFormatter()
        if let date = formatter.date(from: timestamp) {
            let displayFormatter = DateFormatter()
            displayFormatter.dateStyle = .none
            displayFormatter.timeStyle = .medium
            return displayFormatter.string(from: date)
        }
        return timestamp
    }
}

// Safe array subscript extension
extension Array {
    subscript(safe index: Int) -> Element? {
        return indices.contains(index) ? self[index] : nil
    }
}

// MARK: - Preview

struct ScreenshotStreamView_Previews: PreviewProvider {
    static var previews: some View {
        ScreenshotStreamView(screenshots: [
            ScreenshotCapture(
                timestamp: ISO8601DateFormatter().string(from: Date()),
                screenshot: "", // Empty for preview
                width: 1024,
                height: 768,
                actionContext: "Clicking search button"
            )
        ])
        .padding()
    }
}
