from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OfferOut(BaseModel):
    retailer: str
    retailer_product_id: str
    title: str
    url: str
    image_url: str | None = None
    availability: str | None = None
    price_nzd: float
    promo_price_nzd: float | None = None
    promo_text: str | None = None
    discount_pct: float | None = None
    captured_at: datetime


class ProductListItemOut(BaseModel):
    id: str
    canonical_name: str
    vertical: str
    brand: str
    category: str
    image_url: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    best_offer: OfferOut | None = None
    offers_count: int
    value_score: float | None = None


class ProductsListOut(BaseModel):
    items: list[ProductListItemOut]
    total: int
    page: int
    page_size: int


class ProductDetailOut(BaseModel):
    id: str
    canonical_name: str
    vertical: str
    brand: str
    category: str
    model_number: str | None = None
    gtin: str | None = None
    mpn: str | None = None
    image_url: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    offers: list[OfferOut] = Field(default_factory=list)
    value_score: float | None = None
    history: list[OfferOut] | None = None
