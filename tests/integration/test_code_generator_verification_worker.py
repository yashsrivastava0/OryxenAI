from __future__ import annotations

import pytest

from oryxenai.agents.code_generator.core.checkpoint_store import CheckpointStore
from oryxenai.agents.code_generator.core.development_input import DevelopmentInputAdapter
from oryxenai.agents.code_generator.core.development_schemas import (
    CandidateIdentity,
    DesignTokenSystemV4,
    Diagnostic,
    ExperienceBlueprintV4,
    GenerationProjection,
    QualityFindingV2,
    QualityReviewDraftV1,
    QualityReviewReceiptV2,
    QualityScoreEvidenceV1,
    RepairReceipt,
    SitePlan,
    VerificationProfile,
    VerificationProjection,
)
from oryxenai.agents.code_generator.core.generation_orchestrator import (
    CodeGeneratorGenerationOrchestrator,
    _unit_projection_dict,
)
from oryxenai.agents.code_generator.core.workspace import GenerationWorkspace
from oryxenai.core.settings import get_settings
from oryxenai.db.repositories.code_generator_development import CodeGeneratorDevelopmentRepository
from oryxenai.jobs.handlers.code_generator_verification import (
    CodeGeneratorVerificationHandler,
    VerificationFailure,
    _attempt_repair,
    _reconstruct_repair_unit_counts,
)
from oryxenai.storage.preview import MemoryPreviewStorage

pytestmark = pytest.mark.integration


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


def _v4_blueprint() -> ExperienceBlueprintV4:
    return ExperienceBlueprintV4(
        selected_concept_id="concept:proof",
        narrative_arc="positioning to evidence",
        tokens=DesignTokenSystemV4(
            colors=[
                {"name": "ink", "value": "#121212"},
                {"name": "paper", "value": "#f6f2ea"},
            ],
            spacing=[{"name": "section", "value": 4, "unit": "rem"}],
            typography_roles=[
                {
                    "role": "body",
                    "approved_font_slot": "font:body",
                    "family": "Local Sans",
                    "weights": [400, 700],
                    "local_files": ["resources/fonts/local/400-normal.woff2"],
                    "body_min_rem": 1,
                    "body_max_rem": 1.2,
                    "heading_ratio": 1.25,
                    "body_line_height": 1.5,
                }
            ],
            type_steps=[
                {
                    "name": "body",
                    "role": "body",
                    "minimum_rem": 1,
                    "maximum_rem": 1.2,
                    "line_height": 1.5,
                    "tracking_em": 0,
                },
                {
                    "name": "display",
                    "role": "body",
                    "minimum_rem": 2,
                    "maximum_rem": 3,
                    "line_height": 1.05,
                    "tracking_em": -0.02,
                },
            ],
            containers=[
                {
                    "name": "content",
                    "maximum": {"name": "content-max", "value": 1120, "unit": "px"},
                    "inline_padding": {"name": "content-pad", "value": 1, "unit": "rem"},
                }
            ],
            container_max_px=1120,
        ),
        route_shells=[
            {
                "route_id": "home",
                "storage_key": "home",
                "h1_owner": "hero",
                "section_order": ["hero"],
            }
        ],
        section_regions=[
            {
                "region_id": "region:hero",
                "route_id": "home",
                "section_id": "hero",
                "owner_id": "owner:hero",
                "section_selector": '[data-content-id="hero"]',
                "region_selector": '[data-region-id="region:hero"]',
                "order_mobile": 0,
                "order_tablet": 0,
                "order_desktop": 0,
                "columns_mobile": 1,
                "columns_tablet": 2,
                "columns_desktop": 2,
                "max_measure_ch": 68,
                "gap": {"name": "hero-gap", "value": 2, "unit": "rem"},
            }
        ],
        distinctive_moves=[
            {
                "move_id": "move:hero-rail",
                "route_id": "home",
                "section_id": "hero",
                "region_id": "region:hero",
                "implementation_kind": "asymmetric_width",
                "thesis": "The proof rail offsets the positioning headline.",
                "runtime_marker": 'data-distinctive-move-id="move:hero-rail"',
                "source_selector": '[data-distinctive-move-id="move:hero-rail"]',
                "target_selector": '[data-content-id="hero"]',
                "relationship": "width_ratio",
                "minimum_ratio": 0.25,
                "maximum_ratio": 1,
                "viewports": ["mobile", "tablet", "desktop"],
                "required_css_properties": ["grid-template-columns"],
            }
        ],
    )


