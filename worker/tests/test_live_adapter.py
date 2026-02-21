import gzip
from datetime import datetime, timezone

import httpx
import pytest
from bs4 import BeautifulSoup

from worker.adapters.base import RawDetail, RawListing
from worker.adapters.live_base import LiveRetailerAdapter, NonProductPageError, ParsedProductPage


class DummyLiveAdapter(LiveRetailerAdapter):
    vertical = "pharma"
    retailer_slug = "dummy"
    base_url = "https://example.com"
    sitemap_seeds = ["/sitemap.xml"]
    include_url_patterns = ["/product/"]
    exclude_url_patterns = ["/blog", "?", "#"]


class DummyBeautyLiveAdapter(LiveRetailerAdapter):
    vertical = "beauty"
    retailer_slug = "dummy-beauty"
    base_url = "https://example.com"
    sitemap_seeds = ["/sitemap.xml"]
    include_url_patterns = ["/product/"]
    exclude_url_patterns = ["/blog", "?", "#"]


class DummyTechLiveAdapter(LiveRetailerAdapter):
    vertical = "tech"
    retailer_slug = "dummy-tech"
    base_url = "https://example.com"
    sitemap_seeds = ["/sitemap.xml"]
    include_url_patterns = ["/product/"]
    exclude_url_patterns = ["/blog", "?", "#"]


class DummyPetLiveAdapter(LiveRetailerAdapter):
    vertical = "pet-goods"
    retailer_slug = "dummy-pet"
    base_url = "https://example.com"
    sitemap_seeds = ["/sitemap.xml"]
    include_url_patterns = ["/product/"]
    exclude_url_patterns = ["/blog", "?", "#"]


def _response(url: str, status_code: int = 200, text: str = "", content: bytes | None = None, headers: dict[str, str] | None = None) -> httpx.Response:
    request = httpx.Request("GET", url)
    payload = content if content is not None else text.encode("utf-8")
    return httpx.Response(status_code, request=request, content=payload, headers=headers)


def test_fetch_text_retries_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=2, retry_backoff_seconds=0)
    url = "https://example.com/sitemap.xml"
    calls = {"count": 0}

    def fake_get(target_url: str) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            raise httpx.ReadTimeout("timeout", request=httpx.Request("GET", target_url))
        return _response(target_url, text="ok")

    monkeypatch.setattr(adapter.client, "get", fake_get)

    assert adapter._fetch_text(url) == "ok"
    assert calls["count"] == 2


def test_fetch_text_does_not_retry_non_retryable_status(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=3, retry_backoff_seconds=0)
    url = "https://example.com/not-found"
    calls = {"count": 0}

    def fake_get(target_url: str) -> httpx.Response:
        calls["count"] += 1
        return _response(target_url, status_code=404, text="not found")

    monkeypatch.setattr(adapter.client, "get", fake_get)

    with pytest.raises(httpx.HTTPStatusError):
        adapter._fetch_text(url)

    assert calls["count"] == 1


def test_fetch_text_retries_on_challenge_page(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=1, retry_backoff_seconds=0)
    url = "https://example.com/product"
    calls = {"count": 0}

    challenge_html = "<html><head><title>Just a moment...</title></head><body>challenge-form</body></html>"

    def fake_get(target_url: str) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return _response(target_url, text=challenge_html)
        return _response(target_url, text="<html><body>ok</body></html>")

    monkeypatch.setattr(adapter.client, "get", fake_get)

    body = adapter._fetch_text(url)
    assert "ok" in body
    assert calls["count"] == 2


def test_fetch_sitemap_text_supports_gzip(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=0)
    url = "https://example.com/sitemap.xml.gz"
    xml = "<urlset><url><loc>https://example.com/product/abc</loc></url></urlset>"
    compressed = gzip.compress(xml.encode("utf-8"))

    def fake_get(target_url: str) -> httpx.Response:
        return _response(target_url, content=compressed, headers={"content-type": "application/x-gzip"})

    monkeypatch.setattr(adapter.client, "get", fake_get)

    body = adapter._fetch_sitemap_text(url)
    assert "<urlset>" in body
    assert "/product/abc" in body


