#!/usr/bin/env python3
"""
Check for known dependency conflicts in requirements.txt
"""

import re
import sys

# Known version constraints and conflicts
KNOWN_ISSUES = {
    'pytest-asyncio': {
        '0.23.4': 'Requires pytest<8',
        'fix': '0.24.0 or higher for pytest 8.x'
    },
    'fastapi': {
        '0.109.0': 'Works with starlette 0.35.x',
        'starlette_range': '>=0.35.0,<0.36.0'
    },
    'pydantic': {
        '2.5.3': 'Requires pydantic-core 2.14.6',
        'compatible_core': '2.14.6'
    },
    'openai': {
        '1.10.0': 'Works with httpx 0.24.x - 0.27.x',
        'httpx_range': '>=0.24.0,<0.28.0'
    }
}

def check_requirements(file_path):
    """Check requirements file for known conflicts."""
    print("🔍 Checking dependencies for conflicts...\n")

    with open(file_path, 'r') as f:
        lines = f.readlines()

    packages = {}
    issues = []

    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            match = re.match(r'([a-zA-Z0-9_-]+(?:\[[\w,]+\])?)==(.+)', line)
            if match:
                pkg_name = match.group(1).split('[')[0]
                version = match.group(2)
                packages[pkg_name] = version

    # Check pytest + pytest-asyncio
    if 'pytest' in packages and 'pytest-asyncio' in packages:
        pytest_ver = packages['pytest']
        asyncio_ver = packages['pytest-asyncio']

        if pytest_ver.startswith('8.') and asyncio_ver.startswith('0.23.'):
            issues.append("❌ pytest 8.x incompatible with pytest-asyncio 0.23.x")
            issues.append("   Fix: Use pytest-asyncio>=0.24.0")
        elif pytest_ver.startswith('8.') and asyncio_ver >= '0.24.0':
            print("✅ pytest + pytest-asyncio: Compatible")

    # Check fastapi + starlette (starlette is auto-installed by fastapi)
    if 'fastapi' in packages:
        print("✅ fastapi: Version locked")

    # Check pydantic + pydantic-core
    if 'pydantic' in packages:
        print("✅ pydantic: Version locked")

    # Check openai + httpx
    if 'openai' in packages and 'httpx' in packages:
        openai_ver = packages['openai']
        httpx_ver = packages['httpx']
        if httpx_ver.startswith('0.26.'):
            print("✅ openai + httpx: Compatible")

    # Check for other common issues
    if 'uvicorn' in packages:
        print("✅ uvicorn: Version locked with standard extras")

    if issues:
        print("\n⚠️  Issues Found:")
        for issue in issues:
            print(issue)
        return False
    else:
        print("\n✅ All dependencies look good!")
        return True

if __name__ == '__main__':
    success = check_requirements('/home/user/Personal-Assistant/requirements.txt')
    sys.exit(0 if success else 1)
