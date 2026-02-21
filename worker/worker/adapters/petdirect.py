from worker.adapters.fixture_adapter import FixtureAdapter
from worker.adapters.live_base import LiveRetailerAdapter


class PetdirectFixtureAdapter(FixtureAdapter):
    vertical = "pet-goods"
    retailer_slug = "petdirect"
    fixture_name = "petdirect.json"


class PetdirectLiveAdapter(LiveRetailerAdapter):
    vertical = "pet-goods"
    retailer_slug = "petdirect"
    base_url = "https://petdirect.co.nz"
    sitemap_seeds = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemaps/products.xml",
    ]
    include_url_patterns = ["/products/"]
    exclude_url_patterns = ["/blogs/", "/pages/", "/help", "?", "#"]
    fallback_fixture_cls = PetdirectFixtureAdapter
