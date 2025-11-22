//
//  MainTabView.swift
//  Personal Assistant
//
//  Created by LifeOS on 11/15/25.
//

import SwiftUI

struct MainTabView: View {
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            TasksView()
                .tabItem {
                    Label("Tasks", systemImage: "checklist")
                }
                .tag(0)

            ConversationsListView()
                .tabItem {
                    Label("Chat", systemImage: "brain.head.profile")
                }
                .tag(1)

            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gear")
                }
                .tag(2)
        }
        .tint(.blue)
    }
}

#Preview {
    MainTabView()
}
