"""Computer control tools for automated browser and desktop tasks."""

import base64
import logging
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from agents import function_tool
from agents.tool import ToolOutputImage

from app.computers.manager import ComputerManager

logger = logging.getLogger(__name__)

# Global computer manager instance
_computer_manager: Optional[ComputerManager] = None

# Context variables for user and conversation tracking
_current_user_id: ContextVar[Optional[str]] = ContextVar("current_user_id", default=None)
_current_conversation_id: ContextVar[Optional[str]] = ContextVar("current_conversation_id", default=None)

# Context variable for screenshot streaming
_screenshot_stream_enabled: ContextVar[bool] = ContextVar("screenshot_stream_enabled", default=False)
_screenshot_captures: ContextVar[Optional[List[Dict]]] = ContextVar("screenshot_captures", default=None)


def get_computer_manager() -> ComputerManager:
    """Get or create the global ComputerManager instance."""
    global _computer_manager
    if _computer_manager is None:
        _computer_manager = ComputerManager()
    return _computer_manager


def set_user_context(user_id: str, conversation_id: Optional[str] = None):
    """Set user and conversation context for computer control operations."""
    _current_user_id.set(user_id)
    if conversation_id:
        _current_conversation_id.set(conversation_id)


def get_user_id() -> Optional[str]:
    """Get current user ID from context."""
    try:
        return _current_user_id.get()
    except LookupError:
        return None


def get_conversation_id() -> Optional[str]:
    """Get current conversation ID from context."""
    try:
        return _current_conversation_id.get()
    except LookupError:
        return None


def enable_screenshot_streaming():
    """Enable screenshot streaming for the current context."""
    _screenshot_stream_enabled.set(True)
    _screenshot_captures.set([])  # Set to new empty list for this context


def disable_screenshot_streaming():
    """Disable screenshot streaming for the current context."""
    _screenshot_stream_enabled.set(False)


def get_screenshot_captures() -> List[Dict]:
    """Get all captured screenshots from the current context."""
    try:
        captures = _screenshot_captures.get()
        return captures if captures is not None else []
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
            # Initialize if None (first screenshot in this context)
            if captures is None:
                captures = []

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
async def click(x: int, y: int, button: str = "left", action_context: Optional[str] = None) -> Dict[str, str]:
    """Click at specific coordinates on the screen.

    Args:
        x: X coordinate (pixels from left edge)
        y: Y coordinate (pixels from top edge)
        button: Mouse button to use - "left", "right", "middle"
        action_context: Optional description of what you're clicking (e.g., "Submit button", "Search icon")

    Returns:
        Dictionary with success status and message
    """
    try:
        manager = get_computer_manager()
        result = await manager.click(x, y, button)

        # Record action for user visibility
        context_msg = f"Clicking at ({x}, {y})"
        if action_context:
            context_msg += f": {action_context}"
        logger.info(context_msg)

        # Take screenshot after click for visibility
        screenshot_result = await manager.screenshot()
        if "screenshot" in screenshot_result:
            _record_screenshot(
                screenshot_result["screenshot"],
                screenshot_result.get("width", 0),
                screenshot_result.get("height", 0),
                context_msg
            )

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
async def type_text(text: str, delay_ms: int = 50, field_name: Optional[str] = None) -> Dict[str, str]:
    """Type text into the currently focused element.

    Args:
        text: Text to type
        delay_ms: Delay between keystrokes in milliseconds (default 50ms)
        field_name: Optional description of the field being filled (e.g., "Email address", "Password")

    Returns:
        Dictionary with success status and message
    """
    try:
        manager = get_computer_manager()
        result = await manager.type_text(text, delay_ms)

        # Record action for user visibility
        # Mask sensitive data (passwords, credit cards, etc.) in context
        is_sensitive = field_name and any(
            keyword in field_name.lower()
            for keyword in ["password", "credit", "card", "cvv", "ssn", "pin"]
        )

        display_text = "[hidden]" if is_sensitive else text[:30] + ("..." if len(text) > 30 else "")
        context_msg = f"Typing: {display_text}"
        if field_name:
            context_msg = f"Typing into {field_name}: {display_text}"

        logger.info(context_msg)

        # Take screenshot after typing (helps show progress)
        screenshot_result = await manager.screenshot()
        if "screenshot" in screenshot_result:
            _record_screenshot(
                screenshot_result["screenshot"],
                screenshot_result.get("width", 0),
                screenshot_result.get("height", 0),
                context_msg
            )

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
async def navigate_to_url(url: str, purpose: Optional[str] = None) -> Dict[str, str]:
    """Navigate the browser to a specific URL.

    Args:
        url: Full URL to navigate to (e.g., "https://www.example.com")
        purpose: Optional description of why navigating here (e.g., "Opening restaurant booking page")

    Returns:
        Dictionary with success status, message, and final URL
    """
    try:
        manager = get_computer_manager()
        result = await manager.navigate_to_url(url)

        # Record action for user visibility
        context_msg = f"Navigating to {url}"
        if purpose:
            context_msg = f"Navigating to {url}: {purpose}"
        logger.info(context_msg)

        # Take screenshot after navigation
        screenshot_result = await manager.screenshot()
        if "screenshot" in screenshot_result:
            _record_screenshot(
                screenshot_result["screenshot"],
                screenshot_result.get("width", 0),
                screenshot_result.get("height", 0),
                context_msg
            )

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
async def get_computer_status() -> Dict[str, Any]:
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


