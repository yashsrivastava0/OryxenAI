"""Interactively align the local application role/database with `.env`."""

from __future__ import annotations

import asyncio
import getpass

import asyncpg

from oryxenai.core.settings import get_settings


async def _quoted_command(connection: asyncpg.Connection, template: str, *values: str) -> str:
    placeholders = ", ".join(f"${index}" for index in range(1, len(values) + 1))
    command = await connection.fetchval(f"SELECT format('{template}', {placeholders})", *values)
    if not isinstance(command, str):
        raise RuntimeError("PostgreSQL did not produce the requested safe command.")
    return command


async def _main() -> int:
    settings = get_settings()
    database = settings.database
    application_password = settings.postgres_password.get_secret_value()
    if database.url:
        print("Refusing role alignment while database.url overrides the native coordinates.")
        return 1
    if not application_password:
        print("POSTGRES_PASSWORD is empty in .env; nothing can be aligned.")
        return 1

    administrator = input("PostgreSQL administrator role [postgres]: ").strip() or "postgres"
    administrator_password = getpass.getpass("PostgreSQL administrator password: ")
    try:
        connection = await asyncpg.connect(
            host=database.host,
            port=database.port,
            user=administrator,
            password=administrator_password,
            database="postgres",
            timeout=15,
        )
    except Exception as exc:
        print(f"Administrator connection failed safely ({type(exc).__name__}).")
        return 1
    finally:
        administrator_password = ""

    try:
        role_exists = await connection.fetchval(
            "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = $1)", database.user
        )
        if not role_exists:
            command = await _quoted_command(
                connection, "CREATE ROLE %I LOGIN PASSWORD %L", database.user, application_password
            )
            await connection.execute(command)
        else:
            command = await _quoted_command(
                connection, "ALTER ROLE %I LOGIN PASSWORD %L", database.user, application_password
            )
            await connection.execute(command)

        database_exists = await connection.fetchval(
            "SELECT EXISTS (SELECT 1 FROM pg_database WHERE datname = $1)",
            database.database,
        )
        if not database_exists:
            command = await _quoted_command(
                connection,
                "CREATE DATABASE %I OWNER %I",
                database.database,
                database.user,
            )
            await connection.execute(command)
    finally:
        application_password = ""
        await connection.close()

    print(
        "Native application role and database are aligned with .env. "
        "No password was printed or placed in a command argument."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
