from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.seed import seed_retailers
from app.main import app
from app.models import IngestionRun, LatestPrice, Product, Retailer, RetailerProduct

TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture()
def session() -> Session:
    engine = create_engine(TEST_DB_URL)
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    seed_retailers(db)

    pb = db.query(Retailer).filter(Retailer.slug == "pb-tech").one()
    jb = db.query(Retailer).filter(Retailer.slug == "jb-hi-fi").one()
    cw = db.query(Retailer).filter(Retailer.slug == "chemist-warehouse").one()
    bc = db.query(Retailer).filter(Retailer.slug == "bargain-chemist").one()

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
        vertical="pharma",
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
