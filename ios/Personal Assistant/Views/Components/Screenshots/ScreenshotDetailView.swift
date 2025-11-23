//
//  ScreenshotDetailView.swift
//  Personal Assistant
//
//  Created by LifeOS
//

import SwiftUI

struct ScreenshotDetailView: View {
    let screenshot: ScreenshotCapture
    @Environment(\.dismiss) private var dismiss
    @State private var scale: CGFloat = 1.0
    @State private var lastScale: CGFloat = 1.0

    private var image: UIImage? {
        if let imageData = Data(base64Encoded: screenshot.screenshot) {
            return UIImage(data: imageData)
        }
        return nil
    }

    var body: some View {
        NavigationView {
            ZStack {
                Color.black
                    .ignoresSafeArea()

                if let uiImage = image {
                    Image(uiImage: uiImage)
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .scaleEffect(scale)
                        .gesture(
                            MagnificationGesture()
                                .onChanged { value in
                                    let delta = value / lastScale
                                    lastScale = value
                                    scale *= delta
                                }
                                .onEnded { _ in
                                    lastScale = 1.0
                                    // Reset to reasonable bounds
                                    if scale < 0.5 {
                                        withAnimation(.spring()) {
                                            scale = 0.5
                                        }
                                    } else if scale > 3.0 {
                                        withAnimation(.spring()) {
                                            scale = 3.0
                                        }
                                    }
                                }
                        )
                        .onTapGesture(count: 2) {
                            // Double tap to reset zoom
                            withAnimation(.spring()) {
                                scale = 1.0
                            }
                        }
                } else {
                    VStack(spacing: 16) {
                        Image(systemName: "exclamationmark.triangle")
                            .font(.system(size: 50))
                            .foregroundColor(.gray)
                        Text("Failed to load screenshot")
                            .foregroundColor(.gray)
                    }
                }
            }
            .navigationTitle("Screenshot")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Done") {
                        dismiss()
                    }
                    .foregroundColor(.white)
                }

                if screenshot.actionContext != nil || scale != 1.0 {
                    ToolbarItem(placement: .principal) {
                        VStack(spacing: 2) {
                            if let context = screenshot.actionContext {
                                Text(context)
                                    .font(.caption.bold())
                                    .foregroundColor(.white)
                            }
                            if scale != 1.0 {
                                Text("\(Int(scale * 100))%")
                                    .font(.caption2)
                                    .foregroundColor(.white.opacity(0.7))
                            }
                        }
                    }
                }
            }
            .toolbarBackground(.visible, for: .navigationBar)
            .toolbarBackground(Color.black.opacity(0.8), for: .navigationBar)
        }
    }
}

#Preview {
    ScreenshotDetailView(
        screenshot: ScreenshotCapture(
            timestamp: "2025-01-01T00:00:00Z",
            screenshot: "",
            width: 1920,
            height: 1080,
            actionContext: "Navigated to Amazon.com"
        )
    )
}
