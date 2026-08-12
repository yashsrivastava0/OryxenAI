"""Detached development harness for Build Preparation through Phase 3.

Also home to the offline/fixture-fallback generators (`_offline_*`) that
`agent.py` uses when `live_model`/`live_providers` are off — kept here,
next to the harness that is their primary caller, to keep `agent.py`
focused on real pipeline orchestration.
"""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from PIL import Image

from oryxenai.agents.build_preparation.schemas import (
    BuildContextDraft,
    FetchedResource,
    ResourceQuery,
    ResourceSelection,
    RouteBuildContext,
    Stage1QueryPlan,
    Stage2SelectionPlan,
)
from oryxenai.agents.shared.context import build_context
from oryxenai.agents.shared.contracts import AgentKey, ModelClient
from oryxenai.core.settings import Settings
from oryxenai.storage.artifacts import ArtifactStorageError, ArtifactStore


class FixturePreparationError(Exception):
    def __init__(
        self, message: str, *, code: str = "FIXTURE_FAILED", details: dict[str, Any] | None = None
    ) -> None:
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


def _fixture_path(settings: Settings) -> Path:
    configured = Path(settings.build_preparation.fixture_input_path)
    return configured if configured.is_absolute() else Path.cwd() / configured


def _load_default(settings: Settings) -> dict[str, Any]:
    path = _fixture_path(settings)
    if not path.is_file():
        raise FixturePreparationError(
            "The configured VDD fixture file was not found.",
            code="FIXTURE_DEFAULT_NOT_FOUND",
            details={"path": str(path)},
        )
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FixturePreparationError(
            "The configured VDD fixture is not valid JSON.",
            code="FIXTURE_DEFAULT_INVALID",
        ) from exc
    if not isinstance(parsed, dict):
        raise FixturePreparationError(
            "The configured VDD fixture must be a JSON object.",
            code="FIXTURE_DEFAULT_INVALID",
        )
    return parsed


async def run_fixture(
    settings: Settings,
    *,
    raw_override: dict[str, Any] | None = None,
    content_architect_override: dict[str, Any] | None = None,
    live_model: bool = False,
    live_providers: bool = False,
    model_profile: str = "",
    model_client: ModelClient | None = None,
    artifact_store: ArtifactStore | None = None,
) -> dict[str, Any]:
    from oryxenai.agents.build_preparation.agent import BuildPreparationAgent

    raw = raw_override if raw_override is not None else _load_default(settings)
    if isinstance(raw.get("visual_design_director"), dict):
        raw = raw["visual_design_director"]
    run_uuid = uuid4()
    run_id = str(run_uuid)
    if live_model and model_client is None:
        # The provider factory intentionally resolves API keys from the
        # process environment. Ensure the canonical settings loader has
        # exported dotenv-backed secrets before constructing the client.
        from oryxenai.core.settings import get_settings

        get_settings()
        from oryxenai.agents.shared.model_client import build_provider_client

        model_client = build_provider_client(
            "build_preparation",
            settings.models,
            override_profile_name=model_profile or settings.build_preparation.model_profile,
        )
        if model_client is None:
            raise FixturePreparationError(
                "Live model mode requires a configured Build Preparation model profile and API key.",
                code="FIXTURE_MODEL_UNAVAILABLE",
            )
    agent = BuildPreparationAgent(
        model_client=model_client,
        live_model=live_model,
        live_providers=live_providers,
        settings=settings,
        artifact_store=artifact_store,
    )
    context = build_context(
        portfolio_session_id=uuid4(),
        agent_key=AgentKey.BUILD_PREPARATION,
        current_state={},
        agent_input={
            "operation": "build",
            "model_profile": model_profile or settings.build_preparation.model_profile,
            "max_routes": settings.build_preparation.max_routes,
            "visual_design_director": raw,
            "content_architect": content_architect_override or {},
            "live_model": live_model,
            "live_providers": live_providers,
            "output_dir": settings.build_preparation.fixture_output_dir,
            "integration_route_threshold": settings.build_preparation.integration_route_threshold,
            # Offline harness runs still exercise the complete package and
            # read-back flow through MemoryArtifactStore.  An external upload
            # is opt-in with a live model/provider run.
            "artifact_upload": bool(
                settings.build_preparation.fixture_upload and (live_model or live_providers)
            ),
            "debug_mirror": settings.build_preparation.debug_mirror_enabled,
        },
        run_id=run_uuid,
    )
    try:
        result = await agent.run(context)
    except (ValueError, ArtifactStorageError) as exc:
        raise FixturePreparationError(
            str(exc),
            code=getattr(exc, "code", "FIXTURE_INPUT_INVALID"),
            details=getattr(exc, "details", {}),
        ) from exc
    output = dict(result.output)
    return {
        "run_id": run_id,
        "stage": output.get("stage", "phase_3"),
        "status": output.get("status", "ready"),
        "result": output,
        "routes": output.get("routes", []),
        "resource_needs": output.get("resource_needs", []),
        "query_plan": output.get("query_plan"),
        "fetched_candidates": output.get("fetched_candidates", []),
        "selection_plan": output.get("selection_plan"),
        "build_context": output.get("build_context"),
        "materialization": output.get("materialization"),
        "package": output.get("package"),
        "warnings": output.get("warnings", []),
        "events": output.get("events", []),
        "model_calls": output.get("model_calls", 0),
        "provider_calls": output.get("provider_calls", 0),
        "live_model": live_model,
        "live_providers": live_providers,
    }


