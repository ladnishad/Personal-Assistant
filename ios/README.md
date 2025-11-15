# LifeOS iOS App

A beautiful, native iOS app built with SwiftUI that connects to the LifeOS backend to provide an AI-powered personal assistant experience.

## Features

### 🔐 Authentication
- Email/password login and registration
- Secure JWT token management
- Auto-login with saved credentials

### 📧 Email Management
- View synced emails from Gmail/Outlook
- Search and filter emails
- Mark as read/unread, star/unstar
- Beautiful email detail view with attachment support
- Pull to refresh
- Unread filter toggle

### ✅ Task Management
- Create, view, and manage tasks
- Priority levels (Low, Medium, High, Urgent)
- Due dates and reminders
- Task status (To Do, In Progress, Done, Cancelled)
- Swipe to delete
- Filter by status
- Beautiful color-coded UI

### 🤖 AI Assistant Chat
- Natural language chat interface
- Powered by OpenAI GPT-4
- Tool execution (search emails, create tasks, etc.)
- Context-aware responses
- Long-term memory integration
- Real-time message history
- Loading indicators

### ⚙️ Settings
- User profile view
- Integration management
- Account settings
- Sign out functionality

## Architecture

### MVVM Pattern
```
Personal Assistant/
├── Models/
│   ├── User.swift
│   ├── Email.swift
│   ├── Task.swift
│   └── ChatMessage.swift
├── ViewModels/
│   ├── AuthViewModel.swift
│   ├── EmailViewModel.swift
│   ├── TaskViewModel.swift
│   └── ChatViewModel.swift
├── Views/
│   ├── Auth/
│   │   ├── LoginView.swift
│   │   └── RegisterView.swift
│   ├── Email/
│   │   ├── EmailInboxView.swift
│   │   └── EmailDetailView.swift
│   ├── Tasks/
│   │   ├── TasksView.swift
│   │   └── NewTaskView.swift
│   ├── Chat/
│   │   └── AgentChatView.swift
│   ├── Settings/
│   │   ├── SettingsView.swift
│   │   └── IntegrationsView.swift
│   └── MainTabView.swift
└── Services/
    └── APIService.swift
```

## Design Principles

### Following Apple's Human Interface Guidelines
- **Native Components**: Uses only SwiftUI native components
- **Consistency**: Follows iOS design patterns and conventions
- **Clarity**: Clear typography and visual hierarchy
- **Deference**: Content-first design
- **Feedback**: Responsive interactions and animations
- **Accessibility**: VoiceOver ready, Dynamic Type support

### UI/UX Features
- Smooth animations and transitions
- Pull-to-refresh for data updates
- Swipe actions for quick operations
- Progressive disclosure
- Error handling with user-friendly messages
- Loading states
- Empty states with helpful CTAs
- Tab-based navigation
- Search functionality
- Segmented controls for filtering

## Setup

### Prerequisites
- Xcode 15.0 or later
- iOS 17.0 or later
- LifeOS backend running (see main README)

### Configuration

1. **Open the project in Xcode:**
   ```bash
   cd ios
   open "Personal Assistant.xcodeproj"
   ```

2. **Update API Base URL:**
   Edit `Services/APIService.swift` and update the `baseURL`:
   ```swift
   private let baseURL = "http://your-backend-url:8000/api/v1"
   ```

   For local development:
   ```swift
   private let baseURL = "http://localhost:8000/api/v1"
   ```

   For iOS Simulator connecting to localhost on Mac:
   ```swift
   private let baseURL = "http://127.0.0.1:8000/api/v1"
   ```

3. **Build and Run:**
   - Select your target device or simulator
   - Press Cmd+R or click the Play button
   - The app will build and launch

### Running with Local Backend

1. Start the backend server:
   ```bash
   cd ..
   docker-compose up
   ```

2. Ensure MongoDB and backend are running
3. If using iOS Simulator, make sure the backend is accessible at `http://127.0.0.1:8000`

## Usage

### First Time Setup
1. Launch the app
2. Create a new account or sign in
3. Go to Settings → Integrations
4. Connect your Gmail or Outlook account (requires backend OAuth setup)
5. Sync your emails and start chatting with the AI assistant!

### Main Features

#### Inbox
- View all synced emails
- Tap to read full email
- Swipe actions for quick operations
- Pull down to refresh
- Tap filter icon to show unread only

#### Tasks
- Tap + to create a new task
- Set priority and due date
- Tap checkbox to mark complete
- Swipe left to delete
- Use segmented control to filter by status

#### Assistant
- Chat naturally with the AI
- Ask it to search emails
- Request task creation
- Get insights from your data
- Clear chat from menu

#### Settings
- View your profile
- Manage connected accounts
- Sign out

## API Integration

The app uses a clean API service layer (`APIService.swift`) that handles:
- Authentication with JWT tokens
- Automatic token storage
- Error handling
- Type-safe requests
- Async/await for modern Swift concurrency

### Example Usage
```swift
// Login
let tokens = try await APIService.shared.login(email: email, password: password)

// Get emails
let response = try await APIService.shared.getEmails(page: 1)

// Create task
let task = try await APIService.shared.createTask(request)

// Chat with agent
let response = try await APIService.shared.sendChatMessage(message: text)
```

## Screenshots

*(Add screenshots here after running the app)*

## Technologies Used

- **SwiftUI**: Modern declarative UI framework
- **Combine**: Reactive programming
- **Async/Await**: Modern concurrency
- **URLSession**: Native networking
- **Codable**: JSON encoding/decoding
- **UserDefaults**: Secure token storage

## Future Enhancements

- [ ] Push notifications for reminders
- [ ] Widget support
- [ ] Siri integration
- [ ] Shortcuts app support
- [ ] Calendar view
- [ ] File attachments preview
- [ ] Rich text email composer
- [ ] Biometric authentication
- [ ] Dark mode customization
- [ ] Haptic feedback
- [ ] Handoff support
- [ ] iPad optimization
- [ ] macOS Catalyst support

## Contributing

When contributing to the iOS app:
1. Follow Swift style guidelines
2. Use SwiftUI best practices
3. Add comments for complex logic
4. Test on multiple devices/simulators
5. Ensure accessibility support

## Support

For issues specific to the iOS app, please check:
- Xcode console for errors
- Network connectivity
- Backend API availability
- iOS version compatibility

## License

MIT License - See LICENSE file for details
