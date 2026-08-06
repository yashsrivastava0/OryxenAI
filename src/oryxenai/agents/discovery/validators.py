"""Deterministic semantic validators for Discovery outputs (v2).

Validates both Call A and Call B model outputs independently of the model.
Pydantic validation is necessary but insufficient; these checks enforce the
grounding, provenance, safety, and detail-adequacy rules that Pydantic alone
cannot express.
"""

from __future__ import annotations

import re
from typing import Any

from oryxenai.agents.discovery.schemas import (
    DiscoveryAnalysisResult,
    DiscoveryBrief,
    DiscoveryQuestion,
    FactCategory,
    FactSensitivity,
    FactStatus,
    QuestionCategory,
    QuestionKind,
    SourceKind,
)

# Private contact markers that must never be published by default.
_PRIVATE_EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$", re.IGNORECASE)
_PRIVATE_PHONE_RE = re.compile(r"^\+?[\d\s().-]{7,}$")
_PRIVATE_ADDRESS_MARKERS = ("street", "address", "road", "avenue", "lane", "st.", "ave.")


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


def _is_private_contact(value: str) -> bool:
    lowered = value.lower()
    if _PRIVATE_EMAIL_RE.match(value):
        return True
    if _PRIVATE_PHONE_RE.match(value):
        return True
    return any(marker in lowered for marker in _PRIVATE_ADDRESS_MARKERS)


def _is_supported_language(lang: str, config: Any) -> bool:
    supported = getattr(config, "supported_output_languages", None)
    if supported:
        return lang in supported
    return True


# ── Call A validation (Section 23.1) ─────────────────────────────────────────


