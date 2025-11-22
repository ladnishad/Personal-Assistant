"""Computer control tools for automated browser and desktop tasks."""

import base64
import logging
from typing import Dict, List, Optional

from agents import function_tool

from app.computers.manager import ComputerManager

logger = logging.getLogger(__name__)

# Global computer manager instance
_computer_manager: Optional[ComputerManager] = None


def get_computer_manager() -> ComputerManager:
    """Get or create the global ComputerManager instance."""
    global _computer_manager
    if _computer_manager is None:
        _computer_manager = ComputerManager()
    return _computer_manager


@function_tool
async def take_screenshot() -> Dict[str, str]:
    """Take a screenshot of the current desktop/browser state.

    Returns:
        Dictionary with:
        - screenshot: Base64-encoded PNG image
        - width: Display width in pixels
        - height: Display height in pixels
        - timestamp: When screenshot was taken
    """
    try:
        manager = get_computer_manager()
        result = await manager.screenshot()
        logger.info("Screenshot taken successfully")
        return result
    except Exception as e:
        logger.error(f"Error taking screenshot: {e}")
        return {
            "error": str(e),
            "screenshot": "",
            "width": 0,
            "height": 0,
        }


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
