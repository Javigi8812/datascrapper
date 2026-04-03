from __future__ import annotations

import asyncio
import logging
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from config import PAGE_TIMEOUT_MS, MAX_RETRIES, RETRY_BACKOFF_BASE

logger = logging.getLogger(__name__)


class BrowserManager:
    def __init__(self) -> None:
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        self._context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )

    async def stop(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def fetch_html(self, url: str) -> str:
        last_error: Optional[Exception] = None
        for attempt in range(1, MAX_RETRIES + 1):
            page: Optional[Page] = None
            try:
                page = await self._context.new_page()
                logger.info("Fetching %s (attempt %d/%d)", url, attempt, MAX_RETRIES)
                await page.goto(url, wait_until="networkidle", timeout=PAGE_TIMEOUT_MS)
                await page.wait_for_timeout(1500)
                html = await page.content()
                return html
            except Exception as exc:
                last_error = exc
                wait = RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    "Attempt %d failed for %s: %s. Retrying in %ds...",
                    attempt, url, exc, wait,
                )
                await asyncio.sleep(wait)
            finally:
                if page:
                    await page.close()

        raise RuntimeError(
            f"Failed to fetch {url} after {MAX_RETRIES} attempts: {last_error}"
        )

    async def __aenter__(self) -> "BrowserManager":
        await self.start()
        return self

    async def __aexit__(self, *args) -> None:
        await self.stop()