async def test_attempt_repair_persists_rejected_quality_review(
    db_session, test_engine, tmp_path, monkeypatch
) -> None:
    """Regression test for the 2026-08-28 bug: QUALITY_REVIEW_REJECTED_AFTER_REPAIR
    used to raise before any persist ran, silently discarding the real
    rejection reason. It must now be readable afterward via the run's
    generation_projection/integration_review, and the run's accepted
    source_checkpoint must be left untouched (a rejected repair is never
    promoted)."""
    settings = get_settings()
    settings.code_generator_development.input_root = str(tmp_path / "inputs")
    settings.code_generator_generation.workspace_root = str(tmp_path / "workspaces")
    settings.code_generator_generation.checkpoint_root = str(tmp_path / "checkpoints")
    settings.code_generator_generation.max_repair_rounds_total = 6
    settings.code_generator_generation.max_repair_rounds_per_unit = 2

    adapter = DevelopmentInputAdapter(settings)
    reference = adapter.from_fixture("privacy-safe-v3")
    receipt, projections = adapter.admit(reference)
    repository = CodeGeneratorDevelopmentRepository(db_session)
    run = await repository.create(
        input_reference=reference.model_dump(mode="json"), idempotency_key=None
    )
    plan = _plan().model_copy(update={"experience_blueprint": _v4_blueprint()})
    workspace = GenerationWorkspace.open(
        settings, run_id=str(run.id), admitted_identity=receipt.admitted_identity
    )
    from oryxenai.agents.code_generator.core.source_manifest import materialize_trusted_manifests

    materialize_trusted_manifests(workspace, projections, plan)
    checkpoint = CheckpointStore(workspace, generation_id=str(run.id)).accept(
        work_unit_id="phase4-source"
    )

    original_source_checkpoint = {"note": "the run's accepted checkpoint before any repair"}
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
            "status": "repairing",
            "plan": plan.model_dump(mode="json"),
            "generation_projection": generation.model_dump(mode="json"),
            "source_checkpoint": original_source_checkpoint,
        },
    )
    assert updated is not None
    await db_session.commit()

    identity = CandidateIdentity(
        input_receipt_hash="irh",
        site_plan_hash="sph",
        work_graph_hash="wgh",
        source_checkpoint_hash=checkpoint.checkpoint_hash,
        source_manifest_hash="smh",
        scaffold_toolchain_profile_hash="stph",
        verification_profile_hash="vph",
    )
    profile = VerificationProfile(profile_id="test-profile")
    projection = VerificationProjection(
        generation_id=f"generation-{run.id}",
        candidate_identity=identity,
        verification_profile=profile,
        phase="repairing",
        status="repairing",
    )
    diagnostics = [
        Diagnostic(
            diagnostic_id="diag-1",
            group="source_contract",
            code="TEST_DIAGNOSTIC",
            phase="source_contract",
            normalized_message="test diagnostic requiring a repair attempt",
            fingerprint="fingerprint-1",
        )
    ]

    rejected_findings = [
        QualityFindingV2(
            finding_id="finding-1",
            severity="blocking",
            owner_work_unit_id="route-home-compose",
            code="CONTENT_COVERAGE_EMPTY",
            file="src/routes/home/index.tsx",
            line=12,
            marker="content-coverage",
            evidence="The repaired route dropped every real content binding.",
            requested_outcome="Restore the section's real copy and CTA bindings.",
        )
    ]
    score_evidence = [
        QualityScoreEvidenceV1(
            dimension=dimension,
            score=2 if dimension == "resource_fit" else 4,
            owner_work_unit_id="route-home-compose",
            file="src/routes/home/index.tsx",
            line=12,
            marker="content-coverage",
            evidence="Scored against the repaired route source.",
        )
        for dimension in ("hierarchy", "composition", "typography", "resource_fit", "motion")
    ]
    rejected_receipt = QualityReviewReceiptV2(
        source_manifest_hash="smh-2",
        plan_hash="plan-hash-2",
        realization_hash="realization-hash",
        review_context_hash="context-hash",
        response_id="response-1",
        review_hash="review-hash",
        quality_gate_version="test-gate-v1",
        hierarchy_score=4,
        composition_score=4,
        typography_score=4,
        resource_fit_score=2,
        motion_score=4,
        score_evidence=score_evidence,
        findings=rejected_findings,
        accepted=False,
    )
    rejected_draft = QualityReviewDraftV1(
        hierarchy_score=4,
        composition_score=4,
        typography_score=4,
        resource_fit_score=2,
        motion_score=4,
        score_evidence=score_evidence,
        findings=rejected_findings,
        review_summary="The repair stripped real content to dodge a build error.",
    )

    async def fake_repair(self, **_kwargs):
        return checkpoint, checkpoint_repair_receipt

    async def fake_integration_review(self, *, projection, **_kwargs):
        projection.quality_review = rejected_receipt
        return rejected_draft

    from oryxenai.agents.code_generator.core.development_schemas import RepairReceipt
    from oryxenai.agents.code_generator.core.final_repair import FinalRepairer

    checkpoint_repair_receipt = RepairReceipt(
        generation_id=f"generation-{run.id}",
        diagnostic_fingerprints=["fingerprint-1"],
        strategy_summary="bounded-simplification",
        based_on_checkpoint=checkpoint.checkpoint_hash,
        context_receipt="context-receipt-hash",
        corrected_checkpoint=checkpoint.checkpoint_hash,
        accepted_at="2026-08-28T00:00:00Z",
    )

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    sessionmaker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    monkeypatch.setattr(FinalRepairer, "repair", fake_repair)
    monkeypatch.setattr(
        CodeGeneratorGenerationOrchestrator, "_integration_review", fake_integration_review
    )
    with pytest.raises(VerificationFailure) as excinfo:
        await _attempt_repair(
            sessionmaker=sessionmaker,
            run_id=run.id,
            settings=settings,
            workspace=workspace,
            checkpoint_store=CheckpointStore(workspace, generation_id=str(run.id)),
            checkpoint=checkpoint,
            identity=identity,
            plan=plan,
            projections=projections,
            projection=projection,
            diagnostics=diagnostics,
            public_text=set(),
            allowed_packages=set(),
            model_factory=None,
        )

    assert excinfo.value.code == "QUALITY_REVIEW_REJECTED_AFTER_REPAIR"
    assert "resource_fit=2" in excinfo.value.message
    assert "CONTENT_COVERAGE_EMPTY" in excinfo.value.message
    assert "stripped real content" in excinfo.value.message

    refreshed = await CodeGeneratorDevelopmentRepository(db_session).get(run.id)
    assert refreshed is not None
    await db_session.refresh(refreshed)
    assert refreshed.integration_review is not None
    assert refreshed.integration_review["review_summary"] == (
        "The repair stripped real content to dodge a build error."
    )
    assert refreshed.generation_projection["quality_review"]["accepted"] is False
    assert refreshed.generation_projection["quality_review"]["resource_fit_score"] == 2
    # The rejected repair must never be promoted to the run's accepted checkpoint.
    assert refreshed.source_checkpoint == original_source_checkpoint


