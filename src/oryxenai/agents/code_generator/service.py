"""Application service for the Code Generator ("Studio") workflow.

Start (approved Content Architect result) -> ``code_generator.build`` (one job,
one model call for a first build) -> the verified page becomes live. There is no
automatic retry anywhere; a failed build is reported exactly and the user decides
whether to start again. One build runs per session at a time.

Reading the state also *reconciles* it: a build whose job died without reporting
(worker killed, lease expired) is turned into an exact ``WORKER_LOST`` failure so
the Studio can never sit on "building" forever.
"""

from __future__ import annotations

import hashlib
import json
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import Any, NoReturn
from uuid import UUID, uuid4

from oryxenai.agents.code_generator import messages
from oryxenai.agents.code_generator.admission import content_admission_issues
from oryxenai.agents.code_generator.changes import content_sha256
from oryxenai.agents.code_generator.diagnostics import (
    failure_cancelled,
    failure_from_admission,
    failure_worker_lost,
    reference_for,
)
from oryxenai.agents.code_generator.grants import PreviewGrantSigner
from oryxenai.agents.code_generator.schemas import FailureEnvelope
from oryxenai.agents.code_generator.serving import PREVIEW_PREFIX
from oryxenai.agents.code_generator.state import (
    CodeGeneratorSourceRef,
    CodeGeneratorStatus,
    InFlightBuild,
    apply_build_failed,
    apply_build_started,
    apply_restored,
    version_id_for_run,
)
from oryxenai.agents.content_architect.schemas import ContentArchitectStatus
from oryxenai.agents.shared.job_status import public_job_status
from oryxenai.auth.authorization import durable_snapshot_for_session
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.models.site_version import PortfolioChatMessage, PortfolioSiteVersion
from oryxenai.db.repositories.site_versions import SiteVersionRepository
from oryxenai.jobs.service import JobService
from oryxenai.themes import DEFAULT_THEME_ID, ThemeError, get_theme

_BUILD_KIND = "code_generator.build"
_LIVE_JOB_STATUSES = frozenset({"queued", "running"})
_STAGE_FOR_VERSION_STATUS = {"validating": "validate", "verifying": "verify"}


