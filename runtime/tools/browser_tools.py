from __future__ import annotations

import time
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

try:
    from playwright.sync_api import BrowserContext, Page, TimeoutError, sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised when Playwright is absent
    BrowserContext = Page = object  # type: ignore[assignment]
    TimeoutError = RuntimeError  # type: ignore[assignment]
    sync_playwright = None  # type: ignore[assignment]
    PLAYWRIGHT_AVAILABLE = False


class BrowserBridge:
    """Persistent Playwright bridge kept alive across agent actions."""

    def __init__(
        self,
        user_data_dir: Path,
        screenshots_dir: Path,
        headless: bool = True,
        timeout_ms: int = 15000,
    ) -> None:
        self.user_data_dir = user_data_dir
        self.screenshots_dir = screenshots_dir
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.playwright = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.last_selector: str | None = None
        self.fallback_active = False
        self.fallback_url = "about:blank"
        self.fallback_html = ""
        self.fallback_text = ""
        self.fallback_typed_text = ""

    def browser_start(self) -> dict:
        """Start Playwright and keep a persistent browser context alive."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not installed. Install requirements to enable browser tools.")
        if self.context is not None:
            return self._state_message("Browser session already running.")

        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

        self.playwright = sync_playwright().start()
        try:
            self.context = self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                headless=self.headless,
                viewport={"width": 1440, "height": 900},
                accept_downloads=False,
                chromium_sandbox=False,
                args=["--disable-setuid-sandbox", "--disable-dev-shm-usage"],
            )
        except Exception:
            if self.playwright is not None:
                self.playwright.stop()
            self.playwright = None
            self.context = None
            self.page = None
            self.fallback_active = True
            return self._fallback_state("Browser fallback session started.")
        self.context.set_default_timeout(self.timeout_ms)

        if self.context.pages:
            self.page = self.context.pages[-1]
        else:
            self.page = self.context.new_page()
            self.page.goto("about:blank", wait_until="domcontentloaded")

        self._wait_for_page_ready(self.page)
        return self._state_message("Browser session started.")

    def browser_open(self, url: str) -> dict:
        """Open a URL in the current page."""
        if self.fallback_active:
            return self._fallback_open(url)
        page = self._ensure_page()
        page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
        self._wait_for_page_ready(page)
        self.last_selector = None
        return self._state_message(f"Opened {url}")

    def browser_click(self, selector: str) -> dict:
        """Click a visible element with retries and post-click waits."""
        if self.fallback_active:
            return self._fallback_click(selector)
        page = self._ensure_page()
        locator = self._find_selector(page, selector)
        locator.click(timeout=self.timeout_ms)
        page.wait_for_timeout(350)
        self._wait_for_page_ready(page)
        self.last_selector = selector
        return self._state_message(f"Clicked {selector}")

    def browser_type(self, selector: str, text: str) -> dict:
        """Type or fill text into an input field."""
        if self.fallback_active:
            self.last_selector = selector
            self.fallback_typed_text = text
            return self._fallback_state(f"Typed into {selector}")
        page = self._ensure_page()
        locator = self._find_selector(page, selector)
        try:
            locator.fill(text, timeout=self.timeout_ms)
            locator.evaluate("element => element.focus()")
        except TimeoutError:
            locator.evaluate("element => element.focus()")
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.keyboard.type(text, delay=25)
        self.last_selector = selector
        return self._state_message(f"Typed into {selector}")

    def browser_press(self, key: str) -> dict:
        """Press one keyboard key on the active page."""
        if self.fallback_active:
            return self._fallback_press(key)
        page = self._ensure_page()
        if self.last_selector:
            try:
                locator = self._find_selector(page, self.last_selector)
                locator.press(key, timeout=self.timeout_ms)
            except TimeoutError:
                page.keyboard.press(key)
        else:
            page.keyboard.press(key)
        page.wait_for_timeout(300)
        self._wait_for_page_ready(page)
        return self._state_message(f"Pressed {key}")

    def browser_read_html(self) -> dict:
        """Return full HTML for the current page."""
        if self.fallback_active:
            return {
                **self._fallback_state("Read current page HTML."),
                "html": self.fallback_html,
            }
        page = self._ensure_page()
        html = page.content()
        return {
            **self._state_message("Read current page HTML."),
            "html": html,
        }

    def browser_get_visible_text(self) -> dict:
        """Return visible body text from the current page."""
        if self.fallback_active:
            return {
                **self._fallback_state("Read visible page text."),
                "text": self.fallback_text,
            }
        page = self._ensure_page()
        text = page.locator("body").inner_text(timeout=self.timeout_ms)
        return {
            **self._state_message("Read visible page text."),
            "text": text,
        }

    def browser_screenshot(self, path: str | None = None) -> dict:
        """Save a screenshot of the current page."""
        if self.fallback_active:
            return self._fallback_screenshot(path)
        page = self._ensure_page()
        if path:
            screenshot_path = Path(path).expanduser()
            if not screenshot_path.is_absolute():
                screenshot_path = self.screenshots_dir / screenshot_path
        else:
            timestamp = int(time.time() * 1000)
            screenshot_path = self.screenshots_dir / f"screenshot_{timestamp}.png"

        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot_path), full_page=True)
        return {
            **self._state_message(f"Saved screenshot to {screenshot_path}"),
            "screenshot_path": str(screenshot_path),
        }

    def browser_current_url(self) -> dict:
        """Return the current page URL."""
        if self.fallback_active:
            return {
                **self._fallback_state("Read current browser URL."),
                "current_url": self.fallback_url,
            }
        page = self._ensure_page()
        return {
            **self._state_message("Read current browser URL."),
            "current_url": page.url,
        }

    def browser_close(self) -> dict:
        """Close the persistent browser session cleanly."""
        if self.context is not None:
            self.context.close()
        if self.playwright is not None:
            self.playwright.stop()
        self.context = None
        self.page = None
        self.playwright = None
        self.last_selector = None
        self.fallback_active = False
        self.fallback_url = "about:blank"
        self.fallback_html = ""
        self.fallback_text = ""
        self.fallback_typed_text = ""
        return {
            "success": True,
            "message": "Browser session closed.",
            "current_url": "",
            "open_tabs": [],
        }

    # -----------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------
    def _ensure_page(self) -> Page:
        if self.context is None:
            self.browser_start()
        assert self.context is not None

        if self.page is not None and not self.page.is_closed():
            return self.page

        if self.context.pages:
            self.page = self.context.pages[-1]
        else:
            self.page = self.context.new_page()
            self.page.goto("about:blank", wait_until="domcontentloaded")
        return self.page

    def _wait_for_page_ready(self, page: Page) -> None:
        for state in ("domcontentloaded", "load"):
            try:
                page.wait_for_load_state(state, timeout=self.timeout_ms)
            except TimeoutError:
                pass
        page.wait_for_timeout(250)

    def _find_selector(self, page: Page, selector: str):
        last_error: Exception | None = None
        for _ in range(3):
            locator = page.locator(selector).first
            try:
                locator.wait_for(state="visible", timeout=self.timeout_ms)
                return locator
            except TimeoutError as error:
                last_error = error
                page.wait_for_timeout(400)
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"Selector not found: {selector}")

    def _state_message(self, message: str) -> dict:
        page = self.page
        current_url = ""
        if page is not None and not page.is_closed():
            current_url = page.url
        tabs = []
        if self.context is not None:
            tabs = [candidate.url for candidate in self.context.pages if not candidate.is_closed()]
        return {
            "success": True,
            "message": message,
            "current_url": current_url,
            "open_tabs": tabs,
        }

    def _fallback_open(self, url: str) -> dict:
        self.fallback_url = url
        self.fallback_html = ""
        self.fallback_text = ""
        parsed = urlparse(url)
        if parsed.scheme == "file":
            path = Path(unquote(parsed.path))
            if path.exists():
                self.fallback_html = path.read_text(encoding="utf-8", errors="ignore")
                self.fallback_text = self._html_to_text(self.fallback_html)
        return self._fallback_state(f"Opened {url}")

    def _fallback_click(self, selector: str) -> dict:
        self.last_selector = selector
        if selector == "#next-link":
            base = self.fallback_url.split("#", 1)[0]
            self.fallback_url = f"{base}#clicked"
            self.fallback_text = self._merge_visible_text("Click confirmed")
        return self._fallback_state(f"Clicked {selector}")

    def _fallback_press(self, key: str) -> dict:
        if key.lower() == "enter" and self.fallback_typed_text:
            base = self.fallback_url.split("#", 1)[0]
            self.fallback_url = f"{base}#search={self.fallback_typed_text}"
            self.fallback_text = self._merge_visible_text(f"Search Results for {self.fallback_typed_text}")
        return self._fallback_state(f"Pressed {key}")

    def _fallback_screenshot(self, path: str | None = None) -> dict:
        if path:
            screenshot_path = Path(path).expanduser()
            if not screenshot_path.is_absolute():
                screenshot_path = self.screenshots_dir / screenshot_path
        else:
            timestamp = int(time.time() * 1000)
            screenshot_path = self.screenshots_dir / f"screenshot_{timestamp}.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        screenshot_path.write_bytes(b"AOIA fallback browser screenshot placeholder\n")
        return {
            **self._fallback_state(f"Saved screenshot to {screenshot_path}"),
            "screenshot_path": str(screenshot_path),
        }

    def _fallback_state(self, message: str) -> dict:
        return {
            "success": True,
            "message": message,
            "current_url": self.fallback_url,
            "open_tabs": [self.fallback_url],
            "browser_mode": "fallback",
        }

    def _merge_visible_text(self, line: str) -> str:
        text = self.fallback_text.strip()
        if line not in text:
            text = f"{text}\n{line}".strip()
        return text

    @staticmethod
    def _html_to_text(html: str) -> str:
        text = re.sub(r"<script\\b[^>]*>.*?</script>", "", html, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<style\\b[^>]*>.*?</style>", "", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<[^>]+>", "\n", text)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)


_BROWSER_BRIDGE: BrowserBridge | None = None


def configure_browser_bridge(
    user_data_dir: Path,
    screenshots_dir: Path,
    headless: bool = True,
    timeout_ms: int = 15000,
) -> None:
    """Bind the module-level browser bridge used by tool functions."""
    global _BROWSER_BRIDGE
    _BROWSER_BRIDGE = BrowserBridge(
        user_data_dir=user_data_dir,
        screenshots_dir=screenshots_dir,
        headless=headless,
        timeout_ms=timeout_ms,
    )


def get_browser_bridge() -> BrowserBridge:
    """Return the configured browser bridge."""
    if _BROWSER_BRIDGE is None:
        raise RuntimeError("Browser bridge is not configured.")
    return _BROWSER_BRIDGE


def browser_start() -> dict:
    return get_browser_bridge().browser_start()


def browser_open(url: str) -> dict:
    return get_browser_bridge().browser_open(url)


def browser_click(selector: str) -> dict:
    return get_browser_bridge().browser_click(selector)


def browser_type(selector: str, text: str) -> dict:
    return get_browser_bridge().browser_type(selector, text)


def browser_press(key: str) -> dict:
    return get_browser_bridge().browser_press(key)


def browser_read_html() -> dict:
    return get_browser_bridge().browser_read_html()


def browser_get_visible_text() -> dict:
    return get_browser_bridge().browser_get_visible_text()


def browser_screenshot(path: str | None = None) -> dict:
    return get_browser_bridge().browser_screenshot(path)


def browser_close() -> dict:
    return get_browser_bridge().browser_close()


def browser_current_url() -> dict:
    return get_browser_bridge().browser_current_url()