async def test_attempt_repair_retries_within_budget_after_cannot_complete(
    db_session, test_engine, tmp_path, monkeypatch
) -> None:
    """Regression test: a model-reported cannot_complete (FinalRepairError) on
    round 1 must consume one budgeted round and try again, not abandon the
    whole repair budget on the first failed attempt."""
    settings = get_settings()
    settings.code_generator_development.input_root = str(tmp_path / "inputs")
    settings.code_generator_generation.workspace_root = str(tmp_path / "workspaces")
    settings.code_generator_generation.checkpoint_root = str(tmp_path / "checkpoints")
    settings.code_generator_generation.max_repair_rounds_total = 6
    settings.code_generator_generation.max_repair_rounds_per_unit = 3

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
    checkpoint = CheckpointStore(workspace, generation_id=str(run.id)).accept(
        work_unit_id="phase4-source"
    )
    updated = await repository.compare_and_swap(
        run.id,
        expected_revision=run.revision,
        values={"status": "repairing", "plan": plan.model_dump(mode="json")},
    )
    assert updated is not None
    await db_session.commit()

    identity = CandidateIdentity(
        input_receipt_hash="irh",
        site_plan_hash="sph",
        work_graph_hash="wgh",
        source_checkpoint_hash=checkpoint.checkpoint_hash,
        source_manifest_hash="smh",
        scaffold_toolchain_profile_hash="stph",
        verification_profile_hash="vph",
    )
    projection = VerificationProjection(
        generation_id=f"generation-{run.id}",
        candidate_identity=identity,
        verification_profile=VerificationProfile(profile_id="test-profile"),
        phase="repairing",
        status="repairing",
    )
    diagnostics = [
        Diagnostic(
            diagnostic_id="diag-1",
            group="dom_runtime",
            code="RUNTIME_TOUCH_TARGET_TOO_SMALL",
            phase="dom_runtime",
            normalized_message="Interactive control a is smaller than the configured touch target.",
            fingerprint="fingerprint-touch-target",
        )
    ]

    from oryxenai.agents.code_generator.core.development_schemas import RepairReceipt
    from oryxenai.agents.code_generator.core.final_repair import FinalRepairer, FinalRepairError

    call_count = {"value": 0}

    async def flaky_repair(self, **kwargs):
        call_count["value"] += 1
        if call_count["value"] == 1:
            raise FinalRepairError(
                "REPAIR_NO_SOURCE_CHANGE",
                "The repair operation did not return a bounded source correction.",
            )
        receipt = RepairReceipt(
            generation_id=f"generation-{run.id}",
            diagnostic_fingerprints=["fingerprint-touch-target"],
            repair_unit_id="dom_runtime",
            strategy_summary=kwargs["strategy"],
            based_on_checkpoint=checkpoint.checkpoint_hash,
            context_receipt="context-receipt-hash",
            corrected_checkpoint=checkpoint.checkpoint_hash,
            accepted_at="2026-09-02T00:00:00Z",
        )
        return checkpoint, receipt

    monkeypatch.setattr(FinalRepairer, "repair", flaky_repair)

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    sessionmaker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    attempted = await _attempt_repair(
        sessionmaker=sessionmaker,
        run_id=run.id,
        settings=settings,
        workspace=workspace,
        checkpoint_store=CheckpointStore(workspace, generation_id=str(run.id)),
        checkpoint=checkpoint,
        identity=identity,
        plan=plan,
        projections=projections,
        projection=projection,
        diagnostics=diagnostics,
        public_text=set(),
        allowed_packages=set(),
        model_factory=None,
    )

    assert attempted is True
    assert call_count["value"] == 2
    assert projection.repair_rounds == 2
    assert projection.repair_receipts[-1].strategy_summary == "bounded-simplification"


