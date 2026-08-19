from __future__ import annotations

from oryxenai.agents.code_generator.core.checkpoint_store import CheckpointStore
from oryxenai.agents.code_generator.core.development_input import DevelopmentInputAdapter
from oryxenai.agents.code_generator.core.development_schemas import GenerationProjection, SitePlan
from oryxenai.agents.code_generator.core.generation_orchestrator import _unit_projection_dict
from oryxenai.agents.code_generator.core.workspace import GenerationWorkspace
from oryxenai.core.settings import get_settings
from oryxenai.db.repositories.code_generator_development import CodeGeneratorDevelopmentRepository
from oryxenai.jobs.handlers.code_generator_verification import CodeGeneratorVerificationHandler
from oryxenai.storage.preview import MemoryPreviewStorage


class _UnexpectedRepairModel:
    async def generate_structured(self, **_kwargs):
        raise AssertionError("A clean verification fixture must not invoke repair.")


def _plan() -> SitePlan:
    return SitePlan.model_validate(
        {
            "plan_id": "phase4-plan",
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


async def test_verification_builds_and_promotes_a_clean_candidate(db_session, tmp_path) -> None:
    settings = get_settings()
    settings.code_generator_development.input_root = str(tmp_path / "inputs")
    settings.code_generator_generation.workspace_root = str(tmp_path / "workspaces")
    settings.code_generator_generation.checkpoint_root = str(tmp_path / "checkpoints")
    settings.code_generator_acquisition.materials_root = str(tmp_path / "materials")
    settings.code_generator_dependencies.workspaces_root = str(tmp_path / "dependencies")
    settings.code_generator_verification.preview_root = str(tmp_path / "preview")
    settings.code_generator_verification.preview_base_url = "http://127.0.0.1:4174/preview"
    settings.code_generator_verification.preview_parent_origin = "http://test"
    settings.code_generator_verification.install_timeout_seconds = 120
    settings.code_generator_verification.typecheck_timeout_seconds = 120
    settings.code_generator_verification.build_timeout_seconds = 120

    adapter = DevelopmentInputAdapter(settings)
    reference = adapter.from_fixture("privacy-safe-v3")
    receipt, projections = adapter.admit(reference)
    repository = CodeGeneratorDevelopmentRepository(db_session)
    run = await repository.create(
        input_reference=reference.model_dump(mode="json"), idempotency_key=None
    )
    plan = _plan()
    workspace = GenerationWorkspace.open(
        settings, run_id=str(run.id), admitted_identity=receipt.admitted_identity
    )
    from oryxenai.agents.code_generator.core.source_manifest import materialize_trusted_manifests

    materialize_trusted_manifests(workspace, projections, plan)
    route_file = workspace.repo_dir / "src" / "routes" / "home-4ea140588150" / "index.tsx"
    route_file.write_text(
        'import "./route.css";\n'
        'import { publicRouteUrl } from "../../app/ResourceUrl";\n\n'
        "export default function RoutePage() {\n"
        '  return <main data-route-id="home" data-criterion-id="criterion:home:0">\n'
        '    <section data-content-id="hero"><h1>Durable systems</h1></section>\n'
        '    <section data-content-id="project"><h2>QueueGuard</h2><p>Designed durable job lifecycles.</p></section>\n'
        '    <a data-navigation-target="home" data-interaction-id="home-nav" href={publicRouteUrl("/")}>Home</a>\n'
        "    {/* slot-abf48c82a3ef77ddba4e slot-fa09c3c4a6256f2edce6 */}\n"
        "  </main>;\n"
        "}\n",
        encoding="utf-8",
    )
    route_file.with_name("route.css").write_text(
        "main { width: min(calc(100% - 2rem), 64rem); min-height: 16rem; "
        "margin-inline: auto; padding: 2rem 0; }\n"
        "section { min-height: 4.5rem; padding-block: 1rem; }\n"
        "a { display: inline-flex; min-width: 2.75rem; min-height: 2.75rem; "
        "align-items: center; }\n",
        encoding="utf-8",
    )
    checkpoint = CheckpointStore(workspace, generation_id=str(run.id)).accept(
        work_unit_id="phase4-source"
    )
    generation = GenerationProjection(
        generation_id=f"generation-{run.id}",
        input_receipt_hash=receipt.admitted_identity,
        site_plan_hash="plan-hash",
        phase="source_ready",
        accepted_checkpoint=checkpoint,
        source_ready=True,
        work_units=[_unit_projection_dict(unit) for unit in plan.work_graph.units],
    )
    updated = await repository.compare_and_swap(
        run.id,
        expected_revision=run.revision,
        values={
            "status": "source_ready",
            "plan": plan.model_dump(mode="json"),
            "planner_receipt": {"plan_hash": "plan-hash"},
            "input_receipt": receipt.model_dump(mode="json"),
            "resource_ledger": projections["resources/ledger.json"],
            "dependency_ledger": {"receipts": [], "dependency_ledger_hash": ""},
            "generation_projection": generation.model_dump(mode="json"),
            "source_checkpoint": checkpoint.model_dump(mode="json"),
        },
    )
    assert updated is not None
    await db_session.commit()

    storage = MemoryPreviewStorage()
    result = await CodeGeneratorVerificationHandler(
        model_factory=lambda _profile: _UnexpectedRepairModel(),
        storage_factory=lambda _settings: storage,
    ).execute({"development_run_id": str(run.id)}, "test-worker")
    refreshed = await CodeGeneratorDevelopmentRepository(db_session).get(run.id)
    assert refreshed is not None
    await db_session.refresh(refreshed)
    assert result["status"] == "succeeded", {
        "result": result,
        "issues": refreshed.issues,
        "verification": refreshed.verification_projection,
    }
    assert refreshed.status == "ready"
    assert refreshed.active_preview is not None
    assert refreshed.pending_promotion is None
    assert refreshed.verification_projection["gate_results"][-1]["status"] == "passed"
