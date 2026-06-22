"""initial schema

Revision ID: 20260620_0001
Revises:
Create Date: 2026-06-20
"""

from alembic import op
import sqlalchemy as sa


revision = "20260620_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("openid", sa.String(128), nullable=True, unique=True),
        sa.Column("unionid", sa.String(128), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("nickname", sa.String(128), nullable=True),
        sa.Column("is_realname_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "diagnosis_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("anonymous_token", sa.String(128), nullable=False),
        sa.Column("original_input_json", sa.JSON(), nullable=False),
        sa.Column("input_type", sa.String(32), nullable=False),
        sa.Column("voice_transcript", sa.Text(), nullable=True),
        sa.Column("question_round_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="diagnosing"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_diagnosis_sessions_anonymous_token", "diagnosis_sessions", ["anonymous_token"])
    op.create_table(
        "diagnosis_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("diagnosis_sessions.id"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_diagnosis_messages_session_id", "diagnosis_messages", ["session_id"])
    op.create_table(
        "diagnosis_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("diagnosis_sessions.id"), nullable=False),
        sa.Column("primary_category", sa.String(64), nullable=False),
        sa.Column("secondary_category", sa.String(64), nullable=False),
        sa.Column("urgency_level", sa.String(8), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("model_provider", sa.String(64), nullable=False),
        sa.Column("model_version", sa.String(128), nullable=False),
        sa.Column("prompt_version", sa.String(64), nullable=False),
        sa.Column("knowledge_version", sa.String(128), nullable=False),
        sa.Column("cost_total", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_diagnosis_results_session_id", "diagnosis_results", ["session_id"])
    op.create_table(
        "repair_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("anonymous_token", sa.String(128), nullable=True),
        sa.Column("diagnosis_result_id", sa.String(36), sa.ForeignKey("diagnosis_results.id"), nullable=False),
        sa.Column("house_area", sa.String(128), nullable=True),
        sa.Column("actual_solution", sa.Text(), nullable=True),
        sa.Column("actual_cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("provider_name", sa.String(128), nullable=True),
        sa.Column("reminder_status", sa.String(32), nullable=False, server_default="none"),
        sa.Column("is_resolved", sa.Boolean(), nullable=True),
        sa.Column("is_recurred", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_repair_records_anonymous_token", "repair_records", ["anonymous_token"])
    op.create_table(
        "cost_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), nullable=True),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("capability", sa.String(64), nullable=False),
        sa.Column("model_version", sa.String(128), nullable=True),
        sa.Column("tokens", sa.Integer(), nullable=True),
        sa.Column("call_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("cost_estimate", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("estimated", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_cost_logs_session_id", "cost_logs", ["session_id"])
    op.create_table(
        "content_safety_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), nullable=True),
        sa.Column("content_source", sa.String(64), nullable=False),
        sa.Column("result", sa.String(32), nullable=False),
        sa.Column("hit_categories", sa.String(256), nullable=True),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_content_safety_logs_session_id", "content_safety_logs", ["session_id"])
    op.create_table(
        "quota_usage",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("subject_type", sa.String(32), nullable=False),
        sa.Column("subject_id", sa.String(128), nullable=False),
        sa.Column("quota_date", sa.Date(), nullable=False),
        sa.Column("full_diagnosis_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("subject_type", "subject_id", "quota_date", name="uq_quota_subject_date"),
    )


def downgrade() -> None:
    op.drop_table("quota_usage")
    op.drop_index("ix_content_safety_logs_session_id", table_name="content_safety_logs")
    op.drop_table("content_safety_logs")
    op.drop_index("ix_cost_logs_session_id", table_name="cost_logs")
    op.drop_table("cost_logs")
    op.drop_index("ix_repair_records_anonymous_token", table_name="repair_records")
    op.drop_table("repair_records")
    op.drop_index("ix_diagnosis_results_session_id", table_name="diagnosis_results")
    op.drop_table("diagnosis_results")
    op.drop_index("ix_diagnosis_messages_session_id", table_name="diagnosis_messages")
    op.drop_table("diagnosis_messages")
    op.drop_index("ix_diagnosis_sessions_anonymous_token", table_name="diagnosis_sessions")
    op.drop_table("diagnosis_sessions")
    op.drop_table("users")
