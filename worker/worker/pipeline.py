from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from worker.adapters.base import SourceAdapter
from worker.matching.engine import MatchingEngine
from worker.models import IngestionRun, LatestPrice, Price, Product, Retailer, RetailerProduct


class IngestionPipeline:
    def __init__(self, db: Session, adapter: SourceAdapter) -> None:
        self.db = db
        self.adapter = adapter
        self.matcher = MatchingEngine(db)

    def run(self) -> IngestionRun:
        retailer = self.db.execute(select(Retailer).where(Retailer.slug == self.adapter.retailer_slug)).scalar_one_or_none()
        if not retailer:
            raise ValueError(f"Retailer {self.adapter.retailer_slug} not found")

        run = IngestionRun(retailer_id=retailer.id, status="running", items_total=0, items_new=0, items_updated=0, items_failed=0)
        self.db.add(run)
        self.db.flush()

        try:
            pages = self.adapter.list_pages()
            for page in pages:
                listings = self.adapter.parse_listing(page)
                for listing in listings:
                    run.items_total += 1
                    try:
                        detail = self.adapter.fetch_detail(listing)
                        normalized = self.adapter.normalize(listing, detail)
                        is_new = self._upsert_item(retailer.id, normalized)
                        if is_new:
                            run.items_new += 1
                        else:
                            run.items_updated += 1
                    except Exception:
                        run.items_failed += 1

            run.status = "completed"
        except Exception as exc:
            run.status = "failed"
            run.error_summary = str(exc)
        finally:
            run.finished_at = datetime.now(timezone.utc)
            self.db.commit()

        return run

    def _upsert_item(self, retailer_id: int, normalized) -> bool:
        retailer_product = self.db.execute(
            select(RetailerProduct).where(
                and_(RetailerProduct.retailer_id == retailer_id, RetailerProduct.source_product_id == normalized.source_product_id)
            )
        ).scalar_one_or_none()

        retailer_product_id = retailer_product.id if retailer_product else None
        match = self.matcher.match(normalized, retailer_product_id=retailer_product_id)

        product_id = match.product_id
        if not product_id:
            product = Product(
                canonical_name=normalized.canonical_name,
                vertical=normalized.vertical,
                brand=normalized.brand,
                category=normalized.category,
                model_number=normalized.model_number,
                gtin=normalized.gtin,
                mpn=normalized.mpn,
                image_url=normalized.image_url,
                attributes=normalized.attributes,
                searchable_text=f"{normalized.canonical_name} {normalized.model_number or ''} {normalized.mpn or ''}",
            )
            self.db.add(product)
            self.db.flush()
            product_id = product.id

        if retailer_product is None:
            retailer_product = RetailerProduct(
                retailer_id=retailer_id,
                product_id=product_id,
                source_product_id=normalized.source_product_id,
                title=normalized.title,
                url=normalized.url,
                image_url=normalized.image_url,
                raw_attributes=normalized.raw_attributes,
                availability=normalized.availability,
            )
            self.db.add(retailer_product)
            self.db.flush()
            is_new = True
        else:
            retailer_product.product_id = product_id
            retailer_product.title = normalized.title
            retailer_product.url = normalized.url
            retailer_product.image_url = normalized.image_url
            retailer_product.raw_attributes = normalized.raw_attributes
            retailer_product.availability = normalized.availability
            is_new = False

        price = Price(
            retailer_product_id=retailer_product.id,
            price_nzd=Decimal(str(normalized.price_nzd)),
            promo_price_nzd=Decimal(str(normalized.promo_price_nzd)) if normalized.promo_price_nzd is not None else None,
            promo_text=normalized.promo_text,
            discount_pct=Decimal(str(normalized.discount_pct)) if normalized.discount_pct is not None else None,
            captured_at=normalized.captured_at,
        )
        self.db.add(price)

        latest = self.db.get(LatestPrice, retailer_product.id)
        if latest is None:
            latest = LatestPrice(
                retailer_product_id=retailer_product.id,
                price_nzd=price.price_nzd,
                promo_price_nzd=price.promo_price_nzd,
                promo_text=price.promo_text,
                discount_pct=price.discount_pct,
                captured_at=price.captured_at,
            )
            self.db.add(latest)
        else:
            latest.price_nzd = price.price_nzd
            latest.promo_price_nzd = price.promo_price_nzd
            latest.promo_text = price.promo_text
            latest.discount_pct = price.discount_pct
            latest.captured_at = price.captured_at

        self.db.flush()
        return is_new
