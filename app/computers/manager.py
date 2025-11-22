"""Computer Manager for handling different computer environments."""

import logging
from typing import Dict, Optional

from app.computers.base import Computer
from app.config import settings

logger = logging.getLogger(__name__)


class ComputerManager:
    """Manager for computer control environments.

    Handles initialization, selection, and lifecycle of computer environments.
    Supports multiple backends: Playwright (local browser), Docker (VM), Remote services.
    """

    def __init__(
        self,
        environment: Optional[str] = None,
        display_width: int = 1024,
        display_height: int = 768,
    ):
        """Initialize the computer manager.

        Args:
            environment: Which environment to use ("playwright", "docker", "remote")
                        If None, uses config setting
            display_width: Display width in pixels
            display_height: Display height in pixels
        """
        self.environment = environment or getattr(
            settings, "computer_environment", "playwright"
        )
        self.display_width = display_width
        self.display_height = display_height
        self.computer: Optional[Computer] = None
        self._initialized = False

    async def _ensure_initialized(self):
        """Ensure the computer environment is initialized."""
        if not self._initialized:
            await self.initialize()

    async def initialize(self) -> Dict[str, any]:
        """Initialize the computer environment.

        Returns:
            Dictionary with initialization status
        """
        try:
            if self.environment == "playwright":
                from app.computers.playwright_computer import PlaywrightComputer

                self.computer = PlaywrightComputer(self.display_width, self.display_height)
            elif self.environment == "docker":
                from app.computers.docker_computer import DockerComputer

                self.computer = DockerComputer(self.display_width, self.display_height)
            else:
                raise ValueError(f"Unknown computer environment: {self.environment}")

            result = await self.computer.initialize()
            self._initialized = result.get("success", False)
            logger.info(
                f"Computer environment '{self.environment}' initialized: {self._initialized}"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to initialize computer environment: {e}")
            return {
                "success": False,
                "message": f"Initialization failed: {str(e)}",
            }

    async def screenshot(self) -> Dict[str, str]:
        """Take a screenshot."""
        await self._ensure_initialized()
        return await self.computer.screenshot()

    async def click(self, x: int, y: int, button: str = "left") -> Dict[str, str]:
        """Click at coordinates."""
        await self._ensure_initialized()
        return await self.computer.click(x, y, button)

    async def double_click(self, x: int, y: int) -> Dict[str, str]:
        """Double-click at coordinates."""
        await self._ensure_initialized()
        return await self.computer.double_click(x, y)

    async def type_text(self, text: str, delay_ms: int = 50) -> Dict[str, str]:
        """Type text."""
        await self._ensure_initialized()
        return await self.computer.type_text(text, delay_ms)

    async def press_key(self, key: str) -> Dict[str, str]:
        """Press a key."""
        await self._ensure_initialized()
        return await self.computer.press_key(key)

    async def scroll(
        self, x: int, y: int, scroll_x: int = 0, scroll_y: int = -100
    ) -> Dict[str, str]:
        """Scroll at position."""
        await self._ensure_initialized()
        return await self.computer.scroll(x, y, scroll_x, scroll_y)

    async def navigate_to_url(self, url: str) -> Dict[str, str]:
        """Navigate to URL."""
        await self._ensure_initialized()
        return await self.computer.navigate_to_url(url)

    async def wait(self, milliseconds: int) -> Dict[str, str]:
        """Wait for duration."""
        await self._ensure_initialized()
        return await self.computer.wait(milliseconds)

    async def get_status(self) -> Dict[str, any]:
        """Get environment status."""
        if not self._initialized:
            return {
                "ready": False,
                "message": "Computer environment not initialized",
            }
        return await self.computer.get_status()

    async def start_browser(self, start_url: str = "https://www.google.com") -> Dict[str, str]:
        """Start browser and navigate to URL."""
        await self._ensure_initialized()
        # For browser-based environments, navigate to URL
        if hasattr(self.computer, "start_browser"):
            return await self.computer.start_browser(start_url)
        else:
            # Fallback to navigate
            return await self.computer.navigate_to_url(start_url)

    async def cleanup(self) -> Dict[str, str]:
        """Clean up the computer environment."""
        if self.computer:
            result = await self.computer.cleanup()
            self._initialized = False
            return result
        return {"success": True, "message": "Nothing to clean up"}
