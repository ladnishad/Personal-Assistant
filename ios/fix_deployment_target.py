#!/usr/bin/env python3
"""
Script to update the iOS deployment target in Xcode project file
from iOS 26.1 (invalid) to iOS 17.0
"""

import re
import sys

def update_deployment_target(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    # Replace IPHONEOS_DEPLOYMENT_TARGET = 26.1; with 17.0;
    updated_content = re.sub(
        r'IPHONEOS_DEPLOYMENT_TARGET = 26\.1;',
        'IPHONEOS_DEPLOYMENT_TARGET = 17.0;',
        content
    )

    with open(file_path, 'w') as f:
        f.write(updated_content)

    print("✅ Updated deployment target from iOS 26.1 to iOS 17.0")

if __name__ == '__main__':
    project_file = '/home/user/Personal-Assistant/ios/Personal Assistant.xcodeproj/project.pbxproj'
    update_deployment_target(project_file)
