from worker.adapters.fixture_adapter import FixtureAdapter
from worker.adapters.live_base import LiveRetailerAdapter


class HeathcotesFixtureAdapter(FixtureAdapter):
    retailer_slug = "heathcotes"
    fixture_name = "heathcotes.json"


class HeathcotesLiveAdapter(LiveRetailerAdapter):
    retailer_slug = "heathcotes"
    base_url = "https://www.heathcotes.co.nz"
    sitemap_seeds = [
        "/sitemap.xml",
        "/sitemaps/products.xml",
    ]
    include_url_patterns = [
        "/computers/",
        "/tv-and-audio/",
        "/phones-and-smart-home/",
    ]
    exclude_url_patterns = ["/gift-cards", "/services", "/contact-us", "?", "#"]
    fallback_fixture_cls = HeathcotesFixtureAdapter


class HeathcotesHomeFixtureAdapter(FixtureAdapter):
    vertical = "home-appliances"
    retailer_slug = "heathcotes"
    fixture_name = "heathcotes_home.json"


class HeathcotesHomeLiveAdapter(HeathcotesLiveAdapter):
    vertical = "home-appliances"
    include_url_patterns = [
        "/whiteware/",
        "/kitchen-appliances/",
        "/small-appliances/",
    ]
    fallback_fixture_cls = HeathcotesHomeFixtureAdapter
