from types import SimpleNamespace

import pytest

from oryxenai.agents.code_generator.core.integration_review_operation import (
    run_integration_review_operation,
)
from oryxenai.agents.shared.providers.errors import ModelJsonInvalidError


class _RetryingReview:
    def __init__(self) -> None:
        self.calls = 0

    async def generate_structured(self, **_: object) -> SimpleNamespace:
        self.calls += 1
        if self.calls == 1:
            raise ModelJsonInvalidError("invalid review JSON")
        return SimpleNamespace(
            parsed_output={
                "status": "accepted",
                "findings": [],
                "distinctiveness_score": 4,
                "composition_score": 4,
                "typography_score": 4,
                "resource_fit_score": 4,
                "motion_score": 4,
            }
        )


@pytest.mark.asyncio
async def test_integration_review_retries_invalid_provider_json() -> None:
    reviewer = _RetryingReview()

    review, _receipt, _result = await run_integration_review_operation(
        reviewer,  # type: ignore[arg-type]
        context={"source_manifest": "source"},
        profile_name="code_generator_integration",
    )

    assert review.status == "accepted"
    assert reviewer.calls == 2
