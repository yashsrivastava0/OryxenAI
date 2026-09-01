"""Translate the v4 source wire envelope into the internal workflow DTO."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from oryxenai.agents.code_generator.core.development_schemas import (
    ExportedSignature,
    GenerationAccepted,
    GenerationCannotComplete,
    GenerationChanges,
    GenerationContextReceipt,
    GenerationRequests,
    GenerationResult,
    SourceGenerationEnvelopeV2,
)
from oryxenai.agents.code_generator.core.source_lexing import strip_source_comments

_DEFAULT_DECLARATION_RE = re.compile(
    r"(?m)^\s*export\s+default\s+(?:(?:async\s+)?function|class)"
    r"(?:\s+(?P<name>[A-Za-z_$][\w$]*))?"
)
_NAMED_DECLARATION_RE = re.compile(
    r"(?m)^\s*export\s+(?:declare\s+)?(?P<kind>async\s+function|function|class|"
    r"const|let|var|type|interface|enum)\s+(?P<name>[A-Za-z_$][\w$]*)"
)
_DEFAULT_IDENTIFIER_RE = re.compile(
    r"(?m)^\s*export\s+default\s+(?P<name>[A-Za-z_$][\w$]*)\s*;?\s*$"
)
_EXPORT_LIST_RE = re.compile(r"(?m)^\s*export\s*\{(?P<items>[^}]*)\}")


def _deduplicate_identical_files(changes: GenerationChanges) -> GenerationChanges:
    """Collapse byte-identical duplicate file entries from a structured response.

    Repeating the same path, operation, and complete body carries no additional
    source authority.  Conflicting duplicates remain untouched so the source
    validator rejects the ambiguous response instead of choosing one body.
    """

    unique = []
    by_path: dict[str, Any] = {}
    for change in changes.files:
        path = change.path.replace("\\", "/")
        previous = by_path.get(path)
        if previous is None:
            by_path[path] = change
            unique.append(change)
            continue
        if (
            previous.operation == change.operation
            and previous.complete_utf8_content == change.complete_utf8_content
        ):
            continue
        unique.append(change)
    if len(unique) == len(changes.files):
        return changes
    return changes.model_copy(update={"files": unique})


def _scope_exported_signatures(changes: GenerationChanges) -> GenerationChanges:
    """Discard signatures for files that were not emitted by this operation.

    Export signatures describe changed source files; they do not grant file
    ownership or authorize source mutations. Models sometimes repeat a known
    sibling signature while returning a bounded CSS/TSX polish. Keeping that
    non-authoritative echo would reject otherwise inspectable source before the
    host can enforce the important direction: every changed exported file must
    still have a signature.
    """

    changed_paths = {item.path.replace("\\", "/") for item in changes.files}
    scoped = [
        item
        for item in changes.exported_signatures
        if item.path.replace("\\", "/") in changed_paths
    ]
    if len(scoped) == len(changes.exported_signatures):
        return changes
    return changes.model_copy(update={"exported_signatures": scoped})


def _derived_export_signature(path: str, source: str) -> ExportedSignature | None:
    suffix = Path(path).suffix.casefold()
    if suffix not in {".js", ".jsx", ".ts", ".tsx"}:
        return None
    clean = strip_source_comments(source)
    match = _DEFAULT_DECLARATION_RE.search(clean)
    if match:
        name = match.group("name") or "default"
        return ExportedSignature(
            path=path,
            export_name=name,
            kind="component" if suffix in {".jsx", ".tsx"} else "function",
        )
    match = _NAMED_DECLARATION_RE.search(clean)
    if match:
        declaration_kind = match.group("kind").removeprefix("async ")
        name = match.group("name")
        kind: Literal["component", "function", "type", "constant"]
        if declaration_kind == "function":
            kind = "component" if suffix in {".jsx", ".tsx"} and name[:1].isupper() else "function"
        elif declaration_kind == "class":
            kind = "component" if suffix in {".jsx", ".tsx"} and name[:1].isupper() else "type"
        elif declaration_kind in {"type", "interface", "enum"}:
            kind = "type"
        else:
            kind = "constant"
        return ExportedSignature(path=path, export_name=name, kind=kind)
    match = _DEFAULT_IDENTIFIER_RE.search(clean)
    if match:
        return ExportedSignature(
            path=path,
            export_name=match.group("name"),
            kind="component" if suffix in {".jsx", ".tsx"} else "constant",
        )
    for match in _EXPORT_LIST_RE.finditer(clean):
        for item in match.group("items").split(","):
            value = item.strip()
            if not value:
                continue
            name = re.sub(r"^type\s+", "", value).split(" as ", 1)[0].strip()
            if re.fullmatch(r"[A-Za-z_$][\w$]*", name):
                return ExportedSignature(path=path, export_name=name, kind="constant")
    return None


def _complete_missing_exported_signatures(changes: GenerationChanges) -> GenerationChanges:
    """Derive omitted signature metadata from exact changed source exports.

    A signature describes returned bytes; it does not grant ownership or make
    an export valid. The downstream semantic validator remains authoritative
    and still rejects a changed exported file when no literal export can be
    derived.
    """

    signatures = list(changes.exported_signatures)
    described_paths = {item.path.replace("\\", "/") for item in signatures}
    for change in changes.files:
        path = change.path.replace("\\", "/")
        if path in described_paths:
            continue
        signature = _derived_export_signature(path, change.complete_utf8_content)
        if signature is None:
            continue
        signatures.append(signature)
        described_paths.add(path)
    if len(signatures) == len(changes.exported_signatures):
        return changes
    return changes.model_copy(update={"exported_signatures": signatures})


def adapt_v4_generation_result(
    envelope: SourceGenerationEnvelopeV2,
    *,
    operation_id: str,
    context_receipt: GenerationContextReceipt,
    required_coverage: Mapping[str, Any] | None = None,
) -> GenerationResult:
    """Adapt the mapping-free v4 envelope without weakening its evidence.

    The durable orchestration code still has a legacy internal result type for
    compatibility with the v3 workflow.  V4 model calls must nevertheless use
    ``SourceGenerationEnvelopeV2`` on the wire; this adapter is the sole
    boundary between those two representations.
    """

    if envelope.result == "changes":
        changes = _complete_missing_exported_signatures(
            _scope_exported_signatures(
                GenerationChanges(
                    files=list(envelope.files),
                    exported_signatures=list(envelope.exported_signatures),
                    content_coverage=list(envelope.content_ids),
                    criterion_coverage=list(envelope.criterion_ids),
                    resource_usage=list(envelope.resource_slot_ids),
                    interaction_coverage=list(envelope.interaction_ids),
                )
            )
        )
        result = GenerationResult(
            operation_id=operation_id,
            based_on_context_receipt=context_receipt.context_hash,
            mode="changes",
            changes=changes,
        )
        return stamp_v4_required_coverage(result, required_coverage)
    if envelope.result == "requests":
        return GenerationResult(
            operation_id=operation_id,
            based_on_context_receipt=context_receipt.context_hash,
            mode="requests",
            requests=GenerationRequests(
                resource_requests=list(envelope.resource_requests),
                dependency_requests=list(envelope.dependency_requests),
            ),
        )
    if envelope.result == "accepted":
        return GenerationResult(
            operation_id=operation_id,
            based_on_context_receipt=context_receipt.context_hash,
            mode="accepted",
            accepted=GenerationAccepted(
                summary="The v4 source work unit was accepted.",
                verified_contracts=[
                    *envelope.content_ids,
                    *envelope.criterion_ids,
                    *envelope.resource_slot_ids,
                    *envelope.interaction_ids,
                ],
            ),
        )
    detail = envelope.failure_details[0]
    return GenerationResult(
        operation_id=operation_id,
        based_on_context_receipt=context_receipt.context_hash,
        mode="cannot_complete",
        cannot_complete=GenerationCannotComplete(
            code=detail.code,
            safe_reason=detail.message,
            missing_authority_or_capability=detail.next_action,
        ),
    )


def stamp_v4_required_coverage(
    result: GenerationResult,
    required_coverage: Mapping[str, Any] | None,
) -> GenerationResult:
    """Stamp trusted work-unit coverage instead of trusting a model echo.

    V4 validates coverage against actual source calls, selectors, markers, and
    resource bindings after changes are applied.  The four envelope arrays are
    therefore execution metadata already known to the host, not independent
    model evidence.  Stamping them prevents a transcription error in a long ID
    list from discarding otherwise inspectable source while preserving every
    source-bearing field exactly as returned.
    """

    if result.mode != "changes" or result.changes is None or not required_coverage:
        return result
    fields = {
        "content_ids": "content_coverage",
        "criterion_ids": "criterion_coverage",
        "resource_slot_ids": "resource_usage",
        "interaction_ids": "interaction_coverage",
    }
    updates: dict[str, list[str]] = {}
    for contract_name, result_name in fields.items():
        if contract_name not in required_coverage:
            continue
        value = required_coverage[contract_name]
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            updates[result_name] = list(value)
    if not updates:
        return result
    stamped = result.changes.model_copy(update=updates) if updates else result.changes
    return result.model_copy(update={"changes": _deduplicate_identical_files(stamped)})


__all__ = ["adapt_v4_generation_result", "stamp_v4_required_coverage"]
