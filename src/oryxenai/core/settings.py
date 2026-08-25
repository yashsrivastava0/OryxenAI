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
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from oryxenai.agents.shared.providers.capabilities import ModelCapabilities
from oryxenai.auth.domain import AuthInputError, normalize_email_list

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
    # Optional per-job-kind overrides from [worker.job.kind_timeouts] for
    # handlers whose work legitimately outlasts the default (e.g. Code
    # Generator stages driving multiple long model calls per job).
    kind_timeouts: dict[str, float] = Field(default_factory=dict)

    def timeout_for(self, kind: str) -> float:
        override = self.kind_timeouts.get(kind)
        return float(override) if override is not None else self.handler_timeout


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


class AuthConfig(BaseModel):
    """Committed, non-secret policy for the Phase 1 auth boundary."""

    provider: str = "supabase"
    enabled: bool = True
    required: bool = False
    # The main pipeline may be run anonymously only in local/test development.
    # This is deliberately separate from ``enabled`` because detached mode
    # only relaxes the explicitly anonymous local pipeline/fixture boundary;
    # attached and deployment-like surfaces remain protected.
    pipeline_mode: str = "attached"
    # ``allowlist`` keeps local/restricted environments closed.  ``open``
    # admits any verified Google identity until the database-owned normal-user
    # capacity is full.  The provider still remains Google-only; this setting
    # controls OryxenAI admission after Supabase has verified the identity.
    admission_mode: str = "allowlist"
    primary_origin: str = "http://localhost:8000"
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:8000", "http://127.0.0.1:8000"]
    )
    audience: str = "authenticated"
    issuer_path: str = "/auth/v1"
    allowed_algorithms: list[str] = Field(default_factory=lambda: ["RS256", "ES256"])
    sign_in_path: str = "/sign-in"
    callback_path: str = "/auth/callback"
    access_not_approved_path: str = "/access-not-approved"
    account_unavailable_path: str = "/account-unavailable"
    onboarding_path: str = "/onboarding"
    app_path: str = "/app"
    admin_path: str = "/admin"
    normal_user_limit: int = 15
    bootstrap_admin_count: int = 2
    clock_skew_seconds: int = 30
    jwks_cache_ttl_seconds: int = 300
    http_timeout_seconds: float = 5.0
    max_token_bytes: int = 8192

    @field_validator("enabled", "required", mode="before")
    @classmethod
    def _coerce_bool(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return value

    @field_validator("admission_mode", mode="before")
    @classmethod
    def _coerce_admission_mode(cls, value: Any) -> Any:
        return str(value).strip().lower() if value is not None else value

    @field_validator("pipeline_mode", mode="before")
    @classmethod
    def _coerce_pipeline_mode(cls, value: Any) -> Any:
        return str(value).strip().lower() if value is not None else value

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _coerce_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

    @field_validator("allowed_algorithms", mode="before")
    @classmethod
    def _coerce_algorithms(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [part.strip().upper() for part in value.split(",") if part.strip()]
        return [str(item).upper() for item in value]

    @model_validator(mode="after")
    def _validate_policy(self) -> AuthConfig:
        if self.provider != "supabase":
            raise ValueError("Only the configured Supabase auth provider is supported.")
        if self.required and not self.enabled:
            raise ValueError("Required authentication cannot be disabled.")
        if self.admission_mode not in {"allowlist", "open"}:
            raise ValueError("Auth admission mode must be 'allowlist' or 'open'.")
        if self.pipeline_mode not in {"attached", "detached"}:
            raise ValueError("Auth pipeline mode must be 'attached' or 'detached'.")
        if self.audience != "authenticated":
            raise ValueError("Supabase JWT audience must be authenticated.")
        if self.issuer_path != "/auth/v1":
            raise ValueError("Supabase JWT issuer path must be /auth/v1.")
        if self.normal_user_limit != 15:
            raise ValueError("Phase 1 normal-user capacity must be exactly 15.")
        if self.bootstrap_admin_count != 2:
            raise ValueError("Phase 1 requires exactly two bootstrap administrators.")
        if not self.allowed_algorithms or any(
            algorithm not in {"RS256", "ES256"} for algorithm in self.allowed_algorithms
        ):
            raise ValueError("Only explicitly allowed asymmetric JWT algorithms may be used.")
        if len(set(self.allowed_algorithms)) != len(self.allowed_algorithms):
            raise ValueError("JWT algorithms must not be duplicated.")
        if not 0 <= self.clock_skew_seconds <= 300:
            raise ValueError("JWT clock skew must be between 0 and 300 seconds.")
        if not 1 <= self.jwks_cache_ttl_seconds <= 600:
            raise ValueError("JWKS cache TTL must be between 1 and 600 seconds.")
        if not 0.1 <= self.http_timeout_seconds <= 30:
            raise ValueError("Auth HTTP timeout must be between 0.1 and 30 seconds.")
        if not 1024 <= self.max_token_bytes <= 65536:
            raise ValueError("Bearer token size limit is outside the safe range.")

        normalized_origins: list[str] = []
        for origin in [self.primary_origin, *self.allowed_origins]:
            parsed = urlsplit(origin.strip())
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
                or "*" in origin
            ):
                raise ValueError("Auth origins must be exact HTTP(S) origins without wildcards.")
            normalized = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
            normalized_origins.append(normalized)
        if len(set(normalized_origins[1:])) != len(normalized_origins[1:]):
            raise ValueError("Auth allowed origins must be unique.")
        if normalized_origins[0] not in normalized_origins[1:]:
            raise ValueError("The primary auth origin must be explicitly allowlisted.")
        self.primary_origin = normalized_origins[0]
        self.allowed_origins = normalized_origins[1:]

        for path in (
            self.issuer_path,
            self.sign_in_path,
            self.callback_path,
            self.access_not_approved_path,
            self.account_unavailable_path,
            self.onboarding_path,
            self.app_path,
            self.admin_path,
        ):
            if (
                not path.startswith("/")
                or "\\" in path
                or "//" in path
                or "?" in path
                or "#" in path
                or "%" in path
                or "*" in path
            ):
                raise ValueError("Auth page paths must be reviewed relative paths.")
        return self

    def issuer_for(self, supabase_url: str) -> str:
        """Derive the issuer from the configured Supabase project URL."""
        parsed = urlsplit(supabase_url.strip().rstrip("/"))
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("SUPABASE_URL must be a bare HTTP(S) project URL.")
        try:
            _port = parsed.port
        except ValueError as exc:
            raise ValueError("SUPABASE_URL contains an invalid port.") from exc
        origin = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
        return f"{origin}{self.issuer_path}"

    def callback_url(self) -> str:
        return f"{self.primary_origin}{self.callback_path}"

    def validate_environment(
        self,
        *,
        app_env: str,
        supabase_url: str,
        publishable_key: str,
        secret_key: str,
        admin_emails: str,
        allowed_emails: str,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Validate environment-bound auth coordinates without returning secrets."""
        admins = _normalize_configured_emails(admin_emails)
        allowed = _normalize_configured_emails(allowed_emails)
        provider_coordinates_present = any(
            value.strip() for value in (supabase_url, publishable_key, secret_key)
        )
        admission_configured = provider_coordinates_present or bool(admins or allowed)
        environment = app_env.strip().lower()
        if self.pipeline_mode == "detached" and (self.required or environment == "production"):
            raise ValueError(
                "Detached pipeline mode is allowed only in non-production development."
            )
        if (self.required or environment == "production" or admission_configured) and len(
            admins
        ) != self.bootstrap_admin_count:
            raise ValueError("The bootstrap administrator count is invalid.")
        if len(allowed) > self.normal_user_limit:
            raise ValueError("The normal-user allowlist exceeds the configured capacity.")
        if set(admins) & set(allowed):
            raise ValueError("Bootstrap administrators and normal users must not overlap.")

        if supabase_url.strip():
            issuer = self.issuer_for(supabase_url)
            parsed_supabase = urlsplit(supabase_url.strip().rstrip("/"))
            expected_issuer = (
                f"{parsed_supabase.scheme.lower()}://{parsed_supabase.netloc.lower()}"
                f"{self.issuer_path}"
            )
            if issuer != expected_issuer:
                raise ValueError("Supabase issuer does not match SUPABASE_URL.")

        strict_deployment = self.required or environment == "production"
        if strict_deployment:
            if not supabase_url.strip() or not publishable_key.strip() or not secret_key.strip():
                raise ValueError("Required Supabase auth coordinates are missing.")
            if not admins:
                raise ValueError("Required bootstrap administrator list must not be empty.")
            if self.admission_mode == "allowlist" and len(allowed) == 0:
                raise ValueError("Allowlist admission requires at least one normal-user email.")
        elif admission_configured and (
            not supabase_url.strip() or not publishable_key.strip() or not secret_key.strip()
        ):
            raise ValueError("Supabase auth coordinates are incomplete.")

        parsed = urlsplit(supabase_url.strip())
        if environment == "production":
            if parsed.scheme != "https" or parsed.hostname in {
                "localhost",
                "127.0.0.1",
                "::1",
            }:
                raise ValueError(
                    "Production Supabase configuration must use HTTPS and a remote host."
                )
            if len(self.allowed_origins) != 1 or not self.primary_origin.startswith("https://"):
                raise ValueError("Production auth requires one exact HTTPS application origin.")
            if any(
                "localhost" in origin or "127.0.0.1" in origin for origin in self.allowed_origins
            ):
                raise ValueError("Production auth cannot allow localhost origins.")
        return admins, allowed


def _normalize_configured_emails(raw: str) -> tuple[str, ...]:
    if not raw.strip():
        return ()
    try:
        return normalize_email_list(raw)
    except AuthInputError as exc:
        raise ValueError(str(exc)) from exc


class DiscoveryConfig(BaseModel):
    """Discovery agent output limits from [discovery] in config/app.toml."""

    max_questions: int = 8
    max_projects: int = 8
    max_answer_chars: int = 10000


class ContentArchitectConfig(BaseModel):
    """Content Architect agent output limits from [content_architect] in config/app.toml."""

    max_routes: int = 12


class VisualDesignDirectorConfig(BaseModel):
    """Visual Design Director agent output limits from [visual_design_director]
    in config/app.toml."""

    max_pages: int = 12
    max_catalogue_candidates: int = 6


class ImageRetrievalConfig(BaseModel):
    """Shared provider, cache, and image-processing policy."""

    provider_order: list[str] = Field(default_factory=lambda: ["pexels", "pixabay"])
    cache_root: str = ".workspace/image-search-cache"
    cache_ttl_seconds: int = 86400
    max_queries: int = 3
    max_candidates_per_query: int = 6
    max_candidates_total: int = 12
    max_dimension: int = 2400
    raw_download_max_bytes: int = 24 * 1024 * 1024
    optimized_max_bytes: int = 8 * 1024 * 1024
    minimum_width: int = 1200
    minimum_height: int = 700
    responsive_widths: list[int] = Field(default_factory=lambda: [480, 768, 1280, 1920])
    responsive_formats: list[str] = Field(default_factory=lambda: ["webp", "jpeg"])
    responsive_quality: int = Field(default=84, ge=40, le=95)
    timeout_seconds: float = 15.0
    retry_count: int = 2
    max_retry_wait_seconds: float = 8.0
    unsplash_enabled: bool = False
    unsplash_local_vendoring_authorized: bool = False

    @field_validator("unsplash_enabled", "unsplash_local_vendoring_authorized", mode="before")
    @classmethod
    def _coerce_bool(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return value


class BuildPreparationConfig(BaseModel):
    """Build Preparation limits and lifecycle policy."""

    max_routes: int = 12
    bundle_ttl_days: int = 3
    minimum_reuse_hours: int = 24
    max_bundle_bytes: int = 64 * 1024 * 1024
    network_timeout_seconds: float = 15.0
    network_retry_count: int = 2
    target_contract: str = "react-vite-v1"
    fixture_enabled: bool = False
    fixture_input_path: str = "src/oryxenai/output/visual_design_director_Output.md"
    # Matching Content Architect snapshot for the fixture input above; used to
    # reunite the (CA, VDD) pair the fixture compiles into one v3 pack.
    fixture_content_input_path: str = "src/oryxenai/output/content-architect"
    fixture_output_dir: str = "output"
    fixture_upload: bool = True
    fixture_reasoning_enabled: bool = False
    fixture_debug_mirror_enabled: bool = True
    # Ephemeral per-run staging for the real session/worker path — deliberately
    # separate from fixture_output_dir, which is host-mounted (./output) only
    # for the detached developer fixture/CLI and is NOT volume-mounted into the
    # worker container. Follows the same .workspace/<agent-purpose> convention
    # already used by every other agent's ephemeral Docker-writable paths
    # (code_generator_acquisition.materials_root etc.) so it works unmodified
    # under the non-root container user without any Dockerfile/volume change.
    session_staging_root: str = ".workspace/build-preparation-staging"
    debug_mirror_enabled: bool = True
    model_profile: str = "build_preparation"
    reasoning_enabled: bool = True
    integration_route_threshold: int = 2
    # These are policy defaults for image-rich directions.  The approved VDD
    # projection may explicitly lower them for text-led or privacy-limited
    # work; Build Preparation never fabricates missing roles to meet a quota.
    editorial_image_budget: int = 5
    editorial_image_maximum: int = 6
    visual_component_budget: int = 4
    visual_component_maximum: int = 6
    image_source_attempt_maximum: int = 3
    component_source_attempt_maximum: int = 3
    provider_max_wait_seconds: float = 8.0
    provider_max_concurrency: int = 2
    require_live_visual_resources: bool = True
    auto_derive_visual_resources: bool = True
    delegated_acquisition_enabled: bool = False
    delegated_allowed_categories: list[str] = Field(
        default_factory=lambda: ["image", "font", "component_source"]
    )
    delegated_allowed_providers: list[str] = Field(
        default_factory=lambda: [
            "pexels",
            "pixabay",
            "fontsource",
            "shadcn",
            "magicui",
            "smoothui",
            "cultui",
        ]
    )
    delegated_candidate_limit: int = 8
    delegated_attempt_maximum: int = 3

    @field_validator(
        "fixture_enabled",
        "fixture_upload",
        "fixture_reasoning_enabled",
        "fixture_debug_mirror_enabled",
        "debug_mirror_enabled",
        "reasoning_enabled",
        "require_live_visual_resources",
        "auto_derive_visual_resources",
        "delegated_acquisition_enabled",
        mode="before",
    )
    @classmethod
    def _coerce_bool(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return value


class CodeGeneratorDevelopmentConfig(BaseModel):
    """Development-only admission and planning limits for Code Generator Phase 1."""

    enabled: bool = True
    input_root: str = ".workspace/code-generator-development"
    fixture_map: dict[str, str] = Field(default_factory=dict)
    pack_version: str = "build-preparation-pack-v3"
    schema_version: str = "build-preparation-contract-v3"
    accepted_pack_versions: list[str] = Field(
        default_factory=lambda: ["build-preparation-pack-v3", "build-preparation-pack-v4"]
    )
    accepted_schema_versions: list[str] = Field(
        default_factory=lambda: [
            "build-preparation-contract-v3",
            "build-preparation-contract-v4",
        ]
    )
    target_contract: str = "react-vite-v1"
    director_profile: str = "code_generator_director"
    planner_profile: str = "code_generator_planner"
    max_upload_bytes: int = 16 * 1024 * 1024
    max_uncompressed_bytes: int = 64 * 1024 * 1024
    max_entries: int = 256
    max_compression_ratio: float = 100.0
    max_routes: int = 12
    max_work_units: int = 64
    max_events_page_size: int = 100
    # Local Build Preparation debug-mirror root: directories produced by the
    # Build Preparation stage, each holding build-context/ + build-pack.zip.
    build_preparation_mirror_root: str = "output/build-preparation"
    pipeline_contract_version: str = "code-generator-v4"
    worker_release_id: str = "oryxenai-code-generator-v4"
    quality_gate_version: str = "quality-gate-v2"
    design_similarity_threshold: float = Field(default=0.82, ge=0, le=1)
    design_similarity_history: int = Field(default=3, ge=1, le=10)

    @field_validator("enabled", mode="before")
    @classmethod
    def _coerce_bool(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return value


class CodeGeneratorGenerationConfig(BaseModel):
    """Standalone Phase 3 source-generation limits and trusted commands."""

    scaffold_profile: str = "react-vite-v1"
    scaffold_root: str = "src/oryxenai/agents/code_generator/scaffolds"
    workspace_root: str = ".workspace/code-generator-generation"
    checkpoint_root: str = ".workspace/code-generator-checkpoints"
    foundation_profile: str = "code_generator_foundation_builder"
    route_profile: str = "code_generator_route_builder"
    compose_profile: str = "code_generator_route_composer"
    integration_profile: str = "code_generator_integrator"
    repair_profile: str = "code_generator_repairer"
    max_file_bytes: int = 256 * 1024
    max_response_bytes: int = 2 * 1024 * 1024
    max_source_bytes: int = 8 * 1024 * 1024
    max_request_rounds: int = 4
    max_repair_rounds_per_unit: int = 2
    max_repair_rounds_total: int = 6
    max_route_batch_sections: int = 8
    max_concurrency: int = 1
    typecheck_timeout_seconds: float = 120.0
    typecheck_command: list[str] = Field(default_factory=lambda: ["npm", "run", "typecheck"])
    source_audit_command: list[str] = Field(default_factory=lambda: ["npm", "run", "source:audit"])
    format_command: list[str] = Field(default_factory=list)
    use_real_typecheck: bool = True
    route_concurrency: int = 3
    artifact_store_provider: str = "local_fs"
    artifact_root: str = ".workspace/code-generator-artifacts"
    max_context_chars: int = 120000
    quality_review_max_context_chars: int = 600000
    stable_prompt_prefix_version: str = "code-generator-prompts-v4"

    @field_validator("use_real_typecheck", mode="before")
    @classmethod
    def _coerce_bool(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return value


class CodeGeneratorAcquisitionConfig(BaseModel):
    """Trusted Code Generator resource-acquisition policy."""

    allowlist_image_providers: list[str] = Field(default_factory=lambda: ["pexels", "pixabay"])
    allowlist_font_formats: list[str] = Field(default_factory=lambda: ["woff2", "woff"])
    allowlist_icon_package: str = "lucide"
    allowlist_component_registries: list[str] = Field(
        default_factory=lambda: ["shadcn", "magicui", "smoothui", "cultui"]
    )
    allowlist_style_kinds: list[str] = Field(
        default_factory=lambda: ["pattern", "token_preset", "helper"]
    )
    forbidden_subject_terms: list[str] = Field(default_factory=list)
    user_media_substitution_allowed: bool = False
    max_request_rounds: int = 4
    image_max_bytes: int = 4 * 1024 * 1024
    font_max_bytes: int = 2 * 1024 * 1024
    icon_svg_max_bytes: int = 384 * 1024
    component_max_bytes: int = 512 * 1024
    style_max_bytes: int = 256 * 1024
    materials_root: str = ".workspace/code-generator-materials"
    offline_resource_root: str = ""
    prefer_resource_scout_model: bool = False
    resource_scout_profile: str = "code_generator_resource_scout"
    supported_packages: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @field_validator(
        "user_media_substitution_allowed", "prefer_resource_scout_model", mode="before"
    )
    @classmethod
    def _coerce_bool(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return value


class CodeGeneratorDependenciesConfig(BaseModel):
    """Trusted package and disposable workspace policy for Code Generator."""

    workspaces_root: str = ".workspace/code-generator-workspaces"
    npm_executable: str = ""
    npm_cache_root: str = ""
    allow_network_install: bool = False
    allow_install_scripts: bool = False
    supported_packages: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @field_validator("allow_network_install", "allow_install_scripts", mode="before")
    @classmethod
    def _coerce_bool(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return value


class CodeGeneratorVerificationConfig(BaseModel):
    """Final build, browser, artifact, and repair policy."""

    enabled: bool = True
    profile_id: str = "code-generator-verification-v1"
    browser_name: str = "chromium"
    browser_executable: str = ""
    browser_headless: bool = True
    browser_timeout_ms: int = 15000
    install_timeout_seconds: float = 180.0
    typecheck_timeout_seconds: float = 180.0
    format_timeout_seconds: float = 60.0
    build_timeout_seconds: float = 180.0
    runtime_timeout_ms: int = 15000
    max_output_bytes: int = 65536
    max_artifact_bytes: int = 32 * 1024 * 1024
    reject_source_maps: bool = True
    install_command: list[str] = Field(
        default_factory=lambda: [
            "npm",
            "ci",
            "--ignore-scripts",
            "--offline",
            "--no-audit",
            "--no-fund",
        ]
    )
    typecheck_command: list[str] = Field(default_factory=lambda: ["npm", "run", "typecheck"])
    format_command: list[str] = Field(default_factory=list)
    build_command: list[str] = Field(default_factory=lambda: ["npm", "run", "build"])
    source_check_ids: list[str] = Field(
        default_factory=lambda: ["source.paths", "source.coverage", "source.policy"]
    )
    build_check_ids: list[str] = Field(
        default_factory=lambda: [
            "build.install",
            "build.typecheck",
            "build.production",
            "build.closure",
        ]
    )
    runtime_check_ids: list[str] = Field(
        default_factory=lambda: [
            "runtime.routes",
            "runtime.navigation",
            "runtime.assets",
            "runtime.accessibility",
            "runtime.geometry",
            "runtime.reduced_motion",
            "runtime.interactions",
        ]
    )
    viewport_profiles: dict[str, dict[str, int]] = Field(
        default_factory=lambda: {
            "mobile": {"width": 390, "height": 844},
            "tablet": {"width": 768, "height": 1024},
            "desktop": {"width": 1440, "height": 900},
        }
    )
    geometry_thresholds: dict[str, float] = Field(
        default_factory=lambda: {
            "min_text_px": 12.0,
            "min_touch_target_px": 36.0,
            "max_section_gap_vh": 0.9,
            "max_section_overlap_ratio": 0.2,
        }
    )
    preview_root: str = ".workspace/code-generator-preview"
    preview_base_url: str = "http://127.0.0.1:4174/preview"
    preview_host: str = "127.0.0.1"
    preview_port: int = 4174
    preview_parent_origin: str = "http://127.0.0.1:8000"
    preview_embed_origins: list[str] = Field(
        default_factory=lambda: ["http://127.0.0.1:8000", "http://localhost:8000"]
    )
    preview_retention_days: int = 3
    preview_route_prefix: str = "/preview"
    # Production promotion must prove the public gateway URL. Offline tests
    # can disable only that external hop while retaining immutable storage
    # read-back and all source/build/runtime gates.
    preview_public_readback_required: bool = True
    # Local development uses the filesystem. Hosted API/worker/gateway
    # deployments switch this to ``artifact_storage`` so previews survive
    # container restarts without creating a container per portfolio.
    preview_storage_provider: str = "local_fs"
    preview_storage_prefix: str = "preview"
    # Where the complete generated portfolio (source project + built dist +
    # metadata) is exported after a successful promotion. Advisory: export
    # failures never fail a promoted run.
    export_root: str = "output/code-gen-output"
    export_timezone: str = "Asia/Kolkata"

    @field_validator("enabled", "browser_headless", "reject_source_maps", mode="before")
    @classmethod
    def _coerce_bool(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return value


class ArtifactStorageConfig(BaseModel):
    """Non-secret S3-compatible artifact storage settings."""

    provider: str = "r2_s3"
    endpoint_url: str = ""
    bucket: str = ""
    region: str = "auto"
    prefix: str = "temporary"
    require_lifecycle: bool = True
    access_key_env: str = "R2_ACCESS_KEY_ID"
    secret_key_env: str = "R2_SECRET_ACCESS_KEY"  # noqa: S105 - this is an environment-variable name, never a secret value

    @field_validator("require_lifecycle", mode="before")
    @classmethod
    def _coerce_bool(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return value


class ResourceProviderConfig(BaseModel):
    """Non-secret registry provider endpoints and feature flags."""

    registries_enabled: bool = True
    shadcn_catalog_url: str = "https://ui.shadcn.com/r/styles/new-york-v4/registry.json"
    shadcn_item_url_template: str = "https://ui.shadcn.com/r/styles/new-york-v4/{name}.json"
    magicui_catalog_url: str = "https://magicui.design/r/registry.json"
    magicui_item_url_template: str = "https://magicui.design/r/{name}.json"
    magicui_enabled: bool = True
    smoothui_api_base_url: str = "https://smoothui.dev/api/v1"
    smoothui_item_url_template: str = "https://smoothui.dev/r/{name}.json"
    smoothui_enabled: bool = True
    cultui_catalog_url: str = "https://cult-ui.com/r/registry.json"
    cultui_item_url_template: str = "https://cult-ui.com/r/{name}.json"
    cultui_enabled: bool = True
    aceternity_catalog_url: str = "https://ui.aceternity.com/registry/registry.json"
    aceternity_item_url_template: str = "https://ui.aceternity.com/registry/{name}.json"
    aceternity_enabled: bool = False
    registry_order: list[str] = Field(
        default_factory=lambda: ["shadcn", "magicui", "smoothui", "cultui", "aceternity"]
    )
    execution_provider_order: list[str] = Field(
        default_factory=lambda: [
            "fontsource",
            "shadcn",
            "magicui",
            "smoothui",
            "cultui",
            "motion_primitives",
            "lucide",
            "pexels",
        ]
    )
    licence_policy: str = "permissive-local-vendoring-only"
    fontsource_enabled: bool = True
    fontsource_api_base_url: str = "https://api.fontsource.org/v1"
    fontsource_format: str = "woff2"
    fontsource_latin_only: bool = True
    font_profiles: dict[str, dict[str, str]] = Field(default_factory=dict)
    shadcn_release_pin: str = ""
    magicui_release_pin: str = ""
    smoothui_release_pin: str = ""
    cultui_release_pin: str = ""
    shadcn_allowed_components: list[str] = Field(default_factory=list)
    magicui_allowed_components: list[str] = Field(default_factory=list)
    smoothui_allowed_components: list[str] = Field(default_factory=list)
    cultui_allowed_components: list[str] = Field(default_factory=list)
    motion_primitives_enabled: bool = True
    motion_primitives_commit: str = ""
    motion_primitives_allowed_components: list[str] = Field(default_factory=list)
    animate_ui_enabled: bool = False
    pexels_api_key_env: str = "PEXELS_API_KEY"
    pixabay_api_key_env: str = "PIXABAY_API_KEY"
    unsplash_access_key_env: str = "UNSPLASH_ACCESS_KEY"
    lucide_icon_url_template: str = (
        "https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/{name}.svg"
    )

    @field_validator(
        "registries_enabled",
        "magicui_enabled",
        "smoothui_enabled",
        "cultui_enabled",
        "aceternity_enabled",
        "fontsource_enabled",
        "fontsource_latin_only",
        "motion_primitives_enabled",
        "animate_ui_enabled",
        mode="before",
    )
    @classmethod
    def _coerce_bool(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return value


class ModelProfile(BaseModel):
    """A single provider-neutral model profile from config/models.toml."""

    provider: str = "openai_compatible"
    model: str = ""
    display_name: str = ""
    base_url: str = ""
    api_key_env: str = ""
    request_params: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: float = 120.0
    max_retries: int = 0
    max_output_tokens: int = 4096
    reasoning_effort: str = ""
    prompt_cache_ttl: str = ""
    store: bool = False
    capabilities: ModelCapabilities | None = None


class ModelRoutingConfig(BaseModel):
    """Logical engine-to-profile routing from the model configuration."""

    fallback_profile: str = "default"
    selectable_profiles: list[str] = Field(default_factory=list)
    engine_profiles: dict[str, str] = Field(default_factory=dict)


class ModelConfig(BaseModel):
    """All model profiles loaded from config/models.toml."""

    profiles: dict[str, ModelProfile] = Field(default_factory=dict)
    routing: ModelRoutingConfig = Field(default_factory=ModelRoutingConfig)

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
        populate_by_name=True,
    )

    # Secret from .env — optional in code so unit tests can run without it.
    postgres_password: SecretStr = SecretStr("")

    # Supabase coordinates from .env. The publishable key may be rendered to
    # the browser; the secret key and admission lists are server-only.
    supabase_url: str = Field(default="", validation_alias="SUPABASE_URL", repr=False)
    supabase_publishable_key: SecretStr = Field(
        default=SecretStr(""), validation_alias="SUPABASE_PUBLISHABLE_KEY", repr=False
    )
    supabase_secret_key: SecretStr = Field(
        default=SecretStr(""), validation_alias="SUPABASE_SECRET_KEY", repr=False
    )
    admin_bootstrap_emails: str = Field(
        default="", validation_alias="ORYXENAI_ADMIN_BOOTSTRAP_EMAILS", repr=False
    )
    allowed_user_emails: str = Field(
        default="", validation_alias="ORYXENAI_ALLOWED_USER_EMAILS", repr=False
    )

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
    auth: AuthConfig = Field(default_factory=AuthConfig)
    models: ModelConfig = Field(default_factory=ModelConfig)
    discovery: DiscoveryConfig = Field(default_factory=DiscoveryConfig)
    content_architect: ContentArchitectConfig = Field(default_factory=ContentArchitectConfig)
    visual_design_director: VisualDesignDirectorConfig = Field(
        default_factory=VisualDesignDirectorConfig
    )
    image_retrieval: ImageRetrievalConfig = Field(default_factory=ImageRetrievalConfig)
    build_preparation: BuildPreparationConfig = Field(default_factory=BuildPreparationConfig)
    code_generator_development: CodeGeneratorDevelopmentConfig = Field(
        default_factory=CodeGeneratorDevelopmentConfig
    )
    code_generator_generation: CodeGeneratorGenerationConfig = Field(
        default_factory=CodeGeneratorGenerationConfig
    )
    code_generator_acquisition: CodeGeneratorAcquisitionConfig = Field(
        default_factory=CodeGeneratorAcquisitionConfig
    )
    code_generator_dependencies: CodeGeneratorDependenciesConfig = Field(
        default_factory=CodeGeneratorDependenciesConfig
    )
    code_generator_verification: CodeGeneratorVerificationConfig = Field(
        default_factory=CodeGeneratorVerificationConfig
    )
    artifact_storage: ArtifactStorageConfig = Field(default_factory=ArtifactStorageConfig)
    resource_providers: ResourceProviderConfig = Field(default_factory=ResourceProviderConfig)

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
        if "auth" in app_data:
            self.auth = AuthConfig(**app_data["auth"])
        if "discovery" in app_data:
            self.discovery = DiscoveryConfig(**app_data["discovery"])
        if "content_architect" in app_data:
            self.content_architect = ContentArchitectConfig(**app_data["content_architect"])
        if "visual_design_director" in app_data:
            self.visual_design_director = VisualDesignDirectorConfig(
                **app_data["visual_design_director"]
            )
        if "image_retrieval" in app_data:
            self.image_retrieval = ImageRetrievalConfig(**app_data["image_retrieval"])
        if "build_preparation" in app_data:
            self.build_preparation = BuildPreparationConfig(**app_data["build_preparation"])
        if "code_generator_development" in app_data:
            self.code_generator_development = CodeGeneratorDevelopmentConfig(
                **app_data["code_generator_development"]
            )
        if "code_generator_generation" in app_data:
            self.code_generator_generation = CodeGeneratorGenerationConfig(
                **app_data["code_generator_generation"]
            )
        if "code_generator_acquisition" in app_data:
            self.code_generator_acquisition = CodeGeneratorAcquisitionConfig(
                **app_data["code_generator_acquisition"]
            )
        if "code_generator_dependencies" in app_data:
            self.code_generator_dependencies = CodeGeneratorDependenciesConfig(
                **app_data["code_generator_dependencies"]
            )
        if "code_generator_verification" in app_data:
            self.code_generator_verification = CodeGeneratorVerificationConfig(
                **app_data["code_generator_verification"]
            )
        if "artifact_storage" in app_data:
            self.artifact_storage = ArtifactStorageConfig(**app_data["artifact_storage"])
        if "resource_providers" in app_data:
            self.resource_providers = ResourceProviderConfig(**app_data["resource_providers"])

        # Model profiles.
        models_data = _load_toml("models.toml")
        profiles: dict[str, ModelProfile] = {}
        if "profiles" in models_data and isinstance(models_data["profiles"], dict):
            for name, raw in models_data["profiles"].items():
                if isinstance(raw, dict):
                    profiles[name] = ModelProfile(**raw)
        routing_raw = models_data.get("routing", {})
        routing = ModelRoutingConfig(**routing_raw) if isinstance(routing_raw, dict) else None
        self.models = ModelConfig(profiles=profiles, routing=routing or ModelRoutingConfig())
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

    @property
    def normalized_admin_bootstrap_emails(self) -> tuple[str, ...]:
        return _normalize_configured_emails(self.admin_bootstrap_emails)

    @property
    def normalized_allowed_user_emails(self) -> tuple[str, ...]:
        return _normalize_configured_emails(self.allowed_user_emails)

    def validate_auth_configuration(self) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Validate auth startup policy and return normalized admission lists."""
        return self.auth.validate_environment(
            app_env=self.app.env,
            supabase_url=self.supabase_url,
            publishable_key=self.supabase_publishable_key.get_secret_value(),
            secret_key=self.supabase_secret_key.get_secret_value(),
            admin_emails=self.admin_bootstrap_emails,
            allowed_emails=self.allowed_user_emails,
        )

    @property
    def auth_public_config(self) -> dict[str, object]:
        """Return only browser-safe, reviewed auth configuration."""
        return {
            "supabaseUrl": self.supabase_url.rstrip("/"),
            "publishableKey": self.supabase_publishable_key.get_secret_value(),
            "admissionMode": self.auth.admission_mode,
            "primaryOrigin": self.auth.primary_origin,
            "callbackUrl": self.auth.callback_url(),
            "signInPath": self.auth.sign_in_path,
            "callbackPath": self.auth.callback_path,
            "accessNotApprovedPath": self.auth.access_not_approved_path,
            "accountUnavailablePath": self.auth.account_unavailable_path,
            "appPath": self.auth.app_path,
            "adminPath": self.auth.admin_path,
            "onboardingPath": self.auth.onboarding_path,
            "pipelineMode": self.auth.pipeline_mode,
        }


# ---------------------------------------------------------------------------
# Singleton access
# ---------------------------------------------------------------------------

_settings: Settings | None = None


def _export_dotenv_secrets() -> None:
    """Export root .env variables into the process environment.

    pydantic-settings reads .env for declared settings fields, but provider
    adapters resolve API keys via ``os.environ``. To honor the documented
    contract ("read the named secret from .env only when a real model call
    is made"), this exports .env key=value pairs that are not already set
    in the environment.
    """
    env_path = _REPO_ROOT / ".env"
    if not env_path.is_file():
        return
    try:
        values: dict[str, str] = {}
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, _, value = stripped.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                # Keep the last declaration, matching dotenv parsing when a
                # local handoff leaves a sanitized placeholder before the
                # actual private value.
                values[key] = value
        for key, value in values.items():
            if key not in os.environ:
                os.environ[key] = value
    except OSError:
        return


def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    global _settings
    if _settings is None:
        _export_dotenv_secrets()
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Clear the cached settings singleton (used by tests)."""
    global _settings
    _settings = None
