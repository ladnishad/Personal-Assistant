//
//  TaskDetailView.swift
//  Personal Assistant
//
//  Created by LifeOS
//

import SwiftUI
import Combine
import MarkdownUI

struct TaskDetailView: View {
    let taskId: String
    @StateObject private var viewModel: TaskDetailViewModel
    @Environment(\.dismiss) private var dismiss
    @State private var showChatSheet = false
    @State private var isTaskUpdating = false

    init(taskId: String) {
        self.taskId = taskId
        _viewModel = StateObject(wrappedValue: TaskDetailViewModel(taskId: taskId))
    }

    var body: some View {
        ZStack(alignment: .bottom) {
            ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                if viewModel.isLoading {
                    ProgressView()
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if let task = viewModel.task {
                    // Task Header
                    taskHeader(task)

                    Divider()

                    // Task Metadata
                    taskMetadata(task)

                    Divider()

                    // Rich Content Area with Empty State
                    if let content = task.content, !content.isEmpty {
                        VStack(alignment: .leading, spacing: 12) {
                            HStack {
                                Text("Details")
                                    .font(.title3)
                                    .fontWeight(.semibold)
                                Spacer()
                            }

                            MarkdownView(markdown: content)
                                .padding()
                                .background(Color(.systemGray6))
                                .cornerRadius(12)
                        }
                        .padding(.horizontal)

                        Divider()
                            .padding(.vertical, 8)
                    } else {
                        // Empty state when no content yet
                        VStack(spacing: 20) {
                            ZStack {
                                Circle()
                                    .fill(
                                        LinearGradient(
                                            colors: [Color.blue.opacity(0.1), Color.purple.opacity(0.1)],
                                            startPoint: .topLeading,
                                            endPoint: .bottomTrailing
                                        )
                                    )
                                    .frame(width: 100, height: 100)

                                Image(systemName: "doc.text.magnifyingglass")
                                    .font(.system(size: 40))
                                    .foregroundStyle(
                                        LinearGradient(
                                            colors: [.blue, .purple],
                                            startPoint: .topLeading,
                                            endPoint: .bottomTrailing
                                        )
                                    )
                            }

                            VStack(spacing: 8) {
                                Text("No details yet")
                                    .font(.title3)
                                    .fontWeight(.semibold)

                                Text("Start a conversation below and your assistant will research and document everything here")
                                    .font(.subheadline)
                                    .foregroundColor(.secondary)
                                    .multilineTextAlignment(.center)
                                    .padding(.horizontal, 32)
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 32)

                        Divider()
                            .padding(.vertical, 8)
                    }
                } else if let errorMessage = viewModel.errorMessage {
                    VStack(spacing: 16) {
                        Image(systemName: "exclamationmark.triangle")
                            .font(.largeTitle)
                            .foregroundColor(.orange)
                        Text(errorMessage)
                            .multilineTextAlignment(.center)
                    }
                    .padding()
                }
            }
            .padding(.vertical)
            .padding(.bottom, 80) // Add padding for chat trigger
        }

            // Chat trigger button at bottom
            if let task = viewModel.task {
                VStack {
                    Spacer()

                    HStack {
                        Spacer()

                        Button(action: {
                            showChatSheet = true
                        }) {
                            HStack(spacing: 8) {
                                Image(systemName: "sparkles")
                                    .font(.system(size: 14, weight: .semibold))

                                Text("Ask about this task...")
                                    .font(.subheadline)
                            }
                            .foregroundColor(.secondary)
                            .padding(.horizontal, 20)
                            .padding(.vertical, 12)
                            .background(
                                RoundedRectangle(cornerRadius: 25)
                                    .fill(Color(.systemGray6))
                                    .shadow(color: .black.opacity(0.1), radius: 8, x: 0, y: 2)
                            )
                        }
                        .buttonStyle(.plain)

                        Spacer()
                    }
                    .padding(.bottom, 20)
                    .overlay(
                        Group {
                            if isTaskUpdating {
                                HStack(spacing: 6) {
                                    ProgressView()
                                        .scaleEffect(0.7)
                                    Text("Updating task...")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                                .padding(.horizontal, 12)
                                .padding(.vertical, 6)
                                .background(
                                    Capsule()
                                        .fill(Color(.systemBackground))
                                        .shadow(color: .black.opacity(0.1), radius: 4)
                                )
                                .offset(y: -60)
                            }
                        }
                    )
                }
                .sheet(isPresented: $showChatSheet) {
                    TaskChatSheet(taskId: taskId, task: task) {
                        // Reload task when chat updates it
                        isTaskUpdating = true
                        Task {
                            try? await Task.sleep(nanoseconds: 500_000_000) // Small delay for animation
                            await viewModel.loadTask()
                            isTaskUpdating = false
                        }
                    }
                    .presentationDetents([.medium, .large])
                    .presentationDragIndicator(.visible)
                }
            }
        }
        .navigationTitle("Task Details")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar(.hidden, for: .tabBar)
        .task {
            await viewModel.loadTask()
        }
        .refreshable {
            await viewModel.loadTask()
        }
    }

    @ViewBuilder
    private func taskHeader(_ task: TaskItem) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 8) {
                    Text(task.title)
                        .font(.title2)
                        .fontWeight(.bold)

                    if let description = task.description {
                        Text(description)
                            .font(.body)
                            .foregroundColor(.secondary)
                    }
                }

