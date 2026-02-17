"""Browser sidecar FastAPI application.

Exposes Playwright browser operations as HTTP endpoints at port 8001.
A single BrowserSession is started at boot and shared across all requests.
No authentication -- only accessible from localhost within the pod.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request

import browser_ops
from logger import logger
from models import (
    BrowserResult,
    ClickRequest,
    FillRequest,
    HealthResponse,
    NavigateRequest,
    QuerySelectorRequest,
    ScreenshotRequest,
    TabSwitchRequest,
    WaitForRequest,
)
from session import BrowserSession


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start the browser on startup, shut it down on shutdown."""
    session = BrowserSession()
    await session.start()
    app.state.session = session
    logger.info("browser_sidecar_ready")
    yield
    await session.shutdown()
    logger.info("browser_sidecar_stopped")


app = FastAPI(
    title="Botcrew Browser Sidecar",
    description="Playwright browser operations for agent pods",
    version="1.0.0",
    lifespan=lifespan,
)


def _session(request: Request) -> BrowserSession:
    """Retrieve the shared BrowserSession from app state."""
    return request.app.state.session


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/api/v1/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Health check -- reports status, tab count, and current URL."""
    session = _session(request)
    current_url: str | None = None
    try:
        current_url = session.page.url
    except Exception:
        pass
    return HealthResponse(
        status="healthy",
        tabs=len(session.pages),
        current_url=current_url,
    )


# ---------------------------------------------------------------------------
# Browser operations
# ---------------------------------------------------------------------------


@app.post("/api/v1/navigate", response_model=BrowserResult)
async def navigate(body: NavigateRequest, request: Request) -> BrowserResult:
    """Navigate to a URL."""
    return await browser_ops.navigate(
        _session(request), body.url, body.wait_until
    )


@app.post("/api/v1/click", response_model=BrowserResult)
async def click(body: ClickRequest, request: Request) -> BrowserResult:
    """Click an element."""
    return await browser_ops.click(
        _session(request), body.selector, body.timeout
    )


@app.post("/api/v1/fill", response_model=BrowserResult)
async def fill(body: FillRequest, request: Request) -> BrowserResult:
    """Fill an input field."""
    return await browser_ops.fill(
        _session(request), body.selector, body.value, body.timeout
    )


@app.post("/api/v1/screenshot", response_model=BrowserResult)
async def screenshot(body: ScreenshotRequest, request: Request) -> BrowserResult:
    """Capture a JPEG screenshot (viewport-only by default)."""
    return await browser_ops.screenshot(
        _session(request), body.full_page, body.quality
    )


@app.post("/api/v1/element-text", response_model=BrowserResult)
async def element_text(body: QuerySelectorRequest, request: Request) -> BrowserResult:
    """Get the text content of an element."""
    return await browser_ops.get_element_text(
        _session(request), body.selector, body.timeout
    )


@app.post("/api/v1/query-selector", response_model=BrowserResult)
async def query_selector(body: QuerySelectorRequest, request: Request) -> BrowserResult:
    """Query elements matching a selector."""
    return await browser_ops.query_selector(
        _session(request), body.selector, body.timeout
    )


@app.post("/api/v1/wait-for", response_model=BrowserResult)
async def wait_for(body: WaitForRequest, request: Request) -> BrowserResult:
    """Wait for an element to reach a specific state."""
    return await browser_ops.wait_for(
        _session(request), body.selector, body.state, body.timeout
    )


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------


@app.post("/api/v1/reset", response_model=BrowserResult)
async def reset(request: Request) -> BrowserResult:
    """Reset the browser to a clean state (clear cookies, close extra tabs)."""
    session = _session(request)
    try:
        await session.reset()
        return BrowserResult(success=True, data={"message": "Session reset to about:blank"})
    except Exception as exc:
        return BrowserResult(success=False, error=str(exc))


# ---------------------------------------------------------------------------
# Tab management
# ---------------------------------------------------------------------------


@app.get("/api/v1/tabs", response_model=BrowserResult)
async def list_tabs(request: Request) -> BrowserResult:
    """List all open tabs with URL and title."""
    session = _session(request)
    tabs: list[dict] = []
    for i, page in enumerate(session.pages):
        title: str | None = None
        try:
            title = await page.title()
        except Exception:
            pass
        tabs.append({"index": i, "url": page.url, "title": title})
    return BrowserResult(success=True, data={"tabs": tabs})


@app.post("/api/v1/tabs/new", response_model=BrowserResult)
async def new_tab(request: Request) -> BrowserResult:
    """Open a new tab and return its index."""
    session = _session(request)
    try:
        index = await session.new_tab()
        return BrowserResult(success=True, data={"index": index})
    except Exception as exc:
        return BrowserResult(success=False, error=str(exc))


@app.post("/api/v1/tabs/switch", response_model=BrowserResult)
async def switch_tab(body: TabSwitchRequest, request: Request) -> BrowserResult:
    """Switch to the tab at the given index."""
    session = _session(request)
    try:
        await session.switch_tab(body.index)
        return BrowserResult(success=True, data={"active_tab": body.index})
    except (IndexError, RuntimeError) as exc:
        return BrowserResult(success=False, error=str(exc))


@app.post("/api/v1/tabs/close", response_model=BrowserResult)
async def close_tab(body: TabSwitchRequest, request: Request) -> BrowserResult:
    """Close the tab at the given index."""
    session = _session(request)
    try:
        await session.close_tab(body.index)
        return BrowserResult(
            success=True,
            data={"closed_tab": body.index, "remaining_tabs": len(session.pages)},
        )
    except (IndexError, RuntimeError) as exc:
        return BrowserResult(success=False, error=str(exc))