def test_discover_robots_sitemaps(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=0)

    monkeypatch.setattr(
        adapter,
        "_fetch_text",
        lambda _: "User-agent: *\nDisallow: /cart\nSitemap: https://example.com/sitemap.xml\nSitemap: https://example.com/products.xml.gz\n",
    )

    found = adapter._discover_robots_sitemaps()
    assert found == ["https://example.com/sitemap.xml", "https://example.com/products.xml.gz"]


def test_parse_sitemap_index_extracts_child_sitemaps() -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=0)
    xml = """
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <sitemap><loc>https://example.com/a.xml</loc></sitemap>
      <sitemap><loc>https://example.com/b.xml</loc></sitemap>
    </sitemapindex>
    """

    children, urls = adapter._parse_sitemap(xml)
    assert children == ["https://example.com/a.xml", "https://example.com/b.xml"]
    assert urls == []


def test_discover_product_urls_from_html_when_sitemaps_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=0)
    homepage = """
    <html><body>
      <a href="/product/abc">A</a>
      <a href="/product/def?x=1">B</a>
      <a href="/category/supplements">Supplements</a>
    </body></html>
    """
    category = """
    <html><body>
      <a href="/product/ghi">C</a>
    </body></html>
    """

    def fake_fetch_text(url: str) -> str:
        if url == "https://example.com":
            return homepage
        if url == "https://example.com/category/supplements":
            return category
        return ""

    monkeypatch.setattr(adapter, "_fetch_text", fake_fetch_text)
    urls = adapter._discover_product_urls_from_html()
    assert urls[:2] == [
        "https://example.com/product/abc",
        "https://example.com/product/ghi",
    ]


def test_is_candidate_product_url_rejects_external_domains() -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=0)
    assert adapter._is_candidate_product_url("https://other.example.com/product/abc") is False
    assert adapter._is_candidate_product_url("https://example.com/product/abc") is True


def test_discovery_failure_reason_when_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=0, use_fixture_fallback=False)

    monkeypatch.setattr(adapter, "_discover_robots_sitemaps", lambda: [])

    def always_429(url: str) -> str:
        response = _response(url, status_code=429, text="too many requests")
        raise httpx.HTTPStatusError("429", request=response.request, response=response)

    monkeypatch.setattr(adapter, "_fetch_sitemap_text", always_429)
    monkeypatch.setattr(adapter, "_discover_product_urls_from_html", lambda: [])

    urls = adapter._discover_product_urls()
    assert urls == []
    assert adapter.discovery_failure_reason == "source returned HTTP 429 anti-bot challenges"


def test_list_pages_uses_fixture_when_live_probe_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=0, use_fixture_fallback=True)

    class _Fallback:
        def list_pages(self):
            return [{"items": [{"source_product_id": "fixture-1"}]}]

    monkeypatch.setattr(adapter, "_discover_product_urls", lambda: ["https://example.com/product/a"])
    monkeypatch.setattr(adapter, "_probe_live_urls", lambda _: (False, "live product pages blocked by anti-bot/WAF"))
    adapter._fixture_fallback = _Fallback()  # type: ignore[attr-defined]

    pages = adapter.list_pages()
    assert pages == [{"items": [{"source_product_id": "fixture-1"}]}]
    assert adapter.used_fixture_fallback is True


def test_extract_prices_from_scripts_parses_price_keys() -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=0)
    soup = BeautifulSoup(
        '<html><script>window.product={"price":"397.00","salePrice":"349.00"}</script></html>',
        "html.parser",
    )
    prices = adapter._extract_prices_from_scripts(soup)
    assert 397.0 in prices
    assert 349.0 in prices


