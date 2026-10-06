"""Unit tests for settings parsing."""

from __future__ import annotations

import pytest

from oryxenai.core.settings import AuthConfig, GenerationEstimatesConfig, Settings


def test_generation_estimates_are_positive_ordered_ranges():
    assert Settings().generation_estimates.content == (30, 90)
    with pytest.raises(ValueError, match="positive, ordered"):
        GenerationEstimatesConfig(brief=(60, 25))
    with pytest.raises(ValueError, match="positive, ordered"):
        GenerationEstimatesConfig(brief=(0, 60))


def test_settings_load_toml_defaults():
    """Settings loads from committed config/app.toml with safe defaults."""
    s = Settings()
    assert s.app.name == "OryxenAI"
    assert s.app.env == "local"
    assert s.app.host == "127.0.0.1"
    assert s.app.port == 8000
    assert s.app.log_level == "INFO"
    assert s.app.enable_dev_ui is True
    assert s.database.host == "localhost"
    assert s.database.port == 5544
    assert s.database.database == "oryxenai"
    assert s.database.user == "oryxen"


def test_database_url_composition():
    """DATABASE_URL is composed from config + password secret."""
    s = Settings()
    url = s.database_url
    assert url.startswith("postgresql+asyncpg://")
    assert "oryxenai" in url
    assert "@" in url


def test_database_url_override():
    """When database.url is set, it is used verbatim."""
    s = Settings()
    s.database.url = "postgresql+asyncpg://custom@host:5433/customdb"
    assert s.database_url == "postgresql+asyncpg://custom@host:5433/customdb"


def test_database_url_environment_override_uses_asyncpg_and_keeps_ssl_options(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://managed:secret@db.example:5432/app?sslmode=require",
    )

    settings = Settings()

    from sqlalchemy.dialects.postgresql.asyncpg import PGDialect_asyncpg
    from sqlalchemy.engine import make_url

    url = make_url(settings.database_url)
    _, connect_args = PGDialect_asyncpg().create_connect_args(url)
    assert connect_args["ssl"] == "require"
    assert "sslmode" not in connect_args
    assert "managed:secret@" not in repr(settings)


def test_database_url_environment_override_rejects_non_postgresql(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "mysql://user:secret@db.example/app")

    with pytest.raises(ValueError, match="PostgreSQL"):
        _ = Settings().database_url


def test_database_url_environment_override_accepts_encoded_at_in_password(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://managed:pass%40word@db.example:5432/app?sslmode=require",
    )

    from sqlalchemy.engine import make_url

    url = make_url(Settings().database_url)
    assert url.host == "db.example"
    expected_credential = "pass@word"
    assert url.password == expected_credential
    assert url.query["ssl"] == "require"


def test_database_url_environment_override_rejects_unescaped_at_without_secret(monkeypatch):
    credential = "private@password"
    monkeypatch.setenv(
        "DATABASE_URL",
        f"postgresql://managed:{credential}@db.example:5432/app?sslmode=require",
    )

    with pytest.raises(ValueError, match="unescaped @") as error:
        _ = Settings().database_url
    assert credential not in str(error.value)


def test_managed_host_origin_overrides_configured_auth_origins(monkeypatch):
    monkeypatch.setenv("ORYXENAI_AUTH_PRIMARY_ORIGIN", "https://portfolio.example")
    monkeypatch.setenv("ORYXENAI_AUTH_ALLOWED_ORIGINS", "https://portfolio.example")

    settings = Settings()

    assert settings.auth.primary_origin == "https://portfolio.example"
    assert settings.auth.allowed_origins == ["https://portfolio.example"]


def test_model_config_extra_ignore():
    """Leftover env variables are ignored, not errors."""
    import os

    os.environ["SOME_UNUSED_VAR"] = "value"
    s = Settings()
    assert s.app.name == "OryxenAI"
    del os.environ["SOME_UNUSED_VAR"]


def test_model_profiles_loaded():
    """Model profiles and logical routes load from committed TOML."""
    s = Settings()
    profile = s.models.get_profile("default")
    assert profile is not None
    assert profile.provider == "anthropic"
    assert profile.model == "claude-sonnet-5"
    assert profile.api_key_env == "ANTHROPIC_API_KEY"
    assert profile.prompt_cache_ttl == "5m"
    assert s.models.routing.fallback_profile == "experiential_luna"
    pipeline_profile_id = "experiential_luna_6"
    assert s.models.routing.engine_profiles["discovery"] == pipeline_profile_id
    pipeline_profile = s.models.get_profile(pipeline_profile_id)
    assert pipeline_profile is not None
    for engine in ("discovery", "content_architect"):
        routed = s.models.get_profile(s.models.routing.engine_profiles[engine])
        assert routed is not None
        assert routed.provider == pipeline_profile.provider
        assert routed.model == pipeline_profile.model
        assert routed.api_key_env == pipeline_profile.api_key_env


def test_preview_gateway_settings_have_stable_local_defaults():
    settings = Settings()
    assert settings.preview_gateway.host == "127.0.0.1"
    assert settings.preview_gateway.port == 4174
    assert settings.preview_gateway.route_prefix == "/preview"


def test_secrets_not_in_repr():
    """SecretStr values are masked in repr."""
    s = Settings()
    repr_str = repr(s)
    assert "SecretStr" in repr_str


def test_detached_pipeline_is_rejected_for_production():
    config = AuthConfig(pipeline_mode="detached")
    config.validate_environment(
        app_env="local",
        supabase_url="",
        publishable_key="",
        secret_key="",
        admin_emails="",
        allowed_emails="",
    )
    with pytest.raises(ValueError, match="Detached pipeline mode"):
        config.validate_environment(
            app_env="production",
            supabase_url="",
            publishable_key="",
            secret_key="",
            admin_emails="",
            allowed_emails="",
        )


def test_detached_development_harness_is_rejected_outside_local_development():
    config = AuthConfig(development_harness_mode="detached")
    config.validate_environment(
        app_env="local",
        supabase_url="",
        publishable_key="",
        secret_key="",
        admin_emails="",
        allowed_emails="",
    )
    with pytest.raises(ValueError, match="Detached development harnesses"):
        config.validate_environment(
            app_env="production",
            supabase_url="",
            publishable_key="",
            secret_key="",
            admin_emails="",
            allowed_emails="",
        )
