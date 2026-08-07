"""Deterministic validators for Discovery OUTPUTS only.

Transport-level validation: the response must be parseable, the required
envelope keys must exist, the mode must be known, and question entries must
contain usable text. The brief content itself is free Markdown and is NOT
business-validated.
"""

from __future__ import annotations

from typing import Any

from oryxenai.agents.discovery.schemas import OperationMode, QuestionKind

_VALID_MODES_A = {
    OperationMode.NEEDS_DETAILS.value,
    OperationMode.ASK_QUESTIONS.value,
    OperationMode.READY_FOR_BRIEF.value,
}
_VALID_QUESTION_KINDS = {item.value for item in QuestionKind}


class ValidationOutcome:
    """Immutable result of a validation run."""

    def __init__(self, is_valid: bool, errors: list[str]) -> None:
        self.is_valid = is_valid
        self.errors = errors

    def __bool__(self) -> bool:
        return self.is_valid


def validate_questions_output(data: dict[str, Any], max_questions: int = 8) -> ValidationOutcome:
    """Validate the questions output of the understand_and_question model call."""
    errors: list[str] = []

    mode = data.get("mode")
    if mode not in _VALID_MODES_A:
        errors.append(f"'mode' must be one of {sorted(_VALID_MODES_A)}; got {mode!r}")

    questions = data.get("questions")
    if not isinstance(questions, list):
        errors.append("'questions' must be a list")
        questions = []
    if len(questions) > max_questions:
        errors.append(f"Too many questions: {len(questions)} (max {max_questions})")

    seen: set[str] = set()
    for index, question in enumerate(questions):
        if not isinstance(question, dict):
            errors.append(f"Question {index} is not an object")
            continue
        qid = str(question.get("id", "") or question.get("local_key", ""))
        text = str(question.get("text", "") or "").strip()
        if not qid:
            errors.append(f"Question {index} has no id")
        elif qid in seen:
            errors.append(f"Duplicate question id: {qid}")
        else:
            seen.add(qid)
        if not text:
            errors.append(f"Question {index} has no text")
        kind = question.get("kind", "text")
        if kind not in _VALID_QUESTION_KINDS:
            errors.append(f"Question {index} has invalid kind: {kind}")
        elif kind in {"single_select", "multi_select"}:
            options = question.get("options")
            if not isinstance(options, list) or not options:
                errors.append(f"Question {index} ({kind}) has no options")
            else:
                for option in options:
                    if not isinstance(option, dict) or not str(option.get("id", "")).strip():
                        errors.append(f"Question {index} has an option without an id")

    if mode == OperationMode.NEEDS_DETAILS.value and questions:
        errors.append("NEEDS_DETAILS must have an empty questions list")
    if mode == OperationMode.ASK_QUESTIONS.value and not questions:
        errors.append("ASK_QUESTIONS must have at least one question")
    if mode == OperationMode.READY_FOR_BRIEF.value and questions:
        errors.append("READY_FOR_BRIEF must have an empty questions list")
    if not str(data.get("assistant_message", "") or "").strip():
        errors.append("'assistant_message' is empty")

    return ValidationOutcome(len(errors) == 0, errors)


def validate_brief_output(data: dict[str, Any], max_projects: int = 5) -> ValidationOutcome:
    """Validate the brief output of the build_or_revise_brief model call.

    The brief is free Markdown; only the transport envelope is checked.
    """
    errors: list[str] = []

    mode = data.get("mode")
    if mode != OperationMode.BRIEF_READY.value:
        errors.append(f"'mode' must be BRIEF_READY; got {mode!r}")
    if not str(data.get("assistant_message", "") or "").strip():
        errors.append("'assistant_message' is empty")
    if not str(data.get("brief_title", "") or "").strip():
        errors.append("'brief_title' is empty")
    if not str(data.get("brief_markdown", "") or "").strip():
        errors.append("'brief_markdown' is empty")
    open_items = data.get("open_items")
    if open_items is not None and not isinstance(open_items, list):
        errors.append("'open_items' must be a list when present")
    memory_update = data.get("memory_update")
    if memory_update is not None and not isinstance(memory_update, dict):
        errors.append("'memory_update' must be a dict when present")

    return ValidationOutcome(len(errors) == 0, errors)
