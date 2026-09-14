from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from oryxenai.agents.code_generator.core.development_schemas import (
    DependencyRequest,
    GenerationCallReceipt,
    GenerationCannotComplete,
    GenerationChanges,
    GenerationContextReceipt,
    GenerationProjection,
    GenerationRequestReceipt,
    GenerationRequests,
    GenerationResult,
    GenerationWorkUnitProjection,
    IntegrationReviewV1,
    RoutePlan,
    SitePlan,
    SourceCheckpoint,
    SourceDiagnostic,
    SourceFileChange,
    WorkGraph,
    WorkUnit,
)
from oryxenai.agents.code_generator.core.development_service import (
    _reset_generation_projection_for_explicit_retry,
)
from oryxenai.agents.code_generator.core.generation_orchestrator import (
    CodeGeneratorGenerationOrchestrator,
    GenerationError,
    _build_pending_proposal,
    _pending_files_from_ledger,
    _prepare_resumed_projection,
    _record_call_receipt,
    _record_pending_diagnostics,
    _write_pending_proposal,
)
from oryxenai.agents.code_generator.core.semantic_decline import (
    extract_semantic_source_decline,
)
from oryxenai.agents.code_generator.core.workspace import GenerationWorkspace


def _unit_contract(tmp_path):
    workspace = GenerationWorkspace(
        tmp_path / "workspace", tmp_path / "input", tmp_path / "checkpoints"
    )
    workspace.repo_dir.mkdir(parents=True)
    workspace.ledger_dir.mkdir(parents=True)
    owned_path = "src/routes/home/index.tsx"
    unit = WorkUnit(
        unit_id="route-home",
        kind="route",
        route_id="home",
        route_ids=["home"],
        section_ids=["hero"],
        owns_paths=[owned_path],
    )
    plan = SitePlan(
        plan_id="semantic-decline",
        routes=[
            RoutePlan(
                route_id="home",
                path="/",
                section_ids=["hero"],
                responsive_outcome="stacked",
                reduced_motion_outcome="static",
                interaction_outcome="keyboard accessible",
            )
        ],
        work_graph=WorkGraph(units=[unit]),
    )
    projections = {
        "site/contract.json": {
            "routes": [{"route_id": "home", "path": "/", "storage_key": "home"}],
            "criteria": [],
            "facts": [],
            "public_content": [],
        },
        "design/visual-direction.json": {},
        "resources/ledger.json": {},
        "execution/contract.json": {},
    }
    settings = SimpleNamespace(
        code_generator_generation=SimpleNamespace(
            route_profile="route-profile",
            compose_profile="compose-profile",
            integration_profile="integration-profile",
            repair_profile="repair-profile",
            max_response_bytes=2_000_000,
            max_context_chars=170_000,
            max_request_rounds=1,
            max_source_bytes=2_000_000,
            max_repair_rounds_per_unit=2,
            max_repair_rounds_total=4,
        )
    )
    checkpoint = SourceCheckpoint(
        checkpoint_id="checkpoint-route",
        checkpoint_hash="checkpoint-hash",
        stored_relative_path="checkpoints/route",
        source_manifest_hash="manifest-hash",
        file_count=1,
        total_bytes=1,
        work_unit_id=unit.unit_id,
        accepted_at="2026-09-11T00:00:00+00:00",
    )
    return workspace, unit, plan, projections, settings, checkpoint, owned_path


def _decline(context_hash: str) -> GenerationResult:
    return GenerationResult(
        operation_id="route_batch:route-home",
        based_on_context_receipt=context_hash,
        mode="cannot_complete",
        cannot_complete=GenerationCannotComplete(
            code="SOURCE_AUTHORITY_BOUNDED",
            safe_reason="A complete correction is not available in this bounded context.",
            missing_authority_or_capability="complete source candidate",
        ),
    )


def _changes(context_hash: str, owned_path: str) -> GenerationResult:
    return GenerationResult(
        operation_id="route_batch:route-home",
        based_on_context_receipt=context_hash,
        mode="changes",
        changes=GenerationChanges(
            files=[
                SourceFileChange(
                    path=owned_path,
                    operation="create",
                    complete_utf8_content="export default function Home() { return null; }\n",
                )
            ]
        ),
    )


