"""add vertical columns for multi-vertical catalog

Revision ID: 0002_add_vertical_columns
Revises: 0001_initial
Create Date: 2026-02-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_add_vertical_columns"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("retailers", sa.Column("vertical", sa.String(length=32), nullable=False, server_default="tech"))
    op.add_column("products", sa.Column("vertical", sa.String(length=32), nullable=False, server_default="tech"))

    op.create_index("ix_retailers_vertical", "retailers", ["vertical"])
    op.create_index("ix_products_vertical", "products", ["vertical"])
    op.create_index("ix_products_vertical_category_brand", "products", ["vertical", "category", "brand"])


def downgrade() -> None:
    op.drop_index("ix_products_vertical_category_brand", table_name="products")
    op.drop_index("ix_products_vertical", table_name="products")
    op.drop_index("ix_retailers_vertical", table_name="retailers")

    op.drop_column("products", "vertical")
    op.drop_column("retailers", "vertical")
