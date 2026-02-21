from worker.adapters.fixture_adapter import FixtureAdapter
from worker.adapters.live_base import LiveRetailerAdapter


class PetCoNzFixtureAdapter(FixtureAdapter):
    vertical = "pet-goods"
    retailer_slug = "pet-co-nz"
    fixture_name = "pet_co_nz.json"


class PetCoNzLiveAdapter(LiveRetailerAdapter):
    vertical = "pet-goods"
    retailer_slug = "pet-co-nz"
    base_url = "https://pet.co.nz"
    sitemap_seeds = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemaps/products.xml",
    ]
    include_url_patterns = ["/products/"]
    exclude_url_patterns = ["/blogs/", "/pages/", "/help", "?", "#"]
    fallback_fixture_cls = PetCoNzFixtureAdapter
