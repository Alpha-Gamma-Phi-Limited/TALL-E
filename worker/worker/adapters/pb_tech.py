from worker.adapters.fixture_adapter import FixtureAdapter
from worker.adapters.live_base import LiveRetailerAdapter


class PBTechFixtureAdapter(FixtureAdapter):
    retailer_slug = "pb-tech"
    fixture_name = "pb_tech.json"


class PBTechLiveAdapter(LiveRetailerAdapter):
    retailer_slug = "pb-tech"
    base_url = "https://www.pbtech.co.nz"
    sitemap_seeds = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap_products_1.xml",
        "/sitemap_products.xml",
    ]
    include_url_patterns = ["/product/"]
    exclude_url_patterns = ["/blog", "/support", "/help", "?", "#"]
    fallback_fixture_cls = PBTechFixtureAdapter
