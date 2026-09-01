from __future__ import annotations

import pytest

from oryxenai.agents.code_generator.core.development_schemas import (
    GenerationChanges,
    GenerationResult,
    SourceFileChange,
    SourceGenerationEnvelopeV2,
)
from oryxenai.agents.code_generator.core.generation_prompt_builder import build_instructions
from oryxenai.agents.code_generator.core.source_validation import (
    SourceValidationError,
    validate_generation_changes,
)


def test_generation_result_requires_one_tagged_payload() -> None:
    result = GenerationResult.model_validate(
        {
            "operation_id": "foundation",
            "based_on_context_receipt": "context-hash",
            "mode": "changes",
            "changes": {
                "files": [
                    {
                        "path": "src/design/generated.css",
                        "operation": "create",
                        "complete_utf8_content": ".generated { color: red; }",
                    }
                ]
            },
        }
    )
    assert result.mode == "changes"


def test_generation_result_drops_mismatched_payloads() -> None:
    # Strict output schemas make every property required, so models may fill
    # several payload fields; the mode tag decides and the rest are dropped.
    result = GenerationResult.model_validate(
        {
            "operation_id": "foundation",
            "based_on_context_receipt": "context-hash",
            "mode": "changes",
            "changes": {
                "files": [
                    {
                        "path": "src/a.ts",
                        "operation": "create",
                        "complete_utf8_content": "export {};",
                    }
                ]
            },
            "requests": {
                "resource_requests": [
                    {
                        "request_id": "request",
                        "based_on": {"input_receipt_hash": "i", "site_plan_hash": "p"},
                        "origin": {"work_unit_id": "foundation"},
                        "category": "image",
                        "placement": {"purpose": "ornament"},
                        "why_existing_is_insufficient": "needed",
                        "query": {},
                        "technical_constraints": {},
                        "source_constraints": {},
                        "requiredness": "preferred",
                        "fallback": {"kind": "generated_local", "implementation": "css"},
                    }
                ]
            },
        }
    )
    assert result.mode == "changes"
    assert result.changes is not None and len(result.changes.files) == 1
    assert result.requests is None
    assert result.cannot_complete is None


def test_generation_result_still_rejects_empty_mode_payload() -> None:
    # Adoption only applies when exactly one payload is present; a result with
    # no payload at all is still rejected honestly.
    with pytest.raises(ValueError, match="mode=changes requires its matching payload"):
        GenerationResult.model_validate(
            {
                "operation_id": "foundation",
                "based_on_context_receipt": "context-hash",
                "mode": "changes",
                "changes": None,
                "requests": None,
                "cannot_complete": None,
            }
        )


def test_source_changes_reject_remote_runtime_and_ownership_escape(tmp_path) -> None:
    changes = GenerationChanges(
        files=[
            SourceFileChange(
                path="src/routes/home/page.tsx",
                operation="create",
                complete_utf8_content='export default function Page() { return <img src="https://example.com/a.png" />; }',
            )
        ]
    )
    with pytest.raises(SourceValidationError, match="remote"):
        validate_generation_changes(
            changes,
            owned_paths=["src/routes/home/**"],
            repo_dir=tmp_path,
            max_file_bytes=10000,
            max_response_bytes=10000,
            allowed_packages=set(),
            public_text=set(),
        )
    unsafe = changes.model_copy(deep=True)
    unsafe.files[0].path = "src/other.tsx"
    unsafe.files[0].complete_utf8_content = "export default function Page() { return null; }"
    with pytest.raises(SourceValidationError, match="ownership"):
        validate_generation_changes(
            unsafe,
            owned_paths=["src/routes/home/**"],
            repo_dir=tmp_path,
            max_file_bytes=10000,
            max_response_bytes=10000,
            allowed_packages=set(),
            public_text=set(),
        )


