"""Construction and compatibility handling for safe terminal reports."""

from __future__ import annotations

import hashlib
from typing import Any

from pydantic import ValidationError

from oryxenai.agents.code_generator.core.development_schemas import (
    Diagnostic,
    GenerationProjection,
    SafeIssue,
    TerminalFailureReport,
)

_DEFAULT_NEXT_ACTION = "Review the safe diagnostic and start a corrected attempt."


def _fingerprint(code: str, message: str, generation_id: str) -> str:
    return hashlib.sha256(f"{generation_id}:{code}:{message}".encode()).hexdigest()[:32]


def _diagnostics(
    projection: GenerationProjection | None,
    issue: SafeIssue,
    *,
    phase: str,
    generation_id: str,
) -> list[Diagnostic]:
    """Convert internal source diagnostics into the public diagnostic shape."""

    result: list[Diagnostic] = []
    seen: set[str] = set()
    for item in (list(projection.diagnostic_history) if projection is not None else []) + (
        list(projection.diagnostics) if projection is not None else []
    ):
        if item.diagnostic_id in seen:
            continue
        seen.add(item.diagnostic_id)
        result.append(
            Diagnostic(
                diagnostic_id=item.diagnostic_id,
                group=("type_build_artifact" if item.group == "typecheck" else "source_contract"),
                code=item.code,
                severity=item.severity,
                owner=item.owner,
                phase=item.phase,
                work_unit_id=item.work_unit_id,
                route_id=item.route_id,
                command=item.command,
                normalized_message=item.normalized_message,
                file=item.file,
                line=item.line,
                column=item.column,
                symbol=item.symbol,
                expected=item.expected,
                observed=item.observed,
                fingerprint=item.fingerprint,
            )
        )
    issue_code = issue.code or "GENERATION_FAILED"
    issue_message = issue.message or "The Code Generator stage failed safely."
    issue_id = f"terminal-{_fingerprint(issue_code, issue_message, generation_id)}"
    if issue_id not in seen:
        result.insert(
            0,
            Diagnostic(
                diagnostic_id=issue_id,
                group="source_contract",
                code=issue_code,
                severity="blocking",
                owner="generator",
                phase=phase,
                normalized_message=issue_message[:500],
                fingerprint=_fingerprint(issue_code, issue_message, generation_id),
            ),
        )
    return result


def build_terminal_failure_report(
    *,
    run_id: str,
    issue: SafeIssue,
    projection: GenerationProjection | None = None,
) -> TerminalFailureReport:
    """Create the strict, safe report persisted for every generation failure."""

    generation_id = (
        projection.generation_id
        if projection is not None and projection.generation_id
        else f"generation-{run_id}"
    )
    phase = projection.phase if projection is not None and projection.phase else "generation"
    input_hashes: dict[str, str] = {}
    if projection is not None:
        for key, value in (
            ("input_receipt", projection.input_receipt_hash),
            ("site_plan", projection.site_plan_hash),
            ("resource_ledger", projection.resource_ledger_hash),
            ("dependency_ledger", projection.dependency_ledger_hash),
        ):
            if value:
                input_hashes[key] = value
        if projection.accepted_checkpoint is not None:
            input_hashes["source_checkpoint"] = projection.accepted_checkpoint.checkpoint_hash

    resource_failures: list[SafeIssue] = []
    if projection is not None:
        resource_failures.extend(
            item
            for item in projection.issues
            if item.code.upper().startswith(("RESOURCE_", "DEPENDENCY_"))
        )
    if issue.code.upper().startswith(("RESOURCE_", "DEPENDENCY_")):
        resource_failures.append(issue)

    repair_receipts: list[str] = []
    if projection is not None:
        repair_receipts = [
            receipt.receipt_id
            for receipt in projection.call_receipts
            if receipt.operation_id.casefold() == "repair"
        ]

    return TerminalFailureReport(
        generation_id=generation_id,
        terminal_code=issue.code or "GENERATION_FAILED",
        owner="generator",
        phase=phase,
        input_plan_source_build_hashes=input_hashes,
        diagnostics=_diagnostics(
            projection,
            issue,
            phase=phase,
            generation_id=generation_id,
        ),
        fingerprint_occurrences=(
            dict(projection.repair_fingerprint_counts) if projection is not None else {}
        ),
        resource_dependency_failures=resource_failures,
        accepted_checkpoint=(
            projection.accepted_checkpoint.checkpoint_hash
            if projection is not None and projection.accepted_checkpoint is not None
            else ""
        ),
        repair_receipts=repair_receipts,
        active_preview_preserved=True,
        safe_user_summary=(issue.message or "The Code Generator stage failed safely.")[:500],
        recommended_next_action=issue.next_action or _DEFAULT_NEXT_ACTION,
    )


def normalize_terminal_failure(
    raw: Any,
    *,
    run_id: str,
    projection: GenerationProjection | None = None,
) -> dict[str, Any] | None:
    """Return a strict report while keeping old malformed rows readable."""

    if raw is None:
        return None
    if isinstance(raw, TerminalFailureReport):
        return raw.model_dump(mode="json")
    if isinstance(raw, dict):
        try:
            return TerminalFailureReport.model_validate(raw).model_dump(mode="json")
        except ValidationError:
            first_issue = raw.get("first_issue")
            first_issue = first_issue if isinstance(first_issue, dict) else {}
            issue = SafeIssue(
                code=str(
                    raw.get("terminal_code")
                    or raw.get("code")
                    or first_issue.get("code")
                    or "GENERATION_FAILED"
                ),
                message=str(
                    raw.get("safe_user_summary")
                    or raw.get("message")
                    or first_issue.get("message")
                    or "The Code Generator stage failed safely."
                ),
                next_action=str(raw.get("recommended_next_action") or _DEFAULT_NEXT_ACTION),
            )
            return build_terminal_failure_report(
                run_id=run_id,
                issue=issue,
                projection=projection,
            ).model_dump(mode="json")
    return build_terminal_failure_report(
        run_id=run_id,
        issue=SafeIssue(
            code="GENERATION_FAILED",
            message="The Code Generator stage failed safely.",
            next_action=_DEFAULT_NEXT_ACTION,
        ),
        projection=projection,
    ).model_dump(mode="json")


__all__ = ["build_terminal_failure_report", "normalize_terminal_failure"]
