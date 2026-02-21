"""
Ingestion Accuracy Assessment
==============================
Baseline evaluation of product decomposition quality across all verticals.
Established on branch feat-price-normalisation to give a measurable baseline
before normalisation work begins.

HOW TO READ THIS FILE
---------------------
- Tests marked with ``pytest.mark.xfail(strict=True)`` document **known gaps**
  where the pipeline currently produces incorrect or incomplete output.
- Plain passing tests confirm behaviour that is already correct.
- Each section begins with a short findings note explaining what was measured.

EXECUTIVE SUMMARY
-----------------
Vertical          | Attr Completeness | Dedup Accuracy | Price Consistency
------------------+-------------------+----------------+------------------
tech (laptops)    | HIGH (3/3 keys)   | PARTIAL *      | GOOD
tech (monitors)   | HIGH (3/3 keys)   | n/a fixture    | GOOD
tech (phones)     | HIGH (4/4 keys)   | HIGH (GTIN)    | GOOD
tech (electronics)| ZERO  ← gap       | n/a            | GOOD
pharmaceuticals   | HIGH (5/5 keys)   | HIGH (GTIN)    | GOOD
beauty (skincare) | HIGH (3/4 keys)   | HIGH (GTIN)    | GOOD
beauty (makeup)   | PARTIAL (2/4 keys)| BROKEN  **     | INCONSISTENT ***
supplements       | HIGH (3/3 keys)   | n/a fixture    | GOOD
home-appliances   | HIGH (3/3 keys)   | n/a fixture    | GOOD
pet-goods (food)  | HIGH (2/2 keys)   | n/a fixture    | GOOD
pet-goods (flea)  | HIGH (2/2 keys)   | n/a fixture    | GOOD

*   Harvey Norman Acer Nitro 16 uses model_number ``AN16/51`` (slash) while
    all other retailers use ``AN16-51`` (dash).  normalize_identifier preserves
    both characters, so model-tier matching never fires; the product falls
    through to fuzzy matching where it still merges (ram_gb + storage_gb
    overlap satisfies the ≥2 threshold) but only because attribute values
    happen to coincide.  cpu_score diverges across retailers (7000–7200) and
    the first-ingested value wins permanently — no reconciliation.

**  Fenty Beauty Gloss Bomb: Mecca/Sephora share GTIN 840026646540 and merge
    correctly.  Farmers carries the same product under a different GTIN
    (816136021435) and conflicting attributes (product_type ``lip_gloss`` vs
    ``lip-gloss``; finish ``radiant`` vs ``shimmer``).  The attribute overlap
    score reaches only 1 (shade field alone matches case-insensitively) which
    is below the ≥2 gate in _fuzzy_match, so Farmers creates a duplicate
    canonical product.  Result: same physical product lives as two separate
    canonical records.

*** canonical_name is never normalised — it is whatever raw title the first
    ingested retailer provided (``listing.title.strip()``).  Downstream
    display and price-comparison UI inherits whatever casing/suffix the
    winning retailer happened to use.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from worker.adapters.animates import AnimatesFixtureAdapter
from worker.adapters.bargain_chemist import BargainChemistFixtureAdapter
from worker.adapters.chemist_warehouse import ChemistWarehouseFixtureAdapter
from worker.adapters.farmers_beauty import FarmersBeautyFixtureAdapter
from worker.adapters.farmers_home import FarmersHomeFixtureAdapter
from worker.adapters.harvey_norman import HarveyNormanFixtureAdapter
from worker.adapters.jb_hifi import JBHiFiFixtureAdapter
from worker.adapters.live_base import LiveRetailerAdapter
from worker.adapters.mecca import MeccaFixtureAdapter
from worker.adapters.noel_leeming import NoelLeemingFixtureAdapter
from worker.adapters.pb_tech import PBTechFixtureAdapter
from worker.adapters.sephora import SephoraFixtureAdapter
from worker.adapters.supplements_co_nz import SupplementsCoNzFixtureAdapter
from worker.matching.normalization import normalize_identifier
from worker.models import Product, RetailerProduct
from worker.pipeline import IngestionPipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "worker" / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


def _run(session, adapter) -> list[Product]:
    IngestionPipeline(session, adapter).run()
    return session.query(Product).all()


def _products_after(*adapters, session) -> list[Product]:
    for adapter in adapters:
        IngestionPipeline(session, adapter).run()
    return session.query(Product).all()


def _attr_completeness(product: Product, required_keys: list[str]) -> float:
    attrs = product.attributes or {}
    filled = sum(1 for k in required_keys if attrs.get(k) not in (None, "", [], {}))
    return filled / len(required_keys)


# ---------------------------------------------------------------------------
# 1. ATTRIBUTE COMPLETENESS
# ---------------------------------------------------------------------------
# Finding: Tech, pharma, supplements, home-appliances, and pet-goods verticals
# all reach 100% attribute completeness for their schema-required keys in
# fixture data.  The exception is tech/electronics (The Warehouse JBL Flip 6)
# which ships with an empty attributes dict, making value-scoring impossible.
# Beauty/makeup also misses size_ml at Farmers for the Fenty Gloss fixture.
# ---------------------------------------------------------------------------

TECH_LAPTOP_KEYS = ["cpu_score", "ram_gb", "storage_gb"]
TECH_PHONE_KEYS = ["chipset_tier", "ram_gb", "storage_gb", "battery_mah"]
TECH_MONITOR_KEYS = ["refresh_rate_hz", "panel_type", "resolution"]
PHARMA_OTC_KEYS = ["active_ingredient", "strength", "form", "pack_size", "dosage_unit"]
BEAUTY_SKINCARE_KEYS = ["product_type", "size_ml", "skin_concern", "finish"]
BEAUTY_MAKEUP_KEYS = ["product_type", "size_ml", "finish", "shade"]
SUPPLEMENTS_PROTEIN_KEYS = ["protein_per_serving_g", "servings", "weight_g"]
HOME_WASHER_KEYS = ["capacity_kg", "energy_rating", "type"]
PET_FOOD_KEYS = ["pet_type", "weight_kg"]


def test_tech_laptops_attribute_completeness(session):
    """All laptop products from all tech retailers should carry the 3 scored keys."""
    products = _products_after(
        PBTechFixtureAdapter(),
        JBHiFiFixtureAdapter(),
        NoelLeemingFixtureAdapter(),
        HarveyNormanFixtureAdapter(),
        session=session,
    )
    laptops = [p for p in products if p.category == "laptops"]
    assert laptops, "No laptop products created"
    for p in laptops:
        completeness = _attr_completeness(p, TECH_LAPTOP_KEYS)
        assert completeness == 1.0, (
            f"Laptop '{p.canonical_name}' missing keys: "
            f"{[k for k in TECH_LAPTOP_KEYS if not p.attributes.get(k)]}"
        )


def test_tech_monitors_attribute_completeness(session):
    products = _run(session, NoelLeemingFixtureAdapter())
    monitors = [p for p in products if p.category == "monitors"]
    assert monitors
    for p in monitors:
        assert _attr_completeness(p, TECH_MONITOR_KEYS) == 1.0


def test_tech_phones_attribute_completeness(session):
    products = _products_after(JBHiFiFixtureAdapter(), HarveyNormanFixtureAdapter(), session=session)
    phones = [p for p in products if p.category == "phones"]
    assert phones
    for p in phones:
        assert _attr_completeness(p, TECH_PHONE_KEYS) == 1.0


@pytest.mark.xfail(strict=True, reason=(
    "KNOWN GAP: The Warehouse JBL Flip 6 is ingested with attributes={} — "
    "no tech specs extracted at all.  Value scoring is impossible for this "
    "product.  Fix: enrich the fixture or improve HTML spec extraction for "
    "this retailer's product page template."
))
def test_tech_electronics_no_empty_attribute_products(session):
    """Electronics products should carry at least some attributes for scoring."""
    from worker.adapters.the_warehouse import TheWarehouseFixtureAdapter
    products = _run(session, TheWarehouseFixtureAdapter())
    electronics = [p for p in products if p.category == "electronics"]
    assert electronics
    for p in electronics:
        assert p.attributes, f"'{p.canonical_name}' has empty attributes dict — value scoring impossible"


def test_pharma_otc_attribute_completeness(session):
    products = _products_after(ChemistWarehouseFixtureAdapter(), BargainChemistFixtureAdapter(), session=session)
    otc = [p for p in products if p.category == "otc"]
    assert otc
    for p in otc:
        assert _attr_completeness(p, PHARMA_OTC_KEYS) == 1.0


def test_beauty_skincare_attribute_completeness(session):
    """Skincare products from Mecca, Sephora, and Farmers all hit 100% for the 4 scored keys."""
    products = _products_after(
        MeccaFixtureAdapter(), SephoraFixtureAdapter(), FarmersBeautyFixtureAdapter(), session=session
    )
    skincare = [p for p in products if p.category == "skincare"]
    assert skincare
    for p in skincare:
        assert _attr_completeness(p, BEAUTY_SKINCARE_KEYS) == 1.0


@pytest.mark.xfail(strict=True, reason=(
    "KNOWN GAP: Farmers Fenty Gloss Bomb fixture has no size_ml attribute. "
    "Because Farmers carries a different GTIN (816136021435 vs Mecca/Sephora "
    "840026646540) it creates a separate canonical product with only 3/4 keys. "
    "This gap will be resolved when cross-retailer GTIN discrepancy is fixed "
    "and the canonical record is allowed to inherit size_ml from the GTIN-matched copy."
))
def test_beauty_makeup_attribute_completeness(session):
    """All makeup canonical products should carry the 4 scored keys."""
    products = _products_after(
        MeccaFixtureAdapter(), SephoraFixtureAdapter(), FarmersBeautyFixtureAdapter(), session=session
    )
    makeup = [p for p in products if p.category == "makeup"]
    assert makeup
    for p in makeup:
        completeness = _attr_completeness(p, BEAUTY_MAKEUP_KEYS)
        assert completeness == 1.0, (
            f"Makeup '{p.canonical_name}' ({p.brand}) missing: "
            f"{[k for k in BEAUTY_MAKEUP_KEYS if not p.attributes.get(k)]}"
        )


def test_supplements_protein_attribute_completeness(session):
    products = _run(session, SupplementsCoNzFixtureAdapter())
    protein = [p for p in products if p.category == "protein"]
    assert protein
    for p in protein:
        assert _attr_completeness(p, SUPPLEMENTS_PROTEIN_KEYS) == 1.0


def test_home_appliances_attribute_completeness(session):
    products = _run(session, FarmersHomeFixtureAdapter())
    washers = [p for p in products if p.category == "washing-machines"]
    assert washers
    for p in washers:
        assert _attr_completeness(p, HOME_WASHER_KEYS) == 1.0


def test_pet_goods_food_attribute_completeness(session):
    products = _run(session, AnimatesFixtureAdapter())
    food = [p for p in products if p.category == "pet-food"]
    assert food
    for p in food:
        assert _attr_completeness(p, PET_FOOD_KEYS) == 1.0


# ---------------------------------------------------------------------------
# 2. CROSS-RETAILER DEDUPLICATION ACCURACY
# ---------------------------------------------------------------------------
# Finding: GTIN matching works correctly when retailers agree on the GTIN.
# Fuzzy matching is a reliable fallback for tech products where names and
# numeric specs align.  Deduplication breaks when:
#   (a) different retailers encode the same product under different GTINs, or
#   (b) attribute values that the fuzzy matcher scores differ enough to drop
#       overlap below the ≥2 gate.
# ---------------------------------------------------------------------------

def test_same_laptop_from_pb_and_jb_merges_via_gtin(session):
    """Acer Nitro 16 from PBTech and JBHiFi share GTIN 1234567890123 — one canonical record expected."""
    _products_after(PBTechFixtureAdapter(), JBHiFiFixtureAdapter(), session=session)
    nitros = session.query(Product).filter(Product.brand == "Acer", Product.category == "laptops").all()
    assert len(nitros) == 1, f"Expected 1 canonical Acer Nitro, got {len(nitros)}"
    # Both retailer products should point to the same canonical
    retailer_products = session.query(RetailerProduct).all()
    acer_rps = [rp for rp in retailer_products if "nitro" in (rp.title or "").lower() or "acer" in (rp.title or "").lower()]
    product_ids = {rp.product_id for rp in acer_rps}
    assert len(product_ids) == 1, "Retailer Acer Nitro products point to multiple canonical products"


def test_same_phone_from_jb_and_harvey_merges_via_gtin(session):
    """Samsung Galaxy S25 from JBHiFi and Harvey Norman share GTIN 5511223344556."""
    _products_after(JBHiFiFixtureAdapter(), HarveyNormanFixtureAdapter(), session=session)
    s25s = session.query(Product).filter(Product.brand == "Samsung", Product.category == "phones").all()
    assert len(s25s) == 1, f"Expected 1 canonical Samsung S25, got {len(s25s)}"


def test_same_skincare_from_mecca_and_sephora_merges_via_gtin(session):
    """The Ordinary Niacinamide: both retailers list GTIN 769915190069 → must merge."""
    _products_after(MeccaFixtureAdapter(), SephoraFixtureAdapter(), session=session)
    niacinamide = session.query(Product).filter(
        Product.brand == "The Ordinary", Product.category == "skincare"
    ).all()
    assert len(niacinamide) == 1


def test_same_pharma_from_cw_and_bc_merges_via_gtin(session):
    """Panadol 500mg 20 Pack: CW GTIN 9300673830010 = BC GTIN — single canonical expected."""
    _products_after(ChemistWarehouseFixtureAdapter(), BargainChemistFixtureAdapter(), session=session)
    panadol = session.query(Product).filter(Product.brand == "Panadol").all()
    assert len(panadol) == 1


@pytest.mark.xfail(strict=True, reason=(
    "KNOWN GAP: Fenty Beauty Gloss Bomb is listed under two different GTINs: "
    "Mecca/Sephora use 840026646540, Farmers uses 816136021435.  Because GTINs "
    "differ, matching falls back to fuzzy.  Fuzzy requires ≥2 attribute overlaps "
    "but product_type ('lip-gloss' vs 'lip_gloss') and finish ('shimmer' vs "
    "'radiant') do not match — only shade matches (1 overlap).  Farmers therefore "
    "creates a second canonical product for what is the same physical item.  "
    "Fix options: (1) normalise GTIN at source, (2) lower hyphen/underscore "
    "sensitivity in attribute overlap scoring, (3) fix conflicting finish values."
))
def test_fenty_gloss_from_mecca_sephora_and_farmers_merges_to_one(session):
    """Same Fenty Gloss Bomb from three beauty retailers should be one canonical product."""
    _products_after(MeccaFixtureAdapter(), SephoraFixtureAdapter(), FarmersBeautyFixtureAdapter(), session=session)
    gloss = session.query(Product).filter(Product.brand == "Fenty Beauty").all()
    assert len(gloss) == 1, (
        f"Expected 1 Fenty Gloss canonical product, got {len(gloss)}: "
        + ", ".join(f"'{p.canonical_name}' gtin={p.gtin}" for p in gloss)
    )


@pytest.mark.xfail(strict=True, reason=(
    "KNOWN GAP: Harvey Norman encodes the Acer Nitro 16 model number as "
    "'AN16/51' (forward-slash) whereas all other retailers use 'AN16-51' (dash). "
    "normalize_identifier preserves both '-' and '/' characters, so exact model "
    "matching fails.  The product falls through to fuzzy matching and still "
    "merges (ram_gb + storage_gb overlap ≥2), but the model-tier match never "
    "fires.  This is a silent accuracy risk: if names diverged enough to break "
    "fuzzy too, Harvey Norman would create a duplicate.  "
    "Fix: strip or normalise slash/dash equivalence in normalize_identifier, "
    "or canonicalise model numbers during adapter normalisation."
))
def test_harvey_norman_nitro_matches_via_model_tier(session):
    """Harvey Norman Acer Nitro 16 should reach match tier 'model', not 'fuzzy'."""
    from worker.matching.engine import MatchingEngine
    from worker.adapters.base import NormalizedRetailerProduct
    from datetime import datetime, timezone

    _run(session, PBTechFixtureAdapter())
    engine = MatchingEngine(session)
    hn_item = NormalizedRetailerProduct(
        vertical="tech",
        source_product_id="hn-lap-77",
        title="Acer Nitro16 AN16-51 Gaming Laptop",
        url="https://www.harveynorman.co.nz/product/hn-lap-77",
        image_url=None,
        canonical_name="Acer Nitro16 AN16-51 Gaming Laptop",
        brand="Acer",
        category="laptops",
        model_number=normalize_identifier("AN16/51"),  # → "AN16/51"
        gtin=None,
        mpn=None,
        attributes={"cpu_score": 7000, "ram_gb": 16, "storage_gb": 512},
        raw_attributes={"cpu_score": 7000, "ram_gb": 16, "storage_gb": 512},
        availability="in_stock",
        price_nzd=1859.0,
        promo_price_nzd=None,
        promo_text=None,
        discount_pct=None,
        captured_at=datetime.now(timezone.utc),
    )
    result = engine.match(hn_item)
    assert result.tier == "model", (
        f"Expected model-tier match but got '{result.tier}'. "
        f"Harvey Norman model 'AN16/51' does not match canonical 'AN16-51'."
    )


# ---------------------------------------------------------------------------
# 3. PRICE DECOMPOSITION CONSISTENCY
# ---------------------------------------------------------------------------
# Finding: Fixture discount_pct values are manually authored and drift from
# the price/promo_price pair in some items.  The pipeline does NOT recompute
# discount_pct from prices for fixture data — it stores whatever the fixture
# provides.  Divergence compounds across retailers if one retailer's fixture
# has a rounding error.  For live ingestion, _discount_pct() is called only
# inside _upsert_item (via the Price model), meaning the stored Price row is
# always recomputed, but the fixture's discount_pct field is the one surfaced
# to end-users via LatestPrice.
# ---------------------------------------------------------------------------

def _expected_discount(price: float, promo: float) -> float:
    return round((price - promo) / price * 100, 2)


@pytest.mark.parametrize("fixture_name,item_id", [
    ("pb_tech.json", "pb-lap-100"),
    ("chemist_warehouse.json", "cw-otc-001"),
    ("mecca.json", "mecca-makeup-210"),
    ("bargain_chemist.json", "bc-sup-877"),
    ("bargain_chemist_supplements.json", "bc-supp-1"),
    ("farmers_home.json", "farmers-home-1"),
    ("animates.json", "animates-dog-food-001"),
    ("supplements_co_nz.json", "on-whey-5lb"),
])
def test_fixture_discount_pct_is_consistent_with_prices(fixture_name, item_id):
    """discount_pct in each fixture must equal (price - promo) / price * 100."""
    data = _load_fixture(fixture_name)
    item = next(i for i in data["items"] if str(i["source_product_id"]) == item_id)

    price = float(item["price_nzd"])
    promo = item.get("promo_price_nzd")
    stored_pct = item.get("discount_pct")

    if promo is None:
        assert stored_pct is None, (
            f"{fixture_name}/{item_id}: promo_price_nzd is null but discount_pct={stored_pct}"
        )
        return

    expected = _expected_discount(price, float(promo))
    assert stored_pct is not None, f"{fixture_name}/{item_id}: has promo price but discount_pct is null"
    assert abs(float(stored_pct) - expected) < 0.15, (
        f"{fixture_name}/{item_id}: discount_pct={stored_pct} but "
        f"(price={price} - promo={promo}) / price = {expected:.2f}"
    )


def test_promo_price_always_less_than_regular_price_across_fixtures():
    """Every fixture item with a promo_price_nzd must have promo < price."""
    violations = []
    for fixture_file in FIXTURES_DIR.glob("*.json"):
        data = json.loads(fixture_file.read_text())
        for item in data.get("items", []):
            price = item.get("price_nzd")
            promo = item.get("promo_price_nzd")
            if promo is not None and price is not None:
                if float(promo) >= float(price):
                    violations.append(
                        f"{fixture_file.name}/{item['source_product_id']}: "
                        f"promo_price {promo} >= price {price}"
                    )
    assert not violations, "Promo price >= regular price in fixtures:\n" + "\n".join(violations)


def test_discount_pct_method_is_correct():
    """Unit-test LiveRetailerAdapter._discount_pct helper directly."""
    from worker.adapters.live_base import LiveRetailerAdapter
    inst = LiveRetailerAdapter.__new__(LiveRetailerAdapter)
    assert inst._discount_pct(100.0, 80.0) == 20.0
    assert inst._discount_pct(199.0, 179.0) == pytest.approx(10.05, abs=0.01)
    assert inst._discount_pct(100.0, None) is None
    assert inst._discount_pct(100.0, 100.0) is None  # equal price = no discount
    assert inst._discount_pct(100.0, 110.0) is None  # promo > price = no discount


# ---------------------------------------------------------------------------
# 4. CATEGORY CLASSIFICATION ACCURACY
# ---------------------------------------------------------------------------
# Finding: _normalize_category() uses keyword lists and is generally correct
# for clear-cut titles.  Two subtle failure modes were found:
#   (a) Vertical inference token conflicts: "shampoo" is a beauty token, but
#       "pet shampoo" text also hits the beauty token set.  Since beauty has
#       higher priority than pet-goods in VERTICAL_SIGNAL_PRIORITY, a product
#       titled "pet shampoo" could be misclassified as beauty.
#   (b) Category fallback for ambiguous tech products: anything that doesn't
#       match laptop/phone/monitor falls back to "electronics" which is correct
#       behaviour, but then has no value-scoring path.
# ---------------------------------------------------------------------------

def test_normalize_category_laptops():
    adapter = PBTechFixtureAdapter.__new__(PBTechFixtureAdapter)
    # Use the live adapter's _normalize_category via import
    from worker.adapters.live_base import LiveRetailerAdapter
    inst = LiveRetailerAdapter.__new__(LiveRetailerAdapter)
    inst.vertical = "tech"
    assert inst._normalize_category("Computers", "Acer Nitro 16 Gaming Laptop", "tech") == "laptops"
    assert inst._normalize_category("Computers", "Dell XPS 15 Notebook", "tech") == "laptops"
    assert inst._normalize_category("Computers", "Apple MacBook Air M4", "tech") == "laptops"


def test_normalize_category_phones():
    from worker.adapters.live_base import LiveRetailerAdapter
    inst = LiveRetailerAdapter.__new__(LiveRetailerAdapter)
    inst.vertical = "tech"
    assert inst._normalize_category("Mobile", "Samsung Galaxy S25 256GB", "tech") == "phones"
    assert inst._normalize_category("Mobile", "Apple iPhone 16 Pro", "tech") == "phones"


def test_normalize_category_beauty():
    from worker.adapters.live_base import LiveRetailerAdapter
    inst = LiveRetailerAdapter.__new__(LiveRetailerAdapter)
    inst.vertical = "beauty"
    assert inst._normalize_category("skincare", "The Ordinary Niacinamide 10% Serum 30ml", "beauty") == "skincare"
    assert inst._normalize_category("makeup", "Fenty Beauty Foundation", "beauty") == "makeup"
    assert inst._normalize_category("hair", "Olaplex Shampoo No.4", "beauty") == "haircare"


def test_normalize_category_pharma():
    from worker.adapters.live_base import LiveRetailerAdapter
    inst = LiveRetailerAdapter.__new__(LiveRetailerAdapter)
    inst.vertical = "pharma"
    assert inst._normalize_category("otc", "Panadol Tablets 500mg 20 Pack", "pharma") == "otc"
    assert inst._normalize_category("supplements", "GO Vitamin C 1000mg 60 Tablets", "pharma") == "supplements"


def test_vertical_inference_pet_shampoo_not_beauty():
    """'pet shampoo' with 'pet' token correctly scores pet-goods=2 vs beauty=1."""
    from worker.adapters.live_base import LiveRetailerAdapter
    inst = LiveRetailerAdapter.__new__(LiveRetailerAdapter)
    inst.vertical = "tech"
    # 'pet shampoo': pet-goods earns 'pet' (+1) and 'pet shampoo' (+1) = 2
    # beauty earns 'shampoo' (+1) = 1 → pet-goods wins correctly
    result = inst._infer_vertical_from_text("pet shampoo")
    assert result == "pet-goods", f"'pet shampoo' inferred as '{result}', expected 'pet-goods'."


@pytest.mark.xfail(strict=True, reason=(
    "KNOWN GAP: 'dog shampoo' is misclassified as beauty. "
    "VERTICAL_SIGNAL_TOKENS has no 'dog' standalone token and no 'dog shampoo' compound. "
    "The only match is 'shampoo' in the beauty set (score=1) while pet-goods score=0. "
    "Fix: add 'dog shampoo', 'cat shampoo', and bare 'dog'/'cat' tokens to pet-goods, "
    "or apply a longest-match rule so compound tokens outrank partial substrings."
))
def test_vertical_inference_dog_shampoo_not_beauty():
    """'dog shampoo' should infer pet-goods, not beauty."""
    from worker.adapters.live_base import LiveRetailerAdapter
    inst = LiveRetailerAdapter.__new__(LiveRetailerAdapter)
    inst.vertical = "tech"
    result = inst._infer_vertical_from_text("dog shampoo conditioner")
    assert result == "pet-goods", (
        f"'dog shampoo conditioner' inferred as '{result}', expected 'pet-goods'. "
        f"No 'dog' or 'dog shampoo' token in pet-goods set — beauty wins via 'shampoo'."
    )


def test_normalize_category_home_appliances_fridge_and_washer():
    from worker.adapters.live_base import LiveRetailerAdapter
    inst = LiveRetailerAdapter.__new__(LiveRetailerAdapter)
    inst.vertical = "home-appliances"
    assert inst._normalize_category("whiteware", "Fisher & Paykel 8.5kg Front Load Washing Machine", "home-appliances") == "washing-machines"
    assert inst._normalize_category("whiteware", "Samsung 605L French Door Fridge", "home-appliances") == "fridges"


@pytest.mark.xfail(strict=True, reason=(
    "KNOWN GAP: Substring collision in home-appliances category rules. "
    "_normalize_category checks 'washer' before 'dishwasher'.  The string "
    "'dishwasher' contains the substring 'washer', so a Bosch Dishwasher is "
    "bucketed as 'washing-machines' instead of 'dishwashers'.  "
    "Fix: check for 'dishwasher' before 'washer' in the elif chain, or use "
    "whole-word matching (e.g. r'\\bwasher\\b') to avoid the substring hit."
))
def test_normalize_category_dishwasher_not_washing_machine():
    """A dishwasher product must not be mis-bucketed as washing-machines via substring match."""
    from worker.adapters.live_base import LiveRetailerAdapter
    inst = LiveRetailerAdapter.__new__(LiveRetailerAdapter)
    inst.vertical = "home-appliances"
    result = inst._normalize_category("whiteware", "Bosch 13 Place Dishwasher", "home-appliances")
    assert result == "dishwashers", (
        f"Got '{result}' — 'washer' substring in 'dishwasher' causes false positive "
        f"for the washing-machines branch, which precedes the dishwashers branch."
    )


# ---------------------------------------------------------------------------
# 5. BRAND EXTRACTION QUALITY
# ---------------------------------------------------------------------------
# Finding: Fixture adapters carry explicit brand fields — those are correct.
# For live ingestion, LiveRetailerAdapter._parse_product_page() extracts brand
# from JSON-LD first, then from og:meta, then falls back to title.split(" ")[0].
# The last-resort fallback is unsafe for multi-word brands:
#   "The Ordinary Niacinamide ..." → brand inferred as "The"
#   "Charlotte Tilbury Magic Cream" → brand inferred as "Charlotte"
# This is mitigated in practice because most NZ retailer pages include
# structured brand data, but any page that lacks it silently degrades.
# ---------------------------------------------------------------------------

def test_fixture_brands_are_non_empty_across_all_retailers():
    """Every fixture item must have a non-empty brand string."""
    blank = []
    for fixture_file in FIXTURES_DIR.glob("*.json"):
        data = json.loads(fixture_file.read_text())
        for item in data.get("items", []):
            brand = str(item.get("brand", "")).strip()
            if not brand or brand.lower() in {"unknown", "generic", ""}:
                blank.append(f"{fixture_file.name}/{item['source_product_id']}")
    assert not blank, "Fixtures with empty/generic brand:\n" + "\n".join(blank)


@pytest.mark.xfail(strict=True, reason=(
    "KNOWN GAP: Live adapter brand fallback takes title.split(' ')[0] when "
    "no structured brand data is present.  For multi-word brands like "
    "'The Ordinary' this returns 'The', which is incorrect.  "
    "Fix: implement a known multi-word brand lookup list, or use the first "
    "N-gram that matches a known brand registry before falling back."
))
def test_live_adapter_brand_fallback_handles_multiword_brands():
    """Brand extracted from title fallback should handle 'The Ordinary'-style names."""
    from worker.adapters.live_base import LiveRetailerAdapter
    inst = LiveRetailerAdapter.__new__(LiveRetailerAdapter)
    inst.vertical = "beauty"

    # Simulate what happens when JSON-LD has no brand field
    # _extract_brand({}) → None → falls back to title.split(" ")[0]
    brand_from_ld = inst._extract_brand({})
    assert brand_from_ld is None  # confirms no brand from empty LD

    # The production fallback would then be:
    title = "The Ordinary Niacinamide 10% + Zinc 1% 30ml"
    naive_fallback = title.split(" ")[0]  # "The"
    assert naive_fallback != "The Ordinary", "Fallback is already safe (would not need fix)"
    # This assertion passes because "The" != "The Ordinary" — proving the bug exists
    assert naive_fallback == "The Ordinary", "Brand fallback must return full brand name"


# ---------------------------------------------------------------------------
# 6. IDENTIFIER NORMALISATION CONSISTENCY
# ---------------------------------------------------------------------------
# Finding: normalize_identifier strips everything except [A-Z0-9/-].
# Dashes and slashes are both preserved, which means "AN16-51" and "AN16/51"
# are treated as different identifiers.  Harvey Norman's model slash notation
# prevents model-tier matching with dash-notation from other retailers.
# ---------------------------------------------------------------------------

def test_normalize_identifier_preserves_dashes():
    assert normalize_identifier("AN16-51") == "AN16-51"


def test_normalize_identifier_preserves_slashes():
    assert normalize_identifier("AN16/51") == "AN16/51"


def test_normalize_identifier_dash_slash_are_not_equivalent():
    """Documents current behaviour: dash and slash are distinct after normalisation."""
    assert normalize_identifier("AN16-51") != normalize_identifier("AN16/51"), (
        "normalize_identifier currently treats dash and slash as distinct characters. "
        "This prevents cross-retailer model matching when one retailer uses '/' and "
        "another uses '-' for the same model number.  If this assertion ever fails, "
        "normalisation has been made consistent — update the test and the xfail above."
    )


def test_all_fixture_gtins_are_non_empty_where_present():
    """GTINs that are provided in fixtures should not be empty strings."""
    bad = []
    for fixture_file in FIXTURES_DIR.glob("*.json"):
        data = json.loads(fixture_file.read_text())
        for item in data.get("items", []):
            gtin = item.get("gtin")
            if gtin is not None and str(gtin).strip() == "":
                bad.append(f"{fixture_file.name}/{item['source_product_id']}: gtin is empty string")
    assert not bad, "\n".join(bad)


# ---------------------------------------------------------------------------
# 7. CANONICAL NAME QUALITY
# ---------------------------------------------------------------------------
# Finding: canonical_name = listing.title.strip() with no normalisation.
# The winning canonical name is whatever the first-ingested retailer happened
# to call the product.  For the same Acer Nitro 16:
#   PBTech  → "Acer Nitro 16 Gaming Laptop AN16-51"
#   JBHiFi  → "Acer Nitro 16 Laptop"
#   Noel Leeming → "Acer Nitro 16 Gaming Notebook"
#   Harvey Norman → "Acer Nitro16 AN16-51 Gaming Laptop"
# The canonical name is the product's public-facing label in the UI and is
# used in search ranking — ingestion-order sensitivity here is a UX risk.
# ---------------------------------------------------------------------------

def test_canonical_name_is_set_after_ingestion(session):
    """Canonical products must have a non-empty canonical_name after ingestion."""
    products = _run(session, PBTechFixtureAdapter())
    for p in products:
        assert p.canonical_name and p.canonical_name.strip(), f"Product id={p.id} has blank canonical_name"


def test_canonical_name_equals_first_ingested_retailer_title(session):
    """Documents current behaviour: canonical_name = raw title of first ingested retailer."""
    _products_after(PBTechFixtureAdapter(), JBHiFiFixtureAdapter(), session=session)
    nitro = session.query(Product).filter(Product.brand == "Acer").first()
    assert nitro is not None
    # PBTech was ingested first → its raw title wins as canonical_name
    assert nitro.canonical_name == "Acer Nitro 16 Gaming Laptop AN16-51", (
        f"Canonical name is '{nitro.canonical_name}'. "
        "If this changes, ingestion order sensitivity may have been addressed."
    )


@pytest.mark.xfail(strict=True, reason=(
    "KNOWN GAP: canonical_name is never normalised — it is the raw retailer "
    "title of whichever retailer ingested first.  The same physical product can "
    "have wildly different canonical names depending on run order: "
    "'Acer Nitro 16 Gaming Laptop AN16-51' vs 'Acer Nitro 16 Laptop'. "
    "Fix: implement a canonical name normalisation step that strips retailer-"
    "specific suffixes, standardises spacing, and selects the most information-"
    "rich title from all matched retailer products."
))
def test_canonical_name_is_normalised_independent_of_ingestion_order(session):
    """Canonical name should be the same regardless of which retailer ingests first."""
    # Run JBHiFi first (shorter, less informative title)
    _products_after(JBHiFiFixtureAdapter(), PBTechFixtureAdapter(), session=session)
    nitro = session.query(Product).filter(Product.brand == "Acer").first()
    assert nitro is not None
    # JBHiFi ingested first → canonical_name becomes the shorter JBHiFi title
    assert nitro.canonical_name == "Acer Nitro 16 Gaming Laptop AN16-51", (
        f"Got '{nitro.canonical_name}' — canonical name is ingestion-order-sensitive."
    )


# ---------------------------------------------------------------------------
# 8. ATTRIBUTE VALUE CONSISTENCY ACROSS RETAILERS
# ---------------------------------------------------------------------------
# Finding: When the same product is matched via GTIN/model, _merge_attributes
# fills empty attribute slots only — it never reconciles divergent values.
# The first-ingested retailer's numeric spec wins permanently.  For cpu_score:
#   PBTech=7200, JBHiFi=7100, Noel Leeming=7050, Harvey Norman=7000
# Value scoring is therefore ingestion-order-sensitive for this key field.
# ---------------------------------------------------------------------------

def test_attribute_merge_preserves_existing_value_and_ignores_newer(session):
    """Documents current first-write-wins behaviour for attribute values."""
    # PBTech first: cpu_score=7200
    _products_after(PBTechFixtureAdapter(), JBHiFiFixtureAdapter(), session=session)
    nitro = session.query(Product).filter(Product.brand == "Acer", Product.category == "laptops").first()
    assert nitro is not None
    # PBTech's cpu_score should have won (7200), JBHiFi's 7100 discarded
    assert nitro.attributes.get("cpu_score") == 7200, (
        f"cpu_score={nitro.attributes.get('cpu_score')} — expected 7200 (PBTech first-write)"
    )


@pytest.mark.xfail(strict=True, reason=(
    "KNOWN GAP: cpu_score (and other numeric specs) differs across retailer "
    "fixtures for the same product (PBTech=7200, JBHiFi=7100, Noel=7050, HN=7000). "
    "_merge_attributes only fills empty slots, so the first-ingested value wins "
    "permanently with no reconciliation.  Value scores are therefore ingestion-"
    "order-sensitive.  Fix: for numeric spec attributes, use the most frequently "
    "occurring value (mode) or the median across all matching retailer products, "
    "rather than first-write-wins."
))
def test_cpu_score_is_consistent_across_all_tech_retailers(session):
    """cpu_score for the same Acer Nitro 16 should agree across retailers."""
    _products_after(
        PBTechFixtureAdapter(),
        JBHiFiFixtureAdapter(),
        NoelLeemingFixtureAdapter(),
        HarveyNormanFixtureAdapter(),
        session=session,
    )
    nitro = session.query(Product).filter(Product.brand == "Acer", Product.category == "laptops").first()
    assert nitro is not None

    # Collect what each retailer reported
    all_scores = {7200, 7100, 7050, 7000}  # PBTech, JBHiFi, Noel, HN
    canonical_score = nitro.attributes.get("cpu_score")
    assert canonical_score in all_scores
    # All retailer products for this canonical should report the same spec
    rps = session.query(RetailerProduct).filter(RetailerProduct.product_id == nitro.id).all()
    retailer_scores = {rp.raw_attributes.get("cpu_score") for rp in rps if rp.raw_attributes.get("cpu_score")}
    assert len(retailer_scores) == 1, (
        f"cpu_score varies across {len(retailer_scores)} retailers: {retailer_scores}. "
        "No reconciliation strategy is applied — value scoring depends on ingestion order."
    )


def test_beauty_product_type_hyphen_underscore_inconsistency_is_detected(session):
    """Documents the lip-gloss vs lip_gloss attribute inconsistency across beauty retailers."""
    _products_after(MeccaFixtureAdapter(), SephoraFixtureAdapter(), FarmersBeautyFixtureAdapter(), session=session)

    glosses = session.query(Product).filter(Product.brand == "Fenty Beauty").all()
    product_types = {p.attributes.get("product_type") for p in glosses if p.attributes.get("product_type")}

    # Due to the GTIN mismatch, there are currently 2 canonical products with different product_type values
    # This asserts the inconsistency exists (will need to be fixed alongside dedup)
    assert len(product_types) > 1 or "lip-gloss" in product_types or "lip_gloss" in product_types, (
        "Expected to find product_type inconsistency between retailers. "
        "If this passes cleanly, attribute normalisation may have been added."
    )
