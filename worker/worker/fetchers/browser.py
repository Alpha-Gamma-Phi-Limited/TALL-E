from __future__ import annotations

from urllib.parse import urlparse


def _playwright_proxy(proxy_url: str) -> dict[str, str]:
    parsed = urlparse(proxy_url)
    if not parsed.scheme or not parsed.hostname:
        raise ValueError(f"Invalid proxy URL: {proxy_url}")

    server = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port:
        server = f"{server}:{parsed.port}"

    proxy: dict[str, str] = {"server": server}
    if parsed.username:
        proxy["username"] = parsed.username
    if parsed.password:
        proxy["password"] = parsed.password
    return proxy


def fetch_page_html(
    url: str,
    timeout_seconds: float = 30.0,
    user_agent: str | None = None,
    proxy_url: str | None = None,
) -> str:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - import path tested via integration
        raise RuntimeError("Playwright is unavailable in this runtime") from exc

    timeout_ms = int(max(1.0, timeout_seconds) * 1000)
    with sync_playwright() as playwright:
        launch_kwargs: dict[str, object] = {"headless": True}
        if proxy_url:
            launch_kwargs["proxy"] = _playwright_proxy(proxy_url)

        browser = playwright.chromium.launch(**launch_kwargs)
        try:
            context_kwargs: dict[str, object] = {}
            if user_agent:
                context_kwargs["user_agent"] = user_agent
            context = browser.new_context(**context_kwargs)
            try:
                page = context.new_page()
                last_timeout: Exception | None = None
                navigated = False
                for wait_until in ("domcontentloaded", "load", "commit"):
                    try:
                        page.goto(url, wait_until=wait_until, timeout=timeout_ms)
                        navigated = True
                        break
                    except PlaywrightTimeoutError as exc:
                        last_timeout = exc
                        continue
                if not navigated:
                    if last_timeout:
                        raise last_timeout
                    raise RuntimeError(f"Unable to navigate browser to {url}")
                try:
                    page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 8000))
                except Exception:
                    # Some sites keep long-polling; domcontentloaded is enough for parsing.
                    pass
                return page.content()
            finally:
                context.close()
        finally:
            browser.close()
