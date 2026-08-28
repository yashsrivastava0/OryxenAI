from types import SimpleNamespace

import pytest

from oryxenai.agents.code_generator.core.development_schemas import (
    IntegrationFinding,
    IntegrationReviewV1,
)
from oryxenai.agents.code_generator.core.generation_orchestrator import (
    _canonicalize_review_owners,
)
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


def test_review_owner_canonicalization_only_accepts_known_composer_alias() -> None:
    review = IntegrationReviewV1(
        status="findings",
        findings=[
            IntegrationFinding(
                finding_id="finding-1",
                severity="blocking",
                owner_work_unit_id="route-home-composer",
                code="SOURCE_CONTRACT",
                evidence="The source evidence is concrete.",
                requested_outcome="Correct the owned source.",
            ),
            IntegrationFinding(
                finding_id="finding-2",
                severity="advisory",
                owner_work_unit_id="unknown-owner",
                code="ADVISORY",
                evidence="The source evidence is concrete.",
                requested_outcome="Consider the observation.",
            ),
        ],
        distinctiveness_score=4,
        composition_score=4,
        typography_score=4,
        resource_fit_score=4,
        motion_score=4,
    )

    normalized = _canonicalize_review_owners(
        review,
        {"route-home-compose", "route-home-batch-1"},
    )

    assert normalized.findings[0].owner_work_unit_id == "route-home-compose"
    assert normalized.findings[1].owner_work_unit_id == "unknown-owner"
