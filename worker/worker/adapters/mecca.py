from worker.adapters.fixture_adapter import FixtureAdapter
from worker.adapters.live_base import LiveRetailerAdapter


class MeccaFixtureAdapter(FixtureAdapter):
    vertical = "beauty"
    retailer_slug = "mecca"
    fixture_name = "mecca.json"


class MeccaLiveAdapter(LiveRetailerAdapter):
    vertical = "beauty"
    retailer_slug = "mecca"
    base_url = "https://www.meccabeauty.co.nz"
    sitemap_seeds = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap_products_1.xml",
        "/sitemap_products.xml",
    ]
    include_url_patterns = ["/product/"]
    exclude_url_patterns = ["/stores", "/blog", "/help", "?", "#"]
    fallback_fixture_cls = MeccaFixtureAdapter
