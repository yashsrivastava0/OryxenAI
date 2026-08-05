"""Unit tests for the Discovery worker handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from oryxenai.agents.shared.contracts import AgentResult


def _mock_agent_result(output: dict | None = None) -> AgentResult:
    return AgentResult(
        output=output or {"status": "success"},
        prompt_version="1.0.0",
        model_metadata={"provider": "test"},
    )


class TestDiscoveryPrepareQuestionsHandler:
    def test_kind_is_correct(self):
        from oryxenai.jobs.handlers.discovery import DiscoveryPrepareQuestionsHandler

        handler = DiscoveryPrepareQuestionsHandler()
        assert handler.kind == "discovery.prepare_questions"

    def test_execute_succeeds_with_valid_payload(self):
        from oryxenai.jobs.handlers.discovery import DiscoveryPrepareQuestionsHandler

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=_mock_agent_result())
        mock_agent.key = "discovery"

        handler = DiscoveryPrepareQuestionsHandler()

        with patch(
            "oryxenai.jobs.handlers.discovery._build_discovery_agent",
            return_value=mock_agent,
        ):
            import asyncio

            result = asyncio.run(
                handler.execute(
                    payload={
                        "portfolio_session_id": "sess-001",
                        "session_state": {"discovery": {"status": "input_ready"}},
                        "intake": {
                            "main_prompt": "Build a portfolio",
                            "resume_text": "Experienced engineer",
                            "resume_source": "pasted_text",
                            "links": [],
                            "output_language": "en",
                            "source_revision": 1,
                        },
                    },
                    instance_id="worker-1",
                )
            )

        assert result["status"] == "success"
        mock_agent.run.assert_called_once()

    def test_raises_on_missing_intake(self):
        from oryxenai.jobs.handlers.discovery import DiscoveryPrepareQuestionsHandler

        handler = DiscoveryPrepareQuestionsHandler()

        async def _run():
            await handler.execute(
                payload={"portfolio_session_id": "sess-001"},
                instance_id="worker-1",
            )

        import asyncio

        with pytest.raises(ValueError, match="Missing required payload fields"):
            asyncio.run(_run())

    def test_raises_on_missing_session_id(self):
        from oryxenai.jobs.handlers.discovery import DiscoveryPrepareQuestionsHandler

        handler = DiscoveryPrepareQuestionsHandler()

        async def _run():
            await handler.execute(
                payload={"intake": {}},
                instance_id="worker-1",
            )

        import asyncio

        with pytest.raises(ValueError, match="Missing required payload fields"):
            asyncio.run(_run())


class TestDiscoveryBuildBriefHandler:
    def test_kind_is_correct(self):
        from oryxenai.jobs.handlers.discovery import DiscoveryBuildBriefHandler

        handler = DiscoveryBuildBriefHandler()
        assert handler.kind == "discovery.build_brief"

    def test_execute_succeeds_with_valid_payload(self):
        from oryxenai.jobs.handlers.discovery import DiscoveryBuildBriefHandler

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(
            return_value=_mock_agent_result({"operation": "build_brief", "status": "completed"})
        )
        mock_agent.key = "discovery"

        handler = DiscoveryBuildBriefHandler()

        with patch(
            "oryxenai.jobs.handlers.discovery._build_discovery_agent",
            return_value=mock_agent,
        ):
            import asyncio

            result = asyncio.run(
                handler.execute(
                    payload={
                        "portfolio_session_id": "sess-002",
                        "session_state": {"discovery": {"status": "answers_ready"}},
                        "intake": {
                            "main_prompt": "Build a portfolio",
                            "resume_text": "",
                            "resume_source": "none",
                            "links": [],
                            "output_language": "en",
                            "source_revision": 1,
                        },
                        "analysis": {"questions": []},
                        "answers": {"q-001": "yes"},
                    },
                    instance_id="worker-2",
                )
            )

        assert result["status"] == "completed"
        mock_agent.run.assert_called_once()

    def test_passes_analysis_and_answers_to_context(self):
        from oryxenai.jobs.handlers.discovery import DiscoveryBuildBriefHandler

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=_mock_agent_result())
        mock_agent.key = "discovery"

        handler = DiscoveryBuildBriefHandler()

        with patch(
            "oryxenai.jobs.handlers.discovery._build_discovery_agent",
            return_value=mock_agent,
        ):
            import asyncio

            asyncio.run(
                handler.execute(
                    payload={
                        "portfolio_session_id": "sess-003",
                        "intake": {
                            "main_prompt": "",
                            "resume_text": "",
                            "resume_source": "none",
                            "links": [],
                            "output_language": "en",
                            "source_revision": 1,
                        },
                        "analysis": {
                            "fact_candidates": [{"local_key": "fact-001", "value": "PhD"}]
                        },
                        "answers": {"q-abc": "selected_option"},
                    },
                    instance_id="worker-3",
                )
            )

        call_args = mock_agent.run.call_args
        context = call_args[0][0]
        assert context.agent_input["operation"] == "build_brief"
        assert context.agent_input["analysis"]["fact_candidates"][0]["value"] == "PhD"
        assert context.agent_input["answers"]["q-abc"] == "selected_option"


class TestPayloadValidation:
    def test_missing_both_fields(self):
        from oryxenai.jobs.handlers.discovery import _validate_discovery_payload

        with pytest.raises(ValueError, match=r"portfolio_session_id.*intake"):
            _validate_discovery_payload({})

    def test_missing_intake_only(self):
        from oryxenai.jobs.handlers.discovery import _validate_discovery_payload

        with pytest.raises(ValueError, match="intake"):
            _validate_discovery_payload({"portfolio_session_id": "sess-1"})


class TestHandlerRegistration:
    def test_both_handlers_registered(self):
        from oryxenai.jobs import registry

        assert registry.is_registered("discovery.prepare_questions")
        assert registry.is_registered("discovery.build_brief")

    def test_handlers_have_correct_kinds(self):
        from oryxenai.jobs import registry

        prepare = registry.get("discovery.prepare_questions")
        build = registry.get("discovery.build_brief")

        assert prepare is not None
        assert build is not None
        assert prepare.kind == "discovery.prepare_questions"
        assert build.kind == "discovery.build_brief"