def test_extract_prices_prefers_structured_price_over_script_outlier() -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=0)
    soup = BeautifulSoup(
        """
        <html>
          <head><meta property="og:price:amount" content="19.99"/></head>
          <body><script>window.product={"price":"2999","salePrice":"1000"}</script></body>
        </html>
        """,
        "html.parser",
    )
    price, promo = adapter._extract_prices({}, soup, title="CD Album")
    assert price == 19.99
    assert promo is None


def test_extract_prices_rejects_unrealistic_micro_promo() -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=0)
    soup = BeautifulSoup("<html></html>", "html.parser")
    price, promo = adapter._extract_prices({"offers": {"price": "1969", "lowPrice": "4"}}, soup, title="Apple MacBook Air")
    assert price == 1969.0
    assert promo is None


def test_extract_image_url_uses_twitter_meta_when_present() -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=0)
    soup = BeautifulSoup(
        '<html><head><meta name="twitter:image" content="https://cdn.example.com/p/main.jpg"/></head></html>',
        "html.parser",
    )
    assert adapter._extract_image_url({}, soup, title="Example Product") == "https://cdn.example.com/p/main.jpg"


def test_extract_image_url_skips_logo_meta_and_uses_next_og_image() -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=0)
    soup = BeautifulSoup(
        """
        <html><head>
          <meta property="og:image" content="https://cdn.example.com/images/site_logo.png" />
          <meta property="og:image" content="https://cdn.example.com/images/products/sku-1-main.jpg" />
        </head></html>
        """,
        "html.parser",
    )
    image = adapter._extract_image_url({}, soup, title="Example Product")
    assert image == "https://cdn.example.com/images/products/sku-1-main.jpg"


def test_extract_image_url_falls_back_to_product_img_and_skips_logo() -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=0)
    soup = BeautifulSoup(
        """
        <html><body>
          <img id="header-logo" src="https://static.example.com/images/site_logo.png" alt="Site logo" />
          <img class="sub_image" src="https://static.example.com/ams/media/pi/62714/2DF_50.jpg" alt="Nature's Way Kids Smart Vita Gummies Multi-Vitamin + Vegies 60 Gummies" />
          <img class="sub_image" src="https://static.example.com/ams/media/pi/62714/ADD3_50.jpg" alt="Nature's Way Kids Smart Vita Gummies Multi-Vitamin + Vegies 60 Gummies" />
          <img src="https://static.example.com/App_Themes/AMS-CWH/Images/NoImage.jpg" alt="placeholder" />
        </body></html>
        """,
        "html.parser",
    )
    image = adapter._extract_image_url({}, soup, title="Nature's Way Kids Smart Vita Gummies Multi-Vitamin + Vegies 60 Gummies")
    assert image == "https://static.example.com/ams/media/pi/62714/2DF_50.jpg"


def test_extract_image_url_falls_back_to_script_image_url() -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=0)
    soup = BeautifulSoup(
        """
        <html><body>
          <script>
            window.__PRODUCT__ = {"heroImage":"https:\\/\\/cdn.example.com\\/images\\/sku-123-main.webp"};
          </script>
        </body></html>
        """,
        "html.parser",
    )
    image = adapter._extract_image_url({}, soup, title="Example Product")
    assert image == "https://cdn.example.com/images/sku-123-main.webp"


def test_looks_like_bot_challenge_detects_waf_pages() -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=0)
    blocked = "<html><head><title>Just a moment...</title></head><body>challenge-form</body></html>"
    normal = "<html><head><title>Product</title></head><body>$399.00</body></html>"
    assert adapter._looks_like_bot_challenge(blocked) is True
    assert adapter._looks_like_bot_challenge(normal) is False


def test_looks_like_bot_challenge_allows_normal_incapsula_script() -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=0)
    html = """
    <html><head><title>Product</title></head>
    <body>
      <script src="/_Incapsula_Resource?abc=123"></script>
      <meta property="og:image" content="https://cdn.example.com/images/products/a.jpg" />
    </body></html>
    """
    assert adapter._looks_like_bot_challenge(html) is False


