"""Build the full DiscoveryDossier/v1 from the model's compact draft.

The model writes a small, lenient draft (``DossierDraft``). The server owns
everything it cannot get wrong: ids, cross-links, enum values, the question
history, provenance metadata, and the compatibility profile. Content Architect
only needs an ``id`` on every fact, role, project and evidence item, plus the
fields its prompts read, so repairs here never change what the user said.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from oryxenai.agents.discovery.schemas import (
    DiscoveryDossier,
    EducationEntry,
    ExperienceEntry,
    ProjectEntry,
    QuestionHistoryEvent,
    SourceDocument,
    StructuredProfile,
)

_INDIVIDUAL = {"individual", "personal", "self", "me", "own", "solo", "owner", "lead"}
_TEAM = {"team", "shared", "group", "org", "organization", "organisation", "company", "joint"}
_DISPOSITIONS = {"omit", "generalize", "restricted"}
_SKILL_CATEGORIES = {"skill", "skills", "tool", "tools", "technology", "technologies", "tech_stack"}
_LANGUAGE_CATEGORIES = {"language", "languages", "spoken_language", "spoken_languages"}
_PRIVATE_DISPOSITIONS = {"omit", "generalize", "restricted"}


def as_text(value: Any) -> str:
    """Coerce a scalar, list, or mapping into a trimmed string; never raises."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        return ""
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, list | tuple):
        return "; ".join(part for part in (as_text(item) for item in value) if part)
    if isinstance(value, dict):
        for key in ("text", "statement", "detail", "name", "title", "label", "value"):
            text = as_text(value.get(key))
            if text:
                return text
    return ""


def as_text_list(value: Any) -> list[str]:
    """Coerce to a de-duplicated list of non-empty strings, preserving order."""
    if value is None:
        return []
    items = value if isinstance(value, list | tuple) else [value]
    seen: dict[str, None] = {}
    for item in items:
        text = as_text(item)
        if text:
            seen.setdefault(text, None)
    return list(seen)


def _unique_id(preferred: Any, prefix: str, used: set[str]) -> str:
    candidate = as_text(preferred)[:64]
    if candidate and candidate not in used:
        used.add(candidate)
        return candidate
    number = len(used) + 1
    while f"{prefix}{number}" in used:
        number += 1
    generated = f"{prefix}{number}"
    used.add(generated)
    return generated


def _ownership(value: Any) -> str:
    text = as_text(value).casefold()
    if text in _INDIVIDUAL:
        return "individual"
    if text in _TEAM:
        return "team"
    return "unknown"


def _links(value: Any) -> list[dict[str, str]]:
    items = value if isinstance(value, list | tuple) else ([value] if value else [])
    links: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        if isinstance(item, dict):
            url = as_text(item.get("url") or item.get("href") or item.get("link"))
            label = as_text(item.get("label") or item.get("name") or item.get("title"))
        else:
            url = as_text(item)
            label = ""
        if url and url not in seen:
            seen.add(url)
            links.append({"label": label, "url": url})
    return links


