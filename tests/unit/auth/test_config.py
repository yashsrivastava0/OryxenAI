from __future__ import annotations

import pytest

from oryxenai.core.settings import AuthConfig


def _valid_config(**overrides: object) -> AuthConfig:
    values: dict[str, object] = {
        "primary_origin": "https://app.example.test",
        "allowed_origins": ["https://app.example.test"],
    }
    values.update(overrides)
    return AuthConfig(**values)


def test_auth_environment_normalizes_admission_lists() -> None:
    config = _valid_config()
    admins, users = config.validate_environment(
        app_env="production",
        supabase_url="https://project.supabase.co",
        publishable_key="sb_publishable_test",
        secret_key="sb_secret_test",  # noqa: S106 - sentinel only
        admin_emails=" ADMIN1@example.com ; admin2@example.com ",
        allowed_emails="user@example.com",
    )
    assert admins == ("admin1@example.com", "admin2@example.com")
    assert users == ("user@example.com",)
    assert config.issuer_for("https://project.supabase.co") == (
        "https://project.supabase.co/auth/v1"
    )


def test_open_admission_allows_empty_normal_list_in_production() -> None:
    config = _valid_config(admission_mode="open")
    admins, users = config.validate_environment(
        app_env="production",
        supabase_url="https://project.supabase.co",
        publishable_key="sb_publishable_test",
        secret_key="sb_secret_test",  # noqa: S106 - sentinel only
        admin_emails="admin1@example.com admin2@example.com",
        allowed_emails="",
    )
    assert admins == ("admin1@example.com", "admin2@example.com")
    assert users == ()


@pytest.mark.parametrize(
    ("admin_emails", "allowed_emails", "message"),
    [
        ("admin@example.com admin@example.com", "user@example.com", "duplicates"),
        ("admin@example.com other@example.com", "admin@example.com", "overlap"),
        (
            "admin@example.com other@example.com",
            " ".join(f"user{index}@example.com" for index in range(16)),
            "capacity",
        ),
        ("only-one@example.com", "user@example.com", "bootstrap"),
        ("admin@example.com other@example.com", "not-an-email", "email"),
    ],
)
def test_invalid_admission_configuration_is_rejected(
    admin_emails: str, allowed_emails: str, message: str
) -> None:
    config = _valid_config()
    with pytest.raises(ValueError, match=message):
        config.validate_environment(
            app_env="production",
            supabase_url="https://project.supabase.co",
            publishable_key="sb_publishable_test",
            secret_key="sb_secret_test",  # noqa: S106 - sentinel only
            admin_emails=admin_emails,
            allowed_emails=allowed_emails,
        )


def test_production_rejects_local_http_and_missing_provider_coordinates() -> None:
    config = AuthConfig()
    with pytest.raises(ValueError, match="Required Supabase"):
        config.validate_environment(
            app_env="production",
            supabase_url="http://localhost:54321",
            publishable_key="",
            secret_key="",
            admin_emails="admin1@example.com admin2@example.com",
            allowed_emails="user@example.com",
        )

    config = _valid_config(
        primary_origin="http://localhost:8000", allowed_origins=["http://localhost:8000"]
    )
    with pytest.raises(ValueError, match="HTTPS application"):
        config.validate_environment(
            app_env="production",
            supabase_url="https://project.supabase.co",
            publishable_key="sb_publishable_test",
            secret_key="sb_secret_test",  # noqa: S106 - sentinel only
            admin_emails="admin1@example.com admin2@example.com",
            allowed_emails="user@example.com",
        )


def test_auth_policy_rejects_wildcards_and_symmetric_algorithms() -> None:
    with pytest.raises(ValueError, match="asymmetric"):
        AuthConfig(allowed_algorithms=["RS256", "HS256"])
    with pytest.raises(ValueError, match="origins"):
        AuthConfig(allowed_origins=["*"])
    with pytest.raises(ValueError, match="audience"):
        AuthConfig(audience="public")
    with pytest.raises(ValueError, match="issuer path"):
        AuthConfig(issuer_path="/custom-auth")
    with pytest.raises(ValueError, match="admission mode"):
        AuthConfig(admission_mode="everyone")
    with pytest.raises(ValueError, match="development harness mode"):
        AuthConfig(development_harness_mode="public")


def test_configured_local_auth_rejects_incomplete_provider_coordinates() -> None:
    config = _valid_config()
    with pytest.raises(ValueError, match="incomplete"):
        config.validate_environment(
            app_env="local",
            supabase_url="https://project.supabase.co",
            publishable_key="",
            secret_key="sb_secret_test",  # noqa: S106 - sentinel only
            admin_emails="admin1@example.com admin2@example.com",
            allowed_emails="user@example.com",
        )
