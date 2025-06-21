import asyncio
from typing import Any, Dict, Optional

import zendriver
from loguru import logger


async def get_browser(
    ws_endpoint: str,
) -> Optional[Any]:
    """
    Connects to an existing browser instance using Zendriver.

    Args:
        ws_endpoint: The WebSocket endpoint of the running browser.

    Returns:
        An instance of an asynchronous Zendriver browser, or None on failure.
    """
    try:
        browser = await zendriver.connect(endpoint=ws_endpoint)
        logger.info(f"Successfully connected to browser at {ws_endpoint}")
        return browser
    except Exception as e:
        logger.error(f"Failed to connect to browser: {e}")
        return None


async def get_current_ip(browser: Any) -> Optional[str]:
    """
    Gets the current external IP address using the browser.

    Args:
        browser: The Zendriver browser instance.

    Returns:
        The current IP address as a string, or None on failure.
    """
    page = await browser.new_page()
    try:
        await page.goto("https://api.ipify.org", wait_until="domcontentloaded")
        ip = await page.evaluate("() => document.body.textContent")
        logger.info(f"Current IP address is: {ip}")
        return ip
    except Exception as e:
        logger.error(f"Could not determine IP address: {e}")
        return None
    finally:
        await page.close() 