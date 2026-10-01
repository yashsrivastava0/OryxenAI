"""Repair model output into the strict Discovery state shapes.

Every function is pure: it returns a new structure and never mutates its input,
so it can run as the result validator (the executor and cache hand it a shallow
copy) and again on the final result. A response is rejected only when nothing
usable can be recovered: a non-object, or a brief with no Markdown at all.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from pydantic import ValidationError

from oryxenai.agents.discovery.dossier import as_text, as_text_list, build_dossier
from oryxenai.agents.discovery.schemas import (
    OperationMode,
    QuestionHistoryEvent,
    SourceDocument,
)

_SELECT_KINDS = {"single_select", "multi_select"}
_KIND_ALIASES = {
    "text": "text",
    "free_text": "text",
    "freetext": "text",
    "open": "text",
    "open_ended": "text",
    "short_text": "text",
    "long_text": "text",
    "string": "text",
    "single_select": "single_select",
    "single": "single_select",
    "select": "single_select",
    "radio": "single_select",
    "choice": "single_select",
    "single_choice": "single_select",
    "multiple_choice": "single_select",
    "multi_select": "multi_select",
    "multi": "multi_select",
    "multiselect": "multi_select",
    "multiple_select": "multi_select",
    "checkbox": "multi_select",
    "boolean": "boolean",
    "bool": "boolean",
    "yes_no": "boolean",
    "yesno": "boolean",
}
_DEFAULT_MESSAGES = {
    OperationMode.NEEDS_DETAILS.value: (
        "Share whatever you have — a resume, bio, links, projects, or just your goals — "
        "and I'll take it from there."
    ),
    OperationMode.ASK_QUESTIONS.value: "I have a couple of quick questions to get this right.",
    OperationMode.READY_FOR_BRIEF.value: "Thanks — I have what I need. Preparing your brief now.",
}
_DEFAULT_BRIEF_MESSAGE = (
    "I prepared your Discovery brief. Review it, ask for any changes, or approve it to continue."
)
_MAX_OPEN_ITEMS = 40


def gap_id_for(text: str) -> str:
    normalized = " ".join(text.casefold().split())
    return "gap_" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def normalize_questions(
    data: Any,
    max_questions: int = 3,
    *,
    closed_gap_ids: set[str] | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Repair a question round. Returns ``(output, errors)``; output is None only if unusable."""

    if not isinstance(data, dict):
        return None, ["Model output is not a JSON object"]
    closed = closed_gap_ids or set()
    raw_mode = as_text(data.get("mode")).upper().replace(" ", "_").replace("-", "_")

    questions: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    raw_questions = data.get("questions")
    for item in raw_questions if isinstance(raw_questions, list) else []:
        question = _normalize_question(item, len(questions) + 1, used_ids, closed)
        if question is not None:
            questions.append(question)
        if len(questions) >= max(0, max_questions):
            break

    if raw_mode in {OperationMode.NEEDS_DETAILS.value, OperationMode.READY_FOR_BRIEF.value}:
        mode = raw_mode
        questions = []
    elif questions:
        mode = OperationMode.ASK_QUESTIONS.value
    else:
        mode = OperationMode.READY_FOR_BRIEF.value

    message = (
        as_text(data.get("assistant_message") or data.get("message")) or _DEFAULT_MESSAGES[mode]
    )
    return {"mode": mode, "assistant_message": message, "questions": questions}, []


