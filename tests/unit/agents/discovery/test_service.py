"""Unit tests for Discovery service helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from oryxenai.agents.discovery.schemas import (
    DiscoveryIntake,
    DiscoveryQuestion,
    QuestionKind,
    QuestionOption,
)
from oryxenai.agents.discovery.service import (
    DiscoveryOperationError,
    DiscoveryService,
    _answer_text,
    _brief_hash,
    _elapsed_seconds,
    _has_answer_value,
    _merge_intake,
)
from oryxenai.core.settings import Settings


class TestElapsedSeconds:
    def test_none_started_at(self):
        assert _elapsed_seconds(None) is None

    def test_invalid_timestamp(self):
        assert _elapsed_seconds("not-a-date") is None

    def test_past_timestamp_returns_positive(self):
        started = (datetime.now(UTC) - timedelta(seconds=65)).isoformat()
        elapsed = _elapsed_seconds(started)
        assert elapsed is not None
        assert 60 <= elapsed <= 70

    def test_future_timestamp_clamped(self):
        started = (datetime.now(UTC) + timedelta(seconds=10)).isoformat()
        assert _elapsed_seconds(started) == 0.0


class TestIntakePreservation:
    def test_first_source_keeps_exact_text(self):
        submitted = "\n  Priya's resume  \n"
        intake, documents = _merge_intake(DiscoveryIntake(), DiscoveryIntake(source_text=submitted))
        assert intake.source_text == submitted
        assert [document.original_text for document in documents] == [submitted]

    def test_prefixed_append_keeps_exact_separator_and_new_text(self):
        previous = DiscoveryIntake(source_text="First role")
        submitted = "First role\n\n  Second role  \n"
        intake, documents = _merge_intake(previous, DiscoveryIntake(source_text=submitted))
        assert intake.source_text == submitted
        assert [document.original_text for document in documents] == ["\n\n  Second role  \n"]

    def test_new_submission_keeps_existing_and_new_whitespace(self):
        previous = DiscoveryIntake(source_text="First role  ")
        intake, documents = _merge_intake(previous, DiscoveryIntake(source_text="  Second role\n"))
        assert intake.source_text == "First role  \n\n  Second role\n"
        assert [document.original_text for document in documents] == ["  Second role\n"]

    def test_exact_retry_does_not_duplicate_source(self):
        previous = DiscoveryIntake(source_text="First role")
        intake, documents = _merge_intake(previous, DiscoveryIntake(source_text="First role"))
        assert intake.source_text == "First role"
        assert documents == []

    def test_formatting_only_append_is_not_dropped(self):
        previous = DiscoveryIntake(source_text="First role")
        intake, documents = _merge_intake(previous, DiscoveryIntake(source_text="First role\n"))
        assert intake.source_text == "First role\n"
        assert [document.original_text for document in documents] == ["\n"]


class TestAnswerText:
    def test_selected_choice_ids_become_labels(self):
        question = DiscoveryQuestion(
            id="direction",
            text="Which direction?",
            kind=QuestionKind.SINGLE_SELECT,
            options=[QuestionOption(id="backend", label="Backend engineering")],
        )
        assert _answer_text("backend", question) == "Backend engineering"
        assert _answer_text("A different direction", question) == "A different direction"

    def test_multiple_choice_ids_become_labels(self):
        question = DiscoveryQuestion(
            id="skills",
            text="Which skills?",
            kind=QuestionKind.MULTI_SELECT,
            options=[
                QuestionOption(id="research", label="User research"),
                QuestionOption(id="design", label="Interaction design"),
            ],
        )
        assert _answer_text(["research", "design"], question) == "User research, Interaction design"

    def test_blank_answers_are_not_treated_as_responses(self):
        assert not _has_answer_value(None)
        assert not _has_answer_value("  \n")
        assert not _has_answer_value([])
        assert not _has_answer_value({})
        assert _has_answer_value("A personal contribution")


class TestBriefHash:
    def test_deterministic_for_same_markdown(self):
        markdown = "# Portfolio Discovery Brief\n\nContent."
        assert _brief_hash(markdown) == _brief_hash(markdown)

    def test_differs_for_different_markdown(self):
        assert _brief_hash("brief one") != _brief_hash("brief two")


class TestModelProfileSelection:
    @staticmethod
    def _service() -> DiscoveryService:
        service = DiscoveryService.__new__(DiscoveryService)
        service._settings = Settings()
        return service

    def test_empty_selection_keeps_sticky_profile(self):
        assert self._service()._resolve_model_profile("", "sticky") == "sticky"

    def test_unknown_selection_is_rejected(self):
        with pytest.raises(DiscoveryOperationError) as exc_info:
            self._service()._resolve_model_profile("unknown", "")
        assert exc_info.value.code == "MODEL_PROFILE_NOT_SELECTABLE"
        assert exc_info.value.status_code == 400

    def test_selection_cannot_change_after_start(self):
        service = self._service()
        selectable = service._settings.models.routing.selectable_profiles
        assert selectable
        with pytest.raises(DiscoveryOperationError) as exc_info:
            service._resolve_model_profile(selectable[0], "different-profile")
        assert exc_info.value.code == "MODEL_PROFILE_LOCKED"


class TestIdempotencyKey:
    def test_stable_for_same_input(self):
        service = DiscoveryService.__new__(DiscoveryService)
        key1 = service._idempotency_key("s1", "understand_and_question", {"message": "x"}, {})
        key2 = service._idempotency_key("s1", "understand_and_question", {"message": "x"}, {})
        assert key1 == key2

    def test_differs_for_different_input(self):
        service = DiscoveryService.__new__(DiscoveryService)
        key1 = service._idempotency_key("s1", "understand_and_question", {"message": "x"}, {})
        key2 = service._idempotency_key("s1", "understand_and_question", {"message": "y"}, {})
        assert key1 != key2

    def test_differs_for_different_operation(self):
        service = DiscoveryService.__new__(DiscoveryService)
        key1 = service._idempotency_key("s1", "understand_and_question", {"message": "x"}, {})
        key2 = service._idempotency_key("s1", "build_or_revise_brief", {"message": "x"}, {})
        assert key1 != key2

    def test_differs_for_different_memory(self):
        service = DiscoveryService.__new__(DiscoveryService)
        key1 = service._idempotency_key(
            "s1", "understand_and_question", {"message": "x"}, {}, memory={"intent_summary": "a"}
        )
        key2 = service._idempotency_key(
            "s1", "understand_and_question", {"message": "x"}, {}, memory={"intent_summary": "b"}
        )
        assert key1 != key2

    def test_same_memory_same_key(self):
        service = DiscoveryService.__new__(DiscoveryService)
        key1 = service._idempotency_key(
            "s1", "understand_and_question", {"message": "x"}, {}, memory={"intent_summary": "a"}
        )
        key2 = service._idempotency_key(
            "s1", "understand_and_question", {"message": "x"}, {}, memory={"intent_summary": "a"}
        )
        assert key1 == key2

    def test_differs_for_existing_brief(self):
        service = DiscoveryService.__new__(DiscoveryService)
        key1 = service._idempotency_key(
            "s1", "build_or_revise_brief", {"message": "x"}, {}, existing_brief=""
        )
        key2 = service._idempotency_key(
            "s1", "build_or_revise_brief", {"message": "x"}, {}, existing_brief="# old brief"
        )
        assert key1 != key2
