from worker.adapters.fixture_adapter import FixtureAdapter
from worker.adapters.live_base import LiveRetailerAdapter


class LifePharmacyFixtureAdapter(FixtureAdapter):
    vertical = "pharma"
    retailer_slug = "life-pharmacy"
    fixture_name = "life_pharmacy.json"


class LifePharmacyLiveAdapter(LiveRetailerAdapter):
    vertical = "pharma"
    retailer_slug = "life-pharmacy"
    base_url = "https://www.lifepharmacy.co.nz"
    sitemap_seeds = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap_products_1.xml",
        "/sitemap_products.xml",
    ]
    include_url_patterns = ["/product/"]
    exclude_url_patterns = ["/help", "/stores", "/blog", "?", "#"]
    fallback_fixture_cls = LifePharmacyFixtureAdapter
