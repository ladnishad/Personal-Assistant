//
//  Task.swift
//  Personal Assistant
//
//  Created by LifeOS on 11/15/25.
//

import Foundation

struct TaskItem: Codable, Identifiable {
    let id: String
    let userId: String
    let title: String
    let description: String?
    let status: TaskStatus
    let priority: TaskPriority
    let dueDate: Date?
    let completedAt: Date?
    let reminderAt: Date?
    let reminderSent: Bool
    let tags: [String]
    let category: String?
    let content: String?
    let createdAt: Date
    let updatedAt: Date

    enum CodingKeys: String, CodingKey {
        case id = "_id"
        case userId = "user_id"
        case title, description, status, priority
        case dueDate = "due_date"
        case completedAt = "completed_at"
        case reminderAt = "reminder_at"
        case reminderSent = "reminder_sent"
        case tags, category, content
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

enum TaskStatus: String, Codable {
    case todo, inProgress = "in_progress", done, cancelled
}

enum TaskPriority: String, Codable {
    case low, medium, high, urgent

    var color: String {
        switch self {
        case .low: return "gray"
        case .medium: return "blue"
        case .high: return "orange"
        case .urgent: return "red"
        }
    }
}

struct TaskListResponse: Codable {
    let tasks: [TaskItem]
    let total: Int
}

struct TaskCreateRequest: Codable {
    let title: String
    let description: String?
    let priority: TaskPriority
    let dueDate: Date?
    let reminderAt: Date?
    let tags: [String]
    let category: String?

    enum CodingKeys: String, CodingKey {
        case title, description, priority
        case dueDate = "due_date"
        case reminderAt = "reminder_at"
        case tags, category
    }
}
