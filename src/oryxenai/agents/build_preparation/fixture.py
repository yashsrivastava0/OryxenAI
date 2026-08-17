"""Detached development harness for Build Preparation through Phase 3.

Also home to the offline/fixture-fallback generators (`_offline_*`) that
`agent.py` uses when `live_model`/`live_providers` are off — kept here,
next to the harness that is their primary caller, to keep `agent.py`
focused on real pipeline orchestration.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from oryxenai.agents.build_preparation.schemas import (
    BuildContextDraft,
    FetchedResource,
    ResourceQuery,
    ResourceSelection,
    RouteBuildContext,
    Stage1QueryPlan,
    Stage2SelectionPlan,
    StageEvent,
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


EventSink = Callable[[StageEvent], Awaitable[None]]


def fixture_storage_preflight(settings: Settings) -> dict[str, Any]:
    """Return fixture dependency readiness without revealing credential values."""
    config = settings.artifact_storage
    requested = bool(settings.build_preparation.fixture_upload)
    provider = str(config.provider or "")
    r2: dict[str, Any] = {
        "requested": requested,
        "provider": provider,
        "status": "not_requested",
        "message": "R2 upload is disabled for this fixture.",
        "missing": [],
    }
    pexels_env = str(settings.resource_providers.pexels_api_key_env or "PEXELS_API_KEY")
    resources = {
        "pexels": {
            "status": "ready" if os.getenv(pexels_env, "") else "not_configured",
            "message": (
                "Optional editorial-image lookup is ready."
                if os.getenv(pexels_env, "")
                else "Pexels is unavailable; required visual roles will remain execution gaps."
            ),
            "missing": [] if os.getenv(pexels_env, "") else [pexels_env],
        }
    }
    if not requested:
        return {"local": {"status": "ready"}, "r2": r2, "resources": resources}
    if provider not in {"r2_s3", "s3"}:
        r2.update(
            {
                "status": "not_configured",
                "message": "Configured artifact storage is not S3-compatible.",
            }
        )
        return {"local": {"status": "ready"}, "r2": r2, "resources": resources}
    missing = [
        name for name in (config.access_key_env, config.secret_key_env) if not os.getenv(name, "")
    ]
    if not config.endpoint_url or not config.bucket:
        missing.append("artifact_storage_configuration")
    if missing:
        r2.update(
            {
                "status": "not_configured",
                "message": "R2 upload is unavailable until its artifact storage configuration is complete.",
                "missing": missing,
            }
        )
    else:
        r2.update(
            {
                "status": "ready",
                "message": "R2 upload and read-back verification are ready.",
            }
        )
    return {"local": {"status": "ready"}, "r2": r2, "resources": resources}


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


def _fixture_direction_hash(visual: dict[str, Any]) -> str:
    """Deterministic stand-in for the approval hash production stamps on VDD approval."""
    import hashlib

    encoded = json.dumps(visual, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _fixture_inputs(
    settings: Settings,
    raw: dict[str, Any],
    content_architect_override: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve the (CA, VDD) pair the detached fixture compiles from.

    Preference order: an explicit CA override, the configured Content
    Architect snapshot on disk (reuniting the real pair the VDD output came
    from), then the VDD output's own ``intake``. The pair gets the approval
    stamps the production session flow would have on an approved stage, so
    the default fixture run produces a canonical v3 handoff-eligible pack
    instead of a legacy review-only one.
    """

    visual = dict(raw)
    if content_architect_override is not None:
        return content_architect_override, visual
    content = _load_content_snapshot(settings)
    if not content:
        raw_intake = raw.get("intake")
        intake = raw_intake if isinstance(raw_intake, dict) else {}
        content = dict(intake) if intake.get("route_plan") else {}
    ca_hash = str((raw.get("source_ref") or {}).get("content_architect_content_hash", "") or "")
    if content and not isinstance(content.get("approved"), dict):
        stamped = dict(content)
        stamped["approved"] = {"content_hash": ca_hash} if ca_hash else {}
        content = stamped
    if content and not isinstance(visual.get("approved"), dict):
        visual["approved"] = {"visual_direction_hash": _fixture_direction_hash(raw)}
    return content, visual


