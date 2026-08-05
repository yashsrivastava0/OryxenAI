"""Deterministic semantic validators for Discovery outputs.

Validates both Call A and Call B model outputs independently of the model.
"""

from __future__ import annotations

from typing import Any

from oryxenai.agents.discovery.schemas import (
    DiscoveryAnalysisResult,
    DiscoveryBrief,
    DiscoveryQuestion,
    FactStatus,
    QuestionCategory,
    SourceKind,
)


class ValidationOutcome:
    """Immutable result of a validation run."""

    def __init__(
        self,
        is_valid: bool,
        errors: list[str],
        warnings: list[str],
    ) -> None:
        self.is_valid = is_valid
        self.errors = errors
        self.warnings = warnings

    def __bool__(self) -> bool:
        return self.is_valid


def validate_evidence_excerpt(source_text: str, excerpt: str) -> bool:
    if not excerpt.strip():
        return False
    excerpt_normalized = " ".join(excerpt.split()).lower()
    source_normalized = " ".join(source_text.split()).lower()
    return excerpt_normalized in source_normalized


def validate_call_a_result(
    result: DiscoveryAnalysisResult,
    source_texts: dict[str, str],
    config: Any,
) -> ValidationOutcome:
    errors: list[str] = []
    warnings: list[str] = []

    if result.schema_version != 1:
        errors.append(f"Unsupported schema version: {result.schema_version}")

    fact_ids: set[str] = set()
    for fact in result.fact_candidates:
        if fact.local_key in fact_ids:
            errors.append(f"Duplicate fact key: {fact.local_key}")
            continue
        fact_ids.add(fact.local_key)

        if fact.status == FactStatus.SUPPORTED:
            if not fact.evidence:
                errors.append(f"Supported fact '{fact.local_key}' has no evidence")
                continue
            has_valid_evidence = False
            for ev in fact.evidence:
                if ev.source_kind == SourceKind.SYSTEM_DEFAULT:
                    errors.append(f"System default used as evidence for fact '{fact.local_key}'")
                    continue
                source_text = source_texts.get(ev.source_id, "")
                if validate_evidence_excerpt(source_text, ev.evidence_excerpt):
                    has_valid_evidence = True
                else:
                    errors.append(
                        f"Evidence excerpt for fact '{fact.local_key}' not found in source"
                    )
            if not has_valid_evidence:
                errors.append(f"Fact '{fact.local_key}' has no valid evidence")

    question_ids: set[str] = set()
    max_questions = getattr(config, "max_questions", 8)
    if len(result.questions) > max_questions:
        errors.append(f"Too many questions: {len(result.questions)} (max {max_questions})")

    for question in result.questions:
        if question.local_key in question_ids:
            errors.append(f"Duplicate question key: {question.local_key}")
            continue
        question_ids.add(question.local_key)

        if not _question_kind_matches_options(question):
            errors.append(f"Question '{question.local_key}' kind/options mismatch")

        if not question.allows_auto and _is_factual_question(question):
            pass
        elif question.allows_auto and _is_factual_question(question):
            errors.append(f"Factual question '{question.local_key}' incorrectly allows auto")

    return ValidationOutcome(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_call_b_result(
    brief: DiscoveryBrief,
    fact_ids: set[str],
    project_ids: set[str],
    config: Any,
) -> ValidationOutcome:
    errors: list[str] = []
    warnings: list[str] = []

    if brief.schema_version != 1:
        errors.append(f"Unsupported schema version: {brief.schema_version}")

    for fact_id in brief.downstream_fact_ids:
        if fact_id not in fact_ids:
            errors.append(f"Brief references unknown fact: {fact_id}")

    max_projects = getattr(config, "max_featured_projects", 5)
    if len(brief.featured_projects) > max_projects:
        errors.append(
            f"Too many featured projects: {len(brief.featured_projects)} (max {max_projects})"
        )

    for project in brief.featured_projects:
        if project.project_id and project.project_id not in project_ids:
            errors.append(f"Brief references unknown project: {project.project_id}")

    return ValidationOutcome(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_questions(
    questions: list[DiscoveryQuestion],
    config: Any,
) -> ValidationOutcome:
    errors: list[str] = []
    warnings: list[str] = []

    max_questions = getattr(config, "max_questions", 8)
    if len(questions) > max_questions:
        errors.append(f"Too many questions: {len(questions)} (max {max_questions})")

    ids: set[str] = set()
    for question in questions:
        if question.local_key in ids:
            errors.append(f"Duplicate question key: {question.local_key}")
        ids.add(question.local_key)

        if not _question_kind_matches_options(question):
            errors.append(f"Question '{question.local_key}' kind/options mismatch")

        if question.allows_auto and _is_factual_question(question):
            errors.append(f"Factual question '{question.local_key}' incorrectly allows auto")

    return ValidationOutcome(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_answers(
    answers: dict[str, Any],
    questions: list[DiscoveryQuestion],
    config: Any,
) -> ValidationOutcome:
    errors: list[str] = []
    warnings: list[str] = []

    question_map = {q.local_key: q for q in questions}

    for q_id, answer in answers.items():
        question = question_map.get(q_id)
        if question is None:
            errors.append(f"Answer for unknown question: {q_id}")
            continue

        mode = answer.get("mode", "answered")
        if mode == "auto" and _is_factual_question(question):
            errors.append(f"Auto not allowed for factual question: {q_id}")

        value = answer.get("value")
        if mode == "answered" and value is None:
            errors.append(f"Answer for '{q_id}' has no value")
        if question.kind.value == "boolean" and value is not None and not isinstance(value, bool):
            errors.append(f"Boolean question '{q_id}' has non-bool value")

    max_answer_chars = getattr(config, "max_answer_chars", 10000)
    for q_id, answer in answers.items():
        value = answer.get("value")
        if isinstance(value, str) and len(value) > max_answer_chars:
            errors.append(f"Answer for '{q_id}' exceeds max length")

    return ValidationOutcome(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


def _is_factual_question(question: DiscoveryQuestion) -> bool:
    factual_categories = {
        QuestionCategory.TARGET_ROLE,
        QuestionCategory.PROJECT_SELECTION,
        QuestionCategory.PERSONAL_CONTRIBUTION,
        QuestionCategory.CONFIDENTIALITY,
        QuestionCategory.CONTACT,
        QuestionCategory.CONFLICT_RESOLUTION,
    }
    return question.category in factual_categories


def _question_kind_matches_options(question: DiscoveryQuestion) -> bool:
    from oryxenai.agents.discovery.schemas import QuestionKind

    needs_options = {QuestionKind.SINGLE_SELECT, QuestionKind.MULTI_SELECT}
    return not (question.kind in needs_options and not question.options)
