#!/bin/bash

echo "🔍 Deep Dependency Analysis"
echo "============================"
echo ""

# Create a temporary virtual environment to test dependencies
echo "📦 Creating test environment..."
python3 -m venv /tmp/test_venv
source /tmp/test_venv/bin/activate

echo ""
echo "📥 Testing dependency resolution..."
echo ""

# Try to install and check for conflicts
pip install --dry-run -r requirements.txt 2>&1 | tee /tmp/pip_output.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All dependencies resolve successfully!"
    echo ""

    # Show summary
    echo "📊 Dependency Summary:"
    echo "--------------------"
    grep -E "^(fastapi|uvicorn|pydantic|pytest|openai|httpx|beanie|motor)==" requirements.txt | while read line; do
        echo "  ✓ $line"
    done
else
    echo ""
    echo "❌ Dependency resolution failed!"
    echo ""
    echo "Errors found:"
    grep -i "error\|conflict" /tmp/pip_output.txt
fi

# Cleanup
deactivate
rm -rf /tmp/test_venv /tmp/pip_output.txt

echo ""
echo "Analysis complete."
