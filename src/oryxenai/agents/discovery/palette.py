"""The fixed visual choice is application policy, never model output."""

from __future__ import annotations

from typing import Any

from oryxenai.agents.discovery.schemas import (
    DiscoveryQuestion,
    OperationMode,
    QuestionKind,
    QuestionOption,
)
from oryxenai.themes.catalog import theme_catalog

PALETTE_GAP_ID = "visual_palette_v1"
WORK_GAP_ID = "atlas_work_v1"
PALETTE_TO_THEME = {choice.id: choice.theme_id for choice in theme_catalog()}


def palette_question() -> DiscoveryQuestion:
    return DiscoveryQuestion(
        id="visual_palette",
        gap_id=PALETTE_GAP_ID,
        text="Which look feels right for your portfolio?",
        help_text="Each direction pairs its colors with a distinct design style. Choose the complete look you like most.",
        kind=QuestionKind.PALETTE_SELECT,
        options=[
            QuestionOption(
                id=choice.id,
                label=choice.label,
                description=choice.description,
                swatches=list(choice.swatches),
                theme=choice.presentation,
            )
            for choice in theme_catalog()
            if choice.selectable
        ],
        allow_skip=False,
    )


def add_palette_question(output: dict[str, Any], *, already_answered: bool) -> dict[str, Any]:
    if already_answered or output["mode"] == OperationMode.NEEDS_DETAILS.value:
        return output
    questions = [
        question for question in output["questions"] if question.get("gap_id") != PALETTE_GAP_ID
    ]
    return {
        **output,
        "mode": OperationMode.ASK_QUESTIONS.value,
        "questions": [*questions, palette_question().model_dump(mode="json")],
    }


def palette_answer(value: Any) -> tuple[str, str] | None:
    if not isinstance(value, dict) or set(value) != {"choice_id", "note"}:
        return None
    choice, note = value["choice_id"], value["note"]
    if not isinstance(choice, str) or not any(
        entry.id == choice and entry.selectable for entry in theme_catalog()
    ):
        return None
    if not isinstance(note, str) or len(note.strip()) > 1000:
        return None
    return choice, note.strip()


def atlas_work_question(question_id: str) -> DiscoveryQuestion:
    return DiscoveryQuestion(
        id=question_id,
        gap_id=WORK_GAP_ID,
        text="Is there a project you want to feature?",
        help_text=(
            "Share a real project if you like. You can also allow a clearly labeled "
            "illustrative concept if your material has no usable project."
        ),
        kind=QuestionKind.WORK_DETAIL,
        allow_skip=True,
    )


def atlas_work_answer(value: Any) -> tuple[str, bool] | None:
    if not isinstance(value, dict) or set(value) != {"details", "allow_illustrative"}:
        return None
    details, allowed = value["details"], value["allow_illustrative"]
    if not isinstance(details, str) or not isinstance(allowed, bool):
        return None
    if len(details.strip()) > 12000 or (not details.strip() and not allowed):
        return None
    return details.strip(), allowed