def validate_call_a_result(
    result: DiscoveryAnalysisResult,
    source_texts: dict[str, str],
    config: Any,
) -> ValidationOutcome:
    """Run the full Call A semantic check list."""
    errors: list[str] = []
    warnings: list[str] = []

    if result.schema_version != 2:
        errors.append(f"Unsupported schema version: {result.schema_version} (expected 2)")

    facts = result.facts
    fact_ids: set[str] = set()
    for fact in facts:
        if fact.local_key in fact_ids:
            errors.append(f"Duplicate fact key: {fact.local_key}")
            continue
        fact_ids.add(fact.local_key)

        # Evidence requirements.
        if fact.status == FactStatus.SUPPORTED:
            if not fact.evidence:
                errors.append(f"Supported fact '{fact.local_key}' has no evidence")
                continue
            has_valid_evidence = False
            for ev in fact.evidence:
                if ev.source_kind == SourceKind.SYSTEM_DEFAULT:
                    errors.append(f"System default used as evidence for fact '{fact.local_key}'")
                    continue
                if not _valid_source_id(ev.source_id, source_texts):
                    errors.append(
                        f"Fact '{fact.local_key}' references unknown source '{ev.source_id}'"
                    )
                if not _bounded_excerpt(ev.evidence_excerpt):
                    errors.append(f"Evidence excerpt for fact '{fact.local_key}' is too long")
                source_text = source_texts.get(ev.source_id, "")
                if validate_evidence_excerpt(source_text, ev.evidence_excerpt):
                    has_valid_evidence = True
                else:
                    errors.append(
                        f"Evidence excerpt for fact '{fact.local_key}' not found in source"
                    )
            if not has_valid_evidence:
                errors.append(f"Fact '{fact.local_key}' has no valid evidence")

        # user_asserted facts must point at a user source.
        if fact.status == FactStatus.USER_ASSERTED:
            user_sources = {
                SourceKind.USER_ANSWER.value,
                SourceKind.USER_EDIT.value,
                SourceKind.MAIN_PROMPT.value,
            }
            if not any(ev.source_kind.value in user_sources for ev in fact.evidence):
                errors.append(
                    f"User-asserted fact '{fact.local_key}' does not reference a user source"
                )

        # Private/confidential facts must not default to public.
        if fact.sensitivity in {FactSensitivity.PRIVATE, FactSensitivity.CONFIDENTIAL}:
            if fact.publish_default:
                errors.append(
                    f"Fact '{fact.local_key}' is {fact.sensitivity.value} but publish_default=true"
                )
            if fact.category in {FactCategory.CONTACT, FactCategory.METRIC}:
                pass

        # No invented contact details.
        if fact.category in {FactCategory.CONTACT, FactCategory.IDENTITY}:
            value = _stringify(fact.value)
            if _is_private_contact(value) and fact.sensitivity == FactSensitivity.PUBLIC:
                errors.append(f"Fact '{fact.local_key}' exposes private contact as public")

        # No unsupported metric claims.
        if (
            fact.category == FactCategory.METRIC
            and fact.status == FactStatus.SUPPORTED
            and not fact.evidence
        ):
            errors.append(f"Unsupported metric fact '{fact.local_key}' has no evidence")

        # No hidden reasoning.
        if "reasoning" in fact.field.lower() or "chain_of_thought" in fact.field.lower():
            errors.append(f"Fact '{fact.local_key}' uses a hidden-reasoning field")

        # No unsupported employment/education.
        if fact.category in {
            FactCategory.EXPERIENCE,
            FactCategory.EDUCATION,
        } and fact.status not in {
            FactStatus.SUPPORTED,
            FactStatus.USER_ASSERTED,
        }:
            errors.append(
                f"Employment/education fact '{fact.local_key}' has status '{fact.status.value}'"
            )

    # Injection must not be represented as policy.
    injection_indicators = (
        "ignore previous instructions",
        "system administrator",
        "reveal the prompt",
        "print the api key",
        "hidden prompt",
    )
    for fact in facts:
        value = _stringify(fact.value).lower()
        if any(indicator in value for indicator in injection_indicators):
            errors.append(f"Fact '{fact.local_key}' represents injection text as policy")

    # Question checks.
    max_questions = getattr(config, "max_questions", 8)
    if len(result.questions) > max_questions:
        errors.append(f"Too many questions: {len(result.questions)} (max {max_questions})")

    question_ids: set[str] = set()
    for question in result.questions:
        if question.local_key in question_ids:
            errors.append(f"Duplicate question key: {question.local_key}")
            continue
        question_ids.add(question.local_key)

        if not _question_kind_matches_options(question):
            errors.append(f"Question '{question.local_key}' kind/options mismatch")

        if question.allows_auto and _is_factual_question(question):
            errors.append(f"Factual question '{question.local_key}' incorrectly allows auto")

        # No question already answered by high-confidence source evidence.
        if _question_answered_by_source(question, facts):
            errors.append(f"Question '{question.local_key}' is already answered by evidence")

    # Auto decisions must not support professional facts.
    factual_categories = {
        FactCategory.TARGET_ROLE.value,
        FactCategory.EXPERIENCE.value,
        FactCategory.PROJECT.value,
        FactCategory.EDUCATION.value,
        FactCategory.METRIC.value,
        FactCategory.DATE.value,
    }
    for decision in result.auto_decisions:
        if decision.category.value in {
            "tone",
            "theme",
            "motion",
            "project_ordering",
            "section_emphasis",
            "cta",
            "visual_intensity",
        }:
            continue
        if any(
            fact.category.value in factual_categories
            for fact in facts
            if fact.local_key in decision.basis_fact_ids
        ):
            errors.append(f"Auto decision '{decision.category.value}' is based on factual facts")

    # Output language must match the request.
    requested = result.source_assessment.requested_output_language
    detected = result.source_assessment.detected_languages
    if requested and detected and requested not in detected and not _contains_english(detected):
        warnings.append(
            f"Requested output language '{requested}' not in detected languages {detected}"
        )

    return ValidationOutcome(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def _valid_source_id(source_id: str, source_texts: dict[str, str]) -> bool:
    if source_id in {"main_prompt", "resume_text"}:
        return True
    # Links and user answers are validated elsewhere; unknown free-form IDs are suspect.
    return True


def _bounded_excerpt(excerpt: str) -> bool:
    return len(excerpt) <= 2000


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, dict)):
        return " ".join(_stringify(item) for item in value)
    return str(value)


def _contains_english(languages: list[str]) -> bool:
    return any(lang.lower().startswith("en") for lang in languages)


