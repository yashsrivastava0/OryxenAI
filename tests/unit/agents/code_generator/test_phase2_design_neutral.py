from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

from oryxenai.agents.code_generator.core.content_compiler import compile_content_module
from oryxenai.agents.code_generator.core.development_schemas import (
    DesignTokenSystemV3,
    ExperienceBlueprintV3,
    InteractionContract,
    RoutePlan,
    RouteShellV3,
    SitePlan,
    TypedTokenGroupV3,
    WorkGraph,
    WorkUnit,
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
                    values={"section": "clamp(3rem, 10vw, 9rem)"},
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
