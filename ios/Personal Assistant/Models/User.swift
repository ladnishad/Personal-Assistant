//
//  User.swift
//  Personal Assistant
//
//  Created by LifeOS on 11/15/25.
//

import Foundation

struct User: Codable, Identifiable {
    let id: String
    let email: String
    let fullName: String?
    let isActive: Bool
    let isVerified: Bool
    let timezone: String
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id = "_id"
        case email
        case fullName = "full_name"
        case isActive = "is_active"
        case isVerified = "is_verified"
        case timezone
        case createdAt = "created_at"
    }
}

struct TokenResponse: Codable {
    let accessToken: String
    let refreshToken: String
    let tokenType: String
    let expiresIn: Int

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
        case tokenType = "token_type"
        case expiresIn = "expires_in"
    }
}

struct UserResponse: Codable {
    let id: String
    let email: String
    let fullName: String?
    let isActive: Bool
    let isVerified: Bool
    let timezone: String
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id = "_id"
        case email
        case fullName = "full_name"
        case isActive = "is_active"
        case isVerified = "is_verified"
        case timezone
        case createdAt = "created_at"
    }
}
