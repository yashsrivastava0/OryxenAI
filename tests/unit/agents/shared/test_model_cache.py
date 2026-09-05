from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest

from oryxenai.agents.discovery.schemas import QuestionSetOutput, StructuredModelResult
from oryxenai.agents.shared.model_cache import (
    StructuredResultCache,
    build_model_call_key,
    estimate_model_cost,
    prompt_cache_context,
)


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class _FakeSession:
    def __init__(self, entry: object) -> None:
        self.entry = entry

    async def execute(self, statement: object) -> _ScalarResult:
        return _ScalarResult(self.entry)

    async def commit(self) -> None:
        return None


class _SessionContext:
    def __init__(self, session: _FakeSession) -> None:
        self.session = session

    async def __aenter__(self) -> _FakeSession:
        return self.session

    async def __aexit__(self, *_args: object) -> None:
        return None


class _SessionFactory:
    def __init__(self, entry: object) -> None:
        self.session = _FakeSession(entry)

    def __call__(self) -> _SessionContext:
        return _SessionContext(self.session)


class _NeverCallClient:
    calls = 0

    async def generate_structured(self, **_kwargs: object) -> StructuredModelResult:
        self.calls += 1
        raise AssertionError("a ready cache entry should prevent a model call")


def _question_payload() -> dict[str, object]:
    return QuestionSetOutput(
        mode="ASK_QUESTIONS",
        assistant_message="A focused question.",
        questions=[],
    ).model_dump(mode="json")


@pytest.mark.asyncio
async def test_ready_entry_is_returned_without_calling_the_model() -> None:
    owner_id = UUID("00000000-0000-0000-0000-000000000101")
    input_payload = {"message": "same input"}
    cache_key, prompt_fingerprint, input_fingerprint = build_model_call_key(
        agent_key="discovery",
        operation="understand_and_question",
        system_prompt="stable system",
        instructions="stable task",
        input_payload=input_payload,
        output_model=QuestionSetOutput,
        model_profile="openai_luna",
        profile_fingerprint="profile-fingerprint",
        request_context=prompt_cache_context(
            "discovery", "understand_and_question", {"system.md": "hash"}
        ),
        strict_schema=False,
    )
    now = datetime.now(UTC)
    entry = SimpleNamespace(
        owner_user_id=owner_id,
        portfolio_session_id=None,
        agent_key="discovery",
        operation="understand_and_question",
        cache_key=cache_key,
        prompt_fingerprint=prompt_fingerprint,
        input_fingerprint=input_fingerprint,
        profile_fingerprint="profile-fingerprint",
        status="ready",
        output_payload=_question_payload(),
        provider_metadata={
            "model": "gpt-5.6-luna",
            "usage": {"prompt_tokens": 100, "completion_tokens": 20},
            "telemetry": {
                "input_characters": 500,
                "output_characters": 80,
                "estimated_cost": 0.01,
                "cost_unit": "configured_credits",
            },
            "finish_reason": "stop",
        },
        created_at=now - timedelta(minutes=5),
        expires_at=now + timedelta(days=10),
        last_hit_at=None,
        hit_count=0,
    )
    cache = StructuredResultCache(
        _SessionFactory(entry),
        owner_user_id=owner_id,
        portfolio_session_id=UUID("00000000-0000-0000-0000-000000000201"),
    )

    client = _NeverCallClient()
    result = await cache.generate(
        client=client,
        agent_key="discovery",
        operation="understand_and_question",
        system_prompt="stable system",
        instructions="stable task",
        input_payload=input_payload,
        output_model=QuestionSetOutput,
        model_profile="openai_luna",
        profile_fingerprint="profile-fingerprint",
        request_context=prompt_cache_context(
            "discovery", "understand_and_question", {"system.md": "hash"}
        ),
        strict_schema=False,
        validator=lambda payload: QuestionSetOutput.model_validate(payload),
    )

    assert client.calls == 0
    assert result.parsed_output == _question_payload()
    assert result.cache_metadata["cache_hit"] is True
    assert result.cache_metadata["avoided_input_characters"] == 500
    assert entry.hit_count == 1


def test_cache_key_ignores_request_identity_but_changes_with_input() -> None:
    common = {
        "agent_key": "content_architect",
        "operation": "plan_content",
        "system_prompt": "system",
        "instructions": "task",
        "input_payload": {"approved_brief_title": "Title"},
        "output_model": QuestionSetOutput,
        "model_profile": "openai_luna",
        "profile_fingerprint": "profile",
        "strict_schema": False,
    }
    first = build_model_call_key(
        **common,
        request_context={"request_id": "one", "key_order": ["approved_brief_title"]},
    )
    second = build_model_call_key(
        **common,
        request_context={"request_id": "two", "key_order": ["approved_brief_title"]},
    )
    changed = build_model_call_key(
        **{**common, "input_payload": {"approved_brief_title": "Other"}},
        request_context={"request_id": "one", "key_order": ["approved_brief_title"]},
    )

    assert first[0] == second[0]
    assert first[0] != changed[0]


def test_prompt_cache_context_is_stable_and_cost_estimate_uses_cached_rate() -> None:
    context = prompt_cache_context("discovery", "understand_and_question", {"a": "b"})
    assert context["prompt_cache_mode"] == "explicit"
    assert context["prompt_cache_breakpoint"] is True
    assert context["prompt_cache_ttl"] == "30m"

    pricing = {
        "input_per_million": 5,
        "cached_input_per_million": 0.5,
        "cache_write_per_million": 6.25,
        "output_per_million": 30,
    }
    estimate = estimate_model_cost(
        {
            "prompt_tokens": 1_000,
            "cached_prompt_tokens": 800,
            "cache_write_tokens": 100,
            "completion_tokens": 200,
        },
        pricing,
    )
    assert estimate == pytest.approx((100 * 5 + 800 * 0.5 + 100 * 6.25 + 200 * 30) / 1_000_000)
