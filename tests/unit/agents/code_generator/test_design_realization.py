"""Regression tests for resource-fallback-aware runtime resource checks.

Before this fix, `compile_design_realization` built `resource_checks` from
every `blueprint.resource_placements` unconditionally, blind to whether
acquisition actually materialized a real local file or the placement fell
back to an honest decorative composition (the approved, model-instructed
behavior for an optional resource with no real binding -- see
route_batch.md/repair_source.md/integration_review.md). The runtime browser
check then demanded a real decoded `<img>` for a placement that was never
supposed to have one.
"""

from __future__ import annotations

from oryxenai.agents.code_generator.core.design_realization import compile_design_realization
from oryxenai.agents.code_generator.core.development_schemas import ExperienceBlueprintV4
from tests.unit.agents.code_generator.test_v4_contracts import _blueprint

_RESOURCE_SLOT_ID = "resource-hero-photo"


def _blueprint_with_resource_placement() -> ExperienceBlueprintV4:
    payload = _blueprint().model_dump(mode="python")
    payload["resource_placements"] = [
        {
            "resource_slot_id": _RESOURCE_SLOT_ID,
            "route_id": "home",
            "section_id": "hero",
            "element_marker": 'data-resource-slot="slot-hero-photo"',
            "element_selector": '[data-resource-slot="slot-hero-photo"]',
            "alt_policy": "decorative",
            "fit": "cover",
            "focal_position": "center",
            "loading": "eager",
            "responsive_behavior": "Stack below approved hero copy.",
            "sizes": "(max-width: 48rem) 100vw, 40vw",
            "aspect_ratio_min": 1.2,
            "aspect_ratio_max": 1.8,
            "minimum_visible_ratio": 0.4,
        }
    ]
    return ExperienceBlueprintV4.model_validate(payload)


def _execution(*, required: bool) -> dict:
    return {
        "slots": [
            {
                "resource_slot_id": _RESOURCE_SLOT_ID,
                "required": required,
                "resolution": {"resolution_type": "delegated_acquisition", "local_paths": []},
            }
        ]
    }


def _ledger(*, local_paths: list[str]) -> dict:
    return {
        "requests": [{"request_id": f"delegated-{_RESOURCE_SLOT_ID}", "request_hash": "hash-1"}],
        "active_bindings": [
            {
                "request_id_or_pack_need_id": "hash-1",
                "disposition": "admitted" if local_paths else "fallback",
                "local_paths": local_paths,
            }
        ],
    }


def test_no_ledger_data_checks_every_placement_unchanged() -> None:
    """Backward compatible default: callers that don't pass execution/
    resource_ledger keep the prior acquisition-blind behavior."""

    realization = compile_design_realization(
        _blueprint_with_resource_placement(), route_id="home", section_order=["hero"]
    )

    assert [item.resource_slot_id for item in realization.resource_checks] == [_RESOURCE_SLOT_ID]


def test_optional_placement_with_no_real_local_file_is_excluded() -> None:
    realization = compile_design_realization(
        _blueprint_with_resource_placement(),
        route_id="home",
        section_order=["hero"],
        execution=_execution(required=False),
        resource_ledger=_ledger(local_paths=[]),
    )

    assert realization.resource_checks == []


def test_required_placement_is_never_excluded_even_without_a_real_file() -> None:
    """A genuinely required-but-missing resource must still be caught --
    the fix must never excuse an unmet required behavior."""

    realization = compile_design_realization(
        _blueprint_with_resource_placement(),
        route_id="home",
        section_order=["hero"],
        execution=_execution(required=True),
        resource_ledger=_ledger(local_paths=[]),
    )

    assert [item.resource_slot_id for item in realization.resource_checks] == [_RESOURCE_SLOT_ID]


def test_distinctive_move_carries_its_runtime_marker_through() -> None:
    """source_selector measures the width/positional relationship on a
    move's outer wrapper, but required_css_properties can legitimately live
    on a nested element carrying the move's own runtime_marker instead --
    the runtime check needs that marker to look in the right place."""

    realization = compile_design_realization(_blueprint(), route_id="home", section_order=["hero"])

    assert len(realization.distinctive_move_checks) == 1
    assert realization.distinctive_move_checks[0].runtime_marker == (
        'data-distinctive-move-id="move:hero-rail"'
    )


def test_optional_placement_with_a_real_materialized_file_is_kept() -> None:
    realization = compile_design_realization(
        _blueprint_with_resource_placement(),
        route_id="home",
        section_order=["hero"],
        execution=_execution(required=False),
        resource_ledger=_ledger(local_paths=["resources/images/local/hero.jpg"]),
    )

    assert [item.resource_slot_id for item in realization.resource_checks] == [_RESOURCE_SLOT_ID]
