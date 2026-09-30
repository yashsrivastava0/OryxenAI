"""Deterministic validators for model-produced Discovery contracts."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from oryxenai.agents.discovery.schemas import (
    DiscoveryDossier,
    DossierEvidence,
    DossierProject,
    DossierRole,
    OperationMode,
    QuestionKind,
    SourceDocument,
    StructuredProfile,
)

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


def validate_questions_output(
    data: dict[str, Any],
    max_questions: int = 3,
    *,
    closed_gap_ids: set[str] | None = None,
) -> ValidationOutcome:
    """Check a question round: at most three focused questions, no repeats."""

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
    closed_gaps = closed_gap_ids or set()
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
        gap_id = str(question.get("gap_id", "") or "").strip()
        if gap_id and gap_id in closed_gaps:
            errors.append(f"Question {index} repeats a resolved gap: {gap_id}")
        kind = question.get("kind", "text")
        if kind not in _VALID_QUESTION_KINDS:
            errors.append(f"Question {index} has invalid kind: {kind}")
        elif kind in {"single_select", "multi_select"}:
            options = question.get("options")
            if not isinstance(options, list) or not options:
                errors.append(f"Question {index} ({kind}) has no options")
            else:
                seen_option_ids: set[str] = set()
                seen_option_labels: set[str] = set()
                for option in options:
                    if not isinstance(option, dict):
                        errors.append(f"Question {index} has an invalid option")
                        continue
                    option_id = str(option.get("id", "") or "").strip()
                    option_label = str(option.get("label", "") or "").strip()
                    if not option_id:
                        errors.append(f"Question {index} has an option without an id")
                    elif option_id in seen_option_ids:
                        errors.append(f"Question {index} has a duplicate option id: {option_id}")
                    else:
                        seen_option_ids.add(option_id)
                    if not option_label:
                        errors.append(f"Question {index} has an option without a label")
                    elif option_label.casefold() in seen_option_labels:
                        errors.append(f"Question {index} has a duplicate option label")
                    else:
                        seen_option_labels.add(option_label.casefold())

    if mode == OperationMode.NEEDS_DETAILS.value and questions:
        errors.append("NEEDS_DETAILS must have an empty questions list")
    if mode == OperationMode.ASK_QUESTIONS.value and not questions:
        errors.append("ASK_QUESTIONS must have at least one question")
    if mode == OperationMode.READY_FOR_BRIEF.value and questions:
        errors.append("READY_FOR_BRIEF must have an empty questions list")
    if not str(data.get("assistant_message", "") or "").strip():
        errors.append("'assistant_message' is empty")
    return ValidationOutcome(not errors, errors)


def validate_brief_output(
    data: dict[str, Any],
    source_documents: list[SourceDocument] | None = None,
) -> ValidationOutcome:
    """Check the brief envelope and completeness of its evidence dossier."""

    errors: list[str] = []
    if data.get("mode") != OperationMode.BRIEF_READY.value:
        errors.append(f"'mode' must be BRIEF_READY; got {data.get('mode')!r}")
    for key in ("assistant_message", "brief_title", "brief_markdown", "user_summary"):
        if not str(data.get(key, "") or "").strip():
            errors.append(f"'{key}' is empty")
    if not isinstance(data.get("open_items", []), list):
        errors.append("'open_items' must be a list when present")
    if not isinstance(data.get("memory_update", {}), dict):
        errors.append("'memory_update' must be a dict when present")

    profile = data.get("profile")
    if profile is not None:
        try:
            if not isinstance(profile, dict):
                errors.append("'profile' must be an object when present")
            else:
                StructuredProfile.model_validate(profile)
        except ValidationError as exc:
            errors.append(f"'profile' failed schema validation: {exc.error_count()} error(s)")

    raw_dossier = data.get("dossier")
    if not isinstance(raw_dossier, dict):
        errors.append("'dossier' must be a DiscoveryDossier/v1 object")
        return ValidationOutcome(False, errors)
    try:
        dossier = DiscoveryDossier.model_validate(raw_dossier)
    except ValidationError as exc:
        errors.append(f"'dossier' failed schema validation: {exc.error_count()} error(s)")
        return ValidationOutcome(False, errors)

    if dossier.contract_version != "DiscoveryDossier/v1":
        errors.append("'dossier.contract_version' must be DiscoveryDossier/v1")
    fact_ids = [fact.id for fact in dossier.facts]
    if any(not fact_id for fact_id in fact_ids):
        errors.append("Every dossier fact requires an id")
    if len(set(fact_ids)) != len(fact_ids):
        errors.append("Dossier fact ids must be unique")
    known_facts = set(fact_ids)
    facts_by_id = {fact.id: fact for fact in dossier.facts}
    has_indexed_sources = bool(
        source_documents and any(document.spans for document in source_documents)
    )
    for label, entities in (
        ("role", dossier.roles),
        ("project", dossier.projects),
        ("evidence", dossier.other_evidence),
        ("open item", dossier.open_items),
        ("restriction", dossier.restrictions),
    ):
        entity_ids = [item.id for item in entities]
        if any(not entity_id for entity_id in entity_ids):
            errors.append(f"Every dossier {label} requires an id")
        if len(set(entity_ids)) != len(entity_ids):
            errors.append(f"Dossier {label} ids must be unique")
    for fact in dossier.facts:
        if not fact.source_refs and source_documents and any(doc.spans for doc in source_documents):
            errors.append(f"Fact {fact.id!r} has no source references")
    linked_entities: list[DossierRole | DossierProject | DossierEvidence] = [
        *dossier.roles,
        *dossier.projects,
        *dossier.other_evidence,
    ]
    for entity in linked_entities:
        if set(entity.fact_ids) - known_facts:
            errors.append(f"Entity {entity.id!r} references unknown facts")
        if has_indexed_sources and not entity.fact_ids:
            errors.append(f"Entity {entity.id!r} does not link to a source-backed fact")
        linked_fact_refs = {
            source_ref
            for fact_id in entity.fact_ids
            if fact_id in facts_by_id
            for source_ref in facts_by_id[fact_id].source_refs
        }
        if linked_fact_refs - set(entity.source_refs):
            errors.append(f"Entity {entity.id!r} omits a linked fact's source references")
        if (
            not entity.source_refs
            and source_documents
            and any(doc.spans for doc in source_documents)
        ):
            errors.append(f"Entity {entity.id!r} has no source references")
        if isinstance(entity, DossierProject):
            linked_facts = [
                facts_by_id[fact_id] for fact_id in entity.fact_ids if fact_id in facts_by_id
            ]
            if entity.personal_contribution and not any(
                fact.ownership.value == "individual" for fact in linked_facts
            ):
                errors.append(
                    f"Project {entity.id!r} claims personal contribution without individual evidence"
                )
            if entity.team_contribution and not any(
                fact.ownership.value == "team" for fact in linked_facts
            ):
                errors.append(
                    f"Project {entity.id!r} claims team contribution without team evidence"
                )
    if (
        any((dossier.subject.name, dossier.subject.current_title, dossier.subject.location))
        and not dossier.subject.source_refs
        and source_documents
        and any(doc.spans for doc in source_documents)
    ):
        errors.append("Dossier subject has no source references")

    expected_spans: set[str] | None = None
    expected_documents: set[str] | None = None
    expected_hashes: set[str] | None = None
    if source_documents is not None:
        expected_spans = {span.id for doc in source_documents for span in doc.spans}
        expected_documents = {doc.id for doc in source_documents}
        expected_hashes = {doc.sha256 for doc in source_documents}
    coverage_ids = [item.span_id for item in dossier.source_coverage]
    coverage_by_span = {item.span_id: item for item in dossier.source_coverage}
    if len(set(coverage_ids)) != len(coverage_ids):
        errors.append("Dossier source_coverage contains duplicate span ids")
    if expected_spans is not None and set(coverage_ids) != expected_spans:
        missing = expected_spans - set(coverage_ids)
        unknown = set(coverage_ids) - expected_spans
        if missing:
            errors.append(f"Dossier source_coverage is missing {len(missing)} source span(s)")
        if unknown:
            errors.append(f"Dossier source_coverage contains {len(unknown)} unknown span(s)")
    for coverage in dossier.source_coverage:
        if set(coverage.fact_ids) - known_facts:
            errors.append(f"Source span {coverage.span_id!r} references unknown facts")
        if coverage.disposition.value == "fact" and not coverage.fact_ids:
            errors.append(f"Source span {coverage.span_id!r} is a fact but links to no facts")
        for fact_id in coverage.fact_ids:
            linked_fact = facts_by_id.get(fact_id)
            if linked_fact is not None and coverage.span_id not in linked_fact.source_refs:
                errors.append(
                    f"Source span {coverage.span_id!r} is not cited by linked fact {fact_id!r}"
                )
        if coverage.disposition.value in {"duplicate", "excluded"} and not coverage.reason.strip():
            errors.append(f"Source span {coverage.span_id!r} needs a disposition reason")

    intent_refs = {
        source_ref for references in dossier.intent.basis_refs.values() for source_ref in references
    }
    restriction_refs = {
        source_ref for restriction in dossier.restrictions for source_ref in restriction.source_refs
    }
    for coverage in dossier.source_coverage:
        if coverage.disposition.value == "fact":
            for fact in dossier.facts:
                if coverage.span_id in fact.source_refs and fact.id not in coverage.fact_ids:
                    errors.append(f"Source span {coverage.span_id!r} omits a fact that cites it")
        elif (
            coverage.disposition.value == "intent_preference"
            and coverage.span_id not in intent_refs
        ):
            errors.append(f"Intent span {coverage.span_id!r} has no intent basis reference")
        elif (
            coverage.disposition.value == "restriction" and coverage.span_id not in restriction_refs
        ):
            errors.append(f"Restriction span {coverage.span_id!r} has no restriction record")
    for fact in dossier.facts:
        for source_ref in fact.source_refs:
            matching_coverage = coverage_by_span.get(source_ref)
            if matching_coverage is not None and (
                matching_coverage.disposition.value != "fact"
                or fact.id not in matching_coverage.fact_ids
            ):
                errors.append(f"Fact {fact.id!r} is not linked from its source coverage record")

    source_refs: set[str] = set(dossier.subject.source_refs)
    for references in dossier.intent.basis_refs.values():
        source_refs.update(references)
    for fact in dossier.facts:
        source_refs.update(fact.source_refs)
    for entity in linked_entities:
        source_refs.update(entity.source_refs)
    for item in dossier.open_items:
        source_refs.update(item.source_refs)
    for restriction in dossier.restrictions:
        source_refs.update(restriction.source_refs)
    for event in dossier.question_events:
        source_refs.update(event.answer_source_refs)
        for revision in event.answer_history:
            source_refs.update(revision.source_refs)
    if expected_spans is not None and source_refs - expected_spans:
        errors.append("Dossier contains unknown source references")
    if (
        expected_documents is not None
        and set(dossier.lineage.source_document_ids) != expected_documents
    ):
        errors.append("Dossier lineage does not identify every supplied source document")
    if expected_hashes is not None and set(dossier.lineage.source_hashes) != expected_hashes:
        errors.append("Dossier lineage hashes do not match every supplied source document")
    if any(not event.question_id for event in dossier.question_events):
        errors.append("Dossier question history contains an event without a question id")

    return ValidationOutcome(not errors, errors)
