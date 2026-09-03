"""Detached development harness for Build Preparation.

Reads the two upstream JSON snapshots from ``Input-Output-Of-Engine/`` (or
the configured fallback paths), runs the real agent pipeline, and returns the
two Markdown briefs plus diagnostics -- no ZIP, no object storage.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from oryxenai.agents.build_preparation.schemas import StageEvent
from oryxenai.agents.shared.context import build_context
from oryxenai.agents.shared.contracts import AgentKey, ModelClient
from oryxenai.agents.shared.model_router import ModelRouter
from oryxenai.core.settings import Settings


class FixturePreparationError(Exception):
    def __init__(
        self, message: str, *, code: str = "FIXTURE_FAILED", details: dict[str, Any] | None = None
    ) -> None:
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


EventSink = Callable[[StageEvent], Awaitable[None]]


def resolve_fixture_model_profile(
    settings: Settings,
    requested: str = "",
    visual_input: dict[str, Any] | None = None,
) -> str:
    """Return a selectable fixture override, or empty for engine routing.

    ``build_preparation`` is a logical engine route, not a selectable UI
    profile. Detached runs may receive a real selectable profile from the
    approved VDD snapshot, so preserve that choice without treating the
    internal route name as an explicit override.
    """

    router = ModelRouter(settings.models)
    explicit = str(requested or "").strip()
    if explicit:
        if not router.is_selectable(explicit):
            raise FixturePreparationError(
                f"Model profile '{explicit}' is not selectable. Choose an allowlisted pipeline profile.",
                code="FIXTURE_MODEL_PROFILE_INVALID",
            )
        return explicit
    input_profile = ""
    if isinstance(visual_input, dict):
        input_profile = str(visual_input.get("model_profile", "") or "").strip()
    if input_profile and router.is_selectable(input_profile):
        return input_profile
    configured = str(settings.build_preparation.model_profile or "").strip()
    if configured and router.is_selectable(configured):
        return configured
    return ""


def fixture_storage_preflight(settings: Settings) -> dict[str, Any]:
    """Return fixture dependency readiness without revealing credential values."""
    pexels_env = str(settings.resource_providers.pexels_api_key_env or "PEXELS_API_KEY")
    pixabay_env = str(settings.resource_providers.pixabay_api_key_env or "PIXABAY_API_KEY")
    resources = {
        "pexels": {
            "status": "ready" if os.getenv(pexels_env, "") else "not_configured",
            "message": (
                "Pexels image discovery is ready."
                if os.getenv(pexels_env, "")
                else "Pexels is unavailable; image roles will be reported as no material found."
            ),
            "missing": [] if os.getenv(pexels_env, "") else [pexels_env],
        },
        "pixabay": {
            "status": "ready" if os.getenv(pixabay_env, "") else "not_configured",
            "message": (
                "Pixabay image discovery is ready."
                if os.getenv(pixabay_env, "")
                else "Pixabay is unavailable; the other configured image provider will be tried."
            ),
            "missing": [] if os.getenv(pixabay_env, "") else [pixabay_env],
        },
    }
    inputs = _fixture_input_preflight(settings)
    return {"resources": resources, "inputs": inputs}


def _configured_path(value: str) -> Path:
    configured = Path(value)
    return configured if configured.is_absolute() else Path.cwd() / configured


def _attached_output_path(kind: str) -> Path | None:
    """Find the newest matching engine output in the detached input folder."""
    folder = Path.cwd() / "Input-Output-Of-Engine"
    if not folder.is_dir():
        return None
    tokens = ("visual", "design", "director") if kind == "visual" else ("content", "architect")
    candidates: list[Path] = []
    for path in folder.iterdir():
        if not path.is_file() or path.suffix.casefold() not in {".json", ".md", ".markdown"}:
            continue
        stem = path.stem.casefold()
        if all(token in stem for token in tokens):
            candidates.append(path)
    if not candidates:
        return None
    return max(candidates, key=lambda path: (path.stat().st_mtime_ns, path.name.casefold()))


def _fixture_path(settings: Settings) -> Path:
    attached = _attached_output_path("visual")
    if attached is not None:
        return attached
    return _configured_path(settings.build_preparation.fixture_input_path)


def _content_snapshot_path(settings: Settings) -> Path:
    attached = _attached_output_path("content")
    if attached is not None:
        return attached
    return _configured_path(settings.build_preparation.fixture_content_input_path)


def _fixture_input_preflight(settings: Settings) -> dict[str, dict[str, str]]:
    visual = _fixture_path(settings)
    content = _content_snapshot_path(settings)
    return {
        "visual_design_director": {
            "status": "ready" if visual.is_file() else "not_found",
            "path": str(visual),
        },
        "content_architect": {
            "status": "ready" if content.is_file() else "not_found",
            "path": str(content),
        },
    }


def _read_json_object(path: Path, *, label: str, code: str) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise FixturePreparationError(
            f"The {label} output could not be read.", code=code, details={"path": str(path)}
        ) from exc
    try:
        parsed: Any = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
        for block in re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL):
            try:
                parsed = json.loads(block)
                break
            except json.JSONDecodeError:
                continue
        if parsed is None:
            raise FixturePreparationError(
                f"The {label} output is not valid JSON.", code=code, details={"path": str(path)}
            ) from None
    if not isinstance(parsed, dict):
        raise FixturePreparationError(
            f"The {label} output must be a JSON object.", code=code, details={"path": str(path)}
        )
    return parsed


def _load_default(settings: Settings) -> dict[str, Any]:
    path = _fixture_path(settings)
    if not path.is_file():
        raise FixturePreparationError(
            "The configured VDD fixture file was not found.",
            code="FIXTURE_DEFAULT_NOT_FOUND",
            details={"path": str(path)},
        )
    return _read_json_object(path, label="Visual Design Director", code="FIXTURE_DEFAULT_INVALID")


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
    stamps the production session flow would have on an approved stage so a
    default fixture run behaves like a real approved handoff.
    """

    visual = dict(raw)
    if content_architect_override is not None:
        content = dict(content_architect_override)
    else:
        content = _load_content_snapshot(settings)
        if not content:
            raw_intake = raw.get("intake")
            intake = raw_intake if isinstance(raw_intake, dict) else {}
            content = dict(intake) if intake.get("route_plan") else {}
    ca_hash = str((raw.get("source_ref") or {}).get("content_architect_content_hash", "") or "")
    if content and (
        not isinstance(content.get("approved"), dict)
        or not str((content.get("approved") or {}).get("content_hash", "") or "")
    ):
        stamped = dict(content)
        stamped["approved"] = {
            "content_hash": ca_hash or _fixture_direction_hash(content),
        }
        content = stamped
    if content and (
        not isinstance(visual.get("approved"), dict)
        or not str((visual.get("approved") or {}).get("visual_direction_hash", "") or "")
    ):
        visual["approved"] = {"visual_direction_hash": _fixture_direction_hash(raw)}
    return content, visual


