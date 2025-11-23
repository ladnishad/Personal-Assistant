#!/usr/bin/env python3
"""Test the Computer Control agent integration."""

import asyncio
import json

from app.agent.service import AgentService
from app.auth.models import User
from app.computers.playwright_computer import PlaywrightComputer


async def test_computer_initialization():
    """Test if the computer control can initialize properly."""
    print("Testing Computer Control initialization...")

    computer = PlaywrightComputer(display_width=1920, display_height=1080)

    result = await computer.initialize()
    print(f"Initialization result: {json.dumps(result, indent=2)}")

    if result.get("success"):
        print("✓ Computer Control initialized successfully")

        # Test taking a screenshot
        print("\nTaking a test screenshot...")
        screenshot = await computer.screenshot()
        if screenshot.get("screenshot"):
            print(f"✓ Screenshot taken ({screenshot.get('width')}x{screenshot.get('height')})")
        else:
            print(f"✗ Screenshot failed: {screenshot.get('error')}")

        # Test navigation
        print("\nTesting navigation to Google...")
        nav_result = await computer.navigate_to_url("https://www.google.com")
        if nav_result.get("success"):
            print(f"✓ Navigated to: {nav_result.get('url')}")
        else:
            print(f"✗ Navigation failed: {nav_result.get('message')}")

        # Cleanup
        await computer.cleanup()
        print("✓ Cleanup completed")

        return True
    else:
        print(f"✗ Initialization failed: {result.get('message')}")
        return False


async def test_agent_routing():
    """Test if agent properly routes to Computer Control for price queries."""
    print("\n\nTesting Agent Routing to Computer Control...")

    # Create a test user
    test_user = User(
        id="test_user_123",
        email="test@example.com",
        first_name="Test",
        last_name="User"
    )

    # Test messages that should trigger Computer Control
    test_messages = [
        "Check the price of Sony WH-1000XM5 headphones",
        "What's the current price of iPhone 15 Pro?",
        "Is the Nintendo Switch OLED in stock anywhere?",
        "Compare prices for MacBook Air across different stores",
    ]

    for message in test_messages:
        print(f"\nTest message: \"{message}\"")
        try:
            # Set up user context for the agent
            from app.agent.computer_tools import user_context_var
            token = user_context_var.set(test_user)

            # Call the agent service
            result = await AgentService.chat(
                user=test_user,
                message=message,
                use_memory=False,
                conversation_id=f"test_conv_{message[:10]}",
                task_id=None,
                conversation_history=None,
                stream_screenshots=False,
            )

            # Check if Computer Control was invoked
            if "computer" in result.get("message", "").lower() or "browser" in result.get("message", "").lower():
                print("✓ Agent recognized this as a Computer Control task")
            else:
                print("? Agent response:", result.get("message", "")[:200])

            # Clean up context
            user_context_var.reset(token)

        except Exception as e:
            print(f"✗ Error: {e}")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("COMPUTER CONTROL AGENT TEST SUITE")
    print("=" * 60)

    # Test 1: Basic initialization
    init_success = await test_computer_initialization()

    if init_success:
        # Test 2: Agent routing
        await test_agent_routing()

    print("\n" + "=" * 60)
    print("TEST SUITE COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())