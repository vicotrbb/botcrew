"""Single persistent browser session for the sidecar.

One browser per pod -- no auth, no TTL, no multi-session.
The session is started at container boot and shut down on container stop.
"""

from __future__ import annotations

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from env import settings
from logger import logger


class BrowserSession:
    """Manages a single persistent Chromium browser session."""

    def __init__(self) -> None:
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._active_page_index: int = 0

    # --- Lifecycle ---

    async def start(self) -> None:
        """Launch Chromium headless, create one context and one page."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=settings.browser_headless,
        )
        self._context = await self._browser.new_context(
            viewport={
                "width": settings.viewport_width,
                "height": settings.viewport_height,
            },
        )
        await self._context.new_page()
        self._active_page_index = 0
        logger.info(
            "browser_session_started",
            headless=settings.browser_headless,
            viewport=f"{settings.viewport_width}x{settings.viewport_height}",
        )

    async def shutdown(self) -> None:
        """Close browser and stop Playwright."""
        if self._browser:
            try:
                await self._browser.close()
            except Exception as exc:
                logger.error("browser_close_error", error=str(exc))
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception as exc:
                logger.error("playwright_stop_error", error=str(exc))
        logger.info("browser_session_shutdown")

    async def reset(self) -> None:
        """Clear cookies, close extra tabs, navigate to about:blank."""
        if self._context is None:
            return

        await self._context.clear_cookies()

        # Close all pages except the first
        pages = self._context.pages
        for page in pages[1:]:
            await page.close()

        self._active_page_index = 0
        first_page = self._context.pages[0]
        await first_page.goto("about:blank")
        logger.info("browser_session_reset")

    # --- Page access ---

    @property
    def page(self) -> Page:
        """Return the currently active page."""
        pages = self.pages
        if self._active_page_index >= len(pages):
            self._active_page_index = len(pages) - 1
        return pages[self._active_page_index]

    @property
    def pages(self) -> list[Page]:
        """Return all pages in the browser context."""
        if self._context is None:
            return []
        return self._context.pages

    @property
    def default_timeout(self) -> int:
        """Return the default Playwright timeout from settings (ms)."""
        return settings.default_timeout

    # --- Tab management ---

    async def new_tab(self) -> int:
        """Create a new page in the context and return its index."""
        if self._context is None:
            raise RuntimeError("Browser session not started")
        await self._context.new_page()
        new_index = len(self._context.pages) - 1
        self._active_page_index = new_index
        logger.info("tab_opened", index=new_index)
        return new_index

    async def switch_tab(self, index: int) -> None:
        """Set the active page to the page at *index*."""
        pages = self.pages
        if index < 0 or index >= len(pages):
            raise IndexError(f"Tab index {index} out of range (0-{len(pages) - 1})")
        self._active_page_index = index
        logger.info("tab_switched", index=index)

    async def close_tab(self, index: int) -> None:
        """Close the page at *index* and adjust the active page."""
        pages = self.pages
        if index < 0 or index >= len(pages):
            raise IndexError(f"Tab index {index} out of range (0-{len(pages) - 1})")
        if len(pages) <= 1:
            raise RuntimeError("Cannot close the last tab")

        await pages[index].close()

        # Adjust active page index
        if self._active_page_index >= len(self.pages):
            self._active_page_index = len(self.pages) - 1
        elif self._active_page_index > index:
            self._active_page_index -= 1

        logger.info("tab_closed", index=index, active=self._active_page_index)
