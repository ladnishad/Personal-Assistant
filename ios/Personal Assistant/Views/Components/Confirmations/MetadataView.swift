//
//  MetadataView.swift
//  Personal Assistant
//
//  Display additional metadata for confirmation actions
//

import SwiftUI

struct MetadataView: View {
    let metadata: [String: AnyCodable]?
    @State private var isExpanded = false

    var body: some View {
        if let metadata = metadata, !metadata.isEmpty {
            VStack(alignment: .leading, spacing: 12) {
                // Header with expand/collapse
                Button(action: { withAnimation(.spring()) { isExpanded.toggle() } }) {
                    HStack {
                        Image(systemName: isExpanded ? "chevron.down" : "chevron.right")
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundColor(.secondary)

                        Text("Additional Details")
                            .font(.footnote)
                            .fontWeight(.semibold)
                            .foregroundColor(.secondary)

                        Spacer()

                        Text("\(metadata.count) items")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }
                }
                .buttonStyle(PlainButtonStyle())

                // Metadata content
                if isExpanded {
                    VStack(alignment: .leading, spacing: 8) {
                        ForEach(sortedMetadata, id: \.key) { item in
                            MetadataRow(key: item.key, value: item.value)
                        }
                    }
                    .padding(.vertical, 8)
                    .padding(.horizontal, 12)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(Color.secondary.opacity(0.1))
                    )
                    .transition(.asymmetric(
                        insertion: .scale.combined(with: .opacity),
                        removal: .scale.combined(with: .opacity)
                    ))
                }
            }
        }
    }

    private var sortedMetadata: [(key: String, value: AnyCodable)] {
        guard let metadata = metadata else { return [] }
        return metadata.sorted { $0.key < $1.key }
    }
}

struct MetadataRow: View {
    let key: String
    let value: AnyCodable

    private var formattedKey: String {
        // Convert snake_case to Title Case
        key.split(separator: "_")
            .map { $0.capitalized }
            .joined(separator: " ")
    }

    private var formattedValue: String {
        switch value.value {
        case let string as String:
            return string
        case let bool as Bool:
            return bool ? "Yes" : "No"
        case let number as NSNumber:
            if number.isEqual(to: NSNumber(value: number.intValue)) {
                return "\(number.intValue)"
            } else {
                return String(format: "%.2f", number.doubleValue)
            }
        case let array as [Any]:
            return "[\(array.count) items]"
        case let dict as [String: Any]:
            return "{\(dict.count) properties}"
        default:
            return String(describing: value.value)
        }
    }

    private var valueColor: Color {
        switch value.value {
        case is Bool:
            return .blue
        case is NSNumber:
            return .purple
        case is [Any], is [String: Any]:
            return .orange
        default:
            return .primary
        }
    }

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Text(formattedKey + ":")
                .font(.caption)
                .fontWeight(.medium)
                .foregroundColor(.secondary)
                .frame(minWidth: 100, alignment: .leading)

            Text(formattedValue)
                .font(.caption)
                .foregroundColor(valueColor)
                .multilineTextAlignment(.leading)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

#Preview {
    VStack(spacing: 20) {
        MetadataView(metadata: [
            "target_url": AnyCodable("https://example.com"),
            "button_text": AnyCodable("Submit Form"),
            "field_count": AnyCodable(5),
            "is_secure": AnyCodable(true),
            "form_data": AnyCodable([
                "username": "test_user",
                "email": "test@example.com"
            ])
        ])

        MetadataView(metadata: [
            "action_type": AnyCodable("navigation"),
            "destination": AnyCodable("checkout page")
        ])

        MetadataView(metadata: nil)
    }
    .padding()
}