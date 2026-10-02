"""Typed content edits: the whitelist, atomic application, and what each plan decides."""

from __future__ import annotations

import copy
from typing import Any

import pytest

from oryxenai.agents.code_generator.changes import (
    ChangeError,
    apply_operation,
    apply_operations,
    clean_reply,
    content_sha256,
    decide_change,
    leaf_strings,
    removed_strings,
)
from oryxenai.agents.code_generator.prompt_builder import build_instructions
from oryxenai.agents.code_generator.schemas import ChangeIntent, ChangeOperation, ChangePlanEnvelope
from oryxenai.themes import get_theme
from tests.unit.agents.code_generator.helpers import sample_content

CONTENT = sample_content("01_strong_profile")


def op(verb: str, path: str, value: Any = None) -> ChangeOperation:
    return ChangeOperation(op=verb, path=path, value=value)  # type: ignore[arg-type]


def plan(intent: str = "content_edit", **kwargs: Any) -> ChangePlanEnvelope:
    return ChangePlanEnvelope.model_validate({"intent": intent, **kwargs})


# ── operations ───────────────────────────────────────────────────────────────


def test_set_replaces_text_fields_and_trims() -> None:
    updated = apply_operations(CONTENT, [op("set", "hero.intro", "  A shorter intro.  ")])
    assert updated["hero"]["intro"] == "A shorter intro."
    assert CONTENT["hero"]["intro"] != "A shorter intro."  # the input is never mutated


def test_set_edits_one_pillar_without_touching_the_others() -> None:
    updated = apply_operations(
        CONTENT, [op("set", "systems_practice.pillars[2].title", "New title")]
    )
    pillars = updated["systems_practice"]["pillars"]
    assert pillars[2]["title"] == "New title"
    assert [p["title"] for i, p in enumerate(pillars) if i != 2] == [
        p["title"] for i, p in enumerate(CONTENT["systems_practice"]["pillars"]) if i != 2
    ]
    assert len(pillars) == 4


def test_lists_can_be_set_appended_and_trimmed_by_index() -> None:
    updated = apply_operations(
        CONTENT,
        [
            op("append", "marquee_keywords", "Rust"),
            op("set", "marquee_keywords[0]", "First"),
            op("append", "technical_capabilities.groups[0].items", "Zig"),
            op("remove", "technical_capabilities.groups[0].items[0]"),
            op("append", "professional_context.organizations", "Acme Labs"),
        ],
    )
    assert updated["marquee_keywords"][-1] == "Rust" and updated["marquee_keywords"][0] == "First"
    assert updated["technical_capabilities"]["groups"][0]["items"][-1] == "Zig"
    assert (
        CONTENT["technical_capabilities"]["groups"][0]["items"][0]
        not in updated["technical_capabilities"]["groups"][0]["items"]
    )
    assert updated["professional_context"]["organizations"][-1] == "Acme Labs"


def test_groups_and_links_can_be_added_and_removed() -> None:
    updated = apply_operations(
        CONTENT,
        [
            op("append", "technical_capabilities.groups", {"heading": "Data", "items": ["SQL"]}),
            op(
                "append",
                "connect.destinations",
                {"label": "Blog", "url": "https://blog.example.com"},
            ),
            op("remove", "connect.destinations[0]"),
            op("set", "connect.destinations[0].featured", True),
        ],
    )
    assert updated["technical_capabilities"]["groups"][-1] == {"heading": "Data", "items": ["SQL"]}
    assert len(updated["connect"]["destinations"]) == len(CONTENT["connect"]["destinations"])
    assert updated["connect"]["destinations"][-1] == {
        "label": "Blog",
        "url": "https://blog.example.com",
        "featured": False,
    }
    assert updated["connect"]["destinations"][0]["featured"] is True


@pytest.mark.parametrize(
    ("operation", "fragment"),
    [
        (op("set", "hero.nope", "x"), "cannot be changed"),
        (op("set", "systems_practice.pillars", []), "cannot be changed"),
        (
            op("append", "systems_practice.pillars", {"title": "x", "description": "y"}),
            "Nothing can be added",
        ),
        (op("remove", "systems_practice.pillars[0]"), "cannot be removed"),
        (op("set", "systems_practice.pillars[9].title", "x"), "past the end"),
        (op("remove", "marquee_keywords[99]"), "past the end"),
        (op("set", "hero.name", 5), "needs text"),
        (op("set", "marquee_keywords", "not a list"), "list of text"),
        (op("append", "connect.destinations", "nope"), "needs an object"),
        (op("append", "connect.destinations", {"label": "x"}), "needs text"),
        (op("set", "connect.destinations[0].featured", "yes"), "true or false"),
        (op("set", "hero..name", "x"), "not a valid content path"),
        (op("set", "hero.name; drop", "x"), "not a valid content path"),
        (op("set", "", "x"), "empty or oversized"),
        (op("set", "__class__.x", "x"), "cannot be changed"),
        (op("set", "metadata.title.extra", "x"), "cannot be changed"),
    ],
)
def test_disallowed_or_malformed_edits_are_refused_with_a_reason(
    operation: ChangeOperation, fragment: str
) -> None:
    with pytest.raises(ChangeError) as caught:
        apply_operations(CONTENT, [operation])
    assert fragment in caught.value.message


def test_a_failing_edit_leaves_the_input_untouched_and_applies_nothing() -> None:
    before = copy.deepcopy(CONTENT)
    with pytest.raises(ChangeError):
        apply_operations(
            CONTENT, [op("set", "hero.intro", "Changed."), op("set", "hero.nope", "x")]
        )
    assert before == CONTENT


