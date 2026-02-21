from __future__ import annotations

import argparse
from dataclasses import dataclass

from worker.adapters.bargain_chemist import BargainChemistFixtureAdapter, BargainChemistLiveAdapter
from worker.adapters.chemist_warehouse import ChemistWarehouseFixtureAdapter, ChemistWarehouseLiveAdapter
from worker.adapters.harvey_norman import HarveyNormanFixtureAdapter, HarveyNormanLiveAdapter
from worker.adapters.jb_hifi import JBHiFiFixtureAdapter, JBHiFiLiveAdapter
from worker.adapters.life_pharmacy import LifePharmacyFixtureAdapter, LifePharmacyLiveAdapter
from worker.adapters.noel_leeming import NoelLeemingFixtureAdapter, NoelLeemingLiveAdapter
from worker.adapters.pb_tech import PBTechFixtureAdapter, PBTechLiveAdapter
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
    "harvey-norman": AdapterRegistry(fixture=HarveyNormanFixtureAdapter, live=HarveyNormanLiveAdapter),
    "chemist-warehouse": AdapterRegistry(fixture=ChemistWarehouseFixtureAdapter, live=ChemistWarehouseLiveAdapter),
    "bargain-chemist": AdapterRegistry(fixture=BargainChemistFixtureAdapter, live=BargainChemistLiveAdapter),
    "life-pharmacy": AdapterRegistry(fixture=LifePharmacyFixtureAdapter, live=LifePharmacyLiveAdapter),
}


def run_once(
    retailer_slug: str,
    mode: str,
    max_products: int,
    request_delay_seconds: float,
    use_fixture_fallback: bool,
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
            use_fixture_fallback=use_fixture_fallback,
        )

    with SessionLocal() as db:
        pipeline = IngestionPipeline(db, adapter)
        run = pipeline.run()
        print(
            f"run={run.id} status={run.status} total={run.items_total} "
            f"new={run.items_new} updated={run.items_updated} failed={run.items_failed}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="WorthIt ingestion worker")
    parser.add_argument("--retailer", required=True, choices=sorted(ADAPTERS.keys()))
    parser.add_argument("--mode", default="live", choices=["live", "fixture"])
    parser.add_argument("--max-products", type=int, default=120)
    parser.add_argument("--request-delay-seconds", type=float, default=0.0)
    parser.add_argument(
        "--no-fixture-fallback",
        action="store_true",
        help="Disable fixture fallback when live scraping cannot discover products",
    )

    args = parser.parse_args()
    run_once(
        retailer_slug=args.retailer,
        mode=args.mode,
        max_products=max(1, args.max_products),
        request_delay_seconds=max(0.0, args.request_delay_seconds),
        use_fixture_fallback=not args.no_fixture_fallback,
    )


if __name__ == "__main__":
    main()