def _offline_query_plan(needs: list[Any]) -> Stage1QueryPlan:
    queries: list[ResourceQuery] = []
    for need in needs:
        category = f"{need.category} {need.purpose} {' '.join(need.query_terms)}".lower()
        if need.kind == "asset" and any(
            token in category for token in ("photo", "portrait", "editorial", "image")
        ):
            kind = "photo"
        elif need.kind == "resource" and "icon" in category:
            kind = "icon"
        elif need.kind == "resource":
            kind = "component"
        else:
            kind = "custom"
        queries.append(
            ResourceQuery(
                need_id=need.need_id,
                kind=kind,  # type: ignore[arg-type]
                query=" ".join(need.query_terms) or need.purpose or need.category,
                provider_terms=need.query_terms[:5],
                orientation=str(need.details.get("orientation", "") or ""),
                icon_name=(need.query_terms[0] if kind == "icon" and need.query_terms else ""),
                fallback=need.fallback or "Use an explicit custom implementation.",
            )
        )
    return Stage1QueryPlan(queries=queries)


def _offline_candidates(queries: list[ResourceQuery]) -> list[FetchedResource]:
    result: list[FetchedResource] = []
    for query in queries:
        if query.kind == "custom":
            continue
        digest = hashlib.sha256(query.need_id.encode("utf-8")).hexdigest()[:16]
        if query.kind == "photo":
            result.append(
                FetchedResource(
                    resource_id=f"resource-mock-{digest}",
                    need_id=query.need_id,
                    kind="photo",
                    provider="pexels",
                    provider_asset_id=f"mock-{digest}",
                    source_reference="https://www.pexels.com/",
                    preview_url="https://images.pexels.com/",
                    image_url=f"https://images.pexels.com/mock/{digest}.jpg",
                    title="Mock abstract portfolio image",
                    width=640,
                    height=400,
                    orientation="landscape",
                    mime_type="image/png",
                    license="Pexels license",
                )
            )
        elif query.kind == "icon":
            icon = query.icon_name or "sparkles"
            result.append(
                FetchedResource(
                    resource_id=f"resource-mock-icon-{digest}",
                    need_id=query.need_id,
                    kind="icon",
                    provider="lucide",
                    provider_asset_id=icon,
                    source_reference="https://lucide.dev/",
                    icon_name=icon,
                    license="ISC",
                )
            )
        else:
            result.append(
                FetchedResource(
                    resource_id=f"resource-mock-component-{digest}",
                    need_id=query.need_id,
                    kind="component",
                    provider="shadcn",
                    provider_asset_id=f"mock-{digest}",
                    source_reference="https://ui.shadcn.com/",
                    title="Mock adaptable component",
                    source_files={
                        "component.tsx": "export function PreparedComponent() { return null; }"
                    },
                    dependencies=["react"],
                    license="MIT",
                )
            )
    return result


