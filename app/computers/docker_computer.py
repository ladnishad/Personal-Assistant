"""Docker-based computer control (Ubuntu desktop VM with VNC)."""

import asyncio
import base64
import io
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import docker
from PIL import Image

from app.computers.base import Computer

logger = logging.getLogger(__name__)


class DockerComputer(Computer):
    """Computer control using Docker container with Ubuntu desktop.

    This implementation runs a full Ubuntu desktop environment in Docker
    with VNC server for display and remote control capabilities.
    """

    def __init__(self, display_width: int = 1024, display_height: int = 768):
        """Initialize Docker computer.

        Args:
            display_width: Desktop width
            display_height: Desktop height
        """
        super().__init__(display_width, display_height)
        self.client: Optional[docker.DockerClient] = None
        self.container: Optional[docker.models.containers.Container] = None
        self.container_name = "lifeos-computer"  # Match docker-compose container name
        self.vnc_password = "lifeos123"  # Default VNC password
        self.display_number = "99"  # Virtual display number

    async def initialize(self) -> Dict[str, Any]:
        """Initialize Docker container with Ubuntu desktop.

        Returns:
            Dictionary with initialization status
        """
        try:
            # Connect to Docker
            self.client = docker.from_env()

            # Check if container already exists (container reuse for faster startup)
            container_reused = False
            try:
                self.container = self.client.containers.get(self.container_name)

                # Container exists - check its status
                if self.container.status == "running":
                    logger.info(f"Reusing running container: {self.container_name}")
                    container_reused = True
                elif self.container.status == "exited":
                    logger.info(f"Restarting stopped container: {self.container_name}")
                    self.container.start()
                    # Wait longer for services to restart
                    await asyncio.sleep(5)

                    # Verify container is functional after restart
                    try:
                        exit_code, output = await self._exec_command("echo 'health_check'")
                        if exit_code != 0:
                            raise RuntimeError("Container not responding after restart")
                        logger.info("Container health check passed after restart")
                        container_reused = True
                    except Exception as e:
                        logger.error(f"Container restart failed health check: {e}")
                        logger.info("Removing non-functional container and will recreate")
                        self.container.remove(force=True)
                        self.container = None  # Force recreation below
                else:
                    # Container in unexpected state, remove and recreate
                    logger.warning(f"Container in {self.container.status} state, recreating")
                    self.container.remove(force=True)
                    self.container = None  # Will be created below

            except docker.errors.NotFound:
                pass  # Container doesn't exist, will create below

            # Create container if it doesn't exist or was removed
            if self.container is None:
                logger.info(f"Creating new container: {self.container_name}")

                # Pull image if not exists (we'll create this image)
                try:
                    self.client.images.get("lifeos-computer-use:latest")
                except docker.errors.ImageNotFound:
                    return {
                        "success": False,
                        "message": "Docker image 'lifeos-computer-use:latest' not found. Please build it first using: docker build -f Dockerfile.computer -t lifeos-computer-use:latest .",
                    }

                # Create and start container
                self.container = self.client.containers.run(
                    "lifeos-computer-use:latest",
                    name=self.container_name,
                    detach=True,
                    ports={
                        "5900/tcp": 5900,  # VNC port
                        "6080/tcp": 6080,  # noVNC web port
                    },
                    environment={
                        "DISPLAY": f":{self.display_number}",
                        "RESOLUTION": f"{self.display_width}x{self.display_height}",
                        "VNC_PASSWORD": self.vnc_password,
                    },
                    dns=["1.1.1.3"],  # Restricted DNS for safety
                    cap_add=["SYS_ADMIN"],  # Required for some desktop operations
                )

                # Wait for container to be fully ready
                await asyncio.sleep(5)

            self.is_ready = True

            logger.info(
                f"Docker computer initialized ({self.display_width}x{self.display_height})"
            )
            logger.info("VNC available at: vnc://localhost:5900")
            logger.info("Web VNC available at: http://localhost:6080")

            return {
                "success": True,
                "message": f"Docker computer {'reused' if container_reused else 'created'}",
                "display_width": self.display_width,
                "display_height": self.display_height,
                "vnc_port": 5900,
                "web_vnc_port": 6080,
                "container_id": self.container.id[:12],
                "container_reused": container_reused,
            }

        except Exception as e:
            logger.error(f"Failed to initialize Docker computer: {e}")
            self.is_ready = False
            return {
                "success": False,
                "message": f"Initialization failed: {str(e)}",
            }

    async def _exec_command(self, command: str) -> tuple[int, str]:
        """Execute command in Docker container.

        Args:
            command: Shell command to execute

        Returns:
            Tuple of (exit_code, output)
        """
        if not self.container:
            raise RuntimeError("Container not initialized")

        result = self.container.exec_run(command, detach=False)
        return result.exit_code, result.output.decode("utf-8")

    async def screenshot(self) -> Dict[str, str]:
        """Take a screenshot using X11 tools in the container.

        Returns:
            Dictionary with screenshot data
        """
        try:
            if not self.container:
                return {
                    "error": "Container not initialized",
                    "screenshot": "",
                    "width": 0,
                    "height": 0,
                }

            # Take screenshot using import command (from ImageMagick)
            cmd = f"DISPLAY=:{self.display_number} import -window root /tmp/screenshot.png"
            exit_code, _ = await self._exec_command(cmd)

            if exit_code != 0:
                return {
                    "error": "Screenshot command failed",
                    "screenshot": "",
                    "width": 0,
                    "height": 0,
                }

            # Read screenshot file from container
            bits, stats = self.container.get_archive("/tmp/screenshot.png")

            # Extract file from tar archive
            import tarfile

            tar_stream = io.BytesIO(b"".join(bits))
            tar = tarfile.open(fileobj=tar_stream)
            screenshot_file = tar.extractfile("screenshot.png")
            screenshot_bytes = screenshot_file.read()

            # Encode to base64
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

            return {
                "screenshot": screenshot_b64,
                "width": self.display_width,
                "height": self.display_height,
                "timestamp": datetime.utcnow().isoformat(),
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
        """Click at specific coordinates using xdotool.

        Args:
            x: X coordinate
            y: Y coordinate
            button: Mouse button (1=left, 2=middle, 3=right)

        Returns:
            Dictionary with click status
        """
        try:
            if not self.container:
                return {"success": False, "message": "Container not initialized"}

            # Map button names to numbers
            button_map = {"left": "1", "middle": "2", "right": "3"}
            button_num = button_map.get(button.lower(), "1")

            # Execute click using xdotool
            cmd = f"DISPLAY=:{self.display_number} xdotool mousemove {x} {y} click {button_num}"
            exit_code, output = await self._exec_command(cmd)

            if exit_code == 0:
                return {
                    "success": True,
                    "message": f"Clicked at ({x}, {y}) with {button} button",
                }
            else:
                return {
                    "success": False,
                    "message": f"Click failed: {output}",
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
            if not self.container:
                return {"success": False, "message": "Container not initialized"}

            # Execute double-click using xdotool
            cmd = f"DISPLAY=:{self.display_number} xdotool mousemove {x} {y} click --repeat 2 1"
            exit_code, output = await self._exec_command(cmd)

            if exit_code == 0:
                return {
                    "success": True,
                    "message": f"Double-clicked at ({x}, {y})",
                }
            else:
                return {
                    "success": False,
                    "message": f"Double-click failed: {output}",
                }

        except Exception as e:
            logger.error(f"Error double-clicking: {e}")
            return {"success": False, "message": str(e)}

    async def type_text(self, text: str, delay_ms: int = 50) -> Dict[str, str]:
        """Type text using xdotool.

        Args:
            text: Text to type
            delay_ms: Delay between keystrokes

        Returns:
            Dictionary with typing status
        """
        try:
            if not self.container:
                return {"success": False, "message": "Container not initialized"}

            # Escape special characters for shell
            escaped_text = text.replace("'", "'\\''")

            # Execute type using xdotool with delay
            cmd = f"DISPLAY=:{self.display_number} xdotool type --delay {delay_ms} '{escaped_text}'"
            exit_code, output = await self._exec_command(cmd)

            if exit_code == 0:
                return {
                    "success": True,
                    "message": f"Typed {len(text)} characters",
                }
            else:
                return {
                    "success": False,
                    "message": f"Type failed: {output}",
                }

        except Exception as e:
            logger.error(f"Error typing text: {e}")
            return {"success": False, "message": str(e)}

    async def press_key(self, key: str) -> Dict[str, str]:
        """Press a keyboard key using xdotool.

        Args:
            key: Key to press (xdotool key names)

        Returns:
            Dictionary with key press status
        """
        try:
            if not self.container:
                return {"success": False, "message": "Container not initialized"}

            # Execute key press using xdotool
            # Handle key combinations (replace + with space for xdotool)
            xdotool_key = key.replace("+", " ")

            cmd = f"DISPLAY=:{self.display_number} xdotool key {xdotool_key}"
            exit_code, output = await self._exec_command(cmd)

            if exit_code == 0:
                return {
                    "success": True,
                    "message": f"Pressed key: {key}",
                }
            else:
                return {
                    "success": False,
                    "message": f"Key press failed: {output}",
                }

        except Exception as e:
            logger.error(f"Error pressing key: {e}")
            return {"success": False, "message": str(e)}

    async def scroll(
        self, x: int, y: int, scroll_x: int = 0, scroll_y: int = -100
    ) -> Dict[str, str]:
        """Scroll using xdotool.

        Args:
            x: X coordinate
            y: Y coordinate
            scroll_x: Horizontal scroll (not fully supported)
            scroll_y: Vertical scroll (negative = up, positive = down)

        Returns:
            Dictionary with scroll status
        """
        try:
            if not self.container:
                return {"success": False, "message": "Container not initialized"}

            # Move mouse to position
            move_cmd = f"DISPLAY=:{self.display_number} xdotool mousemove {x} {y}"
            await self._exec_command(move_cmd)

            # Determine scroll direction and amount
            # Button 4 = scroll up, Button 5 = scroll down
            if scroll_y < 0:
                button = "4"
                clicks = abs(scroll_y) // 10  # Scale factor
            else:
                button = "5"
                clicks = scroll_y // 10

            clicks = max(1, clicks)  # At least 1 click

            # Execute scroll
            scroll_cmd = f"DISPLAY=:{self.display_number} xdotool click --repeat {clicks} {button}"
            exit_code, output = await self._exec_command(scroll_cmd)

            if exit_code == 0:
                return {
                    "success": True,
                    "message": f"Scrolled at ({x}, {y})",
                }
            else:
                return {
                    "success": False,
                    "message": f"Scroll failed: {output}",
                }

        except Exception as e:
            logger.error(f"Error scrolling: {e}")
            return {"success": False, "message": str(e)}

    async def navigate_to_url(self, url: str) -> Dict[str, str]:
        """Open URL in Firefox browser.

        Args:
            url: URL to navigate to

        Returns:
            Dictionary with navigation status
        """
        try:
            if not self.container:
                return {"success": False, "message": "Container not initialized", "url": ""}

            # Launch Firefox with URL
            cmd = f"DISPLAY=:{self.display_number} firefox '{url}' &"
            exit_code, output = await self._exec_command(cmd)

            # Wait for browser to load
            await asyncio.sleep(3)

            return {
                "success": True,
                "message": f"Opened {url} in Firefox",
                "url": url,
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

    async def get_status(self) -> Dict[str, Any]:
        """Get current container status.

        Returns:
            Dictionary with status information
        """
        if not self.container:
            return {
                "ready": False,
                "message": "Container not initialized",
            }

        try:
            self.container.reload()  # Refresh container state

            return {
                "ready": self.is_ready,
                "display_width": self.display_width,
                "display_height": self.display_height,
                "container_status": self.container.status,
                "container_id": self.container.id[:12],
                "vnc_port": 5900,
                "web_vnc_port": 6080,
                "environment": "docker",
            }
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {
                "ready": False,
                "error": str(e),
            }

    async def start_browser(self, start_url: str = "https://www.google.com") -> Dict[str, str]:
        """Start Firefox browser and navigate to URL.

        Args:
            start_url: Initial URL

        Returns:
            Dictionary with start status
        """
        return await self.navigate_to_url(start_url)

    async def cleanup(self) -> Dict[str, str]:
        """Stop and remove the Docker container.

        Returns:
            Dictionary with cleanup status
        """
        try:
            if self.container:
                logger.info(f"Stopping container: {self.container_name}")
                self.container.stop(timeout=10)
                self.container.remove()
                self.container = None

            if self.client:
                self.client.close()
                self.client = None

            self.is_ready = False

            return {
                "success": True,
                "message": "Container stopped and removed",
            }

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return {"success": False, "message": str(e)}
