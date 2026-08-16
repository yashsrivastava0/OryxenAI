from __future__ import annotations

import pytest

from oryxenai.agents.code_generator.acquisition_validators import (
    AcquisitionValidationError,
    filter_candidates_by_policy,
    inspect_bytes,
    select_candidate,
    validate_plan_delta,
    validate_resource_request,
)
from oryxenai.agents.code_generator.development_schemas import (
    PlanDelta,
    ResourceBinding,
    ResourceCandidate,
    ResourceLedger,
    ResourceRequest,
    SitePlan,
)
from oryxenai.core.settings import Settings


def _plan() -> SitePlan:
    return SitePlan.model_validate(
        {
            "plan_id": "plan-home",
            "routes": [
                {
                    "route_id": "home",
                    "path": "/",
                    "section_ids": ["hero"],
                    "responsive_outcome": "stack on mobile",
                    "reduced_motion_outcome": "static equivalent",
                    "interaction_outcome": "keyboard navigation",
                }
            ],
            "resource_slots": [
                {"slot_id": "hero-image", "route_id": "home", "purpose": "hero image"}
            ],
            "work_graph": {
                "units": [
                    {"unit_id": "foundation", "kind": "foundation"},
                    {
                        "unit_id": "route-home",
                        "kind": "route",
                        "route_id": "home",
                        "section_ids": ["hero"],
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


def _request(**overrides: object) -> ResourceRequest:
    value: dict[str, object] = {
        "request_id": "request-1",
        "based_on": {"input_receipt_hash": "input", "site_plan_hash": "plan"},
        "origin": {"work_unit_id": "route-home"},
        "category": "image",
        "placement": {"route_id": "home", "section_id": "hero", "purpose": "hero image"},
        "why_existing_is_insufficient": "No admitted image fits the slot.",
        "query": {"positive_terms": ["editorial"], "negative_terms": [], "forbidden_subjects": []},
        "technical_constraints": {"media_types": ["image/jpeg"], "max_bytes": 100000},
        "source_constraints": {
            "allowed_source_kinds": ["fixture"],
            "vendoring_required": True,
        },
        "requiredness": "preferred",
        "fallback": {"kind": "generated_local", "implementation": "draw a local abstract mark"},
        "affected_work_unit_ids": ["route-home"],
    }
    value.update(overrides)
    return ResourceRequest.model_validate(value)


def _candidate(candidate_id: str, *, tags: list[str], licence: str = "MIT") -> ResourceCandidate:
    return ResourceCandidate(
        candidate_id=candidate_id,
        provider_key="fixture",
        provider_resource_id=candidate_id,
        category="image",
        title=candidate_id,
        tags=tags,
        canonical_source=f"fixture://{candidate_id}",
        licence=licence,
        attribution="Fixture provider",
        vendoring_policy="download and vendor",
    )


def test_request_hash_is_stable_and_candidate_selection_is_deterministic() -> None:
    request = _request()
    again = request.model_copy(deep=True)
    assert request.request_hash == again.request_hash
    selected, rationale = select_candidate(
        request, [_candidate("plain", tags=["calm"]), _candidate("editorial", tags=["editorial"])]
    )
    assert selected == "editorial"
    assert "overlap" in rationale


def test_forbidden_subject_and_user_media_are_rejected() -> None:
    settings = Settings()
    settings.code_generator_acquisition.forbidden_subject_terms = ["weapon"]
    with pytest.raises(AcquisitionValidationError, match="forbidden subject"):
        validate_resource_request(
            _request(query={"positive_terms": ["weapon"]}), plan=_plan(), settings=settings
        )
    with pytest.raises(AcquisitionValidationError, match="user media"):
        validate_resource_request(
            _request(
                source_constraints={
                    "allowed_source_kinds": ["fixture"],
                    "upstream_source_policy": "approved_user_media",
                }
            ),
            plan=_plan(),
            settings=settings,
        )


def test_duplicate_request_and_unknown_plan_delta_are_rejected() -> None:
    request = _request()
    ledger = ResourceLedger(
        based_on_input_and_plan={"input_receipt_hash": "input", "site_plan_hash": "plan"},
        requests=[request],
    )
    with pytest.raises(AcquisitionValidationError, match="already has"):
        validate_resource_request(
            request, plan=_plan(), ledger_excluding=ledger, settings=Settings()
        )
    delta = PlanDelta(
        delta_id="delta-1",
        based_on_plan_hash="plan",
        binding_changes=[
            ResourceBinding(
                binding_id="binding", request_id_or_pack_need_id="unknown", disposition="admitted"
            )
        ],
    )
    with pytest.raises(AcquisitionValidationError, match="unknown resource slot"):
        validate_plan_delta(delta, plan=_plan())


def test_candidate_policy_drops_unlicensed_and_forbidden_candidates() -> None:
    request = _request(query={"positive_terms": ["editorial"], "forbidden_subjects": ["weapon"]})
    candidates = [
        _candidate("good", tags=["editorial"]),
        _candidate("unlicensed", tags=["editorial"], licence=""),
        _candidate("bad-subject", tags=["weapon"]),
    ]
    assert [
        candidate.candidate_id for candidate in filter_candidates_by_policy(candidates, request)
    ] == ["good"]


def test_structural_byte_inspection_rejects_unsafe_inputs() -> None:
    assert inspect_bytes(b"wOF2" + b"0" * 20, category="font")["media_type"] == "font/woff2"
    with pytest.raises(AcquisitionValidationError, match="scripts"):
        inspect_bytes(b'<svg xmlns="http://www.w3.org/2000/svg"><script /></svg>', category="icon")
    with pytest.raises(AcquisitionValidationError, match="UTF-8"):
        inspect_bytes(b"\xff\xfe", category="component_source")
