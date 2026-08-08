"""Pytest configuration and fixtures.

Integration/worker tests use OryxenAI_CONFIG_OVERLAY=config/app.test.toml
to point to a dedicated test database (oryxenai_test) so the application
database is never touched.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

import pytest
import pytest_asyncio

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

# ── Test-only deterministic model client ────────────────────────────────────
#
# Not a demo feature: a plain test double (the equivalent of
# unittest.mock.Mock) so flow tests never make network calls.


_DEFAULT_QUESTIONS: dict[str, Any] = {
    "mode": "ASK_QUESTIONS",
    "assistant_message": "I have enough to ask a few focused questions.",
    "questions": [
        {
            "id": "target_direction",
            "text": "Should the portfolio lead with backend or full-stack?",
            "kind": "single_select",
            "options": [
                {"id": "backend", "label": "Backend"},
                {"id": "fullstack", "label": "Full-stack"},
                {"id": "balanced", "label": "Balanced"},
            ],
            "reason": "changes positioning and project order",
            "allow_skip": True,
            "allow_auto": False,
        }
    ],
    "memory_update": {"intent_summary": "Backend engineering roles", "open_items": []},
}

_DEFAULT_PROFILE: dict[str, Any] = {
    "name": "Mock User",
    "current_title": "Software Engineer",
    "location": "",
    "links": [{"label": "GitHub", "url": "https://github.com/mockuser"}],
    "experience": [
        {
            "organization": "Northstar Systems",
            "role": "Software Engineer",
            "dates": "2023-present",
            "highlights": ["Built FastAPI services", "Added a durable background job worker"],
        }
    ],
    "education": [],
    "projects": [
        {
            "name": "QueueGuard",
            "summary": "Durable background job system",
            "contribution": "Designed the job lifecycle and retry behavior",
            "tech": ["Python", "FastAPI", "PostgreSQL"],
            "link": "",
        }
    ],
    "skills": ["Python", "FastAPI", "PostgreSQL"],
    "spoken_languages": [],
    "private_omitted": ["phone number"],
}

_DEFAULT_BRIEF: dict[str, Any] = {
    "mode": "BRIEF_READY",
    "assistant_message": "I prepared the Discovery brief. Review it and change anything before approving.",
    "brief_title": "Portfolio Discovery Brief — Mock User",
    "brief_markdown": (
        "# Portfolio Discovery Brief — Mock User\n\n"
        "## Portfolio direction at a glance\n\n"
        "Primary goal: secure backend engineering opportunities.\n\n"
        "## Approval summary\n\n"
        "Ready for approval."
    ),
    "user_summary": (
        "Here's the direction: a backend-engineering portfolio built around Mock User's "
        "current work and the QueueGuard project. The full detailed brief is ready for the next stage."
    ),
    "profile": _DEFAULT_PROFILE,
    "open_items": ["no metrics supplied"],
    "memory_update": {},
}

_DEFAULT_BRIEF_REVISED: dict[str, Any] = {
    **_DEFAULT_BRIEF,
    "brief_title": "Portfolio Discovery Brief — Mock User (revised)",
    "brief_markdown": (
        "# Portfolio Discovery Brief — Mock User (revised)\n\n"
        "## Portfolio direction at a glance\n\n"
        "Primary goal: secure backend engineering opportunities. QueueGuard leads the story.\n\n"
        "## Approval summary\n\n"
        "Ready for approval."
    ),
    "user_summary": (
        "Here's the direction: QueueGuard now leads the story, with a clear backend/platform CTA. "
        "The full detailed brief is ready for the next stage."
    ),
}


class _MockModelClient:
    """Test-only deterministic ModelClient used by flow tests. Not a demo feature."""

    def __init__(
        self,
        questions_payload: dict[str, Any] | None = None,
        brief_payload: dict[str, Any] | None = None,
        brief_revised_payload: dict[str, Any] | None = None,
    ) -> None:
        self.questions_payload = questions_payload or _DEFAULT_QUESTIONS
        self.brief_payload = brief_payload or _DEFAULT_BRIEF
        self.brief_revised_payload = brief_revised_payload or _DEFAULT_BRIEF_REVISED
        self.requests: list[dict[str, Any]] = []

    async def complete(self, *, system: str, task: str, **_kwargs: Any) -> str:
        self.requests.append({"system": system, "task": task})
        return "mock complete"

    async def generate_structured(
        self,
        *,
        operation: str,
        instructions: str,
        input_payload: dict[str, Any],
        output_model: Any,
        **_kwargs: Any,
    ) -> Any:
        self.requests.append(
            {"operation": operation, "instructions": instructions, "input_payload": input_payload}
        )
        from oryxenai.agents.discovery.schemas import StructuredModelResult

        if operation in ("understand_and_question", "prepare_questions"):
            parsed = self.questions_payload
        else:
            revision_request = str((input_payload or {}).get("revision_request", "") or "")
            parsed = self.brief_revised_payload if revision_request else self.brief_payload
        parsed_output = output_model.model_validate(parsed).model_dump(mode="json")
        return StructuredModelResult(
            parsed_output=parsed_output,
            response_id="mock-response-id",
            model="mock-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20},
            finish_reason="stop",
            latency_ms=1.0,
        )

    def reset_requests(self) -> None:
        self.requests = []


@pytest.fixture
def mock_model_client() -> _MockModelClient:
    """Deterministic test model client for Discovery flow tests."""
    return _MockModelClient()


# ── Test-only deterministic Content Architect model client ─────────────────

_CA_PLAN_PAYLOAD: dict[str, Any] = {
    "mode": "STRATEGY_AND_CONTENT",
    "content_included": True,
    "integration_needed": False,
    "site_story_strategy": {
        "positioning": "Backend engineer who ships durable systems.",
        "primary_audience": "Hiring managers for backend roles",
        "primary_action": "Contact for an interview",
        "narrative_thesis": "Reliability-minded engineering, told through one real project.",
        "presentation_mode": "single_page",
        "presentation_rationale": "One strong project and a focused profile fit one page.",
    },
    "decision_basis": [
        {
            "decision": "presentation_mode",
            "value": "single_page",
            "basis": "source_derived",
            "confidence": "high",
            "rationale": "Only one well-documented project exists in the snapshot.",
        }
    ],
    "route_plan": [
        {
            "route_id": "home",
            "path": "/",
            "title": "Mock User — Backend Engineer",
            "purpose": "Single-page portfolio home",
            "audience_takeaway": "Can ship and operate backend systems reliably.",
            "priority": "primary",
            "content_density": "medium",
            "section_sequence": ["hero", "about", "project", "contact"],
            "publication_status": "approved",
        }
    ],
    "claim_grounding": [
        {
            "claim_id": "claim_queueguard",
            "statement": "Designed the job lifecycle and retry behavior for QueueGuard.",
            "source_reference": "profile.projects[0]",
            "source_entity_id": "project:queueguard",
            "evidence_status": "verified",
            "ownership": "individual",
            "publication_status": "approved",
        }
    ],
    "page_content_packs": [
        {
            "route_id": "home",
            "sections": [
                {
                    "section_id": "hero",
                    "purpose": "Introduce the positioning.",
                    "content": {"headline": "Backend systems that stay up."},
                    "claim_ids": [],
                    "priority": "primary",
                },
                {
                    "section_id": "project",
                    "purpose": "Feature the strongest project.",
                    "content": {"title": "QueueGuard", "summary": "A durable job system."},
                    "claim_ids": ["claim_queueguard"],
                    "priority": "primary",
                },
            ],
            "internal_notes": {},
        }
    ],
    "public_content_manifest": {
        "nav": [{"label": "Home", "target": "home"}],
        "contact_cta": "Get in touch",
    },
    "unresolved_issues": ["no metrics supplied"],
    "visual_director_handoff": {
        "content_hierarchy": ["hero", "project", "contact"],
        "never_fabricate": ["performance metrics"],
    },
    "memory_update": {},
}

_CA_PLAN_PAYLOAD_REVISED: dict[str, Any] = {
    **_CA_PLAN_PAYLOAD,
    "site_story_strategy": {
        **_CA_PLAN_PAYLOAD["site_story_strategy"],
        "narrative_thesis": "QueueGuard leads the story; reliability-minded engineering throughout.",
    },
}


class _ContentArchitectMockModelClient:
    """Test-only deterministic ModelClient used by Content Architect flow tests.

    Single-page by design (content_included=True) so tests exercise exactly
    one model call unless a test explicitly overrides the payload.
    """

    def __init__(
        self,
        plan_payload: dict[str, Any] | None = None,
        plan_payload_revised: dict[str, Any] | None = None,
    ) -> None:
        self.plan_payload = plan_payload or _CA_PLAN_PAYLOAD
        self.plan_payload_revised = plan_payload_revised or _CA_PLAN_PAYLOAD_REVISED
        self.requests: list[dict[str, Any]] = []

    async def complete(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError

    async def generate_structured(
        self,
        *,
        operation: str,
        instructions: str,
        input_payload: dict[str, Any],
        output_model: Any,
        **_kwargs: Any,
    ) -> Any:
        self.requests.append({"operation": operation, "input_payload": input_payload})
        from oryxenai.agents.discovery.schemas import StructuredModelResult

        if operation != "plan_content":
            raise AssertionError(
                f"unexpected operation for single-page Content Architect mock: {operation}"
            )
        revision_request = str((input_payload or {}).get("revision_request", "") or "")
        parsed = self.plan_payload_revised if revision_request else self.plan_payload
        parsed_output = output_model.model_validate(parsed).model_dump(mode="json")
        return StructuredModelResult(
            parsed_output=parsed_output,
            response_id="mock-response-id",
            model="mock-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20},
            finish_reason="stop",
            latency_ms=1.0,
        )

    def reset_requests(self) -> None:
        self.requests = []


@pytest.fixture
def content_architect_mock_model_client() -> _ContentArchitectMockModelClient:
    """Deterministic test model client for Content Architect flow tests."""
    return _ContentArchitectMockModelClient()


# ── Test-only deterministic Visual Design Director model client ────────────

_VDD_LANGUAGE_PAYLOAD: dict[str, Any] = {
    "mode": "VISUAL_LANGUAGE_AND_PAGES",
    "pages_included": True,
    "integration_needed": False,
    "user_summary": "A restrained, evidence-first visual direction for a single-page portfolio.",
    "visual_language": {
        "creative_thesis": (
            "Reliability engineering as its own aesthetic: restrained, high-contrast, "
            "evidence-first."
        ),
        "color_behavior": "A single confident accent reserved for evidence and action.",
        "typography": "A calm, confident display/body hierarchy with generous vertical rhythm.",
        "motion_character": "Minimal — used only for the one signature evidence moment.",
        "anti_patterns": "No gradients, no glassmorphism, no decorative motion.",
    },
    "shared_visual_systems": {
        "card_treatment": "Flat, bordered panels with no drop shadow.",
    },
    "navigation_direction": {
        "form": "single anchor nav",
        "mobile_strategy": "collapse to a menu button",
    },
    "motion_system": {"global_character": "minimal", "signature_moments": []},
    "interaction_system": {"hover": "subtle lift on interactive cards"},
    "pages": [
        {
            "route_id": "home",
            "path": "/",
            "purpose": "Single-page portfolio home",
            "storyboard": "Hero establishes positioning, then the project evidence, then contact.",
            "responsive_summary": "Single column on mobile; hero and project sections stack.",
            "scenes": [
                {
                    "scene_id": "hero_scene",
                    "route_id": "home",
                    "narrative_goal": "Establish positioning immediately.",
                    "content_refs": ["hero"],
                    "layout_intent": "Text-dominant asymmetric hero.",
                    "responsive_behavior": (
                        "Single column, centered, on mobile; asymmetric two-column on desktop."
                    ),
                },
                {
                    "scene_id": "project_scene",
                    "route_id": "home",
                    "narrative_goal": "Feature the strongest project as evidence.",
                    "content_refs": ["project"],
                    "layout_intent": "Framed evidence panel beside the project narrative.",
                    "responsive_behavior": "Stacks vertically on mobile; side-by-side on desktop.",
                },
            ],
        }
    ],
    "asset_briefs": [],
    "resource_candidates": [],
    "accessibility_and_performance": {
        "contrast": "WCAG AA minimum for all text.",
        "reduced_motion": "No motion is load-bearing.",
    },
    "must_preserve": ["QueueGuard adoption figure"],
    "must_not_fabricate": ["performance metrics"],
    "conflicts": [],
    "warnings": [],
    "compiler_handoff": {},
    "memory_update": {},
}

_VDD_LANGUAGE_PAYLOAD_REVISED: dict[str, Any] = {
    **_VDD_LANGUAGE_PAYLOAD,
    "visual_language": {
        **_VDD_LANGUAGE_PAYLOAD["visual_language"],
        "color_behavior": "A lighter, single warm accent reserved for evidence and action.",
    },
}


class _VisualDesignDirectorMockModelClient:
    """Test-only deterministic ModelClient used by Visual Design Director flow tests.

    Single-page by design (pages_included=True) so tests exercise exactly one
    model call unless a test explicitly overrides the payload.
    """

    def __init__(
        self,
        language_payload: dict[str, Any] | None = None,
        language_payload_revised: dict[str, Any] | None = None,
    ) -> None:
        self.language_payload = language_payload or _VDD_LANGUAGE_PAYLOAD
        self.language_payload_revised = language_payload_revised or _VDD_LANGUAGE_PAYLOAD_REVISED
        self.requests: list[dict[str, Any]] = []

    async def complete(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError

    async def generate_structured(
        self,
        *,
        operation: str,
        instructions: str,
        input_payload: dict[str, Any],
        output_model: Any,
        **_kwargs: Any,
    ) -> Any:
        self.requests.append({"operation": operation, "input_payload": input_payload})
        from oryxenai.agents.discovery.schemas import StructuredModelResult

        if operation != "establish_visual_language":
            raise AssertionError(
                f"unexpected operation for single-page Visual Design Director mock: {operation}"
            )
        revision_request = str((input_payload or {}).get("revision_request", "") or "")
        parsed = self.language_payload_revised if revision_request else self.language_payload
        parsed_output = output_model.model_validate(parsed).model_dump(mode="json")
        return StructuredModelResult(
            parsed_output=parsed_output,
            response_id="mock-response-id",
            model="mock-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20},
            finish_reason="stop",
            latency_ms=1.0,
        )

    def reset_requests(self) -> None:
        self.requests = []


@pytest.fixture
def visual_design_director_mock_model_client() -> _VisualDesignDirectorMockModelClient:
    """Deterministic test model client for Visual Design Director flow tests."""
    return _VisualDesignDirectorMockModelClient()


# ── Ensure the test overlay is loaded for integration / worker tests. ──────

AUTO_CONFTEST_FLAG = "_ORYXENAI_CONFTEST_RAN"


@pytest.fixture(autouse=True)
def _set_test_overlay(monkeypatch, request):
    """Automatically set the test configuration overlay for integration
    and worker tests so they use the dedicated test database."""
    marks = [m.name for m in request.node.iter_markers()]
    if "integration" in marks or "worker" in marks:
        monkeypatch.setenv("OryxenAI_CONFIG_OVERLAY", "config/app.test.toml")
        # Clear cached settings so the overlay takes effect.
        from oryxenai.core.settings import reset_settings

        reset_settings()
        # Ensure only one conftest run sets the overlay (fixtures are re-run
        # per test, but the env var + reset is idempotent).


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


# ── DB fixtures (integration + worker) ─────────────────────────────────────


@pytest_asyncio.fixture
async def test_engine() -> AsyncIterator[AsyncEngine]:
    """Per-test async engine for integration/worker tests.

    Uses the test overlay (config/app.test.toml -> oryxenai_test).
    Creates/drops all tables per test. Skipped when PostgreSQL is unreachable.
    """
    from sqlalchemy import text

    from oryxenai.core.settings import get_settings
    from oryxenai.db.base import Base
    from oryxenai.db.session import get_engine, reset_engine_cache

    reset_engine_cache()

    settings = get_settings()
    try:
        engine = get_engine(settings)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("PostgreSQL unavailable")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
    reset_engine_cache()


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Per-test DB session with automatic cleanup."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    sessionmaker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with sessionmaker() as session:
        yield session
        await session.rollback()
        await session.execute(text("DELETE FROM background_jobs"))
        await session.execute(text("DELETE FROM service_heartbeats"))
        await session.execute(text("DELETE FROM agent_runs"))
        await session.execute(text("DELETE FROM portfolio_sessions"))
        await session.commit()
