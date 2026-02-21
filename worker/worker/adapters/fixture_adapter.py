from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from worker.adapters.base import NormalizedRetailerProduct, RawDetail, RawListing, SourceAdapter
from worker.matching.normalization import normalize_identifier, normalize_text


class FixtureAdapter(SourceAdapter):
    retailer_slug: str
    fixture_name: str

    def __init__(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.fixture_path = root / "fixtures" / self.fixture_name

    def list_pages(self) -> list[dict[str, object]]:
        payload = json.loads(self.fixture_path.read_text())
        return [payload]

    def parse_listing(self, page: dict[str, object]) -> list[RawListing]:
        listings: list[RawListing] = []
        for item in page.get("items", []):
            listings.append(
                RawListing(
                    source_product_id=str(item["source_product_id"]),
                    title=str(item["title"]),
                    url=str(item["url"]),
                    image_url=item.get("image_url"),
                    category=str(item["category"]),
                    brand=str(item["brand"]),
                    availability=item.get("availability"),
                )
            )
        return listings

    def fetch_detail(self, listing: RawListing) -> RawDetail:
        payload = json.loads(self.fixture_path.read_text())
        details_map = {str(item["source_product_id"]): item for item in payload.get("items", [])}
        item = details_map[listing.source_product_id]
        return RawDetail(
            gtin=item.get("gtin"),
            mpn=item.get("mpn"),
            model_number=item.get("model_number"),
            attributes=item.get("attributes", {}),
            price_nzd=float(item["price_nzd"]),
            promo_price_nzd=float(item["promo_price_nzd"]) if item.get("promo_price_nzd") is not None else None,
            promo_text=item.get("promo_text"),
            discount_pct=float(item["discount_pct"]) if item.get("discount_pct") is not None else None,
            captured_at=datetime.now(timezone.utc),
        )

    def normalize(self, listing: RawListing, detail: RawDetail) -> NormalizedRetailerProduct:
        brand = listing.brand.strip()
        category = listing.category.strip().lower()
        canonical_name = listing.title.strip()

        model_number = normalize_identifier(detail.model_number)
        gtin = normalize_identifier(detail.gtin)
        mpn = normalize_identifier(detail.mpn)

        merged_attributes = dict(detail.attributes)
        if model_number:
            merged_attributes.setdefault("model_number", model_number)

        return NormalizedRetailerProduct(
            vertical=self.vertical,
            source_product_id=listing.source_product_id,
            title=listing.title,
            url=listing.url,
            image_url=listing.image_url,
            canonical_name=canonical_name,
            brand=brand,
            category=category,
            model_number=model_number,
            gtin=gtin,
            mpn=mpn,
            attributes=merged_attributes,
            raw_attributes=detail.attributes,
            availability=listing.availability,
            price_nzd=detail.price_nzd,
            promo_price_nzd=detail.promo_price_nzd,
            promo_text=detail.promo_text,
            discount_pct=detail.discount_pct,
            captured_at=detail.captured_at,
        )
