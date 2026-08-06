"""Tests for the provider capability model and total attempt budget."""

from __future__ import annotations

import pytest

from oryxenai.agents.shared.providers.attempt_policy import AttemptBudget, default_budget
from oryxenai.agents.shared.providers.capabilities import (
    DEFAULT_OPENCODE_GO,
    ModelCapabilities,
)


class TestModelCapabilities:
    def test_all_fields_exist_and_are_bools(self):
        fields = set(ModelCapabilities.model_fields)
        expected = {
            "json_object_mode",
            "json_schema_mode",
            "thinking_mode",
            "reasoning_content",
            "temperature_control",
            "usage_metadata",
            "response_id",
            "context_cache_metadata",
            "supports_store_parameter",
        }
        assert fields == expected

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValueError):
            ModelCapabilities(  # type: ignore[call-arg]
                json_object_mode=True,
                json_schema_mode=False,
                thinking_mode=True,
                reasoning_content=True,
                temperature_control=True,
                usage_metadata=True,
                response_id=True,
                context_cache_metadata=False,
                supports_store_parameter=True,
                unexpected=True,
            )

    def test_default_opencode_go_shape(self):
        assert DEFAULT_OPENCODE_GO.json_object_mode is True
        assert DEFAULT_OPENCODE_GO.json_schema_mode is False
        assert DEFAULT_OPENCODE_GO.thinking_mode is True
        assert DEFAULT_OPENCODE_GO.reasoning_content is True
        assert DEFAULT_OPENCODE_GO.supports_store_parameter is True
        assert DEFAULT_OPENCODE_GO.context_cache_metadata is False


class TestAttemptBudget:
    def test_total_model_calls_is_bounded(self):
        budget = AttemptBudget()
        assert budget.total_model_calls_max == 2  # 1 initial + 1 recovery/repair

    def test_remaining(self):
        budget = AttemptBudget()
        assert budget.remaining(0) == 2
        assert budget.remaining(1) == 1
        assert budget.remaining(2) == 0
        assert budget.remaining(5) == 0

    def test_default_budget_factory(self):
        budget = default_budget()
        assert budget.transport_retry == 1
        assert budget.completed_response_recovery == 1
        assert budget.semantic_repair == 1
        assert budget.worker_max_attempts == 3

    def test_repair_cannot_exceed_recovery_bound(self):
        budget = AttemptBudget(completed_response_recovery=1, semantic_repair=1)
        assert budget.semantic_repair <= budget.completed_response_recovery

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValueError):
            AttemptBudget(nonsense=1)  # type: ignore[call-arg]
