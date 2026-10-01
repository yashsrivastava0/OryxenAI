"""Server-side dossier construction and the compatibility profile projection."""

from __future__ import annotations

from oryxenai.agents.discovery.dossier import build_dossier, profile_from_dossier


def _dossier(raw: dict):
    return build_dossier(raw, open_items=[], goal_text="goal", documents=[], question_events=[])


def test_grouped_and_plural_evidence_projects_into_profile() -> None:
    dossier = _dossier(
        {
            "other_evidence": [
                {"category": "Skills", "title": "Technical skills", "detail": "Go, Python; Kafka"},
                {"category": "languages", "title": "Spoken", "detail": "English (fluent), Hindi"},
            ]
        }
    )
    profile = profile_from_dossier(dossier)
    assert profile.skills == ["Go", "Python", "Kafka"]
    assert profile.spoken_languages == ["English (fluent)", "Hindi"]


def test_ids_are_unique_dangling_links_dropped_and_enums_coerced() -> None:
    dossier = _dossier(
        {
            "facts": [
                {"id": "f1", "statement": "Led a team", "ownership": "TEAM LEAD"},
                {"id": "f1", "statement": "Shipped a CLI", "ownership": "weird"},
            ],
            "roles": [{"organization": "Acme", "fact_ids": ["f1", "missing"]}],
        }
    )
    assert len({fact.id for fact in dossier.facts}) == 2
    assert [fact.ownership.value for fact in dossier.facts] == ["unknown", "unknown"]
    assert dossier.roles[0].fact_ids == ["f1"]
    assert dossier.contract_version == "DiscoveryDossier/v1"
    assert dossier.source_coverage == []
