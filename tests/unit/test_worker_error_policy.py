from oryxenai.agents.shared.observability import durable_model_metadata
from oryxenai.agents.shared.providers.errors import ModelOutputInvalidError
from oryxenai.jobs.worker import _safe_handler_error, _timeout_decision


def test_unknown_programming_error_is_permanent() -> None:
    error = _safe_handler_error(RuntimeError("private implementation detail"))

    assert error.code == "HANDLER_ERROR"
    assert error.retryable is False
    assert "private implementation detail" not in error.message


def test_model_output_contract_failure_remains_retryable_and_redacted() -> None:
    error = _safe_handler_error(ModelOutputInvalidError("private generated validation detail"))

    assert error.code == "MODEL_OUTPUT_INVALID"
    assert error.retryable is True
    assert "private generated validation detail" not in error.message
    assert error.message == "The model returned output that did not satisfy the required structure."


def test_timeout_hook_and_queue_share_retry_decision() -> None:
    retry_error, retry_payload = _timeout_decision("bounded timeout", attempt=1, max_attempts=2)
    final_error, final_payload = _timeout_decision("bounded timeout", attempt=2, max_attempts=2)

    assert retry_error.retryable is True
    assert retry_payload["retryable"] is True
    assert retry_payload["will_retry"] is True
    assert final_error.retryable is True
    assert final_payload["retryable"] is True
    assert final_payload["will_retry"] is False


def test_durable_model_metadata_aggregates_receipts_without_reasoning() -> None:
    metadata = durable_model_metadata(
        {
            "stages": [
                {
                    "operation": "plan",
                    "latency_ms": 12.5,
                    "finish_reason": "stop",
                    "usage": {"input_tokens": 3, "output_tokens": 2},
                    "reasoning_content": "must not persist",
                    "raw_response": {"private": True},
                }
            ]
        },
        profile_id="configured-profile",
        attempt=2,
    )

    assert metadata["latency_ms"] == 12.5
    assert metadata["usage"] == {"input_tokens": 3, "output_tokens": 2}
    assert metadata["finish_reason"] == "stop"
    assert metadata["profile_id"] == "configured-profile"
    assert metadata["attempt"] == 2
    assert "reasoning_content" not in metadata["stages"][0]
    assert "raw_response" not in metadata["stages"][0]
