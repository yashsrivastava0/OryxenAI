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
                    "options": ["Hiring teams"],
                },
                {"id": "same", "text": "What work should lead?", "kind": "text"},
                {"text": "Should we use your latest role?", "kind": "yes_no"},
                {"text": "Extra question"},
            ],
        }
    )
    assert errors == []
    assert output is not None
    assert output["mode"] == "ASK_QUESTIONS"
    assert len(output["questions"]) == 3
    assert output["questions"][0]["kind"] == "text"
    assert output["questions"][0]["options"] == []
    assert len({question["id"] for question in output["questions"]}) == 3


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
