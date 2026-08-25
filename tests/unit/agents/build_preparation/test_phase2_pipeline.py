from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from oryxenai.agents.build_preparation.agent import (
    BuildPreparationAgent,
    _normalize_context_payload,
)
from oryxenai.agents.build_preparation.checkpoint import BuildPreparationCheckpoint
from oryxenai.agents.build_preparation.fixture import _offline_candidates
from oryxenai.agents.build_preparation.schemas import (
    BuildContextDraft,
    FetchedResource,
    ResourceQuery,
    ResourceSelection,
    RouteBuildContext,
    Stage1QueryPlan,
    Stage2SelectionPlan,
    Stage3BuildContextResult,
    Stage4IntegratedContextResult,
    Stage5HandoffReview,
)
from oryxenai.agents.discovery.schemas import StructuredModelResult
from oryxenai.agents.shared.context import build_context
from oryxenai.agents.shared.contracts import AgentKey
from oryxenai.core.settings import Settings


def _visual() -> dict[str, object]:
    return {
        "approved": {"visual_direction_hash": "visual-hash"},
        "source_ref": {"content_architect_content_hash": "content-hash"},
        "pages": [
            {"route_id": "home", "path": "/", "publication_status": "approved", "scenes": []}
        ],
        "asset_briefs": [],
        "resource_candidates": [],
    }


def _content() -> dict[str, object]:
    return {"page_content_packs": [{"route_id": "home", "sections": [{"section_id": "hero"}]}]}


def _context() -> BuildContextDraft:
    return BuildContextDraft(
        overview_markdown="# Build context",
        routes=[RouteBuildContext(route_id="home", path="/", brief_markdown="# Home")],
    )


def _output_dir() -> Path:
    path = Path("output") / "test-build-preparation" / str(uuid4())
    path.mkdir(parents=True)
    return path


def test_normalize_context_payload_drops_well_typed_top_level_context_duplicates() -> None:
    normalized, warnings = _normalize_context_payload(
        {
            "stage": "stage_3",
            "routes": [{"route_id": "home"}],
            "resource_ids": [],
            "acceptance_criteria": ["Keep approved content reachable."],
            "free_to_change": ["Visual composition."],
        },
        {"home"},
    )

    assert normalized == {"stage": "stage_3"}
    assert warnings == [
        "Dropped closed-set duplicate top-level context fields: routes, resource_ids, acceptance_criteria, free_to_change."
    ]


def test_normalize_context_payload_recovers_misplaced_luna_context_fields() -> None:
    normalized, warnings = _normalize_context_payload(
        {
            "stage": "stage_3",
            "status": "ready",
            "context": {
                "overview_markdown": "# Build context",
                "routes": [
                    {
                        "route_id": "home",
                        "brief_markdown": "# Home",
                        "runtime_requirements": {"approved_route_ids": ["home"]},
                        "fixed_facts": ["Use approved copy."],
                        "freedoms": ["Choose the composition."],
                    },
                    "runtime_requirements",
                    "fixed_facts",
                    "freedoms",
                ],
            },
        },
        {"home"},
    )

    validated = Stage3BuildContextResult.model_validate(normalized)
    assert validated.context.routes[0].route_id == "home"
    assert validated.context.runtime_requirements == {"approved_route_ids": ["home"]}
    assert validated.context.fixed_facts == ["Use approved copy."]
    assert validated.context.freedoms == ["Choose the composition."]
    assert any("misplaced nested context fields" in warning for warning in warnings)


