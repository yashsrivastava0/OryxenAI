"""Central classification of durable jobs that can consume model credit."""

from __future__ import annotations

from dataclasses import dataclass

MODEL_GENERATION_LANE = "model-generation"


@dataclass(frozen=True, slots=True)
class JobKindPolicy:
    consumes_model_credit: bool
    portfolio_bound: bool
    # Interactive portfolio requests stay ahead of background jobs in the
    # shared model lane.
    foreground: bool = False


_POLICIES: dict[str, JobKindPolicy] = {
    "system.worker_probe": JobKindPolicy(False, False),
    "discovery.understand_and_question": JobKindPolicy(True, True, True),
    "discovery.build_or_revise_brief": JobKindPolicy(True, True, True),
    "discovery.prepare_questions": JobKindPolicy(True, True, True),
    "discovery.build_brief": JobKindPolicy(True, True, True),
    "content_architect.build": JobKindPolicy(True, True, True),
}


def policy_for(kind: str) -> JobKindPolicy:
    """Return a closed-set policy; unknown jobs are never silently credit-bound."""

    return _POLICIES.get(kind, JobKindPolicy(False, False))


def known_policies() -> dict[str, JobKindPolicy]:
    return dict(_POLICIES)


def foreground_job_kinds() -> tuple[str, ...]:
    """Return interactive portfolio jobs in the scheduling priority class."""

    return tuple(kind for kind, policy in _POLICIES.items() if policy.foreground)
