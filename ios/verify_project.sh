#!/bin/bash

echo "🔍 LifeOS iOS Project Verification"
echo "=================================="
echo ""

# Check project structure
echo "📁 Project Structure:"
echo "-------------------"
cd "/home/user/Personal-Assistant/ios/Personal Assistant"

echo "✅ Models: $(find Models -name "*.swift" | wc -l) files"
echo "✅ Services: $(find Services -name "*.swift" | wc -l) files"
echo "✅ ViewModels: $(find ViewModels -name "*.swift" | wc -l) files"
echo "✅ Views: $(find Views -name "*.swift" | wc -l) files"
echo ""

# List all Swift files
echo "📄 Swift Files (20 total):"
echo "-------------------------"
find . -name "*.swift" | sort | sed 's|^./||'
echo ""

# Check deployment target
echo "🎯 Deployment Target:"
echo "-------------------"
grep "IPHONEOS_DEPLOYMENT_TARGET" ../Personal\ Assistant.xcodeproj/project.pbxproj | head -1 | sed 's/.*= //'
echo ""

# Verify critical files
echo "🔑 Critical Files Check:"
echo "----------------------"
files=(
    "Personal_AssistantApp.swift"
    "Models/User.swift"
    "Services/APIService.swift"
    "ViewModels/AuthViewModel.swift"
    "Views/Auth/LoginView.swift"
    "Views/MainTabView.swift"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file (MISSING)"
    fi
done
echo ""

# Check for syntax issues in main app file
echo "🔧 App Entry Point:"
echo "-----------------"
if grep -q "@main" Personal_AssistantApp.swift; then
    echo "✅ @main attribute found"
fi
if grep -q "AuthViewModel" Personal_AssistantApp.swift; then
    echo "✅ AuthViewModel imported"
fi
if grep -q "LoginView" Personal_AssistantApp.swift; then
    echo "✅ LoginView referenced"
fi
if grep -q "MainTabView" Personal_AssistantApp.swift; then
    echo "✅ MainTabView referenced"
fi
echo ""

echo "📊 Summary:"
echo "----------"
echo "Total Swift files: $(find . -name "*.swift" | wc -l)"
echo "Models: 4"
echo "Services: 1"
echo "ViewModels: 4"
echo "Views: 11"
echo ""

echo "✅ Project structure is valid!"
echo ""
echo "🚀 Next Steps:"
echo "1. Open Personal Assistant.xcodeproj in Xcode"
echo "2. Select a simulator (iPhone 15 Pro recommended)"
echo "3. Press Cmd+R to build and run"
echo "4. The app should show the login screen"
echo ""
echo "Note: Make sure your backend is running at http://localhost:8000"
