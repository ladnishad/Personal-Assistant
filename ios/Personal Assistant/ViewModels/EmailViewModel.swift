//
//  EmailViewModel.swift
//  Personal Assistant
//
//  Created by LifeOS on 11/15/25.
//

import Foundation
import Combine

@MainActor
class EmailViewModel: ObservableObject {
    @Published var emails: [Email] = []
    @Published var isLoading = false
    @Published var isSyncing = false
    @Published var isClassifying = false
    @Published var classificationResult: EmailClassifyAllResponse?
    @Published var errorMessage: String?
    @Published var searchText = ""
    @Published var showUnreadOnly = false

    private let apiService = APIService.shared
    private var currentPage = 1
    private var hasMorePages = true

    func loadEmails() async {
        guard !isLoading else { return }

        isLoading = true
        errorMessage = nil

        do {
            let response = try await apiService.getEmails(
                page: currentPage,
                isRead: showUnreadOnly ? false : nil,
                search: searchText.isEmpty ? nil : searchText
            )
            emails = response.emails
            hasMorePages = response.emails.count == response.pageSize
        } catch let error as APIError {
            errorMessage = error.errorDescription
        } catch {
            errorMessage = "Failed to load emails"
        }

        isLoading = false
    }

    func syncEmails() async {
        isSyncing = true

        do {
            _ = try await apiService.syncEmails()
            await loadEmails()
        } catch let error as APIError {
            errorMessage = error.errorDescription
        } catch {
            errorMessage = "Failed to sync emails"
        }

        isSyncing = false
    }

    func markAsRead(_ email: Email) async {
        do {
            try await apiService.markEmailRead(id: email.id, isRead: true)
            if let index = emails.firstIndex(where: { $0.id == email.id }) {
                var updatedEmail = email
                emails[index] = updatedEmail
            }
        } catch {
            errorMessage = "Failed to mark email as read"
        }
    }

    func toggleUnreadFilter() {
        showUnreadOnly.toggle()
        Task {
            await loadEmails()
        }
    }

    func classifyAllEmails(forceReclassify: Bool = false) async {
        isClassifying = true
        classificationResult = nil
        errorMessage = nil

        do {
            let result = try await apiService.classifyAllEmails(forceReclassify: forceReclassify)
            classificationResult = result

            // Reload emails to show updated classifications
            await loadEmails()
        } catch let error as APIError {
            errorMessage = error.errorDescription
        } catch {
            errorMessage = "Failed to classify emails"
        }

        isClassifying = false
    }

    func classifySingleEmail(_ email: Email, forceReclassify: Bool = false) async -> EmailClassifyResponse? {
        do {
            let result = try await apiService.classifySingleEmail(id: email.id, forceReclassify: forceReclassify)

            // Reload emails to show updated classification
            await loadEmails()

            return result
        } catch let error as APIError {
            errorMessage = error.errorDescription
        } catch {
            errorMessage = "Failed to classify email"
        }

        return nil
    }
}
