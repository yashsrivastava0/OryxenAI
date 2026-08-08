"""Unit tests for Discovery output validators (transport contract only)."""

from __future__ import annotations

from oryxenai.agents.discovery.validators import (
    validate_brief_output,
    validate_questions_output,
)


def _question(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "q1",
        "text": "Which role is this portfolio for?",
        "kind": "single_select",
        "options": [{"id": "backend", "label": "Backend Engineer"}],
    }
    base.update(overrides)
    return base


def _valid_questions_output(questions: list[dict[str, object]] | None = None) -> dict[str, object]:
    return {
        "mode": "ASK_QUESTIONS",
        "assistant_message": "I have a few focused questions.",
        "questions": questions if questions is not None else [_question()],
    }


class TestValidateQuestionsOutput:
    def test_valid_single_select(self):
        outcome = validate_questions_output(_valid_questions_output())
        assert outcome.is_valid
        assert outcome.errors == []

    def test_valid_empty_for_ready_for_brief(self):
        outcome = validate_questions_output(
            {
                "mode": "READY_FOR_BRIEF",
                "assistant_message": "I have enough information.",
                "questions": [],
            }
        )
        assert outcome.is_valid

    def test_missing_questions_key(self):
        outcome = validate_questions_output({"mode": "ASK_QUESTIONS", "assistant_message": "m"})
        assert not outcome.is_valid
        assert "must be a list" in outcome.errors[0]

    def test_mode_required(self):
        outcome = validate_questions_output({"questions": [_question()], "assistant_message": "m"})
        assert not outcome.is_valid
        assert any("'mode' must be one of" in error for error in outcome.errors)

    def test_blank_assistant_message_rejected(self):
        outcome = validate_questions_output(
            {"mode": "ASK_QUESTIONS", "assistant_message": "  ", "questions": [_question()]}
        )
        assert not outcome.is_valid
        assert any("'assistant_message' is empty" in error for error in outcome.errors)

    def test_needs_details_with_questions_rejected(self):
        outcome = validate_questions_output(
            {
                "mode": "NEEDS_DETAILS",
                "assistant_message": "m",
                "questions": [_question()],
            }
        )
        assert not outcome.is_valid
        assert any(
            "NEEDS_DETAILS must have an empty questions list" in error for error in outcome.errors
        )

    def test_ask_questions_without_questions_rejected(self):
        outcome = validate_questions_output(
            {"mode": "ASK_QUESTIONS", "assistant_message": "m", "questions": []}
        )
        assert not outcome.is_valid
        assert any(
            "ASK_QUESTIONS must have at least one question" in error for error in outcome.errors
        )

    def test_ready_for_brief_with_questions_rejected(self):
        outcome = validate_questions_output(
            {
                "mode": "READY_FOR_BRIEF",
                "assistant_message": "m",
                "questions": [_question()],
            }
        )
        assert not outcome.is_valid
        assert any(
            "READY_FOR_BRIEF must have an empty questions list" in error for error in outcome.errors
        )

    def test_too_many_questions(self):
        questions = [_question(id=f"q{i}") for i in range(9)]
        outcome = validate_questions_output(
            {"mode": "ASK_QUESTIONS", "assistant_message": "m", "questions": questions},
            max_questions=8,
        )
        assert not outcome.is_valid
        assert any("Too many questions" in error for error in outcome.errors)

    def test_duplicate_ids_rejected(self):
        questions = [_question(), _question(id="q1")]
        outcome = validate_questions_output(_valid_questions_output(questions))
        assert not outcome.is_valid
        assert any("Duplicate question id" in error for error in outcome.errors)

    def test_missing_text_rejected(self):
        outcome = validate_questions_output(_valid_questions_output([_question(text="  ")]))
        assert not outcome.is_valid

    def test_invalid_kind_rejected(self):
        outcome = validate_questions_output(_valid_questions_output([_question(kind="wild")]))
        assert not outcome.is_valid

    def test_select_requires_options(self):
        outcome = validate_questions_output(
            _valid_questions_output([_question(kind="multi_select", options=[])])
        )
        assert not outcome.is_valid
        assert any("no options" in error for error in outcome.errors)

    def test_select_option_without_id_rejected(self):
        outcome = validate_questions_output(
            _valid_questions_output([_question(options=[{"id": "", "label": "x"}])])
        )
        assert not outcome.is_valid


