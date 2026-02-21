from __future__ import annotations

from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError, AppHTTPException
from app.models import IngestionRun, Product, ProductOverride, Retailer, RetailerProduct
from app.schemas.admin import IngestionRunOut, ReconcileRequest, ReconcileResponse


def reconcile_product(db: Session, payload: ReconcileRequest) -> ReconcileResponse:
    retailer_product = db.get(RetailerProduct, payload.retailer_product_id)
    if not retailer_product:
        raise AppHTTPException(
            status_code=404,
            error=ApiError(
                code="not_found",
                message="Retailer product not found",
                details={"retailer_product_id": payload.retailer_product_id},
            ),
        )
    product = db.get(Product, payload.product_id)
    if not product:
        raise AppHTTPException(
            status_code=404,
            error=ApiError(code="not_found", message="Product not found", details={"product_id": payload.product_id}),
        )

    retailer_product.product_id = payload.product_id
    existing = db.execute(
        select(ProductOverride).where(ProductOverride.retailer_product_id == payload.retailer_product_id)
    ).scalar_one_or_none()
    if existing:
        existing.product_id = payload.product_id
        existing.reason = payload.reason
    else:
        db.add(
            ProductOverride(
                retailer_product_id=payload.retailer_product_id,
                product_id=payload.product_id,
                reason=payload.reason,
            )
        )

    db.commit()
    return ReconcileResponse(
        status="ok",
        retailer_product_id=payload.retailer_product_id,
        product_id=payload.product_id,
    )


def list_ingestion_runs(db: Session, limit: int = 50) -> list[IngestionRunOut]:
    rows = db.execute(
        select(IngestionRun, Retailer.slug)
        .join(Retailer, Retailer.id == IngestionRun.retailer_id)
        .order_by(IngestionRun.started_at.desc())
        .limit(limit)
    ).all()
    outputs: list[IngestionRunOut] = []
    for run, retailer_slug in rows:
        started = run.started_at.astimezone(timezone.utc).isoformat() if run.started_at else ""
        finished = run.finished_at.astimezone(timezone.utc).isoformat() if run.finished_at else None
        outputs.append(
            IngestionRunOut(
                id=run.id,
                retailer=retailer_slug,
                status=run.status,
                items_total=run.items_total,
                items_new=run.items_new,
                items_updated=run.items_updated,
                items_failed=run.items_failed,
                started_at=started,
                finished_at=finished,
            )
        )
    return outputs
