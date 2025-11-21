//
//  TaskViewModel.swift
//  Personal Assistant
//
//  Created by LifeOS on 11/15/25.
//

import Foundation
import Combine

@MainActor
class TaskViewModel: ObservableObject {
    @Published var tasks: [TaskItem] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let apiService = APIService.shared

    func loadTasks() async {
        isLoading = true
        errorMessage = nil

        do {
            print("📋 Loading all tasks")
            let response = try await apiService.getTasks(status: nil)
            print("✅ Loaded \(response.tasks.count) tasks")
            tasks = response.tasks
        } catch let error as APIError {
            print("❌ Task loading error: \(error.errorDescription ?? "unknown")")
            errorMessage = error.errorDescription
        } catch {
            print("❌ Unexpected error loading tasks: \(error)")
            errorMessage = "Failed to load tasks: \(error.localizedDescription)"
        }

        isLoading = false
    }

    func createTask(title: String, description: String?, priority: TaskPriority, dueDate: Date?) async {
        let request = TaskCreateRequest(
            title: title,
            description: description,
            priority: priority,
            dueDate: dueDate,
            reminderAt: nil,
            tags: [],
            category: nil
        )

        do {
            let newTask = try await apiService.createTask(request)
            tasks.insert(newTask, at: 0)
        } catch let error as APIError {
            errorMessage = error.errorDescription
        } catch {
            errorMessage = "Failed to create task"
        }
    }

    func updateTaskStatus(_ task: TaskItem, status: TaskStatus) async {
        do {
            let updatedTask = try await apiService.updateTask(id: task.id, status: status)
            if let index = tasks.firstIndex(where: { $0.id == task.id }) {
                tasks[index] = updatedTask
            }
        } catch let error as APIError {
            errorMessage = error.errorDescription
        } catch {
            errorMessage = "Failed to update task"
        }
    }

    func deleteTask(_ task: TaskItem) async {
        do {
            try await apiService.deleteTask(id: task.id)
            tasks.removeAll { $0.id == task.id }
        } catch let error as APIError {
            errorMessage = error.errorDescription
        } catch {
            errorMessage = "Failed to delete task"
        }
    }
}
