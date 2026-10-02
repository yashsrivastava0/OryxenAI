"""The page build pipeline: one straight line with exact, located failures."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from oryxenai.agents.code_generator.agent import CodeGeneratorAgent
from oryxenai.agents.code_generator.dev.mock_client import ReferenceModelClient
from oryxenai.agents.code_generator.pipeline import (
    VerificationResult,
    build_page,
)
from oryxenai.agents.code_generator.schemas import CodeGeneratorFailure
from oryxenai.agents.shared.context import build_context
from oryxenai.agents.shared.contracts import AgentKey
from oryxenai.agents.shared.providers.errors import ProviderRateLimitError, ProviderTimeoutError
from oryxenai.themes import get_theme
from oryxenai.themes.issues import Issue
from tests.unit.agents.code_generator.helpers import sample_content, shapes

THEME = get_theme()
CONTENT = sample_content("01_strong_profile")


def _context() -> Any:
    return build_context(
        portfolio_session_id=uuid4(),
        agent_key=AgentKey.CODE_GENERATOR,
        current_state={},
        agent_input={"operation": "generate_page", "routing_policy_snapshot": {}},
        run_id=uuid4(),
    )


async def _build(
    client: ReferenceModelClient, content: dict[str, Any] | None = None, **kwargs: Any
):
    trace: dict[str, Any] = {}
    stages: list[str] = []

    async def on_stage(stage: str) -> None:
        stages.append(stage)

    try:
        outcome = await build_page(
            page_content=content or CONTENT,
            agent=CodeGeneratorAgent(client),
            context=_context(),
            theme=THEME,
            max_body_bytes=262144,
            trace=trace,
            reference="cg-test",
            on_stage=on_stage,
            **kwargs,
        )
    except CodeGeneratorFailure as exc:
        return exc, trace, stages
    return outcome, trace, stages


@pytest.mark.asyncio
async def test_a_valid_page_is_sealed_with_a_receipt_and_stage_events() -> None:
    outcome, trace, stages = await _build(ReferenceModelClient())
    assert stages == ["generating", "validating"]
    receipt = outcome.receipt
    assert receipt["contract_version"] == "SiteReceipt/v1"
    assert receipt["theme_id"] == THEME.theme_id
    assert receipt["theme_sha256"] == THEME.css_sha256
    assert receipt["validation"] == {"ok": True, "warning_count": 0, "warnings": []}
    assert receipt["browser"] == {"status": "not_run"}
    assert outcome.bundle.index_html.startswith("<!doctype html>")
    assert outcome.bundle.index_sha256 == receipt["index_sha256"]
    assert set(trace["timings_ms"]) >= {"generate", "validate", "bundle"}
    assert trace["calls"][0]["operation"] == "generate_page"
    assert trace["calls"][0]["prompt_modules"]["theme"].startswith(THEME.theme_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("name", sorted(shapes()))
async def test_every_content_shape_builds_through_the_pipeline(name: str) -> None:
    outcome, _trace, _stages = await _build(ReferenceModelClient(), shapes()[name])
    assert not isinstance(outcome, CodeGeneratorFailure), outcome


@pytest.mark.asyncio
async def test_exactly_one_model_call_is_made_per_build() -> None:
    client = ReferenceModelClient()
    await _build(client)
    assert [request["operation"] for request in client.requests] == ["generate_page"]
    request = client.requests[0]
    assert request["input_payload"]["content"]["hero"]["name"] == CONTENT["hero"]["name"]
    assert request["input_payload"]["derived"]["monogram"]
    assert request["request_context"]["stream"] is True
    assert request["request_context"]["prompt_cache_key"].startswith("oryxenai:code_generator:")


@pytest.mark.asyncio
async def test_paraphrased_copy_fails_validation_naming_the_field_and_keeps_the_body() -> None:
    name = CONTENT["hero"]["name"]
    client = ReferenceModelClient(mutate=lambda body: body.replace(name, name + " Jr.", 1))
    failure, trace, stages = await _build(client)
    assert isinstance(failure, CodeGeneratorFailure)
    envelope = failure.envelope
    assert envelope.code == "PAGE_COPY_MISMATCH"
    assert envelope.stage == "validate"
    assert envelope.owner == "model_output"
    assert envelope.reference == "cg-test"
    assert envelope.where and envelope.where[0].ref.startswith("hero")
    assert stages == ["generating", "validating"]
    assert name + " Jr." in trace["rejected_body_html"]
    assert trace["validation"]["ok"] is False


@pytest.mark.asyncio
async def test_a_script_tag_is_rejected_as_disallowed_markup() -> None:
    client = ReferenceModelClient(mutate=lambda body: body + '<script>alert("x")</script>')
    failure, _trace, _stages = await _build(client)
    assert isinstance(failure, CodeGeneratorFailure)
    assert failure.envelope.stage == "validate"
    assert any(issue["code"] == "TAG_NOT_ALLOWED" for issue in failure.envelope.issues)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "code", "owner"),
    [
        (ProviderTimeoutError("slow"), "PROVIDER_TIMEOUT_ERROR", "infrastructure"),
        (ProviderRateLimitError("busy"), "PROVIDER_RATE_LIMIT_ERROR", "infrastructure"),
    ],
)
async def test_provider_errors_become_exact_generate_stage_failures(
    error: Exception, code: str, owner: str
) -> None:
    failure, trace, stages = await _build(ReferenceModelClient(error=error))
    assert isinstance(failure, CodeGeneratorFailure)
    assert (failure.envelope.code, failure.envelope.stage, failure.envelope.owner) == (
        code,
        "generate",
        owner,
    )
    assert failure.envelope.reference == "cg-test"
    assert stages == ["generating"]
    assert "generate" in trace["timings_ms"]


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", [{"lang": "en"}, {"lang": "en", "body_html": "   "}, {}])
async def test_a_reply_without_page_markup_is_an_output_failure(raw: dict[str, Any]) -> None:
    failure, _trace, _stages = await _build(ReferenceModelClient(raw_output=raw))
    assert isinstance(failure, CodeGeneratorFailure)
    assert failure.envelope.code == "MODEL_OUTPUT_INVALID"
    assert failure.envelope.stage == "generate"


@pytest.mark.asyncio
async def test_output_that_is_not_html_is_rejected_before_parsing() -> None:
    client = ReferenceModelClient(
        raw_output={"lang": "en", "body_html": "```html\n<main></main>\n```"}
    )
    failure, _trace, _stages = await _build(client)
    assert isinstance(failure, CodeGeneratorFailure)
    assert failure.envelope.code == "PAGE_OUTPUT_INVALID"


class _Verifier:
    def __init__(self, result: VerificationResult) -> None:
        self.result = result
        self.seen: list[str] = []

    async def verify(self, bundle: Any, theme: Any) -> VerificationResult:
        self.seen.append(bundle.index_sha256)
        return self.result


@pytest.mark.asyncio
async def test_a_passing_verifier_is_recorded_in_the_receipt() -> None:
    verifier = _Verifier(VerificationResult("passed", [], {"viewports": [320, 1280]}))
    outcome, trace, stages = await _build(ReferenceModelClient(), verifier=verifier)
    assert stages == ["generating", "validating", "verifying"]
    assert outcome.receipt["browser"] == {"status": "passed", "viewports": [320, 1280]}
    assert verifier.seen == [outcome.bundle.index_sha256]
    assert trace["verification"]["status"] == "passed"


@pytest.mark.asyncio
async def test_a_failing_verifier_blocks_with_the_browser_findings() -> None:
    issue = Issue("CONSOLE_ERROR", "error", "A console error was logged.", selector="img.hero")
    verifier = _Verifier(VerificationResult("failed", [issue], {}))
    failure, trace, _stages = await _build(ReferenceModelClient(), verifier=verifier)
    assert isinstance(failure, CodeGeneratorFailure)
    assert failure.envelope.code == "PAGE_BROWSER_CHECK_FAILED"
    assert failure.envelope.stage == "verify"
    assert failure.envelope.owner == "browser"
    assert failure.envelope.where[0].ref == "img.hero"
    assert trace["verification"]["status"] == "failed"


@pytest.mark.asyncio
async def test_an_unavailable_browser_does_not_block_a_valid_page() -> None:
    verifier = _Verifier(VerificationResult("unavailable", [], {"reason": "no browser"}))
    outcome, _trace, _stages = await _build(ReferenceModelClient(), verifier=verifier)
    assert not isinstance(outcome, CodeGeneratorFailure)
    assert outcome.receipt["browser"]["status"] == "unavailable"
