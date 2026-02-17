"""BrowserTools -- Agno toolkit for browser automation via pod-local sidecar.

Enables botcrew agents to control the co-located Playwright browser sidecar
for web automation tasks. Each tool method makes a synchronous HTTP call to
the browser sidecar running at localhost:8001 within the same K8s pod.

All tools return plain ``str`` results (Agno convention). Errors are returned
as descriptive strings -- never raised -- so the agent can interpret and
recover gracefully.
"""

from __future__ import annotations

import json

import httpx
from agno.tools import Toolkit


class BrowserTools(Toolkit):
    """Agno toolkit wrapping the browser sidecar HTTP API.

    The browser sidecar exposes Playwright operations at ``/api/v1/*``
    on port 8001.  Since sidecar and agent share a pod (localhost
    network), latency is negligible and sync HTTP is fine.
    """

    def __init__(
        self,
        browser_url: str = "http://localhost:8001",
        **kwargs,
    ):
        self.browser_url = browser_url.rstrip("/")
        self.default_timeout = 30  # seconds for httpx

        super().__init__(
            name="browser_tools",
            tools=[
                self.navigate,
                self.click,
                self.fill,
                self.screenshot,
                self.get_element_text,
                self.query_selector,
                self.wait_for,
                self.get_tabs,
                self.new_tab,
                self.switch_tab,
                self.close_tab,
                self.reset_browser,
            ],
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        endpoint: str,
        json_data: dict | None = None,
        timeout: int | None = None,
    ) -> dict:
        """Make a synchronous HTTP request to the browser sidecar.

        Returns the parsed JSON response on success, or a synthetic
        error dict on failure.  Never raises.
        """
        url = f"{self.browser_url}/api/v1{endpoint}"
        effective_timeout = timeout or self.default_timeout

        try:
            with httpx.Client(timeout=effective_timeout) as client:
                response = client.request(
                    method=method,
                    url=url,
                    json=json_data,
                )
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            return {"success": False, "error": f"Browser sidecar error: {exc}"}

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def navigate(self, url: str, wait_until: str = "load") -> str:
        """Navigate the browser to a URL. Use 'load' for standard pages, 'networkidle' for SPAs."""
        result = self._request(
            "POST", "/navigate", {"url": url, "wait_until": wait_until}
        )
        if result.get("success"):
            data = result.get("data", {})
            title = data.get("title", "Unknown")
            final_url = data.get("url", url)
            return f"Navigated to {title} ({final_url})"
        return f"Navigation failed: {result.get('error', 'unknown error')}"

    # ------------------------------------------------------------------
    # Interactions
    # ------------------------------------------------------------------

    def click(self, selector: str) -> str:
        """Click an element by CSS selector."""
        result = self._request("POST", "/click", {"selector": selector})
        if result.get("success"):
            return f"Clicked {selector}"
        return f"Click failed: {result.get('error', 'unknown error')}"

    def fill(self, selector: str, value: str) -> str:
        """Fill a form field by CSS selector with the given value."""
        result = self._request(
            "POST", "/fill", {"selector": selector, "value": value}
        )
        if result.get("success"):
            return f"Filled {selector}"
        return f"Fill failed: {result.get('error', 'unknown error')}"

    # ------------------------------------------------------------------
    # Screenshots
    # ------------------------------------------------------------------

    def screenshot(self) -> str:
        """Take a screenshot of the current browser viewport. Returns a base64-encoded JPEG image."""
        result = self._request(
            "POST",
            "/screenshot",
            {"full_page": False, "quality": 80},
            timeout=60,
        )
        if result.get("success"):
            data = result.get("data", {})
            image = data.get("image")
            if image:
                return image
            return "Screenshot captured but no image data returned."
        return f"Screenshot failed: {result.get('error', 'unknown error')}"

    # ------------------------------------------------------------------
    # DOM queries
    # ------------------------------------------------------------------

    def get_element_text(self, selector: str) -> str:
        """Get the text content of an element by CSS selector."""
        result = self._request(
            "POST", "/element-text", {"selector": selector}
        )
        if result.get("success"):
            data = result.get("data", {})
            text = data.get("text", "")
            return text if text else "(empty text)"
        return f"Get text failed: {result.get('error', 'unknown error')}"

    def query_selector(self, selector: str) -> str:
        """Find all elements matching a CSS selector. Returns a summary of each element (tag, text, attributes)."""
        result = self._request(
            "POST", "/query-selector", {"selector": selector}
        )
        if result.get("success"):
            data = result.get("data", {})
            count = data.get("count", 0)
            elements = data.get("elements", [])
            if not elements:
                return f"No elements found matching '{selector}'."
            lines = [f"Found {count} element(s) matching '{selector}':"]
            for i, el in enumerate(elements):
                tag = el.get("tag", "?")
                text = el.get("text", "")
                attrs = el.get("attributes", {})
                attr_str = " ".join(
                    f'{k}="{v}"' for k, v in attrs.items()
                ) if attrs else ""
                text_preview = text[:100] if text else ""
                lines.append(
                    f"  {i + 1}. <{tag}{' ' + attr_str if attr_str else ''}>"
                    f"{' -- ' + text_preview if text_preview else ''}"
                )
            return "\n".join(lines)
        return f"Query failed: {result.get('error', 'unknown error')}"

    # ------------------------------------------------------------------
    # Waiting
    # ------------------------------------------------------------------

    def wait_for(self, selector: str, state: str = "visible") -> str:
        """Wait for an element to reach a given state. States: 'visible', 'hidden', 'attached', 'detached'."""
        result = self._request(
            "POST", "/wait-for", {"selector": selector, "state": state}
        )
        if result.get("success"):
            return f"Element '{selector}' reached state '{state}'."
        return f"Wait failed: {result.get('error', 'unknown error')}"

    # ------------------------------------------------------------------
    # Tab management
    # ------------------------------------------------------------------

    def get_tabs(self) -> str:
        """List all open browser tabs with their URLs and titles."""
        result = self._request("GET", "/tabs")
        if result.get("success"):
            data = result.get("data", {})
            tabs = data.get("tabs", [])
            if not tabs:
                return "No tabs open."
            lines = ["Open tabs:"]
            for tab in tabs:
                idx = tab.get("index", "?")
                url = tab.get("url", "about:blank")
                title = tab.get("title", "")
                lines.append(f"  {idx}. {title or '(no title)'} -- {url}")
            return "\n".join(lines)
        return f"Get tabs failed: {result.get('error', 'unknown error')}"

    def new_tab(self) -> str:
        """Open a new browser tab."""
        result = self._request("POST", "/tabs/new")
        if result.get("success"):
            data = result.get("data", {})
            index = data.get("index", "?")
            return f"Opened new tab (index: {index})"
        return f"New tab failed: {result.get('error', 'unknown error')}"

    def switch_tab(self, index: int) -> str:
        """Switch to a browser tab by index (0-based)."""
        result = self._request("POST", "/tabs/switch", {"index": index})
        if result.get("success"):
            return f"Switched to tab {index}."
        return f"Switch tab failed: {result.get('error', 'unknown error')}"

    def close_tab(self, index: int) -> str:
        """Close a browser tab by index (0-based)."""
        result = self._request("POST", "/tabs/close", {"index": index})
        if result.get("success"):
            return f"Closed tab {index}."
        return f"Close tab failed: {result.get('error', 'unknown error')}"

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def reset_browser(self) -> str:
        """Reset the browser to a clean state. Clears cookies, closes extra tabs, navigates to blank page."""
        result = self._request("POST", "/reset")
        if result.get("success"):
            return "Browser reset to clean state."
        return f"Reset failed: {result.get('error', 'unknown error')}"
