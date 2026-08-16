"""Unit tests for agent contracts and mock agent behavior."""

from __future__ import annotations

import pytest

from oryxenai.agents.code_generator.agent import CodeGeneratorAgent
from oryxenai.agents.code_generator.schemas import CodeGeneratorResponse
from oryxenai.agents.content_architect.agent import ContentArchitectAgent
from oryxenai.agents.content_architect.schemas import (
    ContentArchitectIntake,
    ContentArchitectOutput,
    ContentPlanMode,
)
from oryxenai.agents.discovery.agent import DiscoveryAgent
from oryxenai.agents.discovery.schemas import DiscoveryIntake
from oryxenai.agents.shared.contracts import (
    AgentContext,
    AgentKey,
    AgentRequest,
    AgentResult,
    AgentRunStatus,
)
from oryxenai.agents.visual_design_director.agent import VisualDesignDirectorAgent
from oryxenai.agents.visual_design_director.schemas import (
    VisualDesignDirectorOutput,
    VisualPlanMode,
)
from tests.conftest import (
    _ContentArchitectMockModelClient,
    _MockModelClient,
    _VisualDesignDirectorMockModelClient,
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
    """Discovery agent returns structured output via the test mock client."""
    agent = DiscoveryAgent(model_client=_MockModelClient())
    ctx = _build_context(
        AgentKey.DISCOVERY,
        {
            "operation": "understand_and_question",
            "intake": {
                "message": "Create a portfolio for me. I am a software developer.",
                "document_text": (
                    "Test User\nSoftware Engineer\nExample Corp\n"
                    "Implemented retry handling and stale-job recovery for the PostgreSQL worker\n"
                    "observability\nDocker\nPython, PostgreSQL, FastAPI\nmigrations\n"
                ),
                "goal": "get hired",
            },
        },
    )
    result = await agent.run(ctx)
    assert isinstance(result, AgentResult)
    assert "questions" in result.output
    assert "mode" in result.output
    assert "assistant_message" in result.output
    assert "memory_update" in result.output
    assert result.output["operation"] == "understand_and_question"
    assert result.output["mode"] == "ASK_QUESTIONS"


async def test_content_architect_agent_deterministic_output():
    agent = ContentArchitectAgent(model_client=_ContentArchitectMockModelClient())
    ctx = _build_context(
        AgentKey.CONTENT_ARCHITECT,
        {
            "operation": "build",
            "intake": {"approved_brief_title": "Test Brief"},
            "preferences": {},
        },
    )
    result = await agent.run(ctx)
    assert "route_plan" in result.output
    assert "page_content_packs" in result.output
    assert "claim_grounding" in result.output
    assert result.output["stages_run"] == ["plan_content"]


async def test_visual_design_director_agent_deterministic_output():
    agent = VisualDesignDirectorAgent(model_client=_VisualDesignDirectorMockModelClient())
    ctx = _build_context(
        AgentKey.VISUAL_DESIGN_DIRECTOR,
        {
            "operation": "build",
            "intake": {"content_architect_content_hash": "h", "route_plan": [{"route_id": "home"}]},
            "preferences": {},
        },
    )
    result = await agent.run(ctx)
    assert "visual_language" in result.output
    assert "pages" in result.output
    assert result.output["stages_run"] == ["establish_visual_language"]


async def test_code_generator_agent_structured_planner_output():
    agent = CodeGeneratorAgent(model_client=_MockModelClient())
    ctx = _build_context(
        AgentKey.CODE_GENERATOR,
        {"planner_context": {"site": {"routes": []}}},
    )
    result = await agent.run(ctx)
    assert result.output["plan_id"] == "plan-mock"
    assert result.output["plan"]["plan_id"] == "plan-mock"
    assert result.prompt_version.startswith("code_generator.planner.")
    assert result.model_metadata["operation"] == "code_generator.plan"


async def test_all_agents_return_same_output_for_different_inputs():
    """Deterministic mock: same operation produces the same output."""
    agent = DiscoveryAgent(model_client=_MockModelClient())
    input_data = {
        "operation": "understand_and_question",
        "intake": {"message": "first", "goal": "get hired"},
    }
    ctx1 = _build_context(AgentKey.DISCOVERY, input_data)
    ctx2 = _build_context(AgentKey.DISCOVERY, input_data)
    r1 = await agent.run(ctx1)
    r2 = await agent.run(ctx2)
    assert r1.output == r2.output


def test_discovery_schema_validation():
    """Discovery schemas accept any input."""
    intake = DiscoveryIntake(message="test", document_text="notes", goal="get hired")
    assert intake.message == "test"
    assert intake.document_text == "notes"
    assert intake.goal == "get hired"


def test_content_architect_schema_validation():
    intake = ContentArchitectIntake(approved_brief_title="t", profile={"name": "Test User"})
    assert intake.profile["name"] == "Test User"
    output = ContentArchitectOutput(
        mode=ContentPlanMode.STRATEGY_ONLY,
        site_story_strategy={"positioning": "x"},
    )
    assert output.site_story_strategy["positioning"] == "x"


def test_visual_design_schema_validation():
    output = VisualDesignDirectorOutput(
        mode=VisualPlanMode.VISUAL_LANGUAGE_ONLY,
        visual_language={"creative_thesis": "restrained, evidence-first"},
    )
    assert output.visual_language["creative_thesis"] == "restrained, evidence-first"


def test_code_generator_schema_validation():
    resp = CodeGeneratorResponse(plan={"plan_id": "plan-1"}, plan_id="plan-1", route_ids=["home"])
    assert resp.plan["plan_id"] == "plan-1"
    assert resp.route_ids == ["home"]
