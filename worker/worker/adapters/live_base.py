from __future__ import annotations

import gzip
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup

from worker.adapters.base import NormalizedRetailerProduct, RawDetail, RawListing, SourceAdapter
from worker.adapters.fixture_adapter import FixtureAdapter
from worker.matching.normalization import normalize_identifier


PRICE_RE = re.compile(r"(?:NZD|NZ\$|\$)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", re.I)
PRICE_CONTEXT_RE = re.compile(
    r"(?:was|now|price|sale|special|our\s+price|from|only)\s*[:\-]?\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
    re.I,
)
SCRIPT_IMAGE_RE = re.compile(r'https?://[^"\']+\.(?:jpg|jpeg|png|webp)(?:\?[^"\']*)?', re.I)
RETRYABLE_HTTP_STATUSES = {403, 408, 425, 429, 500, 502, 503, 504}
RX_EXCLUSION_TOKENS = {
    "prescription",
    "pharmacist only",
    "pharmacy only medicine",
    "schedule 4",
    "s4",
    "rx",
}
PHARMA_ALLOWED_CATEGORIES = {"otc", "supplements"}
VERTICAL_FALLBACK_CATEGORIES = {
    "beauty": "beauty",
    "pharma": "other-pharma",
    "pharmaceuticals": "other-pharma",
    "tech": "electronics",
    "home-appliances": "appliances",
    "pet-goods": "pet-supplies",
}
VERTICAL_SIGNAL_TOKENS: dict[str, tuple[str, ...]] = {
    "home-appliances": (
        "whiteware",
        "appliance",
        "fridge",
        "refrigerator",
        "freezer",
        "dishwasher",
        "washing machine",
        "washer",
        "dryer",
        "laundry",
        "microwave",
        "vacuum",
        "air fryer",
        "coffee machine",
        "air conditioner",
        "dehumidifier",
    ),
    "beauty": (
        "beauty",
        "skincare",
        "skin care",
        "makeup",
        "cosmetic",
        "fragrance",
        "perfume",
        "parfum",
        "lipstick",
        "mascara",
        "serum",
        "cleanser",
        "moisturizer",
        "moisturiser",
        "sunscreen",
        "spf",
        "shampoo",
    ),
    "pet-goods": (
        "pet",
        "kitten",
        "puppy",
        "pet food",
        "dog food",
        "cat food",
        "kibble",
        "litter",
        "flea",
        "tick",
        "worming",
        "grooming",
        "pet shampoo",
        "pet treats",
        "dog treats",
        "cat treats",
        "pet toy",
        "dog toy",
        "cat toy",
        "pet bed",
    ),
    "pharma": (
        "pharma",
        "pharmacy",
        "medicine",
        "medication",
        "tablet",
        "caplet",
        "capsule",
        "otc",
        "supplement",
        "vitamin",
        "probiotic",
        "pain relief",
        "ibuprofen",
        "paracetamol",
    ),
    "tech": (
        "electronics",
        "electronic",
        "laptop",
        "notebook",
        "macbook",
        "smartphone",
        "iphone",
        "android",
        "monitor",
        "gaming",
        "camera",
        "headphone",
        "printer",
        "router",
        "ssd",
        "gpu",
    ),
}
VERTICAL_SIGNAL_PRIORITY = ("home-appliances", "beauty", "pet-goods", "pharma", "tech")
BEAUTY_CATEGORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "suncare",
        (
            "sunscreen",
            "sun screen",
            "sunblock",
            "spf",
            "uv",
        ),
    ),
    (
        "skincare",
        (
            "serum",
            "cleanser",
            "moisturiser",
            "moisturizer",
            "toner",
            "essence",
            "retinol",
            "niacinamide",
            "hyaluronic",
            "exfoliant",
            "mask",
            "eye cream",
            "face cream",
        ),
    ),
    (
        "makeup",
        (
            "foundation",
            "concealer",
            "powder",
            "lipstick",
            "lip gloss",
            "lip balm",
            "mascara",
            "eyeliner",
            "eyeshadow",
            "blush",
            "bronzer",
            "highlighter",
            "primer",
            "brow",
        ),
    ),
    (
        "haircare",
        (
            "shampoo",
            "conditioner",
            "hair mask",
            "hair oil",
            "haircare",
            "hair care",
            "scalp",
            "hairspray",
            "hair spray",
            "leave-in",
        ),
    ),
    (
        "fragrance",
        (
            "perfume",
            "parfum",
            "fragrance",
            "eau de",
            "cologne",
            "aftershave",
            "body mist",
        ),
    ),
    (
        "bodycare",
        (
            "body wash",
            "body lotion",
            "body cream",
            "hand cream",
            "deodorant",
            "soap",
            "bath",
        ),
    ),
    (
        "beauty-tools",
        (
            "brush",
            "sponge",
            "applicator",
            "curler",
            "tweezer",
            "beauty tool",
            "roller",
        ),
    ),
)
BEAUTY_PRODUCT_TYPE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("serum", ("serum",)),
    ("cleanser", ("cleanser", "face wash")),
    ("moisturizer", ("moisturiser", "moisturizer", "face cream")),
    ("toner", ("toner",)),
    ("essence", ("essence",)),
    ("mask", ("mask", "sheet mask")),
    ("foundation", ("foundation",)),
    ("concealer", ("concealer",)),
    ("powder", ("powder", "setting powder")),
    ("lipstick", ("lipstick",)),
    ("lip_gloss", ("lip gloss", "luminizer", "lip oil")),
    ("mascara", ("mascara",)),
    ("eyeliner", ("eyeliner",)),
    ("eyeshadow", ("eyeshadow",)),
    ("shampoo", ("shampoo",)),
    ("conditioner", ("conditioner",)),
    ("perfume", ("perfume", "parfum", "eau de", "fragrance")),
    ("sunscreen", ("sunscreen", "sun screen", "sunblock", "spf")),
)
BEAUTY_SKIN_TYPES: tuple[str, ...] = ("dry", "oily", "combination", "normal", "sensitive", "mature")
BEAUTY_CONCERN_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("hydration", ("hydrating", "hydrate", "dehydrated", "dry skin", "moisturizing", "moisturising")),
    ("acne", ("acne", "blemish", "breakout", "oil-control", "oil control")),
    ("brightening", ("brightening", "dark spot", "pigmentation", "radiance", "dullness")),
    ("anti-aging", ("anti-aging", "anti age", "wrinkle", "fine lines", "firming", "retinol")),
    ("soothing", ("soothing", "calming", "redness", "sensitive")),
)
BEAUTY_FINISHES: tuple[str, ...] = ("matte", "dewy", "satin", "natural", "radiant", "glow", "shimmer")
WAF_BLOCKED_STATUSES = {401, 403, 429}
IMAGE_EXCLUDE_TOKENS = {
    "logo",
    "icon",
    "sprite",
    "banner",
    "loading",
    "noimage",
    "placeholder",
    "addtocart",
    "greentick",
    "redcross",
    "arrow",
}
IMAGE_INCLUDE_TOKENS = {"product", "hero", "main", "gallery", "/product/", "/products/", "/media/pi/", "/pi/"}
MISSING_PAGE_MARKERS = (
    "we can't find this page",
    "page not found",
    "404",
    "error 404",
    "sorry, this page cannot be found",
)

logger = logging.getLogger(__name__)


