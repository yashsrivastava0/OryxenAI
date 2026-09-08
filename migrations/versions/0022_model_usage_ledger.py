"""Add durable provider-neutral model usage, attempts, and quota windows."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0022_model_usage_ledger"
down_revision: str | None = "0021_model_call_cache"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "model_operations",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("operation_key", sa.Text(), nullable=False, unique=True),
        sa.Column("owner_id_hash", sa.Text(), nullable=False, server_default=""),
        sa.Column("session_id", sa.Text(), nullable=False, server_default=""),
        sa.Column("run_id", sa.Text(), nullable=False, server_default=""),
        sa.Column("job_id", sa.Text(), nullable=False, server_default=""),
        sa.Column("agent", sa.Text(), nullable=False, server_default=""),
        sa.Column("stage", sa.Text(), nullable=False, server_default=""),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("routing_policy_version", sa.Text(), nullable=False, server_default=""),
        sa.Column("input_classification", sa.Text(), nullable=False, server_default="unknown"),
        sa.Column("status", sa.Text(), nullable=False, server_default="running"),
        sa.Column("normal_calls", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("recovery_allowance", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("normal_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recovery_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_fingerprint", sa.Text(), nullable=False, server_default=""),
        sa.Column("accepted_result_ref", sa.Text(), nullable=True),
        sa.Column("accepted_attempt_id", UUID, nullable=True),
        sa.Column("policy_snapshot", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_model_operations_attribution", "model_operations", ["agent", "operation", "created_at"]
    )

    op.create_table(
        "model_call_attempts",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("operation_id", UUID, nullable=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("profile_name", sa.Text(), nullable=False, server_default=""),
        sa.Column("credential_alias", sa.Text(), nullable=False, server_default=""),
        sa.Column("capacity_source_id", sa.Text(), nullable=False, server_default=""),
        sa.Column("quota_group", sa.Text(), nullable=False, server_default=""),
        sa.Column("agent", sa.Text(), nullable=False, server_default=""),
        sa.Column("stage", sa.Text(), nullable=False, server_default=""),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("job_attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("request_attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fallback_attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempt_kind", sa.Text(), nullable=False, server_default="normal"),
        sa.Column("status", sa.Text(), nullable=False, server_default="reserved"),
        sa.Column("error_class", sa.Text(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("provider_request_id", sa.Text(), nullable=True),
        sa.Column("client_request_id", sa.Text(), nullable=True),
        sa.Column("gateway_attempt_count", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cached_input_tokens", sa.Integer(), nullable=True),
        sa.Column("cache_write_tokens", sa.Integer(), nullable=True),
        sa.Column("reasoning_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("actual_cost_micro_usd", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_micro_usd", sa.Integer(), nullable=True),
        sa.Column("promotional_micro_usd", sa.Integer(), nullable=True),
        sa.Column("rate_limit_seconds", sa.Float(), nullable=True),
        sa.Column("details", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_model_call_attempts_created", "model_call_attempts", ["started_at"])
    op.create_index(
        "ix_model_call_attempts_attribution",
        "model_call_attempts",
        ["provider", "model", "agent", "operation"],
    )
    op.create_index(
        "ix_model_call_attempts_alias", "model_call_attempts", ["credential_alias", "started_at"]
    )

    op.create_table(
        "model_budget_reservations",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("attempt_id", UUID, nullable=False),
        sa.Column("capacity_source_id", sa.Text(), nullable=False),
        sa.Column("quota_group", sa.Text(), nullable=False, server_default=""),
        sa.Column("window_kind", sa.Text(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requests_reserved", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("input_tokens_reserved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.Text(), nullable=False, server_default="reserved"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_model_budget_reservations_window",
        "model_budget_reservations",
        ["capacity_source_id", "window_end"],
    )

    op.create_table(
        "model_capacity_windows",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("capacity_source_id", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("quota_group", sa.Text(), nullable=False, server_default=""),
        sa.Column("window_kind", sa.Text(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_limit", sa.Integer(), nullable=True),
        sa.Column("input_token_limit", sa.Integer(), nullable=True),
        sa.Column("daily_request_limit", sa.Integer(), nullable=True),
        sa.Column("observed_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reserved_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("observed_input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reserved_input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confidence", sa.Text(), nullable=False, server_default="unknown"),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "capacity_source_id",
            "model",
            "window_kind",
            "window_start",
            name="ux_model_capacity_window_key",
        ),
    )

    op.create_table(
        "model_provider_observations",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("capacity_source_id", sa.Text(), nullable=False),
        sa.Column("observation_kind", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("payload", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index(
        "ix_model_provider_observations_source",
        "model_provider_observations",
        ["provider", "capacity_source_id", "observed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_model_provider_observations_source", table_name="model_provider_observations")
    op.drop_table("model_provider_observations")
    op.drop_table("model_capacity_windows")
    op.drop_index("ix_model_budget_reservations_window", table_name="model_budget_reservations")
    op.drop_table("model_budget_reservations")
    op.drop_index("ix_model_call_attempts_alias", table_name="model_call_attempts")
    op.drop_index("ix_model_call_attempts_attribution", table_name="model_call_attempts")
    op.drop_index("ix_model_call_attempts_created", table_name="model_call_attempts")
    op.drop_table("model_call_attempts")
    op.drop_index("ix_model_operations_attribution", table_name="model_operations")
    op.drop_table("model_operations")
