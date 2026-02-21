from __future__ import annotations

import logging

from worker.adapters.fixture_adapter import FixtureAdapter
from worker.adapters.live_base import LiveRetailerAdapter
from worker.fetchers.browser import fetch_page_html


logger = logging.getLogger(__name__)


class HarveyNormanFixtureAdapter(FixtureAdapter):
    retailer_slug = "harvey-norman"
    fixture_name = "harvey_norman.json"


class HarveyNormanLiveAdapter(LiveRetailerAdapter):
    retailer_slug = "harvey-norman"
    base_url = "https://www.harveynorman.co.nz"
    sitemap_seeds = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap_products_1.xml",
        "/sitemap_products.xml",
    ]
    include_url_patterns = [
        "/computers/",
        "/phone-and-gps/",
        "/tv-and-audio/",
        "/cameras/",
        "/gaming/",
    ]
    exclude_url_patterns = ["/gift-card", "/services", "/stores", "?", "#"]
    require_file_suffix = ".html"
    fallback_fixture_cls = HarveyNormanFixtureAdapter

    def __init__(
        self,
        max_products: int = 120,
        timeout_seconds: float = 15.0,
        request_delay_seconds: float = 0.0,
        max_fetch_retries: int = 2,
        retry_backoff_seconds: float = 0.6,
        use_fixture_fallback: bool = True,
        proxy_url: str | None = None,
        browser_fallback: bool = True,
        browser_timeout_seconds: float = 35.0,
        browser_proxy_url: str | None = None,
        vertical: str | None = None,
        include_url_patterns: list[str] | None = None,
    ) -> None:
        super().__init__(
            max_products=max_products,
            timeout_seconds=timeout_seconds,
            request_delay_seconds=request_delay_seconds,
            max_fetch_retries=max_fetch_retries,
            retry_backoff_seconds=retry_backoff_seconds,
            use_fixture_fallback=use_fixture_fallback,
            proxy_url=proxy_url,
            browser_fallback=browser_fallback,
            browser_timeout_seconds=browser_timeout_seconds,
            browser_proxy_url=browser_proxy_url,
            vertical=vertical,
            include_url_patterns=include_url_patterns,
        )

    def _fetch_text(self, url: str) -> str:
        try:
            return super()._fetch_text(url)
        except Exception as exc:
            if not self.browser_fallback:
                raise

            try:
                html = self._fetch_text_with_browser(url)
            except Exception:
                raise exc

            if self._looks_like_bot_challenge(html):
                raise exc
            return html

    def _fetch_text_with_browser(self, url: str) -> str:
        proxy_url = self.browser_proxy_url or self.proxy_url
        logger.info("Using browser fallback for Harvey Norman URL: %s", url)
        return fetch_page_html(
            url,
            timeout_seconds=self.browser_timeout_seconds,
            # Use Playwright's default Chromium UA for anti-bot compatibility.
            user_agent=None,
            proxy_url=proxy_url,
        )


class HarveyNormanHomeFixtureAdapter(FixtureAdapter):
    vertical = "home-appliances"
    retailer_slug = "harvey-norman"
    fixture_name = "harvey_norman_home.json"


class HarveyNormanHomeLiveAdapter(HarveyNormanLiveAdapter):
    vertical = "home-appliances"
    include_url_patterns = [
        "/whiteware/",
        "/kitchen-appliances/",
        "/vacuum-and-floorcare/",
        "/heating-cooling-and-air-quality/",
    ]
    fallback_fixture_cls = HarveyNormanHomeFixtureAdapter
