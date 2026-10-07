"""The fixed visual choice is application policy, never model output."""

from __future__ import annotations

from typing import Any

from oryxenai.agents.discovery.schemas import (
    DiscoveryQuestion,
    OperationMode,
    QuestionKind,
    QuestionOption,
)

PALETTE_GAP_ID = "visual_palette_v1"
WORK_GAP_ID = "atlas_work_v1"
PALETTE_TO_THEME = {
    "forest_copper": "editorial-forest-motion/v1",
    "cobalt_white": "cobalt-atlas/v1",
    "obsidian_lime": "obsidian-signal/v1",
    "cobalt_atlas_interactive": "cobalt-atlas/v2",
    "claret_amber": "claret-marquee/v1",
}


def palette_question() -> DiscoveryQuestion:
    return DiscoveryQuestion(
        id="visual_palette",
        gap_id=PALETTE_GAP_ID,
        text="Which look feels right for your portfolio?",
        help_text="Each direction pairs its colors with a distinct design style. Choose the complete look you like most.",
        kind=QuestionKind.PALETTE_SELECT,
        options=[
            QuestionOption(
                id="forest_copper",
                label="Forest & copper",
                description="Editorial warmth · layered and considered",
                swatches=["#14231c", "#f3f1e9", "#9a3f29"],
            ),
            QuestionOption(
                id="cobalt_white",
                label="Cobalt & white",
                description="Minimal clarity · bright and structured",
                swatches=["#2849c9", "#f7f9fc", "#17253c"],
            ),
            QuestionOption(
                id="obsidian_lime",
                label="Obsidian & lime",
                description="Bold modernity · high contrast and energetic",
                swatches=["#0c0e0d", "#d9fc73", "#f0f2eb"],
            ),
            QuestionOption(
                id="cobalt_atlas_interactive",
                label="Cobalt & volt",
                description="Interactive editorial · layered and vivid",
                swatches=["#f8f8f5", "#3656d6", "#d7fa76"],
            ),
            QuestionOption(
                id="claret_amber",
                label="Claret & amber",
                description="Cinematic depth · warm and dramatic",
                swatches=["#3b0f1e", "#f6eee3", "#ffb04a"],
            ),
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
    if not isinstance(choice, str) or choice not in PALETTE_TO_THEME:
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