def test_source_copy_policy_ignores_pure_jsx_child_expressions(tmp_path) -> None:
    expression = GenerationChanges(
        files=[
            SourceFileChange(
                path="src/routes/home/Disclosure.tsx",
                operation="create",
                complete_utf8_content=(
                    "export function Disclosure({ open }: { open: boolean }) { "
                    'return <button>{open ? "-" : "+"}</button>; }'
                ),
            )
        ]
    )

    validated = validate_generation_changes(
        expression,
        owned_paths=["src/routes/home/**"],
        repo_dir=tmp_path,
        max_file_bytes=10000,
        max_response_bytes=10000,
        allowed_packages=set(),
        public_text={"Approved portfolio copy."},
    )

    assert validated == expression.files

    generic_types = expression.model_copy(deep=True)
    generic_types.files[0].complete_utf8_content = """import { useEffect, useRef } from "react";
export function Disclosure() {
  const sectionRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const section = sectionRef.current;
    const target = section?.querySelector<HTMLElement>("[data-target]");
    if (!section || !target || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(() => target.focus());
    observer.observe(section);
    return () => observer.disconnect();
  }, []);
  return <section ref={sectionRef}><p>{"Approved portfolio copy."}</p></section>;
}
"""

    validated = validate_generation_changes(
        generic_types,
        owned_paths=["src/routes/home/**"],
        repo_dir=tmp_path,
        max_file_bytes=10000,
        max_response_bytes=10000,
        allowed_packages={"react"},
        public_text={"Approved portfolio copy."},
    )

    assert validated == generic_types.files

    invented = expression.model_copy(deep=True)
    invented.files[0].complete_utf8_content = (
        "export function Disclosure() { "
        "return <p>This invented portfolio claim is not approved.</p>; }"
    )
    with pytest.raises(SourceValidationError) as exc_info:
        validate_generation_changes(
            invented,
            owned_paths=["src/routes/home/**"],
            repo_dir=tmp_path,
            max_file_bytes=10000,
            max_response_bytes=10000,
            allowed_packages=set(),
            public_text={"Approved portfolio copy."},
        )
    assert exc_info.value.code == "SOURCE_UNGROUNDED_COPY"
    assert "This invented portfolio claim is not approved." in exc_info.value.message


def test_source_changes_reject_trusted_preview_shell_mutation(tmp_path) -> None:
    with pytest.raises(SourceValidationError, match="trusted toolchain"):
        validate_generation_changes(
            GenerationChanges(
                files=[
                    SourceFileChange(
                        path="src/app/AppRouter.tsx",
                        operation="replace",
                        complete_utf8_content="export function AppRouter() { return null; }",
                    )
                ]
            ),
            owned_paths=["src/app/**"],
            repo_dir=tmp_path,
            max_file_bytes=10000,
            max_response_bytes=10000,
            allowed_packages=set(),
            public_text=set(),
        )


def test_source_change_operations_match_repository_state(tmp_path) -> None:
    target = tmp_path / "src" / "existing.ts"
    target.parent.mkdir(parents=True)
    target.write_text("export const oldValue = true;", encoding="utf-8")
    with pytest.raises(SourceValidationError, match="overwrite"):
        validate_generation_changes(
            GenerationChanges(
                files=[
                    SourceFileChange(
                        path="src/existing.ts",
                        operation="create",
                        complete_utf8_content="export const newValue = true;",
                    )
                ]
            ),
            owned_paths=["src/**"],
            repo_dir=tmp_path,
            max_file_bytes=10000,
            max_response_bytes=10000,
            allowed_packages=set(),
            public_text=set(),
        )


def test_prompt_builder_injects_the_normative_generation_contract() -> None:
    _system, instructions, receipt = build_instructions(
        "integrate",
        {
            "context_receipt_hash": "context",
            "generation_contract": {
                "path_rules": {"owned_paths": ["src/app/**"]},
                "runtime_shell": {
                    "router_file": "src/app/AppRouter.tsx",
                    "required_behaviors": ["Render Page not found for unknown paths."],
                },
                "required_coverage": {
                    "content_ids": ["content-a"],
                    "criterion_ids": [],
                    "resource_slot_ids": ["slot-a", "slot-b"],
                    "interaction_ids": [],
                },
            },
        },
    )
    assert "RUNTIME SHELL CONTRACT: src/app/AppRouter.tsx" in instructions
    assert "Render Page not found for unknown paths." in instructions
    assert "V4 SOURCE ENVELOPE COVERAGE" in instructions
    assert 'content_ids = ["content-a"]' in instructions
    assert "criterion_ids = []" in instructions
    assert 'resource_slot_ids = ["slot-a", "slot-b"]' in instructions
    assert "files=[] is invalid" in instructions
    assert receipt.prompt_versions["operation"] == "code_generator.integrate.v6"