                Spacer()

                // Status toggle button
                Button(action: {
                    Task {
                        await viewModel.toggleTaskStatus()
                    }
                }) {
                    Image(systemName: task.status == .done ? "checkmark.circle.fill" : "circle")
                        .font(.title)
                        .foregroundColor(task.status == .done ? .green : .gray)
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.horizontal)
    }

    @ViewBuilder
    private func taskMetadata(_ task: TaskItem) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            // Priority
            HStack {
                Label("Priority", systemImage: "flag.fill")
                    .foregroundColor(.secondary)
                Spacer()
                HStack(spacing: 6) {
                    Circle()
                        .fill(colorForPriority(task.priority))
                        .frame(width: 8, height: 8)
                    Text(task.priority.rawValue.capitalized)
                        .fontWeight(.medium)
                }
            }

            // Status
            HStack {
                Label("Status", systemImage: "circle.fill")
                    .foregroundColor(.secondary)
                Spacer()
                Text(statusText(task.status))
                    .fontWeight(.medium)
                    .foregroundColor(colorForStatus(task.status))
            }

            // Due Date
            if let dueDate = task.dueDate {
                HStack {
                    Label("Due Date", systemImage: "calendar")
                        .foregroundColor(.secondary)
                    Spacer()
                    Text(dueDate, style: .date)
                        .fontWeight(.medium)
                        .foregroundColor(dueDate < Date() && task.status != .done ? .red : .primary)
                }
            }

            // Tags
            if !task.tags.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Label("Tags", systemImage: "tag")
                        .foregroundColor(.secondary)

                    FlowLayout(spacing: 8) {
                        ForEach(task.tags, id: \.self) { tag in
                            Text(tag)
                                .font(.caption)
                                .padding(.horizontal, 12)
                                .padding(.vertical, 6)
                                .background(Color.blue.opacity(0.1))
                                .foregroundColor(.blue)
                                .cornerRadius(12)
                        }
                    }
                }
            }
        }
        .padding(.horizontal)
    }

    private func colorForPriority(_ priority: TaskPriority) -> Color {
        switch priority {
        case .low: return .gray
        case .medium: return .blue
        case .high: return .orange
        case .urgent: return .red
        }
    }

    private func colorForStatus(_ status: TaskStatus) -> Color {
        switch status {
        case .todo: return .blue
        case .done: return .green
        }
    }

    private func statusText(_ status: TaskStatus) -> String {
        switch status {
        case .todo: return "To Do"
        case .done: return "Done"
        }
    }
}

// MARK: - MarkdownView
struct MarkdownView: View {
    let markdown: String

    var body: some View {
        Markdown(markdown)
            .markdownTheme(.notion)
            .textSelection(.enabled)
    }
}

