from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.seed import seed_retailers
from app.main import app
from app.models import IngestionRun, LatestPrice, Product, Retailer, RetailerProduct

TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture()
def session() -> Session:
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    seed_retailers(db)

    pb = db.query(Retailer).filter(Retailer.slug == "pb-tech").one()
    jb = db.query(Retailer).filter(Retailer.slug == "jb-hi-fi").one()
    cw = db.query(Retailer).filter(Retailer.slug == "chemist-warehouse").one()
    bc = db.query(Retailer).filter(Retailer.slug == "bargain-chemist").one()
    mecca = db.query(Retailer).filter(Retailer.slug == "mecca").one()
    sephora = db.query(Retailer).filter(Retailer.slug == "sephora").one()
    farmers_beauty = db.query(Retailer).filter(Retailer.slug == "farmers").one()
    animates = db.query(Retailer).filter(Retailer.slug == "animates").one()
    petdirect = db.query(Retailer).filter(Retailer.slug == "petdirect").one()
    pet_co_nz = db.query(Retailer).filter(Retailer.slug == "pet-co-nz").one()

    product = Product(
        canonical_name="Acer Nitro 16 Laptop",
        vertical="tech",
        brand="Acer",
        category="laptops",
        model_number="AN16-51",
        gtin="1234567890123",
        mpn="AN16-51-99",
        attributes={"cpu_score": 7000, "ram_gb": 16, "storage_gb": 512},
        searchable_text="acer nitro 16 an16-51",
    )
    db.add(product)
    db.flush()

    pharma_product = Product(
        canonical_name="Panadol Tablets 500mg 20 Pack",
        vertical="pharmaceuticals",
        brand="Panadol",
        category="otc",
        model_number="PAN-500-20",
        gtin="9300673830010",
        mpn="PAN500-20",
        attributes={"active_ingredient": "paracetamol", "strength": "500mg", "form": "tablet", "pack_size": 20},
        searchable_text="panadol tablets 500mg 20 pack",
    )
    db.add(pharma_product)
    db.flush()

    beauty_product = Product(
        canonical_name="The Ordinary Niacinamide 10% + Zinc 1% 30ml",
        vertical="beauty",
        brand="The Ordinary",
        category="skincare",
        model_number="NIA-30ML",
        gtin="769915190069",
        mpn="ORD-NIA-30",
        attributes={"product_type": "serum", "size_ml": 30, "skin_concern": "oil-control"},
        searchable_text="the ordinary niacinamide zinc serum 30ml",
    )
    db.add(beauty_product)
    db.flush()

    home_product = Product(
        canonical_name="Samsung 635L Side by Side Fridge",
        vertical="home-appliances",
        brand="Samsung",
        category="fridges",
        model_number="SRS674DLS",
        gtin="8806092080353",
        mpn="SRS674DLS",
        attributes={"capacity_l": 635, "energy_rating": 3.5, "type": "side-by-side"},
        searchable_text="samsung 635l side by side fridge",
    )
    db.add(home_product)
    db.flush()

    pet_product = Product(
        canonical_name="Royal Canin Maxi Adult Dry Dog Food 15kg",
        vertical="pet-goods",
        brand="Royal Canin",
        category="pet-food",
        model_number="MAXI-ADULT-15KG",
        gtin="3182550402219",
        mpn="RC-MAXI-15",
        attributes={"pet_type": "dog", "weight_kg": 15},
        searchable_text="royal canin maxi adult dog food 15kg",
    )
    db.add(pet_product)
    db.flush()

    rp1 = RetailerProduct(
        retailer_id=pb.id,
        product_id=product.id,
        source_product_id="pb-1",
        title="Acer Nitro 16 Gaming Laptop",
        url="https://example.com/pb/acer-nitro-16",
        image_url="https://example.com/pb/acer.jpg",
        raw_attributes={"ram_gb": 16},
        availability="in_stock",
    )
    rp2 = RetailerProduct(
        retailer_id=jb.id,
        product_id=product.id,
        source_product_id="jb-1",
        title="Acer Nitro 16",
        url="https://example.com/jb/acer-nitro-16",
        image_url="https://example.com/jb/acer.jpg",
        raw_attributes={"ram_gb": 16},
        availability="in_stock",
    )
    db.add_all([rp1, rp2])
    db.flush()

    rp3 = RetailerProduct(
        retailer_id=cw.id,
        product_id=pharma_product.id,
        source_product_id="cw-1",
        title="Panadol Tablets 500mg 20 Pack",
        url="https://example.com/cw/panadol-500-20",
        image_url="https://example.com/cw/panadol.jpg",
        raw_attributes={"strength": "500mg", "form": "tablet", "pack_size": 20},
        availability="in_stock",
    )
    rp4 = RetailerProduct(
        retailer_id=bc.id,
        product_id=pharma_product.id,
        source_product_id="bc-1",
        title="Panadol 500mg Tablets 20",
        url="https://example.com/bc/panadol-500-20",
        image_url="https://example.com/bc/panadol.jpg",
        raw_attributes={"strength": "500mg", "form": "tablet", "pack_size": 20},
        availability="in_stock",
    )
    db.add_all([rp3, rp4])
    db.flush()

    rp5 = RetailerProduct(
        retailer_id=mecca.id,
        product_id=beauty_product.id,
        source_product_id="mecca-1",
        title="The Ordinary Niacinamide 10% + Zinc 1% 30ml",
        url="https://example.com/mecca/niacinamide-30",
        image_url="https://example.com/mecca/niacinamide.jpg",
        raw_attributes={"product_type": "serum", "size_ml": 30},
        availability="in_stock",
    )
    rp6 = RetailerProduct(
        retailer_id=sephora.id,
        product_id=beauty_product.id,
        source_product_id="sephora-1",
        title="The Ordinary Niacinamide 10% + Zinc 1% Serum 30ml",
        url="https://example.com/sephora/niacinamide-30",
        image_url="https://example.com/sephora/niacinamide.jpg",
        raw_attributes={"product_type": "serum", "size_ml": 30},
        availability="in_stock",
    )
    rp7 = RetailerProduct(
        retailer_id=farmers_beauty.id,
        product_id=beauty_product.id,
        source_product_id="farmers-1",
        title="The Ordinary Niacinamide 10% + Zinc 1% 30ml",
        url="https://example.com/farmers/niacinamide-30",
        image_url="https://example.com/farmers/niacinamide.jpg",
        raw_attributes={"product_type": "serum", "size_ml": 30},
        availability="in_stock",
    )
    rp8 = RetailerProduct(
        retailer_id=farmers_beauty.id,
        product_id=home_product.id,
        source_product_id="farmers-home-1",
        title="Samsung 635L Side by Side Fridge",
        url="https://example.com/farmers/samsung-fridge",
        image_url="https://example.com/farmers/fridge.jpg",
        raw_attributes={"capacity_l": 635, "energy_rating": 3.5},
        availability="in_stock",
    )
    rp9 = RetailerProduct(
        retailer_id=animates.id,
        product_id=pet_product.id,
        source_product_id="animates-pet-1",
        title="Royal Canin Maxi Adult Dry Dog Food 15kg",
        url="https://example.com/animates/royal-canin-maxi-adult-15kg",
        image_url="https://example.com/animates/royal-canin-maxi-adult-15kg.jpg",
        raw_attributes={"pet_type": "dog", "weight_kg": 15},
        availability="in_stock",
    )
    rp10 = RetailerProduct(
        retailer_id=petdirect.id,
        product_id=pet_product.id,
        source_product_id="petdirect-pet-1",
        title="Royal Canin Maxi Adult Dog Food 15kg",
        url="https://example.com/petdirect/royal-canin-maxi-adult-15kg",
        image_url="https://example.com/petdirect/royal-canin-maxi-adult-15kg.jpg",
        raw_attributes={"pet_type": "dog", "weight_kg": 15},
        availability="in_stock",
    )
    rp11 = RetailerProduct(
        retailer_id=pet_co_nz.id,
        product_id=pet_product.id,
        source_product_id="pet-co-nz-pet-1",
        title="Royal Canin Maxi Adult 15kg",
        url="https://example.com/pet-co-nz/royal-canin-maxi-adult-15kg",
        image_url="https://example.com/pet-co-nz/royal-canin-maxi-adult-15kg.jpg",
        raw_attributes={"pet_type": "dog", "weight_kg": 15},
        availability="in_stock",
    )
    db.add_all([rp5, rp6, rp7, rp8, rp9, rp10, rp11])
    db.flush()

    db.add_all(
        [
            LatestPrice(
                retailer_product_id=rp1.id,
                price_nzd=Decimal("1999.00"),
                promo_price_nzd=Decimal("1799.00"),
                promo_text="Save 10%",
                discount_pct=Decimal("10.00"),
                captured_at=datetime.now(timezone.utc),
            ),
            LatestPrice(
                retailer_product_id=rp2.id,
                price_nzd=Decimal("1899.00"),
                promo_price_nzd=None,
                promo_text=None,
                discount_pct=None,
                captured_at=datetime.now(timezone.utc),
            ),
            LatestPrice(
                retailer_product_id=rp3.id,
                price_nzd=Decimal("6.99"),
                promo_price_nzd=Decimal("5.99"),
                promo_text="Save",
                discount_pct=Decimal("14.31"),
                captured_at=datetime.now(timezone.utc),
            ),
            LatestPrice(
                retailer_product_id=rp4.id,
                price_nzd=Decimal("6.49"),
                promo_price_nzd=None,
                promo_text=None,
                discount_pct=None,
                captured_at=datetime.now(timezone.utc),
            ),
            LatestPrice(
                retailer_product_id=rp5.id,
                price_nzd=Decimal("14.00"),
                promo_price_nzd=None,
                promo_text=None,
                discount_pct=None,
                captured_at=datetime.now(timezone.utc),
            ),
            LatestPrice(
                retailer_product_id=rp6.id,
                price_nzd=Decimal("15.00"),
                promo_price_nzd=Decimal("12.99"),
                promo_text="Beauty Pass offer",
                discount_pct=Decimal("13.40"),
                captured_at=datetime.now(timezone.utc),
            ),
            LatestPrice(
                retailer_product_id=rp7.id,
                price_nzd=Decimal("13.99"),
                promo_price_nzd=None,
                promo_text=None,
                discount_pct=None,
                captured_at=datetime.now(timezone.utc),
            ),
            LatestPrice(
                retailer_product_id=rp8.id,
                price_nzd=Decimal("2499.00"),
                promo_price_nzd=Decimal("2199.00"),
                promo_text="Special",
                discount_pct=Decimal("12.00"),
                captured_at=datetime.now(timezone.utc),
            ),
            LatestPrice(
                retailer_product_id=rp9.id,
                price_nzd=Decimal("179.99"),
                promo_price_nzd=Decimal("159.99"),
                promo_text="Club price",
                discount_pct=Decimal("11.11"),
                captured_at=datetime.now(timezone.utc),
            ),
            LatestPrice(
                retailer_product_id=rp10.id,
                price_nzd=Decimal("174.99"),
                promo_price_nzd=Decimal("164.99"),
                promo_text="Auto-ship save",
                discount_pct=Decimal("5.71"),
                captured_at=datetime.now(timezone.utc),
            ),
            LatestPrice(
                retailer_product_id=rp11.id,
                price_nzd=Decimal("169.99"),
                promo_price_nzd=None,
                promo_text=None,
                discount_pct=None,
                captured_at=datetime.now(timezone.utc),
            ),
            IngestionRun(
                retailer_id=pb.id,
                status="completed",
                items_total=10,
                items_new=3,
                items_updated=5,
                items_failed=2,
            ),
        ]
    )
    db.commit()

    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(session: Session) -> TestClient:
    from app.db.session import get_db

    def _get_db() -> Session:
        return session

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
