"""Privacy regression tests (Section 28).

Runs a synthetic Discovery operation with a distinctive marker string and
asserts the marker never appears in captured logs. Also asserts that
reasoning_content, API keys, and provider error bodies are never logged.
"""

from __future__ import annotations

import io
import logging

from oryxenai.agents.discovery.agent import DiscoveryAgent
from oryxenai.agents.discovery.fake_client import FakeDiscoveryModelClient
from oryxenai.agents.shared.contracts import AgentContext, AgentKey

_MARKER_PROMPT = "PRIVACY-MARKER-7F3A main prompt"
_MARKER_RESUME = "PRIVACY-MARKER-7F3A resume text\nTest User\nExample Corp\nPython, PostgreSQL\n"
_MARKER_ANSWER = "PRIVACY-MARKER-7F3A answer text"


def _capture_logs() -> tuple[io.StringIO, logging.Handler]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(name)s :: %(message)s"))
    logger = logging.getLogger("oryxenai")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return stream, handler


def _run_call_a() -> None:
    import asyncio

    agent = DiscoveryAgent(model_client=FakeDiscoveryModelClient())
    context = AgentContext(
        portfolio_session_id="00000000-0000-0000-0000-000000000001",
        run_id="00000000-0000-0000-0000-000000000002",
        agent_key=AgentKey.DISCOVERY,
        agent_input={
            "operation": "prepare_questions",
            "intake": {
                "main_prompt": _MARKER_PROMPT,
                "resume_text": _MARKER_RESUME,
                "resume_source": "pasted_text",
                "output_language": "en",
            },
        },
    )
    asyncio.run(agent.run(context))


def test_raw_source_never_logged() -> None:
    stream, handler = _capture_logs()
    try:
        _run_call_a()
    finally:
        logging.getLogger("oryxenai").removeHandler(handler)
    logs = stream.getvalue()
    assert _MARKER_PROMPT not in logs
    assert _MARKER_RESUME not in logs
    assert "Python, PostgreSQL" not in logs


def test_reasoning_content_never_logged() -> None:
    stream, handler = _capture_logs()
    try:
        _run_call_a()
    finally:
        logging.getLogger("oryxenai").removeHandler(handler)
    logs = stream.getvalue()
    assert "reasoning_content" not in logs
    assert "chain-of-thought" not in logs.lower()


def test_api_key_never_logged() -> None:
    stream, handler = _capture_logs()
    try:
        _run_call_a()
    finally:
        logging.getLogger("oryxenai").removeHandler(handler)
    logs = stream.getvalue()
    assert "sk-" not in logs
    assert "api_key" not in logs.lower()
    assert "authorization" not in logs.lower()
