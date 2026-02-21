from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Retailer

DEFAULT_RETAILERS = [
    ("pb-tech", "PB Tech", "tech"),
    ("jb-hi-fi", "JB Hi-Fi", "tech"),
    ("noel-leeming", "Noel Leeming", "tech"),
    ("harvey-norman", "Harvey Norman", "tech"),
    ("apple", "Apple", "tech"),
    ("chemist-warehouse", "Chemist Warehouse", "pharmaceuticals"),
    ("bargain-chemist", "Bargain Chemist", "pharmaceuticals"),
    ("life-pharmacy", "Life Pharmacy", "pharmaceuticals"),
    ("mecca", "Mecca", "beauty"),
    ("sephora", "Sephora", "beauty"),
    ("farmers", "Farmers", "home-appliances"),
    ("mighty-ape", "Mighty Ape", "tech"),
    ("heathcotes", "Heathcotes", "home-appliances"),
    ("the-warehouse", "The Warehouse", "home-appliances"),
    ("supplements-co-nz", "Supplements.co.nz", "supplements"),
    ("animates", "Animates", "pet-goods"),
    ("petdirect", "Petdirect", "pet-goods"),
    ("pet-co-nz", "Pet.co.nz", "pet-goods"),
]


def seed_retailers(db: Session) -> None:
    existing = {row[0] for row in db.execute(select(Retailer.slug)).all()}
    for slug, name, vertical in DEFAULT_RETAILERS:
        if slug not in existing:
            db.add(Retailer(slug=slug, display_name=name, vertical=vertical, active=True))
    db.commit()