def _entries(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _fact_ids(value: Any, known: set[str]) -> list[str]:
    return [fact_id for fact_id in as_text_list(value) if fact_id in known]


def build_dossier(
    raw: Any,
    *,
    open_items: list[str],
    goal_text: str,
    documents: list[SourceDocument],
    question_events: list[QuestionHistoryEvent],
) -> DiscoveryDossier:
    """Return a valid DiscoveryDossier/v1, repairing whatever the model got loose."""

    draft: dict[str, Any] = raw if isinstance(raw, dict) else {}
    raw_intent = draft.get("intent")
    raw_subject = draft.get("subject")
    intent_raw: dict[str, Any] = raw_intent if isinstance(raw_intent, dict) else {}
    subject_raw: dict[str, Any] = raw_subject if isinstance(raw_subject, dict) else {}

    fact_ids: set[str] = set()
    facts: list[dict[str, Any]] = []
    for item in _entries(draft.get("facts")):
        statement = as_text(item.get("statement") or item.get("text") or item.get("claim"))
        if not statement:
            continue
        facts.append(
            {
                "id": _unique_id(item.get("id"), "f", fact_ids),
                "category": as_text(item.get("category")),
                "statement": statement,
                "qualifiers": as_text_list(item.get("qualifiers")),
                "ownership": _ownership(item.get("ownership")),
                "status": "source_asserted",
            }
        )

    role_ids: set[str] = set()
    roles = [
        {
            "id": _unique_id(item.get("id"), "r", role_ids),
            "organization": as_text(item.get("organization") or item.get("company")),
            "role": as_text(item.get("role") or item.get("title")),
            "dates": as_text(item.get("dates")),
            "details": as_text_list(item.get("details")),
            "fact_ids": _fact_ids(item.get("fact_ids"), fact_ids),
        }
        for item in _entries(draft.get("roles"))
        if as_text(item.get("organization") or item.get("company") or item.get("role"))
    ]

    project_ids: set[str] = set()
    projects = [
        {
            "id": _unique_id(item.get("id"), "p", project_ids),
            "name": as_text(item.get("name") or item.get("title")),
            "problem": as_text(
                item.get("problem") or item.get("summary") or item.get("description")
            ),
            "personal_contribution": as_text(item.get("personal_contribution")),
            "team_contribution": as_text(item.get("team_contribution")),
            "approach": as_text_list(item.get("approach")),
            "tools": as_text_list(item.get("tools")),
            "outcomes": as_text_list(item.get("outcomes")),
            "links": as_text_list(item.get("links")),
            "fact_ids": _fact_ids(item.get("fact_ids"), fact_ids),
        }
        for item in _entries(draft.get("projects"))
        if as_text(item.get("name") or item.get("title"))
    ]

    evidence_ids: set[str] = set()
    evidence = [
        {
            "id": _unique_id(item.get("id"), "e", evidence_ids),
            "category": as_text(item.get("category")),
            "title": as_text(item.get("title") or item.get("name")),
            "detail": as_text(item.get("detail") or item.get("description")),
            "fact_ids": _fact_ids(item.get("fact_ids"), fact_ids),
        }
        for item in _entries(draft.get("other_evidence"))
        if as_text(item.get("title") or item.get("name") or item.get("detail"))
    ]

    restriction_ids: set[str] = set()
    restrictions = []
    for item in _entries(draft.get("restrictions")):
        instruction = as_text(item.get("instruction") or item.get("text"))
        if not instruction:
            continue
        disposition = as_text(item.get("disposition")).casefold()
        if disposition not in _DISPOSITIONS:
            disposition = "generalize" if "general" in disposition else "omit"
        restrictions.append(
            {
                "id": _unique_id(item.get("id"), "x", restriction_ids),
                "scope": as_text(item.get("scope")),
                "instruction": instruction,
                "disposition": disposition,
            }
        )

    payload: dict[str, Any] = {
        "contract_version": "DiscoveryDossier/v1",
        "intent": {
            "goal": as_text(intent_raw.get("goal")) or goal_text.strip(),
            "audience": as_text(intent_raw.get("audience")),
            "visitor_action": as_text(intent_raw.get("visitor_action")),
            "language": as_text(intent_raw.get("language")),
            "preferences": as_text_list(intent_raw.get("preferences")),
        },
        "subject": {
            "name": as_text(subject_raw.get("name")),
            "current_title": as_text(subject_raw.get("current_title") or subject_raw.get("title")),
            "location": as_text(subject_raw.get("location")),
            "links": _links(subject_raw.get("links")),
        },
        "facts": facts,
        "roles": roles,
        "projects": projects,
        "other_evidence": evidence,
        "open_items": [
            {
                "id": f"open_{index}",
                "detail": detail,
                "importance": "context",
                "status": "open",
            }
            for index, detail in enumerate(open_items, start=1)
        ],
        "user_choices": [
            f"{event.question} — {event.answer}"
            for event in question_events
            if event.status == "answered" and event.answer.strip()
        ],
        "restrictions": restrictions,
        "source_coverage": [],
        "question_events": [event.model_dump(mode="json") for event in question_events],
    }
    payload["id"] = f"dossier_{uuid4().hex}"
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload["lineage"] = {
        "version": 1,
        "schema_version": "DiscoveryDossier/v1",
        "provenance_status": "brief_derived" if documents else "unverified_legacy",
        "source_document_ids": [document.id for document in documents],
        "source_hashes": [document.sha256 for document in documents],
        "created_at": datetime.now(UTC).isoformat(),
        "payload_hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }
    return DiscoveryDossier.model_validate(payload)


def profile_from_dossier(dossier: DiscoveryDossier) -> StructuredProfile:
    """Project dossier facts into the compact profile Content Architect keeps as a guide."""

    facts_by_id = {fact.id: fact for fact in dossier.facts}
    experience = [
        ExperienceEntry(
            organization=role.organization,
            role=role.role,
            dates=role.dates,
            highlights=[
                _qualified_fact(facts_by_id[fact_id])
                for fact_id in role.fact_ids
                if fact_id in facts_by_id
            ]
            or role.details,
        )
        for role in dossier.roles
    ]
    projects = [
        ProjectEntry(
            name=project.name,
            summary=project.problem,
            contribution=project.personal_contribution,
            tech=project.tools,
            link=project.links[0] if project.links else "",
        )
        for project in dossier.projects
    ]
    education: list[EducationEntry] = []
    skills: list[str] = []
    languages: list[str] = []
    for item in dossier.other_evidence:
        category = item.category.casefold().replace(" ", "_")
        if category in {"education", "certification", "certifications"}:
            education.append(
                EducationEntry(
                    institution=item.title if category == "education" else "",
                    credential=item.detail or item.title,
                )
            )
        elif category in _SKILL_CATEGORIES:
            skills.extend(_listed_values(item.detail or item.title))
        elif category in _LANGUAGE_CATEGORIES:
            languages.extend(_listed_values(item.detail or item.title))
    private_omitted = [
        restriction.instruction
        for restriction in dossier.restrictions
        if restriction.disposition.casefold() in _PRIVATE_DISPOSITIONS and restriction.instruction
    ]
    return StructuredProfile(
        name=dossier.subject.name,
        current_title=dossier.subject.current_title,
        location=dossier.subject.location,
        links=dossier.subject.links,
        experience=experience,
        education=education,
        projects=projects,
        skills=list(dict.fromkeys(skills)),
        spoken_languages=list(dict.fromkeys(languages)),
        private_omitted=private_omitted,
    )


def _listed_values(text: str) -> list[str]:
    """Split a grouped evidence entry ('Go, Python; SQL') into individual items."""
    return [part.strip() for part in re.split(r"[,;\n]", text) if part.strip()]


def _qualified_fact(fact: Any) -> str:
    statement = str(fact.statement)
    if fact.ownership.value == "team":
        return f"Team contribution: {statement}"
    if fact.ownership.value == "unknown":
        return f"Attribution not specified: {statement}"
    return statement
