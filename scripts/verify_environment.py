"""Environment verification script — checks that required configuration exists.

Run: python scripts/verify_environment.py
Does NOT print secret values. Reports missing configuration clearly.
"""

from __future__ import annotations

import sys

from oryxenai.core.settings import get_settings


def main() -> int:
    settings = get_settings()

    print("=== OryxenAI Environment Verification ===\n")
    print(f"App name         : {settings.app.name}")
    print(f"App env          : {settings.app.env}")
    print(f"App host         : {settings.app.host}")
    print(f"App port         : {settings.app.port}")
    print(f"Log level        : {settings.app.log_level}")
    print(f"Dev UI enabled   : {settings.is_dev_ui_enabled}")
    print()
    print(f"DB host (TOML)   : {settings.database.host}")
    print(f"DB host override : {settings.db_host_override or '(none)'}")
    print(f"DB port          : {settings.database.port}")
    print(f"DB database      : {settings.database.database}")
    print(f"DB user          : {settings.database.user}")
    print(f"DB password set  : {'yes' if settings.postgres_password.get_secret_value() else 'NO'}")
    print(f"DB URL (masked)  : {mask_url(settings.database_url)}")

    print()
    if not settings.postgres_password.get_secret_value():
        print("WARNING: POSTGRES_PASSWORD is not set in .env.")
        print("         The application will not be able to connect to PostgreSQL.")
        return 1

    print("OK: All required configuration is present.")
    return 0


def mask_url(url: str) -> str:
    """Mask the password in a database URL for safe display."""
    import re

    return re.sub(r":(.*?)@", ":***@", url)


if __name__ == "__main__":
    sys.exit(main())
