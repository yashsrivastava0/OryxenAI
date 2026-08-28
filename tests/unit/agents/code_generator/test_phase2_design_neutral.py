from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

from oryxenai.agents.code_generator.core.content_compiler import compile_content_module
from oryxenai.agents.code_generator.core.development_schemas import (
    DesignTokenSystemV3,
    ExecutionBindingV2,
    ExperienceBlueprintV3,
    GenerationProjection,
    GenerationWorkUnitProjection,
    InteractionContract,
    RoutePlan,
    RouteShellV3,
    SitePlan,
    SourceDiagnostic,
    TypedTokenGroupV3,
    WorkGraph,
    WorkUnit,
)
from oryxenai.agents.code_generator.core.generation_orchestrator import (
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
        owns_paths=["src/routes/home/sections/hero.tsx"],
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
        "src/routes/home/sections/hero.tsx": "export default function Hero() { return null; }"
    }
    assert "work_graph" not in repair_context["plan"]
    assert "section_regions" not in repair_context["plan"]
    assert "assets" not in repair_context["visual_direction"]


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
