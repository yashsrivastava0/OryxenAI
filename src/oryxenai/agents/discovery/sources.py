"""Deterministic source snapshots and span indexing for Discovery."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from oryxenai.agents.discovery.schemas import SourceDocument, SourceSpan

_SPAN_TARGET_CHARS = 1800


def create_source_document(
    text: str,
    *,
    label: str,
    source_kind: str = "user_provided",
) -> SourceDocument:
    """Capture exact text, its digest, and browser-compatible source offsets."""

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    document_id = f"src_{uuid4().hex}"
    ranges = _span_ranges(text)
    boundary_indices = {boundary for start, end in ranges for boundary in (start, end)}
    offsets = {0: 0}
    utf16_units = 0
    for character_index, character in enumerate(text, start=1):
        utf16_units += 2 if ord(character) > 0xFFFF else 1
        if character_index in boundary_indices:
            offsets[character_index] = utf16_units
    spans = [
        SourceSpan(
            id=f"{document_id}:span:{index:04d}",
            start=offsets[start],
            end=offsets[end],
        )
        for index, (start, end) in enumerate(ranges, start=1)
    ]
    return SourceDocument(
        id=document_id,
        label=label,
        source_kind=source_kind,
        original_text=text,
        sha256=digest,
        spans=spans,
        created_at=datetime.now(UTC).isoformat(),
    )


def documents_from_intake(intake: dict[str, Any]) -> list[SourceDocument]:
    fields = (
        ("source_text", "Pasted source material", "user_provided"),
        ("document_text", "Document text", "user_provided"),
        ("message", "Your notes", "user_provided"),
        ("goal", "Portfolio goal", "user_intent"),
    )
    documents: list[SourceDocument] = []
    for field, label, source_kind in fields:
        text = str(intake.get(field, "") or "")
        if text.strip():
            documents.append(create_source_document(text, label=label, source_kind=source_kind))
    return documents


def document_from_answer(question_id: str, answer: str) -> SourceDocument | None:
    if not answer.strip():
        return None
    return create_source_document(
        answer,
        label=f"Answer to {question_id}",
        source_kind="user_answer",
    )


def source_segments_for_model(documents: list[SourceDocument]) -> list[dict[str, Any]]:
    """Return the source text once, partitioned into addressable evidence spans."""

    packets: list[dict[str, Any]] = []
    for document in documents:
        char_offsets = _utf16_offsets_to_character_offsets(
            document.original_text,
            [offset for span in document.spans for offset in (span.start, span.end)],
        )
        spans: list[dict[str, str]] = []
        for index, span in enumerate(document.spans):
            start = char_offsets[index * 2]
            end = char_offsets[index * 2 + 1]
            spans.append({"id": span.id, "text": document.original_text[start:end]})
        packets.append(
            {
                "id": document.id,
                "label": document.label,
                "source_kind": document.source_kind,
                "sha256": document.sha256,
                "spans": spans,
            }
        )
    return packets


def _span_ranges(text: str) -> list[tuple[int, int]]:
    """Split on stable whitespace boundaries without dropping any character."""

    if not text:
        return []
    ranges: list[tuple[int, int]] = []
    start = 0
    length = len(text)
    while start < length:
        proposed_end = min(start + _SPAN_TARGET_CHARS, length)
        if proposed_end < length:
            newline = text.rfind("\n", start + 1, proposed_end)
            space = text.rfind(" ", start + 1, proposed_end)
            boundary = max(newline + 1, space + 1)
            end = boundary if boundary > start + _SPAN_TARGET_CHARS // 2 else proposed_end
        else:
            end = length
        ranges.append((start, end))
        start = end
    return ranges


def _utf16_length(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def _utf16_offsets_to_character_offsets(text: str, offsets: list[int]) -> list[int]:
    """Translate persisted JavaScript offsets in linear time and span-sized space."""

    requested = set(offsets)
    resolved: dict[int, int] = {0: 0} if 0 in requested else {}
    units = 0
    for index, char in enumerate(text, start=1):
        units += 2 if ord(char) > 0xFFFF else 1
        if units in requested:
            resolved[units] = index
    final_units = _utf16_length(text)
    if final_units in requested:
        resolved[final_units] = len(text)
    return [resolved.get(offset, len(text)) for offset in offsets]