def test_prompt_builder_excludes_accepted_mode_for_first_time_generation() -> None:
    """Regression test for the 2026-08-28 bug: two live confirmation runs
    deterministically hit GENERATION_CHANGES_MISSING because route_batch's
    task instructions unconditionally listed mode=accepted as a valid
    choice, undermining the prompt-file guidance not to use it. A
    first-time-generation operation must never see "accepted" listed."""
    for operation in ("route_batch", "route_compose"):
        _system, instructions, _receipt = build_instructions(
            operation, {"context_receipt_hash": "context"}
        )
        assert "changes/requests/cannot_complete" in instructions
        assert "accepted" not in instructions.split("Set mode to exactly one of")[-1].split(";")[0]
        assert "never a valid choice here" in instructions

    for operation in ("integrate", "repair"):
        _system, instructions, _receipt = build_instructions(
            operation, {"context_receipt_hash": "context"}
        )
        assert "changes/requests/cannot_complete" in instructions
        assert "accepted" not in instructions.split("Set mode to exactly one of")[-1].split(";")[0]

        _system, allowed_instructions, _receipt = build_instructions(
            operation,
            {"context_receipt_hash": "context"},
            allow_accepted_result=True,
        )
        assert "changes/requests/accepted/cannot_complete" in allowed_instructions

    # The actual live failure was on the V4 wire envelope (result_tag), not
    # the legacy GenerationResult (mode) path - cover it explicitly.
    _system, v4_instructions, _receipt = build_instructions(
        "route_batch",
        {"context_receipt_hash": "context"},
        output_model=SourceGenerationEnvelopeV2,
    )
    assert "result_tag to exactly one of changes/requests/cannot_complete" in v4_instructions
    assert "never a valid choice here" in v4_instructions


def _accepted_envelope_payload() -> dict[str, object]:
    return {
        "result": "accepted",
        "files": [],
        "exported_signatures": [],
        "content_ids": ["hero"],
        "criterion_ids": [],
        "resource_slot_ids": [],
        "interaction_ids": [],
        "resource_requests": [],
        "dependency_requests": [],
        "failure_details": [],
    }


def test_v4_envelope_rejects_accepted_result_for_first_time_generation() -> None:
    """Regression test for the 2026-08-28 bug: two live confirmation runs
    deterministically returned result="accepted" for a route batch that had
    never been generated before, and strict structured-output schema
    enforcement meant prose-only prompt guidance could not reliably prevent
    it. The schema itself must reject it via validation context, forcing
    the existing schema-correction retry with explicit feedback."""
    with pytest.raises(ValueError, match='result: "accepted" is not valid'):
        SourceGenerationEnvelopeV2.model_validate(
            _accepted_envelope_payload(),
            context={"forbid_accepted_result": True},
        )
    # Without the context flag (e.g. integrate/repair operations), or with
    # it explicitly false, "accepted" remains valid.
    accepted = SourceGenerationEnvelopeV2.model_validate(_accepted_envelope_payload())
    assert accepted.result == "accepted"
    accepted_explicit = SourceGenerationEnvelopeV2.model_validate(
        _accepted_envelope_payload(), context={"forbid_accepted_result": False}
    )
    assert accepted_explicit.result == "accepted"


def test_repair_prompt_treats_unlisted_quality_findings_as_binding() -> None:
    _system, instructions, receipt = build_instructions(
        "repair",
        {"context_receipt_hash": "context"},
    )

    assert "requested_outcome" in instructions
    assert "JSX/HTML source order is authoritative" in instructions
    assert "`order` rule alone does not repair" in instructions
    assert receipt.prompt_versions["operation"] == "code_generator.repair.v8"


def test_final_repair_prompt_forbids_acceptance_after_a_failed_gate() -> None:
    _system, instructions, _receipt = build_instructions(
        "repair",
        {
            "context_receipt_hash": "context",
            "forbid_accepted_result": True,
        },
        output_model=SourceGenerationEnvelopeV2,
    )

    assert "result_tag to exactly one of changes/requests/cannot_complete" in instructions
    assert "result_tag=accepted is forbidden" in instructions


def test_v4_planner_prompt_requires_concrete_responsive_sizes() -> None:
    _system, instructions, receipt = build_instructions("planner_v4", {})

    assert "browser-valid concrete policy" in instructions
    assert "never spell out a number" in instructions
    assert "copy the matching `section_regions[*].region_selector`" in instructions
    assert "BAD `(max-width: sixtyrem) 100vw, 58vw`" in instructions
    assert "shadcn_theme_bindings" in instructions
    assert "primary-foreground" in instructions
    assert receipt.prompt_versions["operation"] == "code_generator.planner.v12"


def test_generation_result_rejects_accepted_mode_for_first_time_generation() -> None:
    payload = {
        "operation_id": "route_batch:unit-1",
        "based_on_context_receipt": "context-hash",
        "mode": "accepted",
        "accepted": {"summary": "nothing to change", "verified_contracts": ["hero"]},
    }
    with pytest.raises(ValueError, match='mode="accepted" is not valid'):
        GenerationResult.model_validate(payload, context={"forbid_accepted_result": True})
    accepted = GenerationResult.model_validate(payload)
    assert accepted.mode == "accepted"