// MARK: - Notion-like Markdown Theme
extension Theme {
    static let notion = Theme()
        .text {
            ForegroundColor(.primary)
            FontSize(16)
        }
        .heading1 { configuration in
            configuration.label
                .markdownTextStyle {
                    FontWeight(.bold)
                    FontSize(28)
                }
                .markdownMargin(top: 16, bottom: 8)
        }
        .heading2 { configuration in
            configuration.label
                .markdownTextStyle {
                    FontWeight(.semibold)
                    FontSize(24)
                }
                .markdownMargin(top: 14, bottom: 6)
        }
        .heading3 { configuration in
            configuration.label
                .markdownTextStyle {
                    FontWeight(.semibold)
                    FontSize(20)
                }
                .markdownMargin(top: 12, bottom: 4)
        }
        .paragraph { configuration in
            configuration.label
                .markdownMargin(top: 4, bottom: 4)
        }
        .link {
            ForegroundColor(.blue)
        }
        .strong {
            FontWeight(.semibold)
        }
        .emphasis {
            FontStyle(.italic)
        }
        .listItem { configuration in
            configuration.label
                .markdownMargin(top: 4, bottom: 4)
        }
        .codeBlock { configuration in
            configuration.label
                .padding(12)
                .background(Color(.systemGray6))
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .markdownTextStyle {
                    FontFamilyVariant(.monospaced)
                    FontSize(14)
                }
                .markdownMargin(top: 8, bottom: 8)
        }
        .code {
            FontFamilyVariant(.monospaced)
            FontSize(14)
            BackgroundColor(Color(.systemGray5))
        }
        .blockquote { configuration in
            HStack(alignment: .top, spacing: 0) {
                RoundedRectangle(cornerRadius: 2)
                    .fill(Color.blue.opacity(0.5))
                    .frame(width: 4)
                configuration.label
                    .markdownTextStyle {
                        FontStyle(.italic)
                        ForegroundColor(.secondary)
                    }
                    .padding(.leading, 12)
            }
            .markdownMargin(top: 8, bottom: 8)
        }
        .table { configuration in
            configuration.label
                .markdownMargin(top: 8, bottom: 8)
        }
}

// MARK: - FlowLayout for tags
struct FlowLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let rows = arrangeRows(proposal: proposal, subviews: subviews)
        let height = rows.map { $0.maxHeight }.reduce(0, +) + CGFloat(rows.count - 1) * spacing
        return CGSize(width: proposal.width ?? 0, height: height)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let rows = arrangeRows(proposal: proposal, subviews: subviews)
        var y = bounds.minY

        for row in rows {
            var x = bounds.minX
            for (subview, size) in zip(row.subviews, row.sizes) {
                subview.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(size))
                x += size.width + spacing
            }
            y += row.maxHeight + spacing
        }
    }

    private func arrangeRows(proposal: ProposedViewSize, subviews: Subviews) -> [(subviews: [LayoutSubview], sizes: [CGSize], maxHeight: CGFloat)] {
        var rows: [(subviews: [LayoutSubview], sizes: [CGSize], maxHeight: CGFloat)] = []
        var currentRow: ([LayoutSubview], [CGSize], CGFloat) = ([], [], 0)
        var x: CGFloat = 0
        let maxWidth = proposal.width ?? 0

        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)

            if x + size.width > maxWidth && !currentRow.0.isEmpty {
                rows.append(currentRow)
                currentRow = ([], [], 0)
                x = 0
            }

            currentRow.0.append(subview)
            currentRow.1.append(size)
            currentRow.2 = max(currentRow.2, size.height)
            x += size.width + spacing
        }

        if !currentRow.0.isEmpty {
            rows.append(currentRow)
        }

        return rows
    }
}

// MARK: - TaskDetailViewModel
@MainActor
class TaskDetailViewModel: ObservableObject {
    @Published var task: TaskItem?
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let taskId: String
    private let apiService = APIService.shared

    init(taskId: String) {
        self.taskId = taskId
    }

    func loadTask() async {
        isLoading = true
        errorMessage = nil

        do {
            task = try await apiService.getTask(id: taskId)
        } catch let error as APIError {
            errorMessage = error.errorDescription
        } catch {
            errorMessage = "Failed to load task"
        }

        isLoading = false
    }

    func toggleTaskStatus() async {
        guard let currentTask = task else { return }

        let newStatus: TaskStatus = currentTask.status == .done ? .todo : .done

        do {
            let updatedTask = try await apiService.updateTask(id: taskId, status: newStatus)
            task = updatedTask
        } catch let error as APIError {
            errorMessage = error.errorDescription
        } catch {
            errorMessage = "Failed to update task"
        }
    }
}

#Preview {
    NavigationStack {
        TaskDetailView(taskId: "preview-task-id")
    }
}
