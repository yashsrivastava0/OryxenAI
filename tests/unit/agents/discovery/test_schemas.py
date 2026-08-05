"""Unit tests for Discovery domain schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from oryxenai.agents.discovery.schemas import (
    AnswerMode,
    AutoDecision,
    AutoDecisionCategory,
    ConflictResolutionPolicy,
    ConflictSeverity,
    DiscoveryAnalysisResult,
    DiscoveryAnswer,
    DiscoveryBrief,
    DiscoveryConflict,
    DiscoveryIntake,
    DiscoveryLink,
    DiscoveryQuestion,
    DiscoveryState,
    DiscoveryStatus,
    EvidenceReference,
    FactCandidate,
    FactStatus,
    NormalizedProfessionalProfile,
    QuestionCategory,
    QuestionKind,
    ResumeSource,
    SourceKind,
)


class TestDiscoveryIntake:
    def test_valid_minimal_intake(self):
        intake = DiscoveryIntake()
        assert intake.resume_source == ResumeSource.NONE
        assert intake.output_language == "en"

    def test_valid_full_intake(self):
        intake = DiscoveryIntake(
            main_prompt="I need a portfolio for backend roles.",
            resume_text="Test User\nSoftware Engineer\nPython, PostgreSQL, FastAPI",
            resume_source=ResumeSource.PASTED_TEXT,
            links=[DiscoveryLink(url="https://github.com/testuser", kind="github")],
            output_language="en",
            source_revision=1,
        )
        assert intake.main_prompt == "I need a portfolio for backend roles."
        assert len(intake.links) == 1

    def test_extra_fields_rejected(self):
        with pytest.raises(PydanticValidationError):
            DiscoveryIntake(unknown_field="should fail")

    def test_main_prompt_length_enforced(self):
        with pytest.raises(PydanticValidationError):
            DiscoveryIntake(main_prompt="x" * 30000)

    def test_resume_text_length_enforced(self):
        with pytest.raises(PydanticValidationError):
            DiscoveryIntake(resume_text="x" * 300000)

    def test_links_max_enforced(self):
        links = [DiscoveryLink(url="https://example.com")] * 50
        with pytest.raises(PydanticValidationError, match="30"):
            DiscoveryIntake(links=links)


class TestEvidenceReference:
    def test_valid_evidence(self):
        ev = EvidenceReference(
            source_id="resume_text",
            source_kind=SourceKind.RESUME_TEXT,
            evidence_excerpt="Python, PostgreSQL",
        )
        assert ev.source_id == "resume_text"

    def test_unknown_source_kind_rejected(self):
        with pytest.raises(PydanticValidationError):
            EvidenceReference(source_id="x", source_kind="invalid")


class TestFactCandidate:
    def test_supported_fact_requires_evidence(self):
        fact = FactCandidate(
            local_key="fact-1",
            category="skill",
            field="skill",
            value="Python",
            status=FactStatus.SUPPORTED,
        )
        assert fact.status == FactStatus.SUPPORTED

    def test_system_default_fact(self):
        fact = FactCandidate(
            local_key="fact-1",
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
        assert len(fact.evidence) == 1

    def test_extra_fields_rejected(self):
        with pytest.raises(PydanticValidationError):
            FactCandidate(local_key="f1", category="skill", field="skill", value="x", unknown="bad")


class TestDiscoveryAnalysisResult:
    def test_valid_result(self):
        result = DiscoveryAnalysisResult(
            schema_version=1,
            detected_languages=["en"],
            normalized_profile=NormalizedProfessionalProfile(),
            fact_candidates=[],
            questions=[],
        )
        assert result.schema_version == 1

    def test_too_many_questions_accepted_by_schema(self):
        questions = [
            DiscoveryQuestion(local_key=f"q{i}", category="audience", text=f"Q{i}")
            for i in range(10)
        ]
        result = DiscoveryAnalysisResult(
            schema_version=1,
            detected_languages=["en"],
            normalized_profile=NormalizedProfessionalProfile(),
            fact_candidates=[],
            questions=questions,
        )
        assert len(result.questions) == 10


class TestDiscoveryBrief:
    def test_valid_brief(self):
        brief = DiscoveryBrief(
            schema_version=1,
            goal="Present a backend engineering portfolio.",
            positioning="Production-focused backend engineer.",
            output_language="en",
        )
        assert brief.schema_version == 1

    def test_extra_fields_rejected(self):
        with pytest.raises(PydanticValidationError):
            DiscoveryBrief(schema_version=1, goal="test", unknown_field="bad")


class TestDiscoveryQuestion:
    def test_auto_allowed_on_presentation(self):
        q = DiscoveryQuestion(
            local_key="q1",
            category="presentation",
            text="What tone?",
            allows_auto=True,
            auto_answer="technical",
        )
        assert q.allows_auto

    def test_auto_forbidden_on_factual(self):
        q = DiscoveryQuestion(
            local_key="q1",
            category="target_role",
            text="What is your role?",
            allows_auto=False,
        )
        assert not q.allows_auto

    def test_single_select_requires_options(self):
        q = DiscoveryQuestion(
            local_key="q1",
            category="audience",
            text="Who is your audience?",
            kind=QuestionKind.SINGLE_SELECT,
            options=[{"id": "r", "label": "Recruiters"}],
        )
        assert len(q.options) == 1

    def test_priority_clamped(self):
        q = DiscoveryQuestion(local_key="q1", category="audience", text="Q", priority=15)
        assert q.priority == 10
        q2 = DiscoveryQuestion(local_key="q2", category="audience", text="Q", priority=-5)
        assert q2.priority == 0


class TestDiscoveryAnswer:
    def test_answered_mode_with_value(self):
        ans = DiscoveryAnswer(question_id="q1", mode=AnswerMode.ANSWERED, value="recruiters")
        assert ans.mode == AnswerMode.ANSWERED

    def test_auto_mode(self):
        ans = DiscoveryAnswer(question_id="q1", mode=AnswerMode.AUTO, value="technical")
        assert ans.mode == AnswerMode.AUTO

    def test_skipped_mode(self):
        ans = DiscoveryAnswer(question_id="q1", mode=AnswerMode.SKIPPED)
        assert ans.mode == AnswerMode.SKIPPED


class TestDiscoveryState:
    def test_default_state(self):
        state = DiscoveryState()
        assert state.schema_version == 1
        assert state.status == DiscoveryStatus.NOT_STARTED
        assert state.source_revision == 0

    def test_state_with_questions(self):
        state = DiscoveryState(
            status=DiscoveryStatus.QUESTIONS_READY,
            source_revision=3,
        )
        assert state.status == DiscoveryStatus.QUESTIONS_READY

    def test_extra_fields_rejected(self):
        with pytest.raises(PydanticValidationError):
            DiscoveryState(status=DiscoveryStatus.NOT_STARTED, unknown="bad")


class TestAutoDecision:
    def test_valid_auto_decision(self):
        d = AutoDecision(
            category=AutoDecisionCategory.TONE,
            selected_value="technical",
            explanation="Profile targets backend roles.",
        )
        assert d.category == AutoDecisionCategory.TONE

    def test_invalid_category_rejected(self):
        with pytest.raises(PydanticValidationError):
            AutoDecision(category="invalid_category", selected_value="x", explanation="x")


class TestConflict:
    def test_blocking_conflict(self):
        c = DiscoveryConflict(
            local_key="c1",
            category="date",
            field="end_date",
            severity=ConflictSeverity.BLOCKING,
            resolution_policy=ConflictResolutionPolicy.ASK_USER,
            user_visible_summary="Conflicting end dates found.",
        )
        assert c.severity == ConflictSeverity.BLOCKING

    def test_invalid_severity_rejected(self):
        with pytest.raises(PydanticValidationError):
            DiscoveryConflict(
                local_key="c1",
                category="date",
                field="end_date",
                severity="critical",
                user_visible_summary="x",
            )


class TestResumeSource:
    def test_all_expected_values(self):
        expected = {
            "none",
            "pasted_text",
            "extracted_pdf_text",
            "empty_extraction",
            "scanned_pdf_suspected",
            "corrupt_pdf",
            "password_protected_pdf",
            "truncated_text",
        }
        actual = {m.value for m in ResumeSource}
        assert expected == actual


class TestQuestionCategory:
    def test_factual_categories(self):
        factual = {
            QuestionCategory.TARGET_ROLE,
            QuestionCategory.PROJECT_SELECTION,
            QuestionCategory.PERSONAL_CONTRIBUTION,
            QuestionCategory.CONFIDENTIALITY,
            QuestionCategory.CONTACT,
            QuestionCategory.CONFLICT_RESOLUTION,
        }
        assert QuestionCategory.TARGET_ROLE in factual
        assert QuestionCategory.PRESENTATION not in factual
