"""Reconcile terminal Code Generator job failures into run state.

The durable job row is the source of truth for worker execution, but the
Code Generator run is the source of truth for the product UI.  A worker can
therefore fail after a stage has persisted its last checkpoint and before it
has written a run-level terminal report.  This module closes that gap with a
safe, idempotent, compare-and-swap update.
"""

from __future__ import annotations

from contextlib import suppress
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from oryxenai.agents.code_generator.core.development_schemas import (
    DevelopmentRunStatus,
    GenerationProjection,
    SafeIssue,
)
from oryxenai.agents.code_generator.core.terminal_failure import (
    build_terminal_failure_report,
)
from oryxenai.agents.shared.providers.errors import safe_operation_failure
from oryxenai.core.settings import get_settings
from oryxenai.db.repositories.code_generator_development import (
    CodeGeneratorDevelopmentRepository,
)
from oryxenai.db.session import get_sessionmaker

_SECURITY_FAILURE_PREFIXES = (
    "AUTHORIZATION",
    "ENTITLEMENT",
    "SECURITY",
    "PORTFOLIO_READ_ONLY",
    "CODE_GENERATOR_WORKER_CONTRACT",
)


def _as_error_dict(error: Any) -> dict[str, Any]:
    if isinstance(error, dict):
        return dict(error)
    model_dump = getattr(error, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="json")
        if isinstance(dumped, dict):
            return dumped
    return {
        "code": str(getattr(error, "code", "HANDLER_ERROR")),
        "message": str(getattr(error, "message", "Code Generator could not complete.")),
        "retryable": bool(getattr(error, "retryable", False)),
    }


def _run_id_from_payload(payload: dict[str, Any]) -> str | None:
    for key in ("code_generator_run_id", "development_run_id", "run_id"):
        value = payload.get(key)
        if value:
            return str(value)
    return None


def _stage_from_payload(payload: dict[str, Any]) -> str:
    kind = str(payload.get("job_kind") or "")
    if ".verify" in kind:
        return "verify"
    if ".generate" in kind:
        return "generate"
    if ".acquire" in kind:
        return "acquire"
    return "plan"


def _is_security_failure(error: dict[str, Any]) -> bool:
    code = str(error.get("code") or "").upper()
    return code.startswith(_SECURITY_FAILURE_PREFIXES)


def _safe_issue(error: dict[str, Any], *, stage: str) -> SafeIssue:
    code = str(error.get("code") or "CODE_GENERATOR_JOB_FAILED")
    if code == "JOB_TIMEOUT":
        message = "Code Generator timed out before this stage completed."
    elif code == "JOB_CANCELLED":
        message = "Code Generator stopped before this stage completed."
    elif code == "HANDLER_ERROR":
        message = "Code Generator could not complete this stage."
    else:
        safe = safe_operation_failure(error, operation=f"code_generator.{stage}")
        message = str(safe.get("message") or "Code Generator could not complete this stage.")

    details: dict[str, str | int | float | bool] = {}
    support_reference = error.get("support_reference")
    if isinstance(support_reference, str) and support_reference:
        details["support_reference"] = support_reference

    return SafeIssue(
        code=code[:120],
        message=message[:500],
        next_action="Retry generation with the same approved handoff.",
        details=details,
    )


async def reconcile_terminal_failure(
    payload: dict[str, Any],
    error: Any,
) -> None:
    """Persist a safe run-level attention state after a terminal job failure.

    Automatic retries are deliberately excluded.  The worker passes
    ``will_retry`` so a transient failure does not make the UI claim that the
    run is ready for manual recovery before the retry budget is exhausted.
    Authorization and worker-contract failures remain fail-closed and are
    not converted into a user retry affordance here.
    """

    error_dict = _as_error_dict(error)
    if error_dict.get("will_retry") is True:
        return
    if _is_security_failure(error_dict):
        return

    run_id = _run_id_from_payload(payload)
    if run_id is None:
        return
    try:
        run_uuid = UUID(run_id)
    except ValueError:
        return

    settings = get_settings()
    sessionmaker = get_sessionmaker(settings)
    stage = _stage_from_payload(payload)
    issue = _safe_issue(error_dict, stage=stage)

    async with sessionmaker() as db:
        repository = CodeGeneratorDevelopmentRepository(db)
        run = await repository.get(run_uuid)
        if run is None:
            return

        if run.status == DevelopmentRunStatus.READY:
            return
        if run.status == DevelopmentRunStatus.NEEDS_ATTENTION and run.terminal_failure:
            return

        projection: GenerationProjection | None = None
        if isinstance(run.generation_projection, dict):
            with suppress(ValidationError):
                projection = GenerationProjection.model_validate(run.generation_projection)

        report = build_terminal_failure_report(
            run_id=str(run.id),
            issue=issue,
            projection=projection,
        )
        expected_revision = run.revision
        updated = await repository.compare_and_swap(
            run.id,
            expected_revision=expected_revision,
            values={
                "status": DevelopmentRunStatus.NEEDS_ATTENTION,
                "terminal_failure": report.model_dump(mode="json"),
                "issues": [issue.model_dump(mode="json")],
            },
        )
        if updated is None:
            return

        await repository.append_event(
            run.id,
            event_type="needs_attention",
            level="error",
            message=issue.message,
            details={"source": "worker_terminal_failure", "code": issue.code, "stage": stage},
        )
        await db.commit()
