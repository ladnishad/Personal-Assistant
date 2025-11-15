//
//  AuthViewModel.swift
//  Personal Assistant
//
//  Created by LifeOS on 11/15/25.
//

import Foundation
import Combine

@MainActor
class AuthViewModel: ObservableObject {
    @Published var isAuthenticated = false
    @Published var currentUser: UserResponse?
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let apiService = APIService.shared

    init() {
        checkAuthStatus()
    }

    func checkAuthStatus() {
        // Check if we have a valid token
        if UserDefaults.standard.string(forKey: "accessToken") != nil {
            Task {
                do {
                    currentUser = try await apiService.getCurrentUser()
                    isAuthenticated = true
                } catch {
                    // Token might be expired
                    isAuthenticated = false
                }
            }
        }
    }

    func login(email: String, password: String) async {
        isLoading = true
        errorMessage = nil

        do {
            _ = try await apiService.login(email: email, password: password)
            currentUser = try await apiService.getCurrentUser()
            isAuthenticated = true
        } catch let error as APIError {
            errorMessage = error.errorDescription
        } catch {
            errorMessage = "An unexpected error occurred"
        }

        isLoading = false
    }

    func register(email: String, password: String, fullName: String?) async {
        isLoading = true
        errorMessage = nil

        do {
            _ = try await apiService.register(email: email, password: password, fullName: fullName)
            // Auto-login after registration
            await login(email: email, password: password)
        } catch let error as APIError {
            errorMessage = error.errorDescription
        } catch {
            errorMessage = "An unexpected error occurred"
        }

        isLoading = false
    }

    func logout() {
        apiService.logout()
        isAuthenticated = false
        currentUser = nil
    }
}
