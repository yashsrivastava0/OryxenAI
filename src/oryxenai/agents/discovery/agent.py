"""Discovery agent — transforms incomplete professional information into a
grounded structured profile and a user-reviewable portfolio strategy brief.

Supports both mock (fake client) and real (provider) model backends.

Attempt policy (Section 8): one initial model response plus at most one
completed-response recovery attempt (semantic repair). If the repaired
output is still semantically invalid, the agent returns ``status=failed``
with ``MODEL_SEMANTICALLY_INVALID`` — it never returns invalid output.
"""

from __future__ import annotations

import json
from typing import Any

from oryxenai.agents.discovery.ids import (
    answer_snapshot_hash,
)
from oryxenai.agents.discovery.preprocessing import compute_source_hash
from oryxenai.agents.discovery.prompt_builder import (
    build_instructions,
    build_repair_instructions,
)
from oryxenai.agents.discovery.schemas import (
    DiscoveryAnalysisResult,
    DiscoveryBrief,
    DiscoveryIntake,
    StructuredModelResult,
)
from oryxenai.agents.discovery.validators import (
    validate_call_a_result,
    validate_call_b_result,
)
from oryxenai.agents.shared.contracts import Agent, AgentContext, AgentKey, AgentResult, ModelClient
from oryxenai.core.logging import get_logger
from oryxenai.core.settings import get_settings

logger = get_logger("oryxenai.agents.discovery")

_FAILED_STATUS = "failed"
_MODEL_CALL_FAILED = "model_call_failed"
_MODEL_SEMANTICALLY_INVALID = "MODEL_SEMANTICALLY_INVALID"


