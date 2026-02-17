"""Pydantic request/response models for the browser sidecar API."""

from __future__ import annotations

from pydantic import BaseModel


# --- Request models ---


class NavigateRequest(BaseModel):
    """Request to navigate to a URL."""

    url: str
    wait_until: str = "load"  # load, domcontentloaded, networkidle


class ClickRequest(BaseModel):
    """Request to click an element."""

    selector: str
    timeout: int | None = None  # milliseconds; None uses env default


class FillRequest(BaseModel):
    """Request to fill an input field."""

    selector: str
    value: str
    timeout: int | None = None


class ScreenshotRequest(BaseModel):
    """Request to capture a screenshot. JPEG format, viewport-only by default."""

    full_page: bool = False
    quality: int = 80  # JPEG quality (1-100)


class QuerySelectorRequest(BaseModel):
    """Request to query elements or get element text."""

    selector: str
    timeout: int | None = None


class WaitForRequest(BaseModel):
    """Request to wait for an element to reach a specific state."""

    selector: str
    state: str = "visible"  # visible, hidden, attached, detached
    timeout: int | None = None


class TabSwitchRequest(BaseModel):
    """Request to switch to or close a tab by index."""

    index: int


# --- Response models ---


class BrowserResult(BaseModel):
    """Unified response for all browser operations."""

    success: bool
    data: dict | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    """Response for the health check endpoint."""

    status: str
    tabs: int
    current_url: str | None = None
