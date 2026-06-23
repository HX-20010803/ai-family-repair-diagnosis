"""add houses and rooms

Revision ID: 20260622_0003
Revises: 20260621_0002
Create Date: 2026-06-22
"""

from alembic import op
import sqlalchemy as sa


revision = "20260622_0003"
down_revision = "20260621_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "houses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("anonymous_token", sa.String(128), nullable=False),
        sa.Column("city", sa.String(64), nullable=False),
        sa.Column("city_tier", sa.String(8), nullable=False, server_default="other"),
        sa.Column("community_name", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_houses_anonymous_token", "houses", ["anonymous_token"])

    op.create_table(
        "rooms",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("house_id", sa.String(36), sa.ForeignKey("houses.id"), nullable=False),
        sa.Column("room_name", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_rooms_house_id", "rooms", ["house_id"])


def downgrade() -> None:
    op.drop_index("ix_rooms_house_id", table_name="rooms")
    op.drop_table("rooms")
    op.drop_index("ix_houses_anonymous_token", table_name="houses")
    op.drop_table("houses")
