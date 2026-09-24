"""Global operation routing, quota admission, and bounded recovery."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

from oryxenai.agents.shared.contracts import ModelClient, OperationBudget, ResolvedModelRoute
from oryxenai.agents.shared.model_usage import ModelUsageLedger, context_from_request
from oryxenai.agents.shared.providers.errors import (
    ModelCapacityUnavailableError,
    ModelInputTooLargeError,
    ModelOutputInvalidError,
    ModelRoutingPolicyChangedError,
    ModelUsagePersistenceError,
    ProviderAuthError,
    ProviderConfigError,
    ProviderCreditError,
    ProviderError,
)

if TYPE_CHECKING:
    from oryxenai.agents.shared.model_runtime import ModelRuntime


_PIPELINE_ENGINES = frozenset({"discovery", "content_architect"})


class RoutedModelClient(ModelClient):
    """ModelClient facade that owns one shared operation budget.

    Agents remain unaware of provider/model names.  A call chooses the route
    from the immutable config policy, reserves one application transmission,
    and can consume at most one shared recovery slot for a retry or fallback.
    """

    def __init__(
        self,
        runtime: ModelRuntime,
        engine: str,
        *,
        override_profile_name: str = "",
        usage_ledger: ModelUsageLedger | None = None,
        input_classification: str = "unknown",
        operation_budget: OperationBudget | None = None,
    ) -> None:
        self._runtime = runtime
        self._engine = str(engine).strip()
        self._override = str(override_profile_name or "").strip()
        self._usage = usage_ledger or runtime.usage_ledger
        self._input_classification = str(input_classification or "unknown").strip().casefold()
        self._budget = operation_budget or self._build_budget()

    @property
    def budget(self) -> OperationBudget:
        return self._budget

    def route_for(
        self,
        operation: str,
        *,
        request_context: Mapping[str, Any] | None = None,
        input_classification: str | None = None,
    ) -> ResolvedModelRoute:
        classification = self._classification(request_context, input_classification)
        names = self._ordered_names(
            self._runtime.router.operation_profile_names(
                self._engine,
                operation,
                input_classification=classification,
                # A legacy first-four profile lock must not silently route to
                # OpenAI/Anthropic.  It is retained only for API compatibility.
                override_profile_name=(
                    self._override if self._engine not in _PIPELINE_ENGINES else ""
                ),
            )
        )
        if not names:
            raise ProviderConfigError(
                f"No eligible model route is configured for {self._engine}.{operation}."
            )
        profile_name = names[0]
        profile = self._runtime.config.get_profile(profile_name)
        if profile is None:
            raise ProviderConfigError(f"Model profile '{profile_name}' is not configured.")
        route_policy = self._runtime.router.operation_route(self._engine, operation)
        return ResolvedModelRoute(
            profile_name=profile_name,
            provider=profile.provider,
            model=profile.model,
            credential_alias=str(getattr(profile, "credential_alias", "") or ""),
            capacity_source_id=str(getattr(profile, "capacity_source_id", "") or ""),
            quota_group=str(getattr(profile, "quota_group", "") or ""),
            profile_fingerprint=self._runtime.profile_fingerprint(profile_name),
            policy_version=self._runtime.router.config.routing.policy.version,
            input_policy=self._effective_input_policy(profile, route_policy),
            pricing_card_ref=str(getattr(profile, "pricing_card_ref", "") or ""),
            alternatives=tuple(names[1:]),
        )

    async def complete(
        self,
        system_prompt: str,
        task_prompt: str,
        request_params: dict[str, Any] | None = None,
    ) -> str:
        # Plain completion is retained for protocol compatibility.  It still
        # uses the same route/budget controller and never invokes SDK retries.
        route = self.route_for("complete", request_context=request_params)
        self._admit_normal()
        client = self._runtime.resolve_profile_client(route.profile_name)
        context = context_from_request(
            engine=self._engine,
            operation="complete",
            request_context=request_params,
            input_classification=self._input_classification,
        )
        attempt_id = await self._usage.reserve(
            route=route,
            context=context,
            attempt_kind="normal",
            request_attempt=self._budget.transmissions,
            fallback_attempt=0,
        )
        # A transmission is counted only after the durable reservation commits.
        # If admission fails, no provider request has been sent and no retry
        # layer may silently manufacture one.
        self._budget.record_transmission()
        started = time.monotonic()
        try:
            result = await client.complete(system_prompt, task_prompt, request_params)
        except Exception as exc:
            if isinstance(exc, ProviderError):
                exc.details.setdefault("provider_label", _provider_label(route.provider))
                exc.details.setdefault("model", route.model)
            await self._usage.finish(
                attempt_id,
                route=route,
                context=context,
                error=exc,
                elapsed_ms=(time.monotonic() - started) * 1000.0,
            )
            raise
        await self._usage.finish(
            attempt_id,
            route=route,
            context=context,
            result=None,
            elapsed_ms=(time.monotonic() - started) * 1000.0,
        )
        return result

    async def generate_structured(
        self,
        *,
        operation: str,
        instructions: str,
        input_payload: Mapping[str, object],
        output_model: type[Any],
        system_prompt: str | None = None,
        model_profile: Any = None,
        request_context: Any = None,
        strict_schema: bool = False,
        result_validator: Callable[[dict[str, Any]], None] | None = None,
    ) -> Any:
        del model_profile
        classification = self._classification(
            request_context, input_payload.get("input_classification")
        )
        self._assert_policy_snapshot(request_context)
        names = self._ordered_names(
            self._runtime.router.operation_profile_names(
                self._engine,
                operation,
                input_classification=classification,
                override_profile_name=(
                    self._override if self._engine not in _PIPELINE_ENGINES else ""
                ),
            ),
            estimated_input_tokens=max(1, len(str(input_payload)) // 4),
            input_classification=classification,
        )
        if not names:
            raise ProviderConfigError(
                f"No eligible model route is configured for {self._engine}.{operation}."
            )
        route_policy = self._runtime.router.operation_route(self._engine, operation)
        estimated_input_tokens = max(1, len(str(input_payload)) // 4)
        if (
            route_policy is not None
            and route_policy.input_limit_tokens is not None
            and estimated_input_tokens > int(route_policy.input_limit_tokens)
        ):
            raise ModelInputTooLargeError(
                f"The {operation} input exceeds its configured admission ceiling."
            )
        self._admit_normal()
        last_error: BaseException | None = None
        for index, profile_name in enumerate(names):
            if index > 0:
                if self._budget.recovery_remaining <= 0:
                    break
                self._budget.admit_recovery()
            profile = self._runtime.config.get_profile(profile_name)
            if profile is None:
                continue
            route = ResolvedModelRoute(
                profile_name=profile_name,
                provider=profile.provider,
                model=profile.model,
                credential_alias=str(getattr(profile, "credential_alias", "") or ""),
                capacity_source_id=str(getattr(profile, "capacity_source_id", "") or ""),
                quota_group=str(getattr(profile, "quota_group", "") or ""),
                profile_fingerprint=self._runtime.profile_fingerprint(profile_name),
                policy_version=self._runtime.router.config.routing.policy.version,
                input_policy=self._effective_input_policy(profile, route_policy),
                pricing_card_ref=str(getattr(profile, "pricing_card_ref", "") or ""),
                alternatives=tuple(names[index + 1 :]),
            )
            call_context = context_from_request(
                engine=self._engine,
                operation=operation,
                request_context=request_context,
                input_classification=classification,
            )
            call_context.metadata.update(
                {
                    "normal_calls": self._budget.normal_calls,
                    "recovery_allowance": self._budget.recovery_allowance,
                    "input_fingerprint": hashlib.sha256(
                        json.dumps(dict(input_payload), sort_keys=True, default=str).encode("utf-8")
                    ).hexdigest(),
                }
            )
            try:
                attempt_id = await self._usage.reserve(
                    route=route,
                    context=call_context,
                    attempt_kind="normal" if index == 0 else "fallback",
                    request_attempt=self._budget.transmissions + 1,
                    fallback_attempt=index,
                    input_tokens_reserved=estimated_input_tokens,
                )
            except ModelCapacityUnavailableError as exc:
                # Capacity rejection happens before a provider transmission.
                # It is still attributable to the attempted source and may
                # consume the one shared recovery slot when another configured
                # source is eligible.  Never let the exception bypass the
                # remaining Gemini capacity sources.
                exc.details.update(
                    {
                        "provider_label": _provider_label(route.provider),
                        "provider": route.provider,
                        "model": route.model,
                        "credential_alias": route.credential_alias,
                        "capacity_source_id": route.capacity_source_id,
                        "fallback_attempt": index,
                    }
                )
                last_error = exc
                self._runtime.capacity_registry.mark_failure(route.capacity_source_id)
                if not self._can_recover(exc, index, names, route):
                    raise
                continue
            except ModelUsagePersistenceError:
                # A committed accounting record is a precondition for every
                # provider call.  Falling through to a different provider
                # while the ledger is unavailable would make usage
                # attribution and the global budget unverifiable.
                raise
            started = time.monotonic()
            provider_context = dict(request_context) if isinstance(request_context, Mapping) else {}
            provider_context.update(
                {
                    "global_attempt_budget": True,
                    "route_profile": profile_name,
                    "credential_alias": route.credential_alias,
                    "capacity_source_id": route.capacity_source_id,
                    "routing_policy_version": route.policy_version,
                    "input_classification": classification,
                    "request_attempt": self._budget.transmissions,
                    "fallback_attempt": index,
                }
            )
            if route_policy is not None:
                if route_policy.max_output_tokens is not None:
                    provider_context["max_output_tokens"] = int(route_policy.max_output_tokens)
                if route_policy.timeout_seconds is not None:
                    provider_context["timeout_seconds"] = float(route_policy.timeout_seconds)
                if route_policy.reasoning_effort:
                    provider_context["reasoning_effort"] = str(route_policy.reasoning_effort)
            try:
                # Resolve lazily inside the attempt so profile/provider
                # configuration failures are accounted for and can use the
                # configured Gemini fallback just like transport failures.
                client = self._runtime.resolve_profile_client(profile_name)
                # Count the application transmission only after reservation
                # and profile resolution. Provider adapters have retries
                # disabled; this is the only provider-attempt layer.
                self._budget.record_transmission()
                provider_context["request_attempt"] = self._budget.transmissions
                result = await client.generate_structured(
                    operation=operation,
                    instructions=instructions,
                    input_payload=input_payload,
                    output_model=output_model,
                    system_prompt=system_prompt,
                    model_profile=profile_name,
                    request_context=provider_context,
                    strict_schema=strict_schema,
                )
                if result_validator is not None:
                    parsed_output = getattr(result, "parsed_output", result)
                    if not isinstance(parsed_output, Mapping):
                        raise ModelOutputInvalidError(
                            "Model output did not contain a structured object."
                        )
                    try:
                        result_validator(dict(parsed_output))
                    except ProviderError:
                        raise
                    except Exception as exc:
                        # Agent validators may use their own exception type;
                        # expose one safe, retryable contract failure so the
                        # next configured provider can be tried before this
                        # result is marked successful or cached.
                        raise ModelOutputInvalidError() from exc
            except Exception as exc:
                last_error = exc
                if isinstance(exc, ProviderError):
                    exc.details.setdefault("provider_label", _provider_label(route.provider))
                    exc.details.setdefault("model", route.model)
                await self._usage.finish(
                    attempt_id,
                    route=route,
                    context=call_context,
                    error=exc,
                    elapsed_ms=(time.monotonic() - started) * 1000.0,
                )
                self._runtime.capacity_registry.mark_failure(
                    route.capacity_source_id,
                    cooldown_seconds=(
                        float(getattr(exc, "details", {}).get("retry_after_seconds", 0.0) or 0.0)
                        if isinstance(exc, ProviderError)
                        else 0.0
                    ),
                )
                if not self._can_recover(exc, index, names, route):
                    raise
                continue
            await self._usage.finish(
                attempt_id,
                route=route,
                context=call_context,
                result=result,
                elapsed_ms=(time.monotonic() - started) * 1000.0,
            )
            usage = dict(getattr(result, "usage", {}) or {})
            self._runtime.capacity_registry.mark_success(
                route.capacity_source_id,
                input_tokens=int(usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0),
            )
            self._decorate_result(result, route, index)
            return result
        if last_error is not None:
            raise last_error
        raise ProviderConfigError(
            f"No provider profile could be resolved for {self._engine}.{operation}."
        )

    def resolve_route_metadata(
        self, operation: str, request_context: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        route = self.route_for(operation, request_context=request_context)
        return {
            "profile_name": route.profile_name,
            "profile_fingerprint": route.profile_fingerprint,
            "provider": route.provider,
            "model": route.model,
            "credential_alias": route.credential_alias,
            "capacity_source_id": route.capacity_source_id,
            "policy_version": route.policy_version,
        }

    async def aclose(self) -> None:
        # Underlying adapters are owned and closed by ModelRuntime.
        return None

    def _build_budget(self) -> OperationBudget:
        normal = 1
        if self._engine == "content_architect":
            normal = 3
        route = self._runtime.router.operation_route(self._engine, "plan_content")
        recovery = int(route.recovery_allowance) if route is not None else 1
        return OperationBudget(
            normal_calls=normal,
            recovery_allowance=recovery,
            max_transmissions=normal + recovery,
        )

    def _classification(self, context: Any, payload_value: Any = None) -> str:
        if isinstance(context, Mapping):
            value = context.get("input_classification")
            if value:
                return str(value).strip().casefold()
        if payload_value:
            return str(payload_value).strip().casefold()
        return self._input_classification

    @staticmethod
    def _effective_input_policy(profile: Any, route_policy: Any) -> str:
        """Expose the route's effective packet policy in safe telemetry."""

        provider = str(getattr(profile, "provider", "") or "").casefold()
        if provider == "gemini" and getattr(route_policy, "allow_personal_gemini_fallback", False):
            return "any"
        return str(getattr(profile, "input_policy", "any") or "any")

    def _assert_policy_snapshot(self, request_context: Any) -> None:
        if not isinstance(request_context, Mapping):
            return
        snapshot = request_context.get("routing_policy_snapshot")
        if not isinstance(snapshot, Mapping):
            return
        expected = str(snapshot.get("fingerprint", "") or "")
        if not expected:
            return
        current = self._runtime.router.policy_snapshot()
        if expected != str(current.get("fingerprint", "") or ""):
            raise ModelRoutingPolicyChangedError()

    def _admit_normal(self) -> None:
        self._budget.admit_normal()

    def _ordered_names(
        self,
        names: tuple[str, ...],
        *,
        estimated_input_tokens: int = 0,
        input_classification: str | None = None,
    ) -> tuple[str, ...]:
        if len(names) <= 1:
            return names
        pairs: list[tuple[str, str]] = []
        for name in names:
            profile = self._runtime.config.get_profile(name)
            if profile is None:
                continue
            pairs.append((name, str(getattr(profile, "capacity_source_id", "") or name)))
        ordered = self._runtime.capacity_registry.order_profiles(
            pairs,
            estimated_input_tokens=estimated_input_tokens,
        )
        # Capacity ordering may choose among alternatives, but it must never
        # promote a fallback provider into the primary position.
        primary = names[0]
        ordered = [primary, *[name for name in ordered if name != primary]]
        return tuple(ordered or names)

    def _can_recover(
        self,
        error: BaseException,
        index: int,
        names: tuple[str, ...],
        route: ResolvedModelRoute,
    ) -> bool:
        if index >= len(names) - 1 or self._budget.recovery_remaining <= 0:
            return False
        if isinstance(error, ProviderError):
            next_profile = self._runtime.config.get_profile(names[index + 1])
            next_provider = str(getattr(next_profile, "provider", "") or "").casefold()
            if isinstance(error, (ProviderAuthError, ProviderConfigError, ProviderCreditError)):
                # Credential/configuration/quota failures from the primary
                # provider are recoverable only when the next configured
                # source is the explicit Gemini fallback.
                return route.provider.casefold() != "gemini" and next_provider == "gemini"
            return bool(error.retryable)
        return False

    @staticmethod
    def _decorate_result(result: Any, route: ResolvedModelRoute, fallback_attempt: int) -> None:
        telemetry = dict(getattr(result, "telemetry", {}) or {})
        telemetry.update(
            {
                "provider": route.provider,
                "model": route.model,
                "profile_name": route.profile_name,
                "profile_fingerprint": route.profile_fingerprint,
                "credential_alias": route.credential_alias,
                "capacity_source_id": route.capacity_source_id,
                "fallback_attempt": fallback_attempt,
                "routing_policy_version": route.policy_version,
            }
        )
        try:
            result.telemetry = telemetry
        except Exception:
            return


def _provider_label(provider: str) -> str:
    normalized = str(provider or "").casefold()
    if normalized == "gemini":
        return "Google Gemini"
    if normalized == "experiential":
        return "Experiential Labs"
    return "Configured model provider"