async def _run_unit(
    *,
    monkeypatch,
    orchestrator,
    workspace,
    unit,
    plan,
    projections,
    settings,
    checkpoint,
    projection,
    results,
):
    calls: list[tuple[str, str, int]] = []

    async def model_result(**kwargs):
        context_hash = str(kwargs["context_receipt"].context_hash)
        calls.append(
            (
                str(kwargs["operation"]),
                str(kwargs["role_profile"]),
                int(kwargs["context"]["repair_round"]),
            )
        )
        result_factory = results[min(len(calls) - 1, len(results) - 1)]
        result = result_factory(context_hash)
        index = len(calls)
        return result, GenerationCallReceipt(
            receipt_id=f"call-{index}",
            operation_id=str(kwargs["operation"]),
            idempotency_key=f"key-{index}",
            context_receipt_hash=context_hash,
            result_hash=f"result-{index}",
            profile=str(kwargs["role_profile"]),
        )

    async def no_diagnostics(*_args, **_kwargs):
        return []

    async def no_op(*_args, **_kwargs):
        return None

    monkeypatch.setattr(orchestrator, "_model_result", model_result)
    monkeypatch.setattr(orchestrator, "_apply_changes", lambda **_kwargs: None)
    monkeypatch.setattr(orchestrator, "_validate_run", no_op)
    monkeypatch.setattr(
        "oryxenai.agents.code_generator.core.generation_orchestrator.run_source_checks",
        no_diagnostics,
    )

    accepted = await orchestrator._run_unit(
        sessionmaker=None,
        run_id=uuid4(),
        settings=settings,
        run=SimpleNamespace(run_mode="development"),
        plan=plan,
        projections=projections,
        workspace=workspace,
        checkpoint_store=SimpleNamespace(accept=lambda **_kwargs: checkpoint),
        projection=projection,
        unit=unit,
        checkpoint=None,
        allowed_packages=set(),
        public_text=set(),
        persist_projection=False,
    )
    return accepted, calls


def test_shared_semantic_decline_extraction_is_caller_neutral() -> None:
    result = _decline("context-hash")

    decline = extract_semantic_source_decline(result)

    assert decline is not None
    assert decline.code == "SOURCE_AUTHORITY_BOUNDED"
    assert decline.safe_reason.startswith("A complete correction")
    assert decline.missing_authority_or_capability == "complete source candidate"
    assert extract_semantic_source_decline(_changes("context-hash", "src/home.tsx")) is None


@pytest.mark.asyncio
async def test_seeded_no_candidate_decline_retries_original_builder(monkeypatch, tmp_path) -> None:
    workspace, unit, plan, projections, settings, checkpoint, owned_path = _unit_contract(tmp_path)
    unit_projection = GenerationWorkUnitProjection(
        unit_id=unit.unit_id,
        kind=unit.kind,
        status="model_requested",
        owned_paths=list(unit.owns_paths),
        repair_round=1,
        next_operation="route_batch",
        next_role_profile="route-profile",
    )
    projection = GenerationProjection(
        generation_id="generation-seeded",
        input_receipt_hash="input",
        site_plan_hash="plan",
        phase="generating_routes",
        work_units=[unit_projection],
        repair_rounds=1,
        repair_budget_used=1,
    )
    orchestrator = CodeGeneratorGenerationOrchestrator()

    accepted, calls = await _run_unit(
        monkeypatch=monkeypatch,
        orchestrator=orchestrator,
        workspace=workspace,
        unit=unit,
        plan=plan,
        projections=projections,
        settings=settings,
        checkpoint=checkpoint,
        projection=projection,
        results=[_decline, lambda context_hash: _changes(context_hash, owned_path)],
    )

    assert accepted == checkpoint
    assert calls == [
        ("route_batch", "route-profile", 1),
        ("route_batch", "route-profile", 2),
    ]
    assert projection.repair_budget_used == 2
    assert projection.repair_rounds == 2
    assert projection.work_units[0].repair_round == 2
    assert [item.code for item in projection.diagnostic_history] == ["SOURCE_AUTHORITY_BOUNDED"]


