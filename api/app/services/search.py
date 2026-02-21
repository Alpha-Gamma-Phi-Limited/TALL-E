from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.core.cache import cache_client
from app.core.config import get_settings
from app.models import LatestPrice, Product, Retailer, RetailerProduct
from app.schemas.products import OfferOut, ProductListItemOut, ProductsListOut
from app.services.value_scoring import compute_value_score


@dataclass
class ProductSearchParams:
    q: str | None = None
    vertical: str | None = None
    category: str | None = None
    brand: str | None = None
    retailers: list[str] | None = None
    price_min: float | None = None
    price_max: float | None = None
    promo_only: bool = False
    sort: str = "value_desc"
    page: int = 1
    page_size: int = 24


def _effective_price_expr() -> Any:
    return func.coalesce(LatestPrice.promo_price_nzd, LatestPrice.price_nzd)


def _build_cache_key(params: ProductSearchParams) -> str:
    settings = get_settings()
    fingerprint = "|".join(
        [
            params.q or "",
            params.vertical or "",
            params.category or "",
            params.brand or "",
            ",".join(sorted(params.retailers or [])),
            str(params.price_min or ""),
            str(params.price_max or ""),
            str(params.promo_only),
            params.sort,
            str(params.page),
            str(params.page_size),
        ]
    )
    digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
    return f"products:{digest}:page:{params.page}:v:{settings.cache_schema_version}"


def _offer_from_row(row: Any) -> OfferOut:
    return OfferOut(
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


def _best_offer_for_product(db: Session, product_id: str) -> OfferOut | None:
    effective_price = _effective_price_expr()
    row = db.execute(
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
        .limit(1)
    ).first()
    if not row:
        return None
    return _offer_from_row(row)


def search_products(db: Session, params: ProductSearchParams) -> ProductsListOut:
    key = _build_cache_key(params)
    cached = cache_client.get_json(key)
    if cached.hit:
        return ProductsListOut.model_validate(cached.value)

    effective_price = _effective_price_expr()

    stmt = (
        select(
            Product.id,
            Product.canonical_name,
            Product.vertical,
            Product.brand,
            Product.category,
            Product.image_url,
            func.count(RetailerProduct.id).label("offers_count"),
            func.min(effective_price).label("best_effective_price"),
            func.max(LatestPrice.discount_pct).label("max_discount"),
        )
        .join(RetailerProduct, RetailerProduct.product_id == Product.id)
        .join(Retailer, Retailer.id == RetailerProduct.retailer_id)
        .join(LatestPrice, LatestPrice.retailer_product_id == RetailerProduct.id)
        .where(Retailer.active.is_(True))
    )

    filters = []
    if params.vertical:
        filters.append(Product.vertical == params.vertical)
    if params.q:
        term = f"%{params.q.lower()}%"
        filters.append(
            or_(
                func.lower(Product.canonical_name).like(term),
                func.lower(Product.searchable_text).like(term),
                func.lower(func.coalesce(Product.model_number, "")).like(term),
                func.lower(func.coalesce(Product.mpn, "")).like(term),
            )
        )
    if params.category:
        filters.append(Product.category == params.category)
    if params.brand:
        filters.append(Product.brand == params.brand)
    if params.retailers:
        filters.append(Retailer.slug.in_(params.retailers))
    if params.promo_only:
        filters.append(LatestPrice.promo_price_nzd.is_not(None))
    if params.price_min is not None:
        filters.append(effective_price >= params.price_min)
    if params.price_max is not None:
        filters.append(effective_price <= params.price_max)

    if filters:
        stmt = stmt.where(and_(*filters))

    stmt = stmt.group_by(
        Product.id,
        Product.canonical_name,
        Product.vertical,
        Product.brand,
        Product.category,
        Product.image_url,
    )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0

    if params.sort == "price_asc":
        stmt = stmt.order_by(func.min(effective_price).asc(), Product.canonical_name.asc())
    elif params.sort == "price_desc":
        stmt = stmt.order_by(func.min(effective_price).desc(), Product.canonical_name.asc())
    elif params.sort == "discount_desc":
        stmt = stmt.order_by(func.max(LatestPrice.discount_pct).desc().nullslast(), Product.canonical_name.asc())
    elif params.sort == "relevance" and params.q:
        term = f"%{params.q.lower()}%"
        relevance = case((func.lower(Product.canonical_name).like(term), 2), else_=0) + case(
            (func.lower(Product.searchable_text).like(term), 1), else_=0
        )
        stmt = stmt.order_by(relevance.desc(), func.min(effective_price).asc())
    else:
        stmt = stmt.order_by(Product.canonical_name.asc())

    offset = (params.page - 1) * params.page_size
    rows = db.execute(stmt).all() if params.sort == "value_desc" else db.execute(stmt.offset(offset).limit(params.page_size)).all()

    built_items: list[ProductListItemOut] = []
    for row in rows:
        best_offer = _best_offer_for_product(db, row.id)
        product = db.get(Product, row.id)
        product_attributes = product.attributes if product else {}
        effective = None
        if best_offer:
            effective = best_offer.promo_price_nzd or best_offer.price_nzd

        score = None
        if row.vertical in ("tech", "home-appliances", "supplements"):
            score = compute_value_score(row.category, product_attributes or {}, effective)

        built_items.append(
            ProductListItemOut(
                id=row.id,
                canonical_name=row.canonical_name,
                vertical=row.vertical,
                brand=row.brand,
                category=row.category,
                image_url=row.image_url,
                attributes=product_attributes or {},
                best_offer=best_offer,
                offers_count=int(row.offers_count or 0),
                value_score=score,
            )
        )

    items = built_items
    if params.sort == "value_desc":
        items.sort(key=lambda item: item.value_score or -1, reverse=True)
        items = items[offset : offset + params.page_size]

    result = ProductsListOut(items=items, total=total, page=params.page, page_size=params.page_size)
    cache_client.set_json(key, result.model_dump(mode="json"), ttl_seconds=600)
    return result
