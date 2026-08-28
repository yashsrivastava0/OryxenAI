from __future__ import annotations

from oryxenai.agents.code_generator.core.typescript_ast_audit import _route_source_path


def test_route_source_path_does_not_rehash_planner_storage_key() -> None:
    route = {
        "route_id": "home",
        "storage_key": "home-4ea140588150-4859f06d",
    }

    assert _route_source_path(route, semantic=True) == (
        "src/routes/home-4ea140588150-4859f06d/index.tsx"
    )


def test_route_source_path_semanticizes_route_id_without_storage_key() -> None:
    assert _route_source_path({"route_id": "home"}, semantic=True).startswith("src/routes/home-")
