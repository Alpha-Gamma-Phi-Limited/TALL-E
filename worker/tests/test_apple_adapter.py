from bs4 import BeautifulSoup

from worker.adapters.apple import AppleLiveAdapter


def test_apple_candidate_url_filters_out_generic_and_query_pages() -> None:
    adapter = AppleLiveAdapter(max_fetch_retries=0, use_fixture_fallback=False)

    assert adapter._is_candidate_product_url("https://www.apple.com/nz/shop/buy-iphone/iphone-16-pro") is True
    assert adapter._is_candidate_product_url("https://www.apple.com/nz/shop/product/MX2D3X/A") is True

    assert adapter._is_candidate_product_url("https://www.apple.com/nz/shop/buy-iphone") is False
    assert adapter._is_candidate_product_url("https://www.apple.com/iphone/") is False
    assert adapter._is_candidate_product_url("https://www.apple.com/nz/shop/buy-iphone/iphone-16-pro?focus=apple-intelligence") is False


def test_apple_non_product_detection_catches_buying_compare_pages() -> None:
    adapter = AppleLiveAdapter(max_fetch_retries=0, use_fixture_fallback=False)
    soup = BeautifulSoup("<html><head><title>iPhone - Buying iPhone</title></head><body>Compare models</body></html>", "html.parser")

    assert (
        adapter._is_non_product_page(
            url="https://www.apple.com/nz/shop/buy-iphone",
            title="iPhone - Buying iPhone",
            soup=soup,
            product_obj={},
        )
        is True
    )
