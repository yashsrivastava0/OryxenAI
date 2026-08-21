"""Provider-neutral model client infrastructure.

Reads provider profiles from config/models.toml. Builds concrete provider
adapters through the factory in providers/. Agent code depends on the
ModelClient protocol, never on a provider module.

When no real profile is configured (or no API key is set at startup),
`build_model_client()` returns a `MockModelClient`. This lets the application
start without any model credentials.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from oryxenai.agents.shared.contracts import ModelClient
from oryxenai.agents.shared.model_router import ModelRouter
from oryxenai.core.logging import get_logger

if TYPE_CHECKING:
    from oryxenai.core.settings import ModelConfig, ModelProfile

logger = get_logger("oryxenai.agents.model_client")


class MockModelClient:
    """A no-network ModelClient that returns a fixed placeholder.

    Used as fallback when no provider is configured or no API key is set.
    The application can start and pass contract tests without credentials.
    """

    async def complete(
        self,
        system_prompt: str,
        task_prompt: str,
        request_params: dict[str, Any] | None = None,
    ) -> str:
        return "[mock-model-output]"

    async def generate_structured(
        self,
        *,
        operation: str,
        instructions: str,
        input_payload: Mapping[str, object],
        output_model: type[BaseModel],
        system_prompt: str | None = None,
        model_profile: Any = None,
        request_context: Any = None,
        strict_schema: bool = False,
    ) -> Any:
        return _mock_structured_result(output_model)


def _mock_structured_result(output_model: type[BaseModel]) -> Any:
    """Build a deterministic StructuredModelResult for the given output model.

    Discovery, Content Architect, Visual Design Director, and Code Generator
    (SitePlan) output models each get a valid minimal envelope so the
    mock-runs dev harness can execute those agents without network access.
    Any other model falls back to an empty instance.
    """
    from oryxenai.agents.code_generator.core.development_schemas import SitePlan, WorkGraph
    from oryxenai.agents.content_architect.schemas import (
        ClaimGrounding,
        ContentArchitectOutput,
        ContentPlanMode,
        ContentSection,
        DecisionBasis,
        DecisionRecord,
        EvidenceStatus,
        Ownership,
        PageContentPack,
        PublicationStatus,
        RoutePlanEntry,
    )
    from oryxenai.agents.discovery.schemas import (
        BriefOutput,
        DiscoveryQuestion,
        ExperienceEntry,
        OperationMode,
        ProjectEntry,
        QuestionKind,
        QuestionOption,
        QuestionSetOutput,
        StructuredModelResult,
        StructuredProfile,
    )
    from oryxenai.agents.visual_design_director.schemas import (
        PageVisualDirection,
        SceneDirection,
        VisualDesignDirectorOutput,
        VisualPlanMode,
    )

    parsed: BaseModel | None
    if output_model is SitePlan:
        parsed = SitePlan(
            plan_id="plan-mock",
            routes=[],
            work_graph=WorkGraph(units=[]),
        )
    elif output_model is QuestionSetOutput:
        parsed = QuestionSetOutput(
            mode=OperationMode.ASK_QUESTIONS,
            assistant_message="I have enough to ask a few focused questions.",
            questions=[
                DiscoveryQuestion(
                    id="target_direction",
                    text="Should the portfolio lead with backend or full-stack?",
                    kind=QuestionKind.SINGLE_SELECT,
                    options=[
                        QuestionOption(id="backend", label="Backend"),
                        QuestionOption(id="fullstack", label="Full-stack"),
                        QuestionOption(id="balanced", label="Balanced"),
                    ],
                )
            ],
            memory_update={"intent_summary": "Backend engineering roles", "open_items": []},
        )
    elif output_model is BriefOutput:
        parsed = BriefOutput(
            mode=OperationMode.BRIEF_READY,
            assistant_message="I prepared the Discovery brief. Review it and change anything before approving.",
            brief_title="Portfolio Discovery Brief — Mock User",
            brief_markdown=(
                "# Portfolio Discovery Brief — Mock User\n\n"
                "## Portfolio direction at a glance\n\n"
                "**Primary goal:** Create a portfolio that helps the user move forward.\n\n"
                "## Approval summary\n\n"
                "Ready for approval."
            ),
            user_summary=(
                "Here's the direction: a portfolio built around the user's current work. "
                "The full detailed brief is ready for the next stage."
            ),
            profile=StructuredProfile(
                name="Mock User",
                current_title="Software Engineer",
                experience=[
                    ExperienceEntry(
                        organization="Mock Company", role="Software Engineer", dates="2023-present"
                    )
                ],
                projects=[ProjectEntry(name="Mock Project", summary="A sample project.")],
                skills=["Python"],
            ),
            open_items=["no metrics supplied"],
            memory_update={},
        )
    elif output_model is ContentArchitectOutput:
        parsed = ContentArchitectOutput(
            mode=ContentPlanMode.STRATEGY_AND_CONTENT,
            content_included=True,
            integration_needed=False,
            site_story_strategy={
                "positioning": "Backend engineer who ships durable systems.",
                "primary_audience": "Hiring managers for backend/platform roles",
                "primary_action": "Contact for an interview",
                "narrative_thesis": "Reliability-minded engineering, told through one real project.",
                "presentation_mode": "single_page",
                "presentation_rationale": "One strong project and a focused profile fit one page.",
            },
            decision_basis=[
                DecisionRecord(
                    decision="presentation_mode",
                    value="single_page",
                    basis=DecisionBasis.SOURCE_DERIVED,
                    confidence="high",
                    rationale="Only one well-documented project exists in the snapshot.",
                )
            ],
            route_plan=[
                RoutePlanEntry(
                    route_id="home",
                    path="/",
                    title="Mock User — Backend Engineer",
                    purpose="Single-page portfolio home",
                    audience_takeaway="Can ship and operate backend systems reliably.",
                    priority="primary",
                    content_density="medium",
                    section_sequence=["hero", "about", "project", "contact"],
                    publication_status=PublicationStatus.APPROVED,
                )
            ],
            claim_grounding=[
                ClaimGrounding(
                    claim_id="claim_queueguard",
                    statement="Designed the job lifecycle and retry behavior for QueueGuard.",
                    source_reference="profile.projects[0]",
                    source_entity_id="project:queueguard",
                    evidence_status=EvidenceStatus.VERIFIED,
                    ownership=Ownership.INDIVIDUAL,
                    publication_status=PublicationStatus.APPROVED,
                )
            ],
            page_content_packs=[
                PageContentPack(
                    route_id="home",
                    sections=[
                        ContentSection(
                            section_id="hero",
                            purpose="Introduce the positioning.",
                            content={"headline": "Backend systems that stay up."},
                            claim_ids=[],
                            priority="primary",
                        ),
                        ContentSection(
                            section_id="project",
                            purpose="Feature the strongest project.",
                            content={"title": "QueueGuard", "summary": "A durable job system."},
                            claim_ids=["claim_queueguard"],
                            priority="primary",
                        ),
                    ],
                    internal_notes={},
                )
            ],
            public_content_manifest={
                "nav": [{"label": "Home", "target": "home"}],
                "contact_cta": "Get in touch",
            },
            unresolved_issues=["no metrics supplied"],
            visual_director_handoff={
                "content_hierarchy": ["hero", "project", "contact"],
                "never_fabricate": ["performance metrics"],
            },
            memory_update={},
        )
    elif output_model is VisualDesignDirectorOutput:
        parsed = VisualDesignDirectorOutput(
            mode=VisualPlanMode.VISUAL_LANGUAGE_AND_PAGES,
            pages_included=True,
            integration_needed=False,
            user_summary="A restrained, evidence-first visual direction for a single-page portfolio.",
            visual_language={
                "creative_thesis": "Reliability engineering as its own aesthetic: restrained, high-contrast, evidence-first.",
                "color_behavior": "A single confident accent reserved for evidence and action.",
                "typography": "A calm, confident display/body hierarchy with generous vertical rhythm.",
                "motion_character": "Minimal — used only to draw attention to the one signature evidence moment.",
                "anti_patterns": "No gradients, no glassmorphism, no decorative motion.",
            },
            shared_visual_systems={
                "card_treatment": "Flat, bordered panels with no drop shadow.",
                "section_dividers": "Generous whitespace instead of visible rule lines.",
            },
            navigation_direction={
                "form": "single anchor nav",
                "mobile_strategy": "collapse to a menu button",
            },
            motion_system={"global_character": "minimal", "signature_moments": []},
            interaction_system={"hover": "subtle lift on interactive cards"},
            pages=[
                PageVisualDirection(
                    route_id="home",
                    path="/",
                    purpose="Single-page portfolio home",
                    storyboard="Hero establishes positioning, then the project evidence, then contact.",
                    responsive_summary="Single column on mobile; hero and project sections stack.",
                    scenes=[
                        SceneDirection(
                            scene_id="hero_scene",
                            route_id="home",
                            narrative_goal="Establish positioning immediately.",
                            content_refs=["hero"],
                            layout_intent="Text-dominant asymmetric hero.",
                            responsive_behavior=(
                                "Single column, centered, on mobile; asymmetric two-column on desktop."
                            ),
                        )
                    ],
                )
            ],
            accessibility_and_performance={
                "contrast": "WCAG AA minimum for all text.",
                "reduced_motion": "No motion is load-bearing.",
            },
            must_preserve=["QueueGuard adoption figure"],
            must_not_fabricate=["performance metrics"],
            memory_update={},
        )
    else:
        try:
            parsed = output_model()
        except Exception:
            parsed = None

    if parsed is None:
        parsed_output: dict[str, Any] = {}
    elif isinstance(parsed, StructuredModelResult):
        return parsed
    elif isinstance(parsed, BaseModel):
        parsed_output = parsed.model_dump(mode="json")
    else:
        parsed_output = dict(parsed)

    return StructuredModelResult(
        parsed_output=parsed_output,
        response_id="mock-response-id",
        model="mock-model",
        usage={"prompt_tokens": 10, "completion_tokens": 20},
        finish_reason="stop",
        latency_ms=1.0,
    )


def resolve_api_key(profile: ModelProfile) -> str | None:
    """Resolve a profile's API key indirectly via its api_key_env name."""
    import os

    if not profile.api_key_env:
        return None
    return os.environ.get(profile.api_key_env)


