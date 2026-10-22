"""Browser Automation Service supporting isolated sessions, navigation, and DOM interaction.

Provides a clean adapter over Playwright with domain policy checks and fallback.
"""

from typing import Any

from app.core.exceptions import DependencyMissingError, SecurityPolicyError
from app.services.web_research_service import validate_public_url


class BrowserAutomationService:
    """Manages isolated browser sessions for navigation, form filling, and inspection."""

    _active_contexts: dict[str, Any] = {}
    _playwright_instance: Any = None
    _browser_instance: Any = None

    @classmethod
    async def _get_browser(cls):
        """Lazy-initialize headless Chromium browser."""
        if cls._browser_instance is not None:
            return cls._browser_instance

        try:
            from playwright.async_api import async_playwright

            cls._playwright_instance = await async_playwright().start()
            cls._browser_instance = await cls._playwright_instance.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
            )
            return cls._browser_instance
        except Exception as e:
            raise DependencyMissingError(
                f"Playwright browser engine could not start: {e}. "
                "Ensure Playwright browsers are installed via 'playwright install chromium'."
            )

    @classmethod
    async def get_or_create_page(cls, session_id: str = "default") -> Any:
        """Retrieve active page or create an isolated incognito browser context."""
        if session_id in cls._active_contexts:
            return cls._active_contexts[session_id]["page"]

        browser = await cls._get_browser()
        # Create an isolated context with no shared cookies/cache
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)",
            viewport={"width": 1280, "height": 800},
            ignore_https_errors=False,
        )
        page = await context.new_page()
        cls._active_contexts[session_id] = {"context": context, "page": page}
        return page

    @classmethod
    async def open_url(
        cls, url: str, session_id: str = "default", timeout_seconds: int = 30
    ) -> dict[str, Any]:
        """Navigate to a public URL inside an isolated browser session."""
        valid_url = validate_public_url(url)
        page = await cls.get_or_create_page(session_id)

        try:
            response = await page.goto(valid_url, timeout=timeout_seconds * 1000, wait_until="load")
            final_url = page.url
            # Re-verify final redirected URL against SSRF
            validate_public_url(final_url)

            title = await page.title()
            status = response.status if response else 200

            return {
                "success": True,
                "url": final_url,
                "title": title,
                "status": status,
                "session_id": session_id,
            }
        except Exception as e:
            raise SecurityPolicyError(f"Browser navigation failed: {e}")

    @classmethod
    async def read_page_content(cls, session_id: str = "default") -> dict[str, Any]:
        """Extract visible text and links from the current page."""
        if session_id not in cls._active_contexts:
            raise SecurityPolicyError(
                f"No active browser session '{session_id}'. Open a URL first."
            )

        page = cls._active_contexts[session_id]["page"]
        title = await page.title()
        url = page.url

        # Extract visible innerText
        body_text = await page.evaluate("() => document.body ? document.body.innerText : ''")

        # Extract links
        links = await page.evaluate("""() => {
            const anchors = Array.from(document.querySelectorAll('a[href]'));
            return anchors.slice(0, 30).map(a => ({
                href: a.href,
                text: a.innerText.trim().slice(0, 100)
            }));
        }""")

        return {
            "url": url,
            "title": title,
            "text": body_text[:10000],  # Bound text length for prompt safety
            "links": links,
        }

    @classmethod
    async def interact(
        cls,
        action: str,
        selector: str,
        value: str | None = None,
        session_id: str = "default",
    ) -> dict[str, Any]:
        """Interact with a validated DOM element (click, fill, select)."""
        if session_id not in cls._active_contexts:
            raise SecurityPolicyError(
                f"No active browser session '{session_id}'. Open a URL first."
            )

        page = cls._active_contexts[session_id]["page"]

        action_clean = action.lower().strip()
        if action_clean == "click":
            await page.click(selector, timeout=10000)
            return {"success": True, "action": "click", "selector": selector}
        elif action_clean == "fill":
            await page.fill(selector, value or "", timeout=10000)
            return {
                "success": True,
                "action": "fill",
                "selector": selector,
                "value_length": len(value or ""),
            }
        elif action_clean == "select":
            await page.select_option(selector, value or "", timeout=10000)
            return {"success": True, "action": "select", "selector": selector, "value": value}
        else:
            raise SecurityPolicyError(
                f"Unsupported browser action '{action}'. Supported: click, fill, select."
            )

    @classmethod
    async def take_snapshot(cls, session_id: str = "default") -> dict[str, Any]:
        """Capture page metadata and title for internal agent analysis."""
        if session_id not in cls._active_contexts:
            raise SecurityPolicyError(f"No active browser session '{session_id}'.")

        page = cls._active_contexts[session_id]["page"]
        return {
            "url": page.url,
            "title": await page.title(),
            "viewport": page.viewport_size,
        }

    @classmethod
    async def close_session(cls, session_id: str = "default") -> bool:
        """Close an active browser session."""
        if session_id in cls._active_contexts:
            ctx = cls._active_contexts.pop(session_id)
            try:
                await ctx["page"].close()
                await ctx["context"].close()
            except Exception:
                pass
            return True
        return False
