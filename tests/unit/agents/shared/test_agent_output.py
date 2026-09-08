from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from oryxenai.agents.shared.agent_output import (
    public_agent_output,
    public_discovery_outputs,
    public_output_for_run,
)


def test_public_agent_output_preserves_unknown_nested_fields_and_removes_transport() -> None:
    payload = {
        "brief_markdown": "# A brief",
        "future_field": {"nested": [1, {"new_key": "kept"}]},
        "input_payload": {"resume": "private source"},
        "state_before": {"secret": "internal state"},
        "model_metadata": {"provider": "Experiential Labs"},
        "api_key": "must not escape",
        "nested": {"authorization": "Bearer secret", "safe": True},
    }

    result = public_agent_output(payload)

    assert result == {
        "brief_markdown": "# A brief",
        "future_field": {"nested": [1, {"new_key": "kept"}]},
        "nested": {"safe": True},
    }
    assert result is not payload


@pytest.mark.asyncio
async def test_public_output_for_run_requires_success_and_valid_uuid() -> None:
    run_id = uuid4()
    runs = {
        run_id: SimpleNamespace(
            status="succeeded",
            output_payload={"required": True, "unknown": {"value": 3}},
        ),
    }

    async def loader(identifier: UUID) -> object | None:
        return runs.get(identifier)

    assert await public_output_for_run(loader, str(run_id)) == {
        "required": True,
        "unknown": {"value": 3},
    }
    assert await public_output_for_run(loader, str(uuid4())) is None
    assert await public_output_for_run(loader, "not-a-uuid") is None
    assert await public_output_for_run(loader, None) is None


@pytest.mark.asyncio
async def test_public_discovery_outputs_keeps_both_operation_envelopes() -> None:
    questions_id = uuid4()
    brief_id = uuid4()
    runs = {
        questions_id: SimpleNamespace(
            status="succeeded", output_payload={"mode": "ask_questions", "new": ["x"]}
        ),
        brief_id: SimpleNamespace(
            status="succeeded", output_payload={"brief_markdown": "# Brief"}
        ),
    }

    async def loader(identifier: UUID) -> object | None:
        return runs.get(identifier)

    assert await public_discovery_outputs(
        loader,
        questions_run_id=str(questions_id),
        brief_run_id=str(brief_id),
    ) == {
        "understand_and_question": {"mode": "ask_questions", "new": ["x"]},
        "build_or_revise_brief": {"brief_markdown": "# Brief"},
    }
