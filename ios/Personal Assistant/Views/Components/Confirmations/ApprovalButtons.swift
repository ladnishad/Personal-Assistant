//
//  ApprovalButtons.swift
//  Personal Assistant
//
//  Action buttons for approving or denying confirmations
//

import SwiftUI

struct ApprovalButtons: View {
    let riskLevel: RiskLevel
    let isSubmitting: Bool
    let onApprove: () async -> Void
    let onDeny: () async -> Void
    let onAddNote: () -> Void
    let hasNote: Bool

    @State private var showingConfirmation = false
    @State private var actionToConfirm: ConfirmAction?

    private enum ConfirmAction {
        case approve
        case deny
    }

    var body: some View {
        VStack(spacing: 16) {
            // Add Note button
            Button(action: onAddNote) {
                HStack {
                    Image(systemName: hasNote ? "note.text.badge.plus" : "note.text")
                        .font(.system(size: 18))
                    Text(hasNote ? "Edit Note" : "Add Note")
                        .font(.callout)
                }
                .foregroundColor(.primary)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 10)
                .background(
                    RoundedRectangle(cornerRadius: 10)
                        .stroke(Color.secondary.opacity(0.3), lineWidth: 1)
                )
            }

            // Main action buttons
            HStack(spacing: 16) {
                // Deny button
                Button {
                    if riskLevel == .critical {
                        actionToConfirm = .deny
                        showingConfirmation = true
                    } else {
                        Task {
                            await onDeny()
                        }
                    }
                } label: {
                    HStack {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 20))
                        Text("Deny")
                            .fontWeight(.semibold)
                    }
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 16)
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .fill(Color.red)
                    )
                }
                .disabled(isSubmitting)

                // Approve button
                Button {
                    if riskLevel == .high || riskLevel == .critical {
                        actionToConfirm = .approve
                        showingConfirmation = true
                    } else {
                        Task {
                            await onApprove()
                        }
                    }
                } label: {
                    HStack {
                        Image(systemName: "checkmark.circle.fill")
                            .font(.system(size: 20))
                        Text("Approve")
                            .fontWeight(.semibold)
                    }
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 16)
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .fill(Color.green)
                    )
                }
                .disabled(isSubmitting)
            }

            // Risk warning for high/critical actions
            if riskLevel == .high || riskLevel == .critical {
                HStack {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundColor(riskLevel == .critical ? .red : .orange)
                    Text("This is a \(riskLevel.displayName.lowercased()) risk action")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
        }
        .alert(
            "Confirm \(actionToConfirm == .approve ? "Approval" : "Denial")",
            isPresented: $showingConfirmation
        ) {
            Button("Cancel", role: .cancel) {}
            Button(
                actionToConfirm == .approve ? "Approve" : "Deny",
                role: actionToConfirm == .approve ? .none : .destructive
            ) {
                Task {
                    switch actionToConfirm {
                    case .approve:
                        await onApprove()
                    case .deny:
                        await onDeny()
                    case .none:
                        break
                    }
                }
            }
        } message: {
            Text(confirmationMessage)
        }
        .disabled(isSubmitting)
        .overlay {
            if isSubmitting {
                ProgressView()
                    .progressViewStyle(CircularProgressViewStyle())
                    .scaleEffect(1.5)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Color.black.opacity(0.3))
                    .cornerRadius(12)
            }
        }
    }

    private var confirmationMessage: String {
        switch (actionToConfirm, riskLevel) {
        case (.approve, .critical):
            return "This is a CRITICAL risk action. Are you absolutely sure you want to approve it?"
        case (.approve, .high):
            return "This is a high risk action. Are you sure you want to approve it?"
        case (.deny, .critical):
            return "Are you sure you want to deny this critical action?"
        default:
            return "Are you sure you want to \(actionToConfirm == .approve ? "approve" : "deny") this action?"
        }
    }
}

#Preview {
    VStack(spacing: 40) {
        ApprovalButtons(
            riskLevel: .low,
            isSubmitting: false,
            onApprove: {},
            onDeny: {},
            onAddNote: {},
            hasNote: false
        )

        ApprovalButtons(
            riskLevel: .critical,
            isSubmitting: false,
            onApprove: {},
            onDeny: {},
            onAddNote: {},
            hasNote: true
        )

        ApprovalButtons(
            riskLevel: .medium,
            isSubmitting: true,
            onApprove: {},
            onDeny: {},
            onAddNote: {},
            hasNote: false
        )
    }
    .padding()
}