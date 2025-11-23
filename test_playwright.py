#!/usr/bin/env python3
"""Test Playwright browser initialization."""

import asyncio
from playwright.async_api import async_playwright


async def test_browser():
    """Test if Playwright can launch a browser."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            print("✓ Browser launched successfully")
            page = await browser.new_page()
            print("✓ Created new page")
            await page.goto("https://www.google.com")
            print("✓ Navigated to Google")
            title = await page.title()
            print(f"✓ Page title: {title}")
            await browser.close()
            print("✓ Browser closed successfully")
            return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_browser())
    exit(0 if success else 1)