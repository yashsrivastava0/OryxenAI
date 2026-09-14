from types import SimpleNamespace

import pytest

from oryxenai.agents.code_generator.core.development_schemas import (
    CandidateIdentity,
    Diagnostic,
    GenerationContextReceipt,
    SitePlan,
    SourceCheckpoint,
)
from oryxenai.agents.code_generator.core.final_repair import (
    FinalRepairDeclined,
    FinalRepairer,
)
from oryxenai.agents.code_generator.core.workspace import GenerationWorkspace


@pytest.mark.asyncio
async def test_final_repair_surfaces_shared_semantic_decline_to_separate_budget_policy(
    tmp_path, monkeypatch
) -> None:
    workspace = GenerationWorkspace(
        tmp_path / "workspace", tmp_path / "input", tmp_path / "checkpoints"
    )
    workspace.repo_dir.mkdir(parents=True)
    workspace.ledger_dir.mkdir(parents=True)
    source = workspace.repo_dir / "src/routes/home/index.tsx"
    source.parent.mkdir(parents=True)
    source.write_text("export default function Home() { return null; }\n", encoding="utf-8")
    context_receipt = GenerationContextReceipt(
        receipt_id="context-final-repair",
        operation_id="repair",
        role_profile="repair-profile",
        prompt_versions={"operation_hash": "repair-prompt"},
        output_schema_hash="schema-hash",
        owned_paths=["src/routes/home/index.tsx"],
        context_hash="final-repair-context-hash",
    )

    monkeypatch.setattr(
        "oryxenai.agents.code_generator.core.final_repair.build_generation_contract",
        lambda **_kwargs: {},
    )
    monkeypatch.setattr(
        "oryxenai.agents.code_generator.core.final_repair.build_instructions",
        lambda *_args, **_kwargs: ("system", "instructions", context_receipt),
    )
    monkeypatch.setattr(
        "oryxenai.agents.code_generator.core.final_repair._legacy_deterministic_repair",
        lambda **_kwargs: None,
    )

    class DecliningClient:
        async def generate_structured(self, **_kwargs):
            return SimpleNamespace(
                parsed_output={
                    "operation_id": "code-generator.repair",
                    "based_on_context_receipt": context_receipt.context_hash,
                    "mode": "cannot_complete",
                    "cannot_complete": {
                        "code": "FINAL_SOURCE_AUTHORITY_BOUNDED",
                        "safe_reason": "The bounded files cannot resolve this runtime finding.",
                        "missing_authority_or_capability": "a broader source owner",
                    },
                },
                usage={},
            )

    repairer = FinalRepairer(model_factory=lambda _profile: DecliningClient())
    identity = CandidateIdentity(
        input_receipt_hash="input",
        site_plan_hash="plan",
        work_graph_hash="graph",
        source_checkpoint_hash="checkpoint",
        source_manifest_hash="manifest",
        scaffold_toolchain_profile_hash="toolchain",
        verification_profile_hash="verification",
    )
    checkpoint = SourceCheckpoint(
        checkpoint_id="checkpoint-final",
        checkpoint_hash="checkpoint",
        stored_relative_path="checkpoints/final",
        source_manifest_hash="manifest",
        file_count=1,
        total_bytes=source.stat().st_size,
        work_unit_id="route-home",
        accepted_at="2026-09-11T00:00:00+00:00",
    )
    diagnostic = Diagnostic(
        diagnostic_id="diagnostic-runtime",
        group="dom_runtime",
        code="RUNTIME_REGION_INVALID",
        phase="runtime",
        normalized_message="The expected region is unavailable.",
        file="src/routes/home/index.tsx",
        fingerprint="runtime-fingerprint",
    )
    settings = SimpleNamespace(
        code_generator_generation=SimpleNamespace(
            repair_profile="repair-profile",
            max_response_bytes=2_000_000,
        )
    )

    with pytest.raises(FinalRepairDeclined) as exc_info:
        await repairer.repair(
            settings=settings,
            workspace=workspace,
            checkpoint_store=SimpleNamespace(),
            checkpoint=checkpoint,
            identity=identity,
            plan=SitePlan(plan_id="final-decline", routes=[]),
            projections={
                "resources/ledger.json": {"active_bindings": []},
                "dependencies/ledger.json": {"receipts": []},
            },
            diagnostics=[diagnostic],
            allowed_paths=["src/routes/home/index.tsx"],
            public_text=set(),
            allowed_packages=set(),
            strategy="bounded-correction",
            round_number=1,
        )

    assert exc_info.value.code == "FINAL_REPAIR_DECLINED"
    assert exc_info.value.safe_reason == ("The bounded files cannot resolve this runtime finding.")
