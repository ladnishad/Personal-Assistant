# Screenshot Stream Integration Guide

This guide shows how to integrate the screenshot streaming feature into your iOS chat interface.

## Overview

The screenshot streaming feature allows users to see what the computer control agent is doing in real-time by displaying screenshots of the agent's actions in the chat interface.

## Components

### 1. Models (Already Implemented)

- `ScreenshotCapture` - Represents a single screenshot with metadata
- `AgentChatRequest.streamScreenshots` - Toggle to enable screenshot streaming
- `AgentChatResponse.screenshots` - Array of captured screenshots

### 2. UI Component

`ScreenshotStreamView` - A collapsible view that displays screenshots with:
- Toggle to show/hide the preview
- Navigation between multiple screenshots
- Timestamp and action context display
- Responsive image rendering

## Integration Example

### Step 1: Update ChatViewModel

Add a state variable to control screenshot streaming:

```swift
class ChatViewModel: ObservableObject {
    @Published var streamScreenshots: Bool = false
    @Published var messages: [ChatMessage] = []

    func sendMessage(_ text: String) async {
        // Create request with screenshot streaming enabled
        let request = AgentChatRequest(
            message: text,
            useMemory: true,
            conversationId: currentConversationId,
            streamScreenshots: streamScreenshots
        )

        // Send to API and handle response
        guard let response = await apiService.chat(request: request) else {
            return
        }

        // Create message with screenshots
        let message = ChatMessage(
            role: .assistant,
            content: response.message,
            toolsUsed: response.toolsUsed,
            actionsTaken: response.actionsTaken.map { $0.tool },
            screenshots: response.screenshots  // Add screenshots to message
        )

        messages.append(message)
    }
}
```

### Step 2: Update ChatMessage Model

Add screenshots field to your ChatMessage struct:

```swift
struct ChatMessage: Identifiable, Equatable {
    let id: UUID
    let role: MessageRole
    let content: String
    let timestamp: Date
    let toolsUsed: [String]?
    let actionsTaken: [String]?
    let taskReference: TaskReference?
    let screenshots: [ScreenshotCapture]?  // Add this field

    init(
        id: UUID = UUID(),
        role: MessageRole,
        content: String,
        timestamp: Date = Date(),
        toolsUsed: [String]? = nil,
        actionsTaken: [String]? = nil,
        taskReference: TaskReference? = nil,
        screenshots: [ScreenshotCapture]? = nil  // Add this parameter
    ) {
        self.id = id
        self.role = role
        self.content = content
        self.timestamp = timestamp
        self.toolsUsed = toolsUsed
        self.actionsTaken = actionsTaken
        self.taskReference = taskReference
        self.screenshots = screenshots
    }
}
```

### Step 3: Update Chat View

Integrate the ScreenshotStreamView into your chat message display:

```swift
struct ChatView: View {
    @StateObject var viewModel = ChatViewModel()

    var body: some View {
        VStack {
            // Settings toggle
            Toggle("Stream Agent Screen", isOn: $viewModel.streamScreenshots)
                .padding()

            // Message list
            ScrollView {
                ForEach(viewModel.messages) { message in
                    VStack(alignment: .leading, spacing: 8) {
                        // Message content
                        Text(message.content)
                            .padding()
                            .background(messageBackground(for: message.role))
                            .cornerRadius(12)

                        // Screenshot stream (only for assistant messages with screenshots)
                        if message.role == .assistant,
                           let screenshots = message.screenshots,
                           !screenshots.isEmpty {
                            ScreenshotStreamView(screenshots: screenshots)
                                .padding(.horizontal)
                        }
                    }
                }
            }

            // Message input
            // ... your message input UI
        }
    }

    private func messageBackground(for role: ChatMessage.MessageRole) -> Color {
        role == .user ? .blue.opacity(0.2) : .gray.opacity(0.2)
    }
}
```

## API Service Example

```swift
class AgentAPIService {
    func chat(request: AgentChatRequest) async -> AgentChatResponse? {
        guard let url = URL(string: "\(baseURL)/api/v1/agent/chat") else {
            return nil
        }

        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.setValue("Bearer \(authToken)", forHTTPHeaderField: "Authorization")

        do {
            let encoder = JSONEncoder()
            encoder.keyEncodingStrategy = .convertToSnakeCase
            urlRequest.httpBody = try encoder.encode(request)

            let (data, _) = try await URLSession.shared.data(for: urlRequest)

            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            decoder.dateDecodingStrategy = .iso8601

            return try decoder.decode(AgentChatResponse.self, from: data)
        } catch {
            print("API Error: \(error)")
            return nil
        }
    }
}
```

## Usage

1. **Enable screenshot streaming**: Toggle the `streamScreenshots` option in your chat settings
2. **Send a computer control task**: Ask the agent to perform a browser/desktop task
   - Example: "Book a table at OpenTable for 2 people tonight at 7pm"
3. **View the preview**: The ScreenshotStreamView will appear below the assistant's message
4. **Navigate screenshots**: Use the arrow buttons to view different screenshots if multiple were captured
5. **Hide/show**: Click the header to collapse or expand the preview

## Performance Considerations

- Screenshots are base64-encoded and can be large (~200KB-500KB each)
- Consider lazy loading for messages with many screenshots
- Add a limit to how many screenshots are shown at once
- Cache decoded UIImages to avoid repeated decoding

## Customization

The `ScreenshotStreamView` can be customized:

```swift
ScreenshotStreamView(screenshots: screenshots)
    .frame(maxHeight: 400)  // Limit height
    .padding()
    // Add your custom styling
```

## Security Notes

- Screenshots may contain sensitive information
- Consider adding a blur effect by default with explicit unblur action
- Implement secure storage if persisting screenshots locally
- Respect user privacy preferences

## Troubleshooting

### Screenshots not appearing
- Verify `streamScreenshots: true` in AgentChatRequest
- Check network logs to confirm screenshots are in API response
- Validate base64 decoding is successful

### Performance issues
- Reduce image quality in backend (adjust PIL quality parameter)
- Implement pagination for large screenshot arrays
- Use thumbnail previews with full-size on tap

### Memory warnings
- Clear screenshot data when messages scroll off-screen
- Implement message pagination/cleanup for old conversations
- Monitor memory usage with Instruments
