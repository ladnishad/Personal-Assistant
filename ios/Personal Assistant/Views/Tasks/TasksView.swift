//
//  TasksView.swift
//  Personal Assistant
//
//  Created by LifeOS on 11/15/25.
//

import SwiftUI

struct TasksView: View {
    @StateObject private var viewModel = TaskViewModel()
    @State private var showingNewTask = false

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                filterPicker
                    .padding(.horizontal, 16)
                    .padding(.top, 8)
                    .padding(.bottom, 12)

                if viewModel.isLoading && viewModel.tasks.isEmpty {
                    ProgressView()
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if viewModel.tasks.isEmpty {
                    emptyStateView
                } else {
                    taskList
                }
            }
            .navigationTitle("Tasks")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: {
                        showingNewTask = true
                    }) {
                        Image(systemName: "plus")
                    }
                }
            }
            .sheet(isPresented: $showingNewTask) {
                NewTaskView(viewModel: viewModel)
            }
            .task {
                await viewModel.loadTasks()
            }
            .refreshable {
                await viewModel.loadTasks()
            }
        }
    }

    private var filterPicker: some View {
        Picker("Status", selection: Binding(
            get: { viewModel.selectedStatus ?? .todo },
            set: { viewModel.filterTasks(by: $0) }
        )) {
            Text("To Do").tag(TaskStatus.todo)
            Text("In Progress").tag(TaskStatus.inProgress)
            Text("Done").tag(TaskStatus.done)
        }
        .pickerStyle(.segmented)
    }

    private var taskList: some View {
        List {
            ForEach(viewModel.tasks) { task in
                ZStack {
                    NavigationLink(destination: TaskDetailView(taskId: task.id)) {
                        EmptyView()
                    }
                    .opacity(0)

                    TaskRowView(task: task, viewModel: viewModel)
                }
            }
        }
        .listStyle(.plain)
    }

    private var emptyStateView: some View {
        VStack(spacing: 16) {
            Image(systemName: "checkmark.circle")
                .font(.system(size: 60))
                .foregroundColor(.secondary)

            Text("No Tasks")
                .font(.title2)
                .fontWeight(.semibold)

            Text("Create your first task to get started")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)

            Button(action: {
                showingNewTask = true
            }) {
                Label("New Task", systemImage: "plus")
                    .fontWeight(.medium)
            }
            .buttonStyle(.borderedProminent)
            .padding(.top)
        }
        .padding()
    }
}

struct TaskRowView: View {
    let task: TaskItem
    @ObservedObject var viewModel: TaskViewModel

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Button(action: {
                Task {
                    let newStatus: TaskStatus = task.status == .done ? .todo : .done
                    await viewModel.updateTaskStatus(task, status: newStatus)
                }
            }) {
                Image(systemName: task.status == .done ? "checkmark.circle.fill" : "circle")
                    .font(.title3)
                    .foregroundColor(task.status == .done ? .green : .secondary)
            }
            .buttonStyle(.plain)

            VStack(alignment: .leading, spacing: 6) {
                Text(task.title)
                    .font(.body)
                    .fontWeight(.medium)
                    .strikethrough(task.status == .done)
                    .foregroundColor(task.status == .done ? .secondary : .primary)

                if let description = task.description {
                    Text(description)
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .lineLimit(2)
                }

                HStack(spacing: 12) {
                    // Priority badge
                    HStack(spacing: 4) {
                        Circle()
                            .fill(colorForPriority(task.priority))
                            .frame(width: 6, height: 6)
                        Text(task.priority.rawValue.capitalized)
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }

                    if let dueDate = task.dueDate {
                        HStack(spacing: 4) {
                            Image(systemName: "calendar")
                            Text(dueDate, style: .date)
                        }
                        .font(.caption2)
                        .foregroundColor(dueDate < Date() && task.status != .done ? .red : .secondary)
                    }

                    if !task.tags.isEmpty {
                        HStack(spacing: 4) {
                            Image(systemName: "tag")
                            Text(task.tags.prefix(2).joined(separator: ", "))
                        }
                        .font(.caption2)
                        .foregroundColor(.secondary)
                    }
                }
            }

            Spacer()
        }
        .padding(.vertical, 4)
        .swipeActions(edge: .trailing, allowsFullSwipe: false) {
            Button(role: .destructive) {
                Task {
                    await viewModel.deleteTask(task)
                }
            } label: {
                Label("Delete", systemImage: "trash")
            }
        }
    }

    private func colorForPriority(_ priority: TaskPriority) -> Color {
        switch priority {
        case .low: return .gray
        case .medium: return .blue
        case .high: return .orange
        case .urgent: return .red
        }
    }
}

#Preview {
    TasksView()
}
