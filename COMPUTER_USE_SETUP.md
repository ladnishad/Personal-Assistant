# Computer Use Agent Setup Guide

The Computer Use Agent enables LifeOS to automate browser and desktop tasks like booking reservations, ordering items, filling forms, and performing web-based workflows.

## Overview

The Computer Use Agent provides two execution environments:

1. **Playwright (Local Browser)** - Simple, fast, browser-only automation
2. **Docker (Full VM)** - Complete Ubuntu desktop with VNC for advanced use cases

## Quick Start

### Option 1: Playwright (Recommended for Getting Started)

Playwright provides local browser control without additional infrastructure.

**Installation:**

```bash
# Install Playwright
pip install playwright

# Install browser binaries
playwright install chromium
```

**Configuration:**

```bash
# In your .env file
COMPUTER_ENVIRONMENT=playwright
```

**Usage:**

The agent will automatically launch a Chromium browser when needed. No additional setup required!

### Option 2: Docker VM (Advanced)

Docker VM provides a complete Ubuntu desktop environment with full control capabilities.

**Prerequisites:**
- Docker installed and running
- Ports 5900 and 6080 available

**Build the Docker Image:**

```bash
# Build the computer use VM image
docker build -f Dockerfile.computer -t lifeos-computer-use:latest .
```

**Configuration:**

```bash
# In your .env file
COMPUTER_ENVIRONMENT=docker
```

**Access the Desktop:**

Once the container is running, you can view the desktop:

- **VNC Client**: Connect to `vnc://localhost:5900` (password: `lifeos123`)
- **Web Browser**: Open `http://localhost:6080` (no VNC client needed)

**Manual Container Management:**

```bash
# Start container manually
docker run -d \
  --name lifeos-computer-use \
  -p 5900:5900 \
  -p 6080:6080 \
  -e DISPLAY=:99 \
  -e RESOLUTION=1024x768 \
  --dns=1.1.1.3 \
  lifeos-computer-use:latest

# View logs
docker logs -f lifeos-computer-use

# Stop container
docker stop lifeos-computer-use

# Remove container
docker rm lifeos-computer-use
```

## Using the Computer Control Agent

### Through the Main Agent

The main LifeOS agent will automatically hand off to the Computer Control Agent when you request tasks that require visual interface interaction.

**Examples:**

```
User: "Book a table at Resy for 2 people tomorrow at 7pm"
→ Agent transfers to Computer Control Specialist
→ Opens browser, navigates to Resy, searches, and books

User: "Search Amazon for wireless headphones under $100 and show me the top options"
→ Agent opens Amazon, searches, applies filters, shows results

User: "Fill out this form on the website with my information"
→ Agent analyzes form, fills fields, asks for confirmation before submitting
```

### Direct API Usage

You can also interact with the Computer Control Agent directly through the chat API:

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/agent/chat",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "message": "Go to google.com and search for 'OpenAI agents'",
        "conversation_id": "optional-conv-id"
    }
)
```

## Available Actions

The Computer Control Agent can perform these actions:

### Visual Actions
- **Screenshot**: Capture current screen state
- **Click**: Click at specific coordinates
- **Double-click**: Double-click at coordinates
- **Scroll**: Scroll page up/down/left/right

### Keyboard Actions
- **Type Text**: Enter text with configurable delay
- **Press Key**: Single keys or combinations (Enter, Tab, Ctrl+C, etc.)

### Navigation
- **Navigate to URL**: Open websites
- **Start Browser**: Launch browser with initial URL
- **Wait**: Pause for page loads or animations

### Status
- **Get Status**: Check environment readiness and details

## Safety Features

### Built-in Safety Measures

1. **Restricted DNS** (Docker only): Container uses DNS 1.1.1.3 for safer browsing
2. **Explicit Confirmation**: Agent asks before executing financial transactions
3. **No Destructive Actions**: Agent refuses account deletion, data destruction
4. **Authentication Warnings**: Stops if unexpected auth prompts appear
5. **Screenshot Validation**: Verifies each action with visual feedback

### Best Practices

- ✅ Use for public websites and unauthenticated workflows
- ✅ Review agent actions in real-time via VNC (Docker)
- ✅ Provide clear, specific task instructions
- ✅ Confirm before allowing financial transactions
- ❌ Avoid authenticated environments without explicit permission
- ❌ Don't use for high-stakes or sensitive operations
- ❌ Don't share sensitive information visible in screenshots

## Configuration Options

Add these to your `.env` file:

```bash
# Computer environment type
COMPUTER_ENVIRONMENT=playwright  # or "docker"