class TestValidateBriefOutput:
    def test_valid_brief(self):
        outcome = validate_brief_output(
            {
                "mode": "BRIEF_READY",
                "assistant_message": "Review the brief.",
                "brief_title": "Portfolio Discovery Brief — Test",
                "brief_markdown": "# Portfolio Discovery Brief\n\nContent.",
                "user_summary": "A short friendly summary.",
                "profile": {"name": "Test User", "skills": ["Python"]},
                "open_items": ["no metrics"],
                "memory_update": {"intent_summary": "x"},
            }
        )
        assert outcome.is_valid
        assert outcome.errors == []

    def test_empty_open_items_and_memory_accepted(self):
        outcome = validate_brief_output(
            {
                "mode": "BRIEF_READY",
                "assistant_message": "m",
                "brief_title": "t",
                "brief_markdown": "x",
                "user_summary": "s",
            }
        )
        assert outcome.is_valid

    def test_blank_user_summary_rejected(self):
        outcome = validate_brief_output(
            {
                "mode": "BRIEF_READY",
                "assistant_message": "m",
                "brief_title": "t",
                "brief_markdown": "x",
                "user_summary": "   ",
            }
        )
        assert not outcome.is_valid
        assert any("'user_summary' is empty" in error for error in outcome.errors)

    def test_non_dict_profile_rejected(self):
        outcome = validate_brief_output(
            {
                "mode": "BRIEF_READY",
                "assistant_message": "m",
                "brief_title": "t",
                "brief_markdown": "x",
                "user_summary": "s",
                "profile": "not-an-object",
            }
        )
        assert not outcome.is_valid
        assert any("'profile' must be an object" in error for error in outcome.errors)

    def test_malformed_profile_shape_rejected(self):
        outcome = validate_brief_output(
            {
                "mode": "BRIEF_READY",
                "assistant_message": "m",
                "brief_title": "t",
                "brief_markdown": "x",
                "user_summary": "s",
                "profile": {"experience": ["just a string, not an object"]},
            }
        )
        assert not outcome.is_valid
        assert any("'profile' failed schema validation" in error for error in outcome.errors)

    def test_profile_unknown_field_rejected(self):
        outcome = validate_brief_output(
            {
                "mode": "BRIEF_READY",
                "assistant_message": "m",
                "brief_title": "t",
                "brief_markdown": "x",
                "user_summary": "s",
                "profile": {"name": "x", "unexpected_field": "bad"},
            }
        )
        assert not outcome.is_valid
        assert any("'profile' failed schema validation" in error for error in outcome.errors)

    def test_large_project_count_is_not_a_validation_error(self):
        """A long projects list is a fact about the resume, not a shape defect.

        Rejecting the whole brief here would be pointless: the model would
        find the same real projects again on retry and fail identically
        every time. DiscoveryAgent truncates to max_projects instead of
        this validator rejecting it — see test_agent.py.
        """
        outcome = validate_brief_output(
            {
                "mode": "BRIEF_READY",
                "assistant_message": "m",
                "brief_title": "t",
                "brief_markdown": "x",
                "user_summary": "s",
                "profile": {"projects": [{"name": f"p{i}"} for i in range(20)]},
            }
        )
        assert outcome.is_valid

    def test_blank_markdown_rejected(self):
        outcome = validate_brief_output(
            {
                "mode": "BRIEF_READY",
                "assistant_message": "m",
                "brief_title": "t",
                "brief_markdown": "   ",
            }
        )
        assert not outcome.is_valid
        assert any("'brief_markdown' is empty" in error for error in outcome.errors)

    def test_blank_title_rejected(self):
        outcome = validate_brief_output(
            {
                "mode": "BRIEF_READY",
                "assistant_message": "m",
                "brief_title": "",
                "brief_markdown": "x",
            }
        )
        assert not outcome.is_valid
        assert any("'brief_title' is empty" in error for error in outcome.errors)

    def test_wrong_mode_rejected(self):
        outcome = validate_brief_output(
            {
                "mode": "ASK_QUESTIONS",
                "assistant_message": "m",
                "brief_title": "t",
                "brief_markdown": "x",
            }
        )
        assert not outcome.is_valid
        assert any("'mode' must be BRIEF_READY" in error for error in outcome.errors)

    def test_blank_assistant_message_rejected(self):
        outcome = validate_brief_output(
            {
                "mode": "BRIEF_READY",
                "assistant_message": "",
                "brief_title": "t",
                "brief_markdown": "x",
            }
        )
        assert not outcome.is_valid

    def test_non_list_open_items_rejected(self):
        outcome = validate_brief_output(
            {
                "mode": "BRIEF_READY",
                "assistant_message": "m",
                "brief_title": "t",
                "brief_markdown": "x",
                "open_items": "not-a-list",
            }
        )
        assert not outcome.is_valid
        assert any("'open_items' must be a list" in error for error in outcome.errors)
