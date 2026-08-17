from __future__ import annotations

import io
from types import SimpleNamespace

import pytest
from PIL import Image

from oryxenai.agents.code_generator.core.development_input import DevelopmentInputAdapter
from oryxenai.agents.code_generator.core.development_schemas import ResourceCandidate, SitePlan
from oryxenai.agents.code_generator.core.resource_adapters import (
    ImageAdapter,
    OfflineResourceProviderRegistry,
    default_adapters,
)
from oryxenai.core.settings import get_settings
from oryxenai.db.repositories.code_generator_development import CodeGeneratorDevelopmentRepository
from oryxenai.jobs.handlers.code_generator import (
    CodeGeneratorAcquisitionHandler,
    CodeGeneratorPlanningHandler,
)


def _plan(*, resource_slot: bool = False) -> SitePlan:
    return SitePlan.model_validate(
        {
            "plan_id": "plan-home",
            "routes": [
                {
                    "route_id": "home",
                    "path": "/",
                    "section_ids": ["hero", "project"],
                    "responsive_outcome": "stack on mobile",
                    "reduced_motion_outcome": "static equivalent",
                    "interaction_outcome": "keyboard accessible",
                    "composition": {
                        "hierarchy": "headline before evidence",
                        "layout_strategy": "text-led asymmetry",
                        "visual_anchor": "evidence panel",
                    },
                    "responsive_behavior": {
                        "mobile_strategy": "stack sections",
                        "breakpoint_strategy": "collapse at readable measure",
                        "overflow_strategy": "wrap controls",
                        "touch_target_strategy": "large targets",
                    },
                }
            ],
            "creative_thesis": {
                "thesis": "evidence-first systems",
                "distinction": "proof-led rather than card-led",
                "narrative_arc": "positioning to evidence",
            },
            "visual_system": {
                "typography": "confident display and calm body",
                "color_strategy": "single evidence accent",
                "spacing_rhythm": "editorial pauses",
                "motion_vocabulary": "subtle optional reveals",
            },
            "shell": {
                "navigation": "semantic anchor navigation",
                "main_landmark": "one main landmark",
                "focus_treatment": "visible focus ring",
            },
            "shared_component_contracts": [
                {
                    "component_id": "evidence-panel",
                    "purpose": "frame evidence",
                    "visual_role": "quiet contrast",
                    "expected_exports": ["EvidencePanel"],
                }
            ],
            "interactions": [
                {
                    "interaction_id": "home-nav",
                    "route_id": "home",
                    "trigger": "keyboard focus",
                    "outcome": "visible navigation focus",
                    "keyboard_behavior": "native link",
                    "reduced_motion_behavior": "static",
                }
            ],
            "acceptance_coverage": [
                {
                    "criterion_id": "criterion:home:0",
                    "route_id": "home",
                    "expected_outcome": "evidence-first hierarchy",
                    "source_marker": "data-criterion-id",
                }
            ],
            "resource_slots": (
                [{"slot_id": "hero-image", "route_id": "home", "purpose": "editorial image"}]
                if resource_slot
                else []
            ),
            "work_graph": {
                "units": [
                    {"unit_id": "foundation", "kind": "foundation"},
                    {
                        "unit_id": "route-home",
                        "kind": "route",
                        "route_id": "home",
                        "section_ids": ["hero", "project"],
                        "depends_on": ["foundation"],
                    },
                    {
                        "unit_id": "integrate",
                        "kind": "integration",
                        "depends_on": ["foundation", "route-home"],
                        "terminal": True,
                    },
                ]
            },
        }
    )


def _png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (2, 2), (30, 60, 90)).save(output, format="PNG")
    return output.getvalue()


async def _create_run(db_session, settings, plan: SitePlan):
    adapter = DevelopmentInputAdapter(settings)
    reference = adapter.from_fixture("privacy-safe-v3")
    repository = CodeGeneratorDevelopmentRepository(db_session)
    run = await repository.create(
        input_reference=reference.model_dump(mode="json"), idempotency_key=None
    )
    updated = await repository.compare_and_swap(
        run.id,
        expected_revision=run.revision,
        values={
            "status": "planned",
            "plan": plan.model_dump(mode="json"),
            "planner_receipt": {"plan_hash": "plan-hash"},
        },
    )
    assert updated is not None
    await db_session.commit()
    return updated


