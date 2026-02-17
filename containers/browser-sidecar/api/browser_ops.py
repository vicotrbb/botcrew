"""Playwright page operations for the browser sidecar.

Each function takes a BrowserSession and returns a BrowserResult dict.
Errors are caught and returned as BrowserResult(success=False, error=...).
"""

from __future__ import annotations

import base64

from playwright.async_api import Error as PlaywrightError

from logger import logger
from models import BrowserResult
from session import BrowserSession


async def navigate(
    session: BrowserSession,
    url: str,
    wait_until: str = "load",
) -> BrowserResult:
    """Navigate to *url* and return the resulting page URL and title."""
    try:
        await session.page.goto(url, wait_until=wait_until)
        title = await session.page.title()
        logger.info("navigate_success", url=session.page.url, title=title)
        return BrowserResult(
            success=True,
            data={"url": session.page.url, "title": title},
        )
    except PlaywrightError as exc:
        logger.warning("navigate_error", url=url, error=str(exc))
        return BrowserResult(success=False, error=str(exc))


async def click(
    session: BrowserSession,
    selector: str,
    timeout: int | None = None,
) -> BrowserResult:
    """Click the element matched by *selector*."""
    try:
        effective_timeout = timeout if timeout is not None else session.default_timeout
        await session.page.click(selector, timeout=effective_timeout)
        logger.info("click_success", selector=selector)
        return BrowserResult(
            success=True,
            data={"selector": selector},
        )
    except PlaywrightError as exc:
        logger.warning("click_error", selector=selector, error=str(exc))
        return BrowserResult(success=False, error=str(exc))


async def fill(
    session: BrowserSession,
    selector: str,
    value: str,
    timeout: int | None = None,
) -> BrowserResult:
    """Fill the input matched by *selector* with *value*."""
    try:
        effective_timeout = timeout if timeout is not None else session.default_timeout
        await session.page.fill(selector, value, timeout=effective_timeout)
        logger.info("fill_success", selector=selector)
        return BrowserResult(
            success=True,
            data={"selector": selector, "value": value},
        )
    except PlaywrightError as exc:
        logger.warning("fill_error", selector=selector, error=str(exc))
        return BrowserResult(success=False, error=str(exc))


async def screenshot(
    session: BrowserSession,
    full_page: bool = False,
    quality: int = 80,
) -> BrowserResult:
    """Capture a JPEG screenshot and return the base64-encoded image."""
    try:
        screenshot_bytes = await session.page.screenshot(
            type="jpeg",
            quality=quality,
            full_page=full_page,
        )
        image_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
        logger.info("screenshot_success", full_page=full_page, quality=quality)
        return BrowserResult(
            success=True,
            data={"image": image_b64, "format": "jpeg"},
        )
    except PlaywrightError as exc:
        logger.warning("screenshot_error", error=str(exc))
        return BrowserResult(success=False, error=str(exc))


async def get_element_text(
    session: BrowserSession,
    selector: str,
    timeout: int | None = None,
) -> BrowserResult:
    """Wait for *selector* then return its text content."""
    try:
        effective_timeout = timeout if timeout is not None else session.default_timeout
        element = await session.page.wait_for_selector(
            selector, timeout=effective_timeout
        )
        if element is None:
            return BrowserResult(
                success=False, error=f"Element not found: {selector}"
            )
        text = await element.text_content()
        logger.info("get_element_text_success", selector=selector)
        return BrowserResult(
            success=True,
            data={"selector": selector, "text": text},
        )
    except PlaywrightError as exc:
        logger.warning("get_element_text_error", selector=selector, error=str(exc))
        return BrowserResult(success=False, error=str(exc))


async def query_selector(
    session: BrowserSession,
    selector: str,
    timeout: int | None = None,
) -> BrowserResult:
    """Query all elements matching *selector* and return summaries.

    Each summary includes tag name, truncated text content (200 chars),
    and key attributes (href, src, id, class).
    """
    try:
        # Optional wait so the caller can ensure elements are rendered
        if timeout is not None:
            await session.page.wait_for_selector(selector, timeout=timeout)

        elements = await session.page.query_selector_all(selector)
        summaries: list[dict] = []

        for el in elements:
            tag = await el.evaluate("el => el.tagName.toLowerCase()")
            text = await el.text_content()
            attrs: dict = await el.evaluate(
                """el => {
                    const pick = {};
                    for (const name of ['href', 'src', 'id', 'class']) {
                        const val = el.getAttribute(name);
                        if (val !== null) pick[name] = val;
                    }
                    return pick;
                }"""
            )
            summaries.append(
                {
                    "tag": tag,
                    "text": (text.strip()[:200] if text else None),
                    "attributes": attrs,
                }
            )

        logger.info("query_selector_success", selector=selector, count=len(summaries))
        return BrowserResult(
            success=True,
            data={"selector": selector, "count": len(summaries), "elements": summaries},
        )
    except PlaywrightError as exc:
        logger.warning("query_selector_error", selector=selector, error=str(exc))
        return BrowserResult(success=False, error=str(exc))


async def wait_for(
    session: BrowserSession,
    selector: str,
    state: str = "visible",
    timeout: int | None = None,
) -> BrowserResult:
    """Wait for *selector* to reach *state*."""
    try:
        effective_timeout = timeout if timeout is not None else session.default_timeout
        await session.page.wait_for_selector(
            selector, state=state, timeout=effective_timeout
        )
        logger.info("wait_for_success", selector=selector, state=state)
        return BrowserResult(
            success=True,
            data={"selector": selector, "state": state},
        )
    except PlaywrightError as exc:
        logger.warning("wait_for_error", selector=selector, state=state, error=str(exc))
        return BrowserResult(success=False, error=str(exc))
