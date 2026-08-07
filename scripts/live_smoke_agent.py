"""Live Discovery smoke test using the real OpenCode Go adapter.

This test does not use the database or the deterministic test client. It makes
three real model calls: Operation A, brief generation, and brief revision.
Every call has a bounded timeout so a slow model cannot hang the command.

Run:
    uv run python scripts/live_smoke_agent.py

Optional environment variables:
    ORA_SMOK_MODEL                    Model override for this run.
    ORA_SMOKE_TIMEOUT_A               Operation A timeout in seconds (60).
    ORA_SMOKE_TIMEOUT_B               Brief/revision timeout in seconds (120).
    ORA_SMOKE_TOTAL_TIMEOUT           Overall timeout in seconds (300).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from uuid import uuid4

from oryxenai.agents.discovery.agent import DiscoveryAgent
from oryxenai.agents.discovery.schemas import OperationMode
from oryxenai.agents.shared.context import build_context
from oryxenai.agents.shared.contracts import AgentKey, AgentResult
from oryxenai.agents.shared.model_client import build_provider_client
from oryxenai.core.settings import get_settings


class SmokeFailure(RuntimeError):
    """A live smoke assertion or provider operation failed."""


def _number(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise SmokeFailure(f"{name} must be a number, got {raw!r}") from exc
    if value <= 0:
        raise SmokeFailure(f"{name} must be greater than zero")
    return value


def _sample() -> dict[str, str]:
    path = Path("src/oryxenai/agents/discovery/samples/01_software_engineer_input.json")
    return json.loads(path.read_text(encoding="utf-8"))


def _make_context(agent_input: dict[str, object]) -> object:
    return build_context(
        portfolio_session_id=uuid4(),
        agent_key=AgentKey.DISCOVERY,
        current_state={},
        agent_input=agent_input,
        request_id="live-agent-smoke",
        attempt=1,
        run_id=uuid4(),
    )


async def _run(
    agent: DiscoveryAgent,
    label: str,
    agent_input: dict[str, object],
    timeout: float,
) -> AgentResult:
    print(f"[{label}] starting (timeout={timeout:.0f}s)")
    started = time.monotonic()
    try:
        result = await asyncio.wait_for(agent.run(_make_context(agent_input)), timeout=timeout)
    except TimeoutError as exc:
        elapsed = time.monotonic() - started
        raise SmokeFailure(
            f"{label} FAILED: timeout after {elapsed:.1f}s; model is too slow for the smoke budget"
        ) from exc
    except Exception as exc:
        elapsed = time.monotonic() - started
        raise SmokeFailure(f"{label} FAILED after {elapsed:.1f}s: {exc}") from exc

    elapsed = time.monotonic() - started
    metadata = result.model_metadata
    if "reasoning_content" in str(metadata):
        raise SmokeFailure(f"{label} FAILED: reasoning_content leaked into metadata")
    print(
        f"[{label}] passed in {elapsed:.1f}s "
        f"model={metadata.get('model', '(unknown)')} "
        f"latency_ms={metadata.get('latency_ms', 0)} "
        f"finish_reason={metadata.get('finish_reason', '(unknown)')}"
    )
    return result


def _answer_value(question: dict[str, object]) -> object:
    kind = question.get("kind", "text")
    options = question.get("options") or []
    if kind in {"single_select", "multi_select"} and options:
        first = options[0]
        if isinstance(first, dict):
            value = first.get("id", "")
            return [value] if kind == "multi_select" else value
    if kind == "boolean":
        return "true"
    return "Lead with backend/platform engineering for startup CTOs."


async def main() -> None:
    settings = get_settings()
    profile = settings.models.get_profile("discovery")
    if profile is None:
        raise SmokeFailure("[profiles.discovery] is missing")
    override = os.environ.get("ORA_SMOK_MODEL", "").strip()
    if override:
        profile.model = override
    if not profile.model:
        raise SmokeFailure("Discovery model is empty")
    client = build_provider_client("discovery", settings.models)
    if client is None:
        raise SmokeFailure(
            "The discovery provider could not be built. Check OPENCODE_GO_API_KEY and the profile."
        )

    timeout_a = _number("ORA_SMOKE_TIMEOUT_A", 60.0)
    timeout_b = _number("ORA_SMOKE_TIMEOUT_B", 120.0)
    sample = _sample()
    agent = DiscoveryAgent(model_client=client)
    print(f"Live agent smoke model: {profile.model}")

    operation_a = await _run(
        agent,
        "operation-a",
        {
            "operation": "understand_and_question",
            "intake": sample,
            "prior_memory": {},
        },
        timeout_a,
    )
    output_a = operation_a.output
    mode = output_a.get("mode")
    questions = output_a.get("questions") or []
    print(f"    mode={mode} questions={len(questions)}")

    if mode == OperationMode.NEEDS_DETAILS.value:
        operation_a = await _run(
            agent,
            "operation-a-follow-up",
            {
                "operation": "understand_and_question",
                "intake": {
                    **sample,
                    "message": (
                        f"{sample['message']} The details are supplied above; ask only remaining "
                        "high-value questions."
                    ),
                },
                "prior_memory": output_a.get("memory_update", {}),
            },
            timeout_a,
        )
        output_a = operation_a.output
        questions = output_a.get("questions") or []
        print(f"    follow-up mode={output_a.get('mode')} questions={len(questions)}")

    answers = {
        str(question["id"]): {
            "question_id": str(question["id"]),
            "mode": "answered",
            "value": _answer_value(question),
        }
        for question in questions
        if isinstance(question, dict) and question.get("id")
    }
    brief_input = {
        "operation": "build_or_revise_brief",
        "intake": sample,
        "answers": answers,
        "prior_memory": output_a.get("memory_update", {}),
        "existing_brief": "",
        "revision_request": "",
    }
    brief_result = await _run(agent, "operation-b", brief_input, timeout_b)
    brief_markdown = str(brief_result.output.get("brief_markdown", ""))
    if not brief_markdown.strip():
        raise SmokeFailure("operation-b FAILED: brief_markdown is empty")
    print(f"    brief_words={len(brief_markdown.split())}")

    revision_request = "Lead with the QueueGuard story and make the backend/platform CTA explicit."
    revised_result = await _run(
        agent,
        "revision",
        {
            **brief_input,
            "existing_brief": brief_markdown,
            "revision_request": revision_request,
        },
        timeout_b,
    )
    revised_markdown = str(revised_result.output.get("brief_markdown", ""))
    if "QueueGuard" not in revised_markdown:
        raise SmokeFailure("revision FAILED: revised brief does not contain QueueGuard")
    print(f"    revised_words={len(revised_markdown.split())} queueguard=True")
    print("LIVE AGENT SMOKE PASSED")


def run() -> int:
    total_timeout = _number("ORA_SMOKE_TOTAL_TIMEOUT", 300.0)
    try:
        asyncio.run(asyncio.wait_for(main(), timeout=total_timeout))
    except TimeoutError:
        print(
            f"LIVE AGENT SMOKE FAILED: overall timeout after {total_timeout:.0f}s", file=sys.stderr
        )
        return 1
    except Exception as exc:
        print(f"LIVE AGENT SMOKE FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
