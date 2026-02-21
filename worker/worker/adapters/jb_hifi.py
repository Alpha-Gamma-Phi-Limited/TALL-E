from worker.adapters.fixture_adapter import FixtureAdapter
from worker.adapters.live_base import LiveRetailerAdapter


class JBHiFiFixtureAdapter(FixtureAdapter):
    retailer_slug = "jb-hi-fi"
    fixture_name = "jb_hifi.json"


class JBHiFiLiveAdapter(LiveRetailerAdapter):
    retailer_slug = "jb-hi-fi"
    base_url = "https://www.jbhifi.co.nz"
    sitemap_seeds = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap_products_1.xml",
        "/sitemap_products.xml",
    ]
    include_url_patterns = ["/products/"]
    exclude_url_patterns = ["/collections/", "/search", "/help", "/gift-card", "?", "#"]
    fallback_fixture_cls = JBHiFiFixtureAdapter
