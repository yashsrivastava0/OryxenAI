"""Full durable Discovery live smoke test through OpenCode Go.

The smoke uses the real configured provider, service, database, and worker
handlers. It deliberately bounds every model operation so a slow model fails
clearly instead of leaving the command running indefinitely.

Run:
    uv run python scripts/live_smoke.py

Optional environment variables:
    ORA_SMOK_MODEL                    Model override for this run.
    ORA_SMOKE_TIMEOUT_A               Operation A timeout in seconds (60).
    ORA_SMOKE_TIMEOUT_B               Brief/revision timeout in seconds (120).
    ORA_SMOKE_TOTAL_TIMEOUT           Overall timeout in seconds (420).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select

from oryxenai.agents.discovery.schemas import DiscoveryAnswer
from oryxenai.agents.discovery.service import DiscoveryService
from oryxenai.core.settings import get_settings
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.repositories.discovery import DiscoveryRepository
from oryxenai.db.repositories.portfolio_sessions import PortfolioSessionRepository
from oryxenai.db.session import get_sessionmaker
from oryxenai.jobs.handlers.discovery import (
    DiscoveryBuildOrReviseBriefHandler,
    DiscoveryUnderstandAndQuestionHandler,
)
from oryxenai.jobs.service import JobService


class SmokeFailure(RuntimeError):
    """A live smoke assertion or provider operation failed."""


def _number(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise SmokeFailure(f"{name} must be a number, got {raw!r}") from exc
    if value <= 0:
        raise SmokeFailure(f"{name} must be greater than zero")
    return value


def _sample() -> dict[str, str]:
    path = Path("src/oryxenai/agents/discovery/samples/01_software_engineer_input.json")
    return json.loads(path.read_text(encoding="utf-8"))


def _answer_value(question: dict[str, Any]) -> Any:
    kind = question.get("kind", "text")
    options = question.get("options") or []
    if kind in {"single_select", "multi_select"} and options:
        first = options[0]
        if isinstance(first, dict):
            value = first.get("id", "")
            return [value] if kind == "multi_select" else value
    if kind == "boolean":
        return "true"
    return "Lead with backend/platform engineering for startup CTOs."


async def _run_handler(
    sessionmaker: Any,
    handler: Any,
    job_id: UUID,
    label: str,
    timeout: float,
) -> dict[str, Any]:
    async with sessionmaker() as db:
        job = await JobService(db).get(job_id)
        if job is None:
            raise SmokeFailure(f"{label}: job {job_id} not found")
        payload = dict(job.payload)
    print(f"[{label}] starting (timeout={timeout:.0f}s)")
    started = time.monotonic()
    try:
        result = await asyncio.wait_for(handler.execute(payload, "live-smoke"), timeout=timeout)
    except TimeoutError as exc:
        elapsed = time.monotonic() - started
        raise SmokeFailure(
            f"{label} FAILED: timeout after {elapsed:.1f}s; model is too slow for the smoke budget"
        ) from exc
    except Exception as exc:
        elapsed = time.monotonic() - started
        raise SmokeFailure(f"{label} FAILED after {elapsed:.1f}s: {exc}") from exc
    print(f"[{label}] passed in {time.monotonic() - started:.1f}s")
    return result


async def main() -> None:
    settings = get_settings()
    profile = settings.models.get_profile("discovery")
    if profile is None:
        raise SmokeFailure("[profiles.discovery] is missing")
    override = os.environ.get("ORA_SMOK_MODEL", "").strip()
    if override:
        profile.model = override
    if not profile.model:
        raise SmokeFailure("Discovery model is empty")
    sessionmaker = get_sessionmaker(settings)
    timeout_a = _number("ORA_SMOKE_TIMEOUT_A", 60.0)
    timeout_b = _number("ORA_SMOKE_TIMEOUT_B", 120.0)
    sample = _sample()
    print(f"Live durable smoke model: {profile.model}")

    async with sessionmaker() as db:
        session = await PortfolioSessionRepository(db).create("live-smoke-discovery")
        session_id = session.id
        service = DiscoveryService(DiscoveryRepository(db), JobService(db))
        started = await service.start(
            session_id,
            message=sample["message"],
            document_text=sample["document_text"],
            goal=sample["goal"],
        )
        await db.commit()
        print(f"[start] status={started['discovery']['status']}")
        operation_a_job_id = UUID(started["discovery"]["operation_a"]["job_id"])

    await _run_handler(
        sessionmaker,
        DiscoveryUnderstandAndQuestionHandler(),
        operation_a_job_id,
        "operation-a",
        timeout_a,
    )

    async with sessionmaker() as db:
        service = DiscoveryService(DiscoveryRepository(db), JobService(db))
        state = await service.get_discovery_state(session_id)
        operation_a = state["discovery"]["operation_a"]
        print(f"[operation-a] mode={operation_a['mode']} questions={len(operation_a['items'])}")
        if operation_a["mode"] == "NEEDS_DETAILS":
            follow_up = await service.start(
                session_id,
                message=sample["message"] + " Please ask only remaining high-value questions.",
                document_text=sample["document_text"],
                goal=sample["goal"],
            )
            await db.commit()
            await _run_handler(
                sessionmaker,
                DiscoveryUnderstandAndQuestionHandler(),
                UUID(follow_up["discovery"]["operation_a"]["job_id"]),
                "operation-a-follow-up",
                timeout_a,
            )
            state = await service.get_discovery_state(session_id)
            operation_a = state["discovery"]["operation_a"]
            print(
                f"[operation-a-follow-up] mode={operation_a['mode']} questions={len(operation_a['items'])}"
            )

        answers = [
            DiscoveryAnswer(
                question_id=str(question["id"]),
                mode="answered",
                value=_answer_value(question),
            )
            for question in operation_a["items"]
            if question.get("id")
        ]
        answered = await service.save_answers(session_id, answers, complete=True)
        await db.commit()
        print(f"[answers] status={answered['discovery']['status']}")
        brief_job_id = UUID(answered["discovery"]["brief"]["job_id"])

    await _run_handler(
        sessionmaker,
        DiscoveryBuildOrReviseBriefHandler(),
        brief_job_id,
        "operation-b",
        timeout_b,
    )

    async with sessionmaker() as db:
        service = DiscoveryService(DiscoveryRepository(db), JobService(db))
        review = await service.get_discovery_state(session_id)
        if review["discovery"]["status"] != "brief_review":
            raise SmokeFailure(f"brief did not reach review: {review['discovery']['status']}")
        brief = review["discovery"]["brief"]
        markdown = brief["markdown"]
        print(f"[brief] title={brief['title'][:80]!r} words={len(markdown.split())}")

        revised = await service.revise_brief(
            session_id,
            "Lead with the QueueGuard story. Make the backend/platform CTA explicit.",
        )
        await db.commit()
        revised_job_id = UUID(revised["discovery"]["brief"]["job_id"])
        print(f"[revise] status={revised['discovery']['status']}")

    await _run_handler(
        sessionmaker,
        DiscoveryBuildOrReviseBriefHandler(),
        revised_job_id,
        "revision",
        timeout_b,
    )

    async with sessionmaker() as db:
        service = DiscoveryService(DiscoveryRepository(db), JobService(db))
        review = await service.get_discovery_state(session_id)
        brief = review["discovery"]["brief"]
        if "QueueGuard" not in brief["markdown"]:
            raise SmokeFailure("revision did not preserve or add QueueGuard")
        print(f"[revised-brief] words={len(brief['markdown'].split())} queueguard=True")

        approved = await service.approve_brief(session_id)
        await db.commit()
        if approved["discovery"]["status"] != "approved":
            raise SmokeFailure("brief did not reach approved")
        approval = approved["discovery"]["brief"]["approved"]
        if not approval or not approval.get("brief_hash"):
            raise SmokeFailure("approval did not persist a brief hash")
        print(f"[approve] status=approved hash={approval['brief_hash'][:16]}")

        rows = await db.execute(
            select(AgentRun)
            .where(AgentRun.portfolio_session_id == session_id)
            .order_by(AgentRun.created_at)
        )
        runs = rows.scalars().all()
        keys = {run.agent_key for run in runs}
        if keys != {"discovery"}:
            raise SmokeFailure(f"unexpected agent keys: {keys}")
        for run in runs:
            if "reasoning_content" in str(run.model_metadata or {}):
                raise SmokeFailure("reasoning_content leaked into persisted metadata")
        print(f"[runs] count={len(runs)} agent_keys={sorted(keys)} reasoning_content_leak=False")

    print("LIVE DURABLE SMOKE PASSED")


def run() -> int:
    total_timeout = _number("ORA_SMOKE_TOTAL_TIMEOUT", 420.0)
    try:
        asyncio.run(asyncio.wait_for(main(), timeout=total_timeout))
    except TimeoutError:
        print(
            f"LIVE DURABLE SMOKE FAILED: overall timeout after {total_timeout:.0f}s",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(f"LIVE DURABLE SMOKE FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
