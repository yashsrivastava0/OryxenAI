"""Native database authentication, migration, and PostgreSQL-tool diagnostics."""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from oryxenai.core.settings import get_settings
from oryxenai.db.session import get_engine


def _postgres_tool(name: str) -> Path | None:
    discovered = shutil.which(name)
    if discovered:
        return Path(discovered)
    if os.name != "nt":
        return None
    roots = [
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "PostgreSQL",
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "PostgreSQL",
    ]
    matches: list[Path] = []
    executable = f"{name}.exe"
    for root in roots:
        if root.is_dir():
            matches.extend(root.glob(f"*/bin/{executable}"))
    return sorted(matches, reverse=True)[0] if matches else None


def _report_tools() -> bool:
    ok = True
    for name in ("psql", "pg_isready"):
        path = _postgres_tool(name)
        if path is None:
            print(
                f"PostgreSQL tool {name}: NOT FOUND. Add the installed PostgreSQL "
                "bin directory to PATH or install PostgreSQL client tools."
            )
            ok = False
        else:
            print(f"PostgreSQL tool {name}: {path}")
    return ok


async def _verify_database() -> bool:
    settings = get_settings()
    target = settings.database
    print(
        "Database target: "
        f"{target.user}@{target.host}:{target.port}/{target.database} (password redacted)"
    )
    if not settings.postgres_password.get_secret_value() and not target.url:
        print("Database authentication: FAILED - POSTGRES_PASSWORD is empty in .env.")
        return False
    try:
        engine = get_engine(settings)
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
            rows = await connection.execute(text("SELECT version_num FROM alembic_version"))
            current = {str(row[0]) for row in rows}
    except Exception as exc:
        name = type(getattr(exc, "orig", exc)).__name__
        if name in {"InvalidPasswordError", "InvalidAuthorizationSpecificationError"}:
            guidance = (
                "authentication failed; run the interactive native align-db command "
                "and confirm .env POSTGRES_PASSWORD"
            )
        elif name in {"ConnectionRefusedError", "OSError"}:
            guidance = "connection failed; start local PostgreSQL and confirm host/port"
        elif "UndefinedTable" in name:
            guidance = "alembic_version is missing; run the native migrate command"
        else:
            guidance = f"database check failed safely ({name})"
        print(f"Database authentication: FAILED - {guidance}.")
        return False

    print("Database authentication: OK")
    config = Config("alembic.ini")
    expected = set(ScriptDirectory.from_config(config).get_heads())
    if current != expected:
        print(
            "Migration state: OUT OF DATE - run the native migrate command "
            f"(database heads={sorted(current)}, repository heads={sorted(expected)})."
        )
        return False
    print(f"Migration state: OK ({', '.join(sorted(current))})")
    await engine.dispose()
    return True


async def _main() -> int:
    tools_ok = _report_tools()
    database_ok = await _verify_database()
    return 0 if tools_ok and database_ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
