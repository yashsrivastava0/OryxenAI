"""Deterministic ModelClient for tests and the CLI ``--mock`` mode.

Answers ``generate_page`` with the reference renderer's output, optionally
mutated or replaced by an error, so the whole pipeline (worker, validation,
failure reporting) can run without a live model. Never imported by runtime code.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from typing import Any

from pydantic import BaseModel

from oryxenai.agents.code_generator.dev.reference_renderer import render_body
from oryxenai.agents.discovery.schemas import StructuredModelResult

Mutator = Callable[[str], str]


class ReferenceModelClient:
    """Renders the page itself; ``mutate`` / ``error`` / ``raw_output`` inject failures."""

    def __init__(
        self,
        *,
        mutate: Mutator | None = None,
        error: BaseException | None = None,
        raw_output: dict[str, Any] | None = None,
        lang: str = "en",
        delay: float = 0.0,
        plans: list[dict[str, Any]] | None = None,
    ) -> None:
        # ``plans`` are served in order to interpret_change calls (the last repeats).
        self.plans = plans or [{"intent": "chat_only", "reply": "Happy to help."}]
        self.mutate = mutate
        self.error = error
        self.raw_output = raw_output
        self.lang = lang
        self.delay = delay
        self.requests: list[dict[str, Any]] = []

    async def complete(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError

    async def generate_structured(
        self,
        *,
        operation: str,
        instructions: str,
        input_payload: Mapping[str, Any],
        output_model: type[BaseModel],
        **kwargs: Any,
    ) -> StructuredModelResult:
        self.requests.append(
            {
                "operation": operation,
                "instructions": instructions,
                "input_payload": input_payload,
                "system_prompt": kwargs.get("system_prompt"),
                "request_context": kwargs.get("request_context"),
            }
        )
        if operation not in {"generate_page", "interpret_change"}:
            raise AssertionError(f"unexpected operation for the page builder mock: {operation}")
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error is not None:
            raise self.error
        if operation == "interpret_change":
            seen = sum(1 for item in self.requests if item["operation"] == "interpret_change")
            plan = self.plans[min(seen - 1, len(self.plans) - 1)]
            return StructuredModelResult(
                parsed_output=dict(plan),
                response_id="mock-plan",
                model="reference-interpreter",
                usage={"prompt_tokens": 1, "completion_tokens": 1},
                finish_reason="stop",
                latency_ms=1.0,
                telemetry={"provider": "mock"},
            )
        if self.raw_output is not None:
            parsed = dict(self.raw_output)
        else:
            body = render_body(
                input_payload["content"],
                input_payload["derived"],
                theme_id=str(input_payload["theme"]["id"]),
            )
            if self.mutate is not None:
                body = self.mutate(body)
            parsed = {"lang": self.lang, "body_html": body}
        return StructuredModelResult(
            parsed_output=parsed,
            response_id="mock-response",
            model="reference-renderer",
            usage={"prompt_tokens": 1, "completion_tokens": 1},
            finish_reason="stop",
            latency_ms=1.0,
            telemetry={"provider": "mock"},
        )