def test_looks_like_bot_challenge_detects_incapsula_shell_page() -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=0)
    html = """
    <html><head>
      <meta name="robots" content="noindex,nofollow" />
      <script src="/_Incapsula_Resource?SWJIYLWA=abc"></script>
    </head><body>
      <iframe id="main-iframe" src="/_Incapsula_Resource?SWUDNSAI=31&xinfo=foo"></iframe>
    </body></html>
    """
    assert adapter._looks_like_bot_challenge(html) is True


def test_parse_listing_filters_non_otc_non_supplements(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=0)

    monkeypatch.setattr(
        adapter,
        "_parse_product_page",
        lambda **_: ParsedProductPage(
            source_product_id="abc",
            url="https://example.com/product/abc",
            title="Prescription Item",
            image_url=None,
            brand="Brand",
            category="other-pharma",
            availability="in_stock",
            gtin=None,
            mpn=None,
            model_number=None,
            attributes={},
            price_nzd=10.0,
            promo_price_nzd=None,
            promo_text=None,
            discount_pct=None,
        ),
    )

    listing = adapter.parse_listing({"url": "https://example.com/product/abc", "source_product_id": "abc"})
    assert listing == []


def test_parse_listing_skips_non_product_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=0)
    monkeypatch.setattr(
        adapter,
        "_parse_product_page",
        lambda **_: (_ for _ in ()).throw(NonProductPageError("non-product")),
    )
    listing = adapter.parse_listing({"url": "https://example.com/product/landing", "source_product_id": "np-1"})
    assert listing == []


def test_derive_pharma_attributes_extracts_expected_fields() -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=0)
    attrs = adapter._derive_pharma_attributes("Panadol Caplets 500mg 24 Pack")

    assert attrs["strength"] == "500mg"
    assert attrs["pack_size"] == 24
    assert attrs["form"] == "caplet"
    assert attrs["dosage_unit"] == "caplet"


