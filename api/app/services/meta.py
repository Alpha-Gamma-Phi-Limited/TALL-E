from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import cache_client
from app.core.config import get_settings
from app.models import Product, Retailer
from app.schemas.meta import MetaOut

VALID_VERTICALS = {"tech", "pharma"}


def _load_scoring_config(vertical: str | None) -> dict[str, object]:
    if not vertical:
        return {}

    root = Path(__file__).resolve().parents[3]
    config_path = root / "shared" / "verticals" / vertical / "scoring_config.json"
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text())


def get_meta(db: Session, vertical: str | None = None) -> MetaOut:
    settings = get_settings()
    vertical_key = vertical or "all"
    key = f"meta:{vertical_key}:v:{settings.cache_schema_version}"
    cached = cache_client.get_json(key)
    if cached.hit:
        return MetaOut.model_validate(cached.value)

    categories_stmt = select(Product.category).distinct()
    brands_stmt = select(Product.brand).distinct()
    retailer_stmt = select(Retailer.slug, Retailer.display_name).where(Retailer.active.is_(True))

    if vertical in VALID_VERTICALS:
        categories_stmt = categories_stmt.where(Product.vertical == vertical)
        brands_stmt = brands_stmt.where(Product.vertical == vertical)
        retailer_stmt = retailer_stmt.where(Retailer.vertical == vertical)

    categories = sorted([row[0] for row in db.execute(categories_stmt).all() if row[0]])
    brands = sorted([row[0] for row in db.execute(brands_stmt).all() if row[0]])
    retailer_rows = db.execute(retailer_stmt).all()

    payload = MetaOut(
        vertical=vertical,
        categories=categories,
        brands=brands,
        retailers=[{"slug": row.slug, "name": row.display_name} for row in retailer_rows],
        filters={"categories": categories, "brands": brands},
        scoring_config=_load_scoring_config(vertical),
    )
    cache_client.set_json(key, payload.model_dump(mode="json"), ttl_seconds=3600)
    return payload
