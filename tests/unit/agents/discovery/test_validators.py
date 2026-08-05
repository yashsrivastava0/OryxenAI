"""Unit tests for Discovery semantic validators."""

from __future__ import annotations

from oryxenai.agents.discovery.schemas import (
    DiscoveryAnalysisResult,
    DiscoveryBrief,
    DiscoveryQuestion,
    EvidenceReference,
    FactCandidate,
    FactStatus,
    SourceKind,
)
from oryxenai.agents.discovery.validators import (
    validate_answers,
    validate_call_a_result,
    validate_call_b_result,
    validate_evidence_excerpt,
    validate_questions,
)


class TestValidateEvidenceExcerpt:
    def test_excerpt_found_in_source(self):
        assert validate_evidence_excerpt("Python, PostgreSQL, FastAPI", "Python, PostgreSQL")

    def test_excerpt_not_found(self):
        assert not validate_evidence_excerpt("Python only", "Java")

    def test_whitespace_tolerant(self):
        assert validate_evidence_excerpt("Python\n  PostgreSQL", "Python PostgreSQL")

    def test_empty_excerpt(self):
        assert not validate_evidence_excerpt("Python", "")

    def test_case_insensitive(self):
        assert validate_evidence_excerpt("Python Expert", "python expert")


class FakeConfig:
    max_questions = 8
    max_featured_projects = 5


class TestValidateCallAResult:
    def test_valid_result_with_evidence(self):
        result = DiscoveryAnalysisResult(
            schema_version=1,
            detected_languages=["en"],
            fact_candidates=[
                FactCandidate(
                    local_key="f1",
                    category="skill",
                    field="skill",
                    value="Python",
                    status=FactStatus.SUPPORTED,
                    evidence=[
                        EvidenceReference(
                            source_id="resume_text",
                            source_kind=SourceKind.RESUME_TEXT,
                            evidence_excerpt="Python",
                        )
                    ],
                )
            ],
            questions=[],
        )
        sources = {"resume_text": "Python Expert, Software Engineer"}
        validation = validate_call_a_result(result, sources, FakeConfig())
        assert validation.is_valid

    def test_system_default_evidence_rejected(self):
        result = DiscoveryAnalysisResult(
            schema_version=1,
            detected_languages=["en"],
            fact_candidates=[
                FactCandidate(
                    local_key="f1",
                    category="preference",
                    field="tone",
                    value="technical",
                    status=FactStatus.SUPPORTED,
                    evidence=[
                        EvidenceReference(
                            source_id="system",
                            source_kind=SourceKind.SYSTEM_DEFAULT,
                            evidence_excerpt="default",
                        )
                    ],
                )
            ],
            questions=[],
        )
        sources: dict[str, str] = {}
        validation = validate_call_a_result(result, sources, FakeConfig())
        assert not validation.is_valid

    def test_missing_evidence(self):
        result = DiscoveryAnalysisResult(
            schema_version=1,
            detected_languages=["en"],
            fact_candidates=[
                FactCandidate(
                    local_key="f1",
                    category="skill",
                    field="skill",
                    value="Python",
                    status=FactStatus.SUPPORTED,
                    evidence=[],
                )
            ],
            questions=[],
        )
        sources: dict[str, str] = {}
        validation = validate_call_a_result(result, sources, FakeConfig())
        assert not validation.is_valid

    def test_evidence_not_found_in_source(self):
        result = DiscoveryAnalysisResult(
            schema_version=1,
            detected_languages=["en"],
            fact_candidates=[
                FactCandidate(
                    local_key="f1",
                    category="skill",
                    field="skill",
                    value="Python",
                    status=FactStatus.SUPPORTED,
                    evidence=[
                        EvidenceReference(
                            source_id="resume_text",
                            source_kind=SourceKind.RESUME_TEXT,
                            evidence_excerpt="Java Expert",
                        )
                    ],
                )
            ],
            questions=[],
        )
        sources = {"resume_text": "Python Expert"}
        validation = validate_call_a_result(result, sources, FakeConfig())
        assert not validation.is_valid

    def test_unparseable_schema_version(self):
        result = DiscoveryAnalysisResult(
            schema_version=999,
            detected_languages=["en"],
            fact_candidates=[],
            questions=[],
        )
        sources: dict[str, str] = {}
        validation = validate_call_a_result(result, sources, FakeConfig())
        assert not validation.is_valid


