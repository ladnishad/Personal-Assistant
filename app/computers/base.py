"""Base class for computer environments."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class Computer(ABC):
    """Abstract base class for computer control environments.

    This defines the interface that all computer implementations must follow.
    Implementations can be local (Playwright), Docker-based, or remote services.
    """

    def __init__(self, display_width: int = 1024, display_height: int = 768):
        """Initialize the computer environment.

        Args:
            display_width: Display width in pixels
            display_height: Display height in pixels
        """
        self.display_width = display_width
        self.display_height = display_height
        self.is_ready = False

    @abstractmethod
    async def initialize(self) -> Dict[str, Any]:
        """Initialize the computer environment.

        Returns:
            Dictionary with initialization status and details
        """
        pass

    @abstractmethod
    async def screenshot(self) -> Dict[str, str]:
        """Take a screenshot of the current state.

        Returns:
            Dictionary with:
            - screenshot: Base64-encoded PNG image
            - width: Display width
            - height: Display height
            - timestamp: ISO timestamp
        """
        pass

    @abstractmethod
    async def click(self, x: int, y: int, button: str = "left") -> Dict[str, str]:
        """Click at specific coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            button: Mouse button ("left", "right", "middle")

        Returns:
            Dictionary with success status and message
        """
        pass

    @abstractmethod
    async def double_click(self, x: int, y: int) -> Dict[str, str]:
        """Double-click at specific coordinates.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            Dictionary with success status and message
        """
        pass

    @abstractmethod
    async def type_text(self, text: str, delay_ms: int = 50) -> Dict[str, str]:
        """Type text at current cursor position.

        Args:
            text: Text to type
            delay_ms: Delay between keystrokes

        Returns:
            Dictionary with success status and message
        """
        pass

    @abstractmethod
    async def press_key(self, key: str) -> Dict[str, str]:
        """Press a keyboard key or combination.

        Args:
            key: Key name or combination (e.g., "Enter", "Control+c")

        Returns:
            Dictionary with success status and message
        """
        pass

    @abstractmethod
    async def scroll(
        self, x: int, y: int, scroll_x: int = 0, scroll_y: int = -100
    ) -> Dict[str, str]:
        """Scroll at specific position.

        Args:
            x: X coordinate
            y: Y coordinate
            scroll_x: Horizontal scroll amount
            scroll_y: Vertical scroll amount

        Returns:
            Dictionary with success status and message
        """
        pass

    @abstractmethod
    async def navigate_to_url(self, url: str) -> Dict[str, str]:
        """Navigate to a URL (for browser-based environments).

        Args:
            url: URL to navigate to

        Returns:
            Dictionary with success status and final URL
        """
        pass

    @abstractmethod
    async def wait(self, milliseconds: int) -> Dict[str, str]:
        """Wait for specified duration.

        Args:
            milliseconds: Duration to wait

        Returns:
            Dictionary with success status
        """
        pass

    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Get current environment status.

        Returns:
            Dictionary with status information
        """
        pass

    @abstractmethod
    async def cleanup(self) -> Dict[str, str]:
        """Clean up and close the environment.

        Returns:
            Dictionary with cleanup status
        """
        pass
