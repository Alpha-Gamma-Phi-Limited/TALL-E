from datetime import datetime, timezone

from worker.adapters.base import NormalizedRetailerProduct
from worker.matching.engine import MatchingEngine
from worker.models import Product


def _item(**overrides):
    payload = {
        "vertical": "tech",
        "source_product_id": "x",
        "title": "Acer Nitro 16",
        "url": "https://example.com",
        "image_url": None,
        "canonical_name": "Acer Nitro 16",
        "brand": "Acer",
        "category": "laptops",
        "model_number": "AN16-51",
        "gtin": "1234567890123",
        "mpn": "AN16-51-99",
        "attributes": {"cpu_score": 7000, "ram_gb": 16, "storage_gb": 512},
        "raw_attributes": {"cpu_score": 7000, "ram_gb": 16, "storage_gb": 512},
        "availability": "in_stock",
        "price_nzd": 1999.0,
        "promo_price_nzd": None,
        "promo_text": None,
        "discount_pct": None,
        "captured_at": datetime.now(timezone.utc),
    }
    payload.update(overrides)
    return NormalizedRetailerProduct(**payload)


def test_gtin_match(session):
    product = Product(
        canonical_name="Acer Nitro 16",
        brand="Acer",
        category="laptops",
        gtin="1234567890123",
        mpn="AN16-51-99",
        model_number="AN16-51",
        attributes={"cpu_score": 7000, "ram_gb": 16, "storage_gb": 512},
        searchable_text="Acer Nitro",
    )
    session.add(product)
    session.commit()

    match = MatchingEngine(session).match(_item())
    assert match.product_id == product.id
    assert match.tier == "gtin"


def test_fuzzy_match(session):
    product = Product(
        canonical_name="Acer Nitro16 Gaming Laptop",
        brand="Acer",
        category="laptops",
        gtin=None,
        mpn=None,
        model_number=None,
        attributes={"cpu_score": 7000, "ram_gb": 16, "storage_gb": 512},
        searchable_text="Acer Nitro16",
    )
    session.add(product)
    session.commit()

    item = _item(gtin=None, mpn=None, model_number=None, canonical_name="Acer Nitro 16 Gaming")
    match = MatchingEngine(session).match(item)
    assert match.product_id == product.id
    assert match.tier == "fuzzy"


def test_pharma_variant_mismatch_creates_new(session):
    product = Product(
        canonical_name="Panadol Tablets 500mg 20 Pack",
        vertical="pharma",
        brand="Panadol",
        category="otc",
        gtin="9300673830010",
        attributes={"strength": "500mg", "form": "tablet", "pack_size": 20},
        searchable_text="panadol 500mg tablet 20",
    )
    session.add(product)
    session.commit()

    item = _item(
        vertical="pharma",
        canonical_name="Panadol Caplets 500mg 24 Pack",
        brand="Panadol",
        category="otc",
        gtin="9300673830010",
        mpn="PAN500-24",
        model_number="PAN-500-24",
        attributes={"strength": "500mg", "form": "caplet", "pack_size": 24},
        raw_attributes={"strength": "500mg", "form": "caplet", "pack_size": 24},
    )
    match = MatchingEngine(session).match(item)
    assert match.product_id is None