class _Phase2Model:
    def __init__(self) -> None:
        self.operations: list[str] = []

    async def complete(self, system_prompt: str, task_prompt: str, request_params=None) -> str:
        return ""

    async def generate_structured(self, *, operation, output_model, **kwargs):
        self.operations.append(operation)
        if output_model is Stage1QueryPlan:
            parsed = Stage1QueryPlan(
                queries=[
                    ResourceQuery(
                        need_id=need["need_id"],
                        kind=(
                            "component"
                            if need.get("category")
                            in {"component", "visual_component", "registry_component"}
                            else "photo"
                            if need.get("required_for_handoff")
                            else "custom"
                        ),
                        query="abstract technology editorial",
                        orientation="landscape",
                        fallback=need.get("fallback", ""),
                    )
                    for need in kwargs["input_payload"]["resource_needs"]
                ]
            )
        elif output_model is Stage2SelectionPlan:
            candidates = kwargs["input_payload"]["candidate_resources"]
            parsed = Stage2SelectionPlan(
                selections=[
                    ResourceSelection(
                        need_id=need["need_id"],
                        selected_resource_id=next(
                            (
                                candidate["resource_id"]
                                for candidate in candidates
                                if candidate["need_id"] == need["need_id"]
                            ),
                            None,
                        ),
                        fallback=need.get("fallback", ""),
                    )
                    for need in kwargs["input_payload"]["resource_needs"]
                ]
            )
        elif output_model is Stage3BuildContextResult:
            parsed = Stage3BuildContextResult(context=_context())
        elif output_model is Stage4IntegratedContextResult:
            parsed = Stage4IntegratedContextResult(context=_context())
        elif output_model is Stage5HandoffReview:
            parsed = Stage5HandoffReview(summary="Structured handoff review complete.")
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


class _DuplicateTopLevelRouteModel(_Phase2Model):
    async def generate_structured(self, *, operation, output_model, **kwargs):
        result = await super().generate_structured(
            operation=operation, output_model=output_model, **kwargs
        )
        if output_model is Stage3BuildContextResult:
            payload = dict(result.parsed_output)
            payload["routes"] = [
                {
                    "route_id": "home",
                    "path": "/model-path-must-be-ignored",
                    "brief_markdown": "Model duplicate is not authoritative.",
                }
            ]
            return result.model_copy(update={"parsed_output": payload})
        return result


class _RouteFallbackNoteModel(_Phase2Model):
    async def generate_structured(self, *, operation, output_model, **kwargs):
        result = await super().generate_structured(
            operation=operation, output_model=output_model, **kwargs
        )
        if output_model is Stage3BuildContextResult:
            payload = dict(result.parsed_output)
            payload["context"]["routes"][0]["data_fallback_note"] = (
                "Use the approved custom data fallback for this route."
            )
            payload["context"]["routes"][0]["warnings"] = [
                "Selected resource IDs are authoritative for this route."
            ]
            return result.model_copy(update={"parsed_output": payload})
        return result


class _FailingHandoffModel(_Phase2Model):
    async def generate_structured(self, *, operation, output_model, **kwargs):
        if output_model is Stage5HandoffReview:
            raise RuntimeError("provider rejected the advisory handoff review")
        return await super().generate_structured(
            operation=operation, output_model=output_model, **kwargs
        )


