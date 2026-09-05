from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from oryxenai.agents.code_generator.core.content_compiler import compile_content_module
from oryxenai.agents.code_generator.core.development_schemas import (
    DesignTokenSystemV3,
    ExecutionBindingV2,
    ExperienceBlueprintV3,
    GenerationCallReceipt,
    GenerationCannotComplete,
    GenerationChanges,
    GenerationProjection,
    GenerationResult,
    GenerationWorkUnitProjection,
    IntegrationFinding,
    IntegrationReviewV1,
    InteractionContract,
    RoutePlan,
    RouteShellV3,
    SitePlan,
    SourceCheckpoint,
    SourceDiagnostic,
    SourceFileChange,
    TypedTokenGroupV3,
    WorkGraph,
    WorkUnit,
)
from oryxenai.agents.code_generator.core.generation_orchestrator import (
    CodeGeneratorGenerationOrchestrator,
    GenerationError,
    _consume_repair_budget,
    _operation_context,
    _reset_generation_attempt_projection,
    _scoped_repair_plan,
    _scoped_resource_ledger,
    _shared_source_for_unit,
)
from oryxenai.agents.code_generator.core.ownership import (
    OwnershipError,
    validate_work_ownership,
)
from oryxenai.agents.code_generator.core.parallel_scheduler import execute_waves
from oryxenai.agents.code_generator.core.source_validation import SourceValidationError
from oryxenai.agents.code_generator.core.token_compiler import (
    TokenCompilationError,
    compile_generated_tokens,
)
from oryxenai.agents.code_generator.core.typescript_ast_audit import audit_typescript_source
from oryxenai.agents.code_generator.core.work_graph_compiler import compile_site_plan
from oryxenai.agents.code_generator.core.workspace import GenerationWorkspace


def _blueprint() -> ExperienceBlueprintV3:
    return ExperienceBlueprintV3(
        selected_concept_id="concept:editorial",
        narrative_arc="positioning to proof",
        tokens=DesignTokenSystemV3(
            colors={"legacy": "ignored-by-v3-compiler"},
            spacing_rem=[0.5, 1.0],
            radii_rem=[0.25],
            typography={
                "resource_slot_id": "font-slot",
                "family": "Local Sans",
                "weights": [400, 700],
                "body_size_min_rem": 1.0,
                "body_size_max_rem": 1.2,
                "heading_scale_ratio": 1.25,
                "body_line_height": 1.5,
            },
            container_max_px=1120,
            token_groups=[
                TypedTokenGroupV3(
                    group_id="color",
                    values={"ink": "#181818", "paper": "#f5f0e8"},
                ),
                TypedTokenGroupV3(
                    group_id="typography",
                    values={"body-family": '"Local Sans", sans-serif', "body-size": "1rem"},
                ),
                TypedTokenGroupV3(
                    group_id="spacing",
                    values={"2xl": "6", "section": "clamp(3rem, 10vw, 9rem)"},
                ),
                TypedTokenGroupV3(group_id="shape", values={"radius": "0.25rem"}),
                TypedTokenGroupV3(
                    group_id="motion",
                    values={"ease-standard": "cubic-bezier(0.2, 0.8, 0.2, 1)"},
                ),
            ],
        ),
        layout_regions=[],
        route_shells=[
            RouteShellV3(
                route_id="home",
                navigation_owner="composer",
                main_owner="composer",
                footer_owner="composer",
                h1_owner="composer",
                section_order=["hero"],
            )
        ],
        distinctive_moves=[
            {
                "move_id": "move:proof-rail",
                "route_id": "home",
                "thesis": "Proof stays adjacent to positioning.",
                "implementation_constraint": "Use an editorial split, not a card grid.",
            }
        ],
    )


def test_v3_tokens_are_typed_and_compile_without_scaffold_fallbacks() -> None:
    blueprint = _blueprint()
    compiled = compile_generated_tokens(blueprint)
    assert compiled == compile_generated_tokens(blueprint)
    assert "--color-ink: #181818;" in compiled
    assert "--spacing-2xl: 6;" in compiled
    assert "--spacing-section: clamp(3rem, 10vw, 9rem);" in compiled
    assert "var(,--" not in compiled
    with pytest.raises(TokenCompilationError):
        compile_generated_tokens(
            blueprint.model_copy(
                update={
                    "tokens": blueprint.tokens.model_copy(
                        update={
                            "token_groups": [
                                *blueprint.tokens.token_groups[:-1],
                                blueprint.tokens.token_groups[-1].model_copy(
                                    update={"values": {"ease": "var(--unknown, #fff)"}}
                                ),
                            ]
                        }
                    )
                }
            )
        )


def test_v3_font_tokens_ignore_materialized_directory_roots() -> None:
    compiled = compile_generated_tokens(
        _blueprint(),
        [
            ExecutionBindingV2(
                resource_slot_id="font-slot",
                route_id="home",
                category="font",
                purpose="approved typography",
                resolution_type="local_materialized",
                local_paths=[
                    "resources/fonts/font-id",
                    "resources/fonts/font-id/400-normal.woff2",
                    "resources/fonts/font-id/700-normal.woff2",
                    "resources/fonts/font-id/font.json",
                ],
                font_family="Local Sans",
            )
        ],
    )
    assert 'src: url("/resources/fonts/font-id");' not in compiled
    assert 'src: url("/resources/fonts/font-id/font.json")' not in compiled
    assert 'src: url("/resources/pack/fonts/font-id/400-normal.woff2")' in compiled
    assert 'src: url("/resources/pack/fonts/font-id/700-normal.woff2")' in compiled
    assert compiled.count('format("woff2")') == 2


def test_v3_schema_rejects_missing_typed_token_group() -> None:
    with pytest.raises(ValidationError):
        DesignTokenSystemV3(
            colors={},
            spacing_rem=[1.0],
            typography={
                "resource_slot_id": "font-slot",
                "family": "Local Sans",
                "weights": [400],
                "body_size_min_rem": 1.0,
                "body_size_max_rem": 1.1,
                "heading_scale_ratio": 1.2,
                "body_line_height": 1.5,
            },
            container_max_px=1000,
            token_groups=[],
        )


def test_design_neutral_compiler_assigns_shell_to_composer_only() -> None:
    plan = SitePlan(
        plan_id="v3",
        routes=[
            RoutePlan(
                route_id="home",
                path="/",
                section_ids=["hero"],
                responsive_outcome="stacked on mobile",
                reduced_motion_outcome="content remains visible",
                interaction_outcome="keyboard accessible",
            )
        ],
        interactions=[
            InteractionContract(
                interaction_id="interaction:home:contact",
                route_id="home",
                trigger="activate",
                outcome="opens contact",
                keyboard_behavior="Enter activates",
                reduced_motion_behavior="no motion required",
            )
        ],
        experience_blueprint=_blueprint(),
    )
    compiled = compile_site_plan(
        plan,
        {
            "site/contract.json": {
                "routes": [
                    {"route_id": "home", "storage_key": "home", "section_sequence": ["hero"]}
                ]
            },
            "execution/contract.json": {"slots": []},
        },
    )
    batch = next(unit for unit in compiled.work_graph.units if unit.kind == "route_batch")
    composer = next(unit for unit in compiled.work_graph.units if unit.kind == "route_compose")
    assert all("/sections/" in path for path in batch.owns_paths)
    assert batch.owns_route_shell is False
    assert composer.owns_route_shell is True
    assert composer.interaction_ids == ["interaction:home:contact"]
    assert "src/content/generated-content.ts" in compiled.work_graph.units[0].owns_paths