@pytest.mark.asyncio
async def test_complete_rejected_candidate_decline_stays_on_repair_profile(
    monkeypatch, tmp_path
) -> None:
    workspace, unit, plan, projections, settings, checkpoint, owned_path = _unit_contract(tmp_path)
    candidate_files = {owned_path: "export default function Home() { return <main />; }\n"}
    proposal = _build_pending_proposal(
        workspace=workspace,
        unit=unit,
        owned_paths=list(unit.owns_paths),
        base_checkpoint_hash="base-checkpoint",
        base_repo=workspace.repo_dir,
        files=candidate_files,
        attempt_id="attempt-complete",
        candidate_completeness="complete",
    )
    proposal = _write_pending_proposal(workspace, proposal, candidate_files)
    projection = GenerationProjection(
        generation_id="generation-complete-candidate",
        input_receipt_hash="input",
        site_plan_hash="plan",
        phase="generating_routes",
        work_units=[
            GenerationWorkUnitProjection(
                unit_id=unit.unit_id,
                kind=unit.kind,
                status="model_requested",
                owned_paths=list(unit.owns_paths),
                repair_round=1,
                next_operation="repair",
                next_role_profile="repair-profile",
                pending_proposal=proposal,
            )
        ],
        repair_rounds=1,
        repair_budget_used=1,
    )
    orchestrator = CodeGeneratorGenerationOrchestrator()

    accepted, calls = await _run_unit(
        monkeypatch=monkeypatch,
        orchestrator=orchestrator,
        workspace=workspace,
        unit=unit,
        plan=plan,
        projections=projections,
        settings=settings,
        checkpoint=checkpoint,
        projection=projection,
        results=[_decline, lambda context_hash: _changes(context_hash, owned_path)],
    )

    assert accepted == checkpoint
    assert calls == [
        ("repair", "repair-profile", 1),
        ("repair", "repair-profile", 2),
    ]
    assert projection.repair_budget_used == 2


@pytest.mark.asyncio
async def test_semantic_declines_stop_at_existing_per_unit_repair_ceiling(
    monkeypatch, tmp_path
) -> None:
    workspace, unit, plan, projections, settings, checkpoint, _owned_path = _unit_contract(tmp_path)
    projection = GenerationProjection(
        generation_id="generation-decline-ceiling",
        input_receipt_hash="input",
        site_plan_hash="plan",
        phase="generating_routes",
        work_units=[
            GenerationWorkUnitProjection(
                unit_id=unit.unit_id,
                kind=unit.kind,
                status="context_ready",
                owned_paths=list(unit.owns_paths),
            )
        ],
    )
    orchestrator = CodeGeneratorGenerationOrchestrator()

    with pytest.raises(GenerationError) as exc_info:
        await _run_unit(
            monkeypatch=monkeypatch,
            orchestrator=orchestrator,
            workspace=workspace,
            unit=unit,
            plan=plan,
            projections=projections,
            settings=settings,
            checkpoint=checkpoint,
            projection=projection,
            results=[_decline],
        )

    assert exc_info.value.code == "SOURCE_REPAIR_EXHAUSTED"
    assert projection.repair_budget_used == 2
    assert projection.work_units[0].repair_round == 2
    assert len(projection.diagnostics) == 1
    assert len(projection.call_receipts) == 3


@pytest.mark.asyncio
async def test_model_result_cache_replay_keeps_one_logical_call_receipt(tmp_path) -> None:
    workspace = GenerationWorkspace(
        tmp_path / "workspace", tmp_path / "input", tmp_path / "checkpoints"
    )
    workspace.ledger_dir.mkdir(parents=True)
    context_receipt = GenerationContextReceipt(
        receipt_id="context-cache",
        operation_id="route_batch",
        role_profile="route-profile",
        prompt_versions={"operation_hash": "prompt-hash"},
        output_schema_hash="schema-hash",
        context_hash="context-hash",
    )
    generated = _changes(context_receipt.context_hash, "src/routes/home/index.tsx")

    class Client:
        def __init__(self) -> None:
            self.calls = 0

        async def generate_structured(self, **_kwargs):
            self.calls += 1
            return SimpleNamespace(
                parsed_output=generated.model_dump(mode="json"),
                response_id=f"response-{self.calls}",
                model="test-model",
                usage={},
                finish_reason="stop",
            )

    client = Client()
    orchestrator = CodeGeneratorGenerationOrchestrator(model_factory=lambda _profile: client)
    settings = SimpleNamespace()
    kwargs = {
        "settings": settings,
        "operation": "route_batch",
        "role_profile": "route-profile",
        "context": {},
        "system": "system",
        "instructions": "instructions",
        "context_receipt": context_receipt,
        "workspace": workspace,
        "generation_id": "generation-cache",
        "unit_id": "route-home",
        "request_round": 0,
    }

    first_result, first_receipt = await orchestrator._model_result(**kwargs)
    second_result, second_receipt = await orchestrator._model_result(**kwargs)

    assert first_result == second_result
    assert client.calls == 1
    assert second_receipt.retry_class == "cache_hit"
    assert first_receipt.receipt_id == second_receipt.receipt_id
    assert first_receipt.idempotency_key == second_receipt.idempotency_key

    retry_result, retry_receipt = await orchestrator._model_result(**{**kwargs, "attempt_epoch": 1})
    projection = GenerationProjection(
        generation_id="generation-cache",
        input_receipt_hash="input",
        site_plan_hash="plan",
        phase="generating_routes",
    )
    _record_call_receipt(projection, first_receipt)
    _record_call_receipt(projection, second_receipt)
    _record_call_receipt(projection, retry_receipt)

    assert retry_result == first_result
    assert client.calls == 2
    assert retry_receipt.retry_class == ""
    assert retry_receipt.receipt_id != first_receipt.receipt_id
    assert retry_receipt.idempotency_key != first_receipt.idempotency_key
    assert len(projection.call_receipts) == 2


