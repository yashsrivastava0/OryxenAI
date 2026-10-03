"""The model may return useful content with imperfect envelope details."""

from __future__ import annotations

from oryxenai.agents.discovery.normalize import normalize_brief, normalize_questions


def test_questions_repair_mode_options_and_duplicates() -> None:
    output, errors = normalize_questions(
        {
            "mode": "unexpected",
            "questions": [
                {
                    "id": "same",
                    "text": "Which audience?",
                    "kind": "radio",
                    "options": ["Hiring teams", "Clients", "Collaborators"],
                },
                {
                    "id": "same",
                    "text": "What work should lead?",
                    "kind": "text",
                    "options": ["Projects", "Experience", "Research"],
                },
                {"text": "Should we use your latest role?", "kind": "yes_no"},
                {"text": "Extra question"},
            ],
        }
    )
    assert errors == []
    assert output is not None
    assert output["mode"] == "ASK_QUESTIONS"
    assert len(output["questions"]) == 2
    assert all(question["kind"] == "single_select" for question in output["questions"])
    assert all(len(question["options"]) == 3 for question in output["questions"])
    assert len({question["id"] for question in output["questions"]}) == 2


def test_malformed_question_batch_requests_recovery_but_closed_gaps_do_not() -> None:
    candidate = {
        "text": "Which missing project should lead?",
        "kind": "single_select",
        "options": ["Only one choice"],
    }
    payload = {"mode": "ASK_QUESTIONS", "questions": [candidate]}

    output, errors = normalize_questions(payload)
    assert output is None
    assert errors == ["Model proposed questions without three distinct, usable choices"]

    from oryxenai.agents.discovery.normalize import gap_id_for

    output, errors = normalize_questions(payload, closed_gap_ids={gap_id_for(candidate["text"])})
    assert errors == []
    assert output is not None
    assert output["mode"] == "READY_FOR_BRIEF"


def test_brief_repairs_dossier_without_losing_claims() -> None:
    output, errors = normalize_brief(
        {
            "brief_markdown": "# My work\n\nI built a useful tool.",
            "dossier": {
                "facts": [
                    {"id": "f1", "statement": "Built a useful tool", "ownership": "self"},
                    {"id": "f1", "statement": "It served a team", "ownership": "nonsense"},
                ],
                "projects": [{"name": "Useful tool", "fact_ids": ["f1", "missing"]}],
            },
        },
        documents=[],
        question_events=[],
    )
    assert errors == []
    assert output is not None
    dossier = output["dossier"]
    assert output["brief_title"] == "My work"
    assert len({fact.id for fact in dossier.facts}) == 2
    assert dossier.facts[0].ownership.value == "individual"
    assert dossier.facts[1].ownership.value == "unknown"
    assert dossier.projects[0].fact_ids == ["f1"]
    assert dossier.source_coverage == []


def test_brief_requires_markdown() -> None:
    output, errors = normalize_brief({"dossier": {}}, documents=[], question_events=[])
    assert output is None
    assert errors == ["'brief_markdown' is empty"]
