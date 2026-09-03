"""In-process, file-backed monitoring for detached Build Preparation fixture runs.

This development-only manager deliberately does not use the durable production
job queue. It gives the fixture UI immediate progress while retaining a safe,
timestamped diagnostic report and the two Markdown briefs in the ignored
``output/`` tree.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from oryxenai.agents.build_preparation.fixture import (
    fixture_storage_preflight,
    run_fixture,
)
from oryxenai.agents.build_preparation.schemas import StageEvent
from oryxenai.core.settings import Settings

_INDIA_TIME = timezone(timedelta(hours=5, minutes=30), name="IST")


class FixtureRunConflictError(Exception):
    """A fixture run is already consuming the single development slot."""


class FixtureRunNotFoundError(Exception):
    """The requested fixture run has no retained report."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _event(event_id: str, stage: str, message: str, *, level: str = "info") -> dict[str, Any]:
    return {
        "event_id": event_id,
        "stage": stage,
        "level": level,
        "message": message,
        "details": {},
        "timestamp": _now(),
    }


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd())).replace("\\", "/")
    except ValueError:
        return str(path)


def _safe_details(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    try:
        decoded = json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except (TypeError, ValueError):
        return {}
    return cast(dict[str, Any], decoded) if isinstance(decoded, dict) else {}


def _issue_from_error(exc: Exception) -> dict[str, Any]:
    code = str(getattr(exc, "code", "FIXTURE_RUN_FAILED") or "FIXTURE_RUN_FAILED")
    message = str(getattr(exc, "message", str(exc)) or "Build Preparation fixture failed.")
    messages = {
        "PROVIDER_CONNECTION_ERROR": (
            "The configured model provider could not be reached while composing the visual brief."
        ),
        "PROVIDER_TIMEOUT_ERROR": (
            "The configured model provider timed out while composing the visual brief."
        ),
        "PROVIDER_AUTH_ERROR": (
            "The configured model provider rejected its API key while composing the visual brief."
        ),
        "PROVIDER_RATE_LIMIT_ERROR": (
            "The configured model provider rate-limited visual-brief composition."
        ),
        "PROVIDER_SERVER_ERROR": (
            "The configured model provider returned a server error while composing the visual brief."
        ),
    }
    message = messages.get(code, message)
    actions = {
        "FIXTURE_MODEL_UNAVAILABLE": (
            "Check the configured Build Preparation model profile and its API-key environment variable."
        ),
        "PROVIDER_CONNECTION_ERROR": (
            "The live model endpoint could not be reached. Check network access and the configured "
            "model profile endpoint, then retry."
        ),
        "PROVIDER_TIMEOUT_ERROR": (
            "The live model endpoint timed out. Check network access or increase the configured "
            "provider timeout, then retry."
        ),
        "PROVIDER_AUTH_ERROR": (
            "The live model provider rejected the API key. Verify the configured key environment "
            "variable and provider account, then retry."
        ),
        "PROVIDER_RATE_LIMIT_ERROR": (
            "The live model provider rate-limited this run. Wait for the provider window to reset, "
            "then retry once."
        ),
        "PROVIDER_SERVER_ERROR": "The live model provider returned a server error. Retry after the provider recovers.",
        "BUILD_PREPARATION_MODEL_OUTPUT_INVALID": (
            "Inspect the returned model output in the issue report and retry with the same approved inputs."
        ),
        "FIXTURE_INPUT_INVALID": "Confirm the pasted Visual Design Director and Content Architect values are JSON objects.",
        "FIXTURE_INPUT_TOO_LARGE": "Reduce the pasted fixture payload to the configured input-size limit.",
    }
    return {
        "code": code,
        "message": message,
        "next_action": actions.get(
            code,
            "Review this issue code and the stage log, then share diagnostics.json for targeted troubleshooting.",
        ),
        "details": _safe_details(getattr(exc, "details", {})),
    }


@dataclass
class FixtureRunRecord:
    run_id: str
    result_root: Path
    started_at: str
    live_model: bool
    live_providers: bool
    storage: dict[str, Any]
    status: str = "running"
    current_stage: str = "queued"
    completed_at: str = ""
    events: list[dict[str, Any]] = field(default_factory=list)
    issue: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    task: asyncio.Task[None] | None = None

    @property
    def diagnostics_path(self) -> Path:
        return self.result_root / "diagnostics.json"

    @property
    def result_path(self) -> Path:
        return self.result_root / "result.json"

    @property
    def content_brief_path(self) -> Path:
        return self.result_root / "content-and-narrative-brief.md"

    @property
    def visual_brief_path(self) -> Path:
        return self.result_root / "visual-and-build-brief.md"

    def local_result(self) -> dict[str, Any]:
        return {
            "status": "ready" if self.content_brief_path.is_file() else "pending",
            "result_folder": _relative(self.result_root),
            "content_brief_path": _relative(self.content_brief_path),
            "visual_brief_path": _relative(self.visual_brief_path),
            "content_brief_available": self.content_brief_path.is_file(),
            "visual_brief_available": self.visual_brief_path.is_file(),
        }

    def report(self) -> dict[str, Any]:
        return {
            "schema_version": "fixture-run-diagnostics-v3",
            "run_id": self.run_id,
            "status": self.status,
            "current_stage": self.current_stage,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "modes": {
                "live_model": self.live_model,
                "live_providers": self.live_providers,
            },
            "local_result": self.local_result(),
            "storage": self.storage,
            "issue": self.issue,
            "events": self.events,
            "summary": _result_summary(self.result),
        }

    def public(self) -> dict[str, Any]:
        base_download = f"/api/v1/build-preparation/fixture/runs/{self.run_id}/download"
        return {
            **self.report(),
            "result": self.result,
            "details_url": f"/build-preparation-fixture/progress?run={self.run_id}",
            "content_brief_download_url": (
                f"{base_download}?doc=content" if self.content_brief_path.is_file() else ""
            ),
            "visual_brief_download_url": (
                f"{base_download}?doc=visual" if self.visual_brief_path.is_file() else ""
            ),
        }


def _result_summary(result: dict[str, Any] | None) -> dict[str, Any]:
    if not result:
        return {}
    resource_index = result.get("resource_index") or []
    component_index = result.get("component_index") or []
    resolved_resources = sum(
        1
        for item in resource_index
        if isinstance(item, dict) and item.get("status") == "candidates_found"
    )
    resolved_components = sum(
        1 for item in component_index if isinstance(item, dict) and item.get("suggestions")
    )
    return {
        "route_count": len(result.get("routes", []) or []),
        "resource_need_count": len(result.get("resource_needs", []) or []),
        "resource_role_count": len(resource_index),
        "resource_roles_with_candidates": resolved_resources,
        "component_role_count": len(component_index),
        "component_roles_with_suggestions": resolved_components,
        "provider_calls": result.get("provider_calls", 0),
        "model_calls": result.get("model_calls", 0),
        "visual_input_mode": result.get("visual_input_mode", "approved_vdd"),
        "assumption_hash": result.get("assumption_hash", ""),
        "content_brief_length": len(str(result.get("content_brief_markdown", ""))),
        "visual_brief_length": len(str(result.get("visual_brief_markdown", ""))),
        "warning_count": len(result.get("warnings", []) or []),
    }


class FixtureRunManager:
    """Own one active fixture run and retain completed reports on local disk."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._runs: dict[str, FixtureRunRecord] = {}
        self._active_run_id = ""
        self._lock = asyncio.Lock()

    def preflight(self) -> dict[str, Any]:
        return fixture_storage_preflight(self._settings)

    async def start(
        self,
        *,
        visual_design_director: dict[str, Any] | None,
        content_architect: dict[str, Any] | None,
        live_model: bool,
        live_providers: bool,
        model_profile: str,
    ) -> dict[str, Any]:
        async with self._lock:
            if self._active_run_id:
                active = self._runs.get(self._active_run_id)
                if active is not None and active.status == "running":
                    raise FixtureRunConflictError
                self._active_run_id = ""
            run_id = str(uuid4())
            # Windows does not permit ':' in a directory name, so use the
            # safe on-disk form of the requested "HH:MM-DD-MM" timestamp.
            timestamp = datetime.now(_INDIA_TIME).strftime("%H-%M-%d-%m")
            result_root = (
                Path(self._settings.build_preparation.fixture_output_dir)
                / "build-preparation"
                / f"{timestamp}-{run_id[:8]}"
            )
            result_root.mkdir(parents=True, exist_ok=False)
            record = FixtureRunRecord(
                run_id=run_id,
                result_root=result_root,
                started_at=_now(),
                live_model=live_model,
                live_providers=live_providers,
                storage=self.preflight(),
            )
            self._runs[run_id] = record
            self._active_run_id = run_id
            await self._record_event(
                record,
                _event(
                    "fixture_run_queued",
                    "queued",
                    "Fixture run accepted and local result folder created.",
                ),
            )
            record.task = asyncio.create_task(
                self._execute(
                    record,
                    visual_design_director=visual_design_director,
                    content_architect=content_architect,
                    model_profile=model_profile,
                ),
                name=f"build-preparation-fixture-{run_id}",
            )
            return record.public()

    async def get(self, run_id: str) -> dict[str, Any]:
        record = self._runs.get(run_id) or self._load_from_disk(run_id)
        if record is None:
            raise FixtureRunNotFoundError
        self._runs.setdefault(run_id, record)
        return record.public()

    async def download_path(self, run_id: str, doc: str = "content") -> Path:
        record = self._runs.get(run_id) or self._load_from_disk(run_id)
        path = (
            record.content_brief_path
            if record is not None and doc == "content"
            else record.visual_brief_path
            if record is not None
            else None
        )
        if record is None or path is None or not path.is_file():
            raise FixtureRunNotFoundError
        return path

    async def close(self) -> None:
        tasks = [
            record.task
            for record in self._runs.values()
            if record.task is not None and not record.task.done()
        ]
        for task in tasks:
            task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError):
                await task

    async def _execute(
        self,
        record: FixtureRunRecord,
        *,
        visual_design_director: dict[str, Any] | None,
        content_architect: dict[str, Any] | None,
        model_profile: str,
    ) -> None:
        try:
            result = await run_fixture(
                self._settings,
                raw_override=visual_design_director,
                content_architect_override=content_architect,
                live_model=record.live_model,
                live_providers=record.live_providers,
                model_profile=model_profile,
                event_sink=lambda event: self._record_event(record, event.model_dump(mode="json")),
                run_id=record.run_id,
                local_result_root=str(record.result_root),
            )
            record.result = result
            record.storage = result.get("storage", record.storage)
            self._merge_result_events(record, result)
            has_both_briefs = bool(result.get("content_brief_markdown")) and bool(
                result.get("visual_brief_markdown")
            )
            record.status = "ready" if has_both_briefs else "needs_attention"
            if not has_both_briefs:
                record.issue = {
                    "code": "BRIEF_INCOMPLETE",
                    "message": "The run completed but did not produce both Markdown briefs.",
                    "next_action": "Review diagnostics.json and retry.",
                    "details": {},
                }
            record.current_stage = "compose_visual_brief"
            record.completed_at = _now()
            await self._record_event(
                record,
                _event(
                    "fixture_run_complete",
                    "compose_visual_brief",
                    "Both Markdown briefs were composed."
                    if has_both_briefs
                    else "The run completed without producing both briefs.",
                    level="info" if has_both_briefs else "warning",
                ),
            )
            self._write_result(record)
        except asyncio.CancelledError:
            record.status = "failed"
            record.current_stage = "cancelled"
            record.completed_at = _now()
            record.issue = {
                "code": "FIXTURE_RUN_CANCELLED",
                "message": "The fixture run was cancelled before completion.",
                "next_action": "Start a new fixture run after the app is available again.",
                "details": {},
            }
            self._write_diagnostics(record)
            raise
        except Exception as exc:  # The UI must always receive one safe diagnostic record.
            record.completed_at = _now()
            record.issue = _issue_from_error(exc)
            record.status = "failed"
            await self._record_event(
                record,
                _event(
                    "fixture_run_failed",
                    record.current_stage,
                    "Fixture run failed before both briefs were composed.",
                    level="error",
                ),
            )
        finally:
            async with self._lock:
                if self._active_run_id == record.run_id:
                    self._active_run_id = ""

    async def _record_event(
        self, record: FixtureRunRecord, event: StageEvent | dict[str, Any]
    ) -> None:
        payload = event.model_dump(mode="json") if isinstance(event, StageEvent) else dict(event)
        record.events.append(payload)
        record.current_stage = str(
            payload.get("stage", record.current_stage) or record.current_stage
        )
        self._write_diagnostics(record)

    def _merge_result_events(self, record: FixtureRunRecord, result: dict[str, Any]) -> None:
        existing = {
            (str(event.get("event_id", "")), str(event.get("timestamp", "")))
            for event in record.events
        }
        for event in result.get("events", []) or []:
            if not isinstance(event, dict):
                continue
            key = (str(event.get("event_id", "")), str(event.get("timestamp", "")))
            if key not in existing:
                record.events.append(event)
                existing.add(key)

    def _write_diagnostics(self, record: FixtureRunRecord) -> None:
        self._atomic_json(record.diagnostics_path, record.report())

    def _write_result(self, record: FixtureRunRecord) -> None:
        if record.result is not None:
            self._atomic_json(record.result_path, record.result)
            self._atomic_text(
                record.content_brief_path, str(record.result.get("content_brief_markdown", ""))
            )
            self._atomic_text(
                record.visual_brief_path, str(record.result.get("visual_brief_markdown", ""))
            )
        self._write_diagnostics(record)

    @staticmethod
    def _atomic_text(path: Path, text: str) -> None:
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            temporary.write_text(text, encoding="utf-8")
            for attempt in range(5):
                try:
                    os.replace(temporary, path)
                    break
                except PermissionError:
                    if attempt == 4:
                        raise
                    time.sleep(0.01 * (attempt + 1))
        finally:
            if temporary.exists():
                temporary.unlink()

    @staticmethod
    def _atomic_json(path: Path, value: dict[str, Any]) -> None:
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            temporary.write_text(
                json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
                encoding="utf-8",
            )
            for attempt in range(5):
                try:
                    os.replace(temporary, path)
                    break
                except PermissionError:
                    if attempt == 4:
                        raise
                    time.sleep(0.01 * (attempt + 1))
        finally:
            if temporary.exists():
                temporary.unlink()

    def _load_from_disk(self, run_id: str) -> FixtureRunRecord | None:
        base = Path(self._settings.build_preparation.fixture_output_dir) / "build-preparation"
        if not base.is_dir():
            return None
        for diagnostics_path in base.glob("*/diagnostics.json"):
            try:
                report = json.loads(diagnostics_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(report, dict) or report.get("run_id") != run_id:
                continue
            raw_modes = report.get("modes")
            modes = raw_modes if isinstance(raw_modes, dict) else {}
            raw_storage = report.get("storage")
            storage = raw_storage if isinstance(raw_storage, dict) else {}
            raw_events = report.get("events")
            events = (
                [cast(dict[str, Any], event) for event in raw_events if isinstance(event, dict)]
                if isinstance(raw_events, list)
                else []
            )
            raw_issue = report.get("issue")
            record = FixtureRunRecord(
                run_id=run_id,
                result_root=diagnostics_path.parent,
                started_at=str(report.get("started_at", "")),
                live_model=bool(modes.get("live_model", False)),
                live_providers=bool(modes.get("live_providers", False)),
                storage=storage,
                status=str(report.get("status", "failed")),
                current_stage=str(report.get("current_stage", "")),
                completed_at=str(report.get("completed_at", "")),
                events=events,
                issue=cast(dict[str, Any], raw_issue) if isinstance(raw_issue, dict) else None,
            )
            if record.result_path.is_file():
                try:
                    result = json.loads(record.result_path.read_text(encoding="utf-8"))
                    record.result = result if isinstance(result, dict) else None
                except (OSError, json.JSONDecodeError):
                    pass
            return record
        return None
