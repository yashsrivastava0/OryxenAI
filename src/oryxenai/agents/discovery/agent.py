"""Discovery agent — transforms incomplete professional information into a
grounded structured profile and a user-reviewable portfolio strategy brief.

Supports both mock (fake client) and real (provider) model backends.
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

        system_prompt, task_prompt, version = build_instructions(
            operation="prepare_questions",
            source_packet=source_packet,
            config=constraints,
            output_language=intake.output_language,
        )

        model_client = self._model_client or _get_fake_client()

        try:
            result: StructuredModelResult = await model_client.generate_structured(
                operation="prepare_questions",
                instructions=f"{system_prompt}\n\n{task_prompt}",
                input_payload=source_packet,
                output_model=DiscoveryAnalysisResult,
            )
        except Exception:
            return AgentResult(
                output={
                    "operation": "prepare_questions",
                    "status": "failed",
                },
                prompt_version=version,
                model_metadata={"provider": "discovery", "error": "model_call_failed"},
            )

        analysis = DiscoveryAnalysisResult(**result.parsed_output)

        validation = validate_call_a_result(analysis, source_texts, self._config)
        if not validation.is_valid:
            logger.warning(
                "validation failed for prepare_questions: %s",
                validation.errors,
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
                },
            },
            prompt_version=version,
            model_metadata={
                "provider": result.model,
                "model": result.model,
                "response_id": result.response_id,
                "usage": result.usage,
                "latency_ms": result.latency_ms,
            },
        )

    async def _run_build_brief(self, context: AgentContext) -> AgentResult:
        analysis_dict = context.agent_input.get("analysis", {})
        answers_dict = context.agent_input.get("answers", {})
        intake_dict = context.agent_input.get("intake", {})

        analysis = DiscoveryAnalysisResult(**analysis_dict)
        intake = DiscoveryIntake(**intake_dict)

        fact_ids = {f.local_key for f in analysis.fact_candidates}
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

        system_prompt, task_prompt, version = build_instructions(
            operation="build_brief",
            source_packet=source_packet,
            output_language=intake.output_language,
        )

        model_client = self._model_client or _get_fake_client()

        try:
            result: StructuredModelResult = await model_client.generate_structured(
                operation="build_brief",
                instructions=f"{system_prompt}\n\n{task_prompt}",
                input_payload=source_packet,
                output_model=DiscoveryBrief,
            )
        except Exception:
            return AgentResult(
                output={
                    "operation": "build_brief",
                    "status": "failed",
                },
                prompt_version=version,
                model_metadata={"provider": "discovery", "error": "model_call_failed"},
            )

        brief = DiscoveryBrief(**result.parsed_output)

        validation = validate_call_b_result(brief, fact_ids, project_ids, self._config)
        repaired = None
        if not validation.is_valid:
            repaired = await self._attempt_repair(
                model_client,
                brief.model_dump(),
                validation.errors,
            )
            if repaired is not None:
                brief = DiscoveryBrief(**repaired.parsed_output)
                validation = validate_call_b_result(brief, fact_ids, project_ids, self._config)

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
            },
        )

    async def _attempt_repair(
        self,
        model_client: ModelClient,
        original_output: dict[str, Any],
        validation_errors: list[str],
    ) -> StructuredModelResult | None:
        try:
            system_prompt, task_prompt, _version = build_repair_instructions(
                original_output, validation_errors
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
                    },
                    output_model=DiscoveryBrief,
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
