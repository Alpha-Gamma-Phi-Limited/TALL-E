from worker.adapters.fixture_adapter import FixtureAdapter
from worker.adapters.live_base import LiveRetailerAdapter


class SephoraFixtureAdapter(FixtureAdapter):
    vertical = "beauty"
    retailer_slug = "sephora"
    fixture_name = "sephora.json"


class SephoraLiveAdapter(LiveRetailerAdapter):
    vertical = "beauty"
    retailer_slug = "sephora"
    base_url = "https://www.sephora.nz"
    sitemap_seeds = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap_products_1.xml",
        "/sitemap_products.xml",
    ]
    include_url_patterns = ["/products/"]
    exclude_url_patterns = ["/stores", "/blog", "/help", "?", "#"]
    fallback_fixture_cls = SephoraFixtureAdapter
