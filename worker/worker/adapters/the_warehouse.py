from worker.adapters.fixture_adapter import FixtureAdapter
from worker.adapters.live_base import LiveRetailerAdapter


class TheWarehouseFixtureAdapter(FixtureAdapter):
    retailer_slug = "the-warehouse"
    fixture_name = "the_warehouse.json"


class TheWarehouseLiveAdapter(LiveRetailerAdapter):
    retailer_slug = "the-warehouse"
    base_url = "https://www.thewarehouse.co.nz"
    sitemap_seeds = [
        "/sitemap_index.xml",
        "/sitemap_products_1.xml",
    ]
    include_url_patterns = [
        "/c/electronics-gaming/",
        "/electronics-gaming/",
    ]
    exclude_url_patterns = ["/stores", "/services", "/help", "?", "#"]
    fallback_fixture_cls = TheWarehouseFixtureAdapter


class TheWarehouseHomeFixtureAdapter(FixtureAdapter):
    vertical = "home-appliances"
    retailer_slug = "the-warehouse"
    fixture_name = "the_warehouse_home.json"


class TheWarehouseHomeLiveAdapter(TheWarehouseLiveAdapter):
    vertical = "home-appliances"
    include_url_patterns = [
        "/c/home-garden/whiteware-appliances/",
        "/home-garden/whiteware-appliances/",
    ]
    fallback_fixture_cls = TheWarehouseHomeFixtureAdapter
