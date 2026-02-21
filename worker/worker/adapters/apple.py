from worker.adapters.fixture_adapter import FixtureAdapter
from worker.adapters.live_base import LiveRetailerAdapter


class AppleFixtureAdapter(FixtureAdapter):
    retailer_slug = "apple"
    fixture_name = "apple.json"


class AppleLiveAdapter(LiveRetailerAdapter):
    retailer_slug = "apple"
    base_url = "https://www.apple.com/nz"
    sitemap_seeds = [
        "/nz/sitemap.xml",
        "/sitemap.xml",
    ]
    include_url_patterns = ["/shop/buy-", "/mac/", "/iphone/", "/ipad/"]
    exclude_url_patterns = ["/support", "/newsroom", "/legal", "?", "#"]
    fallback_fixture_cls = AppleFixtureAdapter