# Display settings (Docker only)
COMPUTER_DISPLAY_WIDTH=1024
COMPUTER_DISPLAY_HEIGHT=768

# VNC password (Docker only)
COMPUTER_VNC_PASSWORD=lifeos123
```

## Troubleshooting

### Playwright Issues

**Browser won't launch:**
```bash
# Reinstall browser binaries
playwright install chromium --force
```

**Permission errors:**
```bash
# Ensure proper permissions
chmod +x $(which playwright)
```

### Docker Issues

**Container won't start:**
```bash
# Check Docker is running
docker ps

# View container logs
docker logs lifeos-computer-use

# Rebuild image
docker build -f Dockerfile.computer -t lifeos-computer-use:latest . --no-cache
```

**VNC connection fails:**
```bash
# Verify ports are not in use
lsof -i :5900
lsof -i :6080

# Check firewall rules
sudo ufw status
```

**Desktop doesn't appear:**
```bash
# Exec into container
docker exec -it lifeos-computer-use bash

# Check X server
ps aux | grep Xvfb

# Restart services manually
~/start.sh
```

### Agent Issues

**Actions not executing:**
- Check computer status: Agent will call `get_computer_status` first
- Verify environment is initialized
- Check logs for error messages

**Screenshots are blank:**
- Wait a few seconds for desktop to render (Docker)
- Ensure browser has loaded completely
- Check container resources (CPU/memory)

**Clicks miss targets:**
- Take screenshot first to verify coordinates
- Account for page scroll position
- Ensure element is visible on screen

## Architecture

```
┌─────────────────────────────────────────┐
│         LifeOS Main Agent               │
│  (Handles general queries, memory,      │
│   tasks, emails, etc.)                  │
└────────────────┬────────────────────────┘
                 │
                 │ Handoff when user requests
                 │ browser/desktop automation
                 ▼
┌─────────────────────────────────────────┐
│    Computer Control Specialist Agent    │
│  (Specialized in visual automation)     │
└────────────────┬────────────────────────┘
                 │
                 │ Uses computer tools
                 ▼
┌─────────────────────────────────────────┐
│         Computer Manager                │
│  (Selects appropriate environment)      │
└────────────┬────────────────────────────┘
             │
    ┌────────┴─────────┐
    ▼                  ▼
┌─────────────┐  ┌──────────────┐
│ Playwright  │  │    Docker    │
│  Computer   │  │   Computer   │
│             │  │              │
│ • Chromium  │  │ • Ubuntu VM  │
│ • Local     │  │ • VNC        │
│ • Fast      │  │ • Full DE    │
└─────────────┘  └──────────────┘
```

## Use Cases

### Booking & Reservations
- Restaurant reservations (OpenTable, Resy)
- Hotel bookings
- Event tickets
- Appointment scheduling

### E-commerce
- Product searches
- Price comparisons
- Order placement (with confirmation)
- Tracking lookups

### Data Entry
- Form filling
- Spreadsheet data entry
- CMS content updates
- Database management interfaces

### Research & Information Gathering
- Multi-site price checking
- Availability verification
- Content aggregation
- Competitive analysis

### Testing & QA
- Web app testing
- Form validation
- User flow verification
- Cross-browser checks

## API Reference

### Computer Tools

All tools are available to the Computer Control Agent:

```python
# Take screenshot
take_screenshot() -> Dict[str, str]

# Mouse actions
click(x: int, y: int, button: str = "left") -> Dict[str, str]
double_click(x: int, y: int) -> Dict[str, str]
scroll(x: int, y: int, scroll_x: int = 0, scroll_y: int = -100) -> Dict[str, str]

# Keyboard actions
type_text(text: str, delay_ms: int = 50) -> Dict[str, str]
press_key(key: str) -> Dict[str, str]  # e.g., "Enter", "Control+c"

# Navigation
navigate_to_url(url: str) -> Dict[str, str]
start_browser(start_url: str = "https://www.google.com") -> Dict[str, str]

# Utilities
wait(milliseconds: int) -> Dict[str, str]
get_computer_status() -> Dict[str, any]
```

## Contributing

To add new computer environments:

1. Implement `Computer` base class in `app/computers/`
2. Add environment selection logic to `ComputerManager`
3. Update configuration options
4. Add tests
5. Document setup and usage

## License

Same as main LifeOS project.

## Support

For issues or questions:
- Check troubleshooting section above
- Review Docker/Playwright logs
- Open an issue with:
  - Environment type (Playwright/Docker)
  - Error messages
  - Steps to reproduce
  - Screenshots if relevant
