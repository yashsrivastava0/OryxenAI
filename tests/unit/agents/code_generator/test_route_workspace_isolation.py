from __future__ import annotations

import pytest

from oryxenai.agents.code_generator.core.generation_orchestrator import (
    _prepare_isolated_route_repo,
)


@pytest.mark.asyncio
async def test_route_isolation_reuses_dependencies_without_blocking_copy(tmp_path) -> None:
    source_repo = tmp_path / "source"
    (source_repo / "src" / "routes" / "home").mkdir(parents=True)
    (source_repo / "src" / "routes" / "home" / "index.tsx").write_text(
        "export const route = 'home';\n",
        encoding="utf-8",
    )
    (source_repo / "node_modules" / "large-package").mkdir(parents=True)
    (source_repo / "node_modules" / "large-package" / "index.js").write_text(
        "disposable",
        encoding="utf-8",
    )
    (source_repo / "dist").mkdir()
    (source_repo / "dist" / "bundle.js").write_text("disposable", encoding="utf-8")

    isolated_repo = await _prepare_isolated_route_repo(source_repo, tmp_path / "isolated")

    assert (isolated_repo / "src" / "routes" / "home" / "index.tsx").is_file()
    assert (isolated_repo / "node_modules" / "large-package" / "index.js").read_text(
        encoding="utf-8"
    ) == "disposable"
    assert not (isolated_repo / "dist").exists()
