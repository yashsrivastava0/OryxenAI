"""Provider-neutral model client infrastructure.

Reads provider profiles from config/models.toml. Builds concrete provider
adapters through the factory in providers/. Agent code depends on the
ModelClient protocol, never on a provider module.

When no real profile is configured (or no API key is set at startup),
`build_model_client()` returns a `MockModelClient`. This lets the application
start without any model credentials.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from oryxenai.agents.shared.contracts import ModelClient
from oryxenai.core.logging import get_logger

if TYPE_CHECKING:
    from oryxenai.core.settings import ModelConfig, ModelProfile

logger = get_logger("oryxenai.agents.model_client")


class MockModelClient:
    """A no-network ModelClient that returns a fixed placeholder.

    Used as fallback when no provider is configured or no API key is set.
    The application can start and pass contract tests without credentials.
    """

    async def complete(
        self,
        system_prompt: str,
        task_prompt: str,
        request_params: dict[str, Any] | None = None,
    ) -> str:
        return "[mock-model-output]"

    async def generate_structured(
        self,
        *,
        operation: str,
        instructions: str,
        input_payload: Mapping[str, object],
        output_model: type[BaseModel],
        model_profile: Any = None,
        request_context: Any = None,
    ) -> Any:
        return _mock_structured_result(output_model)


def _mock_structured_result(output_model: type[BaseModel]) -> Any:
    """Build a deterministic StructuredModelResult for the given output model.

    Discovery output models get a valid minimal envelope so the mock-runs
    dev harness can execute the Discovery agent without network access.
    Any other model falls back to an empty instance.
    """
    from oryxenai.agents.discovery.schemas import (
        BriefOutput,
        DiscoveryQuestion,
        OperationMode,
        QuestionKind,
        QuestionOption,
        QuestionSetOutput,
        StructuredModelResult,
    )

    parsed: BaseModel | None
    if output_model is QuestionSetOutput:
        parsed = QuestionSetOutput(
            mode=OperationMode.ASK_QUESTIONS,
            assistant_message="I have enough to ask a few focused questions.",
            questions=[
                DiscoveryQuestion(
                    id="target_direction",
                    text="Should the portfolio lead with backend or full-stack?",
                    kind=QuestionKind.SINGLE_SELECT,
                    options=[
                        QuestionOption(id="backend", label="Backend"),
                        QuestionOption(id="fullstack", label="Full-stack"),
                        QuestionOption(id="balanced", label="Balanced"),
                    ],
                )
            ],
            memory_update={"intent_summary": "Backend engineering roles", "open_items": []},
        )
    elif output_model is BriefOutput:
        parsed = BriefOutput(
            mode=OperationMode.BRIEF_READY,
            assistant_message="I prepared the Discovery brief. Review it and change anything before approving.",
            brief_title="Portfolio Discovery Brief — Mock User",
            brief_markdown=(
                "# Portfolio Discovery Brief — Mock User\n\n"
                "## Portfolio direction at a glance\n\n"
                "**Primary goal:** Create a portfolio that helps the user move forward.\n\n"
                "## Approval summary\n\n"
                "Ready for approval."
            ),
            open_items=["no metrics supplied"],
            memory_update={},
        )
    else:
        try:
            parsed = output_model()
        except Exception:
            parsed = None

    if parsed is None:
        parsed_output: dict[str, Any] = {}
    elif isinstance(parsed, StructuredModelResult):
        return parsed
    elif isinstance(parsed, BaseModel):
        parsed_output = parsed.model_dump(mode="json")
    else:
        parsed_output = dict(parsed)

    return StructuredModelResult(
        parsed_output=parsed_output,
        response_id="mock-response-id",
        model="mock-model",
        usage={"prompt_tokens": 10, "completion_tokens": 20},
        finish_reason="stop",
        latency_ms=1.0,
    )


def resolve_api_key(profile: ModelProfile) -> str | None:
    """Resolve a profile's API key indirectly via its api_key_env name."""
    import os

    if not profile.api_key_env:
        return None
    return os.environ.get(profile.api_key_env)


def build_model_client(model_config: ModelConfig) -> ModelClient:
    """Build a ModelClient for the given config.

    Returns a real provider adapter when a profile is configured and the
    required API key environment variable is set. Falls back to
    MockModelClient otherwise — the application starts without credentials.
    """
    from oryxenai.agents.shared.providers.factory import build_adapter, can_build

    profile = model_config.get_profile("default")
    if profile is not None and profile.provider and can_build(profile):
        key = resolve_api_key(profile)
        if key:
            logger.info(
                "building real model client for provider=%s model=%s",
                profile.provider,
                profile.model or "(default)",
            )
            return build_adapter(profile)
        logger.info(
            "provider '%s' configured but API key env var '%s' is not set — using mock client",
            profile.provider,
            profile.api_key_env,
        )
        return MockModelClient()

    if profile is not None:
        logger.info(
            "model profile 'default' provider='%s' not recognised — using mock client",
            profile.provider,
        )
    return MockModelClient()


def build_provider_client(profile_name: str, model_config: ModelConfig) -> ModelClient | None:
    """Build a provider adapter for a named profile, or None if not possible.

    Returns None when the profile is missing, unrecognised, or has no API key.
    Callers should fall back to MockModelClient or choose a different profile.
    """
    from oryxenai.agents.shared.providers.factory import build_adapter, can_build

    profile = model_config.get_profile(profile_name)
    if profile is None:
        logger.warning("profile '%s' not found in config/models.toml", profile_name)
        return None

    if not profile.provider or not can_build(profile):
        logger.warning(
            "profile '%s' provider '%s' is not supported", profile_name, profile.provider
        )
        return None

    key = resolve_api_key(profile)
    if not key:
        logger.warning(
            "profile '%s' API key env var '%s' is not set",
            profile_name,
            profile.api_key_env,
        )
        return None

    logger.info("building %s adapter for profile '%s'", profile.provider, profile_name)
    return build_adapter(profile)
