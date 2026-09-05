"""Regression coverage for the Phase 2 route authorization matrix."""

from __future__ import annotations

from fastapi import FastAPI

from oryxenai.api.dependencies import (
    get_bearer_token,
    get_current_user,
    get_pipeline_user,
    require_admin,
    require_detached_pipeline_mode,
    require_mutable_portfolio,
    require_onboarded_user,
    require_pipeline_mutable,
    require_pipeline_session,
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


_MUTATION_CLASSES: dict[tuple[str, str], str] = {
    ("PUT", "/api/v1/me/username"): "identity_onboarding",
    ("POST", "/api/v1/pipeline/model-profiles/preflight"): "detached_diagnostic",
    ("POST", "/api/v1/sessions"): "portfolio_admission",
    ("POST", "/api/v1/sessions/{session_id}/runs/mock"): "portfolio_mutation",
    ("POST", "/api/v1/sessions/{session_id}/discovery/start"): "portfolio_mutation",
    ("PUT", "/api/v1/sessions/{session_id}/discovery/answers"): "portfolio_mutation",
    ("POST", "/api/v1/sessions/{session_id}/discovery/revise"): "portfolio_mutation",
    ("POST", "/api/v1/sessions/{session_id}/discovery/approve"): "portfolio_mutation",
    ("POST", "/api/v1/sessions/{session_id}/discovery/stop"): "portfolio_mutation",
    ("POST", "/api/v1/sessions/{session_id}/content-architect/start"): "portfolio_mutation",
    ("POST", "/api/v1/sessions/{session_id}/content-architect/revise"): "portfolio_mutation",
    ("POST", "/api/v1/sessions/{session_id}/content-architect/approve"): "portfolio_mutation",
    ("POST", "/api/v1/sessions/{session_id}/content-architect/stop"): "portfolio_mutation",
    ("POST", "/api/v1/sessions/{session_id}/visual-design-director/start"): "portfolio_mutation",
    ("POST", "/api/v1/sessions/{session_id}/visual-design-director/revise"): "portfolio_mutation",
    ("POST", "/api/v1/sessions/{session_id}/visual-design-director/approve"): "portfolio_mutation",
    ("POST", "/api/v1/sessions/{session_id}/visual-design-director/stop"): "portfolio_mutation",
    ("POST", "/api/v1/sessions/{session_id}/build-preparation/start"): "portfolio_mutation",
    ("POST", "/api/v1/sessions/{session_id}/build-preparation/regenerate"): "portfolio_mutation",
    ("POST", "/api/v1/sessions/{session_id}/restart"): "portfolio_mutation",
    ("POST", "/api/v1/sessions/{session_id}/code-generator/start"): "portfolio_mutation",
    ("POST", "/api/v1/sessions/{session_id}/code-generator/regenerate"): "portfolio_mutation",
    ("POST", "/api/v1/sessions/{session_id}/code-generator/retry"): "portfolio_mutation",
    ("POST", "/api/v1/system/worker-probes"): "admin_system_mutation",
    ("POST", "/api/v1/client-diagnostics/events"): "client_diagnostics",
    ("POST", "/api/v1/build-preparation/fixture/run"): "admin_fixture_mutation",
    ("POST", "/api/v1/build-preparation/fixture/runs"): "admin_fixture_mutation",
    ("POST", "/api/v1/development/code-generator/provider-preflight"): "admin_development_mutation",
    ("POST", "/api/v1/development/code-generator/runs"): "admin_development_mutation",
    (
        "POST",
        "/api/v1/development/code-generator/runs/from-build-preparation",
    ): "admin_development_mutation",
    ("POST", "/api/v1/development/code-generator/runs/upload"): "admin_development_mutation",
    (
        "POST",
        "/api/v1/development/code-generator/runs/{run_id}/acquire",
    ): "admin_development_mutation",
    (
        "POST",
        "/api/v1/development/code-generator/runs/{run_id}/generate",
    ): "admin_development_mutation",
    (
        "POST",
        "/api/v1/development/code-generator/runs/{run_id}/verify",
    ): "admin_development_mutation",
}


def test_every_business_api_route_has_an_explicit_phase2_policy() -> None:
    app = create_app()
    routes = _api_routes(app)
    assert routes

    for method, path, route in routes:
        if path == "/api/v1/client-diagnostics/events":
            assert method == "POST"
            continue
        if path.startswith("/api/v1/admin/"):
            _require(route, require_admin)
            continue
        if method != "GET":
            assert (method, path) in _MUTATION_CLASSES, f"Unclassified mutation: {method} {path}"
        if path == "/api/v1/me":
            # Identity admission/onboarding routes deliberately remain usable
            # before username onboarding completes.
            _require(route, get_current_user)
            assert require_onboarded_user not in _dependency_calls(route)
            continue
        if path == "/api/v1/me/username":
            # Username claim performs its own current-user/onboarding decision
            # inside AuthService and must remain reachable before onboarding.
            assert _MUTATION_CLASSES[(method, path)] == "identity_onboarding"
            _require(route, get_bearer_token)
            assert require_onboarded_user not in _dependency_calls(route)
            continue
        if path == "/api/v1/agents":
            _require(route, require_onboarded_user)
            continue
        if path in {"/api/v1/sessions"}:
            if method == "POST":
                _require(route, get_pipeline_user)
            else:
                _require(route, require_onboarded_user)
            if method != "GET":
                assert _MUTATION_CLASSES[(method, path)] == "portfolio_admission"
            continue
        if path.startswith("/api/v1/sessions/{session_id}/runs/mock"):
            assert _MUTATION_CLASSES[(method, path)] == "portfolio_mutation"
            _require(route, require_admin)
            _require(route, require_session_owner_or_admin)
            _require(route, require_mutable_portfolio)
            continue
        if path == "/api/v1/sessions/{session_id}/restart":
            _require(route, require_detached_pipeline_mode)
            continue
        if path.startswith("/api/v1/pipeline/model-profiles"):
            if method != "GET":
                assert _MUTATION_CLASSES[(method, path)] == "detached_diagnostic"
            _require(route, require_detached_pipeline_mode)
            continue
        if (
            path.startswith("/api/v1/sessions/{session_id}/")
            or path == "/api/v1/sessions/{session_id}"
        ):
            pipeline_route = (
                any(
                    stage in path
                    for stage in (
                        "/discovery",
                        "/content-architect",
                        "/visual-design-director",
                        "/build-preparation",
                    )
                )
                or path == "/api/v1/sessions/{session_id}"
            )
            _require(
                route,
                require_pipeline_session if pipeline_route else require_session_owner_or_admin,
            )
            if method != "GET":
                assert _MUTATION_CLASSES[(method, path)] == "portfolio_mutation"
                _require(
                    route, require_pipeline_mutable if pipeline_route else require_mutable_portfolio
                )
            continue
        if path.startswith("/api/v1/system/") or path == "/api/v1/model-profiles":
            if method != "GET":
                assert _MUTATION_CLASSES[(method, path)] == "admin_system_mutation"
            _require(route, require_admin)
            continue
        if path.startswith("/api/v1/build-preparation/fixture/"):
            if method != "GET":
                assert _MUTATION_CLASSES[(method, path)] == "admin_fixture_mutation"
            if app.state.settings.auth.development_harness_mode != "detached":
                _require(route, require_admin)
            continue
        if path.startswith("/api/v1/development/code-generator/"):
            if method != "GET":
                assert _MUTATION_CLASSES[(method, path)] == "admin_development_mutation"
            if app.state.settings.auth.development_harness_mode != "detached":
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


def test_attached_fixture_routes_retain_admin_boundary() -> None:
    settings = Settings()
    settings.auth.development_harness_mode = "attached"
    app = create_app(settings)
    fixture_routes = [
        route
        for _method, path, route in _api_routes(app)
        if path.startswith("/api/v1/build-preparation/fixture/")
    ]

    assert fixture_routes
    for route in fixture_routes:
        _require(route, require_admin)


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