def test_projection_preparation_distinguishes_redelivery_from_explicit_retry() -> None:
    diagnostic = SourceDiagnostic(
        diagnostic_id="diagnostic-active",
        group="source_contract",
        code="SOURCE_ACTIVE",
        phase="source_generation",
        normalized_message="active retry context",
        work_unit_id="route-home",
        fingerprint="active-fingerprint",
    )
    projection = GenerationProjection(
        generation_id="generation-redelivery",
        input_receipt_hash="input",
        site_plan_hash="plan",
        phase="generating_routes",
        diagnostics=[diagnostic],
        work_units=[
            GenerationWorkUnitProjection(
                unit_id="route-home",
                kind="route",
                status="model_requested",
                repair_round=1,
                next_operation="repair",
                next_role_profile="repair-profile",
                diagnostics=[diagnostic.diagnostic_id],
            )
        ],
    )
    explicit_retry = projection.model_copy(deep=True)

    assert _prepare_resumed_projection(projection, entry_status="acquiring") is True
    assert projection.diagnostics == [diagnostic]
    assert projection.work_units[0].diagnostics == [diagnostic.diagnostic_id]
    assert projection.work_units[0].repair_round == 1
    assert projection.work_units[0].next_operation == "repair"

    assert _prepare_resumed_projection(explicit_retry, entry_status="queued") is False
    assert explicit_retry.diagnostics == []
    assert explicit_retry.diagnostic_history == [diagnostic]
    assert explicit_retry.work_units[0].diagnostics == []


def test_explicit_retry_resets_transient_checkpointed_owner_state(tmp_path) -> None:
    workspace, unit, _plan, _projections, _settings, checkpoint, owned_path = _unit_contract(
        tmp_path
    )
    request_receipt = GenerationRequestReceipt(
        unit_id=unit.unit_id,
        context_receipt_hash="request-context",
        request_round=0,
        next_request_round=1,
        requests=GenerationRequests(),
    )
    pending_proposal = _build_pending_proposal(
        workspace=workspace,
        unit=unit,
        owned_paths=unit.owns_paths,
        base_checkpoint_hash=checkpoint.checkpoint_hash,
        base_repo=workspace.repo_dir,
        files={owned_path: "export default function Rejected() { return null; }\n"},
        attempt_id="rejected-attempt",
        candidate_completeness="complete",
        diagnostic_ids=["diagnostic-route"],
    )
    projection = GenerationProjection(
        generation_id="generation-explicit-retry",
        attempt_epoch=2,
        input_receipt_hash="input",
        site_plan_hash="plan",
        phase="integrating",
        accepted_checkpoint=checkpoint,
        repair_rounds=3,
        repair_budget_used=3,
        repair_fingerprint_counts={"fingerprint": 2},
        repair_strategies=["repair:route-home"],
        request_rounds=1,
        work_units=[
            GenerationWorkUnitProjection(
                unit_id=unit.unit_id,
                kind=unit.kind,
                status="checkpointed",
                owned_paths=list(unit.owns_paths),
                checkpoint_before="checkpoint-before",
                checkpoint_after=checkpoint.checkpoint_hash,
                call_receipt_id="call-before-retry",
                request_round=1,
                request_receipt_ids=[request_receipt.receipt_id],
                pending_request=request_receipt,
                repair_round=2,
                next_operation="repair",
                next_role_profile="repair-profile",
                diagnostics=["diagnostic-route"],
                pending_proposal=pending_proposal,
            )
        ],
    )

    reset = GenerationProjection.model_validate(
        _reset_generation_projection_for_explicit_retry(projection.model_dump(mode="json"))
    )
    reset_unit = reset.work_units[0]

    assert reset.attempt_epoch == 3
    assert reset.accepted_checkpoint == checkpoint
    assert reset.request_rounds == 1
    assert reset.repair_rounds == 0
    assert reset.repair_budget_used == 0
    assert reset.repair_fingerprint_counts == {}
    assert reset.repair_strategies == []
    assert reset_unit.status == "checkpointed"
    assert reset_unit.checkpoint_before == "checkpoint-before"
    assert reset_unit.checkpoint_after == checkpoint.checkpoint_hash
    assert reset_unit.call_receipt_id == "call-before-retry"
    assert reset_unit.request_receipt_ids == [request_receipt.receipt_id]
    assert reset_unit.request_round == 0
    assert reset_unit.pending_request is None
    assert reset_unit.repair_round == 0
    assert reset_unit.next_operation == ""
    assert reset_unit.next_role_profile == ""
    assert reset_unit.diagnostics == []
    assert reset_unit.pending_proposal is None


