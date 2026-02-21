"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-02-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    is_postgres = dialect_name == "postgresql"

    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")

    op.create_table(
        "retailers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(length=64), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("canonical_name", sa.String(length=512), nullable=False),
        sa.Column("brand", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("model_number", sa.String(length=128), nullable=True),
        sa.Column("gtin", sa.String(length=64), nullable=True),
        sa.Column("mpn", sa.String(length=128), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("attributes", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("searchable_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "retailer_products",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("retailer_id", sa.Integer(), sa.ForeignKey("retailers.id"), nullable=False),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("source_product_id", sa.String(length=256), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("raw_attributes", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("availability", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("retailer_id", "source_product_id", name="uq_retailer_source_product"),
    )

    op.create_table(
        "prices",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("retailer_product_id", sa.String(length=36), sa.ForeignKey("retailer_products.id"), nullable=False),
        sa.Column("price_nzd", sa.Numeric(10, 2), nullable=False),
        sa.Column("promo_price_nzd", sa.Numeric(10, 2), nullable=True),
        sa.Column("promo_text", sa.Text(), nullable=True),
        sa.Column("discount_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "latest_prices",
        sa.Column("retailer_product_id", sa.String(length=36), sa.ForeignKey("retailer_products.id"), primary_key=True),
        sa.Column("price_nzd", sa.Numeric(10, 2), nullable=False),
        sa.Column("promo_price_nzd", sa.Numeric(10, 2), nullable=True),
        sa.Column("promo_text", sa.Text(), nullable=True),
        sa.Column("discount_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("retailer_id", sa.Integer(), sa.ForeignKey("retailers.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("items_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_new", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "product_overrides",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("retailer_product_id", sa.String(length=36), sa.ForeignKey("retailer_products.id"), nullable=False, unique=True),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("ix_products_brand", "products", ["brand"])
    op.create_index("ix_products_category", "products", ["category"])
    op.create_index("ix_products_model_number", "products", ["model_number"])
    op.create_index("ix_products_gtin", "products", ["gtin"])
    op.create_index("ix_products_mpn", "products", ["mpn"])
    op.create_index("ix_retailer_products_product_id", "retailer_products", ["product_id"])
    op.create_index("ix_retailer_products_retailer_id", "retailer_products", ["retailer_id"])
    op.create_index("ix_prices_retailer_product_id", "prices", ["retailer_product_id"])
    op.create_index("ix_prices_captured_at", "prices", ["captured_at"])
    op.create_index("ix_latest_prices_captured_at", "latest_prices", ["captured_at"])
    op.create_index("ix_ingestion_runs_retailer_id", "ingestion_runs", ["retailer_id"])

    if is_postgres:
        op.create_index("ix_products_attributes_gin", "products", ["attributes"], postgresql_using="gin")
        op.execute(
            "CREATE INDEX ix_products_canonical_name_trgm ON products USING gin (canonical_name gin_trgm_ops)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.drop_index("ix_products_canonical_name_trgm", table_name="products")
        op.drop_index("ix_products_attributes_gin", table_name="products")

    op.drop_index("ix_ingestion_runs_retailer_id", table_name="ingestion_runs")
    op.drop_index("ix_latest_prices_captured_at", table_name="latest_prices")
    op.drop_index("ix_prices_captured_at", table_name="prices")
    op.drop_index("ix_prices_retailer_product_id", table_name="prices")
    op.drop_index("ix_retailer_products_retailer_id", table_name="retailer_products")
    op.drop_index("ix_retailer_products_product_id", table_name="retailer_products")
    op.drop_index("ix_products_mpn", table_name="products")
    op.drop_index("ix_products_gtin", table_name="products")
    op.drop_index("ix_products_model_number", table_name="products")
    op.drop_index("ix_products_category", table_name="products")
    op.drop_index("ix_products_brand", table_name="products")

    op.drop_table("product_overrides")
    op.drop_table("ingestion_runs")
    op.drop_table("latest_prices")
    op.drop_table("prices")
    op.drop_table("retailer_products")
    op.drop_table("products")
    op.drop_table("retailers")
