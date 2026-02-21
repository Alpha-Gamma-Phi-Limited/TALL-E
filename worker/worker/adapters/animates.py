from worker.adapters.fixture_adapter import FixtureAdapter
from worker.adapters.live_base import LiveRetailerAdapter


class AnimatesFixtureAdapter(FixtureAdapter):
    vertical = "pet-goods"
    retailer_slug = "animates"
    fixture_name = "animates.json"


class AnimatesLiveAdapter(LiveRetailerAdapter):
    vertical = "pet-goods"
    retailer_slug = "animates"
    base_url = "https://www.animates.co.nz"
    sitemap_seeds = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap_products.xml",
    ]
    include_url_patterns = ["/products/"]
    exclude_url_patterns = ["/blog", "/stores", "/help", "?", "#"]
    fallback_fixture_cls = AnimatesFixtureAdapter
