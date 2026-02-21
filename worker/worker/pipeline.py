from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from worker.adapters.base import SourceAdapter
from worker.matching.normalization import normalize_text
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
                try:
                    listings = self.adapter.parse_listing(page)
                except Exception:
                    run.items_failed += 1
                    continue
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
        product = self.db.get(Product, product_id) if product_id else None
        if not product_id or product is None:
            merged_attributes = self._merge_attributes(normalized.attributes, normalized.raw_attributes)
            product = Product(
                canonical_name=normalized.canonical_name,
                vertical=normalized.vertical,
                brand=normalized.brand,
                category=normalized.category,
                model_number=normalized.model_number,
                gtin=normalized.gtin,
                mpn=normalized.mpn,
                image_url=normalized.image_url,
                attributes=merged_attributes,
                searchable_text=self._build_searchable_text(
                    normalized=normalized,
                    product_attributes=merged_attributes,
                    raw_attributes=normalized.raw_attributes,
                    existing_text="",
                ),
            )
            self.db.add(product)
            self.db.flush()
            product_id = product.id
        else:
            if normalized.image_url and not product.image_url:
                product.image_url = normalized.image_url
            if normalized.model_number and not product.model_number:
                product.model_number = normalized.model_number
            if normalized.gtin and not product.gtin:
                product.gtin = normalized.gtin
            if normalized.mpn and not product.mpn:
                product.mpn = normalized.mpn
            if normalized.brand and (not product.brand or product.brand.lower() in {"unknown", "generic"}):
                product.brand = normalized.brand
            if normalized.category and (not product.category or product.category.lower() in {"unknown", "other"}):
                product.category = normalized.category

            # Prevent low-confidence vertical flapping; only transition when evidence is strong.
            if (
                normalized.vertical
                and product.vertical != normalized.vertical
                and self._should_transition_vertical(product.vertical, normalized)
            ):
                product.vertical = normalized.vertical

            merged_attributes = self._merge_attributes(product.attributes, normalized.attributes)
            merged_attributes = self._merge_attributes(merged_attributes, normalized.raw_attributes)
            product.attributes = merged_attributes
            product.searchable_text = self._build_searchable_text(
                normalized=normalized,
                product_attributes=merged_attributes,
                raw_attributes=normalized.raw_attributes,
                existing_text=product.searchable_text or "",
            )

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

    def _merge_attributes(self, base: dict[str, object] | None, incoming: dict[str, object] | None) -> dict[str, object]:
        merged = dict(base or {})
        for key, value in (incoming or {}).items():
            if self._is_empty_attr_value(value):
                continue
            if key not in merged or self._is_empty_attr_value(merged.get(key)):
                merged[key] = value
        return merged

    @staticmethod
    def _is_empty_attr_value(value: object | None) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ""
        if isinstance(value, (list, tuple, set, dict)):
            return len(value) == 0
        return False

    def _build_searchable_text(
        self,
        normalized,
        product_attributes: dict[str, object],
        raw_attributes: dict[str, object],
        existing_text: str,
    ) -> str:
        chunks = [
            existing_text,
            normalized.canonical_name,
            normalized.title,
            normalized.brand,
            normalized.category,
            normalized.model_number or "",
            normalized.gtin or "",
            normalized.mpn or "",
        ]
        chunks.extend(self._attribute_tokens(product_attributes))
        chunks.extend(self._attribute_tokens(raw_attributes))

        tokens: list[str] = []
        seen: set[str] = set()
        for chunk in chunks:
            normalized_chunk = normalize_text(str(chunk) if chunk is not None else "")
            if not normalized_chunk:
                continue
            for token in normalized_chunk.split():
                if token in seen:
                    continue
                seen.add(token)
                tokens.append(token)
                if len(tokens) >= 220:
                    return " ".join(tokens)
        return " ".join(tokens)

    def _attribute_tokens(self, attributes: dict[str, object]) -> list[str]:
        tokens: list[str] = []
        for key, value in attributes.items():
            tokens.append(str(key))
            if isinstance(value, dict):
                for child_key, child_value in value.items():
                    tokens.append(str(child_key))
                    tokens.append(str(child_value))
                continue
            if isinstance(value, (list, tuple, set)):
                for item in list(value)[:8]:
                    tokens.append(str(item))
                continue
            if isinstance(value, str):
                compact = value.strip()
                if compact:
                    tokens.append(compact)
                    if re.search(r"[A-Za-z]\d|\d[A-Za-z]", compact):
                        tokens.append(compact.replace(" ", ""))
                continue
            tokens.append(str(value))
        return tokens

    def _should_transition_vertical(self, current_vertical: str, normalized) -> bool:
        if self._same_vertical_family(current_vertical, normalized.vertical):
            return False

        confidence = float(getattr(normalized, "vertical_confidence", 0.0) or 0.0)
        source = str(getattr(normalized, "vertical_source", "") or "").lower()

        if confidence >= 0.93:
            return True
        if source in {"json_ld", "breadcrumb", "structured_category"} and confidence >= 0.88:
            return True
        return False

    @staticmethod
    def _same_vertical_family(left: str | None, right: str | None) -> bool:
        def _canonical(value: str | None) -> str:
            lowered = str(value or "").strip().lower()
            if lowered in {"pharma", "pharmaceuticals"}:
                return "pharma"
            return lowered

        return bool(left and right and _canonical(left) == _canonical(right))
