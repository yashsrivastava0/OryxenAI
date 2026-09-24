"""Shared provider-neutral model runtime.

Agents continue to depend only on ``ModelClient``. This component owns routing,
profile validation, adapter reuse, privacy-free preflight, and client cleanup.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict

from oryxenai.agents.shared.contracts import ModelClient, ResolvedModelRoute
from oryxenai.agents.shared.model_execution import RoutedModelClient
from oryxenai.agents.shared.model_quota import CapacityRegistry, ModelUsageReconciler
from oryxenai.agents.shared.model_router import ModelRouter
from oryxenai.agents.shared.model_usage import ModelUsageLedger, UsageTrackingModelClient
from oryxenai.agents.shared.providers.errors import (
    ProviderConfigError,
    ProviderError,
    stable_provider_failure,
)
from oryxenai.agents.shared.providers.factory import build_adapter, can_build

if TYPE_CHECKING:
    from oryxenai.core.settings import ModelConfig, ModelProfile

_PREFLIGHT_PROTOCOL = "pipeline-model-preflight-v1"
_PREFLIGHT_TTL_SECONDS = 300.0
_PREFLIGHT_OPERATIONS = {
    "discovery": "understand_and_question",
    "content_architect": "plan_content",
}
_ACTIVE_ENGINES = frozenset(_PREFLIGHT_OPERATIONS)


class _PipelinePreflightEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    protocol: Literal["pipeline-model-preflight-v1"]


class ModelRuntime:
    """Resolve and reuse configured provider clients for one process."""

    def __init__(self, model_config: ModelConfig, sessionmaker: Any = None) -> None:
        self._config = model_config
        self._router = ModelRouter(model_config)
        self._clients: dict[str, ModelClient] = {}
        self._tracked_clients: dict[str, ModelClient] = {}
        utilization_ceiling = self._config.routing.policy.utilization_ceiling
        self._usage_ledger = ModelUsageLedger(sessionmaker, utilization_ceiling)
        self._capacity = CapacityRegistry(utilization_ceiling)
        self._preflight_cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._closed = False
        self.validate_configuration()

    @property
    def router(self) -> ModelRouter:
        return self._router

    @property
    def config(self) -> ModelConfig:
        return self._config

    @property
    def usage_ledger(self) -> ModelUsageLedger:
        return self._usage_ledger

    @property
    def capacity_registry(self) -> CapacityRegistry:
        return self._capacity

    def attach_sessionmaker(self, sessionmaker: Any) -> None:
        self._usage_ledger.sessionmaker = sessionmaker

    async def reconcile_usage(self) -> dict[str, int]:
        """Refresh provider usage/capability observations when a DB is attached."""

        if self._usage_ledger.sessionmaker is None:
            return {"observations": 0, "sources": 0}
        return await ModelUsageReconciler(
            sessionmaker=self._usage_ledger.sessionmaker,
            model_config=self._config,
            capacity_registry=self._capacity,
        ).reconcile()

    def resolve_profile_name(self, engine: str, override: str = "") -> str:
        requested = str(override or "").strip()
        if requested and not self._router.is_selectable(requested):
            raise ProviderConfigError(
                f"Model profile '{requested}' is not selectable. Choose an "
                "allowlisted pipeline profile."
            )
        profile_name = self._router.resolve_profile_name(engine, requested)
        if profile_name not in self._config.profiles:
            raise ProviderConfigError(
                f"Model route '{engine}' resolves to missing profile '{profile_name}'."
            )
        return profile_name

    def resolve(self, engine: str, override: str = "") -> ModelClient:
        """Return one lazily initialized client per complete profile fingerprint."""

        if self._closed:
            raise ProviderConfigError("The model runtime is already closed.")
        profile_name = self.resolve_profile_name(engine, override)
        profile = self._require_profile(profile_name)
        self._validate_profile(profile_name, profile)
        fingerprint = self.profile_fingerprint(profile_name)
        client = self._clients.get(fingerprint)
        if client is None:
            try:
                client = build_adapter(profile)
            except ValueError as exc:
                raise ProviderConfigError(str(exc)) from exc
            from oryxenai.agents.shared.model_client import MockModelClient

            if isinstance(client, MockModelClient):
                raise ProviderConfigError(
                    "A live model runtime cannot use MockModelClient. Inject mocks only "
                    "into explicit tests or development harnesses."
                )
            self._clients[fingerprint] = client
        if self._usage_ledger.sessionmaker is None:
            return client
        tracked = self._tracked_clients.get(fingerprint)
        if tracked is None:
            profile_route = ResolvedModelRoute(
                profile_name=profile_name,
                provider=profile.provider,
                model=profile.model,
                credential_alias=str(getattr(profile, "credential_alias", "") or ""),
                capacity_source_id=str(getattr(profile, "capacity_source_id", "") or ""),
                quota_group=str(getattr(profile, "quota_group", "") or ""),
                profile_fingerprint=fingerprint,
                policy_version=self._router.config.routing.policy.version,
                input_policy=str(getattr(profile, "input_policy", "any") or "any"),
                pricing_card_ref=str(getattr(profile, "pricing_card_ref", "") or ""),
            )
            tracked = UsageTrackingModelClient(client, profile_route, self._usage_ledger)
            self._tracked_clients[fingerprint] = tracked
        return tracked

    def resolve_profile_client(self, profile_name: str) -> ModelClient:
        """Resolve a concrete profile without reinterpreting its operation route."""

        profile = self._require_profile(str(profile_name))
        self._validate_profile(str(profile_name), profile)
        fingerprint = self.profile_fingerprint(str(profile_name))
        client = self._clients.get(fingerprint)
        if client is None:
            client = build_adapter(profile)
            from oryxenai.agents.shared.model_client import MockModelClient

            if isinstance(client, MockModelClient):
                raise ProviderConfigError(
                    "A live model runtime cannot use MockModelClient. Inject mocks only "
                    "into explicit tests or development harnesses."
                )
            self._clients[fingerprint] = client
        return client

    def resolve_operation_profile_name(
        self,
        engine: str,
        operation: str,
        *,
        input_classification: str = "unknown",
        override: str = "",
    ) -> str:
        try:
            return self._router.resolve_operation_profile_name(
                engine,
                operation,
                input_classification=input_classification,
                override_profile_name=override,
            )
        except ValueError as exc:
            raise ProviderConfigError(str(exc)) from exc

    def policy_profile_name(self, engine: str, operation: str = "") -> str:
        """Return the configured primary profile for safe metadata/readback."""

        if operation:
            return self.resolve_operation_profile_name(engine, operation)
        routes = self._config.routing.operation_profiles.get(engine, {})
        for route in routes.values():
            if route.primary_profile:
                return route.primary_profile
        return self.resolve_profile_name(engine)

    def routed_client(
        self,
        engine: str,
        *,
        override_profile_name: str = "",
        input_classification: str = "unknown",
    ) -> RoutedModelClient:
        return RoutedModelClient(
            self,
            engine,
            override_profile_name=override_profile_name,
            usage_ledger=self._usage_ledger,
            input_classification=input_classification,
        )

    def profile_fingerprint_for(self, engine: str, override: str = "") -> str:
        return self.profile_fingerprint(self.resolve_profile_name(engine, override))

    def profile_fingerprint(self, profile_name: str) -> str:
        profile = self._require_profile(profile_name)
        material = {"profile_id": profile_name, **profile.model_dump(mode="json")}
        return hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    async def preflight(self, engines: list[str], override: str = "") -> dict[str, Any]:
        """Check each distinct routed profile with fixed privacy-free input."""

        distinct: dict[str, str] = {}
        for engine in engines:
            profile_name = self._preflight_profile_name(engine, override)
            distinct.setdefault(self.profile_fingerprint(profile_name), profile_name)

        receipts: list[dict[str, Any]] = []
        for fingerprint, profile_name in distinct.items():
            cached = self._preflight_cache.get(fingerprint)
            if cached and time.monotonic() - cached[0] <= _PREFLIGHT_TTL_SECONDS:
                receipts.append(dict(cached[1]))
                continue
            profile = self._require_profile(profile_name)
            client = self.resolve(profile_name)
            try:
                result = await client.generate_structured(
                    operation="pipeline.model_preflight",
                    instructions=(
                        f"Return ok=true and protocol={_PREFLIGHT_PROTOCOL}. "
                        "This fixed request contains no user or portfolio data."
                    ),
                    input_payload={"protocol": _PREFLIGHT_PROTOCOL},
                    output_model=_PipelinePreflightEnvelope,
                    system_prompt="You are a transport preflight. Return only the required JSON.",
                    model_profile=profile_name,
                    strict_schema=bool(
                        profile.capabilities
                        and profile.capabilities.structured_output_mode == "native_json_schema"
                    ),
                )
                envelope = _PipelinePreflightEnvelope.model_validate(
                    getattr(result, "parsed_output", result)
                )
                if not envelope.ok:
                    raise ProviderConfigError(
                        "The configured model provider returned an invalid preflight receipt."
                    )
            except ProviderError:
                raise
            except Exception as exc:
                raise ProviderConfigError(
                    "The configured model provider failed its privacy-free preflight."
                ) from exc
            receipt = {
                "profile_id": profile_name,
                "profile_fingerprint": fingerprint,
                "latency_ms": float(getattr(result, "latency_ms", 0.0) or 0.0),
                "finish_reason": str(getattr(result, "finish_reason", "") or ""),
                "usage": dict(getattr(result, "usage", {}) or {}),
            }
            self._preflight_cache[fingerprint] = (time.monotonic(), receipt)
            receipts.append(dict(receipt))

        return {
            "status": "ready",
            "checked_at": datetime.now(UTC).isoformat(),
            "private_context_sent": False,
            "protocol": _PREFLIGHT_PROTOCOL,
            "profiles": receipts,
        }

    def preflight_status(self, engines: list[str], override: str = "") -> dict[str, Any]:
        """Report the in-process preflight cache without making a model call.

        Readiness is polled frequently by the developer UI.  It must be able
        to distinguish a successful explicit preflight from a missing/expired
        one without silently issuing another billable request on every poll.
        ``preflight`` remains the only method that talks to the provider.
        """

        distinct: dict[str, str] = {}
        for engine in engines:
            profile_name = self._preflight_profile_name(engine, override)
            distinct.setdefault(self.profile_fingerprint(profile_name), profile_name)
        now = time.monotonic()
        missing = [
            profile_name
            for fingerprint, profile_name in distinct.items()
            if not (
                (cached := self._preflight_cache.get(fingerprint))
                and now - cached[0] <= _PREFLIGHT_TTL_SECONDS
            )
        ]
        if missing:
            return {
                "status": "required",
                "checked": False,
                "checked_profiles": [],
                "private_context_sent": False,
            }
        return {
            "status": "ready",
            "checked": True,
            "checked_profiles": [name for _fingerprint, name in distinct.items()],
            "private_context_sent": False,
        }

    async def aclose(self) -> None:
        clients = list(self._clients.values())
        self._clients.clear()
        self._tracked_clients.clear()
        self._preflight_cache.clear()
        self._closed = True
        for client in clients:
            close = getattr(client, "aclose", None)
            if close is not None:
                await close()

    def clear_preflight_cache(self) -> None:
        self._preflight_cache.clear()

    def _preflight_profile_name(self, engine: str, override: str = "") -> str:
        operation = _PREFLIGHT_OPERATIONS.get(str(engine).strip())
        if operation and self._router.operation_route(engine, operation) is not None:
            return self.resolve_operation_profile_name(
                engine,
                operation,
                input_classification="personal",
                override=override if engine not in _ACTIVE_ENGINES else "",
            )
        return self.resolve_profile_name(engine, override)

    def validate_configuration(self) -> None:
        referenced = {
            self._router.fallback_profile_name(),
            *self._config.routing.engine_profiles.values(),
            *self._router.selectable_profile_names(),
        }
        for routes in self._config.routing.operation_profiles.values():
            for route in routes.values():
                referenced.update(
                    name
                    for name in (
                        route.primary_profile,
                        route.sanitized_primary_profile,
                        *route.fallback_profiles,
                    )
                    if name
                )
        for profile_name in sorted(str(item).strip() for item in referenced if str(item).strip()):
            self._validate_profile(profile_name, self._require_profile(profile_name))

    def _require_profile(self, profile_name: str) -> ModelProfile:
        profile = self._config.get_profile(profile_name)
        if profile is None:
            raise ProviderConfigError(f"Model profile '{profile_name}' is not configured.")
        return profile

    @staticmethod
    def _validate_profile(profile_name: str, profile: ModelProfile) -> None:
        provider = profile.provider.strip().casefold()
        if provider == "openai_responses":
            raise ProviderConfigError(
                f"Model profile '{profile_name}' requests openai_responses, but no "
                "Responses transport is implemented."
            )
        if not can_build(profile):
            raise ProviderConfigError(
                f"Model profile '{profile_name}' uses unsupported provider '{profile.provider}'."
            )
        if not profile.model.strip():
            raise ProviderConfigError(f"Model profile '{profile_name}' has no model configured.")
        if not profile.api_key_env.strip():
            raise ProviderConfigError(
                f"Model profile '{profile_name}' has no api_key_env configured."
            )
        if profile.timeout_seconds <= 0 or profile.max_output_tokens <= 0:
            raise ProviderConfigError(
                f"Model profile '{profile_name}' has a non-positive timeout or output budget."
            )
        capabilities = profile.capabilities
        if capabilities is None:
            raise ProviderConfigError(
                f"Model profile '{profile_name}' must declare a capabilities table."
            )
        mode = capabilities.structured_output_mode
        if mode == "json_object" and not capabilities.json_object_mode:
            raise ProviderConfigError(
                f"Model profile '{profile_name}' selects JSON-object mode but declares it unsupported."
            )
        if mode == "native_json_schema" and not capabilities.json_schema_mode:
            raise ProviderConfigError(
                f"Model profile '{profile_name}' selects native JSON Schema but declares it unsupported."
            )
        if capabilities.thinking_strategy == "disabled":
            if capabilities.thinking_mode or capabilities.effort_parameter != "none":
                raise ProviderConfigError(
                    f"Model profile '{profile_name}' disables thinking but declares thinking parameters."
                )
        elif not capabilities.thinking_mode:
            raise ProviderConfigError(
                f"Model profile '{profile_name}' configures thinking but declares it unsupported."
            )
        if provider == "anthropic" and capabilities.effort_parameter == "reasoning_effort":
            raise ProviderConfigError(
                f"Model profile '{profile_name}' uses an OpenAI effort parameter on Anthropic."
            )
        if provider in {
            "openai",
            "openai_compatible",
            "experiential",
            "opencode_go",
            "scalemax",
        } and (capabilities.effort_parameter == "output_config_effort"):
            raise ProviderConfigError(
                f"Model profile '{profile_name}' uses an Anthropic effort parameter on an "
                "OpenAI-compatible transport."
            )
        if profile.store and not capabilities.supports_store_parameter:
            raise ProviderConfigError(
                f"Model profile '{profile_name}' enables storage but declares it unsupported."
            )
        if profile.input_policy not in {"any", "sanitized", "synthetic", "personal_luna_only"}:
            raise ProviderConfigError(
                f"Model profile '{profile_name}' has an unsupported input_policy."
            )


_RUNTIMES: dict[int, tuple[ModelConfig, ModelRuntime]] = {}


def get_model_runtime(model_config: ModelConfig, sessionmaker: Any = None) -> ModelRuntime:
    key = id(model_config)
    cached = _RUNTIMES.get(key)
    if cached is not None and cached[0] is model_config:
        if sessionmaker is not None:
            cached[1].attach_sessionmaker(sessionmaker)
        return cached[1]
    runtime = ModelRuntime(model_config, sessionmaker=sessionmaker)
    _RUNTIMES[key] = (model_config, runtime)
    return runtime


async def close_model_runtime(model_config: ModelConfig) -> None:
    cached = _RUNTIMES.pop(id(model_config), None)
    if cached is not None and cached[0] is model_config:
        await cached[1].aclose()


def clear_model_preflight_caches() -> None:
    for _config, runtime in _RUNTIMES.values():
        runtime.clear_preflight_cache()


def safe_preflight_error(error: Exception) -> tuple[str, str]:
    if isinstance(error, ProviderError):
        return stable_provider_failure(error)
    return "PROVIDER_PREFLIGHT_FAILED", "The configured model provider failed preflight safely."


def validate_pipeline_job_timeouts(settings: Any) -> None:
    """Ensure each durable ceiling can contain its bounded call graph."""

    budgets = {
        "discovery.understand_and_question": ("discovery", 1, 60.0),
        "discovery.build_or_revise_brief": ("discovery", 1, 60.0),
        "discovery.prepare_questions": ("discovery", 1, 60.0),
        "discovery.build_brief": ("discovery", 1, 60.0),
        "content_architect.build": ("content_architect", 3, 120.0),
    }
    runtime = get_model_runtime(settings.models)
    for job_kind, (engine, call_count, margin) in budgets.items():
        operation = _PREFLIGHT_OPERATIONS.get(engine, "")
        profile_name = (
            runtime.resolve_operation_profile_name(
                engine, operation, input_classification="personal"
            )
            if operation and runtime.router.operation_route(engine, operation) is not None
            else runtime.resolve_profile_name(engine)
        )
        profile = settings.models.get_profile(profile_name)
        if profile is None:
            continue
        # SDK/provider adapters never retry independently.  Recovery is owned
        # by one shared operation budget and is represented below by one
        # additional bounded transmission.
        per_call_attempts = 1
        route = runtime.router.operation_route(engine, operation) if operation else None
        timeout = (
            float(route.timeout_seconds)
            if route and route.timeout_seconds
            else profile.timeout_seconds
        )
        minimum = timeout * call_count * per_call_attempts + margin
        configured = settings.worker_job.timeout_for(job_kind)
        if configured < minimum:
            raise ProviderConfigError(
                f"Job timeout for '{job_kind}' is {configured:g}s, below the bounded "
                f"runtime budget of {minimum:g}s for profile '{profile_name}'."
            )
