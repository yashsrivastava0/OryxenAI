"""Unit tests for settings parsing."""

from __future__ import annotations

import pytest

from oryxenai.core.settings import AuthConfig, Settings


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
    assert s.models.routing.fallback_profile == "default"
    assert s.models.routing.engine_profiles["discovery"] == "discovery"
    discovery_profile = s.models.get_profile("discovery")
    assert discovery_profile is not None
    for engine in ("discovery", "content_architect", "visual_design_director"):
        routed = s.models.get_profile(s.models.routing.engine_profiles[engine])
        assert routed is not None
        assert routed.provider == discovery_profile.provider
        assert routed.model == discovery_profile.model
        assert routed.api_key_env == discovery_profile.api_key_env

    code_generator_profile = s.models.get_profile("code_generator_director")
    assert code_generator_profile is not None
    for engine in ("code_generator_director", "code_generator_planner"):
        routed = s.models.get_profile(s.models.routing.engine_profiles[engine])
        assert routed is not None
        assert routed.provider == code_generator_profile.provider
        assert routed.model == code_generator_profile.model
        assert routed.api_key_env == code_generator_profile.api_key_env


def test_preview_readback_and_health_url_overlay_contract(monkeypatch):
    """Hosted Docker is strict; local and isolated Docker-dev remain lenient."""

    expectations = (
        ("config/app.toml", False, "http://127.0.0.1:4174/preview"),
        ("config/app.native.toml", False, "http://127.0.0.1:4174/preview"),
        ("config/app.test.toml", False, "http://127.0.0.1:4174/preview"),
        ("config/app.docker.codegen-run.toml", False, "http://127.0.0.1:4174/preview"),
        ("config/app.docker.toml", True, "http://localhost:4174/preview"),
    )

    for overlay, strict, preview_base_url in expectations:
        if overlay == "config/app.toml":
            monkeypatch.delenv("OryxenAI_CONFIG_OVERLAY", raising=False)
        else:
            monkeypatch.setenv("OryxenAI_CONFIG_OVERLAY", overlay)
        settings = Settings()
        verification = settings.code_generator_verification
        assert verification.preview_public_readback_required is strict
        assert verification.preview_base_url == preview_base_url

    monkeypatch.delenv("OryxenAI_CONFIG_OVERLAY", raising=False)


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
