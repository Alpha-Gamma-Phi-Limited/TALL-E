import gzip

import httpx
import pytest

from worker.adapters.live_base import LiveRetailerAdapter, ParsedProductPage


class DummyLiveAdapter(LiveRetailerAdapter):
    vertical = "pharma"
    retailer_slug = "dummy"
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


def test_derive_pharma_attributes_extracts_expected_fields() -> None:
    adapter = DummyLiveAdapter(max_fetch_retries=0)
    attrs = adapter._derive_pharma_attributes("Panadol Caplets 500mg 24 Pack")

    assert attrs["strength"] == "500mg"
    assert attrs["pack_size"] == 24
    assert attrs["form"] == "caplet"
    assert attrs["dosage_unit"] == "caplet"
