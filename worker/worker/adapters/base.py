from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RawListing:
    source_product_id: str
    title: str
    url: str
    image_url: str | None
    category: str
    brand: str
    availability: str | None


@dataclass
class RawDetail:
    gtin: str | None
    mpn: str | None
    model_number: str | None
    attributes: dict[str, object]
    price_nzd: float
    promo_price_nzd: float | None
    promo_text: str | None
    discount_pct: float | None
    captured_at: datetime


@dataclass
class NormalizedRetailerProduct:
    vertical: str
    source_product_id: str
    title: str
    url: str
    image_url: str | None
    canonical_name: str
    brand: str
    category: str
    model_number: str | None
    gtin: str | None
    mpn: str | None
    attributes: dict[str, object]
    raw_attributes: dict[str, object]
    availability: str | None
    price_nzd: float
    promo_price_nzd: float | None
    promo_text: str | None
    discount_pct: float | None
    captured_at: datetime


class SourceAdapter(ABC):
    vertical: str = "tech"
    retailer_slug: str

    @abstractmethod
    def list_pages(self) -> list[dict[str, object]]:
        raise NotImplementedError

    @abstractmethod
    def parse_listing(self, page: dict[str, object]) -> list[RawListing]:
        raise NotImplementedError

    @abstractmethod
    def fetch_detail(self, listing: RawListing) -> RawDetail:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, listing: RawListing, detail: RawDetail) -> NormalizedRetailerProduct:
        raise NotImplementedError
