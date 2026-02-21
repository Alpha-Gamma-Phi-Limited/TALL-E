from worker.adapters.fixture_adapter import FixtureAdapter
from worker.adapters.live_base import LiveRetailerAdapter


class FarmersBeautyFixtureAdapter(FixtureAdapter):
    vertical = "beauty"
    retailer_slug = "farmers-beauty"
    fixture_name = "farmers_beauty.json"


class FarmersBeautyLiveAdapter(LiveRetailerAdapter):
    vertical = "beauty"
    retailer_slug = "farmers-beauty"
    base_url = "https://www.farmers.co.nz"
    sitemap_seeds = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap_products_1.xml",
        "/sitemap_products.xml",
    ]
    include_url_patterns = ["/beauty/", "/product/"]
    exclude_url_patterns = ["/stores", "/blog", "/help", "?", "#"]
    fallback_fixture_cls = FarmersBeautyFixtureAdapter
