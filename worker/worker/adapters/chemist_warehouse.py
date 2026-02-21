from worker.adapters.fixture_adapter import FixtureAdapter
from worker.adapters.live_base import LiveRetailerAdapter


class ChemistWarehouseFixtureAdapter(FixtureAdapter):
    vertical = "pharma"
    retailer_slug = "chemist-warehouse"
    fixture_name = "chemist_warehouse.json"


class ChemistWarehouseLiveAdapter(LiveRetailerAdapter):
    vertical = "pharma"
    retailer_slug = "chemist-warehouse"
    base_url = "https://www.chemistwarehouse.co.nz"
    sitemap_seeds = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap_products_1.xml",
        "/sitemap_products.xml",
    ]
    include_url_patterns = ["/buy/"]
    exclude_url_patterns = ["/stores", "/about", "/help", "?", "#"]
    fallback_fixture_cls = ChemistWarehouseFixtureAdapter
