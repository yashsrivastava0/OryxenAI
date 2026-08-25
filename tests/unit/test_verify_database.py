from alembic.config import Config
from alembic.script import ScriptDirectory
from scripts.verify_database import _migration_diagnostic


def test_migration_diagnostic_rejects_stamped_database_without_core_tables() -> None:
    ok, message = _migration_diagnostic(
        current={"0019"},
        expected={"0019"},
        tables={"alembic_version"},
    )

    assert ok is False
    assert "INCONSISTENT" in message
    assert "agent_runs" in message


def test_migration_diagnostic_reports_outdated_complete_schema() -> None:
    ok, message = _migration_diagnostic(
        current={"0018"},
        expected={"0019"},
        tables={"agent_runs", "background_jobs", "portfolio_sessions"},
    )

    assert ok is False
    assert "OUT OF DATE" in message


def test_migration_diagnostic_accepts_current_complete_schema() -> None:
    ok, message = _migration_diagnostic(
        current={"0019"},
        expected={"0019"},
        tables={"agent_runs", "background_jobs", "portfolio_sessions"},
    )

    assert ok is True
    assert message == "Migration state: OK (0019)"


def test_all_revision_ids_fit_alembic_version_column() -> None:
    revisions = ScriptDirectory.from_config(Config("alembic.ini")).walk_revisions()

    assert all(len(revision.revision) <= 32 for revision in revisions)
