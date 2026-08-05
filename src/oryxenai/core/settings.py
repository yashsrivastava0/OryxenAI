"""Application settings.

Non-secret configuration is loaded from committed TOML files:
  * config/app.toml   -> base application configuration
  * OryxenAI_CONFIG_OVERLAY env var (optional) -> overlay path
  * config/models.toml -> provider-neutral model profiles

Secrets are read from the environment (root .env via pydantic-settings):
  * POSTGRES_PASSWORD  -> database password

Overlay policy:
  Docker sets OryxenAI_CONFIG_OVERLAY=config/app.docker.toml
  Tests set OryxenAI_CONFIG_OVERLAY=config/app.test.toml
  Neither is required — the base config has safe local defaults.

The application starts without any model credential. Credentials are resolved
lazily only when a real model operation is requested.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    pass

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_CONFIG_DIR = _REPO_ROOT / "config"

_OVERLAY_ENV = "OryxenAI_CONFIG_OVERLAY"


def _config_dir() -> Path:
    return _DEFAULT_CONFIG_DIR


def _load_toml(filename: str) -> dict[str, Any]:
    candidate = Path(filename)
    if candidate.is_absolute():
        path = candidate
    elif candidate.parts and candidate.parts[0] == _config_dir().name:
        path = _REPO_ROOT / candidate
    else:
        path = _config_dir() / candidate
    if not path.is_file():
        return {}
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Merge overlay into base, recursing for nested dicts."""
    merged = dict(base)
    for key, val in overlay.items():
        if isinstance(val, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], val)
        else:
            merged[key] = val
    return merged


# ---------------------------------------------------------------------------
# Sub-config models
# ---------------------------------------------------------------------------


