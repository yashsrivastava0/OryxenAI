"""Regression coverage for the Phase 2 route authorization matrix."""

from __future__ import annotations

from fastapi import FastAPI

from oryxenai.api.dependencies import (
    get_bearer_token,
    get_current_user,
    require_admin,
    require_onboarded_user,
    require_session_owner_or_admin,
)
from oryxenai.core.settings import Settings
from oryxenai.main import create_app


def _api_routes(app: FastAPI) -> list[tuple[str, str, object]]:
    routes: list[tuple[str, str, object]] = []
    for included in app.routes:
        contexts = getattr(included, "effective_route_contexts", None)
        if contexts is None:
            continue
        for context in contexts():
            path = context.path
            if not path.startswith("/api/v1"):
                continue
            for method in sorted(context.original_route.methods or set()):
                if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                    continue
                routes.append((method, path, context.original_route))
    return routes


def _dependency_calls(route: object) -> set[object]:
    dependant = route.dependant  # type: ignore[attr-defined]
    calls: set[object] = set()

    def visit(node: object) -> None:
        calls.add(node.call)  # type: ignore[attr-defined]
        for child in node.dependencies:  # type: ignore[attr-defined]
            visit(child)

    visit(dependant)
    return calls


def _require(route: object, dependency: object) -> None:
    assert dependency in _dependency_calls(route), (
        f"{route.methods} {route.path} is missing {getattr(dependency, '__name__', dependency)}"
    )


def test_every_business_api_route_has_an_explicit_phase2_policy() -> None:
    app = create_app()
    routes = _api_routes(app)
    assert routes

    for method, path, route in routes:
        if path == "/api/v1/me":
            # Identity admission/onboarding routes deliberately remain usable
            # before username onboarding completes.
            _require(route, get_current_user)
            assert require_onboarded_user not in _dependency_calls(route)
            continue
        if path == "/api/v1/me/username":
            # Username claim performs its own current-user/onboarding decision
            # inside AuthService and must remain reachable before onboarding.
            _require(route, get_bearer_token)
            assert require_onboarded_user not in _dependency_calls(route)
            continue
        if path == "/api/v1/agents":
            _require(route, require_onboarded_user)
            continue
        if path in {"/api/v1/sessions"}:
            _require(route, require_onboarded_user)
            continue
        if path.startswith("/api/v1/sessions/{session_id}/runs/mock"):
            _require(route, require_admin)
            _require(route, require_session_owner_or_admin)
            continue
        if (
            path.startswith("/api/v1/sessions/{session_id}/")
            or path == "/api/v1/sessions/{session_id}"
        ):
            _require(route, require_session_owner_or_admin)
            continue
        if path.startswith("/api/v1/system/") or path == "/api/v1/model-profiles":
            _require(route, require_admin)
            continue
        if path.startswith("/api/v1/build-preparation/fixture/"):
            _require(route, require_admin)
            continue
        if path.startswith("/api/v1/development/code-generator/"):
            _require(route, require_admin)
            continue
        raise AssertionError(f"Unclassified business API route: {method} {path}")


def test_public_health_routes_have_no_auth_dependency() -> None:
    app = create_app()
    health_routes: dict[str, object] = {}
    for included in app.routes:
        contexts = getattr(included, "effective_route_contexts", None)
        if contexts is None:
            continue
        for context in contexts():
            if context.path in {"/health/live", "/health/ready"}:
                health_routes[context.path] = context.original_route
    assert set(health_routes) == {"/health/live", "/health/ready"}
    for route in health_routes.values():
        assert get_current_user not in _dependency_calls(route)
        assert require_onboarded_user not in _dependency_calls(route)
        assert require_admin not in _dependency_calls(route)


def test_development_api_routes_are_absent_when_dev_ui_is_disabled() -> None:
    settings = Settings()
    settings.app.enable_dev_ui = False
    settings.build_preparation.fixture_enabled = False
    settings.code_generator_development.enabled = False
    app = create_app(settings)
    paths = {path for _method, path, _route in _api_routes(app)}
    assert not any(path.startswith("/api/v1/build-preparation/fixture") for path in paths)
    assert not any(path.startswith("/api/v1/development/code-generator") for path in paths)
    assert "/api/v1/sessions/{session_id}/runs/mock" not in paths