def test_ownership_rejects_duplicate_interaction_owner() -> None:
    plan = SitePlan(
        plan_id="ownership",
        routes=[],
        interactions=[
            InteractionContract(
                interaction_id="interaction:one",
                trigger="activate",
                outcome="works",
                keyboard_behavior="Enter",
                reduced_motion_behavior="static",
            )
        ],
        work_graph=WorkGraph(
            units=[
                WorkUnit(unit_id="a", kind="foundation", interaction_ids=["interaction:one"]),
                WorkUnit(unit_id="b", kind="foundation", interaction_ids=["interaction:one"]),
            ]
        ),
    )
    with pytest.raises(OwnershipError, match="exactly one"):
        validate_work_ownership(plan)


def test_content_compiler_is_stable_and_route_addressable() -> None:
    content = [{"route_id": "home", "sections": [{"section_id": "hero", "copy": "Approved"}]}]
    compiled = compile_content_module(content)
    assert "Approved" in compiled
    assert "contentForRoute" in compiled
    assert compiled == compile_content_module(content)


def test_generation_context_reads_only_trusted_and_assigned_source(tmp_path) -> None:
    repo = tmp_path / "repo"
    for relative in (
        "src/app/ResourceUrl.ts",
        "src/components/generated/SharedSystems.tsx",
        "src/design/generated-tokens.css",
    ):
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(relative, encoding="utf-8")
    content = repo / "src/content/generated-content.ts"
    content.parent.mkdir(parents=True, exist_ok=True)
    content.write_text(
        'export const CONTENT_INDEX = [{"content_id": "home.hero.title", "value": "Approved"}] as const;\n'
        'export function contentValue(contentId: typeof CONTENT_INDEX[number]["content_id"]): string { return contentId; }\n',
        encoding="utf-8",
    )
    component = repo / "src/generated/resources/pack/components/demo/source/index.tsx"
    component.parent.mkdir(parents=True, exist_ok=True)
    component.write_text("export const Demo = () => null;", encoding="utf-8")

    unit = WorkUnit(
        unit_id="route-home-batch",
        kind="route_batch",
        route_id="home",
        route_ids=["home"],
        resource_slot_ids=["component-slot"],
    )
    plan = SitePlan(
        plan_id="context-scope",
        routes=[],
        work_graph=WorkGraph(
            units=[
                WorkUnit(
                    unit_id="foundation",
                    kind="foundation",
                    owns_paths=["src/content/generated-content.ts"],
                ),
                unit,
            ]
        ),
    )
    projections = {
        "execution/contract.json": {
            "slots": [
                {
                    "resource_slot_id": "component-slot",
                    "resolution": {
                        "local_paths": ["resources/components/demo/source"],
                    },
                }
            ]
        }
    }

    shared = _shared_source_for_unit(plan, projections, unit, repo)

    assert "src/content/generated-content.ts" in shared
    assert "contentValue" in shared["src/content/generated-content.ts"]
    assert '"value": "Approved"' not in shared["src/content/generated-content.ts"]
    assert "src/app/ResourceUrl.ts" in shared
    assert "src/generated/resources/pack/components/demo/source/index.tsx" in shared

    composer = unit.model_copy(update={"unit_id": "route-home-compose", "kind": "route_compose"})
    composer_shared = _shared_source_for_unit(plan, projections, composer, repo)
    assert "src/content/generated-content.ts" not in composer_shared


def test_resource_context_drops_historical_ledger_payloads() -> None:
    unit = WorkUnit(unit_id="composer", kind="route_compose", route_id="home")
    scoped = _scoped_resource_ledger(
        {
            "schema_version": "ledger-v1",
            "ledger_hash": "ledger-hash",
            "active_bindings": [{"binding_id": "binding-1"}],
            "receipts": [{"receipt_id": "receipt-1"}],
            "requests": [{"request_id": "request-1"}],
        },
        unit,
    )

    assert scoped == {"schema_version": "ledger-v1", "ledger_hash": "ledger-hash"}


def test_repair_context_preserves_v4_envelope_discriminator() -> None:
    scoped = _scoped_repair_plan(
        {
            "plan_id": "plan-1",
            "routes": [{"route_id": "home"}],
            "work_graph": {"units": ["generation-only"]},
            "tokens": {"large": "generation-only"},
            "experience_blueprint": {
                "schema_version": "code-generator-experience-blueprint-v4",
                "narrative_arc": "approved narrative",
                "distinctive_moves": [{"move_id": "move-1"}],
                "resource_placements": [{"resource_slot_id": "slot-1"}],
                "motion_beats": [{"motion_id": "motion-1"}],
                "section_regions": [{"region_id": "generation-only"}],
            },
        }
    )

    assert scoped["experience_blueprint"]["schema_version"].endswith("-v4")
    assert "work_graph" not in scoped
    assert "tokens" not in scoped
    assert "section_regions" not in scoped["experience_blueprint"]


