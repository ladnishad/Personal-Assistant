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
            if authViewModel.isAuthenticated {
                MainTabView()
                    .environmentObject(authViewModel)
            } else {
                LoginView()
                    .environmentObject(authViewModel)
            }
        }
    }
}