@pytest.mark.asyncio
async def test_legacy_acquisition_replay_consumes_existing_round_credit(
    monkeypatch, tmp_path
) -> None:
    workspace, unit, plan, projections, settings, checkpoint, owned_path = _unit_contract(tmp_path)
    unit_projection = GenerationWorkUnitProjection(
        unit_id=unit.unit_id,
        kind=unit.kind,
        status="needs_resources",
        owned_paths=list(unit.owns_paths),
    )
    projection = GenerationProjection(
        generation_id="generation-legacy-acquisition",
        input_receipt_hash="input",
        site_plan_hash="plan",
        phase="generating_routes",
        active_work_unit_id=unit.unit_id,
        request_rounds=1,
        work_units=[unit_projection],
    )

    assert _prepare_resumed_projection(projection, entry_status="acquiring") is True
    assert unit_projection.legacy_request_count_credit == 1

    orchestrator = CodeGeneratorGenerationOrchestrator()
    model_calls = 0

    async def model_result(**kwargs):
        nonlocal model_calls
        model_calls += 1
        context_hash = str(kwargs["context_receipt"].context_hash)
        if model_calls == 1:
            result = GenerationResult(
                operation_id="route_batch:route-home",
                based_on_context_receipt=context_hash,
                mode="requests",
                requests=GenerationRequests(
                    dependency_requests=[
                        DependencyRequest(
                            request_id="legacy-dependency",
                            requesting_resource_receipt_hash="resource-receipt",
                            package_name="lucide-react",
                            required_api_or_exports=["Heart"],
                            compatibility_constraints="react-vite-v1",
                            reason_existing_stack_is_insufficient=(
                                "The generated route references the approved icon API."
                            ),
                            fallback_component_strategy="Use a local text glyph.",
                        )
                    ]
                ),
            )
        else:
            result = _changes(context_hash, owned_path)
        return result, GenerationCallReceipt(
            receipt_id=f"legacy-call-{model_calls}",
            operation_id=str(kwargs["operation"]),
            idempotency_key=f"legacy-key-{model_calls}",
            context_receipt_hash=context_hash,
            result_hash=f"legacy-result-{model_calls}",
            profile=str(kwargs["role_profile"]),
            retry_class="cache_hit" if model_calls == 1 else "",
        )

    async def no_op(*_args, **_kwargs):
        return None

    async def no_diagnostics(*_args, **_kwargs):
        return []

    monkeypatch.setattr(orchestrator, "_model_result", model_result)
    monkeypatch.setattr(orchestrator, "_persist", no_op)
    monkeypatch.setattr(orchestrator, "_resolve_requests", no_op)
    monkeypatch.setattr(orchestrator, "_validate_run", no_op)
    monkeypatch.setattr(orchestrator, "_apply_changes", lambda **_kwargs: None)
    monkeypatch.setattr(
        "oryxenai.agents.code_generator.core.generation_orchestrator.run_source_checks",
        no_diagnostics,
    )

    accepted = await orchestrator._run_unit(
        sessionmaker=None,
        run_id=uuid4(),
        settings=settings,
        run=SimpleNamespace(run_mode="development"),
        plan=plan,
        projections=projections,
        workspace=workspace,
        checkpoint_store=SimpleNamespace(accept=lambda **_kwargs: checkpoint),
        projection=projection,
        unit=unit,
        checkpoint=None,
        allowed_packages=set(),
        public_text=set(),
        persist_projection=True,
    )

    assert accepted == checkpoint
    assert model_calls == 2
    assert projection.request_rounds == 1
    assert unit_projection.legacy_request_count_credit == 0
    assert unit_projection.request_round == 1
    assert unit_projection.pending_request is None
    assert len(unit_projection.request_receipt_ids) == 1


