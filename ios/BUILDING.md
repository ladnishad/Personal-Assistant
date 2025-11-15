# Building the LifeOS iOS App

## ✅ Pre-Flight Check

The project has been verified and is ready to build! Run the verification script to confirm:

```bash
./verify_project.sh
```

## 🏗️ Building the App

### Method 1: Using Xcode (Recommended)

1. **Open the project:**
   ```bash
   cd ios
   open "Personal Assistant.xcodeproj"
   ```

2. **Select a simulator:**
   - Click on the device selector (top of Xcode window)
   - Choose "iPhone 15 Pro" or any iOS 17.0+ simulator

3. **Build and Run:**
   - Press `Cmd + R` or click the Play button
   - Xcode will compile all 21 Swift files
   - The app will launch in the simulator

### Method 2: Command Line (Advanced)

```bash
# Build the project
xcodebuild -project "Personal Assistant.xcodeproj" \
           -scheme "Personal Assistant" \
           -sdk iphonesimulator \
           -destination 'platform=iOS Simulator,name=iPhone 15 Pro,OS=17.0'

# Run in simulator
xcrun simctl boot "iPhone 15 Pro"  # Boot simulator if not running
open -a Simulator
# Install and run the built app
```

## 📱 What You'll See

### First Launch
- **Login Screen** with LifeOS branding
- Email and password fields
- "Sign In" button with gradient
- "Sign Up" link at bottom

### After Login
- **Tab Bar** with 4 tabs:
  - 📧 Inbox
  - ✅ Tasks
  - 🤖 Assistant
  - ⚙️ Settings

## 🔧 Configuration

### Backend URL

By default, the app connects to `http://localhost:8000`.

To change this, edit `Services/APIService.swift`:

```swift
// Line 20
private let baseURL = "http://your-server:8000/api/v1"
```

For iOS Simulator connecting to Mac localhost:
```swift
private let baseURL = "http://127.0.0.1:8000/api/v1"
```

For physical iPhone on same network:
```swift
private let baseURL = "http://192.168.1.XXX:8000/api/v1"  // Your Mac's IP
```

## 🐛 Troubleshooting

### Build Errors

**"No such module 'Combine'"**
- This shouldn't happen - Combine is part of iOS SDK
- Clean build folder: `Cmd + Shift + K`
- Rebuild: `Cmd + B`

**"Cannot find 'AuthViewModel' in scope"**
- Make sure all files are included in the target
- Check Files & Groups shows all Swift files
- Clean and rebuild

**"Deployment target too high"**
- Already fixed! Should be iOS 17.0
- Verify with: `grep IPHONEOS_DEPLOYMENT_TARGET Personal\ Assistant.xcodeproj/project.pbxproj`

### Runtime Issues

**App shows blank screen**
- Check Console in Xcode for errors
- Verify Personal_AssistantApp.swift is being used (it is!)
- Look for red errors in Issue Navigator

**"Cannot connect to server"**
- Make sure backend is running: `docker-compose up`
- Check backend URL in APIService.swift
- For simulator, use `127.0.0.1` not `localhost`

**"Token expired" errors**
- Clear app data: Long press app icon → Delete App
- Reinstall and login again

## 📊 Project Stats

- **Total Files:** 21 Swift files
- **Architecture:** MVVM
- **Minimum iOS:** 17.0
- **Target:** iPhone & iPad
- **Framework:** 100% SwiftUI

## 🎨 App Features Included

### ✅ Implemented
- [x] Login/Register screens
- [x] JWT authentication
- [x] Email inbox with search
- [x] Task management (CRUD)
- [x] AI chat interface
- [x] Settings & integrations
- [x] Pull-to-refresh
- [x] Swipe actions
- [x] Loading states
- [x] Error handling
- [x] Tab navigation

### 🚧 Ready to Build
- [ ] Push notifications
- [ ] Calendar view
- [ ] File attachment preview
- [ ] Biometric auth (Face ID / Touch ID)
- [ ] Widget support
- [ ] Siri shortcuts

## 🚀 First Run Checklist

1. ✅ Backend is running (`docker-compose up`)
2. ✅ MongoDB is accessible
3. ✅ Xcode project opens without errors
4. ✅ Build succeeds (Cmd+B)
5. ✅ App launches in simulator (Cmd+R)
6. ✅ Login screen appears
7. ✅ Can register new account
8. ✅ Can login and see tabs

## 📝 Test Account

For testing, you can create an account directly in the app:

```
Email: test@lifeos.app
Password: TestPass123!
```

Or use the backend API directly:
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@lifeos.app",
    "password": "TestPass123!",
    "full_name": "Test User"
  }'
```

## 🎉 Success Indicators

When everything is working, you should see:

1. ✅ No build errors or warnings
2. ✅ App icon appears in simulator
3. ✅ Login screen with LifeOS branding
4. ✅ Smooth animations
5. ✅ Can register and login
6. ✅ All 4 tabs are accessible
7. ✅ Network requests succeed (check Xcode console)

## 📚 Next Steps

After successful build:

1. **Test all features**
   - Create account
   - Login
   - Sync emails (if connected)
   - Create tasks
   - Chat with assistant
   - Explore settings

2. **Connect integrations**
   - Go to Settings → Integrations
   - Connect Gmail/Outlook (requires backend OAuth setup)

3. **Customize**
   - Change app icon in Assets.xcassets
   - Modify color scheme
   - Add more features

## 🆘 Getting Help

If you encounter issues:

1. Check Xcode Console for errors
2. Run verification script: `./verify_project.sh`
3. Clean build: `Cmd + Shift + K`
4. Check backend logs: `docker-compose logs api`
5. Verify all files are present

## ✨ You're All Set!

The app is ready to build and run. Open Xcode and press Cmd+R to see your beautiful native iOS app in action!