class _FallbackLookup:
    calls_made = 1
    cache_hits = 0
    rate_limit_events = 0

    def __init__(self) -> None:
        self.provider_receipts: list[dict[str, object]] = []
        self.fetch_attempts: list[str] = []

    async def lookup(self, queries):
        need_id = queries[0].need_id
        return [
            FetchedResource(
                resource_id="component-primary",
                need_id=need_id,
                kind="component",
                provider="shadcn",
                provider_asset_id="accordion",
                title="Accordion",
                description="Accordion disclosure groups",
                dependencies=["react"],
                license="MIT",
                license_reference="https://example.test/license",
                retrieval_metadata={"provider_terms": ["accordion", "disclosure"]},
            ),
            FetchedResource(
                resource_id="component-alternate",
                need_id=need_id,
                kind="component",
                provider="magicui",
                provider_asset_id="disclosure",
                title="Disclosure",
                description="Collapsible disclosure groups",
                dependencies=["react"],
                license="MIT",
                license_reference="https://example.test/license",
                retrieval_metadata={"provider_terms": ["collapsible", "disclosure"]},
            ),
        ]

    async def fetch_component(self, candidate):
        self.fetch_attempts.append(candidate.resource_id)
        if candidate.resource_id == "component-primary":
            raise RuntimeError("selected source returned an empty registry item")
        return candidate.model_copy(
            update={
                "source_files": {
                    "disclosure.tsx": (
                        "import React from 'react';\n"
                        "export function Disclosure() { return <div aria-expanded={false} className='disclosure' data-state='closed'><button type='button'>Open approved capability groups</button><span>Accessible disclosure content</span></div>; }\n"
                    )
                }
            }
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
                "content_architect": _content(),
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
        assert result.output["materialization"]["analysis_path"] == "handoff-analysis.json"
        assert result.output["materialization"]["analysis_hash"]
        assert (
            Path(result.output["materialization"]["root_path"]) / "handoff-analysis.json"
        ).is_file()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_live_component_source_failure_tries_closed_set_alternate() -> None:
    output_dir = _output_dir()
    try:
        settings = Settings()
        settings.build_preparation.fixture_output_dir = str(output_dir)
        visual = _visual()
        visual["pages"][0]["scenes"] = [
            {"scene_id": "capabilities", "resource_candidates": ["capability-role"]}
        ]
        visual["pages"][0]["resource_candidates"] = ["capability-role"]
        visual["resource_candidates"] = [
            {
                "resource_id": "capability-role",
                "category": "component",
                "required_for_handoff": True,
                "possible_use": "Accordion disclosure for grouped capabilities",
                "interaction_role": "capability-grouping",
                "provider_terms": ["accordion", "disclosure", "collapsible"],
                "fallback": "Use the approved grouped list without registry source.",
            }
        ]
        model = _Phase2Model()
        lookup = _FallbackLookup()
        context = build_context(
            portfolio_session_id=uuid4(),
            agent_key=AgentKey.BUILD_PREPARATION,
            current_state={},
            agent_input={
                "operation": "build",
                "visual_design_director": visual,
                "content_architect": _content(),
                "live_model": True,
                "live_providers": True,
                "output_dir": str(output_dir),
                "integration_route_threshold": 99,
            },
        )

        result = await BuildPreparationAgent(
            model_client=model,
            provider_lookup=lookup,
            live_model=True,
            live_providers=True,
            settings=settings,
        ).run(context)

        selection = result.output["selection_plan"]["selections"][0]
        assert lookup.fetch_attempts == ["component-primary", "component-alternate"]
        assert selection["selected_resource_id"] == "component-alternate"
        assert result.output["handoff_report"]["handoff_eligible"] is True
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_offline_fixture_never_fabricates_visual_candidates() -> None:
    queries = [
        ResourceQuery(need_id="image", kind="photo", query="editorial image"),
        ResourceQuery(need_id="component", kind="component", query="interactive component"),
    ]

    assert _offline_candidates(queries) == []


@pytest.mark.asyncio
async def test_live_model_path_uses_structured_handoff_review_when_integration_is_needed() -> None:
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
                "content_architect": _content(),
                "live_model": True,
                "live_providers": False,
                "output_dir": str(output_dir),
                "integration_route_threshold": 1,
            },
        )

        result = await BuildPreparationAgent(
            model_client=model, live_model=True, live_providers=False, settings=settings
        ).run(context)

        assert result.output["model_calls"] == 5
        assert model.operations == [
            "compose_resource_queries",
            "select_resources",
            "write_build_context",
            "integrate_cross_route",
            "review_handoff_quality",
        ]
        assert result.output["handoff_report"]["handoff_eligible"] is True
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_retry_resumes_validated_model_stages_but_rebuilds_package() -> None:
    output_dir = _output_dir()
    checkpoints: list[BuildPreparationCheckpoint] = []

    async def save_checkpoint(checkpoint: BuildPreparationCheckpoint) -> None:
        checkpoints.append(checkpoint)

    try:
        settings = Settings()
        settings.build_preparation.fixture_output_dir = str(output_dir)
        settings.build_preparation.integration_route_threshold = 1
        run_id = str(uuid4())
        base_input = {
            "operation": "build",
            "visual_design_director": _visual(),
            "content_architect": _content(),
            "live_model": True,
            "live_providers": False,
            "output_dir": str(output_dir),
            "integration_route_threshold": 1,
            "checkpoint_binding": {
                "run_id": run_id,
                "approved_source_hash": "source-hash",
                "profile_fingerprint": "profile-fingerprint",
            },
        }
        first_model = _Phase2Model()
        first = await BuildPreparationAgent(
            model_client=first_model,
            live_model=True,
            live_providers=False,
            settings=settings,
            checkpoint_sink=save_checkpoint,
        ).run(
            build_context(
                portfolio_session_id=uuid4(),
                agent_key=AgentKey.BUILD_PREPARATION,
                current_state={},
                agent_input=base_input,
                run_id=uuid4(),
            )
        )

        checkpoint = checkpoints[-1]
        assert checkpoint.completed_stage == "stage_4"
        assert first_model.operations[:4] == [
            "compose_resource_queries",
            "select_resources",
            "write_build_context",
            "integrate_cross_route",
        ]
        assert "package" not in checkpoint.data
        assert "materialization" not in checkpoint.data

        second_model = _Phase2Model()
        second = await BuildPreparationAgent(
            model_client=second_model,
            live_model=True,
            live_providers=False,
            settings=settings,
        ).run(
            build_context(
                portfolio_session_id=uuid4(),
                agent_key=AgentKey.BUILD_PREPARATION,
                current_state={},
                agent_input={
                    **base_input,
                    "checkpoint_payload": checkpoint.model_dump(mode="json"),
                },
                run_id=uuid4(),
            )
        )

        assert second_model.operations == ["review_handoff_quality"]
        assert second.output["package"]["archive_sha256"]
        assert second.output["model_calls"] == first.output["model_calls"]
        resumed = {event["event_id"] for event in second.output["events"]}
        assert {
            "stage_1_checkpoint_resumed",
            "stage_2_checkpoint_resumed",
            "stage_3_checkpoint_resumed",
            "stage_4_checkpoint_resumed",
        } <= resumed

        changed_candidates = checkpoint.model_copy(
            update={"candidate_set_hash": "different-candidate-set"}
        )
        third_model = _Phase2Model()
        third = await BuildPreparationAgent(
            model_client=third_model,
            live_model=True,
            live_providers=False,
            settings=settings,
        ).run(
            build_context(
                portfolio_session_id=uuid4(),
                agent_key=AgentKey.BUILD_PREPARATION,
                current_state={},
                agent_input={
                    **base_input,
                    "checkpoint_payload": changed_candidates.model_dump(mode="json"),
                },
                run_id=uuid4(),
            )
        )

        assert third_model.operations == [
            "select_resources",
            "write_build_context",
            "integrate_cross_route",
            "review_handoff_quality",
        ]
        invalidated_events = {event["event_id"] for event in third.output["events"]}
        assert "stage_1_checkpoint_resumed" in invalidated_events
        assert "checkpoint_candidate_set_changed" in invalidated_events
        assert "stage_2_checkpoint_resumed" not in invalidated_events
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_checkpoint_binding_rejects_source_and_profile_changes() -> None:
    checkpoint = BuildPreparationCheckpoint(
        run_id="run",
        approved_source_hash="source",
        profile_fingerprint="profile",
        completed_stage="stage_1",
    )

    assert checkpoint.compatible_with(
        run_id="run", approved_source_hash="source", profile_fingerprint="profile"
    )
    assert not checkpoint.compatible_with(
        run_id="run", approved_source_hash="changed", profile_fingerprint="profile"
    )
    assert not checkpoint.compatible_with(
        run_id="run", approved_source_hash="source", profile_fingerprint="changed"
    )


