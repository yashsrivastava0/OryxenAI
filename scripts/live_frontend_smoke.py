"""Live smoke test through the HTTP API used by the frontend.

This creates a session, drives Discovery through approval, then explicitly
starts and approves Content Architect and Visual Design Director. It uses the
live configured model and has a hard overall timeout so it cannot wait forever.

Run:
    uv run python scripts/live_frontend_smoke.py

Optional environment variables:
    ORA_API_URL                  API URL (default http://127.0.0.1:8000).
    ORA_FRONTEND_SMOKE_TIMEOUT   Overall timeout in seconds (360).
    ORA_FRONTEND_SMOKE_ACCESS_TOKEN
                                 Ephemeral Supabase access token for this run.

The access token is read only from the process environment, attached as a
Bearer header, and never printed or written to disk.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx


class SmokeFailure(RuntimeError):
    """A frontend API smoke assertion failed."""


def _timeout() -> float:
    raw = os.environ.get("ORA_FRONTEND_SMOKE_TIMEOUT", "360").strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise SmokeFailure(f"ORA_FRONTEND_SMOKE_TIMEOUT must be numeric, got {raw!r}") from exc
    if value <= 0:
        raise SmokeFailure("ORA_FRONTEND_SMOKE_TIMEOUT must be greater than zero")
    return value


def _sample() -> dict[str, str]:
    path = Path("src/oryxenai/agents/discovery/samples/01_software_engineer_input.json")
    return json.loads(path.read_text(encoding="utf-8"))


async def _request(
    client: httpx.AsyncClient, method: str, path: str, **kwargs: Any
) -> dict[str, Any]:
    response = await client.request(method, path, **kwargs)
    try:
        body = response.json()
    except ValueError as exc:
        raise SmokeFailure(
            f"{method} {path} returned non-JSON HTTP {response.status_code}"
        ) from exc
    if response.status_code >= 400:
        error = body.get("error", {}) if isinstance(body, dict) else {}
        raise SmokeFailure(
            f"{method} {path} failed HTTP {response.status_code}: "
            f"{error.get('message', response.text)}"
        )
    return body


async def _poll_discovery(
    client: httpx.AsyncClient,
    path: str,
    accepted: set[str],
    deadline: float,
) -> dict[str, Any]:
    while time.monotonic() < deadline:
        body = await _request(client, "GET", path)
        discovery = body["discovery"]
        status = discovery["status"]
        if status in accepted:
            return body
        if status == "needs_attention":
            error = discovery.get("latest_error") or {}
            raise SmokeFailure(f"Discovery failed: {error.get('code')} {error.get('message')}")
        await asyncio.sleep(1.2)
    raise SmokeFailure(f"Timed out waiting for states: {sorted(accepted)}")


async def _poll_stage(
    client: httpx.AsyncClient,
    path: str,
    stage_key: str,
    accepted: set[str],
    deadline: float,
) -> dict[str, Any]:
    """Poll one explicit post-Discovery stage until it reaches review."""
    while time.monotonic() < deadline:
        body = await _request(client, "GET", path)
        stage = body[stage_key]
        status = stage["status"]
        if status in accepted:
            return body
        if status == "needs_attention":
            error = stage.get("latest_error") or {}
            raise SmokeFailure(f"{stage_key} failed: {error.get('code')} {error.get('message')}")
        await asyncio.sleep(1.2)
    raise SmokeFailure(f"Timed out waiting for {stage_key} states: {sorted(accepted)}")


def _answer_value(question: dict[str, Any]) -> Any:
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
    base_url = os.environ.get("ORA_API_URL", "http://127.0.0.1:8000").rstrip("/")
    access_token = os.environ.get("ORA_FRONTEND_SMOKE_ACCESS_TOKEN", "").strip()
    if not access_token:
        raise SmokeFailure(
            "ORA_FRONTEND_SMOKE_ACCESS_TOKEN is required; provide an ephemeral "
            "Supabase access token for this smoke run."
        )
    sample = _sample()
    deadline = time.monotonic() + _timeout()
    async with httpx.AsyncClient(
        base_url=base_url,
        timeout=10.0,
        headers={"Authorization": f"Bearer {access_token}"},
    ) as client:
        health = await _request(client, "GET", "/health/ready")
        if health.get("status") != "ready":
            raise SmokeFailure(f"API is not ready: {health}")
        session = await _request(
            client, "POST", "/api/v1/sessions", json={"name": "live-frontend-smoke"}
        )
        session_id = session["id"]
        discovery_path = f"/api/v1/sessions/{session_id}/discovery"
        start_path = f"{discovery_path}/start"
        answers_path = f"{discovery_path}/answers"
        revise_path = f"{discovery_path}/revise"
        approve_path = f"{discovery_path}/approve"

        started = await _request(client, "POST", start_path, json=sample)
        print(f"[start] status={started['discovery']['status']}")
        state = await _poll_discovery(client, discovery_path, {"questions_ready"}, deadline)
        operation_a = state["discovery"]["operation_a"]
        print(f"[operation-a] mode={operation_a['mode']} questions={len(operation_a['items'])}")

        if operation_a["mode"] == "NEEDS_DETAILS":
            follow_up = {
                **sample,
                "message": sample["message"] + " Please ask only remaining high-value questions.",
            }
            await _request(client, "POST", start_path, json=follow_up)
            state = await _poll_discovery(client, discovery_path, {"questions_ready"}, deadline)
            operation_a = state["discovery"]["operation_a"]
            print(
                f"[operation-a-follow-up] mode={operation_a['mode']} questions={len(operation_a['items'])}"
            )

        answers = [
            {
                "question_id": str(question["id"]),
                "mode": "answered",
                "value": _answer_value(question),
            }
            for question in operation_a["items"]
            if question.get("id")
        ]
        answered = await _request(
            client, "PUT", answers_path, json={"complete": True, "answers": answers}
        )
        print(f"[answers] status={answered['discovery']['status']}")
        state = await _poll_discovery(client, discovery_path, {"brief_review"}, deadline)
        brief = state["discovery"]["brief"]
        if not brief.get("markdown"):
            raise SmokeFailure("brief_review returned empty markdown")
        print(f"[brief] title={brief['title'][:80]!r} words={len(brief['markdown'].split())}")

        revised = await _request(
            client,
            "POST",
            revise_path,
            json={"revision_request": "Lead with the QueueGuard story and make the CTA explicit."},
        )
        print(f"[revise] status={revised['discovery']['status']}")
        state = await _poll_discovery(client, discovery_path, {"brief_review"}, deadline)
        revised_brief = state["discovery"]["brief"]
        if "QueueGuard" not in revised_brief["markdown"]:
            raise SmokeFailure("revised brief does not contain QueueGuard")
        print(f"[revised-brief] words={len(revised_brief['markdown'].split())} queueguard=True")

        approved = await _request(client, "POST", approve_path, json={})
        if approved["discovery"]["status"] != "approved":
            raise SmokeFailure(f"approval returned {approved['discovery']['status']}")
        print(
            f"[approve] status=approved hash={approved['discovery']['brief']['approved']['brief_hash'][:16]}"
        )

        content_path = f"/api/v1/sessions/{session_id}/content-architect"
        content_start_path = f"{content_path}/start"
        content_approve_path = f"{content_path}/approve"
        content_started = await _request(client, "POST", content_start_path, json={})
        print(f"[content-start] status={content_started['content_architect']['status']}")
        content_review = await _poll_stage(
            client, content_path, "content_architect", {"content_review"}, deadline
        )
        content = content_review["content_architect"]
        if not content.get("route_plan") or not content.get("page_content_packs"):
            raise SmokeFailure("content_review returned incomplete public content")
        print(
            f"[content-review] routes={len(content['route_plan'])} "
            f"page_packs={len(content['page_content_packs'])}"
        )
        content_approved = await _request(client, "POST", content_approve_path, json={})
        if content_approved["content_architect"]["status"] != "approved":
            raise SmokeFailure(
                f"content approval returned {content_approved['content_architect']['status']}"
            )
        print(
            "[content-approve] status=approved "
            f"hash={content_approved['content_architect']['approved']['content_hash'][:16]}"
        )

        design_path = f"/api/v1/sessions/{session_id}/visual-design-director"
        design_start_path = f"{design_path}/start"
        design_approve_path = f"{design_path}/approve"
        design_started = await _request(client, "POST", design_start_path, json={})
        print(f"[design-start] status={design_started['visual_design_director']['status']}")
        design_review = await _poll_stage(
            client, design_path, "visual_design_director", {"design_review"}, deadline
        )
        design = design_review["visual_design_director"]
        if not design.get("visual_language") or not design.get("pages"):
            raise SmokeFailure("design_review returned incomplete visual direction")
        print(
            f"[design-review] pages={len(design['pages'])} "
            f"resources={len(design.get('resource_candidates') or [])}"
        )
        design_approved = await _request(client, "POST", design_approve_path, json={})
        if design_approved["visual_design_director"]["status"] != "approved":
            raise SmokeFailure(
                f"design approval returned {design_approved['visual_design_director']['status']}"
            )
        print(
            "[design-approve] status=approved "
            f"hash={design_approved['visual_design_director']['approved']['visual_direction_hash'][:16]}"
        )

        runs = await _request(client, "GET", f"/api/v1/sessions/{session_id}/runs")
        keys = {run["agent_key"] for run in runs}
        expected_keys = {"discovery", "content_architect", "visual_design_director"}
        if keys != expected_keys:
            raise SmokeFailure(f"unexpected agent keys: {keys}")
        print(f"[runs] count={len(runs)} agent_keys={sorted(keys)}")
    print(f"LIVE FRONTEND API SMOKE PASSED: {base_url}/")


def run() -> int:
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"LIVE FRONTEND API SMOKE FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
