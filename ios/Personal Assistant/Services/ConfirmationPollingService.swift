//
//  ConfirmationPollingService.swift
//  Personal Assistant
//
//  Background service to poll for pending confirmations
//

import Foundation
import Combine

@MainActor
class ConfirmationPollingService: ObservableObject {
    static let shared = ConfirmationPollingService()

    @Published var pendingConfirmations: [PendingConfirmation] = []
    @Published var isPolling = false

    private let apiService = APIService.shared
    private var pollingTask: Task<Void, Never>?
    private let pollingInterval: TimeInterval = 2.5 // 2.5 seconds

    private init() {}

    // Start polling for confirmations
    func startPolling() {
        guard !isPolling else { return }

        isPolling = true
        pollingTask = Task {
            while !Task.isCancelled {
                await fetchPendingConfirmations()

                // Wait for interval before next poll
                try? await Task.sleep(nanoseconds: UInt64(pollingInterval * 1_000_000_000))
            }
        }

        print("✅ Confirmation polling started")
    }

    // Stop polling
    func stopPolling() {
        pollingTask?.cancel()
        pollingTask = nil
        isPolling = false
        print("⏸️ Confirmation polling stopped")
    }

    // Fetch pending confirmations
    private func fetchPendingConfirmations() async {
        do {
            let confirmations = try await apiService.getPendingConfirmations()

            // Filter out expired confirmations
            let activeConfirmations = confirmations.filter { !$0.isExpired }

            // Only update if changed to avoid unnecessary UI updates
            if activeConfirmations.map(\.id) != pendingConfirmations.map(\.id) {
                pendingConfirmations = activeConfirmations
                if !activeConfirmations.isEmpty {
                    print("📬 Fetched \(activeConfirmations.count) pending confirmations")
                }
            }
        } catch {
            // Silent fail - don't interrupt user experience
            // Only log errors that aren't auth-related (user might be logged out)
            if let apiError = error as? APIError, case .unauthorized = apiError {
                stopPolling() // Stop polling if unauthorized
            }
        }
    }

    // Respond to a confirmation
    func respondToConfirmation(
        _ confirmation: PendingConfirmation,
        approved: Bool,
        note: String?
    ) async throws -> ConfirmationResponse {
        let decision = UserConfirmationDecision(approved: approved, note: note)
        let response = try await apiService.respondToConfirmation(
            confirmationId: confirmation.id,
            decision: decision
        )

        // Remove from pending list
        pendingConfirmations.removeAll { $0.id == confirmation.id }

        return response
    }

    // Cancel a confirmation
    func cancelConfirmation(_ confirmation: PendingConfirmation) async throws {
        try await apiService.cancelConfirmation(confirmationId: confirmation.id)

        // Remove from pending list
        pendingConfirmations.removeAll { $0.id == confirmation.id }
    }
}