//
//  ContentView.swift
//  Personal Assistant
//
//  Created by Nishad Lad on 11/15/25.
//

import SwiftUI

struct ContentView: View {
    var body: some View {
        VStack {
            Image(systemName: "brain.head.profile")
                .imageScale(.large)
                .foregroundStyle(
                    LinearGradient(
                        colors: [.blue, .purple],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
            Text("LifeOS")
                .font(.title)
                .fontWeight(.bold)
        }
        .padding()
    }
}

#Preview {
    ContentView()
}
