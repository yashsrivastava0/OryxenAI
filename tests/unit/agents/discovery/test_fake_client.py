"""Unit tests for the fake Discovery model client."""

from __future__ import annotations

import pytest

from oryxenai.agents.discovery.fake_client import FakeDiscoveryModelClient
from oryxenai.agents.discovery.schemas import DiscoveryAnalysisResult, DiscoveryBrief


class TestFakeClient:
    def test_returns_typed_output_for_call_a(self):
        client = FakeDiscoveryModelClient(fixture_name="call_a_normal_output")

        async def _run():
            result = await client.generate_structured(
                operation="prepare_questions",
                instructions="test instructions",
                input_payload={"main_prompt": "test"},
                output_model=DiscoveryAnalysisResult,
            )
            return result

        import asyncio

        result = asyncio.run(_run())
        assert result.response_id == "fake-response-id"
        assert result.model == "fake-model"

    def test_returns_typed_output_for_call_b(self):
        client = FakeDiscoveryModelClient(fixture_name="call_b_normal_output")

        async def _run():
            result = await client.generate_structured(
                operation="build_brief",
                instructions="test",
                input_payload={},
                output_model=DiscoveryBrief,
            )
            return result

        import asyncio

        result = asyncio.run(_run())
        assert result.response_id == "fake-response-id"

    def test_records_requests(self):
        client = FakeDiscoveryModelClient(fixture_name="call_a_normal_output")

        async def _run():
            await client.generate_structured(
                operation="prepare_questions",
                instructions="test",
                input_payload={"key": "value"},
                output_model=DiscoveryAnalysisResult,
            )

        import asyncio

        asyncio.run(_run())
        assert len(client.requests) == 1
        assert client.requests[0]["operation"] == "prepare_questions"
        assert client.requests[0]["input_payload"]["key"] == "value"

    def test_reset_requests(self):
        client = FakeDiscoveryModelClient(fixture_name="call_a_normal_output")

        async def _run():
            await client.generate_structured(
                operation="prepare_questions",
                instructions="test",
                input_payload={},
                output_model=DiscoveryAnalysisResult,
            )

        import asyncio

        asyncio.run(_run())
        assert len(client.requests) == 1
        client.reset_requests()
        assert len(client.requests) == 0

    def test_simulate_timeout(self):
        client = FakeDiscoveryModelClient(
            fixture_name="call_a_normal_output", simulate_timeout=True
        )

        async def _run():
            await client.generate_structured(
                operation="prepare_questions",
                instructions="test",
                input_payload={},
                output_model=DiscoveryAnalysisResult,
            )

        import asyncio

        with pytest.raises(TimeoutError):
            asyncio.run(_run())

    def test_simulate_rate_limit(self):
        client = FakeDiscoveryModelClient(
            fixture_name="call_a_normal_output", simulate_rate_limit=True
        )

        async def _run():
            await client.generate_structured(
                operation="prepare_questions",
                instructions="test",
                input_payload={},
                output_model=DiscoveryAnalysisResult,
            )

        import asyncio

        with pytest.raises(Exception, match="rate limit"):
            asyncio.run(_run())

    def test_simulate_refusal(self):
        client = FakeDiscoveryModelClient(
            fixture_name="call_a_normal_output", simulate_refusal=True
        )

        async def _run():
            await client.generate_structured(
                operation="prepare_questions",
                instructions="test",
                input_payload={},
                output_model=DiscoveryAnalysisResult,
            )

        import asyncio

        with pytest.raises(Exception, match="refusal"):
            asyncio.run(_run())

    def test_no_network_required(self):
        client = FakeDiscoveryModelClient(fixture_name="call_a_normal_output")

        async def _run():
            result = await client.generate_structured(
                operation="prepare_questions",
                instructions="test",
                input_payload={},
                output_model=DiscoveryAnalysisResult,
            )
            return result

        import asyncio

        result = asyncio.run(_run())
        assert result.model == "fake-model"

    def test_fixture_not_found_raises(self):
        client = FakeDiscoveryModelClient(fixture_name="nonexistent_fixture")

        async def _run():
            await client.generate_structured(
                operation="prepare_questions",
                instructions="test",
                input_payload={},
                output_model=DiscoveryAnalysisResult,
            )

        import asyncio

        with pytest.raises(FileNotFoundError):
            asyncio.run(_run())

    def test_complete_legacy_method(self):
        client = FakeDiscoveryModelClient(fixture_name="call_a_normal_output")

        async def _run():
            return await client.complete("system", "task")

        import asyncio

        result = asyncio.run(_run())
        assert isinstance(result, str)

    def test_simulate_incomplete(self):
        client = FakeDiscoveryModelClient(
            fixture_name="call_a_normal_output", simulate_incomplete=True
        )

        async def _run():
            await client.generate_structured(
                operation="prepare_questions",
                instructions="test",
                input_payload={},
                output_model=DiscoveryAnalysisResult,
            )

        import asyncio

        with pytest.raises(Exception, match="incomplete"):
            asyncio.run(_run())

    def test_simulate_invalid_output(self):
        client = FakeDiscoveryModelClient(
            fixture_name="call_a_normal_output", simulate_invalid_output=True
        )

        async def _run():
            await client.generate_structured(
                operation="prepare_questions",
                instructions="test",
                input_payload={},
                output_model=DiscoveryAnalysisResult,
            )

        import asyncio

        with pytest.raises((ValueError, Exception)):
            asyncio.run(_run())
