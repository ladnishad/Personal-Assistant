//
//  CountdownTimer.swift
//  Personal Assistant
//
//  Visual countdown timer with circular progress indicator
//

import SwiftUI

struct CountdownTimer: View {
    let timeRemaining: TimeInterval
    let totalTime: TimeInterval
    let onExpire: () -> Void

    @State private var animateProgress = false

    private var progress: Double {
        guard totalTime > 0 else { return 0 }
        return max(0, min(1, timeRemaining / totalTime))
    }

    private var formattedTime: String {
        let minutes = Int(timeRemaining) / 60
        let seconds = Int(timeRemaining) % 60
        return String(format: "%d:%02d", minutes, seconds)
    }

    private var urgencyColor: Color {
        switch progress {
        case 0.5...1.0:
            return .green
        case 0.25..<0.5:
            return .orange
        default:
            return .red
        }
    }

    var body: some View {
        ZStack {
            // Background circle
            Circle()
                .stroke(
                    urgencyColor.opacity(0.3),
                    lineWidth: 12
                )

            // Progress circle
            Circle()
                .trim(from: 0, to: progress)
                .stroke(
                    urgencyColor,
                    style: StrokeStyle(
                        lineWidth: 12,
                        lineCap: .round
                    )
                )
                .rotationEffect(.degrees(-90))
                .animation(.easeInOut(duration: 0.2), value: progress)

            // Time display
            VStack(spacing: 4) {
                Text(formattedTime)
                    .font(.system(size: 36, weight: .bold, design: .monospaced))
                    .foregroundColor(.primary)

                Text(progress < 0.25 ? "Expiring Soon" : "Remaining")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .frame(width: 140, height: 140)
        .onAppear {
            animateProgress = true

            // Check for expiration
            if timeRemaining <= 0 {
                onExpire()
            }
        }
        .onChange(of: timeRemaining) { newValue in
            if newValue <= 0 {
                onExpire()
            }
        }
    }
}

#Preview {
    VStack(spacing: 40) {
        // Full time
        CountdownTimer(
            timeRemaining: 300,
            totalTime: 300,
            onExpire: {}
        )

        // Half time
        CountdownTimer(
            timeRemaining: 150,
            totalTime: 300,
            onExpire: {}
        )

        // Low time
        CountdownTimer(
            timeRemaining: 30,
            totalTime: 300,
            onExpire: {}
        )
    }
    .padding()
}