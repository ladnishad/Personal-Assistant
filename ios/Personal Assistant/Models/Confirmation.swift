//
//  Confirmation.swift
//  Personal Assistant
//
//  Models for user confirmation system
//

import Foundation

// MARK: - Enums

enum RiskLevel: String, Codable, CaseIterable {
    case low = "low"
    case medium = "medium"
    case high = "high"
    case critical = "critical"

    var color: String {
        switch self {
        case .low: return "green"
        case .medium: return "blue"
        case .high: return "orange"
        case .critical: return "red"
        }
    }

    var displayName: String {
        rawValue.capitalized
    }

    var icon: String {
        switch self {
        case .low: return "info.circle.fill"
        case .medium: return "exclamationmark.circle.fill"
        case .high: return "exclamationmark.triangle.fill"
        case .critical: return "exclamationmark.octagon.fill"
        }
    }
}

enum ConfirmationStatus: String, Codable {
    case pending = "pending"
    case approved = "approved"
    case denied = "denied"
    case expired = "expired"
    case cancelled = "cancelled"
}

// MARK: - API Models

struct PendingConfirmation: Codable, Identifiable {
    let confirmationId: String
    let actionDescription: String
    let riskLevel: RiskLevel
    let createdAt: Date
    let expiresAt: Date
    let metadata: [String: AnyCodable]?

    var id: String { confirmationId }

    enum CodingKeys: String, CodingKey {
        case confirmationId = "confirmation_id"
        case actionDescription = "action_description"
        case riskLevel = "risk_level"
        case createdAt = "created_at"
        case expiresAt = "expires_at"
        case metadata
    }

    // Computed properties
    var timeRemaining: TimeInterval {
        expiresAt.timeIntervalSince(Date())
    }

    var isExpired: Bool {
        Date() >= expiresAt
    }

    var percentTimeRemaining: Double {
        let total = expiresAt.timeIntervalSince(createdAt)
        let remaining = timeRemaining
        return max(0, min(1, remaining / total))
    }
}

struct UserConfirmationDecision: Codable {
    let approved: Bool
    let note: String?
}

struct ConfirmationResponse: Codable {
    let confirmationId: String
    let status: ConfirmationStatus
    let approved: Bool
    let userNote: String?
    let createdAt: Date
    let resolvedAt: Date?

    enum CodingKeys: String, CodingKey {
        case confirmationId = "confirmation_id"
        case status, approved
        case userNote = "user_note"
        case createdAt = "created_at"
        case resolvedAt = "resolved_at"
    }
}

// MARK: - Equatable Conformance for Performance

extension PendingConfirmation: Equatable {
    static func == (lhs: PendingConfirmation, rhs: PendingConfirmation) -> Bool {
        lhs.id == rhs.id
    }
}