from __future__ import annotations

import hashlib

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.cache import cache_client
from app.core.config import get_settings
from app.core.errors import ApiError, AppHTTPException
from app.models import LatestPrice, Price, Product, Retailer, RetailerProduct
from app.schemas.products import OfferOut, ProductDetailOut
from app.services.value_scoring import compute_value_score


def _detail_cache_key(product_id: str, include_history: bool, vertical: str | None) -> str:
    settings = get_settings()
    digest = hashlib.sha1(f"{product_id}:{include_history}:{vertical or ''}".encode("utf-8")).hexdigest()
    return f"product:{digest}:v:{settings.cache_schema_version}"


def get_product_detail(
    db: Session,
    product_id: str,
    include_history: bool = False,
    vertical: str | None = None,
) -> ProductDetailOut:
    key = _detail_cache_key(product_id, include_history, vertical)
    cached = cache_client.get_json(key)
    if cached.hit:
        return ProductDetailOut.model_validate(cached.value)

    product = db.get(Product, product_id)
    if not product or (vertical and product.vertical != vertical):
        raise AppHTTPException(
            status_code=404,
            error=ApiError(code="not_found", message="Product not found", details={"product_id": product_id}),
        )

    effective_price = func.coalesce(LatestPrice.promo_price_nzd, LatestPrice.price_nzd)
    offer_query = (
        select(
            Retailer.slug,
            RetailerProduct.id.label("rp_id"),
            RetailerProduct.title,
            RetailerProduct.url,
            RetailerProduct.image_url,
            RetailerProduct.availability,
            LatestPrice.price_nzd,
            LatestPrice.promo_price_nzd,
            LatestPrice.promo_text,
            LatestPrice.discount_pct,
            LatestPrice.captured_at,
        )
        .join(Retailer, Retailer.id == RetailerProduct.retailer_id)
        .join(LatestPrice, LatestPrice.retailer_product_id == RetailerProduct.id)
        .where(RetailerProduct.product_id == product_id)
        .order_by(effective_price.asc())
    )
    if vertical:
        offer_query = offer_query.where(Retailer.vertical == vertical)

    offer_rows = db.execute(offer_query).all()
    offers = [
        OfferOut(
            retailer=row.slug,
            retailer_product_id=row.rp_id,
            title=row.title,
            url=row.url,
            image_url=row.image_url,
            availability=row.availability,
            price_nzd=float(row.price_nzd),
            promo_price_nzd=float(row.promo_price_nzd) if row.promo_price_nzd is not None else None,
            promo_text=row.promo_text,
            discount_pct=float(row.discount_pct) if row.discount_pct is not None else None,
            captured_at=row.captured_at,
        )
        for row in offer_rows
    ]

    best_effective_price = None
    if offers:
        top = offers[0]
        best_effective_price = top.promo_price_nzd or top.price_nzd

    score = None
    if product.vertical == "tech":
        score = compute_value_score(product.category, product.attributes or {}, best_effective_price)

    history: list[OfferOut] | None = None
    if include_history:
        history_query = (
            select(
                Retailer.slug,
                RetailerProduct.id.label("rp_id"),
                RetailerProduct.title,
                RetailerProduct.url,
                RetailerProduct.image_url,
                RetailerProduct.availability,
                Price.price_nzd,
                Price.promo_price_nzd,
                Price.promo_text,
                Price.discount_pct,
                Price.captured_at,
            )
            .join(RetailerProduct, RetailerProduct.id == Price.retailer_product_id)
            .join(Retailer, Retailer.id == RetailerProduct.retailer_id)
            .where(RetailerProduct.product_id == product_id)
            .order_by(desc(Price.captured_at))
            .limit(200)
        )
        if vertical:
            history_query = history_query.where(Retailer.vertical == vertical)

        history_rows = db.execute(history_query).all()
        history = [
            OfferOut(
                retailer=row.slug,
                retailer_product_id=row.rp_id,
                title=row.title,
                url=row.url,
                image_url=row.image_url,
                availability=row.availability,
                price_nzd=float(row.price_nzd),
                promo_price_nzd=float(row.promo_price_nzd) if row.promo_price_nzd is not None else None,
                promo_text=row.promo_text,
                discount_pct=float(row.discount_pct) if row.discount_pct is not None else None,
                captured_at=row.captured_at,
            )
            for row in history_rows
        ]

    payload = ProductDetailOut(
        id=product.id,
        canonical_name=product.canonical_name,
        vertical=product.vertical,
        brand=product.brand,
        category=product.category,
        model_number=product.model_number,
        gtin=product.gtin,
        mpn=product.mpn,
        image_url=product.image_url,
        attributes=product.attributes or {},
        offers=offers,
        value_score=score,
        history=history,
    )
    cache_client.set_json(key, payload.model_dump(mode="json"), ttl_seconds=2700)
    return payload