def _load_content_snapshot(settings: Settings) -> dict[str, Any]:
    import json as _json

    configured = Path(settings.build_preparation.fixture_content_input_path)
    path = configured if configured.is_absolute() else Path.cwd() / configured
    if not path.is_file():
        return {}
    try:
        parsed = _json.loads(path.read_text(encoding="utf-8"))
    except (OSError, _json.JSONDecodeError):
        return {}
    if not isinstance(parsed, dict) or not isinstance(parsed.get("route_plan"), list):
        return {}
    if not parsed["route_plan"]:
        return {}
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
    event_sink: EventSink | None = None,
    run_id: str | None = None,
    local_result_root: str | None = None,
) -> dict[str, Any]:
    from oryxenai.agents.build_preparation.agent import BuildPreparationAgent

    raw = raw_override if raw_override is not None else _load_default(settings)
    if isinstance(raw.get("visual_design_director"), dict):
        raw = raw["visual_design_director"]
    content_override, raw = _fixture_inputs(settings, raw, content_architect_override)
    run_uuid = uuid4() if run_id is None else UUID(run_id)
    resolved_run_id = str(run_uuid)
    storage = fixture_storage_preflight(settings)
    created_model_client = False
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
        created_model_client = True
    agent = BuildPreparationAgent(
        model_client=model_client,
        live_model=live_model,
        live_providers=live_providers,
        settings=settings,
        artifact_store=artifact_store,
        event_sink=event_sink,
    )
    context = build_context(
        portfolio_session_id=uuid4(),
        agent_key=AgentKey.BUILD_PREPARATION,
        current_state={},
        agent_input={
            "operation": "build",
            "model_profile": model_profile or settings.build_preparation.model_profile,
            "max_routes": settings.build_preparation.max_routes,
            "editorial_image_budget": settings.build_preparation.editorial_image_budget,
            "visual_design_director": raw,
            "content_architect": content_override,
            # The detached fixture follows the same canonical v3 route layout
            # as production. Historical mirrors remain archive diagnostics and
            # are not generated here because v3 admission rejects aliases.
            "legacy_route_layout": False,
            "live_model": live_model,
            "live_providers": live_providers,
            "output_dir": settings.build_preparation.fixture_output_dir,
            "integration_route_threshold": settings.build_preparation.integration_route_threshold,
            # Fixture runs always materialize a local result. R2 upload is
            # attempted independently whenever its configured credentials are ready.
            "artifact_upload": storage["r2"]["status"] == "ready",
            "debug_mirror": settings.build_preparation.fixture_debug_mirror_enabled,
            "local_result_root": local_result_root or "",
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
    finally:
        if created_model_client and model_client is not None:
            close = getattr(model_client, "aclose", None)
            if close is not None:
                await close()
    output = dict(result.output)
    if storage["r2"]["status"] == "ready":
        storage["r2"] = {
            **storage["r2"],
            "status": "verified",
            "message": "R2 upload and read-back verification completed.",
            "artifact": output.get("package", {}).get("artifact"),
        }
    return {
        "run_id": resolved_run_id,
        "stage": output.get("stage", "phase_3"),
        "status": output.get("status", "ready"),
        "result": output,
        "routes": output.get("routes", []),
        "resource_needs": output.get("resource_needs", []),
        "query_plan": output.get("query_plan"),
        "fetched_candidates": output.get("fetched_candidates", []),
        "selection_plan": output.get("selection_plan"),
        "candidate_qualifications": output.get("candidate_qualifications", []),
        "build_context": output.get("build_context"),
        "materialization": output.get("materialization"),
        "package": output.get("package"),
        "handoff_report": output.get("handoff_report", {}),
        "warnings": output.get("warnings", []),
        "events": output.get("events", []),
        "model_calls": output.get("model_calls", 0),
        "provider_calls": output.get("provider_calls", 0),
        "provider_cache_hits": output.get("provider_cache_hits", 0),
        "provider_rate_limit_events": output.get("provider_rate_limit_events", 0),
        "live_model": live_model,
        "live_providers": live_providers,
        "storage": storage,
    }


def _offline_query_plan(needs: list[Any]) -> Stage1QueryPlan:
    queries: list[ResourceQuery] = []
    for need in needs:
        category = f"{need.category} {need.purpose} {' '.join(need.query_terms)}".lower()
        if need.category.casefold() in {"font", "typography", "type_system"}:
            kind = "font"
        elif bool(getattr(need, "required_for_handoff", False)) or (
            need.kind == "asset"
            and any(token in category for token in ("photo", "portrait", "editorial", "image"))
        ):
            kind = "photo"
        elif need.kind == "resource" and "icon" in category:
            kind = "icon"
        elif need.kind == "resource" and str(need.category or "") not in {
            "hero_pattern",
            "background_system",
            "diagram_primitive",
        }:
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
                required_for_handoff=bool(getattr(need, "required_for_handoff", False)),
                allowed_providers=["fontsource"]
                if kind == "font"
                else ["pexels"]
                if bool(getattr(need, "required_for_handoff", False))
                else [],
            )
        )
    return Stage1QueryPlan(queries=queries)


def _offline_candidates(queries: list[ResourceQuery]) -> list[FetchedResource]:
    """Return only honest package metadata; never fabricate visual material.

    Offline fixture runs are useful for exercising the compiler and gap
    reporting, but an image or component needs real provider bytes/source. A
    mock photo/component would make the UI look populated while producing an
    inadmissible pack, so those candidates are deliberately omitted.
    """
    result: list[FetchedResource] = []
    for query in queries:
        if query.kind == "custom":
            continue
        digest = hashlib.sha256(query.need_id.encode("utf-8")).hexdigest()[:16]
        if query.kind == "photo":
            continue
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
                    license_reference="https://github.com/lucide-icons/lucide/blob/main/LICENSE",
                )
            )
        elif query.kind == "font":
            # Provider-free fixtures intentionally exercise the typed local
            # typography recipe; live Fontsource materialization is opt-in.
            continue
        else:
            # Registry source is also unavailable offline. Leave the need
            # unresolved so execution.py emits VDD_EXECUTION_GAP.
            continue
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