def test_probe_live_urls_requires_price_for_beauty(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = DummyBeautyLiveAdapter(max_fetch_retries=0)

    monkeypatch.setattr(adapter, "_fetch_text", lambda _: "<html><body><h1>Beauty Product</h1></body></html>")
    ok, reason = adapter._probe_live_urls(["https://example.com/product/a"])

    assert ok is False
    assert reason == "live product pages reachable but price extraction failed"


def test_probe_live_urls_checks_beyond_first_three_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = DummyBeautyLiveAdapter(max_fetch_retries=0, max_products=20)
    calls: dict[str, int] = {"count": 0}
    urls = [
        "https://example.com/product/1",
        "https://example.com/product/2",
        "https://example.com/product/3",
        "https://example.com/product/4",
        "https://example.com/product/5",
    ]

    def fake_fetch(_: str) -> str:
        calls["count"] += 1
        if calls["count"] <= 3:
            return "<html><head><title>Just a moment...</title></head><body>challenge-form</body></html>"
        return """
        <html><head><meta property="og:price:amount" content="59.00" /></head>
        <body><h1>Valid Product</h1></body></html>
        """

    monkeypatch.setattr(adapter, "_fetch_text", fake_fetch)
    ok, reason = adapter._probe_live_urls(urls)

    assert ok is True
    assert reason is None
    assert calls["count"] == 5
    assert urls[0] == "https://example.com/product/4"
    assert urls[1] == "https://example.com/product/5"


def test_probe_live_urls_flags_missing_page_template(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = DummyBeautyLiveAdapter(max_fetch_retries=0)
    monkeypatch.setattr(
        adapter,
        "_fetch_text",
        lambda _: "<html><head><title>We can't find this page</title></head><body></body></html>",
    )

    ok, reason = adapter._probe_live_urls(["https://example.com/product/missing"])

    assert ok is False
    assert reason == "live product pages resolved to non-product/error pages"


def test_probe_live_urls_treats_runtime_challenge_errors_as_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = DummyBeautyLiveAdapter(max_fetch_retries=0)

    def blocked(_: str) -> str:
        raise RuntimeError("Blocked by anti-bot challenge for dummy: https://example.com/product/a")

    monkeypatch.setattr(adapter, "_fetch_text", blocked)

    ok, reason = adapter._probe_live_urls(["https://example.com/product/a"])

    assert ok is False
    assert reason == "live product pages blocked by anti-bot/WAF"


def test_list_pages_raises_when_live_probe_fails_without_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = DummyBeautyLiveAdapter(max_fetch_retries=0, use_fixture_fallback=False)

    monkeypatch.setattr(adapter, "_discover_product_urls", lambda: ["https://example.com/product/a"])
    monkeypatch.setattr(adapter, "_probe_live_urls", lambda _: (False, "live product pages reachable but price extraction failed"))

    with pytest.raises(RuntimeError, match="Live probe failed for dummy-beauty"):
        adapter.list_pages()


def test_normalize_category_handles_beauty_taxonomy() -> None:
    adapter = DummyBeautyLiveAdapter(max_fetch_retries=0)

    assert adapter._normalize_category("Face", "Hydrating Serum") == "skincare"
    assert adapter._normalize_category("Lip", "Matte Lipstick") == "makeup"
    assert adapter._normalize_category("Hair", "Repair Shampoo") == "haircare"
    assert adapter._normalize_category("", "Unknown beauty item") == "beauty"


def test_normalize_category_handles_pet_goods_taxonomy() -> None:
    adapter = DummyPetLiveAdapter(max_fetch_retries=0)

    assert adapter._normalize_category("Dog Food", "Adult Chicken Kibble") == "pet-food"
    assert adapter._normalize_category("Dog", "Natural Beef Treats") == "treats"
    assert adapter._normalize_category("Dog Care", "Flea and Tick Spot-On") == "flea-tick"
    assert adapter._normalize_category("Accessories", "Plush Rope Toy") == "toys"
    assert adapter._normalize_category("", "Unknown pet item") == "pet-supplies"


def test_extract_attributes_enriches_beauty_metadata() -> None:
    adapter = DummyBeautyLiveAdapter(max_fetch_retries=0)
    title = "Fenty Beauty Gloss Bomb Universal Lip Luminizer 9ml SPF 15"
    soup = BeautifulSoup(
        '<html><head><meta name="keywords" content="lip gloss, shimmer, hydrating"/></head><body></body></html>',
        "html.parser",
    )
    attrs = adapter._extract_attributes(
        {
            "name": title,
            "description": "Hydrating lip gloss with shimmer finish.",
            "additionalProperty": [{"name": "Shade", "value": "Fenty Glow"}],
            "ingredients": ["Jojoba Oil", "Vitamin E"],
        },
        soup,
        title=title,
        raw_category="makeup",
    )

    assert attrs["shade"] == "Fenty Glow"
    assert attrs["product_type"] == "lip_gloss"
    assert attrs["size_ml"] == 9
    assert attrs["spf"] == 15
    assert attrs["finish"] == "shimmer"
    assert attrs["ingredients"] == "Jojoba Oil, Vitamin E"


def test_extract_attributes_captures_additional_property_maps_and_html_specs() -> None:
    adapter = DummyBeautyLiveAdapter(max_fetch_retries=0)
    soup = BeautifulSoup(
        """
        <html><body>
          <table>
            <tr><th>Coverage</th><td>Medium</td></tr>
            <tr><th>Skin Type</th><td>Sensitive</td></tr>
          </table>
          <dl>
            <dt>Finish</dt><dd>Natural</dd>
          </dl>
        </body></html>
        """,
        "html.parser",
    )
    attrs = adapter._extract_attributes(
        {
            "additionalProperty": {
                "@type": "PropertyValue",
                "Shade": "Rose Nude",
                "Undertone": "Warm",
            }
        },
        soup,
        title="Foundation 30ml",
        raw_category="makeup",
    )

    assert attrs["shade"] == "Rose Nude"
    assert attrs["undertone"] == "Warm"
    assert attrs["coverage"] == "Medium"
    assert attrs["skin_type"] == "Sensitive"
    assert attrs["finish"] == "Natural"


def test_normalize_derives_beauty_search_attributes() -> None:
    adapter = DummyBeautyLiveAdapter(max_fetch_retries=0)
    listing = RawListing(
        source_product_id="beauty-1",
        title="Hydrating Face Serum 30ml SPF 50",
        url="https://example.com/product/1",
        image_url="https://cdn.example.com/p/1.jpg",
        category="skincare",
        brand="BrandX",
        availability="in_stock",
    )
    detail = RawDetail(
        gtin=None,
        mpn=None,
        model_number=None,
        attributes={"description": "Hydrating serum for dry skin"},
        price_nzd=49.0,
        promo_price_nzd=None,
        promo_text=None,
        discount_pct=None,
        captured_at=datetime.now(timezone.utc),
    )

    normalized = adapter.normalize(listing, detail)

    assert normalized.attributes["product_type"] == "serum"
    assert normalized.attributes["size_ml"] == 30
    assert normalized.attributes["spf"] == 50
    assert "dry" in normalized.attributes["skin_type"]


def test_normalize_infers_vertical_from_structured_category() -> None:
    adapter = DummyTechLiveAdapter(max_fetch_retries=0)
    listing = RawListing(
        source_product_id="home-1",
        title="Fisher & Paykel Fridge Freezer 494L",
        url="https://example.com/c/whiteware/fridges/home-1",
        image_url=None,
        category="Whiteware Fridges",
        brand="Fisher & Paykel",
        availability="in_stock",
        category_source="json_ld",
    )
    detail = RawDetail(
        gtin=None,
        mpn=None,
        model_number=None,
        attributes={},
        price_nzd=1899.0,
        promo_price_nzd=None,
        promo_text=None,
        discount_pct=None,
        captured_at=datetime.now(timezone.utc),
    )

    normalized = adapter.normalize(listing, detail)

    assert normalized.vertical == "home-appliances"
    assert normalized.vertical_source == "json_ld"
    assert normalized.vertical_confidence >= 0.9
    assert normalized.category == "fridges"


def test_normalize_infers_pet_goods_vertical_from_structured_category() -> None:
    adapter = DummyTechLiveAdapter(max_fetch_retries=0)
    listing = RawListing(
        source_product_id="pet-1",
        title="Royal Canin Adult Dog Food 12kg",
        url="https://example.com/pets/dog-food/pet-1",
        image_url=None,
        category="Dog Food",
        brand="Royal Canin",
        availability="in_stock",
        category_source="json_ld",
    )
    detail = RawDetail(
        gtin=None,
        mpn=None,
        model_number=None,
        attributes={},
        price_nzd=129.0,
        promo_price_nzd=None,
        promo_text=None,
        discount_pct=None,
        captured_at=datetime.now(timezone.utc),
    )

    normalized = adapter.normalize(listing, detail)

    assert normalized.vertical == "pet-goods"
    assert normalized.vertical_source == "json_ld"
    assert normalized.vertical_confidence >= 0.9
    assert normalized.category == "pet-food"


def test_normalize_falls_back_to_adapter_vertical_when_no_clear_signal() -> None:
    adapter = DummyTechLiveAdapter(max_fetch_retries=0)
    listing = RawListing(
        source_product_id="misc-1",
        title="Premium Annual Membership",
        url="https://example.com/membership/misc-1",
        image_url=None,
        category="Misc",
        brand="Example",
        availability="in_stock",
        category_source="fallback",
    )
    detail = RawDetail(
        gtin=None,
        mpn=None,
        model_number=None,
        attributes={},
        price_nzd=99.0,
        promo_price_nzd=None,
        promo_text=None,
        discount_pct=None,
        captured_at=datetime.now(timezone.utc),
    )

    normalized = adapter.normalize(listing, detail)

    assert normalized.vertical == "tech"
    assert normalized.vertical_source == "adapter_default"
    assert normalized.vertical_confidence == pytest.approx(0.55)
