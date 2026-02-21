from worker.adapters.fixture_adapter import FixtureAdapter
from worker.adapters.live_base import LiveRetailerAdapter


class BargainChemistFixtureAdapter(FixtureAdapter):
    vertical = "pharmaceuticals"
    retailer_slug = "bargain-chemist"
    fixture_name = "bargain_chemist.json"


class BargainChemistLiveAdapter(LiveRetailerAdapter):
    vertical = "pharmaceuticals"
    retailer_slug = "bargain-chemist"
    base_url = "https://www.bargainchemist.co.nz"
    sitemap_seeds = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap_products_1.xml",
        "/sitemap_products.xml",
    ]
    include_url_patterns = ["/products/"]
    exclude_url_patterns = ["/pages/", "/policies/", "/collections/", "?", "#"]
    fallback_fixture_cls = BargainChemistFixtureAdapter


class BargainChemistSupplementsFixtureAdapter(FixtureAdapter):
    vertical = "supplements"
    retailer_slug = "bargain-chemist"
    fixture_name = "bargain_chemist_supplements.json"


class BargainChemistSupplementsLiveAdapter(BargainChemistLiveAdapter):
    vertical = "supplements"
    include_url_patterns = ["/products/"]
    fallback_fixture_cls = BargainChemistSupplementsFixtureAdapter