async def test_attempt_repair_retries_within_budget_after_rejected_source_validation(
    db_session, test_engine, tmp_path, monkeypatch
) -> None:
    """Regression test: a live run hit final_repair.py's unwrapped
    validate_generation_changes call raising SourceValidationError
    (duplicate paths in the model's response) on round 1. That is the same
    class of rejected-response problem as FinalRepairError and must be
    retried within budget the same way, not treated as an infrastructure
    crash."""
    settings = get_settings()
    settings.code_generator_development.input_root = str(tmp_path / "inputs")
    settings.code_generator_generation.workspace_root = str(tmp_path / "workspaces")
    settings.code_generator_generation.checkpoint_root = str(tmp_path / "checkpoints")
    settings.code_generator_generation.max_repair_rounds_total = 6
    settings.code_generator_generation.max_repair_rounds_per_unit = 3

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
    checkpoint = CheckpointStore(workspace, generation_id=str(run.id)).accept(
        work_unit_id="phase4-source"
    )
    updated = await repository.compare_and_swap(
        run.id,
        expected_revision=run.revision,
        values={"status": "repairing", "plan": plan.model_dump(mode="json")},
    )
    assert updated is not None
    await db_session.commit()

    identity = CandidateIdentity(
        input_receipt_hash="irh",
        site_plan_hash="sph",
        work_graph_hash="wgh",
        source_checkpoint_hash=checkpoint.checkpoint_hash,
        source_manifest_hash="smh",
        scaffold_toolchain_profile_hash="stph",
        verification_profile_hash="vph",
    )
    projection = VerificationProjection(
        generation_id=f"generation-{run.id}",
        candidate_identity=identity,
        verification_profile=VerificationProfile(profile_id="test-profile"),
        phase="repairing",
        status="repairing",
    )
    diagnostics = [
        Diagnostic(
            diagnostic_id="diag-1",
            group="source_contract",
            code="SOURCE_MOTION_BEAT_UNIMPLEMENTED",
            phase="source_contract",
            normalized_message="Every v4 motion beat needs a target marker and executable source behavior.",
            fingerprint="fingerprint-motion-beat",
        )
    ]

    from oryxenai.agents.code_generator.core.development_schemas import RepairReceipt
    from oryxenai.agents.code_generator.core.final_repair import FinalRepairer
    from oryxenai.agents.code_generator.core.source_validation import SourceValidationError

    call_count = {"value": 0}

    async def flaky_repair(self, **kwargs):
        call_count["value"] += 1
        if call_count["value"] == 1:
            raise SourceValidationError(
                "SOURCE_DUPLICATE_PATH", "The generation response contains duplicate paths."
            )
        receipt = RepairReceipt(
            generation_id=f"generation-{run.id}",
            diagnostic_fingerprints=["fingerprint-motion-beat"],
            repair_unit_id="source_contract",
            strategy_summary=kwargs["strategy"],
            based_on_checkpoint=checkpoint.checkpoint_hash,
            context_receipt="context-receipt-hash",
            corrected_checkpoint=checkpoint.checkpoint_hash,
            accepted_at="2026-09-02T00:00:00Z",
        )
        return checkpoint, receipt

    monkeypatch.setattr(FinalRepairer, "repair", flaky_repair)

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    sessionmaker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    attempted = await _attempt_repair(
        sessionmaker=sessionmaker,
        run_id=run.id,
        settings=settings,
        workspace=workspace,
        checkpoint_store=CheckpointStore(workspace, generation_id=str(run.id)),
        checkpoint=checkpoint,
        identity=identity,
        plan=plan,
        projections=projections,
        projection=projection,
        diagnostics=diagnostics,
        public_text=set(),
        allowed_packages=set(),
        model_factory=None,
    )

    assert attempted is True
    assert call_count["value"] == 2
    assert projection.repair_rounds == 2


