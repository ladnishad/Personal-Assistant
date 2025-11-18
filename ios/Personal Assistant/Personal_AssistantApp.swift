//
//  Personal_AssistantApp.swift
//  Personal Assistant
//
//  Created by Nishad Lad on 11/15/25.
//

import SwiftUI

@main
struct Personal_AssistantApp: App {
    @StateObject private var authViewModel = AuthViewModel()

    var body: some Scene {
        WindowGroup {
            ContentViewContainer(authViewModel: authViewModel)
        }
    }
}

struct ContentViewContainer: View {
    @ObservedObject var authViewModel: AuthViewModel

    var body: some View {
        ZStack {
            if authViewModel.isAuthenticated {
                MainTabView()
                    .environmentObject(authViewModel)
                    .transition(.opacity)
            } else {
                LoginView()
                    .environmentObject(authViewModel)
                    .transition(.opacity)
            }
        }
        .animation(.default, value: authViewModel.isAuthenticated)
        .onAppear {
            print("🎬 ContentViewContainer appeared, isAuthenticated: \(authViewModel.isAuthenticated)")
            authViewModel.checkAuthStatus()
        }
        .onChange(of: authViewModel.isAuthenticated) { oldValue, newValue in
            print("🔄 Authentication state changed from \(oldValue) to \(newValue)")
        }
    }
}

#Preview("Login State") {
    LoginView()
        .environmentObject(AuthViewModel())
}

#Preview("Authenticated State") {
    let authViewModel = AuthViewModel()
    authViewModel.isAuthenticated = true
    return MainTabView()
        .environmentObject(authViewModel)
}
