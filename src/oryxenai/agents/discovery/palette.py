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
PALETTE_TO_THEME = {
    "forest_copper": "editorial-forest-motion/v1",
    "cobalt_white": "cobalt-atlas/v1",
    "obsidian_lime": "obsidian-signal/v1",
}


def palette_question() -> DiscoveryQuestion:
    return DiscoveryQuestion(
        id="visual_palette",
        gap_id=PALETTE_GAP_ID,
        text="Which color direction feels right for your portfolio?",
        help_text="Choose the palette that feels most like you. You can add a note about the mood, too.",
        kind=QuestionKind.PALETTE_SELECT,
        options=[
            QuestionOption(
                id="forest_copper",
                label="Forest & copper",
                description="Warm, considered, editorial",
                swatches=["#14231c", "#f3f1e9", "#9a3f29"],
            ),
            QuestionOption(
                id="cobalt_white",
                label="Cobalt & white",
                description="Bright, structured, open",
                swatches=["#2849c9", "#f7f9fc", "#17253c"],
            ),
            QuestionOption(
                id="obsidian_lime",
                label="Obsidian & lime",
                description="Bold, high contrast, energetic",
                swatches=["#0c0e0d", "#d9fc73", "#f0f2eb"],
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
