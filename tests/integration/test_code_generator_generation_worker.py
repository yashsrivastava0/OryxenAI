from __future__ import annotations

import asyncio
import io
from types import SimpleNamespace

import pytest
from PIL import Image

from oryxenai.agents.code_generator.core.development_input import DevelopmentInputAdapter
from oryxenai.agents.code_generator.core.development_schemas import (
    GenerationProjection,
    ResourceCandidate,
    ResourceRequest,
    SitePlan,
)
from oryxenai.agents.code_generator.core.generation_orchestrator import (
    CodeGeneratorGenerationOrchestrator,
)
from oryxenai.agents.code_generator.core.resource_adapters import (
    OfflineResourceProviderRegistry,
    default_adapters,
)
from oryxenai.core.settings import get_settings
from oryxenai.db.repositories.code_generator_development import CodeGeneratorDevelopmentRepository

pytestmark = pytest.mark.integration


def _plan() -> SitePlan:
    return SitePlan.model_validate(
        {
            "plan_id": "plan-home",
            "routes": [
                {
                    "route_id": "home",
                    "path": "/",
                    "section_ids": ["home:hero", "home:project"],
                    "responsive_outcome": "stack on mobile",
                    "reduced_motion_outcome": "static equivalent",
                    "interaction_outcome": "keyboard accessible",
                    "composition": {
                        "hierarchy": "headline before evidence",
                        "layout_strategy": "text-led asymmetric grid",
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
                    "criterion_id": "criterion:home:hero",
                    "route_id": "home",
                    "expected_outcome": "Positioning",
                    "source_marker": "data-criterion-id",
                },
                {
                    "criterion_id": "criterion:home:project",
                    "route_id": "home",
                    "expected_outcome": "Evidence",
                    "source_marker": "data-criterion-id",
                },
            ],
            "work_graph": {
                "units": [
                    {"unit_id": "foundation", "kind": "foundation"},
                    {
                        "unit_id": "route-home",
                        "kind": "route",
                        "route_id": "home",
                        "section_ids": ["home:hero", "home:project"],
                        "owns_paths": ["src/routes/home/index.tsx"],
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


class _GenerationModel:
    def __init__(self, *, emergent: bool = False) -> None:
        self.calls: list[str] = []
        self.emergent = emergent
        self.requested = False

    async def generate_structured(self, *, operation, **_kwargs):
        self.calls.append(operation)
        context_hash = _kwargs.get("input_payload", {}).get("context_receipt_hash", "")
        if self.emergent and operation.endswith("foundation") and not self.requested:
            self.requested = True
            request = ResourceRequest(
                request_id="emergent-image",
                based_on={"input_receipt_hash": "input", "site_plan_hash": "plan"},
                origin={
                    "phase": "generation",
                    "work_unit_id": "foundation",
                    "role": "foundation_builder",
                    "origin_kind": "emergent_generation",
                },
                category="image",
                placement={
                    "route_id": "home",
                    "section_id": "home:hero",
                    "purpose": "editorial ornament",
                },
                why_existing_is_insufficient="The foundation needs a local decorative texture.",
                query={"positive_terms": ["editorial", "ornament"]},
                technical_constraints={"media_types": ["image/png"], "max_bytes": 4 * 1024 * 1024},
                source_constraints={
                    "allowed_source_kinds": ["fixture"],
                    "vendoring_required": True,
                },
                requiredness="preferred",
                fallback={"kind": "generated_local", "implementation": "CSS ornament"},
                affected_work_unit_ids=["foundation"],
            )
            return SimpleNamespace(
                parsed_output={
                    "operation_id": operation,
                    "based_on_context_receipt": context_hash,
                    "mode": "requests",
                    "requests": {
                        "resource_requests": [request.model_dump(mode="json")],
                        "dependency_requests": [],
                    },
                },
                response_id="request-response",
                model="test-model",
                usage={},
                finish_reason="stop",
            )
        if operation.endswith("foundation"):
            content = ":root { --foundation-ready: 1; }\n"
            path = "src/design/tokens.css"
        elif operation.endswith("route_batch"):
            content = (
                "export default function RoutePage() {\n"
                '  return <main className="route-page"><h1>Durable systems</h1><h2>QueueGuard</h2><p>Designed durable job lifecycles.</p></main>;\n'
                "}\n"
            )
            path = "src/routes/home/index.tsx"
        else:
            content = "export const integrationReady = true;\n"
            path = "src/components/shared/integration.ts"
        return SimpleNamespace(
            parsed_output={
                "operation_id": operation,
                "based_on_context_receipt": context_hash,
                "mode": "changes",
                "changes": {
                    "files": [
                        {
                            "path": path,
                            "operation": "replace",
                            "complete_utf8_content": content,
                        }
                    ],
                    "self_check": {
                        "source_complete": True,
                        "owned_paths_only": True,
                        "facts_preserved": True,
                        "resource_bindings_resolved": True,
                        "reduced_motion_preserved": True,
                    },
                },
            },
            response_id=f"response-{len(self.calls)}",
            model="test-model",
            usage={},
            finish_reason="stop",
        )


@pytest.mark.integration
async def test_generation_resume_rejects_projection_hash_drift_before_workspace_or_model(
    db_session, tmp_path
) -> None:
    settings = get_settings()
    settings.code_generator_development.input_root = str(tmp_path / "inputs")
    settings.code_generator_generation.workspace_root = str(tmp_path / "workspaces")
    settings.code_generator_generation.checkpoint_root = str(tmp_path / "checkpoints")
    adapter = DevelopmentInputAdapter(settings)
    reference = adapter.from_fixture("privacy-safe-v3")
    receipt, _projections = adapter.admit(reference)
    persisted_receipt = receipt.model_dump(mode="json")
    projection_name = next(iter(persisted_receipt["projection_hashes"]))
    persisted_receipt["projection_hashes"][projection_name] = "0" * 64

    repository = CodeGeneratorDevelopmentRepository(db_session)
    run = await repository.create(
        input_reference=reference.model_dump(mode="json"), idempotency_key=None
    )
    generation = GenerationProjection(
        generation_id=f"generation-{run.id}",
        input_receipt_hash=receipt.admitted_identity,
        site_plan_hash="plan-hash",
        phase="acquired",
    )
    updated = await repository.compare_and_swap(
        run.id,
        expected_revision=run.revision,
        values={
            "status": "acquired",
            "plan": _plan().model_dump(mode="json"),
            "planner_receipt": {"plan_hash": "plan-hash"},
            "input_receipt": persisted_receipt,
            "resource_ledger": {
                "based_on_input_and_plan": {},
                "requests": [],
                "receipts": [],
                "active_bindings": [],
                "plan_deltas": [],
                "ledger_hash": "",
            },
            "dependency_ledger": {"receipts": [], "dependency_ledger_hash": ""},
            "generation_projection": generation.model_dump(mode="json"),
        },
    )
    assert updated is not None
    await db_session.commit()

    model = _GenerationModel()
    result = await CodeGeneratorGenerationOrchestrator(
        model_factory=lambda _profile: model
    ).execute({"development_run_id": str(run.id)}, "drift-worker")

    refreshed = await CodeGeneratorDevelopmentRepository(db_session).get(run.id)
    assert refreshed is not None
    await db_session.refresh(refreshed)
    assert result == {
        "status": "needs_attention",
        "run_id": str(run.id),
        "code": "INPUT_PROJECTION_DRIFT",
    }
    assert refreshed.status == "needs_attention"
    assert refreshed.issues[0]["code"] == "INPUT_PROJECTION_DRIFT"
    assert model.calls == []
    repo_dir = tmp_path / "workspaces" / str(run.id) / "repo"
    assert repo_dir.is_dir()  # Failure export creates a metadata-only workspace shell.
    assert not any(repo_dir.rglob("*"))


@pytest.mark.integration
async def test_generation_creates_source_checkpoint_and_reuses_it(db_session, tmp_path) -> None:
    settings = get_settings()
    settings.code_generator_development.input_root = str(tmp_path / "inputs")
    settings.code_generator_generation.workspace_root = str(tmp_path / "workspaces")
    settings.code_generator_generation.checkpoint_root = str(tmp_path / "checkpoints")
    adapter = DevelopmentInputAdapter(settings)
    reference = adapter.from_fixture("privacy-safe-v3")
    receipt, _projections = adapter.admit(reference)
    repository = CodeGeneratorDevelopmentRepository(db_session)
    run = await repository.create(
        input_reference=reference.model_dump(mode="json"), idempotency_key=None
    )
    updated = await repository.compare_and_swap(
        run.id,
        expected_revision=run.revision,
        values={
            "status": "acquired",
            "plan": _plan().model_dump(mode="json"),
            "planner_receipt": {"plan_hash": "plan-hash"},
            "input_receipt": receipt.model_dump(mode="json"),
            "resource_ledger": {
                "based_on_input_and_plan": {},
                "requests": [],
                "receipts": [],
                "active_bindings": [],
                "plan_deltas": [],
                "ledger_hash": "",
            },
            "dependency_ledger": {"receipts": [], "dependency_ledger_hash": ""},
        },
    )
    assert updated is not None
    await db_session.commit()
    model = _GenerationModel()
    result = await CodeGeneratorGenerationOrchestrator(
        model_factory=lambda _profile: model
    ).execute({"development_run_id": str(run.id)}, "test-worker")
    refreshed = await CodeGeneratorDevelopmentRepository(db_session).get(run.id)
    assert refreshed is not None
    await db_session.refresh(refreshed)
    assert result["status"] == "succeeded", {
        "result": result,
        "issues": refreshed.issues,
        "generation": refreshed.generation_projection,
    }
    assert refreshed.status == "source_ready"
    assert refreshed.source_checkpoint["file_count"] > 0
    assert len(model.calls) == 2
    result = await CodeGeneratorGenerationOrchestrator(
        model_factory=lambda _profile: model
    ).execute({"development_run_id": str(run.id)}, "test-worker")
    assert result["reused"] is True
    assert len(model.calls) == 2
    checkpoint_root = tmp_path / "checkpoints" / str(run.id)
    assert not list(checkpoint_root.rglob("node_modules"))
    assert not list(checkpoint_root.rglob("dist"))


@pytest.mark.integration
async def test_emergent_resource_request_pauses_and_resumes(db_session, tmp_path) -> None:
    settings = get_settings()
    settings.code_generator_development.input_root = str(tmp_path / "inputs")
    settings.code_generator_generation.workspace_root = str(tmp_path / "workspaces")
    settings.code_generator_generation.checkpoint_root = str(tmp_path / "checkpoints")
    settings.code_generator_acquisition.materials_root = str(tmp_path / "materials")
    adapter = DevelopmentInputAdapter(settings)
    reference = adapter.from_fixture("privacy-safe-v3")
    receipt, _projections = adapter.admit(reference)
    repository = CodeGeneratorDevelopmentRepository(db_session)
    run = await repository.create(
        input_reference=reference.model_dump(mode="json"), idempotency_key=None
    )
    updated = await repository.compare_and_swap(
        run.id,
        expected_revision=run.revision,
        values={
            "status": "acquired",
            "plan": _plan().model_dump(mode="json"),
            "planner_receipt": {"plan_hash": "plan-hash"},
            "input_receipt": receipt.model_dump(mode="json"),
            "resource_ledger": {
                "based_on_input_and_plan": {},
                "requests": [],
                "receipts": [],
                "active_bindings": [],
                "plan_deltas": [],
                "ledger_hash": "",
            },
            "dependency_ledger": {"receipts": [], "dependency_ledger_hash": ""},
        },
    )
    assert updated is not None
    await db_session.commit()

    image = io.BytesIO()
    Image.new("RGB", (2, 2), (20, 30, 40)).save(image, format="PNG")
    registry = OfflineResourceProviderRegistry()
    registry.register(
        ResourceCandidate(
            candidate_id="fixture-ornament",
            provider_key="fixture",
            provider_resource_id="fixture-ornament",
            category="image",
            title="Editorial ornament",
            tags=["editorial", "ornament"],
            canonical_source="fixture://ornament",
            licence="Fixture License",
            attribution="Fixture",
            vendoring_policy="download and vendor",
        ),
        image.getvalue(),
    )
    model = _GenerationModel(emergent=True)
    result = await CodeGeneratorGenerationOrchestrator(
        model_factory=lambda _profile: model,
        adapter_factory=lambda _settings: default_adapters(registry=registry),
    ).execute({"development_run_id": str(run.id)}, "test-worker")
    refreshed = await CodeGeneratorDevelopmentRepository(db_session).get(run.id)
    assert refreshed is not None
    await db_session.refresh(refreshed)
    assert result["status"] == "succeeded", {
        "result": result,
        "issues": refreshed.issues,
        "generation": refreshed.generation_projection,
    }
    assert refreshed.status == "source_ready"
    assert refreshed.resource_ledger["receipts"][0]["disposition"] == "admitted"
    assert refreshed.generation_projection["request_rounds"] == 1


@pytest.mark.integration
async def test_generation_redelivery_resumes_durable_acquisition_once(
    db_session, tmp_path, monkeypatch
) -> None:
    settings = get_settings()
    settings.code_generator_development.input_root = str(tmp_path / "inputs")
    settings.code_generator_generation.workspace_root = str(tmp_path / "workspaces")
    settings.code_generator_generation.checkpoint_root = str(tmp_path / "checkpoints")
    settings.code_generator_acquisition.materials_root = str(tmp_path / "materials")
    adapter = DevelopmentInputAdapter(settings)
    reference = adapter.from_fixture("privacy-safe-v3")
    receipt, _projections = adapter.admit(reference)
    repository = CodeGeneratorDevelopmentRepository(db_session)
    run = await repository.create(
        input_reference=reference.model_dump(mode="json"), idempotency_key=None
    )
    updated = await repository.compare_and_swap(
        run.id,
        expected_revision=run.revision,
        values={
            "status": "acquired",
            "plan": _plan().model_dump(mode="json"),
            "planner_receipt": {"plan_hash": "plan-hash"},
            "input_receipt": receipt.model_dump(mode="json"),
            "resource_ledger": {
                "based_on_input_and_plan": {},
                "requests": [],
                "receipts": [],
                "active_bindings": [],
                "plan_deltas": [],
                "ledger_hash": "",
            },
            "dependency_ledger": {"receipts": [], "dependency_ledger_hash": ""},
        },
    )
    assert updated is not None
    await db_session.commit()

    image = io.BytesIO()
    Image.new("RGB", (2, 2), (20, 30, 40)).save(image, format="PNG")
    registry = OfflineResourceProviderRegistry()
    registry.register(
        ResourceCandidate(
            candidate_id="fixture-redelivery-ornament",
            provider_key="fixture",
            provider_resource_id="fixture-redelivery-ornament",
            category="image",
            title="Editorial ornament",
            tags=["editorial", "ornament"],
            canonical_source="fixture://redelivery-ornament",
            licence="Fixture License",
            attribution="Fixture",
            vendoring_policy="download and vendor",
        ),
        image.getvalue(),
    )
    model = _GenerationModel(emergent=True)
    interrupted = CodeGeneratorGenerationOrchestrator(
        model_factory=lambda _profile: model,
        adapter_factory=lambda _settings: default_adapters(registry=registry),
    )

    async def cancel_after_request_reservation(**_kwargs):
        raise asyncio.CancelledError()

    monkeypatch.setattr(interrupted, "_resolve_requests", cancel_after_request_reservation)
    with pytest.raises(asyncio.CancelledError):
        await interrupted.execute({"development_run_id": str(run.id)}, "worker-first")

    interrupted_run = await CodeGeneratorDevelopmentRepository(db_session).get(run.id)
    assert interrupted_run is not None
    await db_session.refresh(interrupted_run)
    interrupted_projection = interrupted_run.generation_projection
    foundation = next(
        item for item in interrupted_projection["work_units"] if item["unit_id"] == "foundation"
    )
    assert interrupted_run.status == "acquiring"
    assert interrupted_projection["request_rounds"] == 1
    assert foundation["request_round"] == 1
    assert foundation["pending_request"] is not None
    assert len(foundation["request_receipt_ids"]) == 1
    assert len(interrupted_projection["context_receipts"]) == 1
    assert len(interrupted_projection["call_receipts"]) == 1

    result = await CodeGeneratorGenerationOrchestrator(
        model_factory=lambda _profile: model,
        adapter_factory=lambda _settings: default_adapters(registry=registry),
    ).execute({"development_run_id": str(run.id)}, "worker-redelivery")

    refreshed = await CodeGeneratorDevelopmentRepository(db_session).get(run.id)
    assert refreshed is not None
    await db_session.refresh(refreshed)
    assert result["status"] == "succeeded", {
        "result": result,
        "issues": refreshed.issues,
        "generation": refreshed.generation_projection,
    }
    generation = refreshed.generation_projection
    foundation = next(item for item in generation["work_units"] if item["unit_id"] == "foundation")
    context_ids = [item["receipt_id"] for item in generation["context_receipts"]]
    call_ids = [item["receipt_id"] for item in generation["call_receipts"]]
    assert refreshed.status == "source_ready"
    assert generation["request_rounds"] == 1
    assert foundation["request_round"] == 1
    assert foundation["pending_request"] is None
    assert len(foundation["request_receipt_ids"]) == 1
    assert len(context_ids) == len(set(context_ids)) == 3
    assert len(call_ids) == len(set(call_ids)) == 3
    assert len(refreshed.resource_ledger["requests"]) == 1
    assert len(refreshed.resource_ledger["receipts"]) == 1
    assert len(model.calls) == 3
