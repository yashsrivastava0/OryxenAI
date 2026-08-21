"""Unit tests for settings parsing."""

from __future__ import annotations

from oryxenai.core.settings import Settings


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
    for engine in (
        "discovery",
        "content_architect",
        "visual_design_director",
        "build_preparation",
        "code_generator_director",
        "code_generator_planner",
    ):
        routed = s.models.get_profile(s.models.routing.engine_profiles[engine])
        assert routed is not None
        assert routed.provider == "anthropic"
        assert routed.api_key_env == "ANTHROPIC_API_KEY"


def test_secrets_not_in_repr():
    """SecretStr values are masked in repr."""
    s = Settings()
    repr_str = repr(s)
    assert "SecretStr" in repr_str
