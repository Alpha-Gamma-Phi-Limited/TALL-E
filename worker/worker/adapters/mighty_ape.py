from worker.adapters.fixture_adapter import FixtureAdapter
from worker.adapters.live_base import LiveRetailerAdapter


class MightyApeFixtureAdapter(FixtureAdapter):
    retailer_slug = "mighty-ape"
    fixture_name = "mighty_ape.json"


class MightyApeLiveAdapter(LiveRetailerAdapter):
    retailer_slug = "mighty-ape"
    base_url = "https://www.mightyape.co.nz"
    sitemap_seeds = [
        "/sitemap-index.xml",
        "/sitemaps/products.xml",
        "/sitemaps/products-1.xml",
    ]
    include_url_patterns = [
        "/product/",
        "/computers/",
        "/gaming/",
        "/electronics/",
    ]
    exclude_url_patterns = ["/marketplace/", "/author/", "/help/", "?", "#"]
    fallback_fixture_cls = MightyApeFixtureAdapter


class MightyApeHomeFixtureAdapter(FixtureAdapter):
    vertical = "home-appliances"
    retailer_slug = "mighty-ape"
    fixture_name = "mighty_ape_home.json"


class MightyApeHomeLiveAdapter(MightyApeLiveAdapter):
    vertical = "home-appliances"
    include_url_patterns = [
        "/product/",
        "/home-living/kitchen-appliances/",
        "/home-living/household-appliances/",
    ]
    fallback_fixture_cls = MightyApeHomeFixtureAdapter
