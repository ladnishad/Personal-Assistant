#!/bin/bash

# Script to add all Swift files to Xcode project
# Run this from the ios directory

echo "Adding Swift files to Xcode project..."

cd "Personal Assistant"

# List all new Swift files that need to be added
echo "Files to add:"
find . -name "*.swift" -type f | grep -E "(Models|Services|ViewModels|Views)/" | sort

echo ""
echo "To add these files to Xcode:"
echo "1. Open the project in Xcode"
echo "2. Right-click 'Personal Assistant' in Project Navigator"
echo "3. Select 'Add Files to Personal Assistant...'"
echo "4. Select the folders: Models, Services, ViewModels, Views"
echo "5. Check 'Copy items if needed' and 'Create groups'"
echo "6. Click Add"
echo "7. Clean build (Cmd+Shift+K) and run (Cmd+R)"