def test_route_operation_context_scopes_inventory_and_candidate_source(tmp_path) -> None:
    repo = tmp_path / "repo"
    owned = repo / "src/routes/home/sections/hero.tsx"
    owned.parent.mkdir(parents=True, exist_ok=True)
    owned.write_text("export default function Hero() { return null; }", encoding="utf-8")
    unrelated = repo / "src/routes/home/sections/unrelated.tsx"
    unrelated.write_text("export default function Unrelated() { return null; }", encoding="utf-8")

    workspace = GenerationWorkspace(
        tmp_path / "workspace", tmp_path / "input", tmp_path / "checkpoints"
    )
    workspace.repo_dir = repo
    candidate = workspace.root / "candidate-route-home"
    candidate_owned = candidate / "src/routes/home/sections/hero.tsx"
    candidate_owned.parent.mkdir(parents=True, exist_ok=True)
    candidate_owned.write_text("candidate source", encoding="utf-8")
    (candidate / "src/routes/home/sections/unrelated.tsx").write_text(
        "unrelated candidate source", encoding="utf-8"
    )

    unit = WorkUnit(
        unit_id="route-home",
        kind="route_batch",
        route_id="home",
        route_ids=["home"],
        section_ids=["hero"],
        owns_paths=[
            "src/routes/home/sections/hero.tsx",
            "src/routes/home/sections/hero.css",
        ],
    )
    plan = SitePlan(
        plan_id="context-scope",
        routes=[
            RoutePlan(
                route_id="home",
                path="/",
                section_ids=["hero"],
                responsive_outcome="stacked",
                reduced_motion_outcome="static",
                interaction_outcome="keyboard accessible",
            )
        ],
        work_graph=WorkGraph(units=[unit]),
    )
    context = _operation_context(
        plan=plan,
        projections={
            "site/contract.json": {
                "routes": [{"route_id": "home", "path": "/", "storage_key": "home"}],
                "criteria": [],
                "facts": [],
                "public_content": [],
            },
            "design/visual-direction.json": {},
            "resources/ledger.json": {},
            "execution/contract.json": {},
        },
        unit=unit,
        operation="route_batch",
        checkpoint=None,
        workspace=workspace,
        role_profile="openai_luna",
        output_ceiling=2_000_000,
        diagnostics=[],
        repair_round=0,
    )

    assert context["existing_files"] == ["src/routes/home/sections/hero.tsx"]
    assert context["previous_attempt_files"] == {
        "src/routes/home/sections/hero.tsx": "candidate source"
    }

    owned_css = repo / "src/routes/home/sections/hero.css"
    owned_css.write_text("current companion styles", encoding="utf-8")
    repair_workspace = GenerationWorkspace(
        tmp_path / "repair-workspace", tmp_path / "input", tmp_path / "checkpoints"
    )
    repair_workspace.repo_dir = repo
    repair_context = _operation_context(
        plan=plan,
        projections={
            "site/contract.json": {
                "routes": [{"route_id": "home", "path": "/", "storage_key": "home"}],
                "criteria": [],
                "facts": [],
                "public_content": [],
            },
            "design/visual-direction.json": {},
            "resources/ledger.json": {},
            "execution/contract.json": {},
        },
        unit=unit,
        operation="repair",
        checkpoint=None,
        workspace=repair_workspace,
        role_profile="openai_luna",
        output_ceiling=2_000_000,
        diagnostics=[],
        repair_round=1,
    )

    assert repair_context["previous_attempt_files"] == {
        "src/routes/home/sections/hero.css": "current companion styles",
        "src/routes/home/sections/hero.tsx": "export default function Hero() { return null; }",
    }
    assert "work_graph" not in repair_context["plan"]
    assert "section_regions" not in repair_context["plan"]
    assert "assets" not in repair_context["visual_direction"]

    partial_repair_context = _operation_context(
        plan=plan,
        projections={
            "site/contract.json": {
                "routes": [{"route_id": "home", "path": "/", "storage_key": "home"}],
                "criteria": [],
                "facts": [],
                "public_content": [],
            },
            "design/visual-direction.json": {},
            "resources/ledger.json": {},
            "execution/contract.json": {},
        },
        unit=unit,
        operation="repair",
        checkpoint=None,
        workspace=repair_workspace,
        role_profile="openai_luna",
        output_ceiling=2_000_000,
        diagnostics=[
            SourceDiagnostic(
                diagnostic_id="diagnostic-motion",
                code="SOURCE_ROUTE_BATCH_MOTION_INVALID",
                group="source_contract",
                owner="generator",
                phase="source_generation",
                normalized_message="motion mismatch",
                file="src/routes/home/sections/hero.tsx",
                work_unit_id=unit.unit_id,
                fingerprint="motion",
            )
        ],
        repair_round=2,
        rejected_attempt_files={"src/routes/home/sections/hero.tsx": "rejected partial correction"},
    )

    assert partial_repair_context["previous_attempt_files"] == {
        "src/routes/home/sections/hero.css": "current companion styles",
        "src/routes/home/sections/hero.tsx": "rejected partial correction",
    }

    foreign_diagnostic_context = _operation_context(
        plan=plan,
        projections={
            "site/contract.json": {
                "routes": [{"route_id": "home", "path": "/", "storage_key": "home"}],
                "criteria": [],
                "facts": [],
                "public_content": [],
            },
            "design/visual-direction.json": {},
            "resources/ledger.json": {},
            "execution/contract.json": {},
        },
        unit=unit,
        operation="repair",
        checkpoint=None,
        workspace=repair_workspace,
        role_profile="openai_luna",
        output_ceiling=2_000_000,
        diagnostics=[
            SourceDiagnostic(
                diagnostic_id="diagnostic-foreign",
                code="SOURCE_CSS_INVALID_LENGTH",
                group="source_contract",
                owner="generator",
                phase="source_generation",
                normalized_message="foreign batch failure",
                file="src/routes/home/sections/unrelated.tsx",
                work_unit_id="route-home-batch-2",
                fingerprint="foreign",
            )
        ],
        repair_round=2,
    )

    assert foreign_diagnostic_context["previous_attempt_files"] == {
        "src/routes/home/sections/hero.css": "current companion styles",
        "src/routes/home/sections/hero.tsx": "export default function Hero() { return null; }",
    }

    selected_work_css = repo / "src/routes/home/sections/selected-work.css"
    selected_work_css.write_text("current selected work styles", encoding="utf-8")
    polish_unit = unit.model_copy(
        update={
            "owns_paths": [
                *unit.owns_paths,
                "src/routes/home/sections/selected-work.css",
            ]
        }
    )
    integration_polish_context = _operation_context(
        plan=plan,
        projections={
            "site/contract.json": {
                "routes": [{"route_id": "home", "path": "/", "storage_key": "home"}],
                "criteria": [],
                "facts": [],
                "public_content": [],
            },
            "design/visual-direction.json": {},
            "resources/ledger.json": {},
            "execution/contract.json": {},
        },
        unit=polish_unit,
        operation="repair",
        checkpoint=None,
        workspace=repair_workspace,
        role_profile="openai_luna",
        output_ceiling=2_000_000,
        diagnostics=[
            SourceDiagnostic(
                diagnostic_id="integration-compound-finding",
                code="V4_TYPOGRAPHY_WEIGHT_MISMATCH",
                group="source_contract",
                owner="generator",
                phase="integration_review",
                normalized_message="Correct hero and selected-work title weights.",
                file="src/routes/home/sections/hero.css",
                work_unit_id=unit.unit_id,
                fingerprint="integration-compound",
            )
        ],
        repair_round=1,
    )

    assert integration_polish_context["previous_attempt_files"] == {
        "src/routes/home/sections/hero.css": "current companion styles",
        "src/routes/home/sections/hero.tsx": "export default function Hero() { return null; }",
        "src/routes/home/sections/selected-work.css": "current selected work styles",
    }

    owned.unlink()
    rejected_context = _operation_context(
        plan=plan,
        projections={
            "site/contract.json": {
                "routes": [{"route_id": "home", "path": "/", "storage_key": "home"}],
                "criteria": [],
                "facts": [],
                "public_content": [],
            },
            "design/visual-direction.json": {},
            "resources/ledger.json": {},
            "execution/contract.json": {},
        },
        unit=unit,
        operation="repair",
        checkpoint=None,
        workspace=repair_workspace,
        role_profile="openai_luna",
        output_ceiling=2_000_000,
        diagnostics=[
            SourceDiagnostic(
                diagnostic_id="diagnostic-coverage",
                code="SOURCE_COVERAGE_MISMATCH",
                group="source_contract",
                owner="generator",
                phase="source_generation",
                normalized_message="coverage mismatch",
                file="src/routes/home/sections/hero.tsx",
                work_unit_id=unit.unit_id,
                fingerprint="coverage",
            )
        ],
        repair_round=1,
        rejected_attempt_files={
            "src/routes/home/sections/hero.tsx": "rejected response source",
            "src/routes/home/sections/hero.css": "rejected response styles",
            "src/routes/home/sections/unrelated.tsx": "unrelated rejected source",
        },
    )

    assert rejected_context["existing_files"] == ["src/routes/home/sections/hero.css"]
    assert rejected_context["previous_attempt_files"] == {
        "src/routes/home/sections/hero.css": "rejected response styles",
        "src/routes/home/sections/hero.tsx": "rejected response source",
    }


