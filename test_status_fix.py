"""Test that get_computer_status properly initializes the computer."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.computers.manager import ComputerManager


async def test_status_initialization():
    """Test that calling get_status initializes the computer automatically."""
    print("🧪 Testing computer status initialization fix...")

    # Create a fresh manager (not initialized)
    manager = ComputerManager(environment="playwright")

    print(f"   Initial state - _initialized: {manager._initialized}")
    assert manager._initialized == False, "Manager should start uninitialized"

    # Call get_status - this should auto-initialize
    print("   Calling get_status() - should auto-initialize...")
    status = await manager.get_status()

    print(f"   Status result: {status}")
    print(f"   Manager state - _initialized: {manager._initialized}")

    # Verify initialization happened
    assert manager._initialized == True, "Manager should be initialized after get_status()"
    assert status.get("ready") == True, "Status should show ready=True"
    assert status.get("environment") == "playwright", "Should be using playwright"
    assert "browser_open" in status, "Status should include browser_open field"

    # Cleanup
    print("   Cleaning up...")
    await manager.cleanup()

    print("✅ Test passed! get_status() now properly initializes the computer.\n")
    return True


async def test_multiple_status_calls():
    """Test that multiple status calls don't re-initialize."""
    print("🧪 Testing multiple status calls...")

    manager = ComputerManager(environment="playwright")

    # First call - should initialize
    print("   First get_status() call...")
    status1 = await manager.get_status()
    assert manager._initialized == True
    computer_instance1 = manager.computer

    # Second call - should reuse existing
    print("   Second get_status() call...")
    status2 = await manager.get_status()
    assert manager._initialized == True
    computer_instance2 = manager.computer

    # Should be same instance (not re-initialized)
    assert computer_instance1 is computer_instance2, "Should reuse same computer instance"

    # Cleanup
    await manager.cleanup()

    print("✅ Test passed! Multiple calls don't re-initialize.\n")
    return True


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("COMPUTER STATUS INITIALIZATION FIX - TEST SUITE")
    print("="*60 + "\n")

    try:
        await test_status_initialization()
        await test_multiple_status_calls()

        print("="*60)
        print("🎉 ALL TESTS PASSED!")
        print("="*60 + "\n")
        print("The browser environment will now initialize automatically when")
        print("the agent calls get_computer_status() for the first time.")
        print("\nNo more 'browser environment wasn't fully initialized' errors!")
        return 0

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
