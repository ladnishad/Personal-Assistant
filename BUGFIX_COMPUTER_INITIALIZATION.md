# Computer Control Initialization Bug Fix

## Problem

When users requested browser automation tasks, the agent would respond with:
> "The browser environment wasn't fully initialized for it to start browsing."

## Root Cause

In `app/computers/manager.py`, the `get_status()` method was **not** calling `_ensure_initialized()` before checking the status.

**Buggy Code:**
```python
async def get_status(self) -> Dict[str, any]:
    """Get environment status."""
    if not self._initialized:  # ❌ Returns False without trying to initialize!
        return {
            "ready": False,
            "message": "Computer environment not initialized",
        }
    return await self.computer.get_status()
```

**What Happened:**
1. Agent receives browser task → calls `get_computer_status()` to check readiness
2. `get_status()` checks `_initialized` flag (False on first call)
3. Returns `{"ready": False, "message": "Computer environment not initialized"}`
4. Agent sees "not ready" and gives up without even trying to initialize

## The Fix

Changed `get_status()` to call `_ensure_initialized()` like all other methods:

```python
async def get_status(self) -> Dict[str, any]:
    """Get environment status."""
    await self._ensure_initialized()  # ✅ Now initializes on-demand!
    return await self.computer.get_status()
```

## Verification

All other methods in `ComputerManager` correctly call `_ensure_initialized()`:
- ✅ `screenshot()` - calls `_ensure_initialized()`
- ✅ `click()` - calls `_ensure_initialized()`
- ✅ `double_click()` - calls `_ensure_initialized()`
- ✅ `type_text()` - calls `_ensure_initialized()`
- ✅ `press_key()` - calls `_ensure_initialized()`
- ✅ `scroll()` - calls `_ensure_initialized()`
- ✅ `navigate_to_url()` - calls `_ensure_initialized()`
- ✅ `wait()` - calls `_ensure_initialized()`
- ✅ `start_browser()` - calls `_ensure_initialized()`
- ✅ **`get_status()` - NOW calls `_ensure_initialized()`** (FIXED)

## Impact

**Before Fix:**
- Browser tasks would fail with "not initialized" error
- Agent couldn't browse websites, check prices, book reservations, etc.
- Users had to manually trigger initialization somehow

**After Fix:**
- Browser initializes automatically on first use
- Agent can immediately start browsing when asked
- All computer control features work as expected

## Technical Details

The `_ensure_initialized()` method:
1. Checks if `_initialized` flag is True
2. If False, calls `initialize()` which:
   - Creates the appropriate Computer instance (Playwright or Docker)
   - Launches the browser/environment
   - Sets `_initialized = True`
3. If already initialized, does nothing (no duplicate initialization)

This lazy initialization pattern ensures the browser only starts when needed, but starts automatically on first use.

## Test Case

```python
from app.computers.manager import ComputerManager

manager = ComputerManager(environment="playwright")

# First call - should auto-initialize
status = await manager.get_status()

assert manager._initialized == True
assert status["ready"] == True
assert status["environment"] == "playwright"
assert status["browser_open"] == True

# Second call - should reuse existing browser
status2 = await manager.get_status()
assert status2["ready"] == True  # Still ready, same instance
```

## Files Changed

- `app/computers/manager.py` - Fixed `get_status()` method

## Related

This fix ensures consistency across all ComputerManager methods and enables proper lazy initialization for computer control tasks.
