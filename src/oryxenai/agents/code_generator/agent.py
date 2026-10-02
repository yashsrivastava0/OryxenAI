"""Code Generator agent: the model-backed operations of the page pipeline.

``generate_page`` is one straight call: the approved content plus the host's
derived values go in, the page body comes out. There is deliberately no result
cache, no automatic retry and no repair call: whatever the model returns is
validated by the host, and a failure is reported exactly (see ``diagnostics``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from oryxenai.agents.code_generator.diagnostics import failure_from_provider_error
from oryxenai.agents.code_generator.prompt_builder import (
    build_instructions,
    get_prompt_version,
)
from oryxenai.agents.code_generator.schemas import (
    ChangePlanEnvelope,
    CodeGeneratorFailure,
    GeneratedPageEnvelope,
)
from oryxenai.agents.shared.contracts import Agent, AgentContext, AgentKey, AgentResult, ModelClient
from oryxenai.agents.shared.model_cache import prompt_cache_context
from oryxenai.agents.shared.providers.errors import ModelOutputInvalidError
from oryxenai.themes import DEFAULT_THEME_ID, ThemePackage, get_theme


@dataclass(frozen=True, slots=True)
class ModelCallInfo:
    """Non-secret facts about one model call, for the version trace."""

    operation: str
    prompt_version: str
    provider: str = ""
    model: str = ""
    response_id: str = ""
    finish_reason: str = ""
    latency_ms: float = 0.0
    usage: dict[str, Any] = field(default_factory=dict)
    manifest: dict[str, str] = field(default_factory=dict)
    telemetry: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "prompt_version": self.prompt_version,
            "provider": self.provider,
            "model": self.model,
            "response_id": self.response_id,
            "finish_reason": self.finish_reason,
            "latency_ms": round(self.latency_ms, 1),
            "usage": {k: v for k, v in self.usage.items() if isinstance(v, (int, float))},
            "prompt_modules": self.manifest,
            "telemetry": self.telemetry,
        }


@dataclass(frozen=True, slots=True)
class InterpretedChange:
    plan: ChangePlanEnvelope
    call: ModelCallInfo


@dataclass(frozen=True, slots=True)
class GeneratedPage:
    lang: str
    body_html: str
    call: ModelCallInfo


def _call_info(
    result: Any, operation: str, version: str, manifest: dict[str, str]
) -> ModelCallInfo:
    telemetry = getattr(result, "telemetry", {}) or {}
    return ModelCallInfo(
        operation=operation,
        prompt_version=version,
        provider=str(telemetry.get("provider", "") or ""),
        model=str(getattr(result, "model", "") or ""),
        response_id=str(getattr(result, "response_id", "") or ""),
        finish_reason=str(getattr(result, "finish_reason", "") or ""),
        latency_ms=float(getattr(result, "latency_ms", 0.0) or 0.0),
        usage=dict(getattr(result, "usage", {}) or {}),
        manifest=manifest,
        telemetry=dict(telemetry),
    )


class CodeGeneratorAgent(Agent):
    """Model-backed Code Generator operations behind an injected ModelClient."""

    key = AgentKey.CODE_GENERATOR

    def __init__(
        self,
        model_client: ModelClient,
        *,
        theme_id: str = DEFAULT_THEME_ID,
        profile_name: str = "",
    ) -> None:
        if model_client is None:
            raise ValueError("CodeGeneratorAgent requires a model client")
        self._client = model_client
        self._theme: ThemePackage = get_theme(theme_id)
        self._profile_name = profile_name

    @property
    def theme(self) -> ThemePackage:
        return self._theme

    async def run(self, context: AgentContext) -> AgentResult:
        """Protocol entry point: ``operation == "generate_page"`` with ``page_content``."""
        operation = context.agent_input.get("operation", "generate_page")
        if operation != "generate_page":
            raise ValueError(f"Unknown Code Generator operation: {operation}")
        content = dict(context.agent_input.get("page_content", {}) or {})
        derived = self._theme.contract.derive(content)
        page = await self.generate_page(content, derived, context)
        return AgentResult(
            output={"lang": page.lang, "body_chars": len(page.body_html)},
            prompt_version=page.call.prompt_version,
            model_metadata={"call": page.call.to_dict()},
        )

    async def generate_page(
        self,
        page_content: Mapping[str, Any],
        derived: Mapping[str, Any],
        context: AgentContext,
    ) -> GeneratedPage:
        """One model call that writes the page body. Provider errors propagate unchanged."""
        bundle = build_instructions("generate_page", self._theme)
        packet = {
            "content": dict(page_content),
            "derived": dict(derived),
            "theme": {"id": self._theme.theme_id},
        }
        request_context = prompt_cache_context(
            "code_generator", "generate_page", bundle.manifest, context
        )
        # Streamed so a long generation is never cut by an idle gateway timeout.
        request_context["stream"] = True
        result = await self._client.generate_structured(
            operation="generate_page",
            system_prompt=bundle.system_prompt,
            instructions=bundle.task,
            input_payload=packet,
            output_model=GeneratedPageEnvelope,
            model_profile=self._profile_name,
            request_context=request_context,
            strict_schema=False,
        )
        call = _call_info(
            result, "generate_page", get_prompt_version("generate_page"), bundle.manifest
        )
        parsed = getattr(result, "parsed_output", None)
        try:
            envelope = GeneratedPageEnvelope.model_validate(parsed)
            if not envelope.body_html.strip():
                raise ValueError("body_html is empty")
        except (ValidationError, ValueError) as exc:
            failure = failure_from_provider_error(ModelOutputInvalidError(), stage="generate")
            failure.cause = (
                "The reply was valid JSON but did not contain a non-empty 'body_html' string "
                f"({type(exc).__name__})."
            )
            raise CodeGeneratorFailure(failure) from exc
        return GeneratedPage(
            lang=envelope.lang.strip() or "en", body_html=envelope.body_html, call=call
        )

    async def interpret_change(
        self,
        page_content: Mapping[str, Any],
        instruction: str,
        history: Sequence[Mapping[str, str]],
        context: AgentContext,
    ) -> InterpretedChange:
        """One small model call: what (if anything) does this chat message change?"""
        bundle = build_instructions("interpret_change", self._theme)
        packet = {
            "content": dict(page_content),
            "user_request": instruction,
            "recent_conversation": [dict(item) for item in history],
        }
        request_context = prompt_cache_context(
            "code_generator", "interpret_change", bundle.manifest, context
        )
        result = await self._client.generate_structured(
            operation="interpret_change",
            system_prompt=bundle.system_prompt,
            instructions=bundle.task,
            input_payload=packet,
            output_model=ChangePlanEnvelope,
            model_profile=self._profile_name,
            request_context=request_context,
            strict_schema=False,
        )
        call = _call_info(
            result, "interpret_change", get_prompt_version("interpret_change"), bundle.manifest
        )
        try:
            plan = ChangePlanEnvelope.model_validate(getattr(result, "parsed_output", None))
        except ValidationError as exc:
            failure = failure_from_provider_error(ModelOutputInvalidError(), stage="interpret")
            failure.cause = (
                "The reply was valid JSON but not a valid change plan "
                f"({len(exc.errors())} field problem{'s' if len(exc.errors()) != 1 else ''})."
            )
            raise CodeGeneratorFailure(failure) from exc
        return InterpretedChange(plan=plan, call=call)
