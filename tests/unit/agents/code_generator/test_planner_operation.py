from types import SimpleNamespace

import pytest

import oryxenai.agents.code_generator.core.planner_operation as planner_operation
from oryxenai.agents.code_generator.core.development_planner import SitePlanValidationError
from oryxenai.agents.code_generator.core.planner_operation import (
    _canonicalize_v4_distinctive_move_ratios,
    _canonicalize_v4_typography_bindings,
    run_planner_operation,
)


class _RetryingPlanner:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def generate_structured(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(str(kwargs["instructions"]))
        if len(self.calls) == 1:
            return SimpleNamespace(parsed_output={})
        return SimpleNamespace(parsed_output={"plan_id": "plan-retry", "routes": []})


@pytest.mark.asyncio
async def test_planner_retries_structural_output_once() -> None:
    planner = _RetryingPlanner()

    plan, _prompt_version, _receipt, _result = await run_planner_operation(
        planner,  # type: ignore[arg-type]
        context={"input_hashes": [], "owned_paths": []},
        profile_name="code_generator_planner",
    )

    assert plan.plan_id == "plan-retry"
    assert len(planner.calls) == 2
    assert "previous planner response" in planner.calls[1]
    assert "plan_id" in planner.calls[1]


@pytest.mark.asyncio
async def test_planner_retries_semantic_output_once(monkeypatch) -> None:
    class _SemanticRetryingPlanner:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def generate_structured(self, **kwargs: object) -> SimpleNamespace:
            self.calls.append(str(kwargs["instructions"]))
            return SimpleNamespace(parsed_output={"plan_id": "plan-retry", "routes": []})

    planner = _SemanticRetryingPlanner()
    calls = 0

    def validate(plan, projections, *, max_work_units, require_blueprint):
        del projections, max_work_units, require_blueprint
        nonlocal calls
        calls += 1
        if calls == 1:
            raise SitePlanValidationError(
                "PLAN_SHARED_COMPONENTS",
                "Shared components must be owned by the route composer.",
            )
        return plan

    monkeypatch.setattr(
        planner_operation,
        "compile_site_plan",
        lambda plan, projections, **_: plan,
    )
    monkeypatch.setattr(planner_operation, "validate_site_plan", validate)

    plan, _prompt_version, _receipt, _result = await run_planner_operation(
        planner,  # type: ignore[arg-type]
        context={"input_hashes": [], "owned_paths": []},
        profile_name="code_generator_planner",
        projections={},
    )

    assert plan.plan_id == "plan-retry"
    assert len(planner.calls) == 2
    assert "PLAN_SHARED_COMPONENTS" in planner.calls[1]
    assert "Shared components must be owned by the route composer." in planner.calls[1]


def test_v4_distinctive_move_ratio_canonicalization_widens_rounded_ranges() -> None:
    payload = {
        "distinctive_moves": [
            {
                "relationship": "width_ratio",
                "minimum_ratio": 0.8,
                "maximum_ratio": 0.9,
            },
            {
                "relationship": "horizontal_offset",
                "minimum_ratio": 0.95,
                "maximum_ratio": 1.05,
            },
            {
                "relationship": "sticky_within_section",
                "minimum_ratio": 1,
                "maximum_ratio": 1,
            },
            {
                "relationship": "width_ratio",
                "minimum_ratio": 0.25,
                "maximum_ratio": 0.85,
            },
        ]
    }

    canonical = _canonicalize_v4_distinctive_move_ratios(payload)

    assert canonical["distinctive_moves"][0]["minimum_ratio"] == 0.8
    assert canonical["distinctive_moves"][0]["maximum_ratio"] == 0.95
    assert canonical["distinctive_moves"][1]["minimum_ratio"] == 0.95
    assert canonical["distinctive_moves"][1]["maximum_ratio"] == 1.2
    assert canonical["distinctive_moves"][2]["minimum_ratio"] == 1
    assert canonical["distinctive_moves"][2]["maximum_ratio"] == 1
    assert canonical["distinctive_moves"][3] == payload["distinctive_moves"][3]


def test_v4_distinctive_move_ratio_canonicalization_leaves_invalid_types_for_schema() -> None:
    payload = {
        "distinctive_moves": [
            {"relationship": "width_ratio", "minimum_ratio": "unknown", "maximum_ratio": 1}
        ]
    }

    canonical = _canonicalize_v4_distinctive_move_ratios(payload)

    assert canonical is payload


def test_v4_typography_canonicalization_uses_deferred_font_binding() -> None:
    payload = {
        "tokens": {
            "typography_roles": [
                {
                    "role": "body",
                    "approved_font_slot": "space-grotesk",
                    "family": "Inter",
                    "weights": [300],
                    "style": "italic",
                    "local_files": ["remote-font.woff2"],
                }
            ]
        }
    }
    projections = {
        "execution/contract.json": {
            "slots": [
                {
                    "resource_slot_id": "typography-font",
                    "category": "font",
                    "resolution": {
                        "font_family": "Space Grotesk",
                        "font_weights": ["400", "700"],
                        "local_paths": [
                            "resources/fonts/space-grotesk/400-normal.woff2",
                            "resources/fonts/space-grotesk/700-normal.woff2",
                        ],
                    },
                }
            ]
        }
    }

    canonical = _canonicalize_v4_typography_bindings(payload, projections)
    role = canonical["tokens"]["typography_roles"][0]

    assert role["approved_font_slot"] == "typography-font"
    assert role["family"] == "Space Grotesk"
    assert role["weights"] == [400, 700]
    assert role["style"] == "normal"
    assert (
        role["local_files"]
        == projections["execution/contract.json"]["slots"][0]["resolution"]["local_paths"]
    )
