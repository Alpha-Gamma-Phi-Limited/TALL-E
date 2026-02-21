from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from worker.adapters.base import NormalizedRetailerProduct
from worker.matching.normalization import normalize_identifier, normalize_text
from worker.models import Product, ProductOverride, RetailerProduct


@dataclass
class MatchResult:
    product_id: str | None
    tier: str
    score: float


class MatchingEngine:
    def __init__(self, db: Session) -> None:
        self.db = db

    def match(self, item: NormalizedRetailerProduct, retailer_product_id: str | None = None) -> MatchResult:
        gtin = normalize_identifier(item.gtin)
        if gtin:
            candidate = self.db.execute(
                select(Product).where(and_(Product.gtin == gtin, Product.vertical == item.vertical))
            ).scalar_one_or_none()
            if candidate and self._pharma_variant_compatible(item, candidate):
                return MatchResult(product_id=candidate.id, tier="gtin", score=1.0)

        normalized_model = normalize_identifier(item.mpn) or normalize_identifier(item.model_number)
        if normalized_model:
            candidate = self.db.execute(
                select(Product).where(
                    and_(
                        Product.vertical == item.vertical,
                        func.lower(Product.brand) == item.brand.lower(),
                        or_(Product.mpn == normalized_model, Product.model_number == normalized_model),
                    )
                )
            ).scalar_one_or_none()
            if candidate and self._pharma_variant_compatible(item, candidate):
                return MatchResult(product_id=candidate.id, tier="model", score=0.98)

        if retailer_product_id:
            override = self.db.execute(
                select(ProductOverride).where(ProductOverride.retailer_product_id == retailer_product_id)
            ).scalar_one_or_none()
            if override:
                return MatchResult(product_id=override.product_id, tier="manual_override", score=1.0)

        return self._fuzzy_match(item)

    def _fuzzy_match(self, item: NormalizedRetailerProduct) -> MatchResult:
        candidates = self.db.execute(
            select(Product).where(
                and_(
                    Product.vertical == item.vertical,
                    func.lower(Product.brand) == item.brand.lower(),
                    func.lower(Product.category) == item.category.lower(),
                )
            ).limit(200)
        ).scalars()

        best_id: str | None = None
        best_score = 0.0
        for candidate in candidates:
            if not self._pharma_variant_compatible(item, candidate):
                continue
            attr_matches = self._attribute_overlap(item.attributes, candidate.attributes)
            if attr_matches < 2:
                continue

            name_similarity = fuzz.token_set_ratio(normalize_text(item.canonical_name), normalize_text(candidate.canonical_name)) / 100
            token_jaccard = self._token_jaccard(item.canonical_name, candidate.canonical_name)
            attribute_overlap = min(attr_matches / max(len(item.attributes), 1), 1.0)
            score = 0.55 * name_similarity + 0.30 * attribute_overlap + 0.15 * token_jaccard
            if score > best_score:
                best_id = candidate.id
                best_score = score

        if best_id and best_score >= 0.82:
            return MatchResult(product_id=best_id, tier="fuzzy", score=best_score)

        return MatchResult(product_id=None, tier="new", score=best_score)

    @staticmethod
    def _normalized_variant_key(value: object) -> str | None:
        if value is None:
            return None
        normalized = normalize_text(str(value)).replace(" ", "")
        return normalized or None

    def _pharma_variant_compatible(self, item: NormalizedRetailerProduct, candidate: Product) -> bool:
        if item.vertical != "pharma":
            return True

        for key in ("strength", "form", "pack_size"):
            item_value = self._normalized_variant_key(item.attributes.get(key))
            candidate_value = self._normalized_variant_key(candidate.attributes.get(key))
            if item_value and candidate_value and item_value != candidate_value:
                return False
        return True

    @staticmethod
    def _attribute_overlap(a: dict[str, object], b: dict[str, object]) -> int:
        if not a or not b:
            return 0
        overlap = 0
        for key, value in a.items():
            if key in b and str(b[key]).lower() == str(value).lower():
                overlap += 1
        return overlap

    @staticmethod
    def _token_jaccard(a: str, b: str) -> float:
        a_tokens = set(normalize_text(a).split())
        b_tokens = set(normalize_text(b).split())
        if not a_tokens or not b_tokens:
            return 0.0
        return len(a_tokens & b_tokens) / len(a_tokens | b_tokens)
