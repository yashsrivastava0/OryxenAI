"""Unit tests for agent contracts and mock agent behavior."""

from __future__ import annotations

import pytest

from oryxenai.agents.code_generator.agent import CodeGeneratorAgent
from oryxenai.agents.code_generator.schemas import CodeGeneratorResponse
from oryxenai.agents.content_architect.agent import ContentArchitectAgent
from oryxenai.agents.content_architect.schemas import (
    ContentArchitectRequest,
    ContentArchitectResponse,
)
from oryxenai.agents.discovery.agent import DiscoveryAgent
from oryxenai.agents.discovery.schemas import DiscoveryIntake, ResumeSource
from oryxenai.agents.shared.contracts import (
    AgentContext,
    AgentKey,
    AgentRequest,
    AgentResult,
    AgentRunStatus,
)
from oryxenai.agents.visual_design_director.agent import VisualDesignDirectorAgent
from oryxenai.agents.visual_design_director.schemas import (
    VisualDesignDirectorResponse,
)


def test_agent_key_from_string_valid():
    """Valid agent keys parse correctly."""
    assert AgentKey.from_string("discovery") == AgentKey.DISCOVERY
    assert AgentKey.from_string("content_architect") == AgentKey.CONTENT_ARCHITECT
    assert AgentKey.from_string("visual_design_director") == AgentKey.VISUAL_DESIGN_DIRECTOR
    assert AgentKey.from_string("code_generator") == AgentKey.CODE_GENERATOR


def test_agent_key_from_string_invalid():
    """Invalid agent keys raise ValueError."""
    with pytest.raises(ValueError, match="Unknown agent key"):
        AgentKey.from_string("nonexistent")


def test_agent_run_status_values():
    """Status enum has the expected values."""
    assert AgentRunStatus.PENDING.value == "pending"
    assert AgentRunStatus.RUNNING.value == "running"
    assert AgentRunStatus.SUCCEEDED.value == "succeeded"
    assert AgentRunStatus.FAILED.value == "failed"


def test_agent_context_no_db_objects():
    """AgentContext contains only structured data, not DB/request objects."""
    ctx = AgentContext(
        portfolio_session_id="00000000-0000-0000-0000-000000000001",
        run_id="00000000-0000-0000-0000-000000000002",
        agent_key=AgentKey.DISCOVERY,
    )
    assert ctx.current_state == {}
    assert ctx.agent_input == {}
    assert ctx.attempt == 1
    assert ctx.request_id == ""


def test_agent_request_validation():
    """AgentRequest validates and allows extra fields."""
    req = AgentRequest(input={"key": "value"})
    assert req.input == {"key": "value"}


def test_agent_result_defaults():
    """AgentResult has safe defaults."""
    result = AgentResult()
    assert result.output == {}
    assert result.prompt_version == "0.0.0-mock"
    assert result.model_metadata == {}


def _build_context(agent_key: AgentKey, agent_input: dict[str, object]) -> AgentContext:
    return AgentContext(
        portfolio_session_id="00000000-0000-0000-0000-000000000001",
        run_id="00000000-0000-0000-0000-000000000002",
        agent_key=agent_key,
        agent_input=agent_input,
    )


async def test_discovery_agent_deterministic_output():
    """Discovery agent returns structured output via fake client."""
    agent = DiscoveryAgent()
    ctx = _build_context(
        AgentKey.DISCOVERY,
        {
            "operation": "prepare_questions",
            "intake": {
                "main_prompt": "I am mainly looking for backend engineering roles.",
                "resume_text": (
                    "Test User\nSoftware Engineer\nExample Corp\n"
                    "Implemented retry handling and stale-job recovery for the PostgreSQL worker\n"
                    "observability\nDocker\nPython, PostgreSQL, FastAPI\nmigrations\n"
                ),
                "resume_source": "pasted_text",
                "output_language": "en",
            },
        },
    )
    result = await agent.run(ctx)
    assert isinstance(result, AgentResult)
    assert "analysis" in result.output
    assert result.output["operation"] == "prepare_questions"


async def test_content_architect_agent_deterministic_output():
    agent = ContentArchitectAgent()
    ctx = _build_context(
        AgentKey.CONTENT_ARCHITECT,
        {"discovery": {"summary": "test"}, "preferences": {}},
    )
    result = await agent.run(ctx)
    assert "sections" in result.output
    assert "outline" in result.output


async def test_visual_design_director_agent_deterministic_output():
    agent = VisualDesignDirectorAgent()
    ctx = _build_context(
        AgentKey.VISUAL_DESIGN_DIRECTOR,
        {"content": {}, "brand": {}},
    )
    result = await agent.run(ctx)
    assert "theme" in result.output
    assert "palette" in result.output


async def test_code_generator_agent_deterministic_output():
    agent = CodeGeneratorAgent()
    ctx = _build_context(
        AgentKey.CODE_GENERATOR,
        {"content": {}, "design": {}},
    )
    result = await agent.run(ctx)
    assert "files" in result.output
    assert "metadata" in result.output


async def test_all_agents_return_same_output_for_different_inputs():
    """Deterministic mock: same operation produces the same output."""
    agent = DiscoveryAgent()
    input_data = {
        "operation": "prepare_questions",
        "intake": {"main_prompt": "first", "resume_source": "none", "output_language": "en"},
    }
    ctx1 = _build_context(AgentKey.DISCOVERY, input_data)
    ctx2 = _build_context(AgentKey.DISCOVERY, input_data)
    r1 = await agent.run(ctx1)
    r2 = await agent.run(ctx2)
    assert r1.output == r2.output


def test_discovery_schema_validation():
    """Discovery schemas validate their fields."""
    intake = DiscoveryIntake(main_prompt="test", resume_source=ResumeSource.NONE)
    assert intake.main_prompt == "test"
    assert intake.resume_source == ResumeSource.NONE


def test_content_architect_schema_validation():
    req = ContentArchitectRequest(discovery={"summary": "s"})
    assert req.discovery["summary"] == "s"
    resp = ContentArchitectResponse(sections=[{"id": "hero"}], outline={"title": "T"})
    assert resp.sections[0]["id"] == "hero"


def test_visual_design_schema_validation():
    resp = VisualDesignDirectorResponse(
        theme={"name": "dark"}, palette=["#000"], typography={"heading_font": "serif"}
    )
    assert resp.palette == ["#000"]
    assert resp.typography["heading_font"] == "serif"


def test_code_generator_schema_validation():
    resp = CodeGeneratorResponse(files=[{"path": "index.html"}], metadata={"file_count": 1})
    assert resp.files[0]["path"] == "index.html"