@dataclass
class ParsedProductPage:
    source_product_id: str
    url: str
    title: str
    image_url: str | None
    brand: str
    category: str
    availability: str | None
    gtin: str | None
    mpn: str | None
    model_number: str | None
    attributes: dict[str, object]
    price_nzd: float
    promo_price_nzd: float | None
    promo_text: str | None
    discount_pct: float | None
    normalized_category: str = ""
    category_source: str = "fallback"


@dataclass(frozen=True)
class VerticalInference:
    vertical: str
    source: str
    confidence: float


class NonProductPageError(ValueError):
    pass


class LiveRetailerAdapter(SourceAdapter):
    vertical: str = "tech"
    retailer_slug: str
    base_url: str
    sitemap_seeds: list[str]
    include_url_patterns: list[str]
    exclude_url_patterns: list[str] = ["/blog", "/news", "/support", "/stores", "?", "#"]
    require_file_suffix: str | None = None
    fallback_fixture_cls: type[FixtureAdapter] | None = None

    def __init__(
        self,
        max_products: int = 120,
        timeout_seconds: float = 15.0,
        request_delay_seconds: float = 0.0,
        max_fetch_retries: int = 2,
        retry_backoff_seconds: float = 0.6,
        use_fixture_fallback: bool = True,
        proxy_url: str | None = None,
        browser_fallback: bool = False,
        browser_timeout_seconds: float = 30.0,
        browser_proxy_url: str | None = None,
        vertical: str | None = None,
        include_url_patterns: list[str] | None = None,
    ) -> None:
        self.max_products = max_products
        self.request_delay_seconds = request_delay_seconds
        self.max_fetch_retries = max(0, max_fetch_retries)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)
        self.use_fixture_fallback = use_fixture_fallback
        self.proxy_url = proxy_url
        self.browser_fallback = browser_fallback
        self.browser_timeout_seconds = max(5.0, browser_timeout_seconds)
        self.browser_proxy_url = browser_proxy_url
        if vertical:
            self.vertical = vertical
        if include_url_patterns:
            self.include_url_patterns = include_url_patterns
        self.used_fixture_fallback = False
        self.discovery_failure_reason: str | None = None
        self._page_cache: dict[str, ParsedProductPage] = {}
        self._last_request_at: float | None = None
        self.client = httpx.Client(
            timeout=timeout_seconds,
            headers={
                "User-Agent": (
                    "WorthItBot/1.0 (+https://worthit.tech; "
                    "research-price-comparison; contact=ops@worthit.tech)"
                )
            },
            follow_redirects=True,
            proxy=proxy_url,
        )
        self._fixture_fallback = self.fallback_fixture_cls() if (use_fixture_fallback and self.fallback_fixture_cls) else None

    def list_pages(self) -> list[dict[str, object]]:
        urls = self._discover_product_urls()
        if urls:
            live_ok, reason = self._probe_live_urls(urls)
            if not live_ok:
                self.discovery_failure_reason = reason
                if self._fixture_fallback:
                    self.used_fixture_fallback = True
                    return self._fixture_fallback.list_pages()
                detail = f": {reason}" if reason else ""
                raise RuntimeError(f"Live probe failed for {self.retailer_slug}{detail}")
            return [{"url": url, "source_product_id": self._source_id_from_url(url)} for url in urls[: self.max_products]]

        if self._fixture_fallback:
            self.used_fixture_fallback = True
            return self._fixture_fallback.list_pages()

        reason = f" ({self.discovery_failure_reason})" if self.discovery_failure_reason else ""
        raise RuntimeError(f"No product URLs discovered for {self.retailer_slug}{reason}")

    def _probe_live_urls(self, urls: list[str]) -> tuple[bool, str | None]:
        max_probe_count = min(len(urls), 15)
        sample_urls = urls[:max_probe_count]
        if not sample_urls:
            return False, "no live product URLs discovered"

        success = 0
        blocked = 0
        price_failures = 0
        parse_failures = 0
        successful_urls: list[str] = []

        for url in sample_urls:
            try:
                html = self._fetch_text(url)
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status in WAF_BLOCKED_STATUSES:
                    blocked += 1
                continue
            except RuntimeError as exc:
                if "anti-bot challenge" in str(exc).lower():
                    blocked += 1
                continue
            except Exception:
                continue

            if self._looks_like_bot_challenge(html):
                blocked += 1
                continue

            soup = BeautifulSoup(html, "html.parser")
            if self._looks_like_missing_page(soup):
                parse_failures += 1
                continue

            ld_product = self._extract_json_ld_product(soup)
            price_nzd, _ = self._extract_prices(ld_product, soup)
            if price_nzd <= 0:
                price_failures += 1
                continue

            success += 1
            successful_urls.append(url)
            if success >= 2:
                break

        if success > 0:
            self._prioritize_urls(urls, successful_urls)
            return True, None
        if blocked > 0:
            return False, "live product pages blocked by anti-bot/WAF"
        if price_failures > 0:
            return False, "live product pages reachable but price extraction failed"
        if parse_failures > 0:
            return False, "live product pages resolved to non-product/error pages"
        return False, "live product pages were not parseable"

    def _prioritize_urls(self, urls: list[str], preferred_urls: list[str]) -> None:
        preferred = [url for url in preferred_urls if url in urls]
        if not preferred:
            return
        remainder = [url for url in urls if url not in preferred]
        urls[:] = [*preferred, *remainder]

    def _is_pharma_vertical(self) -> bool:
        return self._is_pharma_vertical_name(self.vertical)

    @staticmethod
    def _is_pharma_vertical_name(vertical: str) -> bool:
        return vertical in {"pharma", "pharmaceuticals"}

    def parse_listing(self, page: dict[str, object]) -> list[RawListing]:
        if "items" in page and self._fixture_fallback:
            return self._fixture_fallback.parse_listing(page)

        url = str(page["url"])
        source_product_id = str(page["source_product_id"])
        try:
            parsed = self._parse_product_page(url=url, source_product_id=source_product_id)
        except NonProductPageError:
            return []
        self._page_cache[source_product_id] = parsed
        parsed_category = parsed.normalized_category or self._normalize_category(parsed.category, parsed.title, self.vertical)
        if self._is_pharma_vertical() and parsed_category not in PHARMA_ALLOWED_CATEGORIES:
            return []

        return [
            RawListing(
                source_product_id=parsed.source_product_id,
                title=parsed.title,
                url=parsed.url,
                image_url=parsed.image_url,
                category=parsed.category,
                brand=parsed.brand,
                availability=parsed.availability,
                category_source=parsed.category_source,
            )
        ]

    def fetch_detail(self, listing: RawListing) -> RawDetail:
        if listing.source_product_id in self._page_cache:
            parsed = self._page_cache[listing.source_product_id]
            return self._to_raw_detail(parsed)

        if self._fixture_fallback:
            try:
                self.used_fixture_fallback = True
                return self._fixture_fallback.fetch_detail(listing)
            except Exception:
                pass

        parsed = self._parse_product_page(url=listing.url, source_product_id=listing.source_product_id)
        self._page_cache[listing.source_product_id] = parsed
        return self._to_raw_detail(parsed)

    def normalize(self, listing: RawListing, detail: RawDetail) -> NormalizedRetailerProduct:
        vertical_inference = self._infer_vertical(listing, detail)
        model_number = normalize_identifier(detail.model_number)
        gtin = normalize_identifier(detail.gtin)
        mpn = normalize_identifier(detail.mpn)

        merged_attributes = dict(detail.attributes)
        if self._is_pharma_vertical_name(vertical_inference.vertical):
            for key, value in self._derive_pharma_attributes(listing.title).items():
                merged_attributes.setdefault(key, value)
        if vertical_inference.vertical == "beauty":
            for key, value in self._derive_beauty_attributes(listing.title, listing.category, merged_attributes).items():
                merged_attributes.setdefault(key, value)
        if vertical_inference.vertical == "home-appliances":
            for key, value in self._derive_home_appliances_attributes(listing.title, merged_attributes).items():
                merged_attributes.setdefault(key, value)
        if model_number:
            merged_attributes.setdefault("model_number", model_number)

        return NormalizedRetailerProduct(
            vertical=vertical_inference.vertical,
            source_product_id=listing.source_product_id,
            title=listing.title.strip(),
            url=listing.url,
            image_url=listing.image_url,
            canonical_name=listing.title.strip(),
            brand=listing.brand.strip(),
            category=self._normalize_category(listing.category, listing.title, vertical_inference.vertical),
            model_number=model_number,
            gtin=gtin,
            mpn=mpn,
            attributes=merged_attributes,
            raw_attributes=detail.attributes,
            availability=listing.availability,
            price_nzd=detail.price_nzd,
            promo_price_nzd=detail.promo_price_nzd,
            promo_text=detail.promo_text,
            discount_pct=detail.discount_pct,
            captured_at=detail.captured_at,
            vertical_source=vertical_inference.source,
            vertical_confidence=vertical_inference.confidence,
        )

    def _infer_vertical(self, listing: RawListing, detail: RawDetail) -> VerticalInference:
        category_signal = self._infer_vertical_from_text(listing.category)
        if category_signal:
            category_source = listing.category_source or "structured_category"
            if category_source in {"json_ld", "breadcrumb", "structured_category"}:
                confidence = 0.96
            elif category_source == "fallback":
                confidence = 0.72
            else:
                confidence = 0.86
            return VerticalInference(vertical=category_signal, source=category_source, confidence=confidence)

        url_signal = self._infer_vertical_from_text(urlparse(listing.url).path.replace("-", " ").replace("/", " "))
        if url_signal:
            return VerticalInference(vertical=url_signal, source="url_path", confidence=0.88)

        attribute_text = self._attributes_to_text(detail.attributes)
        title_signal = self._infer_vertical_from_text(f"{listing.title} {attribute_text}")
        if title_signal:
            return VerticalInference(vertical=title_signal, source="title_attributes", confidence=0.8)

        return VerticalInference(vertical=self.vertical, source="adapter_default", confidence=0.55)

    def _infer_vertical_from_text(self, text: str) -> str | None:
        if not text:
            return None
        lowered = text.lower()
        scores = {vertical: 0 for vertical in VERTICAL_SIGNAL_TOKENS}
        for vertical, tokens in VERTICAL_SIGNAL_TOKENS.items():
            for token in tokens:
                if token in lowered:
                    scores[vertical] += 1

        best_vertical = None
        best_score = 0
        for vertical in VERTICAL_SIGNAL_PRIORITY:
            score = scores.get(vertical, 0)
            if score > best_score:
                best_vertical = vertical
                best_score = score

        if best_score <= 0:
            return None
        return best_vertical

    def _attributes_to_text(self, attributes: dict[str, object]) -> str:
        chunks: list[str] = []
        for key, value in (attributes or {}).items():
            chunks.append(str(key))
            if isinstance(value, dict):
                chunks.extend(str(child_value) for child_value in value.values())
            elif isinstance(value, (list, tuple, set)):
                chunks.extend(str(item) for item in value)
            else:
                chunks.append(str(value))
        return " ".join(chunks)

    def _to_raw_detail(self, parsed: ParsedProductPage) -> RawDetail:
        return RawDetail(
            gtin=parsed.gtin,
            mpn=parsed.mpn,
            model_number=parsed.model_number,
            attributes=parsed.attributes,
            price_nzd=parsed.price_nzd,
            promo_price_nzd=parsed.promo_price_nzd,
            promo_text=parsed.promo_text,
            discount_pct=parsed.discount_pct,
            captured_at=datetime.now(timezone.utc),
        )

    def _discover_product_urls(self) -> list[str]:
        self.discovery_failure_reason = None
        queue = [urljoin(self.base_url, seed) for seed in self.sitemap_seeds]
        queue.extend(self._discover_robots_sitemaps())
        seen_sitemaps: set[str] = set()
        found: list[str] = []
        saw_429 = False
        saw_404 = False

        while queue and len(found) < self.max_products * 4:
            sitemap_url = queue.pop(0)
            if sitemap_url in seen_sitemaps:
                continue
            seen_sitemaps.add(sitemap_url)

            try:
                xml_text = self._fetch_sitemap_text(sitemap_url)
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status == 429:
                    saw_429 = True
                if status == 404:
                    saw_404 = True
                logger.debug("Skipping sitemap %s for %s with status %s", sitemap_url, self.retailer_slug, status)
                continue
            except Exception as exc:
                logger.debug("Skipping sitemap %s for %s: %s", sitemap_url, self.retailer_slug, exc)
                continue

            child_sitemaps, urls = self._parse_sitemap(xml_text)
            for child in child_sitemaps:
                if child not in seen_sitemaps:
                    queue.append(child)
            for url in urls:
                if self._is_candidate_product_url(url):
                    found.append(url)

        deduped: list[str] = []
        seen_urls: set[str] = set()
        discovery_pool_limit = max(self.max_products, 40)
        for url in found:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            deduped.append(url)
            if len(deduped) >= discovery_pool_limit:
                break
        if deduped:
            return deduped

        html_urls = self._discover_product_urls_from_html()
        if html_urls:
            return html_urls

        if saw_429:
            self.discovery_failure_reason = "source returned HTTP 429 anti-bot challenges"
        elif saw_404:
            self.discovery_failure_reason = "configured sitemap endpoints returned HTTP 404"
        else:
            self.discovery_failure_reason = "no sitemap or homepage product links were discoverable"
        return []

    def _discover_robots_sitemaps(self) -> list[str]:
        robots_url = urljoin(self.base_url, "/robots.txt")
        try:
            robots_text = self._fetch_text(robots_url)
        except Exception:
            return []

        discovered: list[str] = []
        for line in robots_text.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            if key.strip().lower() != "sitemap":
                continue
            sitemap_url = value.strip()
            if sitemap_url:
                discovered.append(sitemap_url)
        return discovered

    def _parse_sitemap(self, xml_text: str) -> tuple[list[str], list[str]]:
        try:
            root = ElementTree.fromstring(xml_text.lstrip())
        except ElementTree.ParseError:
            return [], []

        def local_name(tag: str) -> str:
            return tag.rsplit("}", 1)[-1]

        child_sitemaps: list[str] = []
        urls: list[str] = []
        root_name = local_name(root.tag)
        if root_name == "sitemapindex":
            for sitemap in root.findall(".//{*}sitemap"):
                loc = sitemap.find("{*}loc")
                if loc is not None and loc.text:
                    child_sitemaps.append(loc.text.strip())
        elif root_name == "urlset":
            for url in root.findall(".//{*}url"):
                loc = url.find("{*}loc")
                if loc is not None and loc.text:
                    urls.append(loc.text.strip())
        return child_sitemaps, urls

    def _discover_product_urls_from_html(self) -> list[str]:
        crawl_queue = [self.base_url]
        crawled: set[str] = set()
        discovered: list[str] = []
        seen_products: set[str] = set()
        max_crawl_pages = 14

        while crawl_queue and len(crawled) < max_crawl_pages and len(discovered) < self.max_products:
            page_url = crawl_queue.pop(0)
            canonical_page = self._canonicalize_url(page_url)
            if canonical_page in crawled:
                continue
            crawled.add(canonical_page)

            try:
                html = self._fetch_text(canonical_page)
            except Exception:
                continue

            soup = BeautifulSoup(html, "html.parser")
            for anchor in soup.find_all("a", href=True):
                href = anchor.get("href") or ""
                absolute_raw = urljoin(self.base_url, href)
                absolute = self._canonicalize_url(absolute_raw)
                if not absolute_raw or not absolute:
                    continue

                if self._is_candidate_product_url(absolute_raw):
                    if absolute not in seen_products:
                        discovered.append(absolute)
                        seen_products.add(absolute)
                        if len(discovered) >= self.max_products:
                            break
                elif self._is_internal_browse_url(absolute_raw):
                    if absolute not in crawled and absolute not in crawl_queue:
                        crawl_queue.append(absolute)

        return discovered

    def _is_candidate_product_url(self, url: str) -> bool:
        parsed = urlparse(url)
        if not parsed.scheme.startswith("http"):
            return False
        base_host = urlparse(self.base_url).netloc.lower()
        if parsed.netloc.lower() != base_host:
            return False
        normalized = parsed.geturl().lower()
        path = parsed.path.lower()

        if any(excluded in normalized for excluded in self.exclude_url_patterns):
            return False
        if self.require_file_suffix and not path.endswith(self.require_file_suffix.lower()):
            return False
        return any(pattern in normalized for pattern in self.include_url_patterns)

    def _is_internal_browse_url(self, url: str) -> bool:
        parsed = urlparse(url)
        base = urlparse(self.base_url)
        if parsed.netloc.lower() != base.netloc.lower():
            return False
        if not parsed.path or parsed.path == "/":
            return False
        lowered = parsed.path.lower()
        if any(excluded in lowered for excluded in self.exclude_url_patterns):
            return False
        if self._is_candidate_product_url(url):
            return False

        browse_tokens = [
            "/shop",
            "/category",
            "/categories",
            "/collection",
            "/collections",
            "/brand",
            "/brands",
            "/health",
            "/beauty",
            "/supplement",
            "/vitamin",
            "/sale",
        ]
        return any(token in lowered for token in browse_tokens)

    def _canonicalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return ""
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    def _parse_product_page(self, url: str, source_product_id: str) -> ParsedProductPage:
        html = self._fetch_text(url)
        if self._looks_like_bot_challenge(html):
            raise RuntimeError(f"Blocked by anti-bot challenge for {self.retailer_slug}: {url}")
        soup = BeautifulSoup(html, "html.parser")

        ld_product = self._extract_json_ld_product(soup)

        title = (
            self._as_text(ld_product.get("name"))
            or self._as_text(self._extract_meta_content(soup, "property", "og:title"))
            or self._as_text(soup.title.string if soup.title else None)
            or source_product_id
        )
        image_url = self._extract_image_url(ld_product, soup, title=title)
        brand = (
            self._extract_brand(ld_product)
            or self._extract_meta_content(soup, "name", "brand")
            or title.split(" ")[0]
        )

        ld_category = self._as_text(ld_product.get("category"))
        breadcrumb_category = self._extract_breadcrumb_category(soup)
        if ld_category:
            raw_category = ld_category
            category_source = "json_ld"
        elif breadcrumb_category:
            raw_category = breadcrumb_category
            category_source = "breadcrumb"
        else:
            raw_category = self._default_category_for_vertical(self.vertical)
            category_source = "fallback"
        if self._is_pharma_vertical() and self._contains_rx_exclusion(raw_category, title):
            raise ValueError(f"Excluded prescription-like listing for {self.retailer_slug}: {url}")
        if self._is_non_product_page(url=url, title=title, soup=soup, product_obj=ld_product):
            raise NonProductPageError(f"Non-product page for {self.retailer_slug}: {url}")
        category = self._normalize_category(raw_category, title, self.vertical)

        availability = self._extract_availability(ld_product)
        price_nzd, promo_price_nzd = self._extract_prices(ld_product, soup, title=title)
        if price_nzd <= 0:
            raise ValueError(f"Unable to parse positive price for {self.retailer_slug}: {url}")
        discount_pct = self._discount_pct(price_nzd, promo_price_nzd)
        promo_text = "Promo" if promo_price_nzd is not None else None

        attributes = self._extract_attributes(ld_product, soup, title=title, raw_category=raw_category)

        gtin = self._as_text(
            ld_product.get("gtin13")
            or ld_product.get("gtin14")
            or ld_product.get("gtin")
            or self._extract_meta_content(soup, "name", "gtin")
        )
        mpn = self._as_text(ld_product.get("mpn") or ld_product.get("sku"))
        model_number = self._as_text(ld_product.get("model") or attributes.get("model") or attributes.get("model_number"))

        return ParsedProductPage(
            source_product_id=source_product_id,
            url=url,
            title=title.strip(),
            image_url=image_url,
            brand=brand.strip(),
            category=raw_category.strip(),
            availability=availability,
            gtin=gtin,
            mpn=mpn,
            model_number=model_number,
            attributes=attributes,
            price_nzd=price_nzd,
            promo_price_nzd=promo_price_nzd,
            promo_text=promo_text,
            discount_pct=discount_pct,
            normalized_category=category,
            category_source=category_source,
        )

    def _extract_json_ld_product(self, soup: BeautifulSoup) -> dict[str, Any]:
        for script in soup.find_all("script", attrs={"type": re.compile("application/ld\\+json", re.I)}):
            text = script.string or script.get_text("", strip=True)
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            product = self._find_product_object(payload)
            if product:
                return product
        return {}

    def _find_product_object(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, list):
            for item in payload:
                found = self._find_product_object(item)
                if found:
                    return found
            return None

        if not isinstance(payload, dict):
            return None

        graph = payload.get("@graph")
        if graph is not None:
            return self._find_product_object(graph)

        kind = payload.get("@type")
        if isinstance(kind, list):
            kinds = {str(item).lower() for item in kind}
        else:
            kinds = {str(kind).lower()} if kind else set()

        if "product" in kinds:
            return payload

        for value in payload.values():
            found = self._find_product_object(value)
            if found:
                return found
        return None

    def _extract_meta_content(self, soup: BeautifulSoup, attr: str, key: str) -> str | None:
        node = soup.find("meta", attrs={attr: key})
        if not node:
            return None
        return self._as_text(node.get("content"))

    def _extract_meta_contents(self, soup: BeautifulSoup, attr: str, key: str) -> list[str]:
        values: list[str] = []
        for node in soup.find_all("meta", attrs={attr: key}):
            content = self._as_text(node.get("content"))
            if content:
                values.append(content)
        return values

    def _extract_brand(self, product_obj: dict[str, Any]) -> str | None:
        brand = product_obj.get("brand")
        if isinstance(brand, dict):
            return self._as_text(brand.get("name"))
        if isinstance(brand, list) and brand:
            item = brand[0]
            if isinstance(item, dict):
                return self._as_text(item.get("name"))
            return self._as_text(item)
        return self._as_text(brand)

    def _extract_breadcrumb_category(self, soup: BeautifulSoup) -> str | None:
        for script in soup.find_all("script", attrs={"type": re.compile("application/ld\\+json", re.I)}):
            text = script.string or script.get_text("", strip=True)
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            breadcrumb = self._find_breadcrumb(payload)
            if breadcrumb:
                return breadcrumb
        return None

    def _find_breadcrumb(self, payload: Any) -> str | None:
        if isinstance(payload, list):
            for item in payload:
                found = self._find_breadcrumb(item)
                if found:
                    return found
            return None

        if not isinstance(payload, dict):
            return None

        graph = payload.get("@graph")
        if graph is not None:
            return self._find_breadcrumb(graph)

        kind = payload.get("@type")
        kinds = {str(item).lower() for item in kind} if isinstance(kind, list) else {str(kind).lower()} if kind else set()
        if "breadcrumblist" in kinds:
            elements = payload.get("itemListElement") or []
            names = []
            for element in elements:
                if isinstance(element, dict):
                    item = element.get("item")
                    if isinstance(item, dict):
                        name = self._as_text(item.get("name"))
                    else:
                        name = self._as_text(element.get("name"))
                    if name:
                        names.append(name)
            if names:
                return names[-1]

        for value in payload.values():
            found = self._find_breadcrumb(value)
            if found:
                return found
        return None

    def _extract_image_url(self, product_obj: dict[str, Any], soup: BeautifulSoup, title: str | None = None) -> str | None:
        image = product_obj.get("image")
        if isinstance(image, list) and image:
            if isinstance(image[0], dict):
                image = image[0].get("url")
            else:
                image = image[0]
        elif isinstance(image, dict):
            image = image.get("url")

        meta_image_candidates = [
            *self._extract_meta_contents(soup, "property", "og:image"),
            *self._extract_meta_contents(soup, "name", "og:image"),
            *self._extract_meta_contents(soup, "name", "twitter:image"),
            *self._extract_meta_contents(soup, "name", "twitter:image:src"),
            *self._extract_meta_contents(soup, "itemprop", "image"),
        ]

        preferred_meta_image = next((value for value in meta_image_candidates if self._clean_image_url(value)), None)

        image_url = (
            self._as_text(image)
            or preferred_meta_image
            or self._extract_image_from_img_tags(soup, title=title)
            or self._extract_image_from_scripts(soup)
        )
        if image_url:
            cleaned = self._clean_image_url(image_url)
            if cleaned:
                return urljoin(self.base_url, cleaned)
        return None

    def _extract_image_from_img_tags(self, soup: BeautifulSoup, title: str | None) -> str | None:
        best_score = float("-inf")
        best_url: str | None = None
        title_tokens = {token for token in re.findall(r"[a-z0-9]+", (title or "").lower()) if len(token) >= 4}

        for node in soup.find_all("img"):
            src = self._extract_img_source(node)
            if not src:
                continue
            cleaned = self._clean_image_url(src)
            if not cleaned:
                continue

            absolute = urljoin(self.base_url, cleaned)
            lowered_url = absolute.lower()
            classes = " ".join(node.get("class") or []).lower()
            node_id = (node.get("id") or "").lower()
            alt = (node.get("alt") or "").lower()
            context = f"{lowered_url} {classes} {node_id} {alt}"

            if any(token in context for token in IMAGE_EXCLUDE_TOKENS):
                continue

            score = 0
            if any(token in lowered_url for token in IMAGE_INCLUDE_TOKENS):
                score += 6
            if any(token in classes for token in ("product", "hero", "main", "gallery", "sub_image")):
                score += 4
            if any(token in node_id for token in ("product", "hero", "main", "gallery")):
                score += 3
            if title_tokens and sum(1 for token in title_tokens if token in alt) >= 2:
                score += 2
            if lowered_url.endswith(".svg") or lowered_url.endswith(".gif"):
                score -= 10

            if score > best_score:
                best_score = score
                best_url = absolute

        return best_url if best_score > 0 else None

    def _extract_image_from_scripts(self, soup: BeautifulSoup) -> str | None:
        script_text = " ".join(node.get_text(" ", strip=True) for node in soup.find_all("script"))
        if not script_text:
            return None
        normalized = script_text.replace("\\/", "/")
        for match in SCRIPT_IMAGE_RE.findall(normalized):
            cleaned = self._clean_image_url(match)
            if cleaned:
                return cleaned
        return None

    def _extract_img_source(self, node: Any) -> str | None:
        for key in ("src", "data-src", "data-original", "data-lazy-src", "data-zoom-image"):
            value = self._as_text(node.get(key))
            if value:
                return value

        for key in ("srcset", "data-srcset"):
            srcset = self._as_text(node.get(key))
            if not srcset:
                continue
            first = srcset.split(",")[0].strip().split(" ")[0].strip()
            if first:
                return first
        return None

    def _clean_image_url(self, value: str) -> str | None:
        text = self._as_text(value)
        if not text:
            return None
        lowered = text.lower()
        if any(token in lowered for token in IMAGE_EXCLUDE_TOKENS):
            return None
        if lowered.startswith("data:image/"):
            return None
        return text

    def _extract_availability(self, product_obj: dict[str, Any]) -> str | None:
        offers = product_obj.get("offers")
        offer = offers[0] if isinstance(offers, list) and offers else offers if isinstance(offers, dict) else None
        if not isinstance(offer, dict):
            return None
        availability = self._as_text(offer.get("availability"))
        if not availability:
            return None
        token = availability.rsplit("/", 1)[-1].strip().lower()
        if token in {"instock", "in_stock"}:
            return "in_stock"
        if token in {"outofstock", "out_of_stock"}:
            return "out_of_stock"
        if token in {"preorder", "pre_order"}:
            return "preorder"
        return token

    def _extract_prices(
        self, product_obj: dict[str, Any], soup: BeautifulSoup, title: str | None = None
    ) -> tuple[float, float | None]:
        structured_candidates: list[float] = []
        script_candidates: list[float] = []
        text_candidates: list[float] = []

        offers = product_obj.get("offers")
        offer = offers[0] if isinstance(offers, list) and offers else offers if isinstance(offers, dict) else None
        if isinstance(offer, dict):
            self._append_price(structured_candidates, offer.get("price"))
            self._append_price(structured_candidates, offer.get("lowPrice"))
            self._append_price(structured_candidates, offer.get("highPrice"))

            price_spec = offer.get("priceSpecification")
            if isinstance(price_spec, list):
                for spec in price_spec:
                    if isinstance(spec, dict):
                        self._append_price(structured_candidates, spec.get("price"))
            elif isinstance(price_spec, dict):
                self._append_price(structured_candidates, price_spec.get("price"))

        self._append_price(structured_candidates, self._extract_meta_content(soup, "property", "product:price:amount"))
        self._append_price(structured_candidates, self._extract_meta_content(soup, "name", "price"))
        self._append_price(structured_candidates, self._extract_meta_content(soup, "property", "og:price:amount"))

        text_prices = self._extract_prices_from_text(soup.get_text(" ", strip=True))
        for value in text_prices[:12]:
            self._append_price(text_candidates, value)

        script_prices = self._extract_prices_from_scripts(soup)
        for value in script_prices[:20]:
            self._append_price(script_candidates, value)

        structured = self._dedupe_prices(structured_candidates)
        script = self._dedupe_prices(script_candidates)
        text = self._dedupe_prices(text_candidates)

        primary = structured or script or text
        if not primary:
            return 0.0, None

        price_nzd = max(primary)
        if len(primary) == 1:
            return price_nzd, None

        promo_pool = primary
        if not structured and script:
            promo_pool = self._dedupe_prices([*script, *text])

        promo_price = self._select_promo_price(price_nzd, promo_pool, title=title)
        return price_nzd, promo_price

    def _extract_prices_from_scripts(self, soup: BeautifulSoup) -> list[float]:
        script_text = " ".join(node.get_text(" ", strip=True) for node in soup.find_all("script"))
        if not script_text:
            return []

        patterns = [
            r'"(?:price|salePrice|currentPrice|finalPrice|regularPrice|amount|priceValue)"\s*:\s*"?\$?([0-9][0-9,]*(?:\.[0-9]{1,2})?)"?',
            r"'(?:price|salePrice|currentPrice|finalPrice|regularPrice|amount|priceValue)'\s*:\s*'?\$?([0-9][0-9,]*(?:\.[0-9]{1,2})?)'?",
        ]

        candidates: list[float] = []
        for pattern in patterns:
            for match in re.findall(pattern, script_text, flags=re.I):
                value = self._to_float(match)
                normalized = self._normalize_price_candidate(value)
                if normalized is not None:
                    candidates.append(normalized)
        return candidates

    def _dedupe_prices(self, values: list[float]) -> list[float]:
        return sorted({round(value, 2) for value in values if 0 < value < 100000})

    def _select_promo_price(self, price_nzd: float, candidates: list[float], title: str | None) -> float | None:
        for candidate in sorted({round(value, 2) for value in candidates if 0 < value < price_nzd}, reverse=True):
            if self._is_plausible_promo(price_nzd, candidate, title=title):
                return candidate
        return None

    def _is_plausible_promo(self, regular_price: float, promo_price: float, title: str | None) -> bool:
        if promo_price <= 0 or promo_price >= regular_price:
            return False
        ratio = promo_price / regular_price
        if ratio < self._promo_floor_ratio(regular_price, title=title):
            return False
        return True

    def _promo_floor_ratio(self, regular_price: float, title: str | None) -> float:
        floor = 0.20
        if self.vertical == "tech" and regular_price >= 800:
            floor = 0.35
        lowered = (title or "").lower()
        premium_tokens = ("macbook", "iphone", "galaxy", "surface", "playstation", "xbox", "ultrabook")
        if self.vertical == "tech" and regular_price >= 800 and any(token in lowered for token in premium_tokens):
            floor = max(floor, 0.55)
        return floor

    def _normalize_price_candidate(self, value: float | None) -> float | None:
        if value is None or value <= 0:
            return None

        if value > 10000 and float(value).is_integer() and int(value) % 100 == 0:
            cents_converted = value / 100.0
            if 0 < cents_converted < 100000:
                return cents_converted

        if value >= 100000:
            return None
        return value

    def _extract_attributes(
        self, product_obj: dict[str, Any], soup: BeautifulSoup, title: str = "", raw_category: str = ""
    ) -> dict[str, object]:
        attributes: dict[str, object] = {}

        additional = product_obj.get("additionalProperty")
        for name, value in self._iter_additional_properties(additional):
            if name and value is not None:
                attributes[self._normalize_attr_key(name)] = self._normalize_attr_value(value)

        if "model" in product_obj and product_obj.get("model"):
            attributes.setdefault("model", self._as_text(product_obj.get("model")))

        if "sku" in product_obj and product_obj.get("sku"):
            attributes.setdefault("sku", self._as_text(product_obj.get("sku")))

        for key in ("description", "color", "size", "material", "pattern", "scent", "gender"):
            value = self._as_text(product_obj.get(key))
            if value:
                attributes.setdefault(key, value)

        keywords = self._as_text(product_obj.get("keywords")) or self._extract_meta_content(soup, "name", "keywords")
        if keywords:
            attributes.setdefault("keywords", [item.strip() for item in keywords.split(",") if item.strip()][:16])

        ingredients = self._extract_ingredients(product_obj, soup)
        if ingredients:
            attributes.setdefault("ingredients", ingredients)

        for key, value in self._extract_spec_attributes_from_html(soup).items():
            attributes.setdefault(key, value)

        description = attributes.get("description")
        if not description:
            meta_description = self._extract_meta_content(soup, "name", "description")
            if meta_description:
                attributes["description"] = meta_description

        if not attributes:
            # Fallback light parse for inline JSON specs
            script_text = " ".join(node.get_text(" ", strip=True) for node in soup.find_all("script"))
            model_match = re.search(r'"model"\s*:\s*"([^"]+)"', script_text)
            if model_match:
                attributes["model"] = model_match.group(1)

        if self.vertical == "beauty":
            for key, value in self._derive_beauty_attributes(title, raw_category, attributes).items():
                attributes.setdefault(key, value)

        cleaned: dict[str, object] = {}
        for key, value in attributes.items():
            if self._is_non_empty_attr_value(value):
                cleaned[key] = value
        return cleaned

    def _iter_additional_properties(self, additional: Any) -> list[tuple[str, Any]]:
        if additional is None:
            return []
        if isinstance(additional, dict):
            additional = [additional]
        if not isinstance(additional, list):
            return []

        pairs: list[tuple[str, Any]] = []
        for item in additional:
            if not isinstance(item, dict):
                continue
            name = self._as_text(item.get("name"))
            value = item.get("value")
            if name and value is not None:
                pairs.append((name, value))
                continue

            # Some implementations use key/value property maps.
            for raw_key, raw_value in item.items():
                if raw_key in {"@type", "name", "value", "unitCode", "unitText"}:
                    continue
                key_text = self._as_text(raw_key)
                if key_text and raw_value is not None:
                    pairs.append((key_text, raw_value))
        return pairs

    def _extract_spec_attributes_from_html(self, soup: BeautifulSoup) -> dict[str, object]:
        attributes: dict[str, object] = {}

        # Capture structured "specification" rows commonly used by ecommerce templates.
        for row in soup.select("table tr")[:220]:
            cells = row.find_all(["th", "td"])
            if len(cells) < 2:
                continue
            key = self._as_text(cells[0].get_text(" ", strip=True))
            value = self._as_text(cells[1].get_text(" ", strip=True))
            if not key or not value:
                continue
            if len(value) > 260:
                continue
            normalized_key = self._normalize_attr_key(key)
            if normalized_key in {"", "price", "quantity", "qty"}:
                continue
            attributes.setdefault(normalized_key, self._normalize_attr_value(value))
            if len(attributes) >= 60:
                return attributes

        for definition_list in soup.find_all("dl")[:16]:
            for term in definition_list.find_all("dt")[:80]:
                key = self._as_text(term.get_text(" ", strip=True))
                value_node = term.find_next_sibling("dd")
                value = self._as_text(value_node.get_text(" ", strip=True)) if value_node else None
                if not key or not value:
                    continue
                if len(value) > 260:
                    continue
                normalized_key = self._normalize_attr_key(key)
                if normalized_key in {"", "price", "quantity", "qty"}:
                    continue
                attributes.setdefault(normalized_key, self._normalize_attr_value(value))
                if len(attributes) >= 60:
                    return attributes

        return attributes

    def _normalize_attr_key(self, raw_key: str) -> str:
        key = raw_key.strip().lower()
        key = re.sub(r"[^a-z0-9]+", "_", key).strip("_")
        return key

    def _normalize_attr_value(self, value: Any) -> Any:
        if isinstance(value, (int, float, bool)):
            return value
        if isinstance(value, list):
            normalized = [self._normalize_attr_value(item) for item in value]
            return [item for item in normalized if self._is_non_empty_attr_value(item)]
        if isinstance(value, dict):
            return {str(k): self._normalize_attr_value(v) for k, v in value.items() if self._is_non_empty_attr_value(v)}
        text = self._as_text(value)
        if text is None:
            return value
        maybe_num = self._to_float(text)
        if maybe_num is not None and re.search(r"\d", text):
            return maybe_num
        return text

    def _extract_prices_from_text(self, text: str) -> list[float]:
        prices: list[float] = []
        for match in PRICE_RE.finditer(text):
            value = self._to_float(match.group(1))
            if value is not None:
                prices.append(value)
        for match in PRICE_CONTEXT_RE.finditer(text):
            value = self._to_float(match.group(1))
            if value is not None:
                prices.append(value)
        return prices

    def _append_price(self, bucket: list[float], value: Any) -> None:
        numeric = self._to_float(value)
        if numeric is not None:
            bucket.append(numeric)

    def _normalize_category(self, raw_category: str, title: str, vertical: str | None = None) -> str:
        target_vertical = vertical or self.vertical
        text = f"{raw_category} {title}".lower()
        if self._is_pharma_vertical_name(target_vertical):
            if self._contains_rx_exclusion(raw_category, title):
                return "excluded-rx"
            if any(token in text for token in ["vitamin", "supplement", "omega", "probiotic", "collagen", "magnesium"]):
                return "supplements"
            if any(token in text for token in ["pain", "cold", "flu", "tablet", "capsule", "medicine", "paracetamol", "ibuprofen"]):
                return "otc"
            return "other-pharma"
        if target_vertical == "beauty":
            for category, tokens in BEAUTY_CATEGORY_RULES:
                if any(token in text for token in tokens):
                    return category
            return "beauty"
        if target_vertical == "home-appliances":
            if any(token in text for token in ["fridge", "refrigerator", "freezer"]):
                return "fridges"
            if any(token in text for token in ["washing machine", "washer", "dryer", "laundry"]):
                return "washing-machines"
            if any(token in text for token in ["dishwasher"]):
                return "dishwashers"
            return "appliances"
        if target_vertical == "pet-goods":
            if any(
                token in text
                for token in [
                    "dog food",
                    "cat food",
                    "pet food",
                    "kibble",
                    "dry food",
                    "wet food",
                    "puppy food",
                    "kitten food",
                ]
            ):
                return "pet-food"
            if any(token in text for token in ["treat", "chew", "jerky", "biscuit"]):
                return "treats"
            if any(token in text for token in ["flea", "tick", "worm", "deworm", "parasite"]):
                return "flea-tick"
            if any(token in text for token in ["groom", "pet shampoo", "pet conditioner", "brush", "comb", "deodoriser"]):
                return "grooming"
            if any(token in text for token in ["pet toy", "dog toy", "cat toy", "teaser", "rope toy", "plush toy", "ball"]):
                return "toys"
            if any(token in text for token in ["pet bed", "bedding", "crate mat", "blanket"]):
                return "bedding"
            return "pet-supplies"

        if any(token in text for token in ["laptop", "notebook", "macbook", "ultrabook"]):
            return "laptops"
        if any(token in text for token in ["phone", "smartphone", "iphone", "galaxy", "pixel"]):
            return "phones"
        if any(token in text for token in ["monitor", "display", "oled", "refresh"]):
            return "monitors"
        return "electronics"

    def _default_category_for_vertical(self, vertical: str | None = None) -> str:
        target_vertical = vertical or self.vertical
        return VERTICAL_FALLBACK_CATEGORIES.get(target_vertical, "other")

    def _derive_home_appliances_attributes(self, title: str, existing_attributes: dict[str, object]) -> dict[str, object]:
        text = title.lower()
        attributes: dict[str, object] = {}

        # Basic attribute extraction from title for home appliances
        capacity_l_match = re.search(r"(\d+(?:\.\d+)?)\s*l\b", text)
        if capacity_l_match:
            attributes["capacity_l"] = float(capacity_l_match.group(1))

        capacity_kg_match = re.search(r"(\d+(?:\.\d+)?)\s*kg\b", text)
        if capacity_kg_match:
            attributes["capacity_kg"] = float(capacity_kg_match.group(1))

        energy_rating_match = re.search(r"(\d+(?:\.\d+)?)\s*star\b", text)
        if energy_rating_match:
            attributes["energy_rating"] = float(energy_rating_match.group(1))

        return attributes

    def _derive_beauty_attributes(
        self, title: str, raw_category: str, existing_attributes: dict[str, object] | None = None
    ) -> dict[str, object]:
        context = [title, raw_category]
        if existing_attributes:
            for key in ("description", "ingredients", "keywords", "product_type", "category"):
                value = existing_attributes.get(key)
                if isinstance(value, str):
                    context.append(value)
                elif isinstance(value, list):
                    context.extend(str(item) for item in value)
        text = " ".join(context).lower()
        attributes: dict[str, object] = {}

        for product_type, tokens in BEAUTY_PRODUCT_TYPE_RULES:
            if any(token in text for token in tokens):
                attributes["product_type"] = product_type
                break

        size_match = re.search(r"(\d+(?:\.\d+)?)\s*(ml|l|g|kg|oz|fl\s*oz)\b", text)
        if size_match:
            value = float(size_match.group(1))
            unit = re.sub(r"\s+", "", size_match.group(2))
            if unit == "ml":
                attributes["size_ml"] = int(value) if value.is_integer() else value
            elif unit == "l":
                ml = value * 1000
                attributes["size_ml"] = int(ml) if float(ml).is_integer() else round(ml, 2)
            elif unit == "g":
                attributes["size_g"] = int(value) if value.is_integer() else value
            elif unit == "kg":
                grams = value * 1000
                attributes["size_g"] = int(grams) if float(grams).is_integer() else round(grams, 2)
            elif unit in {"oz", "floz"}:
                attributes["size_oz"] = int(value) if value.is_integer() else value

        spf_match = re.search(r"\bspf\s*([0-9]{1,3})\b", text)
        if spf_match:
            attributes["spf"] = int(spf_match.group(1))

        pack_match = re.search(r"\b(\d+)\s*(pack|count|pcs|pieces)\b", text)
        if pack_match:
            attributes["pack_size"] = int(pack_match.group(1))

        shade_match = re.search(r"\b(?:shade|colour|color)\s*[:\-]?\s*([a-z0-9][a-z0-9\s\-]{1,40})", text)
        if shade_match:
            shade_value = shade_match.group(1).strip(" -")
            if shade_value:
                attributes["shade"] = shade_value

        for finish in BEAUTY_FINISHES:
            if finish in text:
                attributes["finish"] = finish
                break

        skin_types = [skin_type for skin_type in BEAUTY_SKIN_TYPES if skin_type in text]
        if skin_types:
            attributes["skin_type"] = sorted(set(skin_types))

        concerns = [concern for concern, tokens in BEAUTY_CONCERN_RULES if any(token in text for token in tokens)]
        if concerns:
            attributes["skin_concern"] = sorted(set(concerns))

        return attributes

    def _extract_ingredients(self, product_obj: dict[str, Any], soup: BeautifulSoup) -> str | None:
        for key in ("ingredients", "ingredient", "activeIngredients", "activeIngredient"):
            value = product_obj.get(key)
            if isinstance(value, list):
                flattened = ", ".join(self._as_text(item) or "" for item in value)
                text = flattened.strip(" ,")
                if text:
                    return text
            text = self._as_text(value)
            if text:
                return text

        script_text = " ".join(node.get_text(" ", strip=True) for node in soup.find_all("script"))
        if script_text:
            for pattern in (
                r'"ingredients"\s*:\s*"([^"]+)"',
                r"'ingredients'\s*:\s*'([^']+)'",
            ):
                match = re.search(pattern, script_text, flags=re.I)
                if match:
                    text = match.group(1).strip()
                    if text:
                        return text
        return None

    def _is_non_empty_attr_value(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip() != ""
        if isinstance(value, (list, tuple, set, dict)):
            return len(value) > 0
        return True

    def _derive_pharma_attributes(self, title: str) -> dict[str, object]:
        lowered = title.lower()
        attributes: dict[str, object] = {}

        strength_match = re.search(r"(\d+(?:\.\d+)?)\s*(mg|g|mcg|ml)", lowered)
        if strength_match:
            attributes["strength"] = f"{strength_match.group(1)}{strength_match.group(2)}"

        pack_match = re.search(r"(\d+)\s*(pack|tablets|tablet|capsules|capsule|caplets|softgels|sachets)", lowered)
        if pack_match:
            attributes["pack_size"] = int(pack_match.group(1))

        if "tablet" in lowered:
            attributes["form"] = "tablet"
            attributes["dosage_unit"] = "tablet"
        elif "caplet" in lowered:
            attributes["form"] = "caplet"
            attributes["dosage_unit"] = "caplet"
        elif "capsule" in lowered:
            attributes["form"] = "capsule"
            attributes["dosage_unit"] = "capsule"
        elif "liquid" in lowered or "syrup" in lowered:
            attributes["form"] = "liquid"
            attributes["dosage_unit"] = "ml"

        return attributes

    def _contains_rx_exclusion(self, *values: str) -> bool:
        text = " ".join(values).lower()
        return any(token in text for token in RX_EXCLUSION_TOKENS)

    def _looks_like_bot_challenge(self, html: str) -> bool:
        lowered = html.lower()
        challenge_markers = [
            "<title>just a moment",
            "/cdn-cgi/challenge-platform",
            "cf-challenge",
            "verifying your connection",
            "challenge-form",
            "please enable javascript and cookies",
        ]
        if any(marker in lowered for marker in challenge_markers):
            return True

        # Incapsula script can exist on normal pages. Treat explicit block shells as challenges.
        if "_incapsula_resource" in lowered or "incapsula" in lowered:
            shell_markers = [
                'meta name="robots" content="noindex, nofollow"',
                'meta name="robots" content="noindex,nofollow"',
                'id="main-iframe"',
                "swudnsai=",
                "xinfo=",
            ]
            if any(marker in lowered for marker in shell_markers):
                return True
            blocked_phrases = ["request unsuccessful", "incident id", "access denied", "blocked"]
            if any(phrase in lowered for phrase in blocked_phrases):
                return True
        return False

    def _looks_like_missing_page(self, soup: BeautifulSoup) -> bool:
        title_text = self._as_text(soup.title.string if soup.title else None) or ""
        heading_text = " ".join(node.get_text(" ", strip=True) for node in soup.find_all(["h1", "h2"], limit=3))
        body_text = f"{title_text} {heading_text}".lower()
        return any(marker in body_text for marker in MISSING_PAGE_MARKERS)

    def _is_non_product_page(self, url: str, title: str, soup: BeautifulSoup, product_obj: dict[str, Any]) -> bool:
        _ = (url, title, product_obj)
        return self._looks_like_missing_page(soup)

    def _discount_pct(self, price: float, promo_price: float | None) -> float | None:
        if promo_price is None or promo_price <= 0 or price <= 0 or promo_price >= price:
            return None
        return round(((price - promo_price) / price) * 100, 2)

    def _source_id_from_url(self, url: str) -> str:
        parsed = urlparse(url)
        base = f"{parsed.netloc}{parsed.path}".strip("/")
        digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]
        return f"{self.retailer_slug}-{digest}"

    def _fetch_text(self, url: str) -> str:
        attempts = self.max_fetch_retries + 1
        for attempt in range(attempts):
            response = self._request_with_retries(url)
            text = response.text
            if not self._looks_like_bot_challenge(text):
                return text

            if attempt >= attempts - 1:
                raise RuntimeError(f"Blocked by anti-bot challenge for {self.retailer_slug}: {url}")

            backoff = self.retry_backoff_seconds * (2**attempt)
            if backoff > 0:
                time.sleep(backoff)

        raise RuntimeError(f"Unreachable fetch-text retry state for {url}")

    def _fetch_sitemap_text(self, url: str) -> str:
        response = self._request_with_retries(url)
        content = response.content
        lower_url = url.lower()
        content_type = response.headers.get("content-type", "").lower()

        if lower_url.endswith(".gz") or "gzip" in content_type or "application/x-gzip" in content_type:
            try:
                content = gzip.decompress(content)
            except OSError:
                logger.debug("Sitemap %s looked gzipped but could not be decompressed; using raw payload", url)

        return content.decode(response.encoding or "utf-8", errors="replace")

    def _request_with_retries(self, url: str) -> httpx.Response:
        attempts = self.max_fetch_retries + 1
        for attempt in range(attempts):
            if self.request_delay_seconds > 0 and self._last_request_at is not None:
                elapsed = time.time() - self._last_request_at
                if elapsed < self.request_delay_seconds:
                    time.sleep(self.request_delay_seconds - elapsed)

            try:
                response = self.client.get(url)
                self._last_request_at = time.time()
                if response.status_code in RETRYABLE_HTTP_STATUSES:
                    raise httpx.HTTPStatusError(
                        f"Retryable status {response.status_code} for {url}",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                if isinstance(exc, httpx.HTTPStatusError):
                    status = exc.response.status_code if exc.response is not None else None
                    if status not in RETRYABLE_HTTP_STATUSES:
                        raise

                if attempt >= attempts - 1:
                    raise

                backoff = self.retry_backoff_seconds * (2**attempt)
                if backoff > 0:
                    time.sleep(backoff)
                logger.debug(
                    "Retrying %s for %s after error (%s), attempt %s/%s",
                    url,
                    self.retailer_slug,
                    exc,
                    attempt + 1,
                    attempts,
                )
        raise RuntimeError(f"Unreachable retry state for {url}")

    def _as_text(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None

    def _to_float(self, value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip()
        if not text:
            return None

        normalized = text.replace("$", "").replace(",", "")
        try:
            return float(normalized)
        except ValueError:
            return None
