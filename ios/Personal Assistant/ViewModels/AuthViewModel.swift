//
//  AuthViewModel.swift
//  Personal Assistant
//
//  Created by LifeOS on 11/15/25.
//

import Foundation
import Combine
import SwiftUI

@MainActor
class AuthViewModel: ObservableObject {
    @Published var isAuthenticated = false
    @Published var currentUser: UserResponse?
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let apiService = APIService.shared

    init() {
        // Don't run async tasks in init - let the view trigger it
    }

    func checkAuthStatus() {
        // Check if we have a valid token
        guard UserDefaults.standard.string(forKey: "accessToken") != nil else {
            isAuthenticated = false
            return
        }

        Task {
            do {
                let user = try await apiService.getCurrentUser()
                withAnimation {
                    currentUser = user
                    isAuthenticated = true
                }
            } catch {
                // Token might be expired
                withAnimation {
                    isAuthenticated = false
                }
            }
        }
    }

    func login(email: String, password: String) async {
        isLoading = true
        errorMessage = nil

        do {
            print("🔐 Attempting login...")
            let tokenResponse = try await apiService.login(email: email, password: password)
            print("✅ Login successful, got tokens")
            print("🔍 Fetching current user...")
            let user = try await apiService.getCurrentUser()
            print("✅ Got current user: \(user.email)")

            // Update state with animation to ensure SwiftUI picks up the change
            withAnimation {
                currentUser = user
                isAuthenticated = true
            }
            print("✅ Authentication state updated to: \(isAuthenticated)")
        } catch let error as APIError {
            print("❌ API Error during login: \(error.errorDescription ?? "unknown")")
            errorMessage = error.errorDescription
            withAnimation {
                isAuthenticated = false
            }
        } catch {
            print("❌ Unexpected error during login: \(error)")
            errorMessage = "An unexpected error occurred: \(error.localizedDescription)"
            withAnimation {
                isAuthenticated = false
            }
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
        withAnimation {
            isAuthenticated = false
            currentUser = nil
        }
        print("✅ Logged out, authentication state: \(isAuthenticated)")
    }
}
