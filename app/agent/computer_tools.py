"""Computer control tools for automated browser and desktop tasks."""

import base64
import logging
from contextvars import ContextVar
from datetime import datetime
from typing import Dict, List, Optional, Union

from agents import function_tool
from agents.tool import ToolOutputImage

from app.computers.manager import ComputerManager

logger = logging.getLogger(__name__)

# Global computer manager instance
_computer_manager: Optional[ComputerManager] = None

# Context variable for screenshot streaming
_screenshot_stream_enabled: ContextVar[bool] = ContextVar("screenshot_stream_enabled", default=False)
_screenshot_captures: ContextVar[List[Dict]] = ContextVar("screenshot_captures", default=[])


def get_computer_manager() -> ComputerManager:
    """Get or create the global ComputerManager instance."""
    global _computer_manager
    if _computer_manager is None:
        _computer_manager = ComputerManager()
    return _computer_manager


def enable_screenshot_streaming():
    """Enable screenshot streaming for the current context."""
    _screenshot_stream_enabled.set(True)
    _screenshot_captures.set([])


def disable_screenshot_streaming():
    """Disable screenshot streaming for the current context."""
    _screenshot_stream_enabled.set(False)


def get_screenshot_captures() -> List[Dict]:
    """Get all captured screenshots from the current context."""
    try:
        return _screenshot_captures.get()
    except LookupError:
        return []


def clear_screenshot_captures():
    """Clear all captured screenshots."""
    _screenshot_captures.set([])


def _record_screenshot(screenshot_b64: str, width: int, height: int, action_context: Optional[str] = None):
    """Record a screenshot if streaming is enabled."""
    try:
        if _screenshot_stream_enabled.get():
            captures = _screenshot_captures.get()
            captures.append({
                "timestamp": datetime.utcnow().isoformat(),
                "screenshot": screenshot_b64,
                "width": width,
                "height": height,
                "action_context": action_context
            })
            _screenshot_captures.set(captures)
            logger.debug(f"Recorded screenshot #{len(captures)} - {action_context}")
    except LookupError:
        # Context not set, skip recording
        pass


@function_tool
async def take_screenshot(action_context: Optional[str] = None) -> Union[ToolOutputImage, Dict[str, str]]:
    """Take a screenshot of the current desktop/browser state.

    The screenshot is returned as an image that the vision model can analyze
    to make decisions about where to click, what to type, etc.

    Args:
        action_context: Optional description of what action is being performed

    Returns:
        ToolOutputImage with the screenshot for vision model analysis,
        or error dictionary if screenshot fails.
    """
    try:
        manager = get_computer_manager()
        result = await manager.screenshot()

        if "error" in result:
            logger.error(f"Error taking screenshot: {result['error']}")
            return {"error": result["error"], "success": False}

        # Extract base64 screenshot data
        screenshot_b64 = result.get("screenshot", "")
        width = result.get("width", 0)
        height = result.get("height", 0)

        if not screenshot_b64:
            return {"error": "Screenshot data is empty", "success": False}

        # Record screenshot if streaming is enabled
        _record_screenshot(screenshot_b64, width, height, action_context)

        # Return as ToolOutputImage so vision model can analyze it
        logger.info(f"Screenshot taken successfully ({width}x{height})")
        return ToolOutputImage(
            image_url=f"data:image/png;base64,{screenshot_b64}",
            detail="high"  # High detail for accurate coordinate identification
        )
    except Exception as e:
        logger.error(f"Error taking screenshot: {e}")
        return {"error": str(e), "success": False}


@function_tool
async def click(x: int, y: int, button: str = "left") -> Dict[str, str]:
    """Click at specific coordinates on the screen.

    Args:
        x: X coordinate (pixels from left edge)
        y: Y coordinate (pixels from top edge)
        button: Mouse button to use - "left", "right", "middle"

    Returns:
        Dictionary with success status and message
    """
    try:
        manager = get_computer_manager()
        result = await manager.click(x, y, button)
        logger.info(f"Clicked at ({x}, {y}) with {button} button")
        return result
    except Exception as e:
        logger.error(f"Error clicking at ({x}, {y}): {e}")
        return {"success": False, "message": str(e)}


@function_tool
async def double_click(x: int, y: int) -> Dict[str, str]:
    """Double-click at specific coordinates on the screen.

    Args:
        x: X coordinate (pixels from left edge)
        y: Y coordinate (pixels from top edge)

    Returns:
        Dictionary with success status and message
    """
    try:
        manager = get_computer_manager()
        result = await manager.double_click(x, y)
        logger.info(f"Double-clicked at ({x}, {y})")
        return result
    except Exception as e:
        logger.error(f"Error double-clicking at ({x}, {y}): {e}")
        return {"success": False, "message": str(e)}


