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
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryxenai.core.logging import get_logger
from oryxenai.core.settings import get_settings
from oryxenai.db.session import get_engine, reset_engine_cache
from oryxenai.jobs.contracts import permanent, retryable
from oryxenai.jobs.registry import get as get_handler
from oryxenai.jobs.repository import JobRepository
from oryxenai.jobs.retry import delay_for_attempt, should_retry

if TYPE_CHECKING:
    from oryxenai.core.settings import Settings

_log_prefix = "[oryxenai.worker]"
logger = get_logger("oryxenai.jobs.worker")


class Worker:
    """Polling job worker with heartbeat and graceful shutdown."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._instance_id = uuid.uuid4().hex
        self._running = True
        self._active_tasks: set[asyncio.Task[None]] = set()

    # ── public entry points ────────────────────────────────────────────────

    async def run(self) -> None:
        self._setup_signals()
        engine = get_engine(self._settings)
        self._sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        logger.info("worker instance=%s starting", self._instance_id)

        await self._init_heartbeat()

        heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        try:
            await self._poll_loop()
        finally:
            self._running = False
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task
            await self._shutdown()
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

        async with self._sessionmaker() as session:
            repo = HeartbeatRepository(session)
            await repo.upsert(
                self._instance_id,
                "oryxenai-worker",
                {"process": f"worker-{self._instance_id}"},
            )
            await session.commit()

    async def _heartbeat_loop(self) -> None:
        from oryxenai.jobs.heartbeat import HeartbeatRepository

        interval = self._settings.worker.heartbeat_interval
        while self._running:
            try:
                async with self._sessionmaker() as session:
                    repo = HeartbeatRepository(session)
                    await repo.upsert(self._instance_id, "oryxenai-worker")
                    await session.commit()
            except Exception as exc:
                logger.warning("worker heartbeat transient error=%s", type(exc).__name__)
            await asyncio.sleep(interval)

    # ── main poll loop ─────────────────────────────────────────────────────

    async def _poll_loop(self) -> None:
        while self._running:
            try:
                await self._recover_stale()
                claimed = await self._claim_due()
                for job in claimed:
                    self._dispatch(job)
            except Exception as exc:
                logger.warning("worker poll transient error=%s", type(exc).__name__)
            finally:
                await asyncio.sleep(self._settings.worker.polling_interval)

    async def _claim_due(self) -> list[Any]:
        async with self._sessionmaker() as session:
            repo = JobRepository(session)
            jobs = await repo.claim_batch(
                self._instance_id,
                self._settings.worker_job.lease_duration,
                self._settings.worker.claim_batch_size,
            )
            await session.commit()
        return jobs

    async def _recover_stale(self) -> None:
        async with self._sessionmaker() as session:
            repo = JobRepository(session)
            stale = await repo.recover_stale(
                self._instance_id,
                self._settings.worker_job.lease_duration,
                self._settings.worker.claim_batch_size,
            )
            if stale:
                for job in stale:
                    self._dispatch(job)
            await session.commit()

    # ── dispatch ───────────────────────────────────────────────────────────

    def _dispatch(self, job: Any) -> None:
        task = asyncio.create_task(self._execute_one(job))
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)

    async def _execute_one(self, job: Any) -> None:
        job_id = job.id
        kind = job.job_kind
        handler = get_handler(kind)
        if handler is None:
            await self._fail_job(
                job_id,
                permanent(
                    "UNKNOWN_JOB_KIND",
                    f"No handler registered for '{kind}'.",
                ),
            )
            return

        heartbeat_task = asyncio.create_task(self._renew_lease_loop(job_id))
        try:
            payload = dict(job.payload or {})
            payload["attempt"] = job.attempt
            payload["max_attempts"] = job.max_attempts
            result = await asyncio.wait_for(
                handler.execute(payload, self._instance_id),
                timeout=self._settings.worker_job.handler_timeout,
            )
        except TimeoutError:
            await self._fail_job(
                job_id,
                retryable(
                    "JOB_TIMEOUT",
                    f"Handler exceeded {self._settings.worker_job.handler_timeout}s timeout.",
                ),
            )
            return
        except Exception as exc:
            error: Any
            if hasattr(exc, "code") and hasattr(exc, "message") and hasattr(exc, "retryable"):
                error = exc
            else:
                logger.warning("job handler failed kind=%s error=%s", kind, type(exc).__name__)
                error = retryable("HANDLER_ERROR", "The background job handler failed.")
            await self._fail_job(
                job_id,
                error,
            )
            return
        finally:
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task

        if result.get("status") == "failed":
            await self._fail_job(
                job_id,
                permanent("JOB_HANDLER_FAILED", "The Discovery operation failed safely."),
            )
            return
        await self._complete_job(job_id, result)

    async def _renew_lease_loop(self, job_id: Any) -> None:
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
                    await repo.update_heartbeat(job_id)
                    await session.commit()
            except Exception as exc:
                logger.warning(
                    "heartbeat renewal failed job_id=%s error=%s", job_id, type(exc).__name__
                )

    async def _complete_job(self, job_id: Any, result: dict[str, Any]) -> None:
        async with self._sessionmaker() as session:
            repo = JobRepository(session)
            await repo.mark_succeeded(job_id, result)
            await session.commit()

    async def _fail_job(self, job_id: Any, error: Any) -> None:
        async with self._sessionmaker() as session:
            repo = JobRepository(session)
            job = await repo.get_by_id(job_id)
            if job is None:
                return
            retry = self._settings.worker_retry
            job_error = error if hasattr(error, "retryable") else permanent("UNKNOWN", str(error))
            if should_retry(job_error, job.attempt, retry.max_attempts):
                delay = delay_for_attempt(
                    job.attempt, retry.base_delay, retry.max_delay, retry.jitter
                )
                available_at = datetime.now(UTC)
                from datetime import timedelta

                available_at = available_at + timedelta(seconds=delay)
                await repo.mark_failed(
                    job_id,
                    {
                        "code": job_error.code,
                        "message": job_error.message,
                        "retryable": job_error.retryable,
                    },
                    available_at=available_at,
                )
            else:
                await repo.mark_failed(
                    job_id,
                    {
                        "code": job_error.code,
                        "message": job_error.message,
                        "retryable": False,
                    },
                )
            await session.commit()

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
    worker = Worker()
    asyncio.run(worker.run())


if __name__ == "__main__":
    main()
