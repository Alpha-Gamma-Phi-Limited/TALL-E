import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from worker.models import Base, Retailer


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.add_all(
        [
            Retailer(slug="pb-tech", display_name="PB Tech", vertical="tech", active=True),
            Retailer(slug="jb-hi-fi", display_name="JB Hi-Fi", vertical="tech", active=True),
            Retailer(slug="noel-leeming", display_name="Noel Leeming", vertical="tech", active=True),
            Retailer(slug="harvey-norman", display_name="Harvey Norman", vertical="tech", active=True),
            Retailer(slug="chemist-warehouse", display_name="Chemist Warehouse", vertical="pharma", active=True),
            Retailer(slug="bargain-chemist", display_name="Bargain Chemist", vertical="pharma", active=True),
            Retailer(slug="life-pharmacy", display_name="Life Pharmacy", vertical="pharma", active=True),
        ]
    )
    db.commit()
    try:
        yield db
    finally:
        db.close()
