from worker.adapters.fixture_adapter import FixtureAdapter
from worker.adapters.live_base import LiveRetailerAdapter


class SupplementsCoNzFixtureAdapter(FixtureAdapter):
    vertical = "supplements"
    retailer_slug = "supplements-co-nz"
    fixture_name = "supplements_co_nz.json"


class SupplementsCoNzLiveAdapter(LiveRetailerAdapter):
    vertical = "supplements"
    retailer_slug = "supplements-co-nz"
    base_url = "https://www.supplements.co.nz"
    sitemap_seeds = [
        "/sitemap.xml",
        "/sitemaps/products.xml",
    ]
    include_url_patterns = ["/products/"]
    exclude_url_patterns = ["/pages/", "/blogs/", "/apps/", "?", "#"]
    fallback_fixture_cls = SupplementsCoNzFixtureAdapter
