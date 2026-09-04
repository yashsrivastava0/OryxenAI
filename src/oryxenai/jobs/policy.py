"""Central classification of durable jobs that can consume model credit."""

from __future__ import annotations

from dataclasses import dataclass

MODEL_GENERATION_LANE = "model-generation"


@dataclass(frozen=True, slots=True)
class JobKindPolicy:
    consumes_model_credit: bool
    portfolio_bound: bool


_POLICIES: dict[str, JobKindPolicy] = {
    "system.worker_probe": JobKindPolicy(False, False),
    "discovery.understand_and_question": JobKindPolicy(True, True),
    "discovery.build_or_revise_brief": JobKindPolicy(True, True),
    "discovery.prepare_questions": JobKindPolicy(True, True),
    "discovery.build_brief": JobKindPolicy(True, True),
    "content_architect.build": JobKindPolicy(True, True),
    "visual_design_director.build": JobKindPolicy(True, True),
    "build_preparation.prepare": JobKindPolicy(True, True),
    "code_generator.plan": JobKindPolicy(True, True),
    "code_generator.acquire": JobKindPolicy(True, True),
    "code_generator.generate": JobKindPolicy(True, True),
    "code_generator.verify_and_preview": JobKindPolicy(True, True),
    # V5 is a fresh queue namespace.  It intentionally coexists with the
    # legacy entries so already-queued v3/v4 runs retain their policy while a
    # stale worker cannot silently execute a v5 job as an old operation.
    "code_generator.v5.plan": JobKindPolicy(True, True),
    "code_generator.v5.acquire": JobKindPolicy(True, True),
    "code_generator.v5.generate": JobKindPolicy(True, True),
    "code_generator.v5.verify_and_preview": JobKindPolicy(True, True),
}


def policy_for(kind: str) -> JobKindPolicy:
    """Return a closed-set policy; unknown jobs are never silently credit-bound."""

    return _POLICIES.get(kind, JobKindPolicy(False, False))


def known_policies() -> dict[str, JobKindPolicy]:
    return dict(_POLICIES)
