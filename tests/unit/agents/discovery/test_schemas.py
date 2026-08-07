"""Unit tests for Discovery domain schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from oryxenai.agents.discovery.schemas import (
    AnswerMode,
    BriefOutput,
    DiscoveryAnswer,
    DiscoveryIntake,
    DiscoveryQuestion,
    DiscoveryState,
    DiscoveryStatus,
    OperationMode,
    QuestionKind,
    QuestionOption,
    QuestionSetOutput,
)


class TestDiscoveryIntake:
    def test_empty_intake(self):
        intake = DiscoveryIntake()
        assert intake.message == ""
        assert intake.document_text == ""
        assert intake.goal == ""

    def test_accepts_any_input(self):
        intake = DiscoveryIntake(
            message="Create a portfolio for me. I am a software developer.",
            document_text="lots of free-form text\n" * 10000,
            goal="get hired",
        )
        assert "software developer" in intake.message

    def test_unknown_fields_accepted(self):
        intake = DiscoveryIntake(message="hi", something_else={"nested": True})
        assert intake.something_else == {"nested": True}


class TestDiscoveryQuestion:
    def test_minimal_question(self):
        question = DiscoveryQuestion(id="q1", text="What is your role?")
        assert question.kind == QuestionKind.TEXT
        assert question.allow_skip is True
        assert question.allow_auto is False
        assert question.reason is None

    def test_select_question_with_options(self):
        question = DiscoveryQuestion(
            id="q1",
            text="Which role?",
            kind=QuestionKind.SINGLE_SELECT,
            options=[QuestionOption(id="backend", label="Backend Engineer")],
        )
        assert question.options[0].label == "Backend Engineer"

    def test_extra_fields_rejected(self):
        with pytest.raises(PydanticValidationError):
            DiscoveryQuestion(id="q1", text="Q", unknown="bad")


class TestOperationMode:
    def test_four_modes_round_trip(self):
        assert OperationMode.NEEDS_DETAILS.value == "NEEDS_DETAILS"
        assert OperationMode.ASK_QUESTIONS.value == "ASK_QUESTIONS"
        assert OperationMode.READY_FOR_BRIEF.value == "READY_FOR_BRIEF"
        assert OperationMode.BRIEF_READY.value == "BRIEF_READY"
        assert OperationMode("NEEDS_DETAILS") is OperationMode.NEEDS_DETAILS
        assert OperationMode("BRIEF_READY") is OperationMode.BRIEF_READY


class TestQuestionSetOutput:
    def test_empty_questions_valid(self):
        output = QuestionSetOutput(
            mode=OperationMode.NEEDS_DETAILS,
            assistant_message="Tell me more.",
            questions=[],
        )
        assert output.questions == []
        assert output.memory_update == {}

    def test_mode_and_assistant_message_required(self):
        with pytest.raises(PydanticValidationError):
            QuestionSetOutput(questions=[])

    def test_extra_fields_rejected(self):
        with pytest.raises(PydanticValidationError):
            QuestionSetOutput(
                mode=OperationMode.ASK_QUESTIONS,
                assistant_message="m",
                unknown="bad",
            )


class TestBriefOutput:
    def test_brief_output_has_no_rigid_field_contract(self):
        fields = set(BriefOutput.model_fields)
        assert fields == {
            "mode",
            "assistant_message",
            "brief_title",
            "brief_markdown",
            "open_items",
            "memory_update",
        }

    def test_valid_brief(self):
        output = BriefOutput(
            mode=OperationMode.BRIEF_READY,
            assistant_message="Review the brief.",
            brief_title="Portfolio Discovery Brief — Test",
            brief_markdown="# Portfolio Discovery Brief\n\nLong readable content.",
            open_items=["no metrics"],
            memory_update={"intent_summary": "x"},
        )
        assert output.brief_markdown.startswith("# Portfolio Discovery Brief")
        assert output.open_items == ["no metrics"]

    def test_mode_required(self):
        with pytest.raises(PydanticValidationError):
            BriefOutput(assistant_message="m", brief_title="t", brief_markdown="x")

    def test_extra_fields_rejected(self):
        with pytest.raises(PydanticValidationError):
            BriefOutput(
                mode=OperationMode.BRIEF_READY,
                assistant_message="m",
                brief_title="t",
                brief_markdown="x",
                role="not allowed",
            )


class TestDiscoveryAnswer:
    def test_answered_mode_with_value(self):
        ans = DiscoveryAnswer(question_id="q1", mode=AnswerMode.ANSWERED, value="recruiters")
        assert ans.mode == AnswerMode.ANSWERED

    def test_skipped_mode(self):
        ans = DiscoveryAnswer(question_id="q1", mode=AnswerMode.SKIPPED, value=None)
        assert ans.mode == AnswerMode.SKIPPED

    def test_any_value_accepted(self):
        ans = DiscoveryAnswer(question_id="q1", value={"multi": [1, 2, 3]})
        assert ans.value == {"multi": [1, 2, 3]}


class TestDiscoveryState:
    def test_default_state(self):
        state = DiscoveryState()
        assert state.status == DiscoveryStatus.NOT_STARTED
        assert state.max_attempts == 3
        assert state.operation_a.mode is None
        assert state.memory == {}
        assert not hasattr(state, "demo")
        assert not hasattr(state, "questions")

    def test_extra_fields_rejected(self):
        with pytest.raises(PydanticValidationError):
            DiscoveryState(status=DiscoveryStatus.NOT_STARTED, unknown="bad")