@function_tool
async def request_user_confirmation(
    action_description: str,
    risk_level: str = "medium"
) -> Dict[str, Any]:
    """Request user confirmation before executing a potentially risky action.

    **CRITICAL: You MUST call this function before executing ANY of these actions:**
    - Submitting forms with financial information (payment details, billing info)
    - Making purchases, bookings, or reservations
    - Sending emails, messages, or any communication
    - Deleting data, accounts, or content
    - Submitting reviews or public posts
    - Making changes to user profiles or settings
    - Any action that is irreversible or has real-world consequences

    **When to use each risk level:**
    - "low": Minor actions with easily reversible consequences (e.g., navigating to a page, reading data)
    - "medium": Actions with some impact but reversible (e.g., filling a form without submitting)
    - "high": Significant actions with consequences (e.g., submitting a reservation, sending a message)
    - "critical": Actions with major financial or irreversible impact (e.g., making a payment, deleting an account)

    **Important workflow:**
    1. First, navigate and fill out all necessary information
    2. Take a screenshot showing what will be submitted
    3. Call this function with a clear description of what you're about to do
    4. If approved, proceed with the action
    5. If denied, explain to the user that the action was cancelled

    Args:
        action_description: Clear, specific description of the action you're about to perform.
                          Include relevant details like amounts, recipients, etc.
                          Example: "Submit restaurant reservation for 2 people at 7pm on Jan 15"
        risk_level: Risk level - "low", "medium", "high", or "critical" (default: "medium")

    Returns:
        Dictionary with:
        - confirmed: Whether the user approved the action
        - user_note: Optional note from the user about their decision
        - message: Status message

    Example:
        User: "Book a table at Restaurant X for 2 people tomorrow at 7pm"
        Agent: 1. Navigate to restaurant website
               2. Fill out reservation form
               3. Take screenshot
               4. request_user_confirmation(
                    action_description="Submit reservation for 2 people at Restaurant X on Jan 15 at 7:00 PM",
                    risk_level="high"
                  )
               5. If confirmed, click submit button
               6. Confirm success to user
    """
    try:
        # Import here to avoid circular dependency
        from app.confirmations.models import RiskLevel
        from app.confirmations.service import ConfirmationService

        user_id = get_user_id()
        conversation_id = get_conversation_id()

        if not user_id:
            return {
                "confirmed": False,
                "message": "User context not available. Cannot request confirmation.",
                "error": True
            }

        # Map risk level string to enum
        risk_level_map = {
            "low": RiskLevel.LOW,
            "medium": RiskLevel.MEDIUM,
            "high": RiskLevel.HIGH,
            "critical": RiskLevel.CRITICAL,
        }
        risk = risk_level_map.get(risk_level.lower(), RiskLevel.MEDIUM)

        # Create confirmation request
        confirmation_id = await ConfirmationService.create_confirmation(
            user_id=user_id,
            action_description=action_description,
            risk_level=risk,
            timeout_seconds=300,  # 5 minutes
            conversation_id=conversation_id,
        )

        logger.info(f"Created confirmation {confirmation_id} for action: {action_description}")

        # Wait for user response with user validation
        result = await ConfirmationService.wait_for_response(
            confirmation_id,
            poll_interval=1.0,
            user_id=user_id
        )

        if result.approved:
            logger.info(f"Confirmation {confirmation_id} approved by user")
            return {
                "confirmed": True,
                "user_note": result.user_note,
                "message": "User approved the action. You may proceed."
            }
        else:
            logger.info(f"Confirmation {confirmation_id} denied by user: {result.status}")
            return {
                "confirmed": False,
                "user_note": result.user_note,
                "message": f"User {'denied' if result.status.value == 'denied' else 'did not respond to'} the confirmation request. Do NOT proceed with the action."
            }

    except Exception as e:
        logger.error(f"Error requesting user confirmation: {e}")
        return {
            "confirmed": False,
            "message": f"Failed to request confirmation: {str(e)}",
            "error": True
        }


@function_tool
async def get_page_html() -> Dict[str, Any]:
    """Get the full HTML content and structure of the current page.

    This provides the complete DOM (Document Object Model) of the page, which is useful when:
    - You need to locate specific elements by ID, class, or other attributes
    - Visual screenshots don't provide enough detail for element selection
    - You need to extract structured text content accurately
    - You want to analyze the page structure semantically

    Use this as a complement to screenshots - the DOM provides structure while
    screenshots provide visual context. Together they give complete page understanding.

    Returns:
        Dictionary containing:
        - success: Whether HTML was retrieved successfully
        - html: The complete HTML content (if successful)
        - url: Current page URL
        - title: Page title
        - character_count: Length of HTML content
        - message: Error message if failed

    Note: This tool only works with Playwright environment. It will return an error
    if used with Docker environment.
    """
    try:
        manager = get_computer_manager()

        # Check if we're using Playwright (which has direct page access)
        from app.computers.playwright_computer import PlaywrightComputer

        if isinstance(manager.computer, PlaywrightComputer):
            page = manager.computer.page

            if not page:
                return {
                    "success": False,
                    "message": "Browser page not initialized. Call start_browser first."
                }

            # Get HTML content
            html_content = await page.content()
            url = page.url
            title = await page.title()

            logger.info(f"Retrieved HTML content from {url} ({len(html_content)} characters)")

            return {
                "success": True,
                "html": html_content,
                "url": url,
                "title": title,
                "character_count": len(html_content)
            }
        else:
            return {
                "success": False,
                "message": "HTML access only available with Playwright environment. "
                          "Currently using: " + manager.environment
            }

    except Exception as e:
        logger.error(f"Error getting page HTML: {e}")
        return {
            "success": False,
            "message": f"Failed to retrieve HTML: {str(e)}"
        }


# List of all computer control tools
COMPUTER_TOOLS = [
    take_screenshot,
    get_page_html,  # DOM access for semantic element selection
    request_user_confirmation,  # Safety confirmation system
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
