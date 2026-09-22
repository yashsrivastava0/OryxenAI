"""Background job worker — main polling loop.

Start via:
    uv run python -m oryxenai.jobs.worker
    or
    .\\scripts\run-worker.ps1

Architecture:
  1. startup validation + engine creation
  2. heartbeat loop (writes periodically to service_heartbeats)
  3. claim → execute → result/retry loop (polling)
  4. stale-job recovery (reclaims expired running jobs)
  5. graceful SIGINT/SIGTERM shutdown

The worker never runs migrations or starts the FastAPI app. Discovery model
calls run here, outside the HTTP request transaction.
"""

from __future__ import annotations

import asyncio
import contextlib
import signal
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryxenai.agents.code_generator.core.toolchain_preflight import run_toolchain_preflight
from oryxenai.agents.code_generator.core.worker_readiness import (
    capability_config_identity_hash,
    capability_proof_blocker,
    capability_toolchain_identity_hash,
    verification_is_enabled,
    worker_contract_readiness,
)
from oryxenai.agents.shared.model_runtime import (
    close_model_runtime,
    get_model_runtime,
    validate_pipeline_job_timeouts,
)
from oryxenai.agents.shared.providers.errors import (
    ProviderError,
    is_provider_credit_error,
    stable_provider_failure,
)
from oryxenai.auth.worker_fence import AuthorizationFenceError, WorkerAuthorizationFence
from oryxenai.core.logging import configure_logging, get_logger
from oryxenai.core.settings import get_settings
from oryxenai.db.session import get_engine, reset_engine_cache
from oryxenai.jobs.contracts import permanent, retryable
from oryxenai.jobs.policy import foreground_job_kinds
from oryxenai.jobs.registry import get as get_handler
from oryxenai.jobs.registry import list_kinds
from oryxenai.jobs.repository import JobRepository
from oryxenai.jobs.retry import delay_for_attempt, should_retry

if TYPE_CHECKING:
    from oryxenai.core.settings import Settings

_log_prefix = "[oryxenai.worker]"
logger = get_logger("oryxenai.jobs.worker")


def _safe_handler_error(error: Any, *, job_kind: str = "") -> Any:
    """Convert unexpected handler errors to the stable public job contract.

    Code Generator handlers persist checkpoints before queueing their next
    stage. An unexpected process/runtime error in that narrow handoff window
    is therefore safe to redeliver and must not strand a run as a permanent
    failure. Other job families retain the existing fail-closed policy.
    """

    if isinstance(error, ProviderError) or is_provider_credit_error(error):
        code, message = stable_provider_failure(error)
        return (
            retryable(code, message)
            if bool(getattr(error, "retryable", False))
            else permanent(code, message)
        )
    if hasattr(error, "retryable") and hasattr(error, "code") and hasattr(error, "message"):
        return error
    if str(job_kind).startswith("code_generator."):
        return retryable(
            "HANDLER_ERROR",
            "The Code Generator worker hit a transient execution error and will retry.",
        )
    return permanent("HANDLER_ERROR", "The background job handler failed.")


def _safe_result_error(raw_error: dict[str, Any]) -> Any:
    if is_provider_credit_error(raw_error):
        code, message = stable_provider_failure(raw_error)
        return permanent(code, message)
    code = str(raw_error.get("code", "JOB_HANDLER_FAILED"))
    message = str(raw_error.get("message", "The background job handler failed."))
    if code.startswith(("PROVIDER_", "NETWORK_", "MODEL_")):
        code, message = stable_provider_failure(raw_error)
        return (
            retryable(code, message)
            if bool(raw_error.get("retryable", False))
            else permanent(code, message)
        )
    details = raw_error.get("details") if isinstance(raw_error.get("details"), dict) else None
    return (
        retryable(code, message, details)
        if bool(raw_error.get("retryable", False))
        else permanent(code, message, details)
    )


def _timeout_decision(
    message: str, *, attempt: int, max_attempts: int
) -> tuple[Any, dict[str, Any]]:
    error = retryable("JOB_TIMEOUT", message)
    return error, {
        "code": error.code,
        "message": error.message,
        "details": {},
        "retryable": True,
        "will_retry": should_retry(error, attempt, max_attempts),
    }