async def test_attempt_repair_reports_true_round_count_when_budget_exhausts_on_cannot_complete(
    db_session, test_engine, tmp_path, monkeypatch
) -> None:
    """Regression test: when every round in one call is an honest
    cannot_complete, the persisted repair_rounds must reflect the real
    number of consumed attempts, not 0 (repair_rounds is only otherwise
    updated after a *successful* round)."""
    settings = get_settings()
    settings.code_generator_development.input_root = str(tmp_path / "inputs")
    settings.code_generator_generation.workspace_root = str(tmp_path / "workspaces")
    settings.code_generator_generation.checkpoint_root = str(tmp_path / "checkpoints")
    settings.code_generator_generation.max_repair_rounds_total = 6
    settings.code_generator_generation.max_repair_rounds_per_unit = 3

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
    checkpoint = CheckpointStore(workspace, generation_id=str(run.id)).accept(
        work_unit_id="phase4-source"
    )
    updated = await repository.compare_and_swap(
        run.id,
        expected_revision=run.revision,
        values={"status": "repairing", "plan": plan.model_dump(mode="json")},
    )
    assert updated is not None
    await db_session.commit()

    identity = CandidateIdentity(
        input_receipt_hash="irh",
        site_plan_hash="sph",
        work_graph_hash="wgh",
        source_checkpoint_hash=checkpoint.checkpoint_hash,
        source_manifest_hash="smh",
        scaffold_toolchain_profile_hash="stph",
        verification_profile_hash="vph",
    )
    projection = VerificationProjection(
        generation_id=f"generation-{run.id}",
        candidate_identity=identity,
        verification_profile=VerificationProfile(profile_id="test-profile"),
        phase="repairing",
        status="repairing",
    )
    diagnostics = [
        Diagnostic(
            diagnostic_id="diag-1",
            group="dom_runtime",
            code="RUNTIME_TOUCH_TARGET_TOO_SMALL",
            phase="dom_runtime",
            normalized_message="Interactive control a is smaller than the configured touch target.",
            fingerprint="fingerprint-touch-target",
        )
    ]

    from oryxenai.agents.code_generator.core.final_repair import FinalRepairer, FinalRepairError

    async def always_cannot_complete(self, **_kwargs):
        raise FinalRepairError(
            "REPAIR_NO_SOURCE_CHANGE",
            "The repair operation did not return a bounded source correction.",
        )

    monkeypatch.setattr(FinalRepairer, "repair", always_cannot_complete)

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    sessionmaker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    attempted = await _attempt_repair(
        sessionmaker=sessionmaker,
        run_id=run.id,
        settings=settings,
        workspace=workspace,
        checkpoint_store=CheckpointStore(workspace, generation_id=str(run.id)),
        checkpoint=checkpoint,
        identity=identity,
        plan=plan,
        projections=projections,
        projection=projection,
        diagnostics=diagnostics,
        public_text=set(),
        allowed_packages=set(),
        model_factory=None,
    )

    assert attempted is False
    assert projection.repair_rounds == 3
    assert projection.repair_receipts == []