def test_pending_diagnostic_successor_preserves_persisted_predecessor(tmp_path) -> None:
    workspace, unit, _plan, _projections, _settings, checkpoint, owned_path = _unit_contract(
        tmp_path
    )
    files = {owned_path: "export default function Candidate() { return null; }\n"}
    initial = _write_pending_proposal(
        workspace,
        _build_pending_proposal(
            workspace=workspace,
            unit=unit,
            owned_paths=unit.owns_paths,
            base_checkpoint_hash=checkpoint.checkpoint_hash,
            base_repo=workspace.repo_dir,
            files=files,
            attempt_id="pending-initial",
        ),
        files,
    )
    persisted_projection = GenerationWorkUnitProjection(
        unit_id=unit.unit_id,
        kind=unit.kind,
        status="model_requested",
        owned_paths=list(unit.owns_paths),
        pending_proposal=initial,
    )
    resumed_projection = persisted_projection.model_copy(deep=True)
    predecessor_path = workspace.root / initial.stored_relative_path

    _record_pending_diagnostics(
        workspace,
        unit=unit,
        projection=resumed_projection,
        files=files,
        diagnostic_ids=["diagnostic-successor"],
    )

    assert resumed_projection.pending_proposal is not None
    successor_path = workspace.root / resumed_projection.pending_proposal.stored_relative_path
    assert successor_path != predecessor_path
    assert predecessor_path.is_file()
    assert successor_path.is_file()
    assert persisted_projection.pending_proposal is not None
    assert persisted_projection.pending_proposal.diagnostic_ids == []
    assert resumed_projection.pending_proposal.diagnostic_ids == ["diagnostic-successor"]
    assert _pending_files_from_ledger(workspace, unit, persisted_projection) == files
    assert _pending_files_from_ledger(workspace, unit, resumed_projection) == files


def test_original_operation_replacement_preserves_db_referenced_proposal(tmp_path) -> None:
    workspace, unit, plan, projections, settings, checkpoint, owned_path = _unit_contract(tmp_path)
    settings.code_generator_generation.max_file_bytes = 100_000
    predecessor_files = {
        owned_path: "export default function RejectedCandidate() { return null; }\n"
    }
    predecessor = _write_pending_proposal(
        workspace,
        _build_pending_proposal(
            workspace=workspace,
            unit=unit,
            owned_paths=unit.owns_paths,
            base_checkpoint_hash=checkpoint.checkpoint_hash,
            base_repo=workspace.repo_dir,
            files=predecessor_files,
            attempt_id="pending-before-replacement",
        ),
        predecessor_files,
    )
    persisted_projection = GenerationWorkUnitProjection(
        unit_id=unit.unit_id,
        kind=unit.kind,
        status="model_requested",
        owned_paths=list(unit.owns_paths),
        pending_proposal=predecessor,
    )
    in_memory_projection = persisted_projection.model_copy(deep=True)
    predecessor_path = workspace.root / predecessor.stored_relative_path
    replacement = _changes("replacement-context", owned_path)

    successor = CodeGeneratorGenerationOrchestrator()._apply_changes(
        changes=replacement.changes,
        unit=unit,
        plan=plan,
        projections=projections,
        workspace=workspace,
        allowed_packages=set(),
        public_text=set(),
        settings=settings,
        checkpoint=checkpoint,
        operation="route_batch",
        pending_files={},
        pending_projection=in_memory_projection,
        replace_pending_proposal=True,
        attempt_id="replacement-attempt",
    )

    assert successor is not None
    assert in_memory_projection.pending_proposal == successor
    successor_path = workspace.root / successor.stored_relative_path
    assert successor_path != predecessor_path
    assert predecessor_path.is_file()
    assert successor_path.is_file()
    assert _pending_files_from_ledger(workspace, unit, persisted_projection) == predecessor_files
    assert _pending_files_from_ledger(workspace, unit, in_memory_projection) == {
        owned_path: replacement.changes.files[0].complete_utf8_content
    }