@function_tool
async def type_text(text: str, delay_ms: int = 50) -> Dict[str, str]:
    """Type text into the currently focused element.

    Args:
        text: Text to type
        delay_ms: Delay between keystrokes in milliseconds (default 50ms)

    Returns:
        Dictionary with success status and message
    """
    try:
        manager = get_computer_manager()
        result = await manager.type_text(text, delay_ms)
        logger.info(f"Typed text: {text[:50]}...")
        return result
    except Exception as e:
        logger.error(f"Error typing text: {e}")
        return {"success": False, "message": str(e)}


@function_tool
async def press_key(key: str) -> Dict[str, str]:
    """Press a keyboard key or key combination.

    Args:
        key: Key to press. Examples:
            - Single keys: "Enter", "Tab", "Escape", "Backspace", "Delete"
            - Combinations: "Control+c", "Control+v", "Alt+Tab"
            - Function keys: "F1", "F2", etc.

    Returns:
        Dictionary with success status and message
    """
    try:
        manager = get_computer_manager()
        result = await manager.press_key(key)
        logger.info(f"Pressed key: {key}")
        return result
    except Exception as e:
        logger.error(f"Error pressing key {key}: {e}")
        return {"success": False, "message": str(e)}


@function_tool
async def scroll(x: int, y: int, scroll_x: int = 0, scroll_y: int = -100) -> Dict[str, str]:
    """Scroll the page at a specific position.

    Args:
        x: X coordinate where to scroll
        y: Y coordinate where to scroll
        scroll_x: Horizontal scroll amount (positive = right, negative = left)
        scroll_y: Vertical scroll amount (positive = down, negative = up)
                  Default is -100 (scroll up)

    Returns:
        Dictionary with success status and message
    """
    try:
        manager = get_computer_manager()
        result = await manager.scroll(x, y, scroll_x, scroll_y)
        logger.info(f"Scrolled at ({x}, {y}) by ({scroll_x}, {scroll_y})")
        return result
    except Exception as e:
        logger.error(f"Error scrolling: {e}")
        return {"success": False, "message": str(e)}


@function_tool
async def navigate_to_url(url: str) -> Dict[str, str]:
    """Navigate the browser to a specific URL.

    Args:
        url: Full URL to navigate to (e.g., "https://www.example.com")

    Returns:
        Dictionary with success status, message, and final URL
    """
    try:
        manager = get_computer_manager()
        result = await manager.navigate_to_url(url)
        logger.info(f"Navigated to URL: {url}")
        return result
    except Exception as e:
        logger.error(f"Error navigating to {url}: {e}")
        return {"success": False, "message": str(e), "url": ""}


@function_tool
async def wait(milliseconds: int) -> Dict[str, str]:
    """Wait for a specified duration.

    Args:
        milliseconds: How long to wait in milliseconds

    Returns:
        Dictionary with success status and message
    """
    try:
        manager = get_computer_manager()
        result = await manager.wait(milliseconds)
        logger.info(f"Waited for {milliseconds}ms")
        return result
    except Exception as e:
        logger.error(f"Error waiting: {e}")
        return {"success": False, "message": str(e)}


@function_tool
async def get_computer_status() -> Dict[str, any]:
    """Get the current status of the computer environment.

    Returns:
        Dictionary with:
        - ready: Whether the computer is ready for commands
        - display_width: Current display width
        - display_height: Current display height
        - browser_open: Whether browser is active
        - current_url: Current browser URL (if applicable)
    """
    try:
        manager = get_computer_manager()
        result = await manager.get_status()
        logger.info("Retrieved computer status")
        return result
    except Exception as e:
        logger.error(f"Error getting computer status: {e}")
        return {
            "ready": False,
            "error": str(e),
        }


@function_tool
async def start_browser(start_url: str = "https://www.google.com") -> Dict[str, str]:
    """Start the browser and navigate to a URL.

    Args:
        start_url: Initial URL to load (default: Google)

    Returns:
        Dictionary with success status and message
    """
    try:
        manager = get_computer_manager()
        result = await manager.start_browser(start_url)
        logger.info(f"Started browser with URL: {start_url}")
        return result
    except Exception as e:
        logger.error(f"Error starting browser: {e}")
        return {"success": False, "message": str(e)}


# List of all computer control tools
COMPUTER_TOOLS = [
    take_screenshot,
    click,
    double_click,
    type_text,
    press_key,
    scroll,
    navigate_to_url,
    wait,
    get_computer_status,
    start_browser,
]
