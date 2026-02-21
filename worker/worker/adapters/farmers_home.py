from worker.adapters.fixture_adapter import FixtureAdapter
from worker.adapters.live_base import LiveRetailerAdapter


class FarmersHomeFixtureAdapter(FixtureAdapter):
    vertical = "home-appliances"
    retailer_slug = "farmers"
    fixture_name = "farmers_home.json"


class FarmersHomeLiveAdapter(LiveRetailerAdapter):
    vertical = "home-appliances"
    retailer_slug = "farmers"
    base_url = "https://www.farmers.co.nz"
    sitemap_seeds = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap_products_1.xml",
        "/sitemap_products.xml",
    ]
    include_url_patterns = ["/home/", "/electrical/"]
    exclude_url_patterns = ["/stores", "/blog", "/help", "?", "#"]
    fallback_fixture_cls = FarmersHomeFixtureAdapter