@pytest.mark.asyncio
async def test_integration_review_replay_deduplicates_within_epoch_and_separates_retry(
    monkeypatch, tmp_path
) -> None:
    workspace, unit, plan, projections, settings, _checkpoint, owned_path = _unit_contract(tmp_path)
    settings.code_generator_generation.quality_review_max_context_chars = 1_000_000
    source_path = workspace.repo_dir / owned_path
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("export default function Home() { return null; }\n", encoding="utf-8")
    review = IntegrationReviewV1(
        status="accepted",
        distinctiveness_score=4,
        composition_score=4,
        typography_score=4,
        resource_fit_score=4,
        motion_score=4,
    )
    retry_review = review.model_copy(
        update={
            "distinctiveness_score": 5,
            "composition_score": 5,
        }
    )
    review_context_receipt = GenerationContextReceipt(
        receipt_id="context-integration-review",
        operation_id="integration_review",
        role_profile="integration-profile",
        prompt_versions={"operation_hash": "integration-prompt"},
        output_schema_hash="integration-schema",
        context_hash="integration-context-hash",
    )
    raw = SimpleNamespace(
        response_id="integration-response",
        model="test-model",
        usage={"input_tokens": 10},
        finish_reason="stop",
        latency_ms=5,
    )
    operation_calls = 0

    async def integration_review_operation(*_args, **_kwargs):
        nonlocal operation_calls
        operation_calls += 1
        returned_review = review if operation_calls <= 2 else retry_review
        return returned_review, review_context_receipt, raw

    async def no_op(*_args, **_kwargs):
        return None

    monkeypatch.setattr(
        "oryxenai.agents.code_generator.core.generation_orchestrator.run_integration_review_operation",
        integration_review_operation,
    )
    orchestrator = CodeGeneratorGenerationOrchestrator(
        model_factory=lambda _profile: SimpleNamespace()
    )
    monkeypatch.setattr(orchestrator, "_validate_run", no_op)
    projection = GenerationProjection(
        generation_id="generation-integration-replay",
        input_receipt_hash="input",
        site_plan_hash="plan",
        phase="integrating",
        work_units=[
            GenerationWorkUnitProjection(
                unit_id=unit.unit_id,
                kind=unit.kind,
                status="checkpointed",
                owned_paths=list(unit.owns_paths),
            )
        ],
    )
    kwargs = {
        "sessionmaker": None,
        "run_id": uuid4(),
        "settings": settings,
        "run": SimpleNamespace(creative_direction={}),
        "plan": plan,
        "projections": projections,
        "workspace": workspace,
        "projection": projection,
        "round_number": 0,
        "persist": False,
    }

    first_review = await orchestrator._integration_review(**kwargs)
    second_review = await orchestrator._integration_review(**kwargs)

    assert first_review == second_review == review
    assert operation_calls == 2
    assert [item.receipt_id for item in projection.context_receipts] == [
        review_context_receipt.receipt_id
    ]
    assert len(projection.call_receipts) == 1
    assert len(projection.attempt_records) == 1

    projection.attempt_epoch = 1
    explicit_retry_review = await orchestrator._integration_review(**kwargs)

    assert explicit_retry_review == retry_review
    assert operation_calls == 3
    assert len(projection.context_receipts) == 1
    assert len(projection.call_receipts) == 2
    assert len({item.receipt_id for item in projection.call_receipts}) == 2
    assert len({item.idempotency_key for item in projection.call_receipts}) == 2
    assert len(projection.attempt_records) == 2
    assert len({item.attempt_id for item in projection.attempt_records}) == 2
    assert {item.status for item in projection.attempt_records} == {"succeeded"}
    assert {item.call_receipt_id for item in projection.attempt_records} == {
        item.receipt_id for item in projection.call_receipts
    }
