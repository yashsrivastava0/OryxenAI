"""Fake (deterministic) Discovery model client for testing.

Returns typed fixture outputs. Requires no network, no API key.
Simulates refusal, timeout, rate limit, invalid output, and incomplete
responses for error-path testing.
"""

from __future__ import annotations

import asyncio
import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel

from oryxenai.agents.shared.contracts import ModelClient
from oryxenai.core.logging import get_logger

logger = get_logger("oryxenai.agents.discovery.fake_client")

_FIXTURE_DIR = Path(__file__).resolve().parent / "samples"


class FakeDiscoveryModelClient(ModelClient):
    """Deterministic fake client for Discovery tests.

    Automatically selects the right fixture based on operation type.
    Call A (prepare_questions) -> call_a_normal_output.json
    Call B (build_brief) -> call_b_normal_output.json
    """

    def __init__(
        self,
        fixture_name: str = "call_a_normal_output",
        simulate_refusal: bool = False,
        simulate_timeout: bool = False,
        simulate_rate_limit: bool = False,
        simulate_invalid_output: bool = False,
        simulate_incomplete: bool = False,
        delay_ms: float = 0.0,
    ) -> None:
        self._default_fixture = fixture_name
        self._simulate_refusal = simulate_refusal
        self._simulate_timeout = simulate_timeout
        self._simulate_rate_limit = simulate_rate_limit
        self._simulate_invalid_output = simulate_invalid_output
        self._simulate_incomplete = simulate_incomplete
        self._delay_ms = delay_ms
        self.requests: list[dict[str, Any]] = []

    async def complete(
        self,
        system_prompt: str,
        task_prompt: str,
        request_params: dict[str, Any] | None = None,
    ) -> str:
        self.requests.append(
            {
                "system_prompt": system_prompt,
                "task_prompt": task_prompt,
                "request_params": request_params,
            }
        )
        await self._maybe_delay()
        await self._maybe_simulate_errors()
        fixture = self._load_fixture(self._default_fixture)
        if isinstance(fixture, dict):
            return json.dumps(fixture)
        return str(fixture)

    async def generate_structured(
        self,
        *,
        operation: str,
        instructions: str,
        input_payload: Mapping[str, object],
        output_model: type[BaseModel],
        model_profile: Any = None,
        request_context: Any = None,
    ) -> Any:
        """Return typed fixture output for the given operation."""
        from oryxenai.agents.discovery.schemas import StructuredModelResult

        self.requests.append(
            {
                "operation": operation,
                "instructions": instructions,
                "input_payload": input_payload,
            }
        )
        await self._maybe_delay()
        await self._maybe_simulate_errors()

        fixture_name = self._resolve_fixture(operation)
        fixture = self._load_fixture(fixture_name)
        if output_model.__name__ == "DiscoveryBrief" and isinstance(fixture, dict):
            fixture = self._adapt_brief_fixture(fixture, input_payload)
        elif output_model.__name__ == "DiscoveryAnalysisResult" and isinstance(fixture, dict):
            fixture = self._adapt_analysis_fixture(fixture, input_payload)
        parsed = output_model(**fixture) if isinstance(fixture, dict) else output_model()

        return StructuredModelResult(
            parsed_output=parsed.model_dump(),
            response_id="fake-response-id",
            model="fake-model",
            usage={"prompt_tokens": 100, "completion_tokens": 200},
            finish_reason="stop",
            latency_ms=50.0,
        )

    def reset_requests(self) -> None:
        self.requests.clear()

    # ── Internal ─────────────────────────────────────────────────────────

    def _load_fixture(self, fixture_name: str) -> dict[str, Any]:
        path = _FIXTURE_DIR / f"{fixture_name}.json"
        if not path.is_file():
            raise FileNotFoundError(f"Fixture not found: {path}")
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)  # type: ignore[no-any-return]

    def _resolve_fixture(self, operation: str) -> str:
        if self._default_fixture != "call_a_normal_output":
            return self._default_fixture
        if operation in ("build_brief", "repair"):
            return "call_b_normal_output"
        return "call_a_normal_output"

    def _adapt_brief_fixture(
        self,
        fixture: dict[str, Any],
        input_payload: Mapping[str, object],
    ) -> dict[str, Any]:
        """Keep the deterministic brief fixture compatible with assigned fact IDs.

        The fixture references facts by category-suffixed IDs such as
        ``fact-target_role-1`` or ``fact-project-1``. These are mapped to the
        application-assigned local_key for the first fact of that category in
        the analysis payload, so the deterministic brief always validates.
        """
        analysis = input_payload.get("analysis")
        if not isinstance(analysis, Mapping):
            return fixture
        by_category: dict[str, str] = {}
        facts = analysis.get("facts") or analysis.get("fact_candidates", [])
        if isinstance(facts, list):
            for fact in facts:
                if isinstance(fact, Mapping):
                    category = str(fact.get("category", ""))
                    local_key = fact.get("local_key")
                    if category and isinstance(local_key, str):
                        by_category.setdefault(category, local_key)
        result = copy.deepcopy(fixture)

        def replace(value: Any) -> Any:
            if isinstance(value, str):
                return self._remap_fact_reference(value, by_category)
            if isinstance(value, list):
                return [replace(item) for item in value]
            if isinstance(value, dict):
                return {key: replace(item) for key, item in value.items()}
            return value

        return cast(dict[str, Any], replace(result))

    def _adapt_analysis_fixture(
        self,
        fixture: dict[str, Any],
        input_payload: Mapping[str, object],
    ) -> dict[str, Any]:
        """Keep the Call A fixture valid against the provided source packet.

        Facts whose evidence excerpts cannot be located in the supplied
        sources are dropped, so the deterministic analysis always passes
        grounding validation regardless of the intake content.
        """
        packet = input_payload if isinstance(input_payload, Mapping) else {}
        source_texts = (
            str(packet.get("main_prompt", "")) + "\n" + str(packet.get("resume_text", ""))
        ).lower()
        result = copy.deepcopy(fixture)
        facts = result.get("facts")
        if isinstance(facts, list):
            kept = []
            for fact in facts:
                if not isinstance(fact, Mapping):
                    continue
                evidence = fact.get("evidence", [])
                if isinstance(evidence, list) and evidence:
                    locatable = any(
                        isinstance(item, Mapping)
                        and " ".join(str(item.get("evidence_excerpt", "")).split()).lower()
                        in source_texts
                        for item in evidence
                    )
                    if not locatable:
                        continue
                kept.append(fact)
            result["facts"] = kept
        return result

    @staticmethod
    def _remap_fact_reference(value: str, by_category: dict[str, str]) -> str:
        """Map ``fact-<category>-<suffix>`` to the assigned ID for that category."""
        if not value.startswith("fact-"):
            return value
        category = value.split("-")[1] if value.count("-") >= 2 else ""
        if category in by_category:
            return by_category[category]
        return value

    async def _maybe_delay(self) -> None:
        if self._delay_ms > 0:
            await asyncio.sleep(self._delay_ms / 1000.0)

    async def _maybe_simulate_errors(self) -> None:
        if self._simulate_timeout:
            raise TimeoutError("Fake timeout")
        if self._simulate_rate_limit:
            raise Exception("Fake rate limit exceeded")
        if self._simulate_refusal:
            raise Exception("Fake model refusal")
        if self._simulate_incomplete:
            raise Exception("Fake incomplete response")
        if self._simulate_invalid_output:
            raise ValueError("Fake schema validation failure")
