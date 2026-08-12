from __future__ import annotations

import pytest

from oryxenai.agents.build_preparation.schemas import (
    ResourceQuery,
    ResourceSelection,
    Stage1QueryPlan,
    Stage2SelectionPlan,
)
from oryxenai.agents.build_preparation.validators import (
    BuildPreparationValidationError,
    validate_query_plan,
    validate_selection_plan,
)


def test_query_plan_must_cover_every_stage0_need() -> None:
    with pytest.raises(BuildPreparationValidationError, match="every Stage 0 need"):
        validate_query_plan(Stage1QueryPlan(), {"need-1"})


def test_selection_plan_is_closed_over_candidates_and_needs() -> None:
    query_plan = Stage1QueryPlan(
        queries=[ResourceQuery(need_id="need-1", kind="custom", fallback="Build it locally.")]
    )
    assert query_plan.queries[0].need_id == "need-1"
    with pytest.raises(BuildPreparationValidationError, match="every Stage 0 need"):
        validate_selection_plan(Stage2SelectionPlan(), {"need-1"}, [])

    plan = Stage2SelectionPlan(
        selections=[ResourceSelection(need_id="need-1", fallback="Build it locally.")]
    )
    assert validate_selection_plan(plan, {"need-1"}, []) == plan