class DiscoveryAgent(Agent):
    """Discovery agent that can use a real or fake ModelClient."""

    key = AgentKey.DISCOVERY

    def __init__(self, model_client: ModelClient | None = None) -> None:
        self._model_client = model_client
        self._config = get_settings().discovery

    async def run(self, context: AgentContext) -> AgentResult:
        operation = context.agent_input.get("operation", "prepare_questions")

        if operation == "prepare_questions":
            return await self._run_prepare_questions(context)
        if operation == "build_brief":
            return await self._run_build_brief(context)
        raise ValueError(f"Unknown Discovery operation: {operation}")

    async def _run_prepare_questions(self, context: AgentContext) -> AgentResult:
        intake_dict = context.agent_input.get("intake", {})
        intake = DiscoveryIntake(**intake_dict)
        source_texts = self._build_source_texts(intake)
        source_hash = compute_source_hash(json.dumps(source_texts, sort_keys=True))

        source_packet = {
            "main_prompt": intake.main_prompt or "",
            "resume_text": intake.resume_text or "",
            "resume_source": intake.resume_source.value,
            "links": [link.model_dump() for link in intake.links],
        }

        constraints = {
            "max_questions": min(
                self._config.max_questions, intake.product_constraints.max_questions
            ),
            "max_featured_projects": min(
                self._config.max_featured_projects,
                intake.product_constraints.max_featured_projects,
            ),
            "product_constraints": intake.product_constraints.model_dump(mode="json"),
        }

        system_prompt, task_prompt, version, manifest = build_instructions(
            operation="prepare_questions",
            source_packet=source_packet,
            config=constraints,
            output_language=intake.output_language,
        )

        model_client = self._model_client or _get_fake_client()

        result = await self._generate_or_failed(
            model_client,
            operation="prepare_questions",
            instructions=f"{system_prompt}\n\n{task_prompt}",
            input_payload=source_packet,
            output_model=DiscoveryAnalysisResult,
            version=version,
        )
        if isinstance(result, AgentResult):
            return result

        analysis = DiscoveryAnalysisResult(**result.parsed_output)

        validation = validate_call_a_result(analysis, source_texts, self._config)
        repaired = None
        if not validation.is_valid:
            logger.warning(
                "prepare_questions validation failed, attempting one repair: %s",
                validation.errors,
            )
            repaired = await self._attempt_repair(
                model_client,
                analysis.model_dump(),
                validation.errors,
                output_model=DiscoveryAnalysisResult,
                valid_source_ids=sorted(source_texts),
                valid_fact_ids=[],
                operation_name="prepare_questions",
                version=version,
            )
            if repaired is not None:
                analysis = DiscoveryAnalysisResult(**repaired.parsed_output)
                validation = validate_call_a_result(analysis, source_texts, self._config)
            if not validation.is_valid:
                return AgentResult(
                    output={
                        "operation": "prepare_questions",
                        "status": _FAILED_STATUS,
                        "error": {
                            "code": _MODEL_SEMANTICALLY_INVALID,
                            "message": "Discovery analysis failed semantic validation after repair.",
                            "errors": validation.errors,
                        },
                    },
                    prompt_version=version,
                    model_metadata={
                        "provider": result.model,
                        "model": result.model,
                        "response_id": result.response_id,
                        "usage": result.usage,
                        "latency_ms": result.latency_ms,
                        "finish_reason": result.finish_reason,
                        "repair_attempted": True,
                        "repair_succeeded": False,
                    },
                )

        return AgentResult(
            output={
                "operation": "prepare_questions",
                "summary": "Discovery analysis prepared.",
                "analysis": analysis.model_dump(),
                "source_hash": source_hash,
                "validation": {
                    "is_valid": validation.is_valid,
                    "errors": validation.errors,
                    "warnings": validation.warnings,
                    "repaired": repaired is not None,
                },
            },
            prompt_version=version,
            model_metadata={
                "provider": result.model,
                "model": result.model,
                "response_id": result.response_id,
                "usage": result.usage,
                "latency_ms": result.latency_ms,
                "finish_reason": result.finish_reason,
                "prompt_modules": manifest,
                "repair_attempted": repaired is not None,
                "repair_succeeded": repaired is not None,
            },
        )

    async def _run_build_brief(self, context: AgentContext) -> AgentResult:
        analysis_dict = context.agent_input.get("analysis", {})
        answers_dict = context.agent_input.get("answers", {})
        intake_dict = context.agent_input.get("intake", {})

        analysis = DiscoveryAnalysisResult(**analysis_dict)
        intake = DiscoveryIntake(**intake_dict)

        fact_ids = {f.local_key for f in analysis.facts}
        project_ids = {
            p.title
            for p in (analysis.normalized_profile.projects if analysis.normalized_profile else [])
            if p.title
        }

        source_packet = {
            "analysis": analysis.model_dump(),
            "answers": answers_dict,
            "output_language": intake.output_language,
        }

        system_prompt, task_prompt, version, manifest = build_instructions(
            operation="build_brief",
            source_packet=source_packet,
            output_language=intake.output_language,
        )

        model_client = self._model_client or _get_fake_client()

        result = await self._generate_or_failed(
            model_client,
            operation="build_brief",
            instructions=f"{system_prompt}\n\n{task_prompt}",
            input_payload=source_packet,
            output_model=DiscoveryBrief,
            version=version,
        )
        if isinstance(result, AgentResult):
            return result

        brief = DiscoveryBrief(**result.parsed_output)

        validation = validate_call_b_result(brief, fact_ids, project_ids, self._config)
        repaired = None
        if not validation.is_valid:
            logger.warning(
                "build_brief validation failed, attempting one repair: %s",
                validation.errors,
            )
            repaired = await self._attempt_repair(
                model_client,
                brief.model_dump(),
                validation.errors,
                output_model=DiscoveryBrief,
                valid_source_ids=[],
                valid_fact_ids=sorted(fact_ids),
                operation_name="build_brief",
                version=version,
            )
            if repaired is not None:
                brief = DiscoveryBrief(**repaired.parsed_output)
                validation = validate_call_b_result(brief, fact_ids, project_ids, self._config)
            if not validation.is_valid:
                return AgentResult(
                    output={
                        "operation": "build_brief",
                        "status": _FAILED_STATUS,
                        "error": {
                            "code": _MODEL_SEMANTICALLY_INVALID,
                            "message": "Discovery brief failed semantic validation after repair.",
                            "errors": validation.errors,
                        },
                    },
                    prompt_version=version,
                    model_metadata={
                        "provider": result.model,
                        "model": result.model,
                        "response_id": result.response_id,
                        "usage": result.usage,
                        "latency_ms": result.latency_ms,
                        "finish_reason": result.finish_reason,
                        "repair_attempted": True,
                        "repair_succeeded": False,
                    },
                )

        answer_hash = answer_snapshot_hash(answers_dict)

        return AgentResult(
            output={
                "operation": "build_brief",
                "brief": brief.model_dump(),
                "answer_hash": answer_hash,
                "validation": {
                    "is_valid": validation.is_valid,
                    "errors": validation.errors,
                    "warnings": validation.warnings,
                    "repaired": repaired is not None,
                },
            },
            prompt_version=version,
            model_metadata={
                "provider": result.model,
                "model": result.model,
                "response_id": result.response_id,
                "usage": result.usage,
                "latency_ms": result.latency_ms,
                "finish_reason": result.finish_reason,
                "prompt_modules": manifest,
                "repair_attempted": repaired is not None,
                "repair_succeeded": repaired is not None,
            },
        )

    async def _generate_or_failed(
        self,
        model_client: ModelClient,
        *,
        operation: str,
        instructions: str,
        input_payload: dict[str, Any],
        output_model: type[Any],
        version: str,
    ) -> AgentResult | StructuredModelResult:
        """Generate a structured result, mapping call failures to failed output."""
        try:
            from typing import cast

            return cast(
                StructuredModelResult,
                await model_client.generate_structured(
                    operation=operation,
                    instructions=instructions,
                    input_payload=input_payload,
                    output_model=output_model,
                ),
            )
        except Exception as exc:
            logger.warning(
                "discovery operation=%s model call failed: %s", operation, type(exc).__name__
            )
            return AgentResult(
                output={
                    "operation": operation,
                    "status": _FAILED_STATUS,
                    "error": {
                        "code": _MODEL_CALL_FAILED,
                        "message": "The Discovery model call failed.",
                    },
                },
                prompt_version=version,
                model_metadata={"provider": "discovery", "error": _MODEL_CALL_FAILED},
            )

    async def _attempt_repair(
        self,
        model_client: ModelClient,
        original_output: dict[str, Any],
        validation_errors: list[str],
        *,
        output_model: type[Any],
        valid_source_ids: list[str],
        valid_fact_ids: list[str],
        operation_name: str,
        version: str,
    ) -> StructuredModelResult | None:
        """One bounded semantic repair attempt (Section 24).

        The repair payload carries the exact validation errors, valid source
        and fact IDs, the current schema, and the operation name — never a
        vague "try again" instruction.
        """
        try:
            system_prompt, task_prompt, _version = build_repair_instructions(
                original_output,
                validation_errors,
                valid_source_ids=valid_source_ids,
                valid_fact_ids=valid_fact_ids,
                operation_name=operation_name,
            )
            from typing import cast

            return cast(
                StructuredModelResult,
                await model_client.generate_structured(
                    operation="repair",
                    instructions=f"{system_prompt}\n\n{task_prompt}",
                    input_payload={
                        "original_output": original_output,
                        "validation_errors": validation_errors,
                        "valid_source_ids": valid_source_ids,
                        "valid_fact_ids": valid_fact_ids,
                        "operation_name": operation_name,
                    },
                    output_model=output_model,
                ),
            )
        except Exception:
            logger.warning("Semantic repair attempt failed")
            return None

    def _build_source_texts(self, intake: DiscoveryIntake) -> dict[str, str]:
        source_texts: dict[str, str] = {}
        if intake.main_prompt:
            source_texts["main_prompt"] = intake.main_prompt
        if intake.resume_text:
            source_texts["resume_text"] = intake.resume_text
        return source_texts


def _get_fake_client() -> ModelClient:
    from oryxenai.agents.discovery.fake_client import FakeDiscoveryModelClient

    return FakeDiscoveryModelClient()
