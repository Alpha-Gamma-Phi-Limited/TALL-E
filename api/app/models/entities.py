from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base


JsonDict = dict[str, object]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class Retailer(Base):
    __tablename__ = "retailers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128))
    vertical: Mapped[str] = mapped_column(String(32), index=True, default="tech")
    active: Mapped[bool] = mapped_column(default=True)

    listings: Mapped[list[RetailerProduct]] = relationship(back_populates="retailer")
    ingestion_runs: Mapped[list[IngestionRun]] = relationship(back_populates="retailer")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    canonical_name: Mapped[str] = mapped_column(String(512), index=True)
    vertical: Mapped[str] = mapped_column(String(32), index=True, default="tech")
    brand: Mapped[str] = mapped_column(String(128), index=True)
    category: Mapped[str] = mapped_column(String(128), index=True)
    model_number: Mapped[str | None] = mapped_column(String(128), index=True)
    gtin: Mapped[str | None] = mapped_column(String(64), index=True)
    mpn: Mapped[str | None] = mapped_column(String(128), index=True)
    image_url: Mapped[str | None] = mapped_column(Text)
    attributes: Mapped[JsonDict] = mapped_column(JSON, default=dict)
    searchable_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    retailer_products: Mapped[list[RetailerProduct]] = relationship(back_populates="product")


class RetailerProduct(Base):
    __tablename__ = "retailer_products"
    __table_args__ = (UniqueConstraint("retailer_id", "source_product_id", name="uq_retailer_source_product"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    retailer_id: Mapped[int] = mapped_column(ForeignKey("retailers.id"), index=True)
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id"), index=True)
    source_product_id: Mapped[str] = mapped_column(String(256))
    title: Mapped[str] = mapped_column(String(512), index=True)
    url: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    raw_attributes: Mapped[JsonDict] = mapped_column(JSON, default=dict)
    availability: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    retailer: Mapped[Retailer] = relationship(back_populates="listings")
    product: Mapped[Product | None] = relationship(back_populates="retailer_products")
    prices: Mapped[list[Price]] = relationship(back_populates="retailer_product", cascade="all, delete-orphan")
    latest_price: Mapped[LatestPrice | None] = relationship(back_populates="retailer_product", uselist=False)


class Price(Base):
    __tablename__ = "prices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    retailer_product_id: Mapped[str] = mapped_column(ForeignKey("retailer_products.id"), index=True)
    price_nzd: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    promo_price_nzd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    promo_text: Mapped[str | None] = mapped_column(Text)
    discount_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    retailer_product: Mapped[RetailerProduct] = relationship(back_populates="prices")


class LatestPrice(Base):
    __tablename__ = "latest_prices"

    retailer_product_id: Mapped[str] = mapped_column(ForeignKey("retailer_products.id"), primary_key=True)
    price_nzd: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    promo_price_nzd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    promo_text: Mapped[str | None] = mapped_column(Text)
    discount_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    retailer_product: Mapped[RetailerProduct] = relationship(back_populates="latest_price")


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    retailer_id: Mapped[int] = mapped_column(ForeignKey("retailers.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    items_total: Mapped[int] = mapped_column(Integer, default=0)
    items_new: Mapped[int] = mapped_column(Integer, default=0)
    items_updated: Mapped[int] = mapped_column(Integer, default=0)
    items_failed: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    retailer: Mapped[Retailer] = relationship(back_populates="ingestion_runs")


class ProductOverride(Base):
    __tablename__ = "product_overrides"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    retailer_product_id: Mapped[str] = mapped_column(ForeignKey("retailer_products.id"), unique=True, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
