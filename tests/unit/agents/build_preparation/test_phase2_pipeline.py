from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from oryxenai.agents.build_preparation.agent import BuildPreparationAgent
from oryxenai.agents.build_preparation.schemas import (
    BuildContextDraft,
    RouteBuildContext,
    Stage1QueryPlan,
    Stage2SelectionPlan,
    Stage3BuildContextResult,
    Stage4IntegratedContextResult,
)
from oryxenai.agents.discovery.schemas import StructuredModelResult
from oryxenai.agents.shared.context import build_context
from oryxenai.agents.shared.contracts import AgentKey
from oryxenai.core.settings import Settings


def _visual() -> dict[str, object]:
    return {
        "pages": [
            {"route_id": "home", "path": "/", "publication_status": "approved", "scenes": []}
        ],
        "asset_briefs": [],
        "resource_candidates": [],
    }


def _context() -> BuildContextDraft:
    return BuildContextDraft(
        overview_markdown="# Build context",
        routes=[RouteBuildContext(route_id="home", path="/", brief_markdown="# Home")],
    )


def _output_dir() -> Path:
    path = Path("output") / "test-build-preparation" / str(uuid4())
    path.mkdir(parents=True)
    return path


class _Phase2Model:
    def __init__(self) -> None:
        self.operations: list[str] = []

    async def complete(self, system_prompt: str, task_prompt: str, request_params=None) -> str:
        return ""

    async def generate_structured(self, *, operation, output_model, **kwargs):
        self.operations.append(operation)
        if output_model is Stage1QueryPlan:
            parsed = Stage1QueryPlan()
        elif output_model is Stage2SelectionPlan:
            parsed = Stage2SelectionPlan()
        elif output_model is Stage3BuildContextResult:
            parsed = Stage3BuildContextResult(context=_context())
        elif output_model is Stage4IntegratedContextResult:
            parsed = Stage4IntegratedContextResult(context=_context())
        else:
            raise AssertionError(output_model)
        return StructuredModelResult(
            parsed_output=parsed.model_dump(mode="json"),
            response_id="phase2-test",
            model="test-model",
            usage={},
            finish_reason="stop",
            latency_ms=1.0,
        )


class _NoisyContextModel(_Phase2Model):
    async def generate_structured(self, *, operation, output_model, **kwargs):
        self.operations.append(operation)
        if output_model is Stage3BuildContextResult:
            parsed = Stage3BuildContextResult(
                context=BuildContextDraft(
                    overview_markdown="# Build context",
                    routes=[
                        RouteBuildContext(route_id="invented", brief_markdown="# Invented"),
                        RouteBuildContext(
                            route_id="home",
                            path="/wrong-path",
                            brief_markdown="",
                            resource_ids=["provider-id-that-was-not-selected"],
                        ),
                    ],
                )
            )
            return StructuredModelResult(
                parsed_output=parsed.model_dump(mode="json"),
                response_id="noisy-context-test",
                model="test-model",
                usage={},
                finish_reason="stop",
                latency_ms=1.0,
            )
        return await super().generate_structured(
            operation=operation, output_model=output_model, **kwargs
        )


@pytest.mark.asyncio
async def test_offline_phase2_runs_all_deterministic_stages_and_materializes() -> None:
    output_dir = _output_dir()
    try:
        settings = Settings()
        settings.build_preparation.fixture_output_dir = str(output_dir)
        settings.build_preparation.integration_route_threshold = 1
        context = build_context(
            portfolio_session_id=uuid4(),
            agent_key=AgentKey.BUILD_PREPARATION,
            current_state={},
            agent_input={
                "operation": "build",
                "visual_design_director": _visual(),
                "live_model": False,
                "live_providers": False,
                "output_dir": str(output_dir),
                "integration_route_threshold": 1,
            },
        )

        result = await BuildPreparationAgent(
            live_model=False, live_providers=False, settings=settings
        ).run(context)

        assert result.output["stage"] == "phase_3"
        assert result.output["model_calls"] == 0
        assert result.output["events"][-1]["event_id"] == "phase_3_complete"
        assert result.output["materialization"]["files"]
        assert result.output["package"]["archive_sha256"]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_live_model_path_is_bounded_to_four_calls_when_integration_is_needed() -> None:
    output_dir = _output_dir()
    try:
        settings = Settings()
        settings.build_preparation.fixture_output_dir = str(output_dir)
        settings.build_preparation.integration_route_threshold = 1
        model = _Phase2Model()
        context = build_context(
            portfolio_session_id=uuid4(),
            agent_key=AgentKey.BUILD_PREPARATION,
            current_state={},
            agent_input={
                "operation": "build",
                "visual_design_director": _visual(),
                "live_model": True,
                "live_providers": False,
                "output_dir": str(output_dir),
                "integration_route_threshold": 1,
            },
        )

        result = await BuildPreparationAgent(
            model_client=model, live_model=True, live_providers=False, settings=settings
        ).run(context)

        assert result.output["model_calls"] == 4
        assert model.operations == [
            "compose_resource_queries",
            "select_resources",
            "write_build_context",
            "integrate_cross_route",
        ]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_live_context_output_is_reconciled_to_approved_route_and_resource_sets() -> None:
    output_dir = _output_dir()
    try:
        settings = Settings()
        settings.build_preparation.fixture_output_dir = str(output_dir)
        settings.build_preparation.integration_route_threshold = 99
        model = _NoisyContextModel()
        context = build_context(
            portfolio_session_id=uuid4(),
            agent_key=AgentKey.BUILD_PREPARATION,
            current_state={},
            agent_input={
                "operation": "build",
                "visual_design_director": _visual(),
                "live_model": True,
                "live_providers": False,
                "output_dir": str(output_dir),
                "integration_route_threshold": 99,
            },
        )

        result = await BuildPreparationAgent(
            model_client=model, live_model=True, live_providers=False, settings=settings
        ).run(context)

        routes = result.output["build_context"]["routes"]
        assert [route["route_id"] for route in routes] == ["home"]
        assert routes[0]["path"] == "/"
        assert routes[0]["resource_ids"] == []
        assert "stage_3_context_reconciled" in {
            event["event_id"] for event in result.output["events"]
        }
        assert any("unknown model route" in warning for warning in result.output["warnings"])
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
