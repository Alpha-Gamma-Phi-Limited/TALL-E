from __future__ import annotations

import argparse
from dataclasses import dataclass

from worker.adapters.apple import AppleFixtureAdapter, AppleLiveAdapter
from worker.adapters.bargain_chemist import (
    BargainChemistFixtureAdapter,
    BargainChemistLiveAdapter,
    BargainChemistSupplementsFixtureAdapter,
    BargainChemistSupplementsLiveAdapter,
)
from worker.adapters.chemist_warehouse import (
    ChemistWarehouseFixtureAdapter,
    ChemistWarehouseLiveAdapter,
    ChemistWarehouseSupplementsFixtureAdapter,
    ChemistWarehouseSupplementsLiveAdapter,
)
from worker.adapters.farmers_beauty import FarmersBeautyFixtureAdapter, FarmersBeautyLiveAdapter
from worker.adapters.farmers_home import FarmersHomeFixtureAdapter, FarmersHomeLiveAdapter
from worker.adapters.harvey_norman import (
    HarveyNormanFixtureAdapter,
    HarveyNormanHomeFixtureAdapter,
    HarveyNormanHomeLiveAdapter,
    HarveyNormanLiveAdapter,
)
from worker.adapters.heathcotes import (
    HeathcotesFixtureAdapter,
    HeathcotesHomeFixtureAdapter,
    HeathcotesHomeLiveAdapter,
    HeathcotesLiveAdapter,
)
from worker.adapters.jb_hifi import JBHiFiFixtureAdapter, JBHiFiLiveAdapter
from worker.adapters.life_pharmacy import LifePharmacyFixtureAdapter, LifePharmacyLiveAdapter
from worker.adapters.mecca import MeccaFixtureAdapter, MeccaLiveAdapter
from worker.adapters.mighty_ape import (
    MightyApeFixtureAdapter,
    MightyApeHomeFixtureAdapter,
    MightyApeHomeLiveAdapter,
    MightyApeLiveAdapter,
)
from worker.adapters.noel_leeming import (
    NoelLeemingFixtureAdapter,
    NoelLeemingHomeFixtureAdapter,
    NoelLeemingHomeLiveAdapter,
    NoelLeemingLiveAdapter,
)
from worker.adapters.pet_co_nz import PetCoNzFixtureAdapter, PetCoNzLiveAdapter
from worker.adapters.petdirect import PetdirectFixtureAdapter, PetdirectLiveAdapter
from worker.adapters.pb_tech import PBTechFixtureAdapter, PBTechLiveAdapter
from worker.adapters.animates import AnimatesFixtureAdapter, AnimatesLiveAdapter
from worker.adapters.sephora import SephoraFixtureAdapter, SephoraLiveAdapter
from worker.adapters.supplements_co_nz import SupplementsCoNzFixtureAdapter, SupplementsCoNzLiveAdapter
from worker.adapters.the_warehouse import (
    TheWarehouseFixtureAdapter,
    TheWarehouseHomeFixtureAdapter,
    TheWarehouseHomeLiveAdapter,
    TheWarehouseLiveAdapter,
)
from worker.db import SessionLocal
from worker.pipeline import IngestionPipeline


@dataclass(frozen=True)
class AdapterRegistry:
    fixture: type
    live: type


ADAPTERS: dict[str, AdapterRegistry] = {
    "pb-tech": AdapterRegistry(fixture=PBTechFixtureAdapter, live=PBTechLiveAdapter),
    "jb-hi-fi": AdapterRegistry(fixture=JBHiFiFixtureAdapter, live=JBHiFiLiveAdapter),
    "noel-leeming": AdapterRegistry(fixture=NoelLeemingFixtureAdapter, live=NoelLeemingLiveAdapter),
    "noel-leeming-home": AdapterRegistry(fixture=NoelLeemingHomeFixtureAdapter, live=NoelLeemingHomeLiveAdapter),
    "harvey-norman": AdapterRegistry(fixture=HarveyNormanFixtureAdapter, live=HarveyNormanLiveAdapter),
    "harvey-norman-home": AdapterRegistry(fixture=HarveyNormanHomeFixtureAdapter, live=HarveyNormanHomeLiveAdapter),
    "apple": AdapterRegistry(fixture=AppleFixtureAdapter, live=AppleLiveAdapter),
    "mighty-ape": AdapterRegistry(fixture=MightyApeFixtureAdapter, live=MightyApeLiveAdapter),
    "mighty-ape-home": AdapterRegistry(fixture=MightyApeHomeFixtureAdapter, live=MightyApeHomeLiveAdapter),
    "heathcotes": AdapterRegistry(fixture=HeathcotesFixtureAdapter, live=HeathcotesLiveAdapter),
    "heathcotes-home": AdapterRegistry(fixture=HeathcotesHomeFixtureAdapter, live=HeathcotesHomeLiveAdapter),
    "chemist-warehouse": AdapterRegistry(fixture=ChemistWarehouseFixtureAdapter, live=ChemistWarehouseLiveAdapter),
    "chemist-warehouse-supplements": AdapterRegistry(fixture=ChemistWarehouseSupplementsFixtureAdapter, live=ChemistWarehouseSupplementsLiveAdapter),
    "bargain-chemist": AdapterRegistry(fixture=BargainChemistFixtureAdapter, live=BargainChemistLiveAdapter),
    "bargain-chemist-supplements": AdapterRegistry(fixture=BargainChemistSupplementsFixtureAdapter, live=BargainChemistSupplementsLiveAdapter),
    "life-pharmacy": AdapterRegistry(fixture=LifePharmacyFixtureAdapter, live=LifePharmacyLiveAdapter),
    "mecca": AdapterRegistry(fixture=MeccaFixtureAdapter, live=MeccaLiveAdapter),
    "sephora": AdapterRegistry(fixture=SephoraFixtureAdapter, live=SephoraLiveAdapter),
    "supplements-co-nz": AdapterRegistry(fixture=SupplementsCoNzFixtureAdapter, live=SupplementsCoNzLiveAdapter),
    "animates": AdapterRegistry(fixture=AnimatesFixtureAdapter, live=AnimatesLiveAdapter),
    "petdirect": AdapterRegistry(fixture=PetdirectFixtureAdapter, live=PetdirectLiveAdapter),
    "pet-co-nz": AdapterRegistry(fixture=PetCoNzFixtureAdapter, live=PetCoNzLiveAdapter),
    "farmers": AdapterRegistry(fixture=FarmersBeautyFixtureAdapter, live=FarmersBeautyLiveAdapter),
    "farmers-home": AdapterRegistry(fixture=FarmersHomeFixtureAdapter, live=FarmersHomeLiveAdapter),
    "the-warehouse": AdapterRegistry(fixture=TheWarehouseFixtureAdapter, live=TheWarehouseLiveAdapter),
    "the-warehouse-home": AdapterRegistry(fixture=TheWarehouseHomeFixtureAdapter, live=TheWarehouseHomeLiveAdapter),
}


