//
//  Email.swift
//  Personal Assistant
//
//  Created by LifeOS on 11/15/25.
//

import Foundation

struct Email: Codable, Identifiable {
    let id: String
    let userId: String
    let messageId: String
    let fromEmail: String
    let fromName: String?
    let to: [String]
    let cc: [String]
    let subject: String?
    let snippet: String?
    let bodyText: String?
    let hasAttachments: Bool
    let attachments: [Attachment]
    let labels: [EmailLabel]
    let isRead: Bool
    let isStarred: Bool
    let receivedAt: Date
    let extractedEntities: [String: String]

    enum CodingKeys: String, CodingKey {
        case id = "_id"
        case userId = "user_id"
        case messageId = "message_id"
        case fromEmail = "from_email"
        case fromName = "from_name"
        case to, cc, subject, snippet
        case bodyText = "body_text"
        case hasAttachments = "has_attachments"
        case attachments, labels
        case isRead = "is_read"
        case isStarred = "is_starred"
        case receivedAt = "received_at"
        case extractedEntities = "extracted_entities"
    }

    struct Attachment: Codable {
        let filename: String
        let mimeType: String
        let size: Int
        let attachmentId: String

        enum CodingKeys: String, CodingKey {
            case filename
            case mimeType = "mime_type"
            case size
            case attachmentId = "attachment_id"
        }
    }
}

enum EmailLabel: String, Codable {
    case inbox, sent, draft, spam, trash, important
}

struct EmailListResponse: Codable {
    let emails: [Email]
    let total: Int
    let page: Int
    let pageSize: Int

    enum CodingKeys: String, CodingKey {
        case emails, total, page
        case pageSize = "page_size"
    }
}
