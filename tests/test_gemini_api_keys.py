"""Test and verification suite for Gemini API keys configured in .env.

Tests GEMINI_API_KEY1, GEMINI_API_KEY2, and GEMINI_API_KEY3 against
Google's Gemini API endpoints (listing models and generating content).

Can be executed in two ways:
  1. Standalone diagnostic script:
     uv run python tests/test_gemini_api_keys.py

  2. Direct pytest invocation:
     uv run pytest tests/test_gemini_api_keys.py -s
"""

from __future__ import annotations

import os
import sys
from typing import Any

import httpx
import pytest
from dotenv import load_dotenv

load_dotenv()

CANDIDATE_MODELS = [
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
]


def _should_run_live() -> bool:
    """Return True if explicitly requested via env or direct pytest argument."""
    if os.environ.get("RUN_LIVE_GEMINI") == "1":
        return True
    return any("test_gemini_api_keys" in arg for arg in sys.argv)


def check_gemini_key(
    key: str | None,
    models: list[str] | None = None,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """Test a Gemini API key against Google Generative Language API.

    Returns a diagnostic dictionary with status code, active model, response text,
    and error message if unsuccessful.
    """
    if not key or not key.strip():
        return {
            "working": False,
            "status_code": None,
            "model": None,
            "response": None,
            "error": "Key is empty or not set in environment.",
        }

    candidate_models = models or CANDIDATE_MODELS
    last_error: str | None = None
    last_status: int | None = None

    with httpx.Client(timeout=timeout) as client:
        # First check models endpoint
        try:
            list_resp = client.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                params={"key": key},
            )
            if list_resp.status_code != 200:
                err_data = (
                    list_resp.json().get("error", {})
                    if "application/json" in list_resp.headers.get("content-type", "")
                    else {}
                )
                msg = err_data.get("message", list_resp.text)
                return {
                    "working": False,
                    "status_code": list_resp.status_code,
                    "model": None,
                    "response": None,
                    "error": f"{list_resp.status_code}: {msg}",
                }
        except Exception as exc:
            return {
                "working": False,
                "status_code": None,
                "model": None,
                "response": None,
                "error": f"Connection error: {exc}",
            }

        # Test content generation with candidate models
        for model in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            payload = {"contents": [{"parts": [{"text": "Reply with exactly: Gemini OK"}]}]}
            try:
                resp = client.post(url, json=payload)
                last_status = resp.status_code
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = "".join(p.get("text", "") for p in parts if "text" in p).strip()
                        return {
                            "working": True,
                            "status_code": 200,
                            "model": model,
                            "response": text,
                            "error": None,
                        }
                err_data = (
                    resp.json().get("error", {})
                    if "application/json" in resp.headers.get("content-type", "")
                    else {}
                )
                last_error = f"{resp.status_code}: {err_data.get('message', resp.text)}"
                if resp.status_code in (401, 403):
                    break
            except Exception as exc:
                last_error = str(exc)

    return {
        "working": False,
        "status_code": last_status,
        "model": None,
        "response": None,
        "error": last_error or "No model succeeded.",
    }


@pytest.mark.live
def test_gemini_api_key_1() -> None:
    """Verify GEMINI_API_KEY1."""
    if not _should_run_live():
        pytest.skip("Live Gemini test skipped. Run directly or set RUN_LIVE_GEMINI=1.")
    key = os.getenv("GEMINI_API_KEY1")
    result = check_gemini_key(key)
    assert result["working"] is True, (
        f"GEMINI_API_KEY1 failed (HTTP {result['status_code']}): {result['error']}"
    )


@pytest.mark.live
def test_gemini_api_key_2() -> None:
    """Verify GEMINI_API_KEY2."""
    if not _should_run_live():
        pytest.skip("Live Gemini test skipped. Run directly or set RUN_LIVE_GEMINI=1.")
    key = os.getenv("GEMINI_API_KEY2")
    result = check_gemini_key(key)
    assert result["working"] is True, (
        f"GEMINI_API_KEY2 failed (HTTP {result['status_code']}): {result['error']}"
    )
    assert result["response"], "Expected non-empty response from GEMINI_API_KEY2"


@pytest.mark.live
def test_gemini_api_key_3() -> None:
    """Verify GEMINI_API_KEY3."""
    if not _should_run_live():
        pytest.skip("Live Gemini test skipped. Run directly or set RUN_LIVE_GEMINI=1.")
    key = os.getenv("GEMINI_API_KEY3")
    result = check_gemini_key(key)
    assert result["working"] is True, (
        f"GEMINI_API_KEY3 failed (HTTP {result['status_code']}): {result['error']}"
    )
    assert result["response"], "Expected non-empty response from GEMINI_API_KEY3"


def main() -> None:
    """Run standalone CLI diagnostic for all 3 Gemini API keys."""
    keys = [
        ("GEMINI_API_KEY1", os.getenv("GEMINI_API_KEY1")),
        ("GEMINI_API_KEY2", os.getenv("GEMINI_API_KEY2")),
        ("GEMINI_API_KEY3", os.getenv("GEMINI_API_KEY3")),
    ]

    print("=" * 70)
    print(" OryxenAI — Gemini Free Tier API Keys Diagnostic")
    print("=" * 70)

    for name, key in keys:
        masked_key = (key[:8] + "..." + key[-4:]) if key and len(key) > 12 else "[NOT SET]"
        print(f"\nEvaluating: {name} (Key: {masked_key})")
        result = check_gemini_key(key)
        if result["working"]:
            print(f"  Status   : [OK] WORKING (HTTP {result['status_code']})")
            print(f"  Model    : {result['model']}")
            print(f"  Response : {result['response']}")
        else:
            print(f"  Status   : [FAIL] NOT WORKING (HTTP {result['status_code']})")
            print(f"  Reason   : {result['error']}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