@pytest.mark.integration
async def test_acquire_full_offline_path_and_no_provider_for_complete_pack(
    db_session, tmp_path
) -> None:
    settings = get_settings()
    settings.code_generator_acquisition.materials_root = str(tmp_path / "materials")
    settings.code_generator_dependencies.workspaces_root = str(tmp_path / "workspaces")
    run = await _create_run(db_session, settings, _plan(resource_slot=True))
    # The fixture is intentionally injected through the adapter factory in the
    # second assertion below; the resource-complete path is tested by the plan
    # without slots and must never call the factory's search method.
    calls = 0

    class SentinelAdapter(ImageAdapter):
        async def search(self, request, *, settings):
            nonlocal calls
            calls += 1
            return []

    handler = CodeGeneratorAcquisitionHandler(
        adapter_factory=lambda _settings: {
            **default_adapters(),
            "image": SentinelAdapter(),
        }
    )
    result = await handler.execute({"development_run_id": str(run.id)}, "test-worker")
    assert result["status"] == "succeeded"
    refreshed = await CodeGeneratorDevelopmentRepository(db_session).get(run.id)
    assert refreshed is not None
    await db_session.refresh(refreshed)
    assert refreshed.status == "acquired"
    assert calls == 1  # the slot is a genuine gap; the no-slot case is below

    complete_run = await _create_run(db_session, settings, _plan(resource_slot=False))
    result = await handler.execute({"development_run_id": str(complete_run.id)}, "test-worker")
    assert result["status"] == "succeeded"
    assert calls == 1


@pytest.mark.integration
async def test_acquire_worker_redelivery_reuses_ledger(db_session, tmp_path) -> None:
    settings = get_settings()
    settings.code_generator_acquisition.materials_root = str(tmp_path / "materials")
    settings.code_generator_dependencies.workspaces_root = str(tmp_path / "workspaces")
    run = await _create_run(db_session, settings, _plan(resource_slot=False))
    handler = CodeGeneratorAcquisitionHandler()
    payload = {"development_run_id": str(run.id)}
    first = await handler.execute(payload, "test-worker")
    assert first["status"] == "succeeded"
    second = await handler.execute(payload, "test-worker")
    assert second == {"status": "succeeded", "run_id": str(run.id), "reused": True}


@pytest.mark.integration
async def test_successful_image_acquisition_materializes_local_bytes(db_session, tmp_path) -> None:
    settings = get_settings()
    settings.code_generator_acquisition.materials_root = str(tmp_path / "materials")
    settings.code_generator_dependencies.workspaces_root = str(tmp_path / "workspaces")
    run = await _create_run(db_session, settings, _plan(resource_slot=True))
    registry = OfflineResourceProviderRegistry()
    registry.register(
        ResourceCandidate(
            candidate_id="fixture-image",
            provider_key="fixture",
            provider_resource_id="fixture-image",
            category="image",
            title="Editorial image",
            tags=["editorial", "image"],
            canonical_source="fixture://image",
            licence="Fixture License",
            attribution="Fixture",
            vendoring_policy="download and vendor",
        ),
        _png(),
    )
    handler = CodeGeneratorAcquisitionHandler(
        adapter_factory=lambda _settings: default_adapters(registry=registry)
    )
    result = await handler.execute({"development_run_id": str(run.id)}, "test-worker")
    assert result["status"] == "succeeded"
    refreshed = await CodeGeneratorDevelopmentRepository(db_session).get(run.id)
    assert refreshed is not None
    await db_session.refresh(refreshed)
    assert refreshed.status == "acquired"
    assert refreshed.acquire_summary["admitted_resource_count"] == 1
    local_path = refreshed.resource_ledger["receipts"][0]["materialized_files"][0]["local_path"]
    assert (tmp_path / "materials" / local_path).is_file()


@pytest.mark.integration
async def test_planner_worker_redelivery_reuses_plan(db_session) -> None:
    settings = get_settings()
    run = await _create_run(db_session, settings, _plan(resource_slot=False))

    class FakePlanner:
        async def generate_structured(self, **_kwargs):
            return SimpleNamespace(
                parsed_output=_plan(resource_slot=False).model_dump(mode="json"),
                response_id="planner-response",
                model="test",
                usage={},
                finish_reason="stop",
            )

    # Rewind the run to the Phase 1 input state so the planner handler owns the
    # transition, rather than bypassing it through the helper above.
    repository = CodeGeneratorDevelopmentRepository(db_session)
    current = await repository.get(run.id)
    assert current is not None
    updated = await repository.compare_and_swap(
        run.id,
        expected_revision=current.revision,
        values={"status": "created", "plan": None, "planner_receipt": None, "issues": []},
    )
    assert updated is not None
    await db_session.commit()
    handler = CodeGeneratorPlanningHandler(planner_factory=FakePlanner)
    payload = {"development_run_id": str(run.id)}
    first = await handler.execute(payload, "test-worker")
    second = await handler.execute(payload, "test-worker")
    assert first["status"] == second["status"] == "succeeded"
    assert second["reused"] is True
