from worker.adapters.fixture_adapter import FixtureAdapter
from worker.adapters.live_base import LiveRetailerAdapter


class NoelLeemingFixtureAdapter(FixtureAdapter):
    retailer_slug = "noel-leeming"
    fixture_name = "noel_leeming.json"


class NoelLeemingLiveAdapter(LiveRetailerAdapter):
    retailer_slug = "noel-leeming"
    base_url = "https://www.noelleeming.co.nz"
    sitemap_seeds = [
        "/sitemap_index.xml",
        "/sitemap_0.xml",
        "/sitemap_1-folder.xml",
        "/sitemap_2.xml",
    ]
    include_url_patterns = ["/p/"]
    exclude_url_patterns = ["/stores", "/services", "/help", "?", "#"]
    require_file_suffix = ".html"
    fallback_fixture_cls = NoelLeemingFixtureAdapter


class NoelLeemingHomeFixtureAdapter(FixtureAdapter):
    vertical = "home-appliances"
    retailer_slug = "noel-leeming"
    fixture_name = "noel_leeming_home.json"


class NoelLeemingHomeLiveAdapter(NoelLeemingLiveAdapter):
    vertical = "home-appliances"
    include_url_patterns = [
        "/c/whiteware",
        "/c/kitchen-appliances",
        "/c/household-appliances",
    ]
    fallback_fixture_cls = NoelLeemingHomeFixtureAdapter
