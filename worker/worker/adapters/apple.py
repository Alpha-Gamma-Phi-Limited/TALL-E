import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from worker.adapters.fixture_adapter import FixtureAdapter
from worker.adapters.live_base import LiveRetailerAdapter


class AppleFixtureAdapter(FixtureAdapter):
    retailer_slug = "apple"
    fixture_name = "apple.json"


class AppleLiveAdapter(LiveRetailerAdapter):
    retailer_slug = "apple"
    base_url = "https://www.apple.com/nz"
    sitemap_seeds = [
        "/nz/sitemap.xml",
        "/sitemap.xml",
    ]
    include_url_patterns = ["/shop/buy-", "/shop/product/"]
    exclude_url_patterns = [
        "/support",
        "/newsroom",
        "/legal",
        "/feedback/",
        "/compare/",
        "/iphone/battery",
        "/iphone/cellular",
        "/ipad/cellular",
        "?",
        "#",
    ]
    fallback_fixture_cls = AppleFixtureAdapter

    _GENERIC_BUY_LEAVES = {"iphone", "ipad", "mac", "watch", "airpods", "vision-pro", "apple-vision-pro"}
    _GENERIC_PAGE_MARKERS = (
        "buying iphone",
        "buying ipad",
        "buying mac",
        "compare models",
        "compare all models",
    )
    _MODEL_HINT_TOKENS = (
        "iphone",
        "ipad",
        "macbook",
        "imac",
        "mac-mini",
        "mac-studio",
        "watch",
        "airpods",
        "vision",
        "pro",
        "max",
        "ultra",
        "mini",
    )
    _GENERIC_TITLE_RE = re.compile(r"^\s*(iphone|ipad|mac)\s*[-|].*$", re.I)

    def _is_candidate_product_url(self, url: str) -> bool:
        if not super()._is_candidate_product_url(url):
            return False

        parsed = urlparse(url)
        path = parsed.path.lower().rstrip("/")
        segments = [segment for segment in path.split("/") if segment]

        if "/shop/product/" in path:
            return True
        if "/shop/buy-" not in path:
            return False

        buy_idx = next((idx for idx, segment in enumerate(segments) if segment.startswith("buy-")), None)
        if buy_idx is None or buy_idx + 1 >= len(segments):
            return False

        model_leaf = segments[buy_idx + 1]
        if model_leaf in self._GENERIC_BUY_LEAVES:
            return False
        if model_leaf in {"compare", "carrier-offers", "switch", "for-business"}:
            return False

        if any(token in model_leaf for token in self._MODEL_HINT_TOKENS):
            return True
        return bool(re.fullmatch(r"[a-z0-9-]{6,}", model_leaf))

    def _is_non_product_page(self, url: str, title: str, soup: BeautifulSoup, product_obj: dict[str, object]) -> bool:
        if super()._is_non_product_page(url=url, title=title, soup=soup, product_obj=product_obj):
            return True

        parsed = urlparse(url)
        path = parsed.path.lower().rstrip("/")
        lowered_title = title.lower()
        title_text = f"{title} {soup.get_text(' ', strip=True)[:160]}".lower()

        if re.search(r"/shop/buy-(iphone|ipad|mac|watch|airpods|vision)(?:/)?$", path):
            return True
        if path in {"/iphone", "/ipad", "/mac"}:
            return True
        if any(marker in title_text for marker in self._GENERIC_PAGE_MARKERS):
            return True
        if self._GENERIC_TITLE_RE.match(title) and "pro" not in lowered_title and "max" not in lowered_title:
            return True
        return False