@pytest.mark.asyncio
async def test_live_handoff_review_failure_retains_deterministic_package() -> None:
    output_dir = _output_dir()
    try:
        settings = Settings()
        settings.build_preparation.fixture_output_dir = str(output_dir)
        settings.build_preparation.integration_route_threshold = 99
        context = build_context(
            portfolio_session_id=uuid4(),
            agent_key=AgentKey.BUILD_PREPARATION,
            current_state={},
            agent_input={
                "operation": "build",
                "visual_design_director": _visual(),
                "content_architect": _content(),
                "live_model": True,
                "live_providers": False,
                "output_dir": str(output_dir),
                "integration_route_threshold": 99,
            },
        )

        result = await BuildPreparationAgent(
            model_client=_FailingHandoffModel(),
            live_model=True,
            live_providers=False,
            settings=settings,
        ).run(context)

        report = result.output["handoff_report"]
        assert result.output["model_calls"] == 4
        # Stage 5 is advisory only (per its own prompt): a live-review
        # failure must retain the deterministic report's eligibility, not
        # force needs_attention. The failure is recorded as diagnostic
        # metadata in model_review, not as a blocking issue.
        assert report["handoff_eligible"] is True
        assert not any(issue["code"] == "MODEL_REVIEW_UNAVAILABLE" for issue in report["issues"])
        assert report["model_review"]["mode"] == "live_model_unavailable"
        assert result.output["package"]["archive_size_bytes"] > 0
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
                "content_architect": _content(),
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


