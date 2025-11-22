"""Playwright-based computer control (local browser automation)."""

import asyncio
import base64
import logging
from datetime import datetime
from typing import Dict, Optional

from playwright.async_api import async_playwright, Browser, Page, Playwright

from app.computers.base import Computer

logger = logging.getLogger(__name__)


class PlaywrightComputer(Computer):
    """Computer control using Playwright for local browser automation.

    This implementation uses Playwright to control a local browser instance.
    It's simpler than Docker-based solutions and works well for web-based tasks.
    """

    def __init__(self, display_width: int = 1024, display_height: int = 768):
        """Initialize Playwright computer.

        Args:
            display_width: Browser viewport width
            display_height: Browser viewport height
        """
        super().__init__(display_width, display_height)
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.current_url: str = ""

    async def initialize(self) -> Dict[str, any]:
        """Initialize Playwright and launch browser.

        Returns:
            Dictionary with initialization status
        """
        try:
            # Start Playwright
            self.playwright = await async_playwright().start()

            # Launch browser (Chromium by default)
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # Run with visible browser
                args=[
                    f"--window-size={self.display_width},{self.display_height}",
                ],
            )

            # Create browser context
            context = await self.browser.new_context(
                viewport={
                    "width": self.display_width,
                    "height": self.display_height,
                },
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            )

            # Create page
            self.page = await context.new_page()
            self.is_ready = True

            logger.info(
                f"Playwright browser initialized ({self.display_width}x{self.display_height})"
            )

            return {
                "success": True,
                "message": "Playwright browser initialized",
                "display_width": self.display_width,
                "display_height": self.display_height,
            }

        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            self.is_ready = False
            return {
                "success": False,
                "message": f"Initialization failed: {str(e)}",
            }

    async def screenshot(self) -> Dict[str, str]:
        """Take a screenshot of the current page.

        Returns:
            Dictionary with screenshot data
        """
        try:
            if not self.page:
                return {
                    "error": "Browser not initialized",
                    "screenshot": "",
                    "width": 0,
                    "height": 0,
                }

            # Take screenshot
            screenshot_bytes = await self.page.screenshot(full_page=False, type="png")

            # Encode to base64
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

            return {
                "screenshot": screenshot_b64,
                "width": self.display_width,
                "height": self.display_height,
                "timestamp": datetime.utcnow().isoformat(),
                "url": self.page.url if self.page else "",
            }

        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return {
                "error": str(e),
                "screenshot": "",
                "width": 0,
                "height": 0,
            }

    async def click(self, x: int, y: int, button: str = "left") -> Dict[str, str]:
        """Click at specific coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            button: Mouse button

        Returns:
            Dictionary with click status
        """
        try:
            if not self.page:
                return {"success": False, "message": "Browser not initialized"}

            # Map button names
            button_map = {
                "left": "left",
                "right": "right",
                "middle": "middle",
            }

            playwright_button = button_map.get(button.lower(), "left")

            # Perform click
            await self.page.mouse.click(x, y, button=playwright_button)

            # Wait a bit for page updates
            await asyncio.sleep(0.2)

            return {
                "success": True,
                "message": f"Clicked at ({x}, {y}) with {button} button",
            }

        except Exception as e:
            logger.error(f"Error clicking: {e}")
            return {"success": False, "message": str(e)}

    async def double_click(self, x: int, y: int) -> Dict[str, str]:
        """Double-click at specific coordinates.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            Dictionary with double-click status
        """
        try:
            if not self.page:
                return {"success": False, "message": "Browser not initialized"}

            # Perform double-click
            await self.page.mouse.dblclick(x, y)

            # Wait a bit for page updates
            await asyncio.sleep(0.2)

            return {
                "success": True,
                "message": f"Double-clicked at ({x}, {y})",
            }

        except Exception as e:
            logger.error(f"Error double-clicking: {e}")
            return {"success": False, "message": str(e)}

    async def type_text(self, text: str, delay_ms: int = 50) -> Dict[str, str]:
        """Type text at current cursor position.

        Args:
            text: Text to type
            delay_ms: Delay between keystrokes

        Returns:
            Dictionary with typing status
        """
        try:
            if not self.page:
                return {"success": False, "message": "Browser not initialized"}

            # Type text with delay
            await self.page.keyboard.type(text, delay=delay_ms)

            return {
                "success": True,
                "message": f"Typed {len(text)} characters",
            }

        except Exception as e:
            logger.error(f"Error typing text: {e}")
            return {"success": False, "message": str(e)}

    async def press_key(self, key: str) -> Dict[str, str]:
        """Press a keyboard key or combination.

        Args:
            key: Key to press (e.g., "Enter", "Control+c")

        Returns:
            Dictionary with key press status
        """
        try:
            if not self.page:
                return {"success": False, "message": "Browser not initialized"}

            # Handle key combinations
            if "+" in key:
                # Split combination (e.g., "Control+c" -> ["Control", "c"])
                parts = [k.strip() for k in key.split("+")]

                # Press modifiers and final key
                for part in parts[:-1]:
                    await self.page.keyboard.down(part)

                await self.page.keyboard.press(parts[-1])

                for part in reversed(parts[:-1]):
                    await self.page.keyboard.up(part)
            else:
                # Single key
                await self.page.keyboard.press(key)

            return {
                "success": True,
                "message": f"Pressed key: {key}",
            }

        except Exception as e:
            logger.error(f"Error pressing key: {e}")
            return {"success": False, "message": str(e)}

    async def scroll(
        self, x: int, y: int, scroll_x: int = 0, scroll_y: int = -100
    ) -> Dict[str, str]:
        """Scroll the page at specific position.

        Args:
            x: X coordinate
            y: Y coordinate
            scroll_x: Horizontal scroll amount
            scroll_y: Vertical scroll amount

        Returns:
            Dictionary with scroll status
        """
        try:
            if not self.page:
                return {"success": False, "message": "Browser not initialized"}

            # Move mouse to position first
            await self.page.mouse.move(x, y)

            # Scroll using wheel
            await self.page.mouse.wheel(scroll_x, scroll_y)

            # Wait a bit for scroll to complete
            await asyncio.sleep(0.2)

            return {
                "success": True,
                "message": f"Scrolled at ({x}, {y}) by ({scroll_x}, {scroll_y})",
            }

        except Exception as e:
            logger.error(f"Error scrolling: {e}")
            return {"success": False, "message": str(e)}

    async def navigate_to_url(self, url: str) -> Dict[str, str]:
        """Navigate to a URL.

        Args:
            url: URL to navigate to

        Returns:
            Dictionary with navigation status
        """
        try:
            if not self.page:
                return {"success": False, "message": "Browser not initialized", "url": ""}

            # Navigate to URL
            response = await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)

            self.current_url = self.page.url

            # Check if navigation was successful
            if response and response.ok:
                return {
                    "success": True,
                    "message": f"Navigated to {url}",
                    "url": self.current_url,
                    "status": response.status,
                }
            else:
                return {
                    "success": False,
                    "message": f"Navigation failed with status {response.status if response else 'unknown'}",
                    "url": self.current_url,
                }

        except Exception as e:
            logger.error(f"Error navigating to URL: {e}")
            return {"success": False, "message": str(e), "url": ""}

    async def wait(self, milliseconds: int) -> Dict[str, str]:
        """Wait for specified duration.

        Args:
            milliseconds: Duration to wait

        Returns:
            Dictionary with wait status
        """
        try:
            await asyncio.sleep(milliseconds / 1000.0)
            return {
                "success": True,
                "message": f"Waited for {milliseconds}ms",
            }
        except Exception as e:
            logger.error(f"Error waiting: {e}")
            return {"success": False, "message": str(e)}

    async def get_status(self) -> Dict[str, any]:
        """Get current browser status.

        Returns:
            Dictionary with status information
        """
        return {
            "ready": self.is_ready,
            "display_width": self.display_width,
            "display_height": self.display_height,
            "browser_open": self.browser is not None,
            "page_open": self.page is not None,
            "current_url": self.page.url if self.page else "",
            "environment": "playwright",
        }

    async def start_browser(self, start_url: str = "https://www.google.com") -> Dict[str, str]:
        """Start browser and navigate to URL.

        Args:
            start_url: Initial URL

        Returns:
            Dictionary with start status
        """
        # For Playwright, browser is already started, just navigate
        return await self.navigate_to_url(start_url)

    async def cleanup(self) -> Dict[str, str]:
        """Close browser and cleanup resources.

        Returns:
            Dictionary with cleanup status
        """
        try:
            if self.page:
                await self.page.close()
                self.page = None

            if self.browser:
                await self.browser.close()
                self.browser = None

            if self.playwright:
                await self.playwright.stop()
                self.playwright = None

            self.is_ready = False

            return {
                "success": True,
                "message": "Browser closed successfully",
            }

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return {"success": False, "message": str(e)}