class TestValidateCallBResult:
    def test_valid_brief(self):
        brief = DiscoveryBrief(
            schema_version=1,
            goal="Test goal",
            positioning="Test positioning",
            output_language="en",
            downstream_fact_ids=["f1", "f2"],
        )
        validation = validate_call_b_result(brief, {"f1", "f2"}, set(), FakeConfig())
        assert validation.is_valid

    def test_unknown_fact_id(self):
        brief = DiscoveryBrief(
            schema_version=1,
            goal="Test",
            positioning="Test",
            output_language="en",
            downstream_fact_ids=["f1", "f3"],
        )
        validation = validate_call_b_result(brief, {"f1", "f2"}, set(), FakeConfig())
        assert not validation.is_valid


class TestValidateQuestions:
    def test_valid_questions(self):
        questions = [
            DiscoveryQuestion(
                local_key="q1",
                category="audience",
                text="Who is your audience?",
                kind="short_text",
            )
        ]
        validation = validate_questions(questions, FakeConfig())
        assert validation.is_valid

    def test_too_many_questions(self):
        questions = [
            DiscoveryQuestion(
                local_key=f"q{i}", category="audience", text=f"Q{i}", kind="short_text"
            )
            for i in range(10)
        ]
        validation = validate_questions(questions, FakeConfig())
        assert not validation.is_valid

    def test_duplicate_keys(self):
        questions = [
            DiscoveryQuestion(local_key="q1", category="audience", text="Q1", kind="short_text"),
            DiscoveryQuestion(local_key="q1", category="audience", text="Q2", kind="short_text"),
        ]
        validation = validate_questions(questions, FakeConfig())
        assert not validation.is_valid

    def test_auto_on_factual_question(self):
        questions = [
            DiscoveryQuestion(
                local_key="q1",
                category="target_role",
                text="What is your role?",
                kind="short_text",
                allows_auto=True,
            )
        ]
        validation = validate_questions(questions, FakeConfig())
        assert not validation.is_valid

    def test_auto_on_presentation_ok(self):
        questions = [
            DiscoveryQuestion(
                local_key="q1",
                category="presentation",
                text="What tone?",
                kind="single_select",
                options=[{"id": "tech", "label": "Technical"}],
                allows_auto=True,
            )
        ]
        validation = validate_questions(questions, FakeConfig())
        assert validation.is_valid


class TestValidateAnswers:
    def test_valid_answers(self):
        questions = [
            DiscoveryQuestion(
                local_key="q1",
                category="audience",
                text="Audience?",
                kind="single_select",
                options=[{"id": "r", "label": "Recruiters"}],
                allows_auto=False,
            )
        ]
        answers = {"q1": {"mode": "answered", "value": "recruiters"}}
        validation = validate_answers(answers, questions, FakeConfig())
        assert validation.is_valid

    def test_auto_on_factual(self):
        questions = [
            DiscoveryQuestion(
                local_key="q1",
                category="target_role",
                text="Role?",
                kind="short_text",
                allows_auto=False,
            )
        ]
        answers = {"q1": {"mode": "auto", "value": "engineer"}}
        validation = validate_answers(answers, questions, FakeConfig())
        assert not validation.is_valid

    def test_unknown_question(self):
        questions: list = []
        answers = {"q-unknown": {"mode": "answered", "value": "x"}}
        validation = validate_answers(answers, questions, FakeConfig())
        assert not validation.is_valid

    def test_boolean_wrong_type(self):
        questions = [
            DiscoveryQuestion(
                local_key="q1",
                category="presentation",
                text="Include contact?",
                kind="boolean",
            )
        ]
        answers = {"q1": {"mode": "answered", "value": "not a bool"}}
        validation = validate_answers(answers, questions, FakeConfig())
        assert not validation.is_valid
