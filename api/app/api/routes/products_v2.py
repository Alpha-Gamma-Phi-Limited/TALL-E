from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.products import ProductDetailOut, ProductsListOut
from app.services.details import get_product_detail
from app.services.search import ProductSearchParams, search_products

Vertical = Literal["tech", "pharma"]

router = APIRouter(prefix="/v2/products", tags=["products-v2"])


@router.get("", response_model=ProductsListOut)
def list_products_v2(
    vertical: Vertical = Query(...),
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    brand: str | None = Query(default=None),
    retailers: str | None = Query(default=None),
    price_min: float | None = Query(default=None, ge=0),
    price_max: float | None = Query(default=None, ge=0),
    promo_only: bool = Query(default=False),
    sort: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ProductsListOut:
    retailer_list = None
    if retailers:
        retailer_list = [item.strip() for item in retailers.split(",") if item.strip()]

    effective_sort = sort or ("price_asc" if vertical == "pharma" else "value_desc")

    params = ProductSearchParams(
        q=q,
        vertical=vertical,
        category=category,
        brand=brand,
        retailers=retailer_list,
        price_min=price_min,
        price_max=price_max,
        promo_only=promo_only,
        sort=effective_sort,
        page=page,
        page_size=page_size,
    )
    return search_products(db, params)


@router.get("/{product_id}", response_model=ProductDetailOut)
def product_detail_v2(
    product_id: str,
    vertical: Vertical = Query(...),
    include_history: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> ProductDetailOut:
    return get_product_detail(db, product_id=product_id, include_history=include_history, vertical=vertical)