def _code_generator_blocked_error(blocker: str) -> Any:
    messages = {
        "code_generator_verification_disabled": (
            "Code Generator verification is disabled; enable it before resuming this job."
        ),
        "code_generator_worker_capability_proof_expired": (
            "The Code Generator worker capability proof expired; wait for a fresh proof, then retry."
        ),
        "code_generator_worker_toolchain_unavailable": (
            "The Code Generator worker has not proven its toolchain and preview path; fix the reported prerequisite, then retry."
        ),
        "code_generator_worker_unavailable": (
            "No live Code Generator worker is available; start a compatible worker, then retry."
        ),
        "code_generator_worker_contract_mismatch": (
            "Code Generator workers have mixed release contracts; drain incompatible workers, then retry."
        ),
        "code_generator_worker_heartbeat_unavailable": (
            "Worker capability could not be checked; restore heartbeat storage, then retry."
        ),
    }
    stable_code = blocker or "code_generator_worker_toolchain_unavailable"
    return permanent(
        stable_code.upper(),
        messages.get(
            stable_code,
            "The Code Generator worker capability proof is missing or stale; restore readiness, then retry.",
        ),
        {"worker_contract_blocker": stable_code},
    )


class Worker:
    """Polling job worker with heartbeat and graceful shutdown."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._model_runtime = get_model_runtime(self._settings.models)
        validate_pipeline_job_timeouts(self._settings)
        # Heartbeat rows use PostgreSQL UUID; keep the proof's worker identity
        # in the same canonical representation returned when that row is read.
        self._instance_id = str(uuid.uuid4())
        self._running = True
        self._active_tasks: set[asyncio.Task[None]] = set()
        self._active_job_ids: set[uuid.UUID] = set()
        self._code_generator_capability_proof: dict[str, Any] | None = None
        self._capability_refresh_lock = asyncio.Lock()

    # ── public entry points ────────────────────────────────────────────────

    async def run(self) -> None:
        self._setup_signals()
        engine = get_engine(self._settings)
        self._sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        self._model_runtime.attach_sessionmaker(self._sessionmaker)
        logger.info("worker instance=%s starting", self._instance_id)

        await self._init_heartbeat()

        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        usage_task = asyncio.create_task(self._usage_reconciliation_loop())

        try:
            await self._poll_loop()
        finally:
            self._running = False
            heartbeat_task.cancel()
            usage_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task
            with contextlib.suppress(asyncio.CancelledError):
                await usage_task
            await self._shutdown()
            await close_model_runtime(self._settings.models)
            await engine.dispose()
            reset_engine_cache()
            logger.info("worker instance=%s stopped", self._instance_id)

    # ── setup ──────────────────────────────────────────────────────────────

    def _setup_signals(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(sig, self._handle_shutdown_signal)

    def _handle_shutdown_signal(self) -> None:
        logger.info("worker shutdown signal received; draining")
        self._running = False

    # ── heartbeat ──────────────────────────────────────────────────────────

    async def _init_heartbeat(self) -> None:
        from oryxenai.jobs.heartbeat import HeartbeatRepository

        await self._refresh_code_generator_capability(force=True)
        async with self._sessionmaker() as session:
            repo = HeartbeatRepository(session)
            await repo.upsert(
                self._instance_id,
                "oryxenai-worker",
                self._worker_metadata(),
            )
            await session.commit()

    async def _heartbeat_loop(self) -> None:
        from oryxenai.jobs.heartbeat import HeartbeatRepository

        interval = self._settings.worker.heartbeat_interval
        while self._running:
            try:
                await self._refresh_code_generator_capability()
                async with self._sessionmaker() as session:
                    repo = HeartbeatRepository(session)
                    await repo.upsert(self._instance_id, "oryxenai-worker", self._worker_metadata())
                    await session.commit()
            except Exception as exc:
                logger.warning("worker heartbeat transient error=%s", type(exc).__name__)
            await asyncio.sleep(interval)

    async def _usage_reconciliation_loop(self) -> None:
        """Periodically refresh provider usage without sending portfolio data."""

        interval = max(
            30.0,
            float(self._settings.models.routing.capacity.observation_refresh_seconds),
        )
        while self._running:
            try:
                await self._model_runtime.reconcile_usage()
            except Exception as exc:
                logger.warning("model usage reconciliation failed error=%s", type(exc).__name__)
            await asyncio.sleep(interval)

    # ── main poll loop ─────────────────────────────────────────────────────

    async def _poll_loop(self) -> None:
        while self._running:
            try:
                capacity = max(0, int(self._settings.worker.concurrency) - len(self._active_tasks))
                if capacity <= 0:
                    await asyncio.sleep(self._settings.worker.polling_interval)
                    continue
                recovered = await self._recover_stale(capacity)
                claimed = await self._claim_due(max(0, capacity - len(recovered)))
                for job in recovered:
                    self._dispatch(job)
                for job in claimed:
                    self._dispatch(job)
            except Exception as exc:
                logger.warning("worker poll transient error=%s", type(exc).__name__)
            finally:
                await asyncio.sleep(self._settings.worker.polling_interval)

    async def _claim_due(self, limit: int | None = None) -> list[Any]:
        if limit == 0:
            return []
        await self._refresh_code_generator_capability()
        claim_blocker = ""
        async with self._sessionmaker() as session:
            from oryxenai.jobs.heartbeat import HeartbeatRepository

            allowed_job_kinds = list_kinds()
            if any(kind.startswith("code_generator.") for kind in allowed_job_kinds):
                await HeartbeatRepository(session).upsert(
                    self._instance_id,
                    "oryxenai-worker",
                    self._worker_metadata(),
                )
                await session.commit()
                lane_readiness = await worker_contract_readiness(
                    HeartbeatRepository(session), self._settings
                )
                local_blocker = capability_proof_blocker(
                    self._code_generator_capability_proof,
                    settings=self._settings,
                    worker_instance_id=self._instance_id,
                )
                if local_blocker:
                    claim_blocker = local_blocker
                elif not lane_readiness.get("ready"):
                    claim_blocker = str(
                        lane_readiness.get("blocker")
                        or "code_generator_worker_toolchain_unavailable"
                    )
            repo = JobRepository(session)
            jobs = await repo.claim_batch(
                self._instance_id,
                self._settings.worker_job.lease_duration,
                min(
                    limit or self._settings.worker.claim_batch_size,
                    self._settings.worker.claim_batch_size,
                ),
                allowed_job_kinds=allowed_job_kinds,
                foreground_job_kinds=foreground_job_kinds(),
            )
            await session.commit()
        if claim_blocker:
            ready_jobs: list[Any] = []
            for job in jobs:
                kind = str(getattr(job, "job_kind", ""))
                if not kind.startswith("code_generator."):
                    ready_jobs.append(job)
                    continue
                payload = dict(getattr(job, "payload", {}) or {})
                payload.update(
                    {
                        "attempt": job.attempt,
                        "max_attempts": job.max_attempts,
                        "job_id": str(job.id),
                        "job_kind": kind,
                        "worker_instance": self._instance_id,
                    }
                )
                if job.lease_token:
                    payload["lease_token"] = job.lease_token
                await self._fail_job(
                    job,
                    _code_generator_blocked_error(claim_blocker),
                    handler=get_handler(kind),
                    payload=payload,
                )
            return ready_jobs
        return jobs

    async def _recover_stale(self, limit: int | None = None) -> list[Any]:
        if limit == 0:
            return []
        async with self._sessionmaker() as session:
            repo = JobRepository(session)
            await repo.terminalize_exhausted_stale(
                self._settings.worker_job.lease_duration,
                allowed_job_kinds=list_kinds(),
            )
            await repo.requeue_stale(
                self._settings.worker_job.lease_duration,
                min(
                    limit or self._settings.worker.claim_batch_size,
                    self._settings.worker.claim_batch_size,
                ),
                exclude_job_ids=set(self._active_job_ids),
                allowed_job_kinds=list_kinds(),
                foreground_job_kinds=foreground_job_kinds(),
            )
            await session.commit()
        # Requeue before claiming so a fresh foreground request can take the
        # unique model-generation lane before an abandoned job is dispatched.
        return await self._claim_due(limit)

    # ── dispatch ───────────────────────────────────────────────────────────

    def _dispatch(self, job: Any) -> None:
        self._active_job_ids.add(job.id)
        task = asyncio.create_task(self._execute_one(job))
        self._active_tasks.add(task)

        def forget_active(done: asyncio.Task[None]) -> None:
            self._active_tasks.discard(done)
            self._active_job_ids.discard(job.id)

        task.add_done_callback(forget_active)

    async def _execute_one(self, job: Any) -> None:
        kind = job.job_kind
        handler = get_handler(kind)
        if handler is None:
            await self._fail_job(
                job,
                permanent(
                    "UNKNOWN_JOB_KIND",
                    f"No handler registered for '{kind}'.",
                ),
            )
            return

        try:
            async with self._sessionmaker() as session:
                await WorkerAuthorizationFence(session).validate_job(job)
        except AuthorizationFenceError as exc:
            await self._fail_job(job, permanent(exc.code, exc.message))
            return
        except Exception as exc:
            logger.warning(
                "worker authorization fence unavailable kind=%s error=%s",
                kind,
                type(exc).__name__,
            )
            await self._fail_job(
                job,
                retryable(
                    "AUTHORIZATION_FENCE_UNAVAILABLE",
                    "Authorization could not be rechecked safely.",
                ),
            )
            return

        payload = dict(job.payload or {})
        payload["attempt"] = job.attempt
        payload["max_attempts"] = job.max_attempts
        payload["job_id"] = str(job.id)
        payload["job_kind"] = kind
        payload["worker_instance"] = self._instance_id
        if job.lease_token:
            payload["lease_token"] = job.lease_token
        if kind.startswith("code_generator."):
            await self._refresh_code_generator_capability()
            capability_blocker = capability_proof_blocker(
                self._code_generator_capability_proof,
                settings=self._settings,
                worker_instance_id=self._instance_id,
            )
            if not capability_blocker:
                async with self._sessionmaker() as session:
                    from oryxenai.jobs.heartbeat import HeartbeatRepository

                    lane_readiness = await worker_contract_readiness(
                        HeartbeatRepository(session), self._settings
                    )
                if not lane_readiness.get("ready"):
                    capability_blocker = str(
                        lane_readiness.get("blocker")
                        or "code_generator_worker_toolchain_unavailable"
                    )
            if capability_blocker:
                await self._fail_job(
                    job,
                    _code_generator_blocked_error(capability_blocker),
                    handler=handler,
                    payload=payload,
                )
                return

        heartbeat_task = asyncio.create_task(self._renew_lease_loop(job))
        try:
            result = await asyncio.wait_for(
                handler.execute(payload, self._instance_id),
                timeout=self._settings.worker_job.timeout_for(kind),
            )
        except TimeoutError:
            timeout_message = (
                f"Handler exceeded {self._settings.worker_job.timeout_for(kind)}s timeout."
            )
            timeout_error, timeout_payload = _timeout_decision(
                timeout_message,
                attempt=job.attempt,
                max_attempts=job.max_attempts,
            )
            # asyncio.wait_for cancels handler.execute() from outside, so the
            # handler's own try/except (which normally persists a terminal
            # failure into its agent-specific session state) never runs.
            # Without this, a session hits max_attempts and stays stuck
            # reporting "running"/"build_running" forever with no visible
            # error and no way to retry through the UI (live-reproduced).
            on_timeout = getattr(handler, "on_timeout", None)
            if on_timeout is not None:
                try:
                    await on_timeout(
                        payload,
                        timeout_payload,
                    )
                except Exception as exc:
                    logger.warning(
                        "on_timeout hook failed kind=%s error=%s", kind, type(exc).__name__
                    )
            await self._fail_job(
                job,
                timeout_error,
                handler=handler,
                payload=payload,
            )
            return
        except Exception as exc:
            if not (hasattr(exc, "code") and hasattr(exc, "message") and hasattr(exc, "retryable")):
                logger.warning("job handler failed kind=%s error=%s", kind, type(exc).__name__)
            error = _safe_handler_error(exc, job_kind=kind)
            await self._fail_job(
                job,
                error,
                handler=handler,
                payload=payload,
            )
            return
        finally:
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task

        if result.get("status") == "cancelled":
            # The API already made the durable row terminal. Do not turn a
            # user cancellation into a success/failure transition.
            await self._notify_terminal_failure(
                handler,
                payload,
                permanent("JOB_CANCELLED", "The Code Generator job was cancelled."),
            )
            return
        if result.get("status") == "failed":
            raw_error = result.get("error")
            if isinstance(raw_error, dict):
                error = _safe_result_error(raw_error)
            else:
                error = permanent("JOB_HANDLER_FAILED", "The background job handler failed safely.")
            await self._fail_job(
                job,
                error,
                handler=handler,
                payload=payload,
            )
            return
        result_code = result.get("code")
        if is_provider_credit_error({"code": result_code}):
            code, message = stable_provider_failure({"code": result_code})
            await self._fail_job(
                job,
                permanent(code, message),
                handler=handler,
                payload=payload,
            )
            return
        await self._complete_job(job, result)

    async def _refresh_code_generator_capability(self, *, force: bool = False) -> None:
        async with self._capability_refresh_lock:
            identity_hash = capability_config_identity_hash(self._settings)
            proof = self._code_generator_capability_proof
            now = datetime.now(UTC)
            if (
                not force
                and isinstance(proof, dict)
                and proof.get("config_identity_sha256") == identity_hash
            ):
                try:
                    expires_at = datetime.fromisoformat(str(proof.get("expires_at", "")))
                    if expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=UTC)
                    if expires_at > now:
                        return
                except (TypeError, ValueError):
                    pass

            verification = self._settings.code_generator_verification
            development = self._settings.code_generator_development
            ttl = max(30, int(getattr(verification, "capability_proof_ttl_seconds", 900) or 900))
            checked_at = now
            if verification_is_enabled(self._settings):
                try:
                    result = await run_toolchain_preflight(
                        self._settings,
                        require_brief_dependency_paths=False,
                    )
                except Exception as exc:
                    logger.warning(
                        "code generator capability proof failed error=%s", type(exc).__name__
                    )
                    result = {
                        "ready": False,
                        "checks": {},
                        "checked_at": checked_at.isoformat(),
                    }
            else:
                result = {
                    "ready": False,
                    "checks": {"verification_enabled": False},
                    "checked_at": checked_at.isoformat(),
                }

            try:
                checked_at = datetime.fromisoformat(str(result.get("checked_at", "")))
                if checked_at.tzinfo is None:
                    checked_at = checked_at.replace(tzinfo=UTC)
            except (TypeError, ValueError):
                checked_at = now
            try:
                expires_at = datetime.fromisoformat(str(result.get("expires_at", "")))
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=UTC)
            except (TypeError, ValueError):
                expires_at = checked_at + timedelta(seconds=ttl)
            self._code_generator_capability_proof = {
                "schema_version": "code-generator-worker-capability-v1",
                "worker_instance_id": self._instance_id,
                "release_id": str(development.worker_release_id),
                "pipeline_contract_version": str(development.pipeline_contract_version),
                "config_identity_sha256": identity_hash,
                "toolchain_facts": dict(result.get("facts", {}))
                if isinstance(result.get("facts"), dict)
                else {},
                "checked_at": checked_at.isoformat(),
                "expires_at": expires_at.isoformat(),
                "ready": bool(result.get("ready")) and verification_is_enabled(self._settings),
                "checks": dict(result.get("checks", {}))
                if isinstance(result.get("checks"), dict)
                else {},
            }
            self._code_generator_capability_proof["toolchain_identity_sha256"] = (
                capability_toolchain_identity_hash(
                    identity_hash,
                    self._code_generator_capability_proof["toolchain_facts"],
                )
            )

    def _worker_metadata(self) -> dict[str, object]:
        development = self._settings.code_generator_development
        generation = self._settings.code_generator_generation
        proof = self._code_generator_capability_proof or {}
        proof_blocker = capability_proof_blocker(
            proof,
            settings=self._settings,
            worker_instance_id=self._instance_id,
        )
        checks = proof.get("checks", {})
        checks = checks if isinstance(checks, dict) else {}
        node = bool(checks.get("node", False))
        npm = bool(checks.get("npm", False))
        browser = bool(checks.get("browser", False))
        return {
            "process": f"worker-{self._instance_id}",
            "release_id": str(getattr(development, "worker_release_id", "oryxenai-worker")),
            "pipeline_contract_version": str(
                getattr(development, "pipeline_contract_version", "code-generator-v3")
            ),
            "artifact_store_provider": str(
                getattr(generation, "artifact_store_provider", "local_fs")
            ),
            "code_generator_capability": not bool(proof_blocker),
            "code_generator_toolchain": {
                "node": node,
                "npm": npm,
                "browser": browser,
            },
            "code_generator_capability_proof": dict(proof),
            "code_generator_capability_blocker": proof_blocker,
        }

    async def _renew_lease_loop(self, job: Any) -> None:
        """Keep a claimed job's heartbeat fresh while its handler is running.

        Without this, a handler that legitimately runs longer than
        worker.job.lease_duration (e.g. a large model generation close to
        its own provider timeout) looks abandoned to _recover_stale, which
        re-dispatches the same job for a second, concurrent execution.
        """
        interval = max(self._settings.worker_job.lease_duration / 3, 5.0)
        while True:
            await asyncio.sleep(interval)
            try:
                async with self._sessionmaker() as session:
                    repo = JobRepository(session)
                    await repo.update_heartbeat(
                        job.id,
                        worker_instance=self._instance_id,
                        attempt=job.attempt,
                        lease_token=job.lease_token,
                    )
                    await session.commit()
            except Exception as exc:
                logger.warning(
                    "heartbeat renewal failed job_id=%s error=%s", job.id, type(exc).__name__
                )

    async def _complete_job(self, job: Any, result: dict[str, Any]) -> None:
        async with self._sessionmaker() as session:
            repo = JobRepository(session)
            await repo.mark_succeeded(
                job.id,
                result,
                worker_instance=self._instance_id,
                attempt=job.attempt,
                lease_token=job.lease_token,
            )
            await session.commit()

    async def _fail_job(
        self,
        job: Any,
        error: Any,
        *,
        handler: Any | None = None,
        payload: dict[str, Any] | None = None,
    ) -> bool:
        marked = False
        will_retry = False
        job_error = error if hasattr(error, "retryable") else permanent("UNKNOWN", str(error))
        async with self._sessionmaker() as session:
            repo = JobRepository(session)
            retry = self._settings.worker_retry
            will_retry = should_retry(job_error, job.attempt, job.max_attempts)
            if will_retry:
                delay = delay_for_attempt(
                    job.attempt, retry.base_delay, retry.max_delay, retry.jitter
                )
                available_at = datetime.now(UTC)
                from datetime import timedelta

                available_at = available_at + timedelta(seconds=delay)
                marked = await repo.mark_failed(
                    job.id,
                    {
                        "code": job_error.code,
                        "message": job_error.message,
                        "retryable": job_error.retryable,
                        "details": getattr(job_error, "details", {}),
                        "will_retry": True,
                    },
                    available_at=available_at,
                    worker_instance=self._instance_id,
                    attempt=job.attempt,
                    lease_token=job.lease_token,
                )
            else:
                marked = await repo.mark_failed(
                    job.id,
                    {
                        "code": job_error.code,
                        "message": job_error.message,
                        "retryable": False,
                        "details": getattr(job_error, "details", {}),
                        "will_retry": False,
                    },
                    worker_instance=self._instance_id,
                    attempt=job.attempt,
                    lease_token=job.lease_token,
                )
            await session.commit()
        if marked and not will_retry and handler is not None and payload is not None:
            await self._notify_terminal_failure(handler, payload, job_error)
        return will_retry

    async def _notify_terminal_failure(
        self,
        handler: Any,
        payload: dict[str, Any],
        error: Any,
    ) -> None:
        hook = getattr(handler, "on_terminal_failure", None)
        if hook is None:
            return
        error_payload = {
            "code": str(getattr(error, "code", "HANDLER_ERROR")),
            "message": str(getattr(error, "message", "Code Generator could not complete.")),
            # The job has already exhausted its automatic retry budget when
            # this hook runs.  The run-level report must not be mistaken for
            # another transient failure by the reconciler.
            "retryable": False,
            "details": getattr(error, "details", {}),
            "will_retry": False,
        }
        try:
            await hook(payload, error_payload)
        except Exception as exc:
            logger.warning(
                "terminal failure hook failed kind=%s error=%s",
                payload.get("job_kind", "unknown"),
                type(exc).__name__,
            )

    # ── shutdown ───────────────────────────────────────────────────────────

    async def _shutdown(self) -> None:
        grace = self._settings.worker.shutdown_grace
        try:
            await self._mark_instance_stopped()
        except Exception as exc:
            logger.warning("worker shutdown heartbeat error=%s", type(exc).__name__)
        if self._active_tasks:
            logger.info("worker waiting grace=%.0fs active_jobs=%d", grace, len(self._active_tasks))
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._active_tasks, return_exceptions=True),
                    timeout=grace,
                )
            except TimeoutError:
                logger.warning("worker jobs did not finish before shutdown grace")

    async def _mark_instance_stopped(self) -> None:
        from oryxenai.jobs.heartbeat import HeartbeatRepository

        async with self._sessionmaker() as session:
            repo = HeartbeatRepository(session)
            await repo.mark_stopped(self._instance_id)
            await session.commit()


def main() -> None:
    # Unlike main.py's FastAPI lifespan, nothing else configures logging for
    # this standalone entrypoint — without this, every logger.info/.warning
    # call in the worker (including job failure diagnostics) is silently
    # dropped by Python's unconfigured root logger.
    configure_logging(get_settings())
    worker = Worker()
    asyncio.run(worker.run())


if __name__ == "__main__":
    main()
