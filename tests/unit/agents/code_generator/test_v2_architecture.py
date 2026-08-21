from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from oryxenai.agents.code_generator.core.development_schemas import (
    CreativeConcept,
    CreativeDirectionSetV2,
    IntegrationReviewV1,
    RoutePlan,
    SitePlan,
)
from oryxenai.agents.code_generator.core.work_graph_compiler import compile_site_plan
from oryxenai.agents.code_generator.core.workspace import GenerationWorkspace


def _concept(concept_id: str) -> CreativeConcept:
    return CreativeConcept(
        concept_id=concept_id,
        thesis=f"Thesis for {concept_id}",
        typography_direction="Editorial display type with compact technical labels",
        composition_direction="Asymmetric proof-led composition",
        color_direction="Warm paper and precise ink",
        motion_direction="Sequenced entrances tied to reading order",
        distinguishing_moves=["offset proof rail"],
    )


def test_creative_direction_requires_exactly_two_grounded_concepts() -> None:
    result = CreativeDirectionSetV2(
        candidates=[_concept("editorial"), _concept("technical")],
        recommended_concept_id="editorial",
        recommendation_basis="The approved route is text-led and proof-dense.",
    )
    assert result.recommended_concept_id == "editorial"

    with pytest.raises(ValidationError):
        CreativeDirectionSetV2(
            candidates=[_concept("only")],
            recommended_concept_id="only",
            recommendation_basis="Insufficient comparison",
        )


def test_integration_acceptance_requires_all_quality_scores_at_least_four() -> None:
    with pytest.raises(ValidationError):
        IntegrationReviewV1(
            status="accepted",
            distinctiveness_score=3,
            composition_score=5,
            typography_score=5,
            resource_fit_score=5,
            motion_score=5,
        )


def test_work_graph_compiler_splits_routes_and_scopes_resources_to_each_batch() -> None:
    plan = SitePlan(
        plan_id="plan-v2",
        routes=[
            RoutePlan(
                route_id="route:home",
                path="/",
                section_ids=["hero", "work", "about", "connect"],
                responsive_outcome="All viewports preserve narrative order",
                reduced_motion_outcome="Static content remains visible",
                interaction_outcome="Keyboard-operable links",
            )
        ],
    )
    projections = {
        "site/contract.json": {
            "routes": [
                {
                    "route_id": "route:home",
                    "storage_key": "routes/route-home-hash",
                    "section_sequence": ["hero", "work", "about", "connect"],
                }
            ]
        },
        "execution/contract.json": {
            "slots": [
                {
                    "resource_slot_id": "hero-image",
                    "route_id": "route:home",
                    "section_ids": ["hero"],
                    "category": "image",
                    "required": True,
                    "rationale": "Hero visual anchor",
                    "resolution": {
                        "resolution_type": "local_material",
                        "local_paths": ["resources/images/hero.jpg"],
                    },
                },
                {
                    "resource_slot_id": "connect-image",
                    "route_id": "route:home",
                    "section_ids": ["connect"],
                    "category": "image",
                    "required": True,
                    "rationale": "Connect visual anchor",
                    "resolution": {
                        "resolution_type": "local_material",
                        "local_paths": ["resources/images/connect.jpg"],
                    },
                },
            ]
        },
    }
    compiled = compile_site_plan(plan, projections, max_sections_per_unit=2)
    batches = [unit for unit in compiled.work_graph.units if unit.kind == "route_batch"]

    assert [unit.section_ids for unit in batches] == [["hero", "work"], ["about", "connect"]]
    assert batches[0].resource_slot_ids == ["hero-image"]
    assert batches[1].resource_slot_ids == ["connect-image"]
    assert compiled.work_graph.units[-1].terminal is True
    assert compiled.work_graph.units[-1].depends_on == sorted(
        unit.unit_id for unit in compiled.work_graph.units[:-1]
    )


def test_acquired_executable_source_is_importable_and_media_is_public(tmp_path: Path) -> None:
    workspace = GenerationWorkspace(tmp_path / "run", tmp_path / "inputs", tmp_path / "checkpoints")
    workspace.repo_dir.mkdir(parents=True)
    component = tmp_path / "component.tsx"
    component.write_text("export const Component = () => null;", encoding="utf-8")
    image = tmp_path / "image.webp"
    image.write_bytes(b"image")

    component_path = workspace.materialize_acquired_file(component, "component.tsx")
    image_path = workspace.materialize_acquired_file(image, "image.webp")

    assert component_path == "src/generated/resources/acquired/component.tsx"
    assert image_path == "public/resources/acquired/image.webp"
    assert (workspace.repo_dir / component_path).is_file()
    assert (workspace.repo_dir / image_path).is_file()


def test_pack_fonts_are_browser_public_but_components_are_importable(tmp_path: Path) -> None:
    workspace = GenerationWorkspace(tmp_path / "run", tmp_path / "inputs", tmp_path / "checkpoints")
    (workspace.input_dir / "resources" / "fonts" / "local").mkdir(parents=True)
    (workspace.input_dir / "resources" / "components" / "local").mkdir(parents=True)
    (workspace.input_dir / "resources" / "fonts" / "local" / "body.woff2").write_bytes(b"font")
    (workspace.input_dir / "resources" / "components" / "local" / "Card.tsx").write_text(
        "export const Card = () => null;", encoding="utf-8"
    )

    copied = workspace.materialize_pack_resources()

    assert "public/resources/pack/fonts/local/body.woff2" in copied
    assert "src/generated/resources/pack/components/local/Card.tsx" in copied
    assert (workspace.repo_dir / "public/resources/pack/fonts/local/body.woff2").is_file()
    assert (workspace.repo_dir / "src/generated/resources/pack/components/local/Card.tsx").is_file()


def test_work_graph_compiler_keeps_an_empty_approved_route_executable() -> None:
    plan = SitePlan(
        plan_id="empty-route",
        routes=[
            RoutePlan(
                route_id="route:empty",
                path="/empty",
                section_ids=[],
                responsive_outcome="Readable at every viewport",
                reduced_motion_outcome="No motion required",
                interaction_outcome="Route remains addressable",
            )
        ],
    )
    compiled = compile_site_plan(
        plan,
        {
            "site/contract.json": {
                "routes": [
                    {
                        "route_id": "route:empty",
                        "storage_key": "routes/route-empty-hash",
                        "section_sequence": [],
                    }
                ]
            },
            "execution/contract.json": {"slots": []},
        },
    )

    route_unit = next(unit for unit in compiled.work_graph.units if unit.kind == "route")
    assert route_unit.owns_paths == [
        "src/routes/route-empty-hash/index.tsx",
        "src/routes/route-empty-hash/route.css",
    ]
