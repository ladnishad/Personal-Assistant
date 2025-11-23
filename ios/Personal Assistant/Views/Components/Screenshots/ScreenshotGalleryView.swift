//
//  ScreenshotGalleryView.swift
//  Personal Assistant
//
//  Created by LifeOS
//

import SwiftUI

struct ScreenshotGalleryView: View {
    let screenshots: [ScreenshotCapture]
    @State private var selectedScreenshot: ScreenshotCapture?

    var body: some View {
        if screenshots.isEmpty {
            EmptyView()
        } else {
            VStack(alignment: .leading, spacing: 8) {
                Text("Agent Activity")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 4)

                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 12) {
                        ForEach(Array(screenshots.enumerated()), id: \.offset) { index, screenshot in
                            ScreenshotThumbnailView(
                                screenshot: screenshot,
                                index: index + 1
                            )
                            .onTapGesture {
                                selectedScreenshot = screenshot
                            }
                        }
                    }
                    .padding(.horizontal, 4)
                }
            }
            .sheet(item: $selectedScreenshot) { screenshot in
                ScreenshotDetailView(screenshot: screenshot)
            }
        }
    }
}

struct ScreenshotThumbnailView: View {
    let screenshot: ScreenshotCapture
    let index: Int

    private var image: UIImage? {
        if let imageData = Data(base64Encoded: screenshot.screenshot) {
            return UIImage(data: imageData)
        }
        return nil
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            ZStack(alignment: .topLeading) {
                if let uiImage = image {
                    Image(uiImage: uiImage)
                        .resizable()
                        .aspectRatio(contentMode: .fill)
                        .frame(width: 160, height: 120)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                } else {
                    RoundedRectangle(cornerRadius: 12)
                        .fill(Color.gray.opacity(0.2))
                        .frame(width: 160, height: 120)
                        .overlay(
                            Image(systemName: "photo")
                                .foregroundColor(.gray)
                                .font(.title)
                        )
                }

                // Step number badge
                Text("\(index)")
                    .font(.caption2.bold())
                    .foregroundColor(.white)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(
                        Capsule()
                            .fill(Color.blue)
                    )
                    .padding(8)
            }

            if let context = screenshot.actionContext {
                Text(context)
                    .font(.caption2)
                    .foregroundColor(.secondary)
                    .lineLimit(2)
                    .frame(width: 160, alignment: .leading)
            }
        }
    }
}

#Preview {
    ScreenshotGalleryView(screenshots: [
        ScreenshotCapture(
            timestamp: "2025-01-01T00:00:00Z",
            screenshot: "",
            width: 1920,
            height: 1080,
            actionContext: "Navigated to Amazon.com"
        ),
        ScreenshotCapture(
            timestamp: "2025-01-01T00:00:01Z",
            screenshot: "",
            width: 1920,
            height: 1080,
            actionContext: "Searched for 'Sony headphones'"
        )
    ])
}