def _load_content_snapshot(settings: Settings) -> dict[str, Any]:
    path = _content_snapshot_path(settings)
    if not path.is_file():
        return {}
    try:
        parsed = _read_json_object(
            path, label="Content Architect", code="FIXTURE_CONTENT_INPUT_INVALID"
        )
    except FixturePreparationError:
        if _attached_output_path("content") == path:
            raise
        return {}
    if not isinstance(parsed, dict) or not isinstance(parsed.get("route_plan"), list):
        if _attached_output_path("content") == path:
            raise FixturePreparationError(
                "The attached Content Architect output must include a route_plan.",
                code="FIXTURE_CONTENT_INPUT_INVALID",
                details={"path": str(path)},
            )
        return {}
    if not parsed["route_plan"]:
        if _attached_output_path("content") == path:
            raise FixturePreparationError(
                "The attached Content Architect output contains no routes.",
                code="FIXTURE_CONTENT_INPUT_INVALID",
                details={"path": str(path)},
            )
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
    event_sink: EventSink | None = None,
    run_id: str | None = None,
    local_result_root: str | None = None,
) -> dict[str, Any]:
    from oryxenai.agents.build_preparation.agent import BuildPreparationAgent

    raw = raw_override if raw_override is not None else _load_default(settings)
    if isinstance(raw.get("visual_design_director"), dict):
        raw = raw["visual_design_director"]
    content_override, raw = _fixture_inputs(settings, raw, content_architect_override)
    profile_override = resolve_fixture_model_profile(settings, model_profile, raw)
    resolved_profile = ModelRouter(settings.models).resolve_profile_name(
        "build_preparation", profile_override
    )
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
            override_profile_name=profile_override,
        )
        if model_client is None:
            raise FixturePreparationError(
                "Live model mode requires a configured Build Preparation model profile and API key.",
                code="FIXTURE_MODEL_UNAVAILABLE",
            )
        created_model_client = True
    agent = BuildPreparationAgent(
        model_client=model_client,
        settings=settings,
        live_model=live_model,
        live_providers=live_providers,
        profile_name=resolved_profile,
        event_sink=event_sink,
    )
    context = build_context(
        portfolio_session_id=uuid4(),
        agent_key=AgentKey.BUILD_PREPARATION,
        current_state={},
        agent_input={
            "model_profile": resolved_profile,
            "max_routes": settings.build_preparation.max_routes,
            "visual_design_director": raw,
            "content_architect": content_override,
            "debug_mirror": settings.build_preparation.debug_mirror_enabled,
            "output_dir": settings.build_preparation.fixture_output_dir,
            "debug_mirror_dir": local_result_root or "",
        },
        run_id=run_uuid,
    )
    try:
        result = await agent.run(context)
    except ValueError as exc:
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
    return {
        "run_id": resolved_run_id,
        "status": "ready",
        "result": output,
        "routes": output.get("routes", []),
        "resource_needs": output.get("resource_needs", []),
        "resource_index": output.get("resource_index", []),
        "component_index": output.get("component_index", []),
        "content_brief_markdown": output.get("content_brief_markdown", ""),
        "visual_brief_markdown": output.get("visual_brief_markdown", ""),
        "target_contract": output.get("target_contract", ""),
        "recommended_dependencies": output.get("recommended_dependencies", []),
        "debug_mirror_path": output.get("debug_mirror_path", ""),
        "warnings": output.get("warnings", []),
        "events": output.get("events", []),
        "model_calls": output.get("model_calls", 0),
        "provider_calls": output.get("provider_calls", 0),
        "visual_input_mode": output.get("visual_input_mode", "approved_vdd"),
        "assumption_hash": output.get("assumption_hash", ""),
        "assumptions": output.get("assumptions", []),
        "live_model": live_model,
        "live_providers": live_providers,
        "storage": storage,
    }
