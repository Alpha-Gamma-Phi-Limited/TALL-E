from worker.adapters.fixture_adapter import FixtureAdapter
from worker.adapters.live_base import LiveRetailerAdapter


class HarveyNormanFixtureAdapter(FixtureAdapter):
    retailer_slug = "harvey-norman"
    fixture_name = "harvey_norman.json"


class HarveyNormanLiveAdapter(LiveRetailerAdapter):
    retailer_slug = "harvey-norman"
    base_url = "https://www.harveynorman.co.nz"
    sitemap_seeds = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap_products_1.xml",
        "/sitemap_products.xml",
    ]
    include_url_patterns = [
        "/computers/",
        "/phone-and-gps/",
        "/tv-and-audio/",
        "/cameras/",
        "/gaming/",
    ]
    exclude_url_patterns = ["/gift-card", "/services", "/stores", "?", "#"]
    require_file_suffix = ".html"
    fallback_fixture_cls = HarveyNormanFixtureAdapter
