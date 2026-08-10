from __future__ import annotations

import pytest
from pydantic import ValidationError

from oryxenai.api.routes.build_preparation import FixtureRunRequest, StartRequest
from oryxenai.main import create_app


def test_build_preparation_routes_are_exposed() -> None:
    paths = set(create_app().openapi()["paths"])
    assert "/api/v1/sessions/{session_id}/build-preparation" in paths
    assert "/api/v1/sessions/{session_id}/build-preparation/start" in paths
    assert "/api/v1/build-preparation/fixture/run" in paths


def test_start_request_rejects_untrusted_extra_fields() -> None:
    with pytest.raises(ValidationError):
        StartRequest.model_validate({"model_profile": "default", "approve": True})


def test_fixture_request_rejects_untrusted_extra_fields() -> None:
    with pytest.raises(ValidationError):
        FixtureRunRequest.model_validate({"path": "../../secret"})