def _normalize_question(
    item: Any, index: int, used_ids: set[str], closed_gap_ids: set[str]
) -> dict[str, Any] | None:
    if isinstance(item, str):
        item = {"text": item}
    if not isinstance(item, dict):
        return None
    text = as_text(item.get("text") or item.get("question") or item.get("prompt"))
    if not text:
        return None
    gap_id = as_text(item.get("gap_id")) or gap_id_for(text)
    if gap_id in closed_gap_ids:
        return None

    kind = _KIND_ALIASES.get(
        as_text(item.get("kind") or item.get("type"))
        .casefold()
        .replace(" ", "_")
        .replace("-", "_"),
        "text",
    )
    options = _normalize_options(item.get("options") or item.get("choices"))
    if kind in _SELECT_KINDS:
        if len(options) < 3:
            kind, options = "text", []
        else:
            options = options[:3]
    else:
        options = []

    base = re.sub(r"[^a-z0-9_]+", "_", as_text(item.get("id")).casefold()).strip("_")[:48]
    question_id = base or f"q{index}"
    suffix = 2
    while question_id in used_ids:
        question_id = f"{base or f'q{index}'}_{suffix}"
        suffix += 1
    used_ids.add(question_id)

    return {
        "id": question_id,
        "text": text,
        "help_text": as_text(item.get("help_text") or item.get("hint")) or None,
        "kind": kind,
        "options": options,
        "reason": as_text(item.get("reason")) or None,
        "gap_id": gap_id,
        "affected_ids": [],
        "allow_skip": True,
        "allow_auto": False,
    }


def _normalize_options(raw: Any) -> list[dict[str, str]]:
    options: list[dict[str, str]] = []
    labels: set[str] = set()
    used_ids: set[str] = set()
    for item in raw if isinstance(raw, list) else []:
        label = (
            as_text(item.get("label") or item.get("text") or item.get("name"))
            if isinstance(item, dict)
            else as_text(item)
        )
        if not label or label.casefold() in labels:
            continue
        labels.add(label.casefold())
        option_id = as_text(item.get("id")) if isinstance(item, dict) else ""
        if not option_id or option_id in used_ids:
            option_id = f"o{len(options) + 1}"
            while option_id in used_ids:
                option_id += "x"
        used_ids.add(option_id)
        options.append({"id": option_id, "label": label})
    return options


def normalize_brief(
    data: Any,
    *,
    documents: list[SourceDocument],
    question_events: list[QuestionHistoryEvent],
    goal_text: str = "",
) -> tuple[dict[str, Any] | None, list[str]]:
    """Repair a brief response. Returns ``(output, errors)``; output is None only if unusable."""

    if not isinstance(data, dict):
        return None, ["Model output is not a JSON object"]
    markdown = as_text(
        data.get("brief_markdown")
        or data.get("brief")
        or data.get("markdown")
        or data.get("report")
    )
    if not markdown:
        return None, ["'brief_markdown' is empty"]

    title = (
        as_text(data.get("brief_title") or data.get("title"))
        or _title_from_markdown(markdown)
        or "Portfolio Discovery Brief"
    )
    summary = as_text(data.get("user_summary") or data.get("summary")) or _summary_from_markdown(
        markdown
    )
    open_items = as_text_list(data.get("open_items"))[:_MAX_OPEN_ITEMS]
    try:
        dossier = build_dossier(
            data.get("dossier"),
            open_items=open_items,
            goal_text=goal_text,
            documents=documents,
            question_events=question_events,
        )
    except ValidationError as exc:
        return None, [f"dossier could not be built: {exc.error_count()} error(s)"]

    return (
        {
            "mode": OperationMode.BRIEF_READY.value,
            "assistant_message": as_text(data.get("assistant_message")) or _DEFAULT_BRIEF_MESSAGE,
            "brief_title": title,
            "brief_markdown": markdown,
            "user_summary": summary,
            "open_items": open_items,
            "dossier": dossier,
        },
        [],
    )


def _title_from_markdown(markdown: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading:
                return heading[:160]
    return ""


def _summary_from_markdown(markdown: str, limit: int = 700) -> str:
    paragraphs: list[str] = []
    for block in re.split(r"\n\s*\n", markdown):
        lines = [
            line.strip()
            for line in block.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        text = " ".join(line.lstrip("-*• ").strip() for line in lines).replace("**", "")
        if text:
            paragraphs.append(text)
        if sum(len(item) for item in paragraphs) >= limit:
            break
    summary = " ".join(paragraphs)
    if len(summary) > limit:
        summary = summary[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return summary