def run_once(
    retailer_slug: str,
    mode: str,
    max_products: int,
    request_delay_seconds: float,
    max_fetch_retries: int,
    retry_backoff_seconds: float,
    use_fixture_fallback: bool,
    proxy_url: str | None,
    browser_fallback: bool,
    browser_timeout_seconds: float,
    browser_proxy_url: str | None,
    vertical: str | None = None,
) -> None:
    registry = ADAPTERS.get(retailer_slug)
    if not registry:
        raise ValueError(f"Unknown retailer slug: {retailer_slug}")

    if mode == "fixture":
        adapter = registry.fixture()
    else:
        adapter = registry.live(
            max_products=max_products,
            request_delay_seconds=request_delay_seconds,
            max_fetch_retries=max_fetch_retries,
            retry_backoff_seconds=retry_backoff_seconds,
            use_fixture_fallback=use_fixture_fallback,
            proxy_url=proxy_url,
            browser_fallback=browser_fallback,
            browser_timeout_seconds=browser_timeout_seconds,
            browser_proxy_url=browser_proxy_url,
            vertical=vertical,
        )

    with SessionLocal() as db:
        pipeline = IngestionPipeline(db, adapter)
        run = pipeline.run()
        fallback_used = getattr(adapter, "used_fixture_fallback", False)
        print(
            f"run={run.id} status={run.status} total={run.items_total} "
            f"new={run.items_new} updated={run.items_updated} failed={run.items_failed} "
            f"fixture_fallback={int(bool(fallback_used))}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="WorthIt ingestion worker")
    parser.add_argument("--retailer", required=True, choices=sorted(ADAPTERS.keys()))
    parser.add_argument("--mode", default="live", choices=["live", "fixture"])
    parser.add_argument("--max-products", type=int, default=120)
    parser.add_argument("--request-delay-seconds", type=float, default=0.35)
    parser.add_argument("--max-fetch-retries", type=int, default=3)
    parser.add_argument("--retry-backoff-seconds", type=float, default=1.0)
    parser.add_argument(
        "--no-fixture-fallback",
        action="store_true",
        help="Disable fixture fallback when live scraping cannot discover products",
    )
    parser.add_argument("--proxy-url", default=None, help="Optional upstream HTTP proxy URL for live scraping")
    parser.add_argument(
        "--browser-fallback",
        action="store_true",
        help="Enable headless browser fallback for blocked live pages (primarily Harvey Norman)",
    )
    parser.add_argument("--browser-timeout-seconds", type=float, default=35.0)
    parser.add_argument("--browser-proxy-url", default=None, help="Optional proxy URL specifically for browser fallback")
    parser.add_argument("--vertical", default=None, help="Force override of the vertical for this run")

    args = parser.parse_args()
    run_once(
        retailer_slug=args.retailer,
        mode=args.mode,
        max_products=max(1, args.max_products),
        request_delay_seconds=max(0.0, args.request_delay_seconds),
        max_fetch_retries=max(0, args.max_fetch_retries),
        retry_backoff_seconds=max(0.0, args.retry_backoff_seconds),
        use_fixture_fallback=not args.no_fixture_fallback,
        proxy_url=args.proxy_url,
        browser_fallback=args.browser_fallback,
        browser_timeout_seconds=max(5.0, args.browser_timeout_seconds),
        browser_proxy_url=args.browser_proxy_url,
        vertical=args.vertical,
    )


if __name__ == "__main__":
    main()