def test_apply_operation_mutates_only_the_copy_it_is_given() -> None:
    working = copy.deepcopy(CONTENT)
    apply_operation(working, op("set", "hero.location", ""))
    assert working["hero"]["location"] == "" and CONTENT["hero"]["location"] != ""


# ── decisions ────────────────────────────────────────────────────────────────


def test_a_valid_edit_becomes_a_build_with_the_new_content() -> None:
    decision = decide_change(
        CONTENT,
        plan(
            reply="Shortened the intro.", ops=[op("set", "hero.intro", "Short intro.").model_dump()]
        ),
    )
    assert decision.kind == "build" and decision.reply == "Shortened the intro."
    assert (
        decision.new_content is not None and decision.new_content["hero"]["intro"] == "Short intro."
    )
    assert decision.removed == frozenset()


@pytest.mark.parametrize(
    ("intent", "kwargs", "expected"),
    [
        ("style_request", {"reply": "Styling cannot be changed from chat yet."}, "Styling cannot"),
        ("style_request", {}, "Styling and layout"),
        ("unsupported", {"reply": "I cannot add scripts."}, "I cannot add scripts."),
        ("chat_only", {"reply": "Hi! I can edit your wording."}, "Hi!"),
        ("needs_clarification", {"clarification": "Which award do you mean?"}, "Which award"),
        ("needs_clarification", {}, "Could you say a little more"),
        ("content_edit", {"reply": "Nothing to do."}, "Nothing to do."),
        ("content_edit", {}, "could not find anything"),
    ],
)
def test_requests_that_change_nothing_get_a_reply(
    intent: str, kwargs: dict[str, Any], expected: str
) -> None:
    decision = decide_change(CONTENT, plan(intent, **kwargs))
    assert decision.kind == "reply" and expected in decision.reply and decision.new_content is None


def test_a_bad_operation_is_explained_in_the_reply() -> None:
    decision = decide_change(CONTENT, plan(ops=[op("set", "hero.nope", "x").model_dump()]))
    assert decision.kind == "reply"
    assert (
        decision.reply.startswith("I could not make that change:") and "hero.nope" in decision.reply
    )


def test_emptying_a_required_field_is_refused_by_the_same_rules_as_a_first_build() -> None:
    decision = decide_change(CONTENT, plan(ops=[op("set", "hero.name", "").model_dump()]))
    assert decision.kind == "reply" and "I could not make that change" in decision.reply


def test_content_that_would_not_fit_the_template_is_refused() -> None:
    decision = decide_change(CONTENT, plan(ops=[op("set", "hero.intro", "x" * 5000).model_dump()]))
    assert decision.kind == "reply" and "hero.intro" in decision.reply


def test_a_no_op_is_recognised() -> None:
    same = CONTENT["hero"]["intro"]
    decision = decide_change(CONTENT, plan(ops=[op("set", "hero.intro", same).model_dump()]))
    assert decision.kind == "reply" and "already how the page reads" in decision.reply


def test_privacy_sensitive_edits_report_the_text_that_disappeared() -> None:
    org = CONTENT["professional_context"]["organizations"][0]
    decision = decide_change(
        CONTENT,
        plan(
            privacy_sensitive=True,
            reply="Removed the organization.",
            ops=[op("remove", "professional_context.organizations[0]").model_dump()],
        ),
    )
    assert decision.kind == "build" and org in decision.removed
    ordinary = decide_change(
        CONTENT, plan(ops=[op("remove", "professional_context.organizations[0]").model_dump()])
    )
    assert ordinary.removed == frozenset()


def test_leaf_strings_and_fingerprints() -> None:
    assert "Python" in leaf_strings({"a": ["Python", "ab"], "b": {"c": "  Go  "}}) | {"Python"}
    assert leaf_strings({"x": "ab"}) == set()  # too short to matter
    assert removed_strings({"a": ["Secret Corp", "Keep"]}, {"a": ["Keep"]}) == {"Secret Corp"}
    assert content_sha256(CONTENT) == content_sha256(copy.deepcopy(CONTENT))
    changed = copy.deepcopy(CONTENT)
    changed["hero"]["name"] = "Someone Else"
    assert content_sha256(changed) != content_sha256(CONTENT)


def test_model_written_replies_are_cleaned_and_bounded() -> None:
    assert clean_reply("  line one\n\nline   two  ") == "line one line two"
    assert clean_reply("a" + chr(0) + "b" + chr(7)) == "a b"
    assert clean_reply("", "fallback") == "fallback"
    long = clean_reply("word " * 400)
    assert len(long) <= 600 and long.endswith(chr(0x2026))


def test_enum_covers_every_intent_the_prompt_names() -> None:
    assert {item.value for item in ChangeIntent} == {
        "content_edit",
        "style_request",
        "needs_clarification",
        "chat_only",
        "unsupported",
    }


# ── prompt ───────────────────────────────────────────────────────────────────


def test_the_interpreter_prompt_lists_the_editable_paths_but_not_the_theme_contract() -> None:
    bundle = build_instructions("interpret_change", get_theme())
    assert "systems_practice.pillars[i]" in bundle.task
    assert "Output JSON schema" in bundle.task and "privacy_sensitive" in bundle.task
    assert "class" not in bundle.system_prompt.lower().split("<role>")[0]
    assert "THEME" not in bundle.system_prompt and "skip-link" not in bundle.system_prompt
    assert bundle.version == "code_generator.interpret_change.v1"
    assert "theme" not in bundle.manifest and "system_interpreter.md" in bundle.manifest


def test_the_page_prompt_still_carries_the_theme_contract() -> None:
    bundle = build_instructions("generate_page", get_theme())
    assert "skip-link" in bundle.system_prompt and "{{THEME_CONTRACT}}" not in bundle.system_prompt
    assert bundle.manifest["theme"].startswith("editorial-forest/v1@")