@pytest.mark.asyncio
async def test_run_unit_supplies_rejected_result_source_to_repair(tmp_path, monkeypatch) -> None:
    workspace = GenerationWorkspace(
        tmp_path / "workspace", tmp_path / "input", tmp_path / "checkpoints"
    )
    workspace.repo_dir.mkdir(parents=True)
    workspace.ledger_dir.mkdir(parents=True)
    owned_path = "src/routes/home/sections/hero.tsx"
    unit = WorkUnit(
        unit_id="route-home",
        kind="route",
        route_id="home",
        route_ids=["home"],
        section_ids=["hero"],
        owns_paths=[owned_path],
    )
    plan = SitePlan(
        plan_id="rejected-source-repair",
        routes=[
            RoutePlan(
                route_id="home",
                path="/",
                section_ids=["hero"],
                responsive_outcome="stacked",
                reduced_motion_outcome="static",
                interaction_outcome="keyboard accessible",
            )
        ],
        work_graph=WorkGraph(units=[unit]),
    )
    projections = {
        "site/contract.json": {
            "routes": [{"route_id": "home", "path": "/", "storage_key": "home"}],
            "criteria": [],
            "facts": [],
            "public_content": [],
        },
        "design/visual-direction.json": {},
        "resources/ledger.json": {},
        "execution/contract.json": {},
    }
    generated_source = "export default function Hero() { return <section />; }"
    result = GenerationResult(
        operation_id="route_batch:route-home",
        based_on_context_receipt="test-context",
        mode="changes",
        changes=GenerationChanges(
            files=[
                SourceFileChange(
                    path=owned_path,
                    operation="create",
                    complete_utf8_content=generated_source,
                )
            ]
        ),
    )
    contexts: list[dict[str, object]] = []
    orchestrator = CodeGeneratorGenerationOrchestrator()

    async def model_result(**kwargs):
        contexts.append(kwargs["context"])
        index = len(contexts)
        return result, GenerationCallReceipt(
            receipt_id=f"call-{index}",
            operation_id=str(kwargs["operation"]),
            idempotency_key=f"key-{index}",
            context_receipt_hash=str(kwargs["context_receipt"].context_hash),
            result_hash=f"result-{index}",
            profile=str(kwargs["role_profile"]),
        )

    apply_count = 0

    def apply_changes(**_kwargs) -> None:
        nonlocal apply_count
        apply_count += 1
        if apply_count == 1:
            raise SourceValidationError(
                "SOURCE_COVERAGE_MISMATCH",
                "The v4 content coverage array does not exactly match its work unit.",
            )

    async def no_diagnostics(*_args, **_kwargs):
        return []

    async def validate_run(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(orchestrator, "_model_result", model_result)
    monkeypatch.setattr(orchestrator, "_apply_changes", apply_changes)
    monkeypatch.setattr(orchestrator, "_validate_run", validate_run)
    monkeypatch.setattr(
        "oryxenai.agents.code_generator.core.generation_orchestrator.run_source_checks",
        no_diagnostics,
    )

    checkpoint = SourceCheckpoint(
        checkpoint_id="checkpoint-test",
        checkpoint_hash="checkpoint-hash",
        stored_relative_path="checkpoints/test",
        source_manifest_hash="manifest-hash",
        file_count=1,
        total_bytes=len(generated_source),
        work_unit_id=unit.unit_id,
        accepted_at="2026-08-29T00:00:00+00:00",
    )
    checkpoint_store = SimpleNamespace(accept=lambda **_kwargs: checkpoint)
    generation_config = SimpleNamespace(
        route_profile="route-profile",
        compose_profile="compose-profile",
        integration_profile="integration-profile",
        repair_profile="repair-profile",
        max_response_bytes=2_000_000,
        max_context_chars=170_000,
        max_request_rounds=1,
        max_source_bytes=2_000_000,
        max_repair_rounds_per_unit=2,
        max_repair_rounds_total=6,
    )
    projection = GenerationProjection(
        generation_id="generation-test",
        input_receipt_hash="input-hash",
        site_plan_hash="plan-hash",
        phase="generating_routes",
    )

    accepted = await orchestrator._run_unit(
        sessionmaker=None,
        run_id=uuid4(),
        settings=SimpleNamespace(code_generator_generation=generation_config),
        run=SimpleNamespace(run_mode="development"),
        plan=plan,
        projections=projections,
        workspace=workspace,
        checkpoint_store=checkpoint_store,
        projection=projection,
        unit=unit,
        checkpoint=None,
        allowed_packages=set(),
        public_text=set(),
        persist_projection=False,
    )

    assert accepted == checkpoint
    assert len(contexts) == 2
    assert contexts[0]["previous_attempt_files"] == {}
    assert contexts[1]["previous_attempt_files"] == {owned_path: generated_source}
    assert contexts[1]["operation"] == "repair"


@pytest.mark.asyncio
async def test_integration_polish_repairs_late_finding_through_third_rereview(
    tmp_path, monkeypatch
) -> None:
    workspace = GenerationWorkspace(
        tmp_path / "workspace", tmp_path / "input", tmp_path / "checkpoints"
    )
    workspace.repo_dir.mkdir(parents=True)
    workspace.ledger_dir.mkdir(parents=True)
    owned_path = "src/routes/home/index.tsx"
    source = workspace.repo_dir / owned_path
    source.parent.mkdir(parents=True)
    source.write_text("export default function Home() { return null; }", encoding="utf-8")
    unit = WorkUnit(
        unit_id="route-home",
        kind="route",
        route_id="home",
        route_ids=["home"],
        section_ids=["hero"],
        owns_paths=[owned_path],
    )
    plan = SitePlan(
        plan_id="three-round-polish",
        routes=[
            RoutePlan(
                route_id="home",
                path="/",
                section_ids=["hero"],
                responsive_outcome="stacked",
                reduced_motion_outcome="static",
                interaction_outcome="keyboard accessible",
            )
        ],
        work_graph=WorkGraph(units=[unit]),
    )
    projections = {
        "site/contract.json": {
            "routes": [{"route_id": "home", "path": "/", "storage_key": "home"}],
            "criteria": [],
            "facts": [],
            "public_content": [],
        },
        "design/visual-direction.json": {},
        "resources/ledger.json": {},
        "execution/contract.json": {},
    }

    def rejected_review(finding_id: str, code: str) -> IntegrationReviewV1:
        return IntegrationReviewV1(
            status="findings",
            findings=[
                IntegrationFinding(
                    finding_id=finding_id,
                    severity="blocking",
                    section_id=owned_path,
                    owner_work_unit_id=unit.unit_id,
                    code=code,
                    evidence="concrete source mismatch",
                    requested_outcome="correct the owned source",
                )
            ],
            distinctiveness_score=4,
            composition_score=4,
            typography_score=3,
            resource_fit_score=4,
            motion_score=4,
        )

    reviews = [
        rejected_review("finding-first", "FIRST_DEFECT"),
        rejected_review("finding-new", "NEW_REREVIEW_DEFECT"),
        rejected_review("finding-late", "LATE_REREVIEW_DEFECT"),
        IntegrationReviewV1(
            status="accepted",
            findings=[],
            distinctiveness_score=4,
            composition_score=4,
            typography_score=4,
            resource_fit_score=4,
            motion_score=4,
        ),
    ]
    review_rounds: list[int] = []
    repair_units: list[str] = []
    checkpoint_units: list[str] = []
    orchestrator = CodeGeneratorGenerationOrchestrator()

    async def integration_review(**kwargs):
        round_number = int(kwargs["round_number"])
        review_rounds.append(round_number)
        return reviews[round_number]

    async def model_result(**kwargs):
        repair_units.append(str(kwargs["unit_id"]))
        return (
            GenerationResult(
                operation_id=f"repair:{kwargs['unit_id']}",
                based_on_context_receipt=str(kwargs["context_receipt"].context_hash),
                mode="changes",
                changes=GenerationChanges(
                    files=[
                        SourceFileChange(
                            path=owned_path,
                            operation="replace",
                            complete_utf8_content=source.read_text(encoding="utf-8"),
                        )
                    ]
                ),
            ),
            GenerationCallReceipt(
                receipt_id=f"call-{len(repair_units)}",
                operation_id="repair",
                idempotency_key=f"repair-{len(repair_units)}",
                context_receipt_hash=str(kwargs["context_receipt"].context_hash),
                result_hash=f"result-{len(repair_units)}",
                profile="repair-profile",
            ),
        )

    async def no_diagnostics(*_args, **_kwargs):
        return []

    async def no_op(*_args, **_kwargs) -> None:
        return None

    def accept_checkpoint(**kwargs) -> SourceCheckpoint:
        checkpoint_units.append(str(kwargs["work_unit_id"]))
        index = len(checkpoint_units)
        return SourceCheckpoint(
            checkpoint_id=f"checkpoint-{index}",
            parent_checkpoint_hash=str(kwargs["parent_hash"]),
            checkpoint_hash=f"hash-{index}",
            stored_relative_path=f"checkpoints/{index}",
            source_manifest_hash=f"manifest-{index}",
            file_count=1,
            total_bytes=source.stat().st_size,
            work_unit_id=str(kwargs["work_unit_id"]),
            accepted_at="2026-08-30T00:00:00+00:00",
        )

    monkeypatch.setattr(orchestrator, "_integration_review", integration_review)
    monkeypatch.setattr(orchestrator, "_model_result", model_result)
    monkeypatch.setattr(orchestrator, "_apply_changes", lambda **_kwargs: None)
    monkeypatch.setattr(orchestrator, "_validate_run", no_op)
    monkeypatch.setattr(orchestrator, "_persist", no_op)
    monkeypatch.setattr(
        "oryxenai.agents.code_generator.core.generation_orchestrator.run_source_checks",
        no_diagnostics,
    )
    settings = SimpleNamespace(
        code_generator_generation=SimpleNamespace(
            repair_profile="repair-profile",
            max_response_bytes=2_000_000,
            max_context_chars=170_000,
            max_source_bytes=2_000_000,
            max_integration_polish_rounds=3,
        )
    )
    projection = GenerationProjection(
        generation_id="generation-polish",
        input_receipt_hash="input-hash",
        site_plan_hash="plan-hash",
        phase="integrating",
    )
    initial_checkpoint = SourceCheckpoint(
        checkpoint_id="checkpoint-initial",
        checkpoint_hash="hash-initial",
        stored_relative_path="checkpoints/initial",
        source_manifest_hash="manifest-initial",
        file_count=1,
        total_bytes=source.stat().st_size,
        work_unit_id=unit.unit_id,
        accepted_at="2026-08-30T00:00:00+00:00",
    )

    await orchestrator._review_and_polish(
        sessionmaker=None,
        run_id=uuid4(),
        settings=settings,
        run=SimpleNamespace(),
        plan=plan,
        projections=projections,
        workspace=workspace,
        projection=projection,
        checkpoint_store=SimpleNamespace(accept=accept_checkpoint),
        checkpoint=initial_checkpoint,
        allowed_packages=set(),
        public_text=set(),
    )

    assert review_rounds == [0, 1, 2, 3]
    assert repair_units == [
        "route-home-integration-polish",
        "route-home-integration-polish-2",
        "route-home-integration-polish-3",
    ]
    assert checkpoint_units == repair_units


@pytest.mark.asyncio
async def test_integration_polish_survives_cannot_complete_and_reaches_unresolved(
    tmp_path, monkeypatch
) -> None:
    """Regression test for the 2026-09-05 live-discovered bug: an owner-scoped
    polish repair call reporting cannot_complete (repair_source.md's honest
    escape hatch) used to raise INTEGRATION_POLISH_INCOMPLETE and kill the
    whole run on the very first such response, with zero retry -- even
    though the outer polish-round loop is already bounded specifically to
    give a different round another try (the same class of gap Fix A closed
    for the final-verification-gate's own post-repair rejection). It must
    now leave that owner's files untouched for the round and let the
    bounded loop continue, landing on the pre-existing
    INTEGRATION_REVIEW_UNRESOLVED terminal state once rounds are exhausted,
    never INTEGRATION_POLISH_INCOMPLETE.

    Also a regression test for a second, later live finding (2026-09-05,
    run 93d4d3c4-...): the same STILL_BROKEN code recurring across rounds
    used to get an identical, doomed repair call every single round with no
    memory of the previous round's cannot_complete. The review here returns
    the same code every round on purpose -- once round 1 answers "no", round
    2 must not spend another repair call re-asking the identical question."""
    workspace = GenerationWorkspace(
        tmp_path / "workspace", tmp_path / "input", tmp_path / "checkpoints"
    )
    workspace.repo_dir.mkdir(parents=True)
    workspace.ledger_dir.mkdir(parents=True)
    owned_path = "src/routes/home/index.tsx"
    source = workspace.repo_dir / owned_path
    source.parent.mkdir(parents=True)
    source.write_text("export default function Home() { return null; }", encoding="utf-8")
    unit = WorkUnit(
        unit_id="route-home",
        kind="route",
        route_id="home",
        route_ids=["home"],
        section_ids=["hero"],
        owns_paths=[owned_path],
    )
    plan = SitePlan(
        plan_id="cannot-complete-polish",
        routes=[
            RoutePlan(
                route_id="home",
                path="/",
                section_ids=["hero"],
                responsive_outcome="stacked",
                reduced_motion_outcome="static",
                interaction_outcome="keyboard accessible",
            )
        ],
        work_graph=WorkGraph(units=[unit]),
    )
    projections = {
        "site/contract.json": {
            "routes": [{"route_id": "home", "path": "/", "storage_key": "home"}],
            "criteria": [],
            "facts": [],
            "public_content": [],
        },
        "design/visual-direction.json": {},
        "resources/ledger.json": {},
        "execution/contract.json": {},
    }

    def rejected_review(finding_id: str) -> IntegrationReviewV1:
        return IntegrationReviewV1(
            status="findings",
            findings=[
                IntegrationFinding(
                    finding_id=finding_id,
                    severity="blocking",
                    section_id=owned_path,
                    owner_work_unit_id=unit.unit_id,
                    code="STILL_BROKEN",
                    evidence="concrete source mismatch",
                    requested_outcome="correct the owned source",
                )
            ],
            distinctiveness_score=4,
            composition_score=4,
            typography_score=3,
            resource_fit_score=4,
            motion_score=4,
        )

    review_rounds: list[int] = []
    repair_units: list[str] = []
    orchestrator = CodeGeneratorGenerationOrchestrator()

    async def integration_review(**kwargs):
        round_number = int(kwargs["round_number"])
        review_rounds.append(round_number)
        return rejected_review(f"finding-round-{round_number}")

    async def model_result(**kwargs):
        repair_units.append(str(kwargs["unit_id"]))
        return (
            GenerationResult(
                operation_id=f"repair:{kwargs['unit_id']}",
                based_on_context_receipt=str(kwargs["context_receipt"].context_hash),
                mode="cannot_complete",
                cannot_complete=GenerationCannotComplete(
                    code="STILL_BROKEN",
                    safe_reason=(
                        "The requested correction is outside this unit's bounded authority."
                    ),
                ),
            ),
            GenerationCallReceipt(
                receipt_id=f"call-{len(repair_units)}",
                operation_id="repair",
                idempotency_key=f"repair-{len(repair_units)}",
                context_receipt_hash=str(kwargs["context_receipt"].context_hash),
                result_hash=f"result-{len(repair_units)}",
                profile="repair-profile",
            ),
        )

    async def no_diagnostics(*_args, **_kwargs):
        return []

    async def no_op(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(orchestrator, "_integration_review", integration_review)
    monkeypatch.setattr(orchestrator, "_model_result", model_result)
    monkeypatch.setattr(orchestrator, "_apply_changes", lambda **_kwargs: None)
    monkeypatch.setattr(orchestrator, "_validate_run", no_op)
    monkeypatch.setattr(orchestrator, "_persist", no_op)
    monkeypatch.setattr(
        "oryxenai.agents.code_generator.core.generation_orchestrator.run_source_checks",
        no_diagnostics,
    )
    settings = SimpleNamespace(
        code_generator_generation=SimpleNamespace(
            repair_profile="repair-profile",
            max_response_bytes=2_000_000,
            max_context_chars=170_000,
            max_source_bytes=2_000_000,
            max_integration_polish_rounds=2,
        )
    )
    projection = GenerationProjection(
        generation_id="generation-cannot-complete-polish",
        input_receipt_hash="input-hash",
        site_plan_hash="plan-hash",
        phase="integrating",
    )
    initial_checkpoint = SourceCheckpoint(
        checkpoint_id="checkpoint-initial",
        checkpoint_hash="hash-initial",
        stored_relative_path="checkpoints/initial",
        source_manifest_hash="manifest-initial",
        file_count=1,
        total_bytes=source.stat().st_size,
        work_unit_id=unit.unit_id,
        accepted_at="2026-09-05T00:00:00+00:00",
    )

    with pytest.raises(GenerationError) as excinfo:
        await orchestrator._review_and_polish(
            sessionmaker=None,
            run_id=uuid4(),
            settings=settings,
            run=SimpleNamespace(),
            plan=plan,
            projections=projections,
            workspace=workspace,
            projection=projection,
            checkpoint_store=SimpleNamespace(accept=lambda **_kwargs: initial_checkpoint),
            checkpoint=initial_checkpoint,
            allowed_packages=set(),
            public_text=set(),
        )

    assert excinfo.value.code == "INTEGRATION_REVIEW_UNRESOLVED"
    # The review itself still runs every round -- it must always reflect the
    # tree's current state -- but round 2 must not re-attempt the owner: its
    # only finding (STILL_BROKEN) already returned cannot_complete in round
    # 1, so a fresh, identical repair call would be spending budget on a
    # question already answered "no" once.
    assert review_rounds == [0, 1, 2]
    assert repair_units == ["route-home-integration-polish"]


@pytest.mark.asyncio
async def test_integration_polish_still_attempts_a_genuinely_new_finding_code(
    tmp_path, monkeypatch
) -> None:
    """Companion to the dedup regression above: skipping a re-attempt is
    scoped to the exact finding code that already returned cannot_complete,
    never the whole owner. A different code for the same owner next round is
    a genuinely new question and must still get its fair first attempt."""
    workspace = GenerationWorkspace(
        tmp_path / "workspace", tmp_path / "input", tmp_path / "checkpoints"
    )
    workspace.repo_dir.mkdir(parents=True)
    workspace.ledger_dir.mkdir(parents=True)
    owned_path = "src/routes/home/index.tsx"
    source = workspace.repo_dir / owned_path
    source.parent.mkdir(parents=True)
    source.write_text("export default function Home() { return null; }", encoding="utf-8")
    unit = WorkUnit(
        unit_id="route-home",
        kind="route",
        route_id="home",
        route_ids=["home"],
        section_ids=["hero"],
        owns_paths=[owned_path],
    )
    plan = SitePlan(
        plan_id="new-finding-polish",
        routes=[
            RoutePlan(
                route_id="home",
                path="/",
                section_ids=["hero"],
                responsive_outcome="stacked",
                reduced_motion_outcome="static",
                interaction_outcome="keyboard accessible",
            )
        ],
        work_graph=WorkGraph(units=[unit]),
    )
    projections = {
        "site/contract.json": {
            "routes": [{"route_id": "home", "path": "/", "storage_key": "home"}],
            "criteria": [],
            "facts": [],
            "public_content": [],
        },
        "design/visual-direction.json": {},
        "resources/ledger.json": {},
        "execution/contract.json": {},
    }

    def review_for_round(round_number: int) -> IntegrationReviewV1:
        if round_number == 2:
            return IntegrationReviewV1(
                status="accepted",
                findings=[],
                distinctiveness_score=4,
                composition_score=4,
                typography_score=4,
                resource_fit_score=4,
                motion_score=4,
            )
        code = "STILL_BROKEN" if round_number == 0 else "NEW_ISSUE"
        return IntegrationReviewV1(
            status="findings",
            findings=[
                IntegrationFinding(
                    finding_id=f"finding-round-{round_number}",
                    severity="blocking",
                    section_id=owned_path,
                    owner_work_unit_id=unit.unit_id,
                    code=code,
                    evidence="concrete source mismatch",
                    requested_outcome="correct the owned source",
                )
            ],
            distinctiveness_score=4,
            composition_score=4,
            typography_score=3,
            resource_fit_score=4,
            motion_score=4,
        )

    review_rounds: list[int] = []
    repair_units: list[str] = []
    orchestrator = CodeGeneratorGenerationOrchestrator()

    async def integration_review(**kwargs):
        round_number = int(kwargs["round_number"])
        review_rounds.append(round_number)
        return review_for_round(round_number)

    async def model_result(**kwargs):
        repair_units.append(str(kwargs["unit_id"]))
        # Round 1's attempt (STILL_BROKEN) cannot complete; round 2's
        # attempt (NEW_ISSUE) succeeds.
        if len(repair_units) == 1:
            return (
                GenerationResult(
                    operation_id=f"repair:{kwargs['unit_id']}",
                    based_on_context_receipt=str(kwargs["context_receipt"].context_hash),
                    mode="cannot_complete",
                    cannot_complete=GenerationCannotComplete(
                        code="STILL_BROKEN",
                        safe_reason="Outside this unit's bounded authority.",
                    ),
                ),
                GenerationCallReceipt(
                    receipt_id=f"call-{len(repair_units)}",
                    operation_id="repair",
                    idempotency_key=f"repair-{len(repair_units)}",
                    context_receipt_hash=str(kwargs["context_receipt"].context_hash),
                    result_hash=f"result-{len(repair_units)}",
                    profile="repair-profile",
                ),
            )
        return (
            GenerationResult(
                operation_id=f"repair:{kwargs['unit_id']}",
                based_on_context_receipt=str(kwargs["context_receipt"].context_hash),
                mode="changes",
                changes=GenerationChanges(
                    files=[
                        SourceFileChange(
                            path=owned_path,
                            operation="replace",
                            complete_utf8_content=(
                                "export default function Home() { return null; }"
                            ),
                        )
                    ]
                ),
            ),
            GenerationCallReceipt(
                receipt_id=f"call-{len(repair_units)}",
                operation_id="repair",
                idempotency_key=f"repair-{len(repair_units)}",
                context_receipt_hash=str(kwargs["context_receipt"].context_hash),
                result_hash=f"result-{len(repair_units)}",
                profile="repair-profile",
            ),
        )

    async def no_diagnostics(*_args, **_kwargs):
        return []

    async def no_op(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(orchestrator, "_integration_review", integration_review)
    monkeypatch.setattr(orchestrator, "_model_result", model_result)
    monkeypatch.setattr(orchestrator, "_apply_changes", lambda **_kwargs: None)
    monkeypatch.setattr(orchestrator, "_validate_run", no_op)
    monkeypatch.setattr(orchestrator, "_persist", no_op)
    monkeypatch.setattr(
        "oryxenai.agents.code_generator.core.generation_orchestrator.run_source_checks",
        no_diagnostics,
    )
    settings = SimpleNamespace(
        code_generator_generation=SimpleNamespace(
            repair_profile="repair-profile",
            max_response_bytes=2_000_000,
            max_context_chars=170_000,
            max_source_bytes=2_000_000,
            max_integration_polish_rounds=2,
        )
    )
    projection = GenerationProjection(
        generation_id="generation-new-finding-polish",
        input_receipt_hash="input-hash",
        site_plan_hash="plan-hash",
        phase="integrating",
    )
    initial_checkpoint = SourceCheckpoint(
        checkpoint_id="checkpoint-initial",
        checkpoint_hash="hash-initial",
        stored_relative_path="checkpoints/initial",
        source_manifest_hash="manifest-initial",
        file_count=1,
        total_bytes=source.stat().st_size,
        work_unit_id=unit.unit_id,
        accepted_at="2026-09-05T00:00:00+00:00",
    )

    await orchestrator._review_and_polish(
        sessionmaker=None,
        run_id=uuid4(),
        settings=settings,
        run=SimpleNamespace(),
        plan=plan,
        projections=projections,
        workspace=workspace,
        projection=projection,
        checkpoint_store=SimpleNamespace(accept=lambda **_kwargs: initial_checkpoint),
        checkpoint=initial_checkpoint,
        allowed_packages=set(),
        public_text=set(),
    )

    assert review_rounds == [0, 1, 2]
    # Both rounds spent a repair call: STILL_BROKEN in round 1, then the
    # different NEW_ISSUE code in round 2 -- a new code is never suppressed
    # by an unrelated code's earlier cannot_complete for the same owner.
    assert repair_units == ["route-home-integration-polish", "route-home-integration-polish-2"]


@pytest.mark.asyncio
async def test_integration_polish_repairs_malformed_source_before_checkpoint(
    tmp_path, monkeypatch
) -> None:
    workspace = GenerationWorkspace(
        tmp_path / "workspace", tmp_path / "input", tmp_path / "checkpoints"
    )
    workspace.repo_dir.mkdir(parents=True)
    workspace.ledger_dir.mkdir(parents=True)
    owned_path = "src/routes/home/index.tsx"
    source = workspace.repo_dir / owned_path
    source.parent.mkdir(parents=True)
    valid_source = "export default function Home() { return <main />; }\n"
    malformed_source = 'import { useState } from "react";\n'
    source.write_text(valid_source, encoding="utf-8")
    unit = WorkUnit(
        unit_id="route-home",
        kind="route",
        route_id="home",
        route_ids=["home"],
        section_ids=["hero"],
        owns_paths=[owned_path],
    )
    plan = SitePlan(
        plan_id="source-safe-polish",
        routes=[
            RoutePlan(
                route_id="home",
                path="/",
                section_ids=["hero"],
                responsive_outcome="stacked",
                reduced_motion_outcome="static",
                interaction_outcome="keyboard accessible",
            )
        ],
        work_graph=WorkGraph(units=[unit]),
    )
    projections = {
        "site/contract.json": {
            "routes": [{"route_id": "home", "path": "/", "storage_key": "home"}],
            "criteria": [],
            "facts": [],
            "public_content": [],
        },
        "design/visual-direction.json": {},
        "resources/ledger.json": {},
        "execution/contract.json": {},
    }
    finding = IntegrationFinding(
        finding_id="finding-polish",
        severity="blocking",
        section_id=owned_path,
        owner_work_unit_id=unit.unit_id,
        code="COMPOSITION_DEFECT",
        evidence="concrete source mismatch",
        requested_outcome="correct the owned source",
    )
    reviews = [
        IntegrationReviewV1(
            status="findings",
            findings=[finding],
            distinctiveness_score=4,
            composition_score=3,
            typography_score=4,
            resource_fit_score=4,
            motion_score=4,
        ),
        IntegrationReviewV1(
            status="accepted",
            findings=[],
            distinctiveness_score=4,
            composition_score=4,
            typography_score=4,
            resource_fit_score=4,
            motion_score=4,
        ),
    ]
    contexts: list[dict[str, object]] = []
    repair_units: list[str] = []
    checkpoint_units: list[str] = []
    orchestrator = CodeGeneratorGenerationOrchestrator()

    async def integration_review(**kwargs):
        return reviews[int(kwargs["round_number"])]

    async def model_result(**kwargs):
        contexts.append(dict(kwargs["context"]))
        repair_units.append(str(kwargs["unit_id"]))
        generated = malformed_source if len(repair_units) == 1 else valid_source
        return (
            GenerationResult(
                operation_id=f"repair:{kwargs['unit_id']}",
                based_on_context_receipt=str(kwargs["context_receipt"].context_hash),
                mode="changes",
                changes=GenerationChanges(
                    files=[
                        SourceFileChange(
                            path=owned_path,
                            operation="replace",
                            complete_utf8_content=generated,
                        )
                    ]
                ),
            ),
            GenerationCallReceipt(
                receipt_id=f"call-{len(repair_units)}",
                operation_id="repair",
                idempotency_key=f"repair-{len(repair_units)}",
                context_receipt_hash=str(kwargs["context_receipt"].context_hash),
                result_hash=f"result-{len(repair_units)}",
                profile="repair-profile",
            ),
        )

    def apply_changes(**kwargs) -> None:
        change = kwargs["changes"].files[0]
        source.write_text(change.complete_utf8_content, encoding="utf-8")

    async def source_checks(*_args, **_kwargs):
        if source.read_text(encoding="utf-8") == malformed_source:
            return [
                SourceDiagnostic(
                    diagnostic_id="diagnostic-missing-export",
                    code="SOURCE_AST_AUDIT_FAILED",
                    group="source_contract",
                    owner="generator",
                    phase="source_generation",
                    normalized_message="The route module has no default export.",
                    file=owned_path,
                    work_unit_id=unit.unit_id,
                    fingerprint="missing-export",
                )
            ]
        return []

    async def no_op(*_args, **_kwargs) -> None:
        return None

    def accept_checkpoint(**kwargs) -> SourceCheckpoint:
        assert source.read_text(encoding="utf-8") == valid_source
        checkpoint_units.append(str(kwargs["work_unit_id"]))
        return SourceCheckpoint(
            checkpoint_id="checkpoint-polished",
            parent_checkpoint_hash=str(kwargs["parent_hash"]),
            checkpoint_hash="hash-polished",
            stored_relative_path="checkpoints/polished",
            source_manifest_hash="manifest-polished",
            file_count=1,
            total_bytes=source.stat().st_size,
            work_unit_id=str(kwargs["work_unit_id"]),
            accepted_at="2026-08-31T00:00:00+00:00",
        )

    monkeypatch.setattr(orchestrator, "_integration_review", integration_review)
    monkeypatch.setattr(orchestrator, "_model_result", model_result)
    monkeypatch.setattr(orchestrator, "_apply_changes", apply_changes)
    monkeypatch.setattr(orchestrator, "_validate_run", no_op)
    monkeypatch.setattr(orchestrator, "_persist", no_op)
    monkeypatch.setattr(
        "oryxenai.agents.code_generator.core.generation_orchestrator.run_source_checks",
        source_checks,
    )
    settings = SimpleNamespace(
        code_generator_generation=SimpleNamespace(
            repair_profile="repair-profile",
            max_response_bytes=2_000_000,
            max_context_chars=170_000,
            max_source_bytes=2_000_000,
            max_integration_polish_rounds=1,
            max_repair_rounds_per_unit=2,
            max_repair_rounds_total=6,
        )
    )
    projection = GenerationProjection(
        generation_id="generation-source-safe-polish",
        input_receipt_hash="input-hash",
        site_plan_hash="plan-hash",
        phase="integrating",
    )
    initial_checkpoint = SourceCheckpoint(
        checkpoint_id="checkpoint-initial",
        checkpoint_hash="hash-initial",
        stored_relative_path="checkpoints/initial",
        source_manifest_hash="manifest-initial",
        file_count=1,
        total_bytes=source.stat().st_size,
        work_unit_id=unit.unit_id,
        accepted_at="2026-08-31T00:00:00+00:00",
    )

    await orchestrator._review_and_polish(
        sessionmaker=None,
        run_id=uuid4(),
        settings=settings,
        run=SimpleNamespace(),
        plan=plan,
        projections=projections,
        workspace=workspace,
        projection=projection,
        checkpoint_store=SimpleNamespace(accept=accept_checkpoint),
        checkpoint=initial_checkpoint,
        allowed_packages=set(),
        public_text=set(),
    )

    assert repair_units == [
        "route-home-integration-polish",
        "route-home-integration-polish-source-repair-1",
    ]
    assert contexts[1]["previous_attempt_files"] == {owned_path: malformed_source}
    assert checkpoint_units == ["route-home-integration-polish-source-repair-1"]
    assert projection.repair_budget_used == 1


def test_source_repair_budget_allows_third_round_and_reports_final_diagnostics() -> None:
    projection = GenerationProjection(
        generation_id="generation-budget",
        input_receipt_hash="input-hash",
        site_plan_hash="plan-hash",
        phase="generating_routes",
    )
    diagnostics = [
        SourceDiagnostic(
            diagnostic_id="diagnostic-final",
            code="SOURCE_IMAGE_PATH_INVALID",
            group="source_contract",
            owner="generator",
            phase="source_generation",
            normalized_message="The exact rendition path is missing.",
            work_unit_id="route-home",
            fingerprint="final-fingerprint",
        )
    ]
    settings = SimpleNamespace(
        code_generator_generation=SimpleNamespace(
            max_repair_rounds_per_unit=3,
            max_repair_rounds_total=6,
        )
    )

    for repair_round in range(3):
        _consume_repair_budget(
            projection,
            diagnostics,
            repair_round=repair_round,
            settings=settings,
        )

    assert projection.repair_budget_used == 3
    with pytest.raises(GenerationError) as exc_info:
        _consume_repair_budget(
            projection,
            diagnostics,
            repair_round=3,
            settings=settings,
        )
    assert exc_info.value.code == "SOURCE_REPAIR_EXHAUSTED"
    assert "SOURCE_IMAGE_PATH_INVALID" in exc_info.value.message
    assert "exact rendition path" in exc_info.value.message


def test_resumed_generation_clears_rejected_attempt_diagnostics_only() -> None:
    projection = GenerationProjection(
        generation_id="generation-1",
        input_receipt_hash="input",
        site_plan_hash="plan",
        phase="generating_routes",
        diagnostics=[
            SourceDiagnostic(
                diagnostic_id="diagnostic-stale",
                code="SOURCE_STALE",
                group="source_contract",
                owner="generator",
                phase="source_generation",
                normalized_message="stale",
                fingerprint="stale-fingerprint",
            )
        ],
        issues=[],
        work_units=[
            GenerationWorkUnitProjection(
                unit_id="route-home",
                kind="route_batch",
                status="checkpointed",
                diagnostics=["stale-diagnostic"],
            )
        ],
    )
    _reset_generation_attempt_projection(projection)

    assert projection.diagnostics == []
    assert projection.issues == []
    assert projection.work_units[0].diagnostics == []


def test_v3_typescript_audit_catches_route_contract_regressions(tmp_path) -> None:
    plan = SitePlan(
        plan_id="audit",
        routes=[
            RoutePlan(
                route_id="home",
                path="/",
                section_ids=["hero"],
                responsive_outcome="stacked on mobile",
                reduced_motion_outcome="static",
                interaction_outcome="keyboard accessible",
            )
        ],
        experience_blueprint=_blueprint(),
    )
    shared = """export function RouteShell() { return <main />; }
export function SectionAnchor() { return publicSectionUrl('/'); }
export function useDisclosure() { return { close: () => {} }; }
export function Disclosure() { return <button aria-expanded={false}>x</button>; }
export const keyboardBehavior = "Escape closes and returns focus";
"""
    route = """export function Home() { return <RouteShell routeId=\"home\"><h1>Home</h1>
<section data-content-id=\"hero\" data-distinctive-move-id=\"move:proof-rail\" id=\"hero\">
<button data-interaction-id=\"interaction:home:contact\">Open</button></section></RouteShell>; }
"""
    files = {
        "src/components/generated/SharedSystems.tsx": shared,
        "src/routes/home/index.tsx": route,
    }
    repo = tmp_path
    for relative, source in files.items():
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
    assert audit_typescript_source(repo, files=files, plan=plan) == []

    broken = route.replace('id="hero"', 'id="hero" id="hero-duplicate"')
    broken = broken.replace("<h1>Home</h1>", "<h1>Home</h1><h1>Again</h1>")
    broken = broken.replace(
        '<button data-interaction-id="interaction:home:contact">',
        '<button data-interaction-id="interaction:home:contact" className="card">',
    )
    broken_files = {**files, "src/routes/home/index.tsx": broken}
    codes = {item.code for item in audit_typescript_source(repo, files=broken_files, plan=plan)}
    assert "SOURCE_ROUTE_H1_COUNT_INVALID" in codes
    assert "SOURCE_GENERIC_SCAFFOLD_CLASS" in codes


@pytest.mark.asyncio
async def test_wave_scheduler_caps_concurrency_and_orders_results() -> None:
    active = 0
    maximum = 0

    async def execute(unit: WorkUnit) -> str:
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        await asyncio.sleep(0)
        active -= 1
        return unit.unit_id

    units = [WorkUnit(unit_id=f"u-{index}", kind="foundation") for index in range(5)]
    results = await execute_waves(units, execute, max_concurrency=2)
    assert maximum <= 2
    assert [item.unit_id for item in results] == [f"u-{index}" for index in range(5)]
