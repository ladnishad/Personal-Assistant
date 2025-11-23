//
//  RiskLevelBadge.swift
//  Personal Assistant
//
//  Color-coded risk level indicator
//

import SwiftUI

struct RiskLevelBadge: View {
    let riskLevel: RiskLevel

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: riskLevel.icon)
                .font(.system(size: 20, weight: .semibold))

            Text("\(riskLevel.displayName) Risk")
                .font(.headline)
                .fontWeight(.semibold)
        }
        .foregroundColor(.white)
        .padding(.horizontal, 20)
        .padding(.vertical, 12)
        .background(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(colorForRiskLevel)
        )
        .shadow(color: colorForRiskLevel.opacity(0.3), radius: 8, x: 0, y: 4)
    }

    private var colorForRiskLevel: Color {
        switch riskLevel {
        case .low: return .green
        case .medium: return .blue
        case .high: return .orange
        case .critical: return .red
        }
    }
}

#Preview {
    VStack(spacing: 20) {
        RiskLevelBadge(riskLevel: .low)
        RiskLevelBadge(riskLevel: .medium)
        RiskLevelBadge(riskLevel: .high)
        RiskLevelBadge(riskLevel: .critical)
    }
    .padding()
}