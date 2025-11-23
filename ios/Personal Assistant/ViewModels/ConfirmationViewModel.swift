//
//  ConfirmationViewModel.swift
//  Personal Assistant
//
//  Manages state for a single confirmation interaction
//

import Foundation
import Combine

@MainActor
class ConfirmationViewModel: ObservableObject {
    @Published var isSubmitting = false
    @Published var errorMessage: String?
    @Published var userNote = ""
    @Published var showNoteInput = false
    @Published var timeRemaining: TimeInterval = 0

    private let confirmation: PendingConfirmation
    private let pollingService = ConfirmationPollingService.shared
    private var timerTask: Task<Void, Never>?

    var riskLevel: RiskLevel {
        confirmation.riskLevel
    }

    var actionDescription: String {
        confirmation.actionDescription
    }

    var metadata: [String: AnyCodable]? {
        confirmation.metadata
    }

    init(confirmation: PendingConfirmation) {
        self.confirmation = confirmation
        self.timeRemaining = confirmation.timeRemaining
        startCountdown()
    }

    deinit {
        timerTask?.cancel()
    }

    // Start countdown timer
    private func startCountdown() {
        timerTask = Task {
            while !Task.isCancelled {
                timeRemaining = confirmation.timeRemaining

                if timeRemaining <= 0 {
                    break
                }

                try? await Task.sleep(nanoseconds: 100_000_000) // Update every 0.1s
            }
        }
    }

    // Approve the action
    func approve(onSuccess: @escaping () -> Void) async {
        await submitDecision(approved: true, onSuccess: onSuccess)
    }

    // Deny the action
    func deny(onSuccess: @escaping () -> Void) async {
        await submitDecision(approved: false, onSuccess: onSuccess)
    }

    // Submit decision to backend
    private func submitDecision(approved: Bool, onSuccess: @escaping () -> Void) async {
        isSubmitting = true
        errorMessage = nil

        do {
            let note = showNoteInput && !userNote.isEmpty ? userNote : nil
            _ = try await pollingService.respondToConfirmation(
                confirmation,
                approved: approved,
                note: note
            )

            // Cancel timer before calling onSuccess
            timerTask?.cancel()
            timerTask = nil

            onSuccess()
        } catch let error as APIError {
            errorMessage = error.errorDescription
        } catch {
            errorMessage = "Failed to submit response"
        }

        isSubmitting = false
    }

    // Cancel the confirmation
    func cancel(onSuccess: @escaping () -> Void) async {
        isSubmitting = true
        errorMessage = nil

        do {
            try await pollingService.cancelConfirmation(confirmation)

            // Cancel timer before calling onSuccess
            timerTask?.cancel()
            timerTask = nil

            onSuccess()
        } catch let error as APIError {
            errorMessage = error.errorDescription
        } catch {
            errorMessage = "Failed to cancel confirmation"
        }

        isSubmitting = false
    }

    // Toggle note input
    func toggleNoteInput() {
        showNoteInput.toggle()
        if !showNoteInput {
            userNote = ""
        }
    }
}