class CodeGeneratorOperationError(Exception):
    """Safe, transport-neutral error raised by the Code Generator service."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 409,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


def _iso(value: Any) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None


def _section(receipt: dict[str, Any], key: str) -> dict[str, Any]:
    value = receipt.get(key)
    return value if isinstance(value, dict) else {}


def public_version(version: PortfolioSiteVersion) -> dict[str, Any]:
    """A version as the API shows it (never the page markup)."""
    receipt: dict[str, Any] = dict(version.receipt or {})
    validation = _section(receipt, "validation")
    browser = _section(receipt, "browser")
    model = _section(receipt, "model")
    return {
        "id": str(version.id),
        "seq": version.seq,
        "version_number": version.version_number,
        "origin": version.origin,
        "status": version.status,
        "instruction": version.instruction,
        "parent_version_id": str(version.parent_version_id) if version.parent_version_id else None,
        "restricted": bool(version.restricted),
        "theme_id": version.theme_id,
        "lang": version.lang,
        "index_sha256": version.index_sha256,
        "error": version.error,
        "created_at": _iso(version.created_at),
        "completed_at": _iso(version.completed_at),
        "summary": {
            "warning_count": int(validation.get("warning_count", 0) or 0),
            "browser": str(browser.get("status", "")) or None,
            "model": str(model.get("model", "")) or None,
            "latency_ms": model.get("latency_ms"),
        },
    }


def public_chat(row: PortfolioChatMessage) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "seq": row.seq,
        "role": row.role,
        "kind": row.kind,
        "body": row.body,
        "version_id": str(row.version_id) if row.version_id else None,
        "created_at": _iso(row.created_at),
    }


class CodeGeneratorService:
    """Coordinates Code Generator state, runs, jobs, versions and preview grants."""

    def __init__(
        self,
        repository: SiteVersionRepository,
        job_service: JobService,
        signer: PreviewGrantSigner,
    ) -> None:
        self._repo = repository
        self._jobs = job_service
        self._signer = signer

        from oryxenai.core.settings import get_settings

        self._settings = get_settings()

    # ── start ────────────────────────────────────────────────────────────────

    async def start(self, session_id: UUID, *, request_id: str = "") -> dict[str, Any]:
        """Build the portfolio page from the approved Content Architect result."""
        session = await self._repo.lock_session(session_id)
        if session is None:
            self._not_found()
        await self._reconcile_locked(session_id)
        state = await self._repo.get_state(session_id)
        if state.status in {CodeGeneratorStatus.BUILD_RUNNING, CodeGeneratorStatus.READY}:
            # Idempotent: a double click or a second tab never starts a second build.
            return await self._response(session_id)

        content = await self._repo.get_content_architect_state(session_id)
        if content.status is not ContentArchitectStatus.APPROVED or content.approved is None:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_CONTENT_NOT_APPROVED",
                "Approve your content plan before generating the portfolio.",
                details={"content_architect_status": content.status.value},
            )
        page_content = content.page_content.model_dump(mode="json")
        issues = content_admission_issues(page_content)
        if issues:
            envelope = failure_from_admission(issues, reference=reference_for(session_id, "admit"))
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_CONTENT_NOT_BUILDABLE",
                envelope.summary,
                status_code=422,
                details={"failure": envelope.to_payload()},
            )
        theme_id = (
            content.intake.selected_theme_id
            or self._settings.code_generator.theme_id
            or DEFAULT_THEME_ID
        )
        try:
            get_theme(theme_id)
        except ThemeError as exc:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_THEME_UNAVAILABLE",
                "The configured page theme is not installed.",
                status_code=500,
            ) from exc

        from oryxenai.agents.shared.model_runtime import get_model_runtime

        policy_snapshot = get_model_runtime(self._settings.models).router.policy_snapshot()
        source_ref = CodeGeneratorSourceRef(
            content_hash=content.approved.content_hash,
            snapshotted_at=datetime.now(UTC).isoformat(),
        )
        origin = "retry" if state.builds_started > 0 else "initial"
        run_id = uuid4()
        version_id = version_id_for_run(run_id)
        key = hashlib.sha256(
            json.dumps(
                {
                    "session": str(session_id),
                    "op": "build",
                    "content": content.approved.content_hash,
                    "origin": origin,
                    "n": state.builds_started,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()

        run = AgentRun(
            id=run_id,
            agent_key="code_generator",
            status="pending",
            input_payload={
                "operation": "build",
                "origin": origin,
                "page_content": page_content,
                "content_sha256": content_sha256(page_content),
                "source_ref": source_ref.model_dump(mode="json"),
                "theme_id": theme_id,
                "version_id": str(version_id),
                "instruction": "",
                "model_profile": "",
                "input_classification": "personal",
                "routing_policy_snapshot": policy_snapshot,
            },
            state_before=dict(session.current_state),
            idempotency_key=key,
            **durable_snapshot_for_session(self._jobs.authorization_context, session_id),
        )
        await self._repo.create_run(run)
        job = await self._jobs.enqueue(
            _BUILD_KIND,
            {
                "portfolio_session_id": str(session_id),
                "agent_run_id": str(run.id),
                "version_id": str(version_id),
                "expected_session_revision": session.revision + 1,
                "request_id": request_id,
            },
            # One shot: this feature never retries on its own.
            max_attempts=1,
            idempotency_scope=f"code_generator:{session_id}",
            idempotency_key=key,
        )

        running = apply_build_started(
            state,
            in_flight=InFlightBuild(
                run_id=str(run.id),
                job_id=str(job.id),
                version_id=str(version_id),
                origin="retry" if origin == "retry" else "initial",
                started_at=datetime.now(UTC).isoformat(),
            ),
            source_ref=source_ref,
            theme_id=theme_id,
            routing_policy_version=str(policy_snapshot["version"]),
            routing_policy_fingerprint=str(policy_snapshot["fingerprint"]),
        )
        saved = await self._repo.save_state(session_id, running, session.revision)
        if saved is None:
            self._revision_conflict(session.revision)
        await self._repo.append_chat(
            session_id,
            role="assistant",
            kind="build",
            body=messages.build_started(origin),
            version_id=version_id,
        )
        return await self._response(session_id)

    # ── stop ─────────────────────────────────────────────────────────────────

    async def stop(self, session_id: UUID) -> dict[str, Any]:
        """Stop the in-flight build. The live page (if any) is untouched."""
        session = await self._repo.lock_session(session_id)
        if session is None:
            self._not_found()
        state = await self._repo.get_state(session_id)
        flight = state.in_flight
        if state.status is not CodeGeneratorStatus.BUILD_RUNNING or flight is None:
            return await self._response(session_id)

        reference = reference_for(flight.run_id)
        envelope = failure_cancelled(reference=reference)
        with suppress(TypeError, ValueError):
            await self._jobs.cancel(UUID(flight.job_id))
        stopped = apply_build_failed(state, envelope)
        saved = await self._repo.save_state(session_id, stopped, session.revision)
        if saved is None:
            self._revision_conflict(session.revision)
        await self._repo.mark_version_failed(
            UUID(flight.version_id), error=envelope.to_payload(), status="cancelled"
        )
        with suppress(TypeError, ValueError):
            await self._repo.mark_run_cancelled(
                UUID(flight.run_id),
                {"code": envelope.code, "message": envelope.summary, "retryable": False},
            )
        await self._repo.append_chat(
            session_id,
            role="system",
            kind="build",
            body=messages.build_stopped(kept_previous=bool(state.active_version_id)),
            version_id=UUID(flight.version_id),
        )
        return await self._response(session_id)

    # ── chat edits ───────────────────────────────────────────────────────────

    async def post_message(
        self,
        session_id: UUID,
        *,
        message: str,
        client_message_id: str,
        base_version_id: str | None,
        request_id: str = "",
    ) -> dict[str, Any]:
        """Ask for a content change. The interpreter + build run in one background job."""
        settings = self._settings.code_generator
        text = (message or "").strip()
        client_id = (client_message_id or "").strip()
        if not text or len(text) > settings.max_instruction_chars:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_MESSAGE_INVALID",
                f"Write between 1 and {settings.max_instruction_chars} characters.",
                status_code=422,
            )
        if not client_id or len(client_id) > 80:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_MESSAGE_INVALID",
                "A client_message_id of 1 to 80 characters is required.",
                status_code=422,
            )
        session = await self._repo.lock_session(session_id)
        if session is None:
            self._not_found()
        await self._reconcile_locked(session_id)
        if await self._repo.find_chat_by_client_id(session_id, client_id) is not None:
            return await self._response(session_id)  # a retried request: already accepted
        state = await self._repo.get_state(session_id)
        if state.status is CodeGeneratorStatus.BUILD_RUNNING:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_BUILD_IN_PROGRESS",
                "Your page is being built. Wait for it to finish, or stop it first.",
            )
        if state.status is not CodeGeneratorStatus.READY or not state.active_version_id:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_NOT_READY",
                "Generate your portfolio before asking for changes.",
                details={"status": state.status.value},
            )
        if base_version_id and base_version_id != state.active_version_id:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_STALE_BASE",
                "The page changed since you last looked. Reload and ask again.",
                details={"active_version_id": state.active_version_id},
            )
        since = datetime.now(UTC) - timedelta(hours=1)
        sent = await self._repo.count_user_messages_since(session_id, since)
        if sent >= settings.max_changes_per_hour:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_RATE_LIMITED",
                "You have reached the hourly limit for change requests. Try again a little later.",
                status_code=429,
            )
        base = await self._repo.get_version(UUID(state.active_version_id), session_id=session_id)
        if base is None or base.status != "ready" or base.restricted:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_NOT_READY", "The live page is not available to edit."
            )

        from oryxenai.agents.shared.model_runtime import get_model_runtime

        policy_snapshot = get_model_runtime(self._settings.models).router.policy_snapshot()
        history = await self._repo.recent_conversation(
            session_id, settings.interpreter_history_messages
        )
        run_id = uuid4()
        version_id = version_id_for_run(run_id)
        key = hashlib.sha256(
            json.dumps(
                {"session": str(session_id), "op": "change", "client": client_id},
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        run = AgentRun(
            id=run_id,
            agent_key="code_generator",
            status="pending",
            input_payload={
                "operation": "change",
                "origin": "change",
                "page_content": dict(base.content_snapshot),
                "content_sha256": base.content_sha256,
                "source_ref": state.source_ref.model_dump(mode="json"),
                "theme_id": base.theme_id,
                "version_id": str(version_id),
                "base_version_id": str(base.id),
                "instruction": text,
                "history": history,
                "model_profile": "",
                "input_classification": "personal",
                "routing_policy_snapshot": policy_snapshot,
            },
            state_before=dict(session.current_state),
            idempotency_key=key,
            **durable_snapshot_for_session(self._jobs.authorization_context, session_id),
        )
        await self._repo.create_run(run)
        job = await self._jobs.enqueue(
            _BUILD_KIND,
            {
                "portfolio_session_id": str(session_id),
                "agent_run_id": str(run.id),
                "version_id": str(version_id),
                "expected_session_revision": session.revision + 1,
                "request_id": request_id,
            },
            max_attempts=1,
            idempotency_scope=f"code_generator:{session_id}",
            idempotency_key=key,
        )
        running = apply_build_started(
            state,
            in_flight=InFlightBuild(
                run_id=str(run.id),
                job_id=str(job.id),
                version_id=str(version_id),
                origin="change",
                instruction=text,
                base_version_id=str(base.id),
                started_at=datetime.now(UTC).isoformat(),
            ),
            source_ref=state.source_ref,
            theme_id=state.theme_id,
            routing_policy_version=str(policy_snapshot["version"]),
            routing_policy_fingerprint=str(policy_snapshot["fingerprint"]),
        )
        if await self._repo.save_state(session_id, running, session.revision) is None:
            self._revision_conflict(session.revision)
        await self._repo.append_chat(
            session_id,
            role="user",
            kind="message",
            body=text,
            client_message_id=client_id,
        )
        return await self._response(session_id)

    async def restore(self, session_id: UUID, version_id: UUID) -> dict[str, Any]:
        """Make an earlier verified page live again: a copy, no build and no model call."""
        session = await self._repo.lock_session(session_id)
        if session is None:
            self._not_found()
        await self._reconcile_locked(session_id)
        state = await self._repo.get_state(session_id)
        if state.status is CodeGeneratorStatus.BUILD_RUNNING:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_BUILD_IN_PROGRESS",
                "Your page is being built. Wait for it to finish, or stop it first.",
            )
        if state.status is not CodeGeneratorStatus.READY:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_NOT_READY", "There is no finished page to restore into yet."
            )
        source = await self._repo.get_version(version_id, session_id=session_id)
        if source is None:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_VERSION_NOT_FOUND", "That version was not found.", status_code=404
            )
        if str(source.id) == state.active_version_id:
            return await self._response(session_id)
        reason = self._not_restorable(source)
        if reason:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_VERSION_NOT_RESTORABLE",
                reason,
                details={"version_id": str(source.id)},
            )

        number = await self._repo.next_version_number(session_id)
        duplicate = await self._repo.create_version(
            version_id=uuid4(),
            session_id=session_id,
            origin="restore",
            status="ready",
            instruction=f"Restore version {source.version_number}",
            content_snapshot=dict(source.content_snapshot),
            content_sha256=source.content_sha256,
            theme_id=source.theme_id,
            run_id=None,
            job_id=None,
            parent_version_id=source.id,
        )
        await self._repo.mark_version_ready(
            duplicate,
            version_number=number,
            lang=source.lang,
            index_html=str(source.index_html),
            index_sha256=str(source.index_sha256),
            theme_sha256=source.theme_sha256,
            manifest=dict(source.manifest),
            receipt={
                **dict(source.receipt),
                "restored_from": {
                    "version_id": str(source.id),
                    "version_number": source.version_number,
                },
            },
            trace={},
        )
        restored = apply_restored(state, version_id=str(duplicate.id), version_number=number)
        if await self._repo.save_state(session_id, restored, session.revision) is None:
            self._revision_conflict(session.revision)
        await self._repo.append_chat(
            session_id,
            role="system",
            kind="build",
            body=f"Restored version {source.version_number} as version {number}.",
            version_id=duplicate.id,
        )
        await self._repo.prune_versions(
            session_id,
            keep=self._settings.code_generator.max_versions_per_session,
            active_id=duplicate.id,
        )
        return await self._response(session_id)

    @staticmethod
    def _not_restorable(version: PortfolioSiteVersion) -> str:
        if version.restricted:
            return "That version was removed because it contained information you asked to hide."
        if version.status != "ready" or not version.index_html:
            return "Only finished versions can be restored."
        try:
            theme = get_theme(version.theme_id)
        except ThemeError:
            return "The theme this version was built with is no longer installed."
        if theme.css_sha256 != version.theme_sha256:
            return "The theme files changed since this version was built."
        return ""

    # ── read ─────────────────────────────────────────────────────────────────

    async def get_state(self, session_id: UUID) -> dict[str, Any]:
        """Current state (never 409): reconciles a lost build before answering."""
        if await self._repo.get_session(session_id) is None:
            self._not_found()
        state = await self._repo.get_state(session_id)
        flight = state.in_flight
        if (
            state.status is CodeGeneratorStatus.BUILD_RUNNING
            and flight is not None
            and not await self._job_alive(flight.job_id)
        ):
            await self._repo.lock_session(session_id)
            await self._reconcile_locked(session_id)
        return await self._response(session_id)

    async def get_version(
        self, session_id: UUID, version_id: UUID, *, include_html: bool = False
    ) -> dict[str, Any]:
        version = await self._repo.get_version(version_id, session_id=session_id)
        if version is None:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_VERSION_NOT_FOUND", "That version was not found.", status_code=404
            )
        payload = public_version(version)
        payload["receipt"] = version.receipt
        payload["trace"] = {
            key: value
            for key, value in (version.trace or {}).items()
            if include_html or key != "rejected_body_html"
        }
        if include_html:
            payload["index_html"] = version.index_html
        return payload

    async def mint_preview(
        self, session_id: UUID, version_id: UUID | None = None
    ) -> dict[str, Any]:
        """A short-lived signed URL for a ready version (default: the live one)."""
        state = await self._repo.get_state(session_id)
        target = version_id or (UUID(state.active_version_id) if state.active_version_id else None)
        if target is None:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_NO_PREVIEW",
                "There is no finished page to preview yet.",
                details={"status": state.status.value},
            )
        version = await self._repo.get_version(target, session_id=session_id, light=True)
        if version is None or version.status != "ready" or version.restricted:
            raise CodeGeneratorOperationError(
                "CODE_GENERATOR_VERSION_NOT_FOUND",
                "That version is not available for preview.",
                status_code=404,
            )
        ttl = self._settings.code_generator.preview_grant_ttl_seconds
        token, expires_at = self._signer.mint(session_id, version.id, ttl)
        return {
            "url": f"{PREVIEW_PREFIX}/{token}/index.html",
            "expires_at": datetime.fromtimestamp(expires_at, UTC).isoformat(),
            "expires_in_seconds": ttl,
            "version_id": str(version.id),
            "version_number": version.version_number,
        }

    # ── internals ────────────────────────────────────────────────────────────

    async def _response(self, session_id: UUID) -> dict[str, Any]:
        session = await self._repo.get_session(session_id)
        if session is None:
            self._not_found()
        state = await self._repo.get_state(session_id)
        versions = await self._repo.list_versions(session_id)
        chat = await self._repo.list_chat(
            session_id, limit=self._settings.code_generator.chat_tail_messages
        )
        code_generator = state.model_dump(mode="json")
        jobs: list[dict[str, Any]] = []
        flight = state.in_flight
        if flight is not None:
            job = None
            with suppress(Exception):
                job = await self._jobs.get(UUID(flight.job_id))
            if job is not None:
                jobs.append(public_job_status(job))
            version = next((item for item in versions if str(item.id) == flight.version_id), None)
            stage = "queued"
            if version is not None:
                stage = version.status
            elif job is not None and job.status == "running":
                stage = "starting"
            code_generator["in_flight"] = {
                **code_generator["in_flight"],
                "stage": stage,
                "elapsed_seconds": _elapsed_seconds(flight.started_at),
            }
        return {
            "session_id": str(session_id),
            "session_revision": session.revision,
            "code_generator": code_generator,
            "versions": [public_version(item) for item in versions],
            "chat": [public_chat(row) for row in chat],
            "jobs": jobs,
        }

    async def _job_alive(self, job_id: str) -> bool:
        try:
            job = await self._jobs.get(UUID(job_id))
        except (TypeError, ValueError):
            return False
        return job is not None and job.status in _LIVE_JOB_STATUSES

    async def _reconcile_locked(self, session_id: UUID) -> None:
        """Turn a build whose job is gone into ``WORKER_LOST``. Caller holds the lock."""
        state = await self._repo.get_state(session_id)
        flight = state.in_flight
        if state.status is not CodeGeneratorStatus.BUILD_RUNNING or flight is None:
            return
        if await self._job_alive(flight.job_id):
            return
        session = await self._repo.get_session(session_id)
        if session is None:
            return
        version_uuid = UUID(flight.version_id)
        version = await self._repo.get_version(version_uuid, session_id=session_id, light=True)
        stage = _STAGE_FOR_VERSION_STATUS.get(version.status if version else "", "generate")
        envelope: FailureEnvelope = failure_worker_lost(
            stage=stage,  # type: ignore[arg-type]
            reference=reference_for(flight.run_id),
        )
        failed = apply_build_failed(state, envelope)
        saved = await self._repo.save_state(session_id, failed, session.revision)
        if saved is None:
            return
        await self._repo.mark_version_failed(version_uuid, error=envelope.to_payload())
        with suppress(TypeError, ValueError):
            await self._repo.mark_run_failed(
                UUID(flight.run_id),
                {"code": envelope.code, "message": envelope.summary, "retryable": True},
            )
        await self._repo.append_chat(
            session_id,
            role="system",
            kind="build",
            body=messages.build_failed(
                envelope, kept_previous=bool(state.active_version_id), origin=flight.origin
            ),
            version_id=version_uuid,
        )

    @staticmethod
    def _not_found() -> NoReturn:
        raise CodeGeneratorOperationError(
            "SESSION_NOT_FOUND", "Portfolio session was not found.", status_code=404
        )

    @staticmethod
    def _revision_conflict(expected: int) -> NoReturn:
        raise CodeGeneratorOperationError(
            "CODE_GENERATOR_REVISION_CONFLICT",
            "The session changed while this request was being processed. Reload and try again.",
            details={"expected_revision": expected},
        )


def _elapsed_seconds(started_at: str | None) -> float | None:
    if not started_at:
        return None
    try:
        started = datetime.fromisoformat(started_at)
    except ValueError:
        return None
    return max(0.0, (datetime.now(UTC) - started).total_seconds())