class AppConfig(BaseModel):
    """Non-secret application settings from [app] in config/app.toml."""

    name: str = "OryxenAI"
    env: str = "local"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    enable_dev_ui: bool = True

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.upper()
        return v

    @field_validator("port", mode="before")
    @classmethod
    def _coerce_port(cls, v: Any) -> Any:
        if isinstance(v, str) and v.strip().isdigit():
            return int(v)
        return v

    @field_validator("enable_dev_ui", mode="before")
    @classmethod
    def _coerce_bool(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip().lower() in {"1", "true", "yes", "on"}
        return v


class DatabaseConfig(BaseModel):
    """Non-secret database connection parameters from [database] in config/app.toml."""

    host: str = "localhost"
    port: int = 5432
    database: str = "oryxenai"
    user: str = "oryxen"
    url: str = ""

    @field_validator("port", mode="before")
    @classmethod
    def _coerce_port(cls, v: Any) -> Any:
        if isinstance(v, str) and v.strip().isdigit():
            return int(v)
        return v


class PoolConfig(BaseModel):
    """Engine connection-pool settings from [database.pool]."""

    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600


class WorkerConfig(BaseModel):
    """Worker process settings from [worker]."""

    polling_interval: float = 2.0
    heartbeat_interval: float = 30.0
    claim_batch_size: int = 5
    concurrency: int = 2
    shutdown_grace: float = 10.0


class WorkerJobConfig(BaseModel):
    """Per-job execution settings from [worker.job]."""

    handler_timeout: float = 300.0
    lease_duration: float = 120.0


class WorkerRetryConfig(BaseModel):
    """Retry scheduling settings from [worker.retry]."""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter: bool = True


class ApiConfig(BaseModel):
    """API-level settings from [api]."""

    max_input_bytes: int = 262144


class DiagnosticsConfig(BaseModel):
    """Diagnostics/heartbeat settings from [diagnostics]."""

    heartbeat_staleness: float = 60.0


class DiscoveryConfig(BaseModel):
    """Discovery agent input limits from [discovery] in config/app.toml."""

    max_main_prompt_chars: int = 10000
    max_resume_chars: int = 160000
    max_links: int = 20
    max_answer_chars: int = 10000
    max_questions: int = 8
    max_featured_projects: int = 5


class ModelProfile(BaseModel):
    """A single provider-neutral model profile from config/models.toml."""

    provider: str = "openai_compatible"
    model: str = ""
    base_url: str = ""
    api_key_env: str = ""
    request_params: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: float = 120.0
    max_retries: int = 0
    max_output_tokens: int = 4096
    reasoning_effort: str = ""
    store: bool = False


class ModelConfig(BaseModel):
    """All model profiles loaded from config/models.toml."""

    profiles: dict[str, ModelProfile] = Field(default_factory=dict)

    def get_profile(self, name: str = "default") -> ModelProfile | None:
        return self.profiles.get(name)


# ---------------------------------------------------------------------------
# Central Settings
# ---------------------------------------------------------------------------


class Settings(BaseSettings):
    """Central settings object.

    Composes non-secret TOML configuration (base + optional overlay) with the
    database password secret read from the environment.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Secret from .env — optional in code so unit tests can run without it.
    postgres_password: SecretStr = SecretStr("")

    # Non-secret infrastructure overrides (env vars, not in .env):
    # Docker Compose sets these to redirect to the postgres service.
    db_host_override: str = ""
    db_port_override: int = 0

    # Loaded from committed TOML (not from env).
    app: AppConfig = Field(default_factory=AppConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    pool: PoolConfig = Field(default_factory=PoolConfig)
    worker: WorkerConfig = Field(default_factory=WorkerConfig)
    worker_job: WorkerJobConfig = Field(default_factory=WorkerJobConfig)
    worker_retry: WorkerRetryConfig = Field(default_factory=WorkerRetryConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    diagnostics: DiagnosticsConfig = Field(default_factory=DiagnosticsConfig)
    models: ModelConfig = Field(default_factory=ModelConfig)
    discovery: DiscoveryConfig = Field(default_factory=DiscoveryConfig)

    @model_validator(mode="after")
    def _load_toml_files(self) -> Settings:
        app_data = _load_toml("app.toml")

        # Apply overlay if configured.
        overlay_path = os.environ.get(_OVERLAY_ENV, "").strip()
        if overlay_path:
            overlay_data = _load_toml(overlay_path)
            if overlay_data:
                app_data = _deep_merge(app_data, overlay_data)

        if "app" in app_data:
            self.app = AppConfig(**app_data["app"])
        if "database" in app_data:
            raw_db = dict(app_data["database"])
            pool_raw = raw_db.pop("pool", None)
            self.database = DatabaseConfig(**raw_db)
            if pool_raw:
                self.pool = PoolConfig(**pool_raw)
        if "worker" in app_data:
            worker_raw = dict(app_data["worker"])
            job_raw = worker_raw.pop("job", None)
            retry_raw = worker_raw.pop("retry", None)
            self.worker = WorkerConfig(**worker_raw)
            if job_raw:
                self.worker_job = WorkerJobConfig(**job_raw)
            if retry_raw:
                self.worker_retry = WorkerRetryConfig(**retry_raw)
        if "api" in app_data:
            self.api = ApiConfig(**app_data["api"])
        if "diagnostics" in app_data:
            self.diagnostics = DiagnosticsConfig(**app_data["diagnostics"])
        if "discovery" in app_data:
            self.discovery = DiscoveryConfig(**app_data["discovery"])

        # Model profiles.
        models_data = _load_toml("models.toml")
        profiles: dict[str, ModelProfile] = {}
        if "profiles" in models_data and isinstance(models_data["profiles"], dict):
            for name, raw in models_data["profiles"].items():
                if isinstance(raw, dict):
                    profiles[name] = ModelProfile(**raw)
        self.models = ModelConfig(profiles=profiles)
        return self

    @property
    def database_url(self) -> str:
        """Compose the async SQLAlchemy database URL."""
        from urllib.parse import quote_plus

        override = self.database.url.strip()
        if override:
            return override
        password = quote_plus(self.postgres_password.get_secret_value())
        host = self.db_host_override or self.database.host
        port = self.db_port_override or self.database.port
        return (
            f"postgresql+asyncpg://{self.database.user}:{password}"
            f"@{host}:{port}/{self.database.database}"
        )

    @property
    def is_dev_ui_enabled(self) -> bool:
        return self.app.enable_dev_ui


# ---------------------------------------------------------------------------
# Singleton access
# ---------------------------------------------------------------------------

_settings: Settings | None = None


def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Clear the cached settings singleton (used by tests)."""
    global _settings
    _settings = None
