"""Tests for bounded semantic repair and agent-level enforcement (v2)."""

from __future__ import annotations

from typing import Any

from oryxenai.agents.discovery.agent import DiscoveryAgent
from oryxenai.agents.discovery.fake_client import FakeDiscoveryModelClient
from oryxenai.agents.discovery.schemas import StructuredModelResult
from oryxenai.agents.shared.contracts import AgentContext, AgentKey


def _build_context(agent_input: dict) -> AgentContext:
    return AgentContext(
        portfolio_session_id="00000000-0000-0000-0000-000000000001",
        run_id="00000000-0000-0000-0000-000000000002",
        agent_key=AgentKey.DISCOVERY,
        agent_input=agent_input,
    )


def _intake() -> dict:
    return {
        "main_prompt": "I am mainly looking for backend engineering roles.",
        "resume_text": (
            "Test User\nSoftware Engineer\nExample Corp\n"
            "Implemented retry handling and stale-job recovery for the PostgreSQL worker\n"
            "observability\nDocker\nPython, PostgreSQL, FastAPI\nmigrations\n"
        ),
        "resume_source": "pasted_text",
        "output_language": "en",
    }


class _SemanticallyInvalidClient(FakeDiscoveryModelClient):
    """Returns a parseable analysis whose facts carry no evidence.

    The main call and the repair call both return the same invalid output,
    so the agent must fail the operation after exactly one repair.
    """

    def __init__(self) -> None:
        super().__init__(fixture_name="call_a_normal_output")
        self._invalid_payload = {
            "schema_version": 2,
            "operation": "prepare_questions",
            "facts": [
                {
                    "local_key": "fact-unverifiable-1",
                    "category": "skill",
                    "field": "skill",
                    "value": "Rust",
                    "status": "supported",
                    "evidence": [],
                    "sensitivity": "public",
                    "publish_default": True,
                    "origin": "directly_stated",
                }
            ],
            "questions": [],
        }

    async def generate_structured(self, **kwargs: Any) -> Any:
        self.requests.append(
            {
                "operation": kwargs.get("operation"),
                "instructions": kwargs.get("instructions"),
                "input_payload": kwargs.get("input_payload"),
            }
        )
        parsed = self._invalid_payload
        return StructuredModelResult(
            parsed_output=parsed,
            response_id="fake-response-id",
            model="fake-model",
            usage={"prompt_tokens": 10, "completion_tokens": 10},
            finish_reason="stop",
            latency_ms=5.0,
        )


async def test_call_a_semantically_invalid_fails_after_one_repair():
    """A perpetually-invalid Call A result is failed, with exactly one repair."""
    fake = _SemanticallyInvalidClient()
    agent = DiscoveryAgent(model_client=fake)
    ctx = _build_context({"operation": "prepare_questions", "intake": _intake()})

    result = await agent.run(ctx)
    assert result.output["status"] == "failed"
    assert result.output["error"]["code"] == "MODEL_SEMANTICALLY_INVALID"
    assert "analysis" not in result.output
    assert result.model_metadata.get("repair_attempted") is True
    assert result.model_metadata.get("repair_succeeded") is False


async def test_repair_bounded_to_one_call():
    """The agent never retries repair: exactly one repair request total."""
    fake = _SemanticallyInvalidClient()
    agent = DiscoveryAgent(model_client=fake)
    ctx = _build_context({"operation": "prepare_questions", "intake": _intake()})

    await agent.run(ctx)
    repair_calls = [r for r in fake.requests if r.get("operation") == "repair"]
    assert len(repair_calls) == 1


async def test_happy_path_does_not_trigger_repair():
    """A valid result never triggers a repair call."""
    fake = FakeDiscoveryModelClient()
    agent = DiscoveryAgent(model_client=fake)
    ctx = _build_context({"operation": "prepare_questions", "intake": _intake()})

    result = await agent.run(ctx)
    assert "analysis" in result.output
    assert result.output.get("status") != "failed"
    repair_calls = [r for r in fake.requests if r.get("operation") == "repair"]
    assert len(repair_calls) == 0


async def test_invalid_call_a_is_not_delivered_to_caller():
    """Invalid output is never returned as a usable analysis."""
    fake = _SemanticallyInvalidClient()
    agent = DiscoveryAgent(model_client=fake)
    ctx = _build_context({"operation": "prepare_questions", "intake": _intake()})

    result = await agent.run(ctx)
    assert result.output.get("status") == "failed"
    assert result.output.get("analysis") is None
