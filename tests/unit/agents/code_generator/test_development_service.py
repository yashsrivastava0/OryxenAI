from types import SimpleNamespace

from oryxenai.agents.code_generator.core import development_service


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
