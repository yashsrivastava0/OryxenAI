from __future__ import annotations

from oryxenai.jobs import registry
from oryxenai.jobs.policy import known_policies, policy_for


def test_every_registered_job_kind_has_a_closed_phase3_policy() -> None:
    policies = known_policies()

    assert set(registry.list_kinds()) <= set(policies)
    assert policy_for("unknown.job").consumes_model_credit is False
    assert policy_for("unknown.job").portfolio_bound is False

    for kind in registry.list_kinds():
        policy = policy_for(kind)
        if kind == "system.worker_probe":
            assert policy.consumes_model_credit is False
            assert policy.portfolio_bound is False
        else:
            assert policy.consumes_model_credit is True
            assert policy.portfolio_bound is True
