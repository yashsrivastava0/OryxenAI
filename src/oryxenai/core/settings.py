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

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from oryxenai.agents.shared.providers.capabilities import ModelCapabilities

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
    component_source_attempt_maximum: int = 3
    provider_max_wait_seconds: float = 8.0
    provider_max_concurrency: int = 2
    provider_max_requests: int = 32
    require_live_visual_resources: bool = True
    auto_derive_visual_resources: bool = True

    @field_validator(
        "fixture_enabled",
        "fixture_upload",
        "fixture_reasoning_enabled",
        "fixture_debug_mirror_enabled",
        "debug_mirror_enabled",
        "reasoning_enabled",
        "require_live_visual_resources",
        "auto_derive_visual_resources",
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
    target_contract: str = "react-vite-v1"
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
    format_command: list[str] = Field(default_factory=list)
    use_real_typecheck: bool = True

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
    component_request_maximum: int = 6
    style_max_bytes: int = 256 * 1024
    materials_root: str = ".workspace/code-generator-materials"
    offline_resource_root: str = ""
    prefer_resource_scout_model: bool = False
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
        ]
    )
    viewport_profiles: dict[str, dict[str, int]] = Field(
        default_factory=lambda: {
            "mobile": {"width": 390, "height": 844},
            "tablet": {"width": 768, "height": 1024},
            "desktop": {"width": 1440, "height": 900},
        }
    )
    preview_root: str = ".workspace/code-generator-preview"
    preview_base_url: str = "http://127.0.0.1:4174/preview"
    preview_host: str = "127.0.0.1"
    preview_port: int = 4174
    preview_parent_origin: str = "http://127.0.0.1:8000"
    preview_retention_days: int = 3
    preview_route_prefix: str = "/preview"
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
    base_url: str = ""
    api_key_env: str = ""
    request_params: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: float = 120.0
    max_retries: int = 0
    max_output_tokens: int = 4096
    reasoning_effort: str = ""
    store: bool = False
    capabilities: ModelCapabilities | None = None


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
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, _, value = stripped.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
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