async def test_attempt_repair_stops_repeated_diagnostic_group_at_ceiling(
    db_session, test_engine
) -> None:
    """A repeated final-verification gate stops at its own third attempt."""
    settings = get_settings()
    settings.code_generator_generation.max_repair_rounds_total = 6
    settings.code_generator_generation.max_repair_rounds_per_unit = 3

    repository = CodeGeneratorDevelopmentRepository(db_session)
    run = await repository.create(
        input_reference={"kind": "repair-budget-test"}, idempotency_key=None
    )
    await db_session.commit()

    identity = CandidateIdentity(
        input_receipt_hash="input",
        site_plan_hash="plan",
        work_graph_hash="graph",
        source_checkpoint_hash="checkpoint",
        source_manifest_hash="manifest",
        scaffold_toolchain_profile_hash="toolchain",
        verification_profile_hash="verification",
    )
    repair_receipts = [
        RepairReceipt(
            generation_id="generation",
            diagnostic_fingerprints=[f"dom-runtime-{index}"],
            repair_unit_id="dom_runtime",
            strategy_summary="bounded-correction",
            based_on_checkpoint="checkpoint",
            context_receipt=f"context-{index}",
            corrected_checkpoint=f"corrected-{index}",
            accepted_at="2026-09-02T00:00:00Z",
        )
        for index in range(3)
    ]
    projection = VerificationProjection(
        generation_id="generation",
        candidate_identity=identity,
        verification_profile=VerificationProfile(profile_id="verification"),
        phase="repairing",
        status="repairing",
        repair_rounds=3,
        repair_receipts=repair_receipts,
    )
    diagnostic = Diagnostic(
        diagnostic_id="dom-runtime-current",
        group="dom_runtime",
        code="RUNTIME_TOUCH_TARGET_TOO_SMALL",
        phase="runtime",
        normalized_message="The current interactive target is too small.",
        fingerprint="dom-runtime-current",
    )

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    sessionmaker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    attempted = await _attempt_repair(
        sessionmaker=sessionmaker,
        run_id=run.id,
        settings=settings,
        workspace=None,
        checkpoint_store=None,
        checkpoint=None,
        identity=identity,
        plan=None,
        projections={},
        projection=projection,
        diagnostics=[diagnostic],
        public_text=set(),
        allowed_packages=set(),
        model_factory=lambda _profile: pytest.fail("repair model must not run after the ceiling"),
    )

    assert attempted is False
    assert projection.active_gate == "dom_runtime"
    assert projection.repair_rounds == 3
    assert _reconstruct_repair_unit_counts(projection.repair_receipts) == {"dom_runtime": 3}