@pytest.mark.asyncio
async def test_live_context_drops_closed_set_duplicate_top_level_route_scope() -> None:
    output_dir = _output_dir()
    try:
        settings = Settings()
        settings.build_preparation.fixture_output_dir = str(output_dir)
        settings.build_preparation.integration_route_threshold = 99
        context = build_context(
            portfolio_session_id=uuid4(),
            agent_key=AgentKey.BUILD_PREPARATION,
            current_state={},
            agent_input={
                "operation": "build",
                "visual_design_director": _visual(),
                "content_architect": _content(),
                "live_model": True,
                "live_providers": False,
                "output_dir": str(output_dir),
                "integration_route_threshold": 99,
            },
        )

        result = await BuildPreparationAgent(
            model_client=_DuplicateTopLevelRouteModel(),
            live_model=True,
            live_providers=False,
            settings=settings,
        ).run(context)

        assert result.output["build_context"]["routes"][0]["path"] == "/"
        assert any(
            "closed-set duplicate top-level route scope" in warning
            for warning in result.output["warnings"]
        )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_live_context_accepts_grounded_route_data_fallback_note() -> None:
    output_dir = _output_dir()
    try:
        settings = Settings()
        settings.build_preparation.fixture_output_dir = str(output_dir)
        settings.build_preparation.integration_route_threshold = 99
        context = build_context(
            portfolio_session_id=uuid4(),
            agent_key=AgentKey.BUILD_PREPARATION,
            current_state={},
            agent_input={
                "operation": "build",
                "visual_design_director": _visual(),
                "content_architect": _content(),
                "live_model": True,
                "live_providers": False,
                "output_dir": str(output_dir),
                "integration_route_threshold": 99,
            },
        )

        result = await BuildPreparationAgent(
            model_client=_RouteFallbackNoteModel(),
            live_model=True,
            live_providers=False,
            settings=settings,
        ).run(context)

        assert (
            result.output["build_context"]["routes"][0]["data_fallback_note"]
            == "Use the approved custom data fallback for this route."
        )
        assert result.output["build_context"]["routes"][0]["warnings"] == [
            "Selected resource IDs are authoritative for this route."
        ]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