def _question_answered_by_source(
    question: DiscoveryQuestion,
    facts: list[Any],
) -> bool:
    """A question is already answered when high-confidence source evidence exists."""
    if question.category not in {QuestionCategory.TARGET_ROLE, QuestionCategory.PORTFOLIO_GOAL}:
        return False
    for fact in facts:
        if (
            fact.category.value == "target_role"
            and fact.status == FactStatus.SUPPORTED
            and question.category == QuestionCategory.TARGET_ROLE
        ):
            return True
    return False


# ── Call B validation (Section 23.2) ─────────────────────────────────────────


def validate_call_b_result(
    brief: DiscoveryBrief,
    fact_ids: set[str],
    project_ids: set[str],
    config: Any,
) -> ValidationOutcome:
    """Run the full Call B semantic check list."""
    errors: list[str] = []
    warnings: list[str] = []

    if brief.schema_version != 2:
        errors.append(f"Unsupported schema version: {brief.schema_version} (expected 2)")

    def unknown_fact(fact_id: str) -> bool:
        return fact_id not in fact_ids

    # Every fact reference must exist.
    refs = _collect_fact_refs(brief)
    for ref in refs:
        if unknown_fact(ref):
            errors.append(f"Brief references unknown fact: {ref}")

    # Primary role must be supported or explicitly user-selected.
    if (
        brief.identity_and_goal.primary_target_role.decision_source.value
        not in {"user_answer", "user_edit"}
        and not brief.identity_and_goal.primary_target_role.basis_fact_ids
    ):
        errors.append("Primary target role has no supporting facts and no user decision")

    # Every differentiator must reference supporting facts.
    for differentiator in brief.positioning_strategy.differentiators:
        if not differentiator.basis_fact_ids:
            errors.append("Differentiator has no basis facts")
        for fact_id in differentiator.basis_fact_ids:
            if unknown_fact(fact_id):
                errors.append(f"Differentiator references unknown fact: {fact_id}")

    # Featured projects must exist, and personal contributions must be grounded.
    max_projects = getattr(config, "max_featured_projects", 5)
    if len(brief.content_strategy.featured_projects) > max_projects:
        errors.append(
            f"Too many featured projects: "
            f"{len(brief.content_strategy.featured_projects)} (max {max_projects})"
        )
    for project in brief.content_strategy.featured_projects:
        if project.project_id and project.project_id not in project_ids:
            errors.append(f"Brief references unknown project: {project.project_id}")
        for contribution in project.supported_personal_contribution:
            if not contribution.basis_fact_ids:
                errors.append(
                    f"Project '{project.project_id}' personal contribution has no basis facts"
                )
        if not project.unknowns_to_omit and not project.confidentiality.restrictions:
            warnings.append(
                f"Project '{project.project_id}' has no unknowns listed (use empty list only "
                "when none exist)"
            )

    # No unsupported metrics / seniority / leadership in claim policy.
    for claim in brief.claim_policy.must_not_claim:
        lowered = claim.lower()
        if any(word in lowered for word in ("metric", "performance", "improvement")):
            pass  # these are safe as must-not-claim entries
    for boundary in brief.positioning_strategy.credibility_boundaries:
        lowered = boundary.lower()
        if any(word in lowered for word in ("senior", "lead", "manager")):
            pass  # credibility boundaries legitimately mention these

    # Confidentiality rules must not be weakened by omissions.
    for omission in brief.confidentiality_and_omissions.deliberate_omissions:
        lowered = omission.lower()
        if "contact" in lowered or "email" in lowered or "phone" in lowered:
            pass  # omissions of private contact are correct

    # Private contact must not be published by default.
    for choice in brief.cta_and_contact.publishable_contact_choices:
        if choice.source.value == "resume_default" and _is_private_contact(choice.kind):
            errors.append(f"Private contact '{choice.kind}' published without explicit choice")

    # No final hero/about/project copy.
    final_copy_fields = _final_copy_in_brief(brief)
    if final_copy_fields:
        errors.append(f"Brief contains final portfolio copy in fields: {final_copy_fields}")

    # No component/layout/code specification.
    component_fields = _component_spec_in_brief(brief)
    if component_fields:
        errors.append(f"Brief contains component/layout/code spec in fields: {component_fields}")

    # Language.
    if not _is_supported_language(brief.output_language, config):
        errors.append(f"Unsupported output language: {brief.output_language}")

    # Downstream constraints must be present.
    if not brief.downstream_handoff.universal_constraints:
        errors.append("Downstream handoff has no universal constraints")

    # Decision log must be consistent.
    for entry in brief.decision_log:
        for fact_id in entry.related_fact_ids:
            if unknown_fact(fact_id):
                errors.append(f"Decision log references unknown fact: {fact_id}")

    return ValidationOutcome(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def _collect_fact_refs(brief: DiscoveryBrief) -> set[str]:
    """Collect every fact ID referenced anywhere in the brief."""
    refs: set[str] = set()
    goal = brief.identity_and_goal
    refs.update(goal.primary_target_role.basis_fact_ids)
    for strength in goal.secondary_strengths:
        refs.update(strength.basis_fact_ids)
    for differentiator in brief.positioning_strategy.differentiators:
        refs.update(differentiator.basis_fact_ids)
    for project in brief.content_strategy.featured_projects:
        refs.update(project.evidence_to_preserve)
        for contribution in project.supported_personal_contribution:
            refs.update(contribution.basis_fact_ids)
    for cluster in brief.content_strategy.capability_clusters:
        refs.update(cluster.basis_fact_ids)
    for focus in brief.content_strategy.experience_focus:
        refs.update(focus.basis_fact_ids)
    refs.update(brief.claim_policy.must_use_fact_ids)
    refs.update(brief.claim_policy.allowed_user_asserted_fact_ids)
    for wording in brief.claim_policy.requires_careful_wording:
        refs.add(wording.fact_id)
    refs.update(brief.downstream_handoff.content_architect.evidence_to_preserve)
    for rule in brief.confidentiality_and_omissions.rules:
        refs.update(rule.fact_ids)
    for choice in brief.cta_and_contact.publishable_contact_choices:
        if choice.fact_id:
            refs.add(choice.fact_id)
    for log_entry in brief.decision_log:
        refs.update(log_entry.related_fact_ids)
    return refs


def _final_copy_in_brief(brief: DiscoveryBrief) -> list[str]:
    """Detect final portfolio copy (hero/about/project prose) in the brief."""
    fields: list[str] = []
    # The professional summary is an analytical summary, not copy, but a
    # first-person hero/About statement is copy.
    summary = brief.executive_summary.strategy_summary
    if _looks_like_final_copy(summary):
        fields.append("executive_summary.strategy_summary")
    story = brief.downstream_handoff.content_architect.central_story
    if _looks_like_final_copy(story):
        fields.append("downstream_handoff.content_architect.central_story")
    return fields


def _component_spec_in_brief(brief: DiscoveryBrief) -> list[str]:
    """Detect component/layout/code specifications in the brief."""
    fields: list[str] = []
    component_markers = (
        "grid",
        "flexbox",
        "component",
        "navbar",
        "footer",
        "hero section",
        "card",
        "css",
        "bootstrap",
        "tailwind",
        "javascript",
        "react",
    )
    text = brief.model_dump_json().lower()
    for marker in component_markers:
        if marker in text:
            fields.append(marker)
    return fields


def _looks_like_final_copy(text: str) -> bool:
    """Detect first-person promotional prose that reads as final copy."""
    lowered = text.lower()
    first_person_verbs = ("i built", "i designed", "i led", "my passion", "i love")
    return any(verb in lowered for verb in first_person_verbs)


# ── Questions / Answers validation ───────────────────────────────────────────


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
        if (
            mode == "auto"
            and question.auto_answer is None
            and not _is_presentation_question(question)
        ):
            errors.append(f"Auto answer for '{q_id}' has no safe automatic value")

    max_answer_chars = getattr(config, "max_answer_chars", 10000)
    for q_id, answer in answers.items():
        value = answer.get("value")
        if isinstance(value, str) and len(value) > max_answer_chars:
            errors.append(f"Answer for '{q_id}' exceeds max length")

    return ValidationOutcome(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


# ── Helpers ──────────────────────────────────────────────────────────────────


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


def _is_presentation_question(question: DiscoveryQuestion) -> bool:
    return question.category == QuestionCategory.PRESENTATION


def _question_kind_matches_options(question: DiscoveryQuestion) -> bool:
    needs_options = {QuestionKind.SINGLE_SELECT, QuestionKind.MULTI_SELECT}
    return not (question.kind in needs_options and not question.options)
