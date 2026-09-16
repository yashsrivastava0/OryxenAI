"""Unit and property-based tests for `service.py`'s `_compute_stage_estimate`.

Scoped narrowly to `design.md`'s Fix Implementation item 3: a backend-only,
non-fabricated `stage_estimate` sub-object computed inside
`CodeGeneratorService.get_state()`. `_compute_stage_estimate` itself is a
pure, DB-free, service-free function (no `CodeGeneratorService` instance,
no repository, no database session is constructed anywhere in this file) so
these tests exercise it directly, matching this codebase's own precedent in
`test_build_runner.py`'s `_run()` unit tests and
`tests/unit/agents/visual_design_director/test_service.py`'s convention of
testing pure service-module helpers standalone.

This codebase has no Hypothesis (or other dedicated property-based testing
library) dependency anywhere today (confirmed by a repository-wide grep).
`TestNoFabricationProperty` below follows this codebase's own existing
"property-based test" convention instead: a plain pytest test that iterates
many randomized, seeded input combinations and asserts an invariant holds
for every one of them (the same shape already used by, e.g.,
`test_model_routing_policy.py`'s multi-input loops), rather than introducing
a new test dependency for this one bugfix.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

# Reuses this sibling test module's own fake repository/jobs/fixture helpers
# (`_Repository`, `_Jobs`, `_ready_preparation`) rather than re-declaring an
# equivalent fake, matching this codebase's existing convention of one
# canonical fake-repository shape per agent's test suite.
from tests.unit.agents.code_generator.test_session_service import (
    _Jobs,
    _ready_preparation,
    _Repository,
)

from oryxenai.agents.code_generator.service import (
    _STAGE_ORDER,
    CodeGeneratorService,
    _compute_stage_estimate,
)
from oryxenai.agents.code_generator.session_schemas import CodeGeneratorSessionState
from oryxenai.core.settings import Settings, get_settings


def _configured_budget_ms(kind: str) -> float:
    """The real, committed `config/app.toml` budget for one `code_generator.*`
    `kind_timeouts` key, via the same `WorkerJobConfig.timeout_for` the
    production code path uses -- never a value invented by this test file."""

    return get_settings().worker_job.timeout_for(kind) * 1000.0


class TestConfiguredBudgetSource:
    """`source == "configured_budget"` only when zero `stage_durations_ms`
    entries exist for this run (Preservation Requirements 3.1: additive-only,
    degrades gracefully for a session with no observed-duration data)."""

    def test_empty_stage_durations_uses_configured_budget_source(self) -> None:
        estimate = _compute_stage_estimate(
            stage_durations_ms={},
            created_at=datetime.now(UTC),
            now=datetime.now(UTC),
            timeout_for=get_settings().worker_job.timeout_for,
        )
        assert estimate["source"] == "configured_budget"

    def test_none_stage_durations_uses_configured_budget_source(self) -> None:
        """A fresh run row before task 2's coordinator has ever written an
        entry -- `stage_durations_ms` may be `None`/missing entirely, not
        just an empty dict. Must degrade gracefully, not raise."""

        estimate = _compute_stage_estimate(
            stage_durations_ms=None,
            created_at=datetime.now(UTC),
            now=datetime.now(UTC),
            timeout_for=get_settings().worker_job.timeout_for,
        )
        assert estimate["source"] == "configured_budget"

    def test_all_budget_total_equals_exact_sum_of_configured_kind_timeouts(self) -> None:
        """The all-budget case's `estimated_total_ms` must equal the exact
        sum of the four real `code_generator.*` `kind_timeouts` entries --
        never a value not traceable to `config/app.toml`."""

        expected_total_ms = (
            _configured_budget_ms("code_generator.plan")
            + _configured_budget_ms("code_generator.acquire")
            + _configured_budget_ms("code_generator.generate")
            + _configured_budget_ms("code_generator.verify_and_preview")
        )

        estimate = _compute_stage_estimate(
            stage_durations_ms={},
            created_at=datetime.now(UTC),
            now=datetime.now(UTC),
            timeout_for=get_settings().worker_job.timeout_for,
        )

        assert estimate["estimated_total_ms"] == int(expected_total_ms)

    def test_stage_verify_maps_to_verify_and_preview_config_key(self) -> None:
        """`stage_durations_ms`'s stage-name vocabulary ("verify") and
        `kind_timeouts`'s dotted-key vocabulary ("code_generator.verify_and_
        preview") diverge on exactly this one stage; the mapping must use
        the correct key, not a naive `f"code_generator.{stage}"` concat."""

        seen_kinds: list[str] = []

        def recording_timeout_for(kind: str) -> float:
            seen_kinds.append(kind)
            return 1.0

        _compute_stage_estimate(
            stage_durations_ms={},
            created_at=datetime.now(UTC),
            now=datetime.now(UTC),
            timeout_for=recording_timeout_for,
        )

        assert "code_generator.verify_and_preview" in seen_kinds
        assert "code_generator.verify" not in seen_kinds


class TestObservedAndBudgetSource:
    """`source == "observed_and_budget"` when at least one stage has a
    recorded duration, even if others still fall back to configured
    budgets."""

    def test_single_observed_stage_flips_source(self) -> None:
        estimate = _compute_stage_estimate(
            stage_durations_ms={"plan": 60_000.0},
            created_at=datetime.now(UTC),
            now=datetime.now(UTC),
            timeout_for=lambda _kind: 100.0,
        )
        assert estimate["source"] == "observed_and_budget"

    def test_observed_stage_uses_observed_value_not_configured_budget(self) -> None:
        """When `plan` has an observed duration, its contribution to
        `estimated_total_ms` must be the *observed* value, not the
        configured budget -- otherwise the "observed" half of the mix is
        fake."""

        observed_plan_ms = 42_000.0
        configured_budget_ms = 999_000.0  # deliberately different from observed

        estimate = _compute_stage_estimate(
            stage_durations_ms={"plan": observed_plan_ms},
            created_at=datetime.now(UTC),
            now=datetime.now(UTC),
            timeout_for=lambda _kind: configured_budget_ms / 1000.0,
        )

        # plan observed (42_000) + acquire/generate/verify each budget (999_000)
        expected_total_ms = observed_plan_ms + 3 * configured_budget_ms
        assert estimate["estimated_total_ms"] == int(expected_total_ms)

    def test_all_four_stages_observed_never_falls_back_to_budget(self) -> None:
        durations = {"plan": 1_000.0, "acquire": 2_000.0, "generate": 3_000.0, "verify": 4_000.0}

        def failing_timeout_for(_kind: str) -> float:
            raise AssertionError("must not consult configured budget when all stages observed")

        estimate = _compute_stage_estimate(
            stage_durations_ms=durations,
            created_at=datetime.now(UTC),
            now=datetime.now(UTC),
            timeout_for=failing_timeout_for,
        )

        assert estimate["source"] == "observed_and_budget"
        assert estimate["estimated_total_ms"] == 10_000


class TestElapsedAndRemainingArithmetic:
    """Exact arithmetic for `elapsed_ms`/`estimated_remaining_ms`, including
    the non-negative clamp (Preservation: no fabricated negative values)."""

    def test_elapsed_ms_derived_from_created_at_to_now(self) -> None:
        created_at = datetime.now(UTC) - timedelta(seconds=30)
        now = datetime.now(UTC)

        estimate = _compute_stage_estimate(
            stage_durations_ms={},
            created_at=created_at,
            now=now,
            timeout_for=lambda _kind: 0.0,
        )

        # ~30_000ms elapsed; allow small tolerance for test wall-clock noise.
        assert 29_500 <= estimate["elapsed_ms"] <= 30_500

    def test_remaining_is_total_minus_elapsed(self) -> None:
        # Fixed, exact-millisecond delta (rather than a real `datetime.now()`
        # gap) so the pre-truncation arithmetic is exactly representable and
        # this assertion needs no floating-point/rounding tolerance.
        now = datetime(2026, 1, 1, tzinfo=UTC)
        created_at = now - timedelta(milliseconds=10_000)

        estimate = _compute_stage_estimate(
            stage_durations_ms={},
            created_at=created_at,
            now=now,
            timeout_for=lambda _kind: 100.0,  # 100s per stage * 4 stages = 400_000ms total
        )

        assert estimate["estimated_total_ms"] == 400_000
        assert estimate["elapsed_ms"] == 10_000
        assert estimate["estimated_remaining_ms"] == 390_000

    def test_remaining_clamped_to_zero_when_elapsed_exceeds_total(self) -> None:
        created_at = datetime.now(UTC) - timedelta(hours=10)
        now = datetime.now(UTC)

        estimate = _compute_stage_estimate(
            stage_durations_ms={},
            created_at=created_at,
            now=now,
            timeout_for=lambda _kind: 1.0,  # tiny total budget, long elapsed
        )

        assert estimate["estimated_remaining_ms"] == 0

    def test_none_created_at_degrades_to_zero_elapsed_without_raising(self) -> None:
        """A run row somehow missing even `created_at` must not raise --
        this is the same defensive posture `getattr(..., None)` establishes
        at the call site in `service.py::get_state`."""

        estimate = _compute_stage_estimate(
            stage_durations_ms={},
            created_at=None,
            now=datetime.now(UTC),
            timeout_for=lambda _kind: 10.0,
        )

        assert estimate["elapsed_ms"] == 0
        assert estimate["estimated_remaining_ms"] == estimate["estimated_total_ms"]


class TestResponseShape:
    """Exact key set design.md specifies -- no extra keys, no missing keys."""

    def test_returns_exactly_the_four_documented_keys(self) -> None:
        estimate = _compute_stage_estimate(
            stage_durations_ms={},
            created_at=datetime.now(UTC),
            now=datetime.now(UTC),
            timeout_for=lambda _kind: 1.0,
        )

        assert set(estimate.keys()) == {
            "elapsed_ms",
            "estimated_total_ms",
            "estimated_remaining_ms",
            "source",
        }

    def test_all_numeric_fields_are_plain_ints(self) -> None:
        estimate = _compute_stage_estimate(
            stage_durations_ms={"plan": 1234.5},
            created_at=datetime.now(UTC) - timedelta(seconds=5),
            now=datetime.now(UTC),
            timeout_for=lambda _kind: 2.0,
        )

        assert isinstance(estimate["elapsed_ms"], int)
        assert isinstance(estimate["estimated_total_ms"], int)
        assert isinstance(estimate["estimated_remaining_ms"], int)
        assert estimate["source"] in {"configured_budget", "observed_and_budget"}


class TestNoFabricationProperty:
    """Property 3 (design.md): the estimated-time value is always exactly
    reconstructible from real sources -- never a fabricated constant.

    **Validates: Requirements 2.4**

    This codebase has no Hypothesis dependency; this test follows this
    project's own existing convention for a property-style check -- iterate
    many random, seeded input combinations in a plain loop and assert the
    invariant holds for every one, rather than adding a new test library
    for this one bugfix.
    """

    def test_estimated_total_always_equals_sum_of_observed_plus_configured_budget(self) -> None:
        rng = random.Random(20260914)  # noqa: S311 - deterministic test seed, not cryptographic

        for _trial in range(200):
            # Randomly choose which subset of the 4 stages has an observed
            # duration (0 to 4 populated), each a random non-negative value.
            observed_stage_count = rng.randint(0, len(_STAGE_ORDER))
            observed_stages = set(rng.sample(list(_STAGE_ORDER), observed_stage_count))

            stage_durations_ms: dict[str, float] = {
                stage: rng.uniform(0.0, 10_000_000.0) for stage in observed_stages
            }

            # Random configured budgets (seconds) for every stage -- only the
            # ones NOT in `observed_stages` should actually be consulted by
            # the function, but generate one for every stage anyway so a
            # bug that mistakenly falls back for an observed stage would
            # still be caught by the assertion below.
            configured_budgets_seconds: dict[str, float] = {
                stage: rng.uniform(0.0, 10_000.0) for stage in _STAGE_ORDER
            }

            def timeout_for(kind: str, _budgets=configured_budgets_seconds) -> float:
                # Reverse the exact mapping under test so this fake config
                # source is keyed the same way `config/app.toml` really is.
                reverse_map = {
                    "code_generator.plan": "plan",
                    "code_generator.acquire": "acquire",
                    "code_generator.generate": "generate",
                    "code_generator.verify_and_preview": "verify",
                }
                return _budgets[reverse_map[kind]]

            estimate = _compute_stage_estimate(
                stage_durations_ms=stage_durations_ms,
                created_at=datetime.now(UTC),
                now=datetime.now(UTC),
                timeout_for=timeout_for,
            )

            expected_total_ms = sum(
                max(0.0, stage_durations_ms[stage]) for stage in observed_stages
            ) + sum(
                max(0.0, configured_budgets_seconds[stage] * 1000.0)
                for stage in _STAGE_ORDER
                if stage not in observed_stages
            )

            assert estimate["estimated_total_ms"] == int(expected_total_ms), (
                f"trial with observed_stages={observed_stages!r}, "
                f"stage_durations_ms={stage_durations_ms!r}, "
                f"configured_budgets_seconds={configured_budgets_seconds!r}: "
                f"expected {int(expected_total_ms)}, got {estimate['estimated_total_ms']}"
            )

            expected_source = "observed_and_budget" if observed_stages else "configured_budget"
            assert estimate["source"] == expected_source

    def test_never_produces_a_value_absent_from_either_source_across_random_trials(self) -> None:
        """A stronger restatement of the same invariant: for every trial,
        `estimated_total_ms` must be expressible as a sum drawn only from
        the two allowed sources -- there is no third, unaccounted-for
        contribution (i.e., no fabricated constant is silently added)."""

        rng = random.Random(9)  # noqa: S311 - deterministic test seed, not cryptographic

        for _trial in range(200):
            observed_stages = set(rng.sample(list(_STAGE_ORDER), rng.randint(0, len(_STAGE_ORDER))))
            stage_durations_ms = {stage: rng.uniform(0.0, 500_000.0) for stage in observed_stages}
            budget_seconds = rng.uniform(0.0, 5_000.0)

            estimate = _compute_stage_estimate(
                stage_durations_ms=stage_durations_ms,
                created_at=datetime.now(UTC),
                now=datetime.now(UTC),
                timeout_for=lambda _kind, _b=budget_seconds: _b,
            )

            observed_sum_ms = sum(stage_durations_ms.values())
            incomplete_count = len(_STAGE_ORDER) - len(observed_stages)
            allowed_total_ms = observed_sum_ms + incomplete_count * budget_seconds * 1000.0

            assert estimate["estimated_total_ms"] == int(allowed_total_ms)


class TestGetStateEndToEndPreservation:
    """Exercises the real `CodeGeneratorService.get_state()` (not just the
    pure `_compute_stage_estimate` helper) using this agent's own existing
    fake-repository fixtures from `test_session_service.py`, to directly
    confirm Preservation Requirements 3.1: no existing `payload["progress"]`
    key changes value or is removed by this addition, and the new
    `stage_estimate` sub-object is present and well-formed on a real call."""

    @pytest.mark.asyncio
    async def test_stage_estimate_is_additive_alongside_every_existing_progress_key(self) -> None:
        session_id = uuid4()
        repository = _Repository(session_id, _ready_preparation())
        jobs = _Jobs()
        run = SimpleNamespace(
            id=uuid4(),
            revision=3,
            status="generating",
            issues=[],
            terminal_failure=None,
            active_preview=None,
            coordinator_stage="generate",
            current_attempt=1,
            active_attempt_id=None,
            plan_summary={"routes": 5},
            source_summary={"files_written": 12},
            plan=None,
            planner_receipt=None,
            acquire_receipt=None,
            resource_ledger=None,
            dependency_ledger=None,
            source_checkpoint=None,
            generation_projection=None,
            creative_direction={},
            pipeline_contract_version="code-generator-v4",
            trace_id="trace-progress-preservation",
            background_job_id=jobs.job.id,
            acquire_job_id=None,
            generation_job_id=None,
            verification_job_id=None,
            # The new field this task wires up. A real run may also simply
            # lack this attribute entirely on an older fixture/row -- both
            # shapes are exercised across this test class.
            stage_durations_ms={"plan": 55_000.0},
            created_at=datetime.now(UTC) - timedelta(minutes=2),
        )
        repository.runs.items[run.id] = run
        repository.state = CodeGeneratorSessionState(
            status="generating",
            current_run_id=str(run.id),
            active_preview=run.active_preview,
        )
        service = CodeGeneratorService(repository, jobs, Settings())  # type: ignore[arg-type]

        result = await service.get_state(session_id)
        progress = result["code_generator"]["progress"]

        # Every pre-existing key is untouched -- exact values, not just
        # presence.
        assert progress["coordinator_stage"] == "generate"
        assert progress["current_attempt"] == 1
        assert progress["plan_summary"] == {"routes": 5}
        assert progress["source_summary"] == {"files_written": 12}

        # The new field is present, additive, and well-formed.
        assert "stage_estimate" in progress
        estimate = progress["stage_estimate"]
        assert set(estimate.keys()) == {
            "elapsed_ms",
            "estimated_total_ms",
            "estimated_remaining_ms",
            "source",
        }
        assert estimate["source"] == "observed_and_budget"

    @pytest.mark.asyncio
    async def test_stage_estimate_degrades_gracefully_when_run_lacks_the_attribute(self) -> None:
        """A run row/fixture that predates this task's field (no
        `stage_durations_ms`/`created_at` attribute at all -- not even
        `None`) must not raise; `getattr(..., None)` at the call site
        degrades this to the same `configured_budget`, zero-elapsed shape
        as an explicit `None`."""

        session_id = uuid4()
        repository = _Repository(session_id, _ready_preparation())
        jobs = _Jobs()
        run = SimpleNamespace(
            id=uuid4(),
            revision=1,
            status="planning",
            issues=[],
            terminal_failure=None,
            active_preview=None,
            coordinator_stage="plan",
            current_attempt=1,
            active_attempt_id=None,
            plan_summary={},
            source_summary={},
            plan=None,
            planner_receipt=None,
            acquire_receipt=None,
            resource_ledger=None,
            dependency_ledger=None,
            source_checkpoint=None,
            generation_projection=None,
            creative_direction={},
            pipeline_contract_version="code-generator-v4",
            trace_id="trace-no-attribute",
            background_job_id=None,
            acquire_job_id=None,
            generation_job_id=None,
            verification_job_id=None,
            # Deliberately no `stage_durations_ms` / `created_at` attribute.
        )
        repository.runs.items[run.id] = run
        repository.state = CodeGeneratorSessionState(
            status="planning",
            current_run_id=str(run.id),
            active_preview=None,
        )
        service = CodeGeneratorService(repository, jobs, Settings())  # type: ignore[arg-type]

        result = await service.get_state(session_id)
        estimate = result["code_generator"]["progress"]["stage_estimate"]

        assert estimate["source"] == "configured_budget"
        assert estimate["elapsed_ms"] == 0
