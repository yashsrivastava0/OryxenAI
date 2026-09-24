"""Remove obsolete stage bindings while preserving their stored references."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0025_retire_generation_pipeline"
down_revision: str | None = "0024_codegen_stage_durations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "portfolio_entitlements",
        sa.Column(
            "archived_pipeline_binding",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.execute(
        sa.text(
            "UPDATE portfolio_entitlements SET archived_pipeline_binding = "
            "jsonb_strip_nulls(jsonb_build_object("
            "'generation_run_id', generation_run_id::text, "
            "'successful_run_id', successful_run_id::text, "
            "'consumed_at', consumed_at)) "
            "WHERE generation_run_id IS NOT NULL OR successful_run_id IS NOT NULL "
            "OR consumed_at IS NOT NULL"
        )
    )

    for name in (
        "ck_portfolio_entitlements_consumed_consistency",
        "ck_portfolio_entitlements_success_matches_generation",
        "ck_portfolio_entitlements_success_requires_generation",
        "ck_portfolio_entitlements_generation_requires_session",
        "ck_portfolio_entitlements_deleted_project_consistency",
    ):
        op.drop_constraint(name, "portfolio_entitlements", type_="check")
    for name in (
        "fk_portfolio_entitlements_success",
        "fk_portfolio_entitlements_generation",
    ):
        op.drop_constraint(name, "portfolio_entitlements", type_="foreignkey")
    for name in (
        "uq_portfolio_entitlements_success",
        "uq_portfolio_entitlements_generation",
    ):
        op.drop_constraint(name, "portfolio_entitlements", type_="unique")

    for column in ("generation_run_id", "successful_run_id", "consumed_at"):
        op.drop_column("portfolio_entitlements", column)

    op.create_check_constraint(
        "ck_portfolio_entitlements_deleted_project_consistency",
        "portfolio_entitlements",
        "deleted_portfolio_session_id IS NULL OR "
        "(project_deleted_at IS NOT NULL AND portfolio_session_id IS NULL)",
    )

    for table, name in (
        ("admin_audit_events", "ck_admin_audit_action"),
        ("admin_operations", "ck_admin_operations_action"),
    ):
        op.drop_constraint(name, table, type_="check")
        op.create_check_constraint(
            name,
            table,
            "action ~ '^[a-z][a-z0-9_]{0,63}$'",
        )


def downgrade() -> None:
    for table, name in (
        ("admin_operations", "ck_admin_operations_action"),
        ("admin_audit_events", "ck_admin_audit_action"),
    ):
        op.drop_constraint(name, table, type_="check")
        op.create_check_constraint(
            name,
            table,
            "action ~ '^[a-z][a-z0-9_]{0,63}$'",
        )

    op.drop_constraint(
        "ck_portfolio_entitlements_deleted_project_consistency",
        "portfolio_entitlements",
        type_="check",
    )
    op.add_column(
        "portfolio_entitlements",
        sa.Column("generation_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "portfolio_entitlements",
        sa.Column("successful_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "portfolio_entitlements",
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE portfolio_entitlements SET "
            "generation_run_id = NULLIF(archived_pipeline_binding->>'generation_run_id', '')::uuid, "
            "successful_run_id = NULLIF(archived_pipeline_binding->>'successful_run_id', '')::uuid, "
            "consumed_at = NULLIF(archived_pipeline_binding->>'consumed_at', '')::timestamptz"
        )
    )
    op.drop_column("portfolio_entitlements", "archived_pipeline_binding")

    op.create_unique_constraint(
        "uq_portfolio_entitlements_generation",
        "portfolio_entitlements",
        ["generation_run_id"],
    )
    op.create_unique_constraint(
        "uq_portfolio_entitlements_success",
        "portfolio_entitlements",
        ["successful_run_id"],
    )
    op.create_foreign_key(
        "fk_portfolio_entitlements_generation",
        "portfolio_entitlements",
        "code_generator_runs",
        ["generation_run_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_portfolio_entitlements_success",
        "portfolio_entitlements",
        "code_generator_runs",
        ["successful_run_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_portfolio_entitlements_generation_requires_session",
        "portfolio_entitlements",
        "generation_run_id IS NULL OR portfolio_session_id IS NOT NULL",
    )
    op.create_check_constraint(
        "ck_portfolio_entitlements_success_requires_generation",
        "portfolio_entitlements",
        "successful_run_id IS NULL OR generation_run_id IS NOT NULL",
    )
    op.create_check_constraint(
        "ck_portfolio_entitlements_success_matches_generation",
        "portfolio_entitlements",
        "successful_run_id IS NULL OR successful_run_id = generation_run_id",
    )
    op.create_check_constraint(
        "ck_portfolio_entitlements_consumed_consistency",
        "portfolio_entitlements",
        "(consumed_at IS NULL AND successful_run_id IS NULL) OR "
        "(consumed_at IS NOT NULL AND successful_run_id IS NOT NULL) OR "
        "(consumed_at IS NOT NULL AND deleted_portfolio_session_id IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_portfolio_entitlements_deleted_project_consistency",
        "portfolio_entitlements",
        "deleted_portfolio_session_id IS NULL OR "
        "(project_deleted_at IS NOT NULL AND portfolio_session_id IS NULL "
        "AND generation_run_id IS NULL AND successful_run_id IS NULL)",
    )