def build_model_client(model_config: ModelConfig) -> ModelClient:
    """Build a ModelClient for the given config.

    Returns a real provider adapter when a profile is configured and the
    required API key environment variable is set. Falls back to
    MockModelClient otherwise — the application starts without credentials.
    """
    from oryxenai.agents.shared.providers.factory import build_adapter, can_build

    router = ModelRouter(model_config)
    profile_name = router.resolve_profile_name("default")
    profile = model_config.get_profile(profile_name)
    if profile is not None and profile.provider and can_build(profile):
        key = resolve_api_key(profile)
        if key:
            logger.info(
                "building real model client for provider=%s model=%s",
                profile.provider,
                profile.model or "(default)",
            )
            return build_adapter(profile)
        logger.info(
            "provider '%s' configured but API key env var '%s' is not set — using mock client",
            profile.provider,
            profile.api_key_env,
        )
        return MockModelClient()

    if profile is not None:
        logger.info(
            "model profile '%s' provider='%s' not recognised — using mock client",
            profile_name,
            profile.provider,
        )
    return MockModelClient()


def build_provider_client(
    profile_name: str,
    model_config: ModelConfig,
    *,
    override_profile_name: str | None = None,
) -> ModelClient | None:
    """Build the configured provider adapter for a logical engine/profile."""
    from oryxenai.agents.shared.providers.factory import build_adapter, can_build

    router = ModelRouter(model_config)
    requested_override = str(override_profile_name or "").strip()
    if requested_override and not router.is_selectable(requested_override):
        logger.warning(
            "override profile '%s' is not selectable - using configured route for '%s'",
            requested_override,
            profile_name,
        )
        requested_override = ""
    resolved_name = router.resolve_profile_name(profile_name, requested_override)

    profile = model_config.get_profile(resolved_name)
    if profile is None:
        logger.warning("profile '%s' not found in config/models.toml", resolved_name)
        return None

    if not profile.provider or not can_build(profile):
        logger.warning(
            "profile '%s' provider '%s' is not supported", resolved_name, profile.provider
        )
        return None

    key = resolve_api_key(profile)
    if not key:
        logger.warning(
            "profile '%s' API key env var '%s' is not set",
            resolved_name,
            profile.api_key_env,
        )
        return None

    logger.info("using model route '%s' -> profile '%s'", profile_name, resolved_name)
    logger.info("building %s adapter for profile '%s'", profile.provider, resolved_name)
    return build_adapter(profile)
