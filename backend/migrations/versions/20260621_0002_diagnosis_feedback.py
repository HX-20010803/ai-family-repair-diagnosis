"""add diagnosis feedback

Revision ID: 20260621_0002
Revises: 20260620_0001
Create Date: 2026-06-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260621_0002"
down_revision = "20260620_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "diagnosis_feedback",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("result_id", sa.String(36), sa.ForeignKey("diagnosis_results.id"), nullable=False),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("diagnosis_sessions.id"), nullable=False),
        sa.Column("anonymous_token", sa.String(128), nullable=False),
        sa.Column("rating", sa.String(32), nullable=False),
        sa.Column("reason_tags", sa.JSON(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("result_id", "anonymous_token", name="uq_feedback_result_anonymous"),
    )
    op.create_index("ix_diagnosis_feedback_result_id", "diagnosis_feedback", ["result_id"])
    op.create_index("ix_diagnosis_feedback_session_id", "diagnosis_feedback", ["session_id"])
    op.create_index("ix_diagnosis_feedback_anonymous_token", "diagnosis_feedback", ["anonymous_token"])


def downgrade() -> None:
    op.drop_index("ix_diagnosis_feedback_anonymous_token", table_name="diagnosis_feedback")
    op.drop_index("ix_diagnosis_feedback_session_id", table_name="diagnosis_feedback")
    op.drop_index("ix_diagnosis_feedback_result_id", table_name="diagnosis_feedback")
    op.drop_table("diagnosis_feedback")
