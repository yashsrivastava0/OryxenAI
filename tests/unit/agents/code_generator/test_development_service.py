from types import SimpleNamespace

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


@pytest.mark.asyncio
async def test_provider_preflight_is_exposed_as_a_safe_service_operation(monkeypatch):
    settings = Settings()

    async def fake_preflight(_settings, profile_names):
        assert settings is _settings
        assert settings.code_generator_development.planner_profile in profile_names
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