def _offline_selection_plan(
    needs: list[Any], candidates: list[FetchedResource]
) -> Stage2SelectionPlan:
    by_need: dict[str, list[FetchedResource]] = {}
    for candidate in candidates:
        by_need.setdefault(candidate.need_id, []).append(candidate)
    return Stage2SelectionPlan(
        selections=[
            ResourceSelection(
                need_id=need.need_id,
                selected_resource_id=(
                    by_need[need.need_id][0].resource_id if by_need.get(need.need_id) else None
                ),
                why_selected=(
                    "Deterministic offline candidate for local harness verification."
                    if by_need.get(need.need_id)
                    else "No provider candidate was available."
                ),
                fallback=need.fallback or "Use an explicit custom implementation.",
                adaptation_notes="The Code Generator may adapt or ignore this optional resource.",
            )
            for need in needs
        ]
    )


def _offline_context(
    routes: list[Any],
    needs: list[Any],
    selections: Stage2SelectionPlan,
    content: dict[str, Any],
    visual: dict[str, Any],
) -> BuildContextDraft:
    selected_by_need = {
        selection.need_id: selection.selected_resource_id for selection in selections.selections
    }
    route_contexts: list[RouteBuildContext] = []
    for route in routes:
        refs: list[str] = []
        for need in needs:
            selected_id = selected_by_need.get(need.need_id)
            if route.route_id in need.route_ids and selected_id:
                refs.append(selected_id)
        page = next(
            (
                item
                for item in visual.get("pages", [])
                if isinstance(item, dict) and item.get("route_id") == route.route_id
            ),
            {},
        )
        route_contexts.append(
            RouteBuildContext(
                route_id=route.route_id,
                path=route.path,
                brief_markdown=(
                    f"# {route.title or route.route_id}\n\n"
                    f"Purpose: {route.purpose or 'Present the approved portfolio content.'}\n\n"
                    f"Responsive direction: {page.get('responsive_summary', '')}\n\n"
                    "Use approved public content and keep implementation choices flexible."
                ),
                data={"route_id": route.route_id},
                resource_ids=refs,
                acceptance_criteria=list(page.get("acceptance_criteria", []) or []),
                free_to_change=[
                    "DOM structure",
                    "CSS and component composition",
                    "non-load-bearing motion",
                ],
            )
        )
    strategy = content.get("site_story_strategy", {}) if isinstance(content, dict) else {}
    thesis = strategy.get("narrative_thesis", "") if isinstance(strategy, dict) else ""
    return BuildContextDraft(
        overview_markdown=(
            "# Portfolio Build Context\n\n"
            f"{thesis}\n\n"
            "Preserve approved public facts, accessibility requirements, and explicit privacy boundaries."
        ),
        routes=route_contexts,
        runtime_requirements={
            "target_contract": "react-vite-v1",
            "no_runtime_provider_calls": True,
        },
        fixed_facts=list(visual.get("must_preserve", []) or []),
        freedoms=[
            "DOM structure",
            "component composition",
            "exact layout implementation",
            "custom visual technique",
        ],
    )


async def _offline_download(_candidate: FetchedResource) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (640, 400), "#1f2937").save(buffer, format="PNG")
    return buffer.getvalue()


async def _offline_trigger(_candidate: FetchedResource) -> None:
    return None
