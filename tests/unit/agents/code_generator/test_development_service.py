from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest

from oryxenai.agents.code_generator.core import development_service
from oryxenai.core.settings import Settings


def test_browser_ready_accepts_configured_system_executable(monkeypatch):
    monkeypatch.setattr(development_service.shutil, "which", lambda value: value)

    assert development_service.browser_ready(
        SimpleNamespace(browser_executable="chromium", browser_name="chromium")
    )


def test_browser_ready_accepts_playwright_browser_cache(monkeypatch, tmp_path):
    browser_dir = tmp_path / "chromium-1234"
    browser_dir.mkdir()
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))
    monkeypatch.setattr(development_service.shutil, "which", lambda value: None)

    assert development_service.browser_ready(
        SimpleNamespace(browser_executable="", browser_name="chromium")
    )


def test_preview_health_url_derives_native_target_and_rejects_bind_address() -> None:
    assert (
        development_service._preview_health_url(
            SimpleNamespace(preview_health_url="", preview_host="127.0.0.1", preview_port=4174)
        )
        == "http://127.0.0.1:4174/health/live"
    )
    assert (
        development_service._preview_health_url(
            SimpleNamespace(
                preview_health_url="",
                preview_host="0.0.0.0",  # noqa: S104
                preview_port=4174,
            )
        )
        is None
    )
    assert (
        development_service._preview_health_url(
            SimpleNamespace(
                preview_health_url="not-a-url", preview_host="127.0.0.1", preview_port=4174
            )
        )
        is None
    )


def test_generation_retry_identity_changes_after_terminal_run_write() -> None:
    first = development_service._generation_attempt_key(
        UUID("00000000-0000-0000-0000-000000000123"),
        plan_hash="plan-hash",
        resource_hash="resource-hash",
        dependency_hash="dependency-hash",
        attempt=2,
        revision=10,
    )
    second = development_service._generation_attempt_key(
        UUID("00000000-0000-0000-0000-000000000123"),
        plan_hash="plan-hash",
        resource_hash="resource-hash",
        dependency_hash="dependency-hash",
        attempt=2,
        revision=11,
    )

    assert first != second


@pytest.mark.asyncio
async def test_preview_gateway_probe_accepts_only_successful_2xx(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    class FakeResponse:
        status_code = 204

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            calls.append(("options", kwargs))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def get(self, url: str) -> FakeResponse:
            calls.append((url, {}))
            return FakeResponse()

    monkeypatch.setattr(development_service.httpx, "AsyncClient", FakeClient)
    ready, blocker = await development_service._probe_preview_gateway(
        SimpleNamespace(
            preview_health_url="http://preview-gateway:4174/health/live",
            preview_host="0.0.0.0",  # noqa: S104
            preview_port=4174,
        )
    )

    assert ready is True
    assert blocker is None
    assert calls[0] == ("options", {"follow_redirects": False, "timeout": 1.5, "trust_env": False})
    assert calls[1][0] == "http://preview-gateway:4174/health/live"


@pytest.mark.asyncio
async def test_preview_gateway_probe_reports_unreachable_for_failure_and_non_2xx(
    monkeypatch,
) -> None:
    class FakeResponse:
        status_code = 503

    class FakeClient:
        def __init__(self, **_kwargs: object) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def get(self, _url: str) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(development_service.httpx, "AsyncClient", FakeClient)
    ready, blocker = await development_service._probe_preview_gateway(
        SimpleNamespace(preview_health_url="http://preview-gateway:4174/health/live")
    )
    assert ready is False
    assert blocker == "preview_gateway_unreachable"

    class FailingClient(FakeClient):
        async def get(self, url: str) -> FakeResponse:
            raise httpx.ConnectError("gateway down", request=httpx.Request("GET", url))

    monkeypatch.setattr(development_service.httpx, "AsyncClient", FailingClient)
    ready, blocker = await development_service._probe_preview_gateway(
        SimpleNamespace(preview_health_url="http://preview-gateway:4174/health/live")
    )
    assert ready is False
    assert blocker == "preview_gateway_unreachable"


@pytest.mark.asyncio
async def test_readiness_is_async_and_exposes_preview_configuration_blocker(monkeypatch) -> None:
    settings = Settings()
    settings.code_generator_verification.preview_health_url = ""
    settings.code_generator_verification.preview_host = "0.0.0.0"  # noqa: S104
    settings.code_generator_verification.preview_port = 4174
    service = development_service.CodeGeneratorDevelopmentService(
        None,
        None,
        settings,  # type: ignore[arg-type]
    )
    monkeypatch.setattr(service, "build_preparation_packs", lambda: [])
    monkeypatch.setattr(development_service, "browser_ready", lambda _config: False)
    monkeypatch.setattr(development_service, "create_preview_storage", lambda _settings: object())
    monkeypatch.setattr(development_service, "code_generator_wire_schema_issues", lambda: {})

    result = await service.readiness()

    assert result["preview_gateway_ready"] is False
    assert "preview_gateway_not_configured" in result["readiness_blockers"]


@pytest.mark.asyncio
async def test_provider_preflight_is_exposed_as_a_safe_service_operation(monkeypatch):
    settings = Settings()

    async def fake_preflight(_settings, profile_names):
        assert settings is _settings
        assert settings.code_generator_development.planner_profile in profile_names
        assert "code_generator_foundation_builder" not in profile_names
        return {
            "status": "ready",
            "checked_profiles": [settings.code_generator_development.planner_profile],
            "private_context_sent": False,
        }

    monkeypatch.setattr(development_service, "run_provider_preflight", fake_preflight)
    service = development_service.CodeGeneratorDevelopmentService(None, None, settings)  # type: ignore[arg-type]

    result = await service.provider_preflight()

    assert result["status"] == "ready"
    assert result["private_context_sent"] is False
