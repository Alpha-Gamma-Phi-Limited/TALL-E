from datetime import datetime, timezone

from worker.adapters.apple import AppleFixtureAdapter
from worker.adapters.bargain_chemist import BargainChemistFixtureAdapter
from worker.adapters.base import NormalizedRetailerProduct, RawDetail, RawListing, SourceAdapter
from worker.adapters.farmers_beauty import FarmersBeautyFixtureAdapter
from worker.adapters.mecca import MeccaFixtureAdapter
from worker.adapters.pb_tech import PBTechFixtureAdapter
from worker.adapters.sephora import SephoraFixtureAdapter
from worker.pipeline import IngestionPipeline
from worker.models import LatestPrice, Product, RetailerProduct


def test_pipeline_ingests_fixture(session):
    pipeline = IngestionPipeline(session, PBTechFixtureAdapter())
    run = pipeline.run()

    assert run.status == "completed"
    assert run.items_total > 0
    assert session.query(Product).count() >= 1
    assert session.query(RetailerProduct).count() >= 1
    assert session.query(LatestPrice).count() >= 1


def test_pipeline_ingests_apple_fixture(session):
    pipeline = IngestionPipeline(session, AppleFixtureAdapter())
    run = pipeline.run()

    assert run.status == "completed"
    assert run.items_total > 0
    product = session.query(Product).filter(Product.brand == "Apple", Product.vertical == "tech").first()
    assert product is not None


def test_pipeline_ingests_pharma_fixture(session):
    pipeline = IngestionPipeline(session, BargainChemistFixtureAdapter())
    run = pipeline.run()

    assert run.status == "completed"
    assert run.items_total > 0
    product = session.query(Product).filter(Product.vertical == "pharma").first()
    assert product is not None


def test_pipeline_ingests_beauty_fixture(session):
    pipeline = IngestionPipeline(session, MeccaFixtureAdapter())
    run = pipeline.run()

    assert run.status == "completed"
    assert run.items_total > 0
    product = session.query(Product).filter(Product.vertical == "beauty").first()
    assert product is not None


def test_pipeline_ingests_sephora_beauty_fixture(session):
    pipeline = IngestionPipeline(session, SephoraFixtureAdapter())
    run = pipeline.run()

    assert run.status == "completed"
    assert run.items_total > 0
    product = session.query(Product).filter(Product.vertical == "beauty", Product.brand == "The Ordinary").first()
    assert product is not None


def test_pipeline_ingests_farmers_beauty_fixture(session):
    pipeline = IngestionPipeline(session, FarmersBeautyFixtureAdapter())
    run = pipeline.run()

    assert run.status == "completed"
    assert run.items_total > 0
    product = session.query(Product).filter(Product.vertical == "beauty", Product.brand == "Fenty Beauty").first()
    assert product is not None


class BrokenListingAdapter(SourceAdapter):
    retailer_slug = "pb-tech"
    vertical = "tech"

    def list_pages(self) -> list[dict[str, object]]:
        return [{"url": "https://example.com/a", "source_product_id": "x"}]

    def parse_listing(self, page: dict[str, object]) -> list[RawListing]:
        raise RuntimeError("parse failed")

    def fetch_detail(self, listing: RawListing) -> RawDetail:
        raise NotImplementedError

    def normalize(self, listing: RawListing, detail: RawDetail):  # type: ignore[override]
        raise NotImplementedError


def test_pipeline_continues_when_parse_listing_fails(session):
    pipeline = IngestionPipeline(session, BrokenListingAdapter())
    run = pipeline.run()

    assert run.status == "completed"
    assert run.items_failed == 1


class MetadataPreservationAdapter(SourceAdapter):
    retailer_slug = "pb-tech"
    vertical = "tech"

    def list_pages(self) -> list[dict[str, object]]:
        return [{"url": "https://example.com/macbook", "source_product_id": "meta-1"}]

    def parse_listing(self, page: dict[str, object]) -> list[RawListing]:
        return [
            RawListing(
                source_product_id="meta-1",
                title="Apple MacBook Air 13-inch M4 16GB 512GB",
                url="https://example.com/macbook",
                image_url="https://cdn.example/macbook.jpg",
                category="laptops",
                brand="Apple",
                availability="in_stock",
            )
        ]

    def fetch_detail(self, listing: RawListing) -> RawDetail:
        return RawDetail(
            gtin="1234567890001",
            mpn="MBA-M4-16-512",
            model_number="MBA13M4",
            attributes={"ram_gb": 16, "storage_gb": 512, "chipset_tier": "high"},
            price_nzd=1999.0,
            promo_price_nzd=5.0,
            promo_text="incorrect promo",
            discount_pct=None,
            captured_at=datetime.now(timezone.utc),
        )

    def normalize(self, listing: RawListing, detail: RawDetail) -> NormalizedRetailerProduct:
        return NormalizedRetailerProduct(
            vertical="tech",
            source_product_id=listing.source_product_id,
            title=listing.title,
            url=listing.url,
            image_url=listing.image_url,
            canonical_name="Apple MacBook Air 13-inch M4",
            brand="Apple",
            category="laptops",
            model_number=detail.model_number,
            gtin=detail.gtin,
            mpn=detail.mpn,
            attributes={"ram_gb": 16, "storage_gb": 512, "chipset_tier": "high"},
            raw_attributes={"memory": "16GB", "storage": "512GB SSD", "colour": "midnight"},
            availability=listing.availability,
            price_nzd=1999.0,
            promo_price_nzd=None,
            promo_text=None,
            discount_pct=None,
            captured_at=detail.captured_at,
        )


def test_pipeline_merges_product_metadata_for_search(session):
    existing = Product(
        canonical_name="Apple MacBook Air 13-inch",
        vertical="tech",
        brand="Apple",
        category="laptops",
        gtin="1234567890001",
        attributes={"cpu_score": 8500},
        searchable_text="APPLE MACBOOK AIR",
    )
    session.add(existing)
    session.commit()

    pipeline = IngestionPipeline(session, MetadataPreservationAdapter())
    run = pipeline.run()
    session.refresh(existing)

    assert run.status == "completed"
    assert existing.attributes["cpu_score"] == 8500
    assert existing.attributes["ram_gb"] == 16
    assert existing.attributes["storage_gb"] == 512
    assert existing.attributes["memory"] == "16GB"
    assert "MBA13M4" in existing.searchable_text
    assert "512GB" in existing.searchable_text
