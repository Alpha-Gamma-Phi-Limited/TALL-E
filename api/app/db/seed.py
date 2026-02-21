from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Retailer

DEFAULT_RETAILERS = [
    ("pb-tech", "PB Tech", "tech"),
    ("jb-hi-fi", "JB Hi-Fi", "tech"),
    ("noel-leeming", "Noel Leeming", "tech"),
    ("harvey-norman", "Harvey Norman", "tech"),
    ("apple", "Apple", "tech"),
    ("chemist-warehouse", "Chemist Warehouse", "pharma"),
    ("bargain-chemist", "Bargain Chemist", "pharma"),
    ("life-pharmacy", "Life Pharmacy", "pharma"),
    ("mecca", "Mecca", "beauty"),
    ("sephora", "Sephora", "beauty"),
    ("farmers-beauty", "Farmers Beauty", "beauty"),
]


def seed_retailers(db: Session) -> None:
    existing = {row[0] for row in db.execute(select(Retailer.slug)).all()}
    for slug, name, vertical in DEFAULT_RETAILERS:
        if slug not in existing:
            db.add(Retailer(slug=slug, display_name=name, vertical=vertical, active=True))
    db.commit()
