//
//  ConfirmationSheet.swift
//  Personal Assistant
//
//  Main confirmation sheet that combines all confirmation components
//

import SwiftUI

struct ConfirmationSheet: View {
    let confirmation: PendingConfirmation
    @Binding var isPresented: Bool
    let onDismiss: () -> Void

    @StateObject private var viewModel: ConfirmationViewModel
    @State private var showingCancelAlert = false

    init(confirmation: PendingConfirmation, isPresented: Binding<Bool>, onDismiss: @escaping () -> Void) {
        self.confirmation = confirmation
        self._isPresented = isPresented
        self.onDismiss = onDismiss
        self._viewModel = StateObject(wrappedValue: ConfirmationViewModel(confirmation: confirmation))
    }

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 24) {
                    // Risk level badge
                    RiskLevelBadge(riskLevel: viewModel.riskLevel)
                        .padding(.top, 8)

                    // Action description
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Action Requested")
                            .font(.caption)
                            .foregroundColor(.secondary)
                            .textCase(.uppercase)

                        Text(viewModel.actionDescription)
                            .font(.body)
                            .foregroundColor(.primary)
                            .multilineTextAlignment(.leading)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(16)
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .fill(Color.secondary.opacity(0.1))
                    )

                    // Countdown timer
                    CountdownTimer(
                        timeRemaining: viewModel.timeRemaining,
                        totalTime: confirmation.expiresAt.timeIntervalSince(confirmation.createdAt),
                        onExpire: {
                            handleExpiration()
                        }
                    )

                    // Note input (if visible)
                    if viewModel.showNoteInput {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Add Note (Optional)")
                                .font(.caption)
                                .foregroundColor(.secondary)

                            TextEditor(text: $viewModel.userNote)
                                .frame(minHeight: 80, maxHeight: 120)
                                .padding(8)
                                .background(
                                    RoundedRectangle(cornerRadius: 8)
                                        .stroke(Color.secondary.opacity(0.3), lineWidth: 1)
                                )
                                .overlay(alignment: .topLeading) {
                                    if viewModel.userNote.isEmpty {
                                        Text("Provide additional context or reasoning...")
                                            .foregroundColor(.secondary.opacity(0.5))
                                            .padding(.horizontal, 12)
                                            .padding(.vertical, 16)
                                            .allowsHitTesting(false)
                                    }
                                }
                        }
                        .transition(.asymmetric(
                            insertion: .scale.combined(with: .opacity),
                            removal: .scale.combined(with: .opacity)
                        ))
                    }

                    // Metadata view
                    MetadataView(metadata: viewModel.metadata)

                    // Error message (if any)
                    if let errorMessage = viewModel.errorMessage {
                        HStack {
                            Image(systemName: "exclamationmark.circle.fill")
                                .foregroundColor(.red)
                            Text(errorMessage)
                                .font(.caption)
                                .foregroundColor(.red)
                        }
                        .padding(12)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(Color.red.opacity(0.1))
                        )
                    }

                    // Approval buttons
                    ApprovalButtons(
                        riskLevel: viewModel.riskLevel,
                        isSubmitting: viewModel.isSubmitting,
                        onApprove: {
                            await viewModel.approve {
                                dismissSheet()
                            }
                        },
                        onDeny: {
                            await viewModel.deny {
                                dismissSheet()
                            }
                        },
                        onAddNote: {
                            viewModel.toggleNoteInput()
                        },
                        hasNote: viewModel.showNoteInput && !viewModel.userNote.isEmpty
                    )
                }
                .padding()
            }
            .navigationTitle("Action Confirmation")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Cancel") {
                        showingCancelAlert = true
                    }
                    .disabled(viewModel.isSubmitting)
                }
            }
        }
        .alert("Cancel Confirmation?", isPresented: $showingCancelAlert) {
            Button("Keep Waiting", role: .cancel) {}
            Button("Cancel", role: .destructive) {
                Task {
                    await viewModel.cancel {
                        dismissSheet()
                    }
                }
            }
        } message: {
            Text("This will cancel the pending confirmation request. The action will not be executed.")
        }
        .interactiveDismissDisabled(viewModel.isSubmitting)
    }

    private func dismissSheet() {
        isPresented = false
        onDismiss()
    }

    private func handleExpiration() {
        // Auto-dismiss when expired
        dismissSheet()
    }
}

#Preview {
    @State var isPresented = true

    return ConfirmationSheet(
        confirmation: PendingConfirmation(
            confirmationId: "test-123",
            actionDescription: "Navigate to https://example.com/checkout and submit payment form with credit card ending in 4242",
            riskLevel: .high,
            createdAt: Date(),
            expiresAt: Date().addingTimeInterval(300),
            metadata: [
                "url": AnyCodable("https://example.com/checkout"),
                "form_fields": AnyCodable(["card_number", "cvv", "expiry"]),
                "total_amount": AnyCodable(149.99)
            ]
        ),
        isPresented: $isPresented,
        onDismiss: {}
    )
